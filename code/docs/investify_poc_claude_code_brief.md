# Investify: proposal-stage proof of concept

You are building a focused technical spike for a final year project proposal defence on **Friday**. It is currently Wednesday evening. Everything below is scoped to that deadline. Read this whole brief before writing any code.

---

## 0. Context you need

**Project.** Investify, a retail equity decision-support system. A user's risk profile plus technical indicators plus news sentiment feed a calibrated XGBoost model, which produces a Buy/Hold/Sell view for a 1-week horizon with a probability. TreeSHAP attributes the decision. A language model renders it in English and a deterministic verifier checks every claim before the user sees it.

**The project claims two contributions.** Neither is the model.

1. A leakage-audited point-in-time evaluation harness. News arrives continuously; price bars arrive on a trading calendar with weekends, holidays and half-days. Aligning the two without look-ahead, and proving that alignment is clean, is the claim.
2. A deterministic verifier for generated explanations. Because the explainer's input is entirely structured and numeric, whether an explanation is grounded is decidable by code rather than by another model's opinion.

**What the university guide requires of this spike.** One focused feasibility proof, testing the assumption that carries the greatest risk, demonstrated live at the defence rather than described. It must answer five questions: what risky assumption was tested, what input and setup was used, what result was obtained, what was learned or disproved, and what it changes in the design or plan. A polished interface that does not test a technical risk is explicitly not sufficient.

**The riskiest assumption, stated precisely.** That asynchronous dated text can be aligned to price bars across a trading calendar with no look-ahead, and, critically, that when leakage is present our test suite detects it. If we cannot detect leakage, every downstream result in the project is worthless, because a leaked pipeline makes a useless model look skilful and nothing in its own output reveals it.

A prior spike by this team covered technical features only, using four arms (clean, shuffled K-fold, no-purge, and one future-peeking feature) across 4 tickers, and found that the clean configuration sat at chance while the leaked arms were detected. **That spike did not involve any text.** Text-to-price alignment is the untested half and is what this spike must now cover.

---

## 1. Environment and hard constraints

- macOS, Apple M1 Pro. **No CUDA.** Use CPU, or `torch` MPS where it helps.
- Python 3.11. Use `uv` if available, otherwise `venv` + `pip`. Pin every dependency in a lock file.
- Internet access is available. If a command is blocked by network policy, stop and say exactly which domain you need.
- Colab free tier exists as a fallback for anything heavy, but **prefer solutions that run entirely on the Mac**, because the panel demo must run on this machine.
- Everything must be re-runnable in front of a panel in under two minutes from cached artefacts, and fully re-runnable from scratch in a documented longer path.

**Honesty rules, non-negotiable.**

- Never fabricate a result. Every number in the report must come from a run that actually happened.
- Never substitute synthetic text for real dated headlines in the headline experiment. Synthetic fixtures are fine and expected for unit tests, and must be clearly labelled as fixtures.
- If something cannot be obtained or does not work, that is a finding to be written up, not a gap to be papered over. The guide explicitly says a spike that disproves an assumption is more valuable than one that confirms it.
- Fail loudly. No silent `except: pass`, no default fallbacks that hide a missing input.

---

## 2. What this spike must prove, and what it must not attempt

**In scope.**

- 3 tickers: AAPL, NVDA, TSLA. Roughly 2018-01-01 to 2023-12-31, bounded by whatever the news corpus actually covers.
- Daily OHLCV, as-traded, with a content hash over the snapshot.
- An append-only store where every row carries both a source event timestamp and an ingestion timestamp.
- Exchange-calendar session mapping with a 16:00 America/New_York cutoff. A headline published at 16:05 belongs to the **next** session, never the one that just closed. Weekends, market holidays and half-days handled explicitly.
- Backward as-of join with an explicit maximum look-back. Never a nearest-in-time join.
- FinBERT (`ProsusAI/finbert`) over headlines only, truncated to 128 tokens, cached by document hash.
- Backward-only technical indicators. Fold-local normalisation.
- Expanding purged walk-forward cross-validation with a 5-day embargo.
- Five experimental arms (section 6) at two horizons, with lift measured against a stratified-random baseline and bootstrap confidence intervals.
- XGBoost 3-class classifier, isotonic calibration, Brier score, TreeSHAP with an additivity assertion.
- A deterministic groundedness verifier scored against a fixture set of deliberately corrupted explanations.
- A two-tab Streamlit demo, if and only if phases 1 to 3 are complete.

**Explicitly out of scope. Do not build these.**

