# Scientific source corrections and evidence boundary

## Fresh scientific execution - 12 October 2026

The new **Alpaca revision-conservative experiment has completed and passed actual
model/calibration/native-TreeSHAP replay**. It consumed 1,509 complete NYSE price
sessions and 6,768 news rows, with 5,748 distinct headlines scored offline by the
pinned original ProsusAI/finbert checkpoint. The recovery doctor had zero blockers
and all three scientific commands completed.

Six arms at both horizons ran on shared row sets: 1,309 rows at one day and
1,305 at five days, six folds each. Clean five-day macro-F1 is **0.2843** against
the training-distribution random baseline **0.3287** (lift -0.0444).
The deliberately centred Bollinger canary has five-day lift **+0.2104**,
95% fold-bootstrap CI **[+0.1698, +0.2421]**. E_SAMEBAR_TEXT remains a lag ablation.

Both current calibration modes still emit **186 Buy decisions**. Raw frozen-mode
predictions are Buy 40 / Hold 51 / Sell 95; learned isotonic maps make Buy highest
on every evaluation row. Frozen Brier improves **0.7929 to 0.6105**; refit-transfer
improves **0.7760 to 0.6078**. Better Brier does not resolve decision collapse or
establish useful prediction. Five unavailable calibration labels were excluded;
181 rows calibrate, and evaluation runs 29 March to 21 December 2023.

Actual retained-model inference reproduces margins/probabilities exactly; native
TreeSHAP agrees with every exported contribution/bias, with maximum frozen
additivity residual about 1.02e-6. All 372 **new** guided explanations validate,
separately from the 372 preserved historical records. New engineering checks:
179 passed / six legacy-input skips, plus eight admission-refusal passes.

This is a fresh SIP split-adjusted snapshot using max(created_at, updated_at)
for news availability, not the original September data or exact uv.lock.
Historical vintage is not proven; all original records, freezes and ZIPs remain
separate. No FNSPID was requested.

[Reviewed summary](../evidence/fresh_alpaca_science_summary_20261012_run01.json) and [actual replay](../evidence/fresh_alpaca_science_replay_20261012_run01.json).

Readiness is now **78.5%, approximately 79%**, with unchanged weights and other
areas: science alone rises from 60% to 85%. Remaining substantive gaps are the
social comparison, rendered institutional report/deck, and genuine team review,
contribution/rehearsal and repository evidence. The 90% target is not achieved.

## Post-recovery verification

After the former native task's context-window failure, separate implementation owners completed trace/export binding, strict V4 original-file/class/loading/receipt checks and portable request ownership. [The matching selected receipt](../evidence/recovery_selected_tests_20261012.xml) has **212 passes, twenty Streamlit cases, no skips**. [The core receipt](../evidence/recovery_core_tests_20261012.xml) has **153 passes and three shuffled cases deselected** in the Python 3.11 viewer. These scopes overlap and are not summed as full scientific acceptance.

Existing read-only E: packages support actual SciPy/sklearn imports through the existing CPython 3.13 base. [Three unchanged shuffled-split function bodies](../evidence/recovery_shuffled_split_checks_20261012.json) pass with real sklearn, using synthetic dates/indices and direct execution rather than pytest. [The actual isotonic backend fixture](../evidence/recovery_isotonic_backend_20261012.json) fits three mappings on disclosed float32 numeric fixtures and replays the current trace; maximum interpolation difference is approximately `4.88e-8`, within the explicit `1e-6` tolerance. No classifier fit/inference, original market run or Python 3.11 scientific-lock restoration is implied. XGBoost, SHAP, real NYSE loading and genuine market inputs remain unavailable.

The recovery runner now retains a receipt before and after each step, explicit launch/timeout failures and partial logs; seven orchestration checks pass. The fresh FNSPID doctor still reports eighteen prerequisite/input blockers and **zero commands executed**. Current full traces bind exact bytes to run identity/records/Brier and validate score/scaler/class/date consistency. They explicitly report `model_inference_replayed=false`; numeric replay does not establish that a retained classifier generated the scores. Original weights/config/tokenizer metadata and actual paired sentiment outputs remain absent; the V4 catalog stays `metadata_incomplete`.

The continuation repairs temporal and ingestion contracts in the isolated working code. **Historical market/model results have not been rerun.** The old scientific implementation is preserved under [the source snapshot](../sources/historical_science_20261012/) and its verified hash manifest. Existing records, teacher/source/AI freezes and earlier archives remain unchanged. These corrections are not an explanation of the all-Buy result or evidence of improved prediction.

