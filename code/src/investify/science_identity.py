"""Byte/config identity for a scientific run, without loading scientific libraries."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILES = (
    'src/investify/engine.py', 'src/investify/decision_record.py', 'src/investify/calibration_split.py',
    'src/investify/science_identity.py', 'src/investify/calendars.py', 'src/investify/labels.py',
    'src/investify/harness/arms.py', 'src/investify/harness/splits.py', 'src/investify/harness/metrics.py',
    'src/investify/features/indicators.py', 'src/investify/features/assembly.py',
    'src/investify/features/sentiment.py', 'src/investify/news_cache.py', 'src/investify/scaling.py',
    'src/investify/market_inputs.py',
    'src/investify/corpus_lineage.py',
    'src/investify/scientific_trace.py',
    'src/investify/ingest/news.py', 'src/investify/store.py', 'pyproject.toml', 'uv.lock',
    'src/investify/harness/run_spike.py', 'scripts/build_decision_records.py',
)


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def input_snapshots(cfg, corpus):
    ticker = cfg['tickers'][0]
    store = Path(cfg['paths']['store'])
    specification = cfg['corpora'][corpus]
    locations = {'prices': store / 'prices' / f'ticker={ticker}',
                 'news': store / 'news' / f'ticker={ticker}' if specification['loader'] == 'fnspid' else Path(specification['path']),
                 'sentiment_scores': Path(cfg['sentiment']['cache_dir']) / 'finbert_scores.parquet'}
    locations['corpus_manifest'] = Path(cfg['paths']['artifacts']) / 'corpus_manifest.json'
    result = {}
    for kind, path in locations.items():
        path = (ROOT / path).resolve()
        files = sorted(path.rglob('*.parquet')) if path.is_dir() else [path]
        if not files or any(not file.is_file() for file in files):
            raise FileNotFoundError(f'No complete {kind} snapshot at {path}')
        result[kind] = {'path': str(path), 'files': {str(file.relative_to(path)) if path.is_dir() else file.name:
                                                   file_digest(file) for file in files}}
    if specification['loader'] == 'fnspid':
        raw = (ROOT / Path(cfg['news']['extracted_path'])).resolve()
        # Restored stores can lack the old extract; retain its absence and
        # detect restoration or mutation during an execution.
        result['declared_raw_subset'] = {'path': str(raw), 'status': 'available' if raw.is_file() else 'missing',
                                         'files': {raw.name: file_digest(raw)} if raw.is_file() else {}}
    return result


def run_identity(cfg, corpus, *, include_inputs=True):
    config_hash = hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
    sources = {relative: file_digest(ROOT / relative) for relative in SOURCE_FILES}
    versions = {}
    for package in ('numpy', 'pandas', 'pyarrow', 'scikit-learn', 'scipy', 'xgboost', 'shap', 'pandas-market-calendars'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    identity = {'source_sha256': sources, 'configuration_sha256': config_hash,
                'input_snapshots': input_snapshots(cfg, corpus) if include_inputs else None,
                'runtime': {'python': sys.version.split()[0], 'packages': versions},
                'scope': 'Byte/config/runtime identity, not proof of source rights, truth, timing quality or inference execution'}
    identity['identity_sha256'] = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return identity