- Social-register sentiment, CryptoBERT, divergence features, the hand-labelled social benchmark.
- Any language model, local or hosted. The explanation layer in this spike is a deterministic template only.
- QLoRA, distillation, constrained decoding.
- Optuna or any hyperparameter search. Use one fixed, documented XGBoost configuration everywhere.
- Docker, cloud deployment, FastAPI, schedulers, nightly jobs.
- The 1-month horizon, portfolio logic, position sizing, trading-strategy metrics such as Sharpe or drawdown.
- Live news feeds. This spike is historical only.

**Optional stretch, only if everything else is done and tested.** Add BTC-USD daily bars on a continuous 24-hour calendar behind the same calendar interface, and run the clean arm on it, to evidence that the calendar layer is a genuine abstraction rather than NYSE assumptions in disguise. This is worth about an hour. Do not start it before phase 4 is finished.

---

## 3. Repository layout

```
investify-poc/
  pyproject.toml / requirements.txt + lock
  README.md
  Makefile                     # make setup / data / features / spike / test / app
  config/
    spike.yaml                 # tickers, dates, seeds, thresholds, paths
  src/investify/
    calendars.py               # SessionCalendar interface; NYSE impl; Continuous24h impl
    ingest/
      prices.py                # yfinance -> parquet, content-hashed snapshot
      news.py                  # corpus adapter -> parquet, dual timestamps
    store.py                   # append-only parquet + duckdb views; hash dedup
    features/
      indicators.py            # backward-only technicals
      sentiment.py             # FinBERT scoring + hash cache
      assembly.py              # as-of join, aggregation, fold-local scaling
    labels.py                  # volatility-adjusted forward returns -> 3 classes
    splits.py                  # expanding purged walk-forward + embargo; shuffled KFold
    engine.py                  # XGBoost, isotonic calibration, TreeSHAP
    harness/
      arms.py                  # the five configurations
      metrics.py               # macro-F1, lift, bootstrap CI, Brier
      run_spike.py             # entrypoint -> results.json + results.csv + chart
    explain/
      template.py              # deterministic explanation from a decision record
      verifier.py              # the six checks, claim-level scoring
      fixtures.py              # corrupted-explanation generator
  tests/
    test_calendar.py
    test_asof_join.py
    test_backward_only.py
    test_fold_local_scaling.py
    test_store_append_only.py
    test_shap_additivity.py
    test_verifier.py
    test_leak_canary.py
  artifacts/                   # committed: results.json, results.csv, figures, hashes
  app/streamlit_app.py
  POC_REPORT.md
```

Use `git`. Commit at the end of each phase with a message naming the phase.

---

## 4. Phase 0: corpus acquisition probe. STOP AND REPORT.

**This is the highest-risk unknown and must be resolved first. Timebox: 2 hours.**

The intended historical news source is **FNSPID** (Dong et al., 2024), article-level financial news with publication timestamps and explicit ticker tags, covering to 2023, on Hugging Face. The full corpus is large and must not be downloaded in its entirety.

Do this:

1. Use the Hugging Face Hub API to **list the files** in the FNSPID dataset repository without downloading them. Report file names and sizes.
2. Identify the smallest file that contains, at minimum: a ticker or symbol column, a publication timestamp, and a headline or title. Report the exact column names and dtypes from a small sample.
3. **Determine whether the publication timestamp carries a time of day or only a calendar date.** This is the single most important fact in the whole spike. The 16:00 ET cutoff rule and the same-bar leak arm are only meaningfully testable if there is a time of day. Report what you find, with evidence.
4. Pull only the rows for AAPL, NVDA and TSLA, using streaming or chunked reads so the full file is never held in memory. Report row counts per ticker per year and the date range actually covered.

**Then stop and write a short report before building anything else**, covering: source chosen, size pulled, timestamp granularity, per-ticker coverage, and any licensing note. Wait for the user to confirm before proceeding.

If FNSPID proves unworkable within the timebox, report that as a data-availability finding and present the alternatives you found, with the same four facts for each. Do not silently switch sources and do not generate synthetic headlines for the main experiment.

Store the result as `artifacts/corpus_manifest.json` recording source, file, SHA-256, row count, date range and retrieval timestamp.

---

## 5. Phase 1: store, calendar, alignment

**Store.** Parquet partitioned by asset and date, queried through DuckDB. Every row carries `event_ts` (when the thing happened in the world) and `ingest_ts` (when we wrote it). Writes are idempotent, keyed by SHA-256 content hash. **There is no update path**, and a test asserts this. Replaying an ingest must produce zero duplicate rows.

**Prices.** yfinance daily bars, as-traded. Hash the snapshot and record it. Validate every bar against real exchange sessions and assert zero orphan bars.