| Correction | Current source / actual evidence | Limit |
| --- | --- | --- |
| Trading-row labels versus calendar-day purge | `labels.py` retains the full-price endpoint; arm/engine folds carry it through the shared mask. `observed-label-end-purge-v2` requires training endpoints strictly before the test session. Preserved versus corrected functions have 18 versus zero overlapping endpoints on the same business-day fixture/test blocks. | Fixture proves the mismatch; historical overlap extent and metric effects remain unmeasured. |
| Calibration outcome availability | `calibration_split.py` excludes outcomes ending on/after the first evaluation session. Five of twenty fixture candidates are removed; a first-evaluation-price shock leaves retained inputs unchanged. | No actual calibrator/model fit is implied. |
| Frozen versus refitted classifier | Explicit `frozen_classifier` reuses the same classifier and scaler; `refit_transfer` is a labelled comparator with corrected boundaries. Five mocked orchestration checks trace masks/endpoints/model objects and reject identity mutation. | Actual trained-model comparison needs genuine inputs and supported runtime. This comparator does not overwrite the preserved historical baseline. |
| As-of key resolution | `assembly.py` normalizes both session keys to nanoseconds and rejects missing/intraday/timezone session keys. Production-shaped DatetimeIndex bars now join Python-date news aggregation keys under Pandas 3. | Date/session contracts are not real exchange-calendar loading. |
| News lag interpretation | Actual mapping-plus-join fixtures retain publication-before-bar timing in both rules. E_SAMEBAR_TEXT changes lag under the strict-prior join. | It is a lag-rule ablation, not a proved publication-leak canary. Centred-feature mutations remain separate deliberate leaks. |
| RSI edge cases | Completed rising/falling windows give 100/0; flat completed windows use the explicit project midpoint 50. Fourteen-change warm-up remains missing. | This is an implementation policy, not a new profitable trading rule. |
| Cached-news integrity | `news_cache.py` checks unique SHA256 document keys, finite normalized probabilities, consistent polarity and many-to-one cardinality. Missing scores refuse execution. | It does not authenticate the original FinBERT checkpoint or sentiment accuracy. |
| Input/time/snapshot identity | Explicit UTC-offset news times, date-range audits, ticker/price-value checks, duplicate-revision and orphan/missing-session refusal. New price identity includes OHLCV. | A vendor snapshot is not automatically as-traded or a full corporate-action audit. |
| Append-only storage | V2 canonical typed JSON hashes, batch deduplication, immutable prior Parquet bytes, explicit audits, timezone-aware events and contract markers. Historical unversioned tables are read unchanged; append requires explicit legacy mode. | Serial fixture tests do not establish concurrent multiwriter idempotence. Legacy delimiter hashing retains its disclosed limits. |
| Run provenance and trace | Source/config/runtime/input byte identity before/after; normalized manifest-path lookup and external-copy byte checks. Future sidecars retain all class scores/margins/truth, isotonic knots, scaler statistics and model JSON bytes/hashes with Brier replay. | Hash/trace consistency does not independently attest that inference occurred. Missing original raw subsets remain declared-only, not verified lineage. |

[The 108-pass scoped core receipt](../evidence/background_core_contract_tests_20261012.xml) explicitly excludes three shuffled-KFold tests needing sklearn. [The 186-pass selected receipt](../evidence/background_consolidated_tests_20261012.xml) includes twenty Streamlit cases and excludes scientific reproduction. Additional later targeted receipts cover trace, original-byte gates and runtime recovery; do not sum overlapping receipts as a full-suite result. Six original CSV-dependent loader cases were skipped and remain open.

## Reproduction and recovery

`scripts/prepare_scientific_recovery.py` prepares absolute input configuration and new result directories under `code/artifacts/scientific_runs`. `--corpus fnspid` or `--corpus alpaca` lets an available corpus advance independently. `--execute` refuses missing input/package prerequisites, uses offline/process-local E: caches, retains command logs/failures and prepares both calibration modes. The first doctor receipt was blocked with 29 listed issues and zero commands executed; it is a dated earlier snapshot, not current eligibility after source edits.

Feature builders require new run and score-cache directories, retain actual endpoints and refuse overwriting historical outputs. Model/harness results likewise use new directories. An exact Python 3.11 scientific lock, genuine price/news store and original scores/cache remain missing. The recovered Python 3.13 CPU classifier imports are a separate environment and do not close this pipeline gap.

When genuine inputs are restored, preserve the historical source/data and compare the corrected modes on matching chronological evaluation identities. Retain failures and unfavourable results, full arrays, class distributions, Brier, macro-F1, scaler/model/input identities and calibration knots. Do not tune held-out thresholds to manufacture varied decisions. Review original price adjustment/timestamp limitations before claiming point-in-time market validity.
