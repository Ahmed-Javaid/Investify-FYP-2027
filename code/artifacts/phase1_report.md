# Phase 1 report: store, calendar, alignment, features, labels

**Status: complete. All 29 unit tests pass. Real end-to-end pipeline run on NVDA, 2018-01-01 to 2023-12-31.**

## What was built

| Module | What it does |
|---|---|
| `calendars.py` | `SessionCalendar` interface, `NYSECalendar` (fixed 16:00 ET cutoff, real tz-aware conversion), `Continuous24hCalendar` stub |
| `store.py` | Append-only Parquet + DuckDB, SHA-256 content-hash dedup, no update path |
| `ingest/prices.py` | yfinance daily bars, content-hashed snapshot, validated against real NYSE sessions |
| `ingest/news.py` | Loads the Phase 0 NVDA extract, maps each headline to its session |
| `features/indicators.py` | RSI(14), MACD histogram, distance from SMA-200, Bollinger position, OBV slope — all backward-only |
| `features/sentiment.py` | FinBERT scoring, 128-token truncation, batched, cached by document hash |
| `features/assembly.py` | Backward as-of join (per ticker, max look-back, same-session excluded) attaching prior-session sentiment to each price bar |
| `labels.py` | Volatility-adjusted forward-return labels, fixed thresholds |
| `scaling.py` | Fold-local `StandardScaler` fitting |

## Test coverage (29/29 passing)

- `test_calendar.py` (7): Friday→Monday, holiday→next session, half-day uses the fixed cutoff not the actual early close, exact 16:00:00 boundary, winter/summer DST divergence at the same UTC hour, naive-timestamp rejection.
- `test_store_append_only.py` (6): idempotent replay, partial overlap, no update path even when non-hashed fields differ, `event_ts` required, `ingest_ts` recorded separately.
- `test_backward_only.py` (5): perturbing `close[t]` never changes any indicator at an index `< t`.
- `test_asof_join.py` (4): joined `event_ts` is strictly before the session's open, same-session text never joins its own bar, max look-back respected, backward (not nearest-in-time) confirmed.
- `test_labels.py` (4): label depends on `close[t+horizon]`, not on anything beyond it or strictly before the vol window; thresholds are fixed constants.
- `test_fold_local_scaling.py` (3): scaler parameters differ across differently-distributed folds; never derived from held-out rows.

## Real pipeline run (not a fixture — actual NVDA data)

- **Prices**: 1,509 daily bars, 2018-01-02 → 2023-12-29. Snapshot hashed. Zero orphan bars against the real NYSE calendar.
- **News**: 11,708 NVDA headlines loaded from the Phase 0 extract, every one mapped to a session.
- **Sentiment**: FinBERT scored 10,923 headlines fresh, 785 from cache, in 35.3s (309 docs/sec on MPS).
- **As-of join**: 1,206 of 1,509 bars (79.9%) got sentiment attached within the 7-day look-back; 303 bars (20.1%) had none.
- **Labels**: 1-day horizon — Hold 603, Buy 495, Sell 390 (21 NaN, tail/warmup). 5-day horizon — Buy 714, Sell 486, Hold 284 (25 NaN).

**Sanity checks performed, not just assumed:**
- Every indicator's NaN count matches its warmup window exactly (RSI: 14, SMA-200 distance: 199, Bollinger: 19, OBV slope: 14).
- RSI stays in [8, 97] — sane range. Bollinger %B occasionally exceeds [0,1] during breakouts, which is correct behaviour for that indicator, not a bug.
- **The 303 no-sentiment bars cluster in March 2021** — directly matching Phase 0's finding that NVDA's news coverage, while "continuous" year-to-year, has a real sparse patch in 2021 (702 rows that year vs. 2,332 in 2022 and 5,537 in 2023). This is the same gap showing up downstream, not a new bug.

## What this means for Phase 2

The feature matrix (`data/store/feature_matrix.parquet`, gitignored — reproducible via `scripts/build_phase1_feature_matrix.py`) is ready for the five-arm leakage harness. The ~20% no-sentiment-attached rows and the thin real-timestamp count from Phase 0 (§3, §7) both bear on how much weight the `E_SAMEBAR_TEXT` arm's result can carry — flagged again here so it isn't lost between phases.