**Calendar.** Define a `SessionCalendar` interface with two methods: `session_for(timestamp)` and `next_session(timestamp)`. Implement `NYSECalendar` using `pandas_market_calendars` or `exchange_calendars`, and leave a stub for `Continuous24hCalendar`. The mapping rule is: a text record with `event_ts` at or after 16:00 America/New_York maps to the **next** tradable session. Before the close, it maps to the current session. Use a real timezone database, never fixed UTC offsets, because the same UTC instant falls before the bell in winter and after it in summer.

`tests/test_calendar.py` must cover, at minimum: a Friday 16:05 timestamp mapping to Monday, a timestamp on a market holiday mapping to the next open session, a half-day session (use a real historical one such as the day after Thanksgiving), a timestamp at exactly 16:00:00, and one winter and one summer timestamp at the same UTC hour that map to different sides of the close.

**As-of join.** Join text-derived features to price bars with a backward as-of join and an explicit maximum look-back. `tests/test_asof_join.py` asserts that every joined text `event_ts` is strictly earlier than the open of the session it is attached to.

**Indicators.** RSI(14), MACD histogram, distance from SMA-200, Bollinger position, OBV slope. Every window backward-only. `tests/test_backward_only.py` proves this directly: perturb a value at index `t` and assert that no feature at any index `< t` changes.

**Sentiment.** FinBERT over headlines, 128-token truncation, batched. Cache scored results keyed by document hash so a re-run is near-instant. Aggregate per ticker per session into mean polarity, 3-day momentum, 7-day momentum, mention volume z-score and dispersion. Compute rolling statistics backward-only. Report wall-clock for the scoring pass.

**Labels.** Forward return over the horizon, divided by 20-day trailing realised volatility, mapped to three classes at fixed thresholds of plus and minus 0.5. Thresholds are constants, not fitted, and this must be stated in the report. The label at time `t` must be knowable only strictly after `t + horizon`, asserted by test.

**Scaling.** All normalisation statistics fitted inside the training fold only. `tests/test_fold_local_scaling.py` asserts scaler parameters differ across folds and are never derived from test rows.

---

## 6. Phase 2: the harness and the five arms

Everything is held constant across arms except temporal discipline: same features, same model configuration, same seed (42), same folds where applicable.

| Arm | What it changes | What it is for |
|---|---|---|
| `A_CLEAN` | Nothing. Correct throughout. | Must sit at chance. Makes any later positive result interpretable. |
| `B_SHUFFLED` | Shuffled K-fold instead of expanding walk-forward. | Overlapping-label leak. Expected to be invisible at 1 day and visible at 5 days. |
| `C_NOPURGE` | Purge and embargo removed, walk-forward retained. | Tests whether purging is doing the work people assume. |
| `D_CENTRED` | One technical feature computed with a centred rather than trailing window. | Feature-level look-ahead. Should leak loudly. This is the permanent leak canary. |
| `E_SAMEBAR_TEXT` | Text mapped to the **same** session it was published in, rather than the next, and after-close items joined to the just-closed bar. | **The new arm and the point of this spike.** This is the mistake published pipelines make when they align by calendar date. Its magnitude is genuinely unknown. |

Run every arm at horizons of 1 day and 5 days (1 week). Six expanding walk-forward folds, 5-day embargo, seed 42.

**Metrics.** Macro-F1 per fold, mean and standard deviation. A stratified-random baseline drawn from the **training-fold** class distribution. Lift is macro-F1 minus baseline. Bootstrap confidence interval on lift, 10,000 resamples. **Pass condition for a control: absolute lift at most 0.03 with a CI overlapping zero.**

**Outputs.** `artifacts/results.json` and `results.csv` with one row per arm per horizon carrying macro-F1, SD, chance, lift, CI bounds and verdict. A grouped bar chart with the 0.03 threshold drawn as a line. Record seed, snapshot hashes, corpus manifest hash, package versions and git commit alongside the results.

**`tests/test_leak_canary.py` is the crux.** It must assert both directions: that `A_CLEAN` does **not** breach the threshold, and that `D_CENTRED` **does**. A detector that has stopped detecting is worse than no detector, so the build fails if the canary goes quiet.

Do not tune anything to produce a nice-looking result. If `A_CLEAN` shows signal, that is a leakage alarm in our own pipeline and must be investigated and reported, not smoothed over.

---

## 7. Phase 3: engine, attribution and verifier

**Engine.** One fixed XGBoost configuration, `hist` tree method, class weights for imbalance, macro-F1 reported. Isotonic calibration on a held-out fold. Report Brier score and produce a reliability curve. Also implement the transparent linear baseline `C = R*S + (1-R)*T` mapped to three classes, as the comparator.

