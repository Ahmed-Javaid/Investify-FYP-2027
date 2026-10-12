"""Phase 1 end-to-end: fetch NVDA prices, load+session-map+score NVDA
news, write both to the append-only store, compute indicators, as-of
join sentiment onto price bars, compute labels at both horizons. Writes
the resulting feature matrix to data/store/feature_matrix.parquet and
prints a summary.
"""
import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.calendars import NYSECalendar  # noqa: E402
from investify.features.assembly import add_backward_only_momentum, aggregate_session_sentiment, asof_join_features  # noqa: E402
from investify.features.indicators import compute_indicators  # noqa: E402
from investify.ingest.news import load_ticker_news, map_to_sessions  # noqa: E402
from investify.labels import compute_labels  # noqa: E402
from investify.store import AppendOnlyStore  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config', type=Path, default=Path('config/spike.yaml'))
parser.add_argument('--run-directory', required=True, type=Path)
parser.add_argument('--sentiment-cache', required=True, type=Path, help='New score-cache directory on E:/AI-Tools')
args = parser.parse_args()
run_directory = args.run_directory.resolve()
score_cache = args.sentiment_cache.resolve()
if run_directory.exists() or score_cache.exists():
    raise ValueError('Preserve existing ingestion outputs/cache; choose new run and score-cache directories')
if not run_directory.is_relative_to(Path(__file__).resolve().parents[1] / 'artifacts/scientific_runs'):
    raise ValueError('Ingestion run must remain under artifacts/scientific_runs')
if not score_cache.is_relative_to(Path('E:/AI-Tools').resolve()):
    raise ValueError('Scoring cache must remain on E:/AI-Tools')
os.environ['HF_HOME'] = str(Path('E:/AI-Tools/Temp/investify-scientific-huggingface').resolve())
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
from investify.features.sentiment import FinBERTScorer  # noqa: E402
from investify.ingest.prices import fetch_prices, validate_against_calendar  # noqa: E402
t0 = time.time()
cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))
run_directory.mkdir(parents=True)
cfg['paths']['store'] = str(run_directory / 'store')
cfg['sentiment']['cache_dir'] = str(score_cache)
ticker = cfg["tickers"][0]
assert ticker == "NVDA", f"expected NVDA per the recorded scope decision, got {ticker}"

cal = NYSECalendar()
store = AppendOnlyStore(cfg["paths"]["store"])

print(f"=== Fetching prices for {ticker} {cfg['date_range']['start']}..{cfg['date_range']['end']} ===", flush=True)
prices_df, snapshot_hash = fetch_prices(ticker, cfg["date_range"]["start"], cfg["date_range"]["end"])
validate_against_calendar(prices_df, cal)
print(f"{len(prices_df)} price bars, snapshot_hash={snapshot_hash[:16]}..., zero orphan bars confirmed", flush=True)

n_written = store.append(
    prices_df, "prices",
    content_cols=["ticker", "date", "open", "high", "low", "close", "volume"],
    partition_cols=["ticker"],
)
print(f"store: {n_written} new price rows written ({store.row_count('prices')} total in store)", flush=True)

print(f"\n=== Loading news for {ticker} ===", flush=True)
news_df = load_ticker_news(cfg["news"]["extracted_path"], ticker)
news_df = map_to_sessions(news_df, cal)
print(f"{len(news_df)} headlines loaded, mapped to sessions", flush=True)

n_written = store.append(
    news_df, "news",
    content_cols=["ticker", "headline", "event_ts"],
    partition_cols=["ticker"],
)
print(f"store: {n_written} new news rows written ({store.row_count('news')} total in store)", flush=True)

print(f"\n=== FinBERT sentiment scoring ({len(news_df)} headlines) ===", flush=True)
scorer = FinBERTScorer(cache_dir=cfg["sentiment"]["cache_dir"])
scored_news = scorer.score(news_df, text_col="headline")

print(f"\n=== Aggregating session-level sentiment + momentum ===", flush=True)
session_sentiment = aggregate_session_sentiment(scored_news)
session_sentiment = add_backward_only_momentum(session_sentiment)
print(f"{len(session_sentiment)} (ticker, session) rows with sentiment features", flush=True)

print(f"\n=== Computing technical indicators ===", flush=True)
indicators = compute_indicators(prices_df)
priced = pd.concat([prices_df.reset_index(drop=True), indicators.reset_index(drop=True)], axis=1)

print(f"\n=== As-of joining sentiment onto price bars (max_lookback={cfg['as_of_join']['max_lookback_days']}d) ===", flush=True)
joined = asof_join_features(
    priced, session_sentiment,
    max_lookback_days=cfg["as_of_join"]["max_lookback_days"],
)
n_with_sentiment = joined["mean_polarity"].notna().sum()
print(f"{len(joined)} bars, {n_with_sentiment} ({100*n_with_sentiment/len(joined):.1f}%) have sentiment features attached", flush=True)

print(f"\n=== Computing labels ===", flush=True)
for horizon in cfg["labels"]["horizons_days"]:
    labels = compute_labels(
        joined[["date", "close"]], horizon_days=horizon,
        vol_window_days=cfg["labels"]["volatility_window_days"],
        thresholds=tuple(cfg["labels"]["class_thresholds"]),
    )
    joined[f"label_{horizon}d"] = labels["label"].values
    joined[f"label_score_{horizon}d"] = labels["label_score"].values
    joined[f"label_end_{horizon}d"] = labels['label_end_date'].values
    dist = labels["label"].value_counts(dropna=False)
    print(f"  horizon={horizon}d class distribution: {dist.to_dict()}", flush=True)

out_path = run_directory / "feature_matrix.parquet"
joined.to_parquet(out_path, index=False)
print(f"\n=== DONE in {time.time()-t0:.1f}s. Feature matrix: {len(joined)} rows x {len(joined.columns)} cols -> {out_path} ===", flush=True)
print(joined.columns.tolist(), flush=True)
