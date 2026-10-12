"""Prepare a new Alpaca scientific run from receipt-bound real snapshots.

No network requests or historical replacements. Local publisher weights and
every consumed source are checked against retained acquisition receipts.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT / 'src'))
PUBLISHER = 'ProsusAI/finbert'
REVISION = '0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031'
EXPECTED_MODEL_SHA256 = {
    'config.json': 'f6449ddda85eb726207a40be59c0cd3bd4b142ccb27298d5e45f9ae3396b1abe',
    'tokenizer_config.json': 'ffc7913f6084b138dad68de5a0c2f0ee25ac983709260901e01f53be5796b9d9',
    'special_tokens_map.json': '303df45a03609e4ead04bc3dc1536d0ab19b5358db685b6f3da123d05ec200e3',
    'vocab.txt': '07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3',
    'model.safetensors': 'e5897858ff819aad7629b96ce521ae5477952d03634ef5dd30ed2d76357a9f00',
}


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def save(path, value, *, exclusive=False):
    with path.open('x' if exclusive else 'w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False, default=str)
        stream.write('\n')


def verified_inputs(price_receipt, news_receipt, model_receipt):
    prices = json.loads(price_receipt.read_text(encoding='utf-8'))
    news = json.loads(news_receipt.read_text(encoding='utf-8'))
    model = json.loads(model_receipt.read_text(encoding='utf-8'))
    if prices.get('schema') != 'investify-fresh-alpaca-prices-v1':
        raise ValueError('Unrecognised price acquisition receipt')
    if news.get('status') != 'acquired_and_audited' or news.get('pagination_complete') is not True:
        raise ValueError('News acquisition must have completed and passed its audit')
    if model.get('publisher') != PUBLISHER or model.get('revision') != REVISION:
        raise ValueError('Use the pinned original FinBERT publisher revision')
    if model.get('status') != 'downloaded_and_hash_verified':
        raise ValueError('FinBERT acquisition has not passed its byte gate')
    rows = [row for row in prices['results'] if row['source'] == 'split']
    if len(rows) != 1 or rows[0].get('http_status') != 200 or rows[0].get('pagination_complete') is not True:
        raise ValueError('Require one complete split-adjusted provider price response')
    price = rows[0]
    price_path = (PROJECT / price['response_file']).resolve()
    news_path = Path(news['conservative_csv']['path']).resolve()
    if digest(price_path) != price['response_sha256'] or digest(news_path) != news['conservative_csv']['sha256']:
        raise ValueError('Acquired price/news bytes no longer match their receipts')
    model_path = Path(model['directory']).resolve()
    required = {'config.json', 'tokenizer_config.json', 'special_tokens_map.json', 'vocab.txt', 'model.safetensors'}
    if {row['filename'] for row in model['files']} != required:
        raise ValueError('Require the complete five-file original FinBERT snapshot')
    if any(row['sha256'] != EXPECTED_MODEL_SHA256[row['filename']] for row in model['files']):
        raise ValueError('Model receipt differs from the pinned publisher hashes')
    for row in model['files']:
        path = model_path / row['filename']
        if (row.get('publisher_identity_verified') is not True or path.stat().st_size != row['size_bytes']
                or digest(path) != row['sha256']):
            raise ValueError('Publisher model file identity changed: ' + row['filename'])
    return price_path, news_path, model_path, {
        'price_response_sha256': digest(price_path), 'conservative_news_sha256': digest(news_path),
        'model_files_sha256': {row['filename']: row['sha256'] for row in model['files']},
        'acquisition_receipts_sha256': {str(path): digest(path) for path in (price_receipt, news_receipt, model_receipt)},
        'price_adjustment': 'Alpaca SIP split adjustment, including vendor action vintage; no cash-dividend adjustment',
        'news_timing': news['audit']['revision_policy'],
        'point_in_time_availability_proven': False, 'historical_byte_reproduction': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--price-receipt', type=Path, required=True)
    parser.add_argument('--news-receipt', type=Path, required=True)
    parser.add_argument('--model-receipt', type=Path, required=True)
    parser.add_argument('--run-directory', type=Path, required=True)
    parser.add_argument('--score-cache', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--batch-size', type=int, default=32)
    args = parser.parse_args()
    run, cache, receipt = args.run_directory.resolve(), args.score_cache.resolve(), args.receipt.resolve()
    if not run.is_relative_to(ROOT / 'artifacts/scientific_runs'):
        raise ValueError('New outputs belong under code/artifacts/scientific_runs')
    if not cache.is_relative_to(Path('E:/AI-Tools/Cache').resolve()):
        raise ValueError('Score caches belong on E:/AI-Tools/Cache')
    if not receipt.is_relative_to(PROJECT / 'evidence'):
        raise ValueError('Use a project evidence receipt')
    if run.exists() or cache.exists() or receipt.exists():
        raise ValueError('Preserve all prior outputs; choose new run/cache/receipt identities')
    if args.threads < 1 or args.batch_size < 1:
        raise ValueError('Threads and batch size must be positive')
    os.environ.update(TEMP='E:/AI-Tools/Temp', TMP='E:/AI-Tools/Temp',
                      PYTHONDONTWRITEBYTECODE='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      HF_HOME='E:/AI-Tools/Cache/huggingface',
                      MPLCONFIGDIR='E:/AI-Tools/Temp/investify-scientific-process-cache/matplotlib',
                      NUMBA_CACHE_DIR='E:/AI-Tools/Temp/investify-scientific-process-cache/numba')
    report = {'schema': 'investify-fresh-alpaca-science-inputs-v1',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'status': 'verifying',
              'run_directory': str(run), 'score_cache': str(cache), 'network_requests': 0,
              'fnspid_requests': 0, 'historical_outputs_modified': False,
              'scientific_harness_executed': False, 'model_inference_executed': False}
    save(receipt, report, exclusive=True)
    try:
        price_path, news_path, model_path, identities = verified_inputs(
            args.price_receipt.resolve(), args.news_receipt.resolve(), args.model_receipt.resolve())
        report['verified_inputs'] = identities
        import numpy as np
        import pandas as pd
        import torch
        import yaml
        from investify.calendars import NYSECalendar
        from investify.market_inputs import price_snapshot, validate_price_sessions
        from investify.ingest.news import load_alpaca_ticker_news
        from investify.news_cache import attach_cached_scores
        from investify.store import AppendOnlyStore
        from investify.features.sentiment import FinBERTScorer
        torch.set_num_threads(args.threads)
        report['runtime'] = {'python': sys.version, 'executable': sys.executable,
                            'torch_threads': args.threads, 'exact_uv_lock_restored': False,
                            'packages': {name: importlib.metadata.version(name) for name in (
                                'numpy', 'pandas', 'torch', 'transformers', 'scikit-learn', 'xgboost',
                                'shap', 'pyarrow', 'pandas-market-calendars')}}
        payload = json.loads(price_path.read_text(encoding='utf-8'))
        if payload.get('next_page_token') or set(payload['bars']) != {'NVDA'}:
            raise ValueError('Price payload pagination/ticker does not match the experiment')
        bars = payload['bars']['NVDA']
        prices = pd.DataFrame([{'ticker': 'NVDA', 'date': pd.Timestamp(row['t']).tz_convert('America/New_York').date(),
                                'open': row['o'], 'high': row['h'], 'low': row['l'], 'close': row['c'],
                                'volume': row['v']} for row in bars])
        values = prices[['open', 'high', 'low', 'close', 'volume']].to_numpy(dtype=float)
        if (not np.isfinite(values).all() or (values[:, :4] <= 0).any()
                or (values[:, 4] < 0).any()
                or not (prices['low'] <= prices[['open', 'close']].min(axis=1)).all()
                or not (prices['high'] >= prices[['open', 'close']].max(axis=1)).all()):
            raise ValueError('Malformed or inconsistent provider OHLCV')
        prices = price_snapshot(prices, ticker='NVDA', start='2018-01-01', end='2023-12-31')
        calendar = NYSECalendar()
        report['calendar_audit'] = validate_price_sessions(prices, calendar)
        expected = {day for day in calendar._valid_days if pd.Timestamp('2018-01-01').date()
                    <= day <= pd.Timestamp('2023-12-31').date()}
        if set(prices['date']) != expected:
            raise ValueError('Provider prices do not cover every requested exchange session')
        prices['event_ts'] = pd.to_datetime(prices['date']).dt.tz_localize('America/New_York') + pd.Timedelta(hours=16)
        prices['year'] = pd.to_datetime(prices['date']).dt.year
        news = load_alpaca_ticker_news(str(news_path), 'NVDA', start='2018-01-01', end='2023-12-31')
        report['news_ingestion_audit'] = news.attrs['ingestion_audit']
        raw_news = pd.read_csv(news_path)
        available = pd.to_datetime(raw_news['available_at'], utc=True, format='ISO8601')
        event = pd.to_datetime(raw_news['event_ts'], utc=True, format='ISO8601')
        created = pd.to_datetime(raw_news['created_at'], utc=True, format='ISO8601')
        updated = pd.to_datetime(raw_news['updated_at'], utc=True, format='ISO8601')
        if not event.eq(available).all() or not event.eq(pd.concat([created, updated], axis=1).max(axis=1)).all():
            raise ValueError('Conservative news must use max(created_at, updated_at)')
        run.mkdir(parents=True)
        inputs = run / 'inputs'
        inputs.mkdir()
        store = AppendOnlyStore(inputs / 'store')
        written = store.append(prices, 'prices', ['ticker','date','open','high','low','close','volume'], ['ticker','year'])
        report.update(status='scoring', price_rows=written, news_rows=len(news),
                      finbert_publisher=PUBLISHER, finbert_revision=REVISION)
        save(receipt, report)
        scorer = FinBERTScorer(str(cache), model_path=model_path, device='cpu')
        started = time.monotonic()
        # Repeated batches checkpoint the score cache and expose actual progress.
        for offset in range(0, len(news), 256):
            scorer.score(news.iloc[offset:offset + 256], batch_size=args.batch_size)
            report.update(scored_news_rows=min(offset + 256, len(news)),
                          unique_scored_headlines=len(scorer._cache), model_inference_executed=True)
            save(receipt, report)
            print(f"Scored {report['scored_news_rows']}/{len(news)} rows", flush=True)
        score_file = cache / 'finbert_scores.parquet'
        scored = attach_cached_scores(news, pd.read_parquet(score_file))
        report.update(scoring_seconds=round(time.monotonic() - started, 3),
                      score_cache_sha256=digest(score_file), scored_cardinality=len(scored))
        cfg = yaml.safe_load((ROOT / 'config/spike.yaml').read_text(encoding='utf-8'))
        cfg['paths'] = {'store': str(inputs / 'store'), 'artifacts': str(inputs)}
        cfg['sentiment'].update(cache_dir=str(cache), publisher=PUBLISHER, revision=REVISION,
                                model_path=str(model_path), acquisition_receipt_sha256=digest(args.model_receipt))
        cfg['corpora'] = {'alpaca': dict(cfg['corpora']['alpaca'], path=str(news_path),
                                        feature_matrix=str(inputs / 'not_precomputed.parquet'))}
        cfg['default_corpus'] = 'alpaca'
        cfg['news'].update(source='Alpaca/Benzinga', extracted_path=str(news_path))
        cfg['fresh_snapshot_policy'] = identities
        manifest = {'schema': 'investify-fresh-alpaca-corpus-v1', 'identity': run.name,
                    'source': 'Alpaca/Benzinga fresh revision-conservative snapshot',
                    'raw_subsets': [{'path': str(news_path), 'sha256': digest(news_path)}],
                    'price_response': {'path': str(price_path), 'sha256': digest(price_path)},
                    'acquisition': identities,
                    'scope': 'New experiment; does not restore September corpus or historical data vintage'}
        save(inputs / 'corpus_manifest.json', manifest, exclusive=True)
        config_path = run / 'fresh_config.yaml'
        with config_path.open('x', encoding='utf-8') as stream:
            yaml.safe_dump(cfg, stream, sort_keys=False)
        after = verified_inputs(args.price_receipt.resolve(), args.news_receipt.resolve(), args.model_receipt.resolve())[3]
        if after != identities:
            raise ValueError('Acquired source identities changed during preparation')
        report.update(status='prepared_and_validated', config_path=str(config_path),
                      config_sha256=digest(config_path), manifest_sha256=digest(inputs / 'corpus_manifest.json'),
                      script_sha256=digest(__file__), sentiment_source_sha256=digest(ROOT / 'src/investify/features/sentiment.py'))
    except Exception as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        save(receipt, report)
    print(f"Prepared fresh scientific inputs: {run}", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