**Attribution.** TreeSHAP, path-dependent, no interaction values. `tests/test_shap_additivity.py` asserts contributions plus base value equal the model output within tolerance, for every emitted decision.

**Decision record.** A single frozen schema carrying: ticker, session date, decision, calibrated class probabilities, the full feature vector, the SHAP vector, base value, top-k ranked contributors, risk tier, model version, data hashes and timestamps. Everything downstream reads only this record.

**Template explainer.** Deterministic English generated from the decision record. Grounded by construction. No model.

**Verifier.** Six checks, per the project design:

1. Numeric extraction from a structured JSON payload where present, with pattern matching over free prose as fallback.
2. Tolerance matching: probabilities within 0.5 percentage points, SHAP values within a fixed epsilon.
3. Sign and direction: if the text claims a feature pushed towards a class, that feature's contribution for that class must actually be positive.
4. Rank consistency: cited features must come from the top-k contributor set, and a minor contributor must not be promoted to a headline cause.
5. Closed-vocabulary validation: every feature name mentioned must exist in the known feature set.
6. Claim-level scoring: decompose into atomic claims, each verifiable-correct, verifiable-incorrect, or unverifiable.

Report numeric fidelity, directional consistency, claim recall and unverifiable-claim rate. Thresholds for a pass are 0.98, 0.95, 0.80 and 0.15 respectively. Report all four, never the headline score alone, because a model that speaks vaguely enough to make every claim unverifiable scores a perfect groundedness while saying nothing.

**Fixtures are how the verifier is evidenced.** `explain/fixtures.py` takes a correct template explanation and produces a corrupted variant for each error class: a wrong probability, a wrong SHAP magnitude, a flipped direction, a promoted minor feature, an invented feature name, and a vague unverifiable sentence. `tests/test_verifier.py` asserts the verifier catches every corruption and passes the clean original. Report a confusion matrix over roughly 100 generated fixtures. **This is stronger evidence than a language model would give, and say so in the report.**

Any explanation failing verification is replaced by the deterministic template, so an unverified explanation is never emitted.

---

## 8. Phase 4: the demo. Only after phases 1 to 3 pass.

A Streamlit app, two tabs, running from cached artefacts in under two minutes.

**Tab 1, Leakage Lab.** The arms table, the bar chart with the threshold line, and a button that re-runs one arm live so the panel watches the leak appear rather than reading about it. Show the snapshot hash and seed on screen.

**Tab 2, Decision.** A short risk quiz (a few capacity questions plus a Grable-Lytton subset), reconciled by taking the more restrictive of capacity and tolerance into a three-tier profile. Then a ticker and date picker, showing the decision, calibrated probability, a SHAP contribution bar chart, the template explanation, and the per-claim verifier report as a table. Include a "corrupt this explanation" control that injects an error and shows the verifier rejecting it and the template taking over.

Every screen carries the non-advice notice and the horizon.

---

## 9. POC_REPORT.md

Write this last, from the actual results. Structure it around the five questions the guide requires:

1. What risky assumption was tested.
2. What input and setup was used. Exact tickers, date range, row counts, corpus source and hash, feature list, model configuration, folds, embargo, seed.
3. What result was obtained. The arms table and the chart. The verifier confusion matrix.
4. What was learned or disproved. Write the honest reading, including anything that contradicts the team's prior assumptions. If `E_SAMEBAR_TEXT` leaks, quantify by how much and say that this is the exact mistake the closest published work makes. If it does not leak, say so plainly and reason about why.
5. What it changes in the design or plan. Concrete amendments to gate criteria, controls or requirements.

Add a section titled **"What this spike does not establish"**, listing at minimum: social-register sentiment and divergence features are untested; only 3 tickers and one market; no language model was involved, so the verifier is evidenced against fixtures rather than live generations; the crypto calendar path is unexercised unless the stretch goal was completed.

Also produce `artifacts/slide_content.md`: the content for a single defence slide, being the arms table, the chart reference, one sentence on what was disproved, and one sentence on what changed.

---

## 10. Sequencing and reporting

Work in this order and **report at each boundary before continuing**:

- **Phase 0** by Thursday morning. Stop for confirmation.
- **Phases 1 and 2** by Thursday evening. This alone is a defensible POC. If time runs out here, stop and write the report.
- **Phase 3** by Friday morning.
- **Phase 4** only if phase 3 is green.
- Report written from real results, whatever they are.

If you are running short, cut phase 4 first, then phase 3's Streamlit-facing parts, never the leakage harness or its tests. The harness and its canary are the proof of concept. Everything else is presentation.

At every stopping point, tell the user plainly what works, what does not, and what you had to change. Do not present a partially working system as complete.
