"""Build the feature matrix on the Alpaca/Benzinga corpus.

Mirrors scripts/build_phase1_feature_matrix.py, with two differences:

1. News comes from the Alpaca pull via `load_alpaca_ticker_news` instead of
   the FNSPID extract. That is the whole point -- 100% of Alpaca rows carry a
   genuine publication time, against FNSPID's 0.22%, which is what makes
   E_SAMEBAR_TEXT measurable.
2. Prices are read from the append-only store rather than re-fetched from
   yfinance. The price side is identical across corpora and re-fetching would
   risk a different snapshot hash for no reason.

Writes to a SEPARATE feature-matrix path so the committed FNSPID artefacts
stay untouched and the two corpora can be compared.
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
from investify.features.assembly import (  # noqa: E402
    add_backward_only_momentum,
    aggregate_session_sentiment,
    asof_join_features,
)
from investify.features.indicators import compute_indicators  # noqa: E402
from investify.ingest.news import load_alpaca_ticker_news, map_to_sessions  # noqa: E402
from investify.labels import compute_labels  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config', type=Path, default=Path('config/spike.yaml'))
parser.add_argument('--run-directory', required=True, type=Path)
parser.add_argument('--sentiment-cache', required=True, type=Path, help='New score-cache directory on E:/AI-Tools')
args = parser.parse_args()
run_directory = args.run_directory.resolve()
score_cache = args.sentiment_cache.resolve()
if run_directory.exists() or score_cache.exists():
    raise ValueError('Preserve existing feature outputs/cache; choose new run and score-cache directories')
if not run_directory.is_relative_to(Path(__file__).resolve().parents[1] / 'artifacts/scientific_runs'):
    raise ValueError('Feature run must remain under artifacts/scientific_runs')
if not score_cache.is_relative_to(Path('E:/AI-Tools').resolve()):
    raise ValueError('Scoring cache must remain on E:/AI-Tools')
os.environ['HF_HOME'] = str(Path('E:/AI-Tools/Temp/investify-scientific-huggingface').resolve())
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
from investify.features.sentiment import FinBERTScorer  # noqa: E402
t0 = time.time()
cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))
cfg['sentiment']['cache_dir'] = str(score_cache)
run_directory.mkdir(parents=True)
ticker = cfg["tickers"][0]
corpus = cfg["corpora"]["alpaca"]

cal = NYSECalendar()

print(f"=== Reading {ticker} prices from the store ===", flush=True)
prices_path = Path(cfg["paths"]["store"]) / "prices" / f"ticker={ticker}"
if not prices_path.exists():
    raise FileNotFoundError(
        f"price store missing at {prices_path}; run scripts/build_phase1_feature_matrix.py first"
    )
prices_df = pd.read_parquet(prices_path).sort_values("date").reset_index(drop=True)
prices_df["ticker"] = ticker
prices_df = prices_df.drop(columns=["content_hash", "ingest_ts"], errors="ignore")
print(f"{len(prices_df)} price bars", flush=True)

print(f"\n=== Loading Alpaca news for {ticker} ===", flush=True)
news_df = load_alpaca_ticker_news(
    corpus["path"], ticker, start=cfg["date_range"]["start"], end=cfg["date_range"]["end"]
)
n_real_ts = (
    ~(
        (news_df["event_ts"].dt.hour == 0)
        & (news_df["event_ts"].dt.minute == 0)
        & (news_df["event_ts"].dt.second == 0)
    )
).sum()
print(
    f"{len(news_df)} headlines; {n_real_ts} ({100*n_real_ts/len(news_df):.2f}%) carry a "
    f"genuine time of day",
    flush=True,
)
news_df = map_to_sessions(news_df, cal)

print(f"\n=== FinBERT sentiment scoring ({len(news_df)} headlines) ===", flush=True)
scorer = FinBERTScorer(cache_dir=cfg["sentiment"]["cache_dir"])
t_score = time.time()
scored_news = scorer.score(news_df, text_col="headline")
print(f"scoring pass wall-clock: {time.time()-t_score:.1f}s", flush=True)

print("\n=== Aggregating session-level sentiment + momentum ===", flush=True)
session_sentiment = aggregate_session_sentiment(scored_news)
session_sentiment = add_backward_only_momentum(session_sentiment)
print(f"{len(session_sentiment)} (ticker, session) rows with sentiment features", flush=True)

print("\n=== Computing technical indicators ===", flush=True)
indicators = compute_indicators(prices_df)
priced = pd.concat(
    [prices_df.reset_index(drop=True), indicators.reset_index(drop=True)], axis=1
)

print(
    f"\n=== As-of joining (max_lookback={cfg['as_of_join']['max_lookback_days']}d) ===",
    flush=True,
)
joined = asof_join_features(
    priced, session_sentiment, max_lookback_days=cfg["as_of_join"]["max_lookback_days"]
)
n_with = joined["mean_polarity"].notna().sum()
print(
    f"{len(joined)} bars, {n_with} ({100*n_with/len(joined):.1f}%) have sentiment attached "
    f"-- {len(joined)-n_with} bars have none",
    flush=True,
)

print("\n=== Computing labels ===", flush=True)
for horizon in cfg["labels"]["horizons_days"]:
    labels = compute_labels(
        joined[["date", "close"]],
        horizon_days=horizon,
        vol_window_days=cfg["labels"]["volatility_window_days"],
        thresholds=tuple(cfg["labels"]["class_thresholds"]),
    )
    joined[f"label_{horizon}d"] = labels["label"].values
    joined[f"label_score_{horizon}d"] = labels["label_score"].values
    joined[f"label_end_{horizon}d"] = labels['label_end_date'].values
    print(
        f"  horizon={horizon}d: {labels['label'].value_counts(dropna=False).to_dict()}",
        flush=True,
    )

out_path = run_directory / 'feature_matrix_alpaca.parquet'
joined.to_parquet(out_path, index=False)
print(
    f"\n=== DONE in {time.time()-t0:.1f}s. {len(joined)} rows x {len(joined.columns)} cols "
    f"-> {out_path} ===",
    flush=True,
)
