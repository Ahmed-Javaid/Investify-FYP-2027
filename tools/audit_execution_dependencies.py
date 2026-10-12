"""Bounded read-only execution audit; no installation, download or model call."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
sys.path.insert(0, str(CODE / 'src'))
from investify.demo_readiness import harness_input_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'evidence') or output.exists():
        raise ValueError('Use a new receipt under this workspace evidence directory')
    import yaml  # Explicit viewer dependency; this does not restore science.
    cfg = yaml.safe_load((CODE / 'config/spike.yaml').read_text(encoding='utf-8'))
    packages = {}
    for module, distribution in (('numpy', 'numpy'), ('pandas', 'pandas'), ('scipy', 'scipy'),
                                  ('sklearn', 'scikit-learn'), ('xgboost', 'xgboost'),
                                  ('pandas_market_calendars', 'pandas-market-calendars'),
                                  ('pyarrow', 'pyarrow'), ('torch', 'torch'),
                                  ('transformers', 'transformers'), ('shap', 'shap'),
                                  ('peft', 'peft'), ('bitsandbytes', 'bitsandbytes'),
                                  ('datasets', 'datasets'), ('accelerate', 'accelerate')):
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
        packages[module] = {'discoverable': importlib.util.find_spec(module) is not None,
                            'installed_distribution_version': version}
    known_inputs = {}
    original = Path('E:/Uni_Stuff/investify_repo')
    for root in (CODE, original):
        for relative in ('data/store', 'data/raw', '.cache/finbert_scores/finbert_scores.parquet'):
            path = root / relative
            known_inputs[str(path)] = path.exists()
    weights = {}
    # Inspect only these declared candidate locations, not the whole drive.
    for relative in ('investify-official-models/qwen25', 'investify-official-models/qwen3',
                     'investify-social-models/cryptobert', 'investify-social-models/cardiff',
                     'investify-student-models/phi3-mini'):
        directory = Path('E:/AI-Tools/Temp') / relative
        weights[str(directory)] = {'exists': directory.exists(),
            'top_level_weight_files': [p.name for p in sorted(directory.glob('*'))
                                      if p.is_file() and p.suffix in ('.gguf', '.safetensors')]}
    health = {}
    opener = build_opener(ProxyHandler({}))
    for url in ('http://127.0.0.1:8501/_stcore/health', 'http://127.0.0.1:8765/health'):
        try:
            with opener.open(url, timeout=3) as response:
                health[url] = {'http_status': response.status}
        except OSError as error:
            health[url] = {'error': f'{type(error).__name__}: {error}'}
    report = {'schema': 'investify-execution-dependency-audit-v1',
              'checked_utc': datetime.now(timezone.utc).isoformat(),
              'python': sys.version.split()[0], 'executable': sys.executable,
              'known_original_and_working_inputs': known_inputs,
              'harness_preflight': {c: harness_input_report(cfg, c, CODE) for c in cfg['corpora']},
              'runtime_packages': packages, 'declared_candidate_locations': weights,
              'latex_commands': {n: shutil.which(n) for n in ('pdflatex', 'lualatex', 'xelatex', 'tectonic', 'latexmk')},
              'local_service_health': health,
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (Path(__file__), CODE / 'src/investify/demo_readiness.py', CODE / 'config/spike.yaml')},
              'scientific_run_executed': False, 'candidate_inference_executed': False,
              'scope': 'Known input paths, current interpreter package metadata/discovery, declared candidate directories, '
                       'compiler PATH and loopback health only. No exhaustive disk search, package import/lock validation, '
                       'model identity validation, external network attempt, inference or training.'}
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Execution audit saved: {output}; no scientific/model run performed')


if __name__ == '__main__':
    main()
