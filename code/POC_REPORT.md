# Investify — proposal-stage proof of concept

**F26-003-QuantamentalAI** · FAST NUCES · Report written 2026-09-10

Every number in this report comes from a run that actually happened. The
commands that reproduce each one are given in §7. Where a result is
unflattering — and several are — it is reported as it came out.

---

## 1. What risky assumption was tested

The project claims two contributions, neither of which is the model:

1. **A leakage-audited point-in-time evaluation harness.** News arrives
   continuously; price bars arrive on a trading calendar with weekends,
   holidays and half-days. Aligning the two without look-ahead, and *proving*
   that alignment is clean, is the claim.
2. **A deterministic verifier for generated explanations.** Because the
   explainer's input is entirely structured and numeric, whether an
   explanation is grounded is decidable by code rather than by another model's
   opinion.

The riskiest assumption, stated precisely:

> That asynchronous dated text can be aligned to price bars across a trading
> calendar with no look-ahead, and — critically — that **when leakage is
> present, our test suite detects it.**

If leakage cannot be detected, every downstream result in the project is
worthless, because a leaked pipeline makes a useless model look skilful and
nothing in its own output reveals it.

A prior spike by this team covered technical features only, across four arms
and four tickers, and found the clean configuration at chance while leaked
arms were detected. **That spike involved no text at all.** Text-to-price
alignment was the untested half, and is what this spike covers.

---

## 2. What input and setup was used

**Scope narrowed from the brief, and why.** The brief specified AAPL, NVDA and
TSLA. A full coverage scan of both FNSPID files found AAPL and TSLA each
missing 2021 entirely, and AAPL additionally missing 2018-2019. **NVDA is the
only ticker with continuous 2018-2023 coverage, so the spike is NVDA-only.**
This narrows the demonstration universe; it does not affect either contribution
claim. Recorded in `artifacts/phase0_report.md` §7.

| | |
| --- | --- |
| Ticker | NVDA only |
| Date range | 2018-01-01 to 2023-12-31 |
| Price bars | 1,509 daily OHLCV, as-traded, content-hashed, zero orphan bars |
| Usable rows | 1,309 at the 1-day horizon, 1,305 at 5-day |
| Features | 5 technical (RSI-14, MACD histogram, distance from SMA-200, Bollinger position, OBV slope) + 6 sentiment (mean polarity, mention volume, 3-day and 7-day momentum, volume z-score, dispersion) |
| Sentiment model | FinBERT (`ProsusAI/finbert`), headlines only, 128-token truncation, cached by SHA-256 of the text |
| Labels | Forward return ÷ 20-day trailing realised volatility, mapped to Buy/Hold/Sell at fixed thresholds of ±0.5. **Thresholds are constants, not fitted.** |
| Model | One fixed XGBoost configuration everywhere (`hist`, 300 trees, depth 4, lr 0.05, balanced class weights). No Optuna, no hyperparameter search. |
| Folds | 6 expanding purged walk-forward, 5-day embargo |
| Seed | 42 |
| Leak threshold | absolute lift ≤ 0.03 with a bootstrap CI overlapping zero |

**Two news corpora**, reported side by side:

| | FNSPID | Alpaca / Benzinga |
| --- | --- | --- |
| NVDA headlines 2018-2023 | 11,708 | 6,767 |
| Carrying a genuine time of day | **26 (0.22%)** | **6,767 (100%)** |
| Rows disagreeing between same-bar and next-session mapping | **1** | **749 (11.1%)** |
| Price bars with sentiment attached | 1,206 of 1,509 | 1,494 of 1,509 |

The second corpus was added mid-spike, under change control (§6), because the
first could not answer the spike's central question. Neither replaces the
other.

**Held constant across every arm**: identical feature list, identical model
configuration, identical seed, and an identical **row set** pinned to the clean
arm. Bars with missing sentiment are kept, with NaNs passed to XGBoost's native
missing-value handling. Dropping them would have given the text-remapping arm a
different sample than the control, quietly invalidating the comparison.

---

## 3. What result was obtained

### 3.1 The arms

Lift = macro-F1 − a stratified-random baseline drawn from the **training**
fold's class distribution. Verdicts are three-way: `PASS`, `LEAK` (positive
lift — evidence of look-ahead), `BELOW_CHANCE` (negative lift — no signal, not
leakage).

**FNSPID** (`artifacts/results.csv`, chart `arms_lift.png`)

| Arm | H | Macro-F1 | Chance | Lift | 95% CI | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| A_CLEAN | 1d | 0.3072 ± 0.0457 | 0.3314 | −0.0242 | [−0.0589, +0.0073] | PASS |
| B_SHUFFLED | 1d | 0.3597 ± 0.0190 | 0.3317 | +0.0280 | [+0.0128, +0.0418] | LEAK |
| C_NOPURGE | 1d | 0.3052 ± 0.0480 | 0.3314 | −0.0261 | [−0.0649, +0.0044] | PASS |
| **D_CENTRED** | 1d | 0.3892 ± 0.0632 | 0.3314 | **+0.0578** | [+0.0057, +0.1019] | **LEAK** |
| D_CENTRED_SMA200 | 1d | 0.3132 ± 0.0446 | 0.3314 | −0.0182 | [−0.0491, +0.0148] | PASS |
| E_SAMEBAR_TEXT | 1d | 0.3228 ± 0.0422 | 0.3314 | −0.0086 | [−0.0397, +0.0213] | PASS |
| A_CLEAN | 5d | 0.2604 ± 0.0422 | 0.3288 | −0.0684 | [−0.0967, −0.0354] | BELOW_CHANCE |
| B_SHUFFLED | 5d | 0.4557 ± 0.0188 | 0.3314 | +0.1242 | [+0.1097, +0.1375] | LEAK |
| C_NOPURGE | 5d | 0.2680 ± 0.0341 | 0.3289 | −0.0609 | [−0.0826, −0.0344] | BELOW_CHANCE |
| **D_CENTRED** | 5d | 0.5115 ± 0.0562 | 0.3288 | **+0.1827** | [+0.1456, +0.2263] | **LEAK** |
| D_CENTRED_SMA200 | 5d | 0.3078 ± 0.0267 | 0.3288 | −0.0209 | [−0.0419, +0.0001] | PASS |
| E_SAMEBAR_TEXT | 5d | 0.2904 ± 0.0501 | 0.3288 | −0.0383 | [−0.0762, −0.0044] | BELOW_CHANCE |

**Alpaca / Benzinga** (`artifacts/results_alpaca.csv`, chart `arms_lift_alpaca.png`)

| Arm | H | Macro-F1 | Chance | Lift | 95% CI | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| A_CLEAN | 1d | 0.3078 ± 0.0410 | 0.3314 | −0.0236 | [−0.0568, +0.0007] | PASS |
| B_SHUFFLED | 1d | 0.3395 ± 0.0173 | 0.3317 | +0.0078 | [−0.0034, +0.0195] | PASS |
| C_NOPURGE | 1d | 0.3153 ± 0.0366 | 0.3314 | −0.0160 | [−0.0428, +0.0101] | PASS |
| **D_CENTRED** | 1d | 0.3844 ± 0.0358 | 0.3314 | **+0.0530** | [+0.0244, +0.0758] | **LEAK** |
| D_CENTRED_SMA200 | 1d | 0.3315 ± 0.0290 | 0.3314 | +0.0001 | [−0.0209, +0.0218] | PASS |
| E_SAMEBAR_TEXT | 1d | 0.3233 ± 0.0537 | 0.3314 | −0.0081 | [−0.0478, +0.0288] | PASS |
| A_CLEAN | 5d | 0.2792 ± 0.0432 | 0.3288 | −0.0495 | [−0.0796, −0.0163] | BELOW_CHANCE |
| B_SHUFFLED | 5d | 0.4418 ± 0.0224 | 0.3314 | +0.1104 | [+0.0927, +0.1262] | LEAK |
| C_NOPURGE | 5d | 0.2792 ± 0.0458 | 0.3289 | −0.0497 | [−0.0790, −0.0145] | BELOW_CHANCE |
| **D_CENTRED** | 5d | 0.5481 ± 0.0310 | 0.3288 | **+0.2194** | [+0.1983, +0.2393] | **LEAK** |
| D_CENTRED_SMA200 | 5d | 0.3116 ± 0.0408 | 0.3288 | −0.0171 | [−0.0462, +0.0134] | PASS |
| E_SAMEBAR_TEXT | 5d | 0.2742 ± 0.0309 | 0.3288 | −0.0546 | [−0.0757, −0.0329] | BELOW_CHANCE |

### 3.2 The verifier

112 fixtures — 8 records × 2 payload modes × (clean + 6 corruption classes).
`artifacts/verifier_confusion_matrix.json`.

| | Predicted corrupt | Predicted clean |
| --- | --- | --- |
| **Actually corrupt** | 80 | 16 |
| **Actually clean** | **0** | 16 |

| Corruption class | Detection rate |
| --- | --- |
| wrong_probability | 1.000 |
| wrong_shap_magnitude | 1.000 |
| flipped_direction | 1.000 |
| promoted_minor_feature | 1.000 |
| invented_feature_name | 1.000 |
| vague_unverifiable | **0.000** |
| clean (correctly passed) | 1.000 |

On clean explanations: numeric fidelity 1.000, directional consistency 1.000,
claim recall 1.000, unverifiable rate 0.000 — against pass conditions of ≥0.98,
≥0.95, ≥0.80 and ≤0.15.

### 3.3 The engine

| Metric | Corpus | Model | Linear baseline `C = R·S + (1−R)·T` |
| --- | --- | --- | --- |
| CV macro-F1 (6 folds) | FNSPID | 0.2604 ± 0.0422 | **0.2962 ± 0.0919** |
| CV macro-F1 (6 folds) | Alpaca | 0.2792 ± 0.0432 | **0.2815 ± 0.0595** |
| Eval-fold macro-F1 (n=186) | FNSPID | **0.2238** | 0.1495 |
| Eval-fold macro-F1 (n=186) | Alpaca | **0.2238** | 0.1851 |
| Brier before → after calibration | FNSPID | 0.8191 → 0.6119 | — |
| Brier before → after calibration | Alpaca | 0.8124 → 0.6111 | — |

TreeSHAP additivity holds to a maximum residual of **1.9e-7** across all 186
emitted decision records.

The linear baseline beats the model on CV mean under **both** corpora, though
the gap narrows sharply on Alpaca (0.0023 against FNSPID's 0.0358).

---

## 4. What was learned or disproved

### 4.1 The detector detects — this is the spike's core positive result

`D_CENTRED`, a feature with a deliberately centred (future-peeking) window,
breaches the threshold loudly on both corpora: **+0.183 on FNSPID, +0.219 on
Alpaca**, six to seven times the 0.03 threshold, with confidence intervals far
clear of zero. `tests/test_leak_canary.py` re-runs this arm for real and fails
the build if it ever goes quiet.

A **positive control** rules out the reverse error. An oracle feature — the
label score itself — injected into the clean pipeline scores macro-F1 0.9925,
lift **+0.664**. The harness converts real signal into detected lift. So when
an arm shows no lift, that is a statement about the arm, not a broken detector.

### 4.2 The spike's central arm: a null result, and the difference between two kinds of nothing

`E_SAMEBAR_TEXT` — mapping text to the session it published in rather than the
next — is the arm the brief calls "the point of this spike", and its magnitude
was described as genuinely unknown.

**On FNSPID the arm was not measurable.** 26 of 11,708 headlines carry a real
time of day, and exactly one maps differently under the two rules. The correct
statement there is not "the leak is small" — it is that the corpus lacks the
resolution to answer.

**On Alpaca it is measurable, and there is no detectable leak.** With 749 rows
(11.1%) genuinely disagreeing between the two mappings, the arm tracks the
clean control almost exactly: −0.055 against −0.050 at 5 days, −0.008 against
−0.024 at 1 day.

This distinction is the single most important thing the spike produced.
Absence of evidence became evidence of absence only once the corpus could tell
the two apart. **The same-bar text alignment error, on daily bars at a 1- to
5-day horizon, does not by itself produce detectable look-ahead.** That does
not make the alignment discipline unnecessary — it means this particular error
is not where the danger lies at this granularity, and the project should stop
citing it as the motivating risk without this caveat.

### 4.3 The clean arm fails its own pass condition, and it is not leakage

`A_CLEAN` passes at 1 day but at 5 days sits at −0.068 (FNSPID) and −0.050
(Alpaca), with CIs excluding zero. The brief said the clean arm "must sit at
chance". It sits *below* chance.

Investigated rather than tuned away:

- Not a pipeline fault — the oracle control above.
- Not the class weighting — removing `sample_weight` moves lift only from
  −0.068 to −0.059.
- **Regime shift is the mechanism.** Fold 0 predicts 86% Sell into a test block
  that is 55% Buy. A model with no usable signal, trained through one NVDA
  regime and tested in the next, is not merely uninformative; it is
  confidently wrong, and macro-F1 punishes confident wrongness below what
  random guessing achieves.

The honest reading: **at a 5-day horizon on a single volatile ticker, this
pipeline has no predictive signal, and the brief's "sits at chance" framing was
too generous.** A no-signal model is free to land below chance out-of-sample.

### 4.4 Leak magnitude depends on window/horizon overlap

The canary was originally built on a centred **200-day** SMA and **did not
leak** (−0.021, PASS). The same non-causal construction on a **20-day**
Bollinger window leaks at +0.183. Both are equally future-peeking; the
difference is overlap. A centred 200-day mean spreads its future content over
~100 days ahead and says almost nothing about the next five.

Measured against the 5-day label score: trailing `dist_sma200` correlates
+0.060, centred `dist_sma200` −0.242, centred Bollinger(20) −0.532. The centred
long-window feature *does* carry future information — just not information
about the next five days.

**"Is this feature causal?" is not a window-independent question when the
detector is a downstream performance metric.** A leak audit that only exercises
long-window features can pass while short-window look-ahead goes undetected.
Both configurations are reported (`D_CENTRED`, `D_CENTRED_SMA200`).

### 4.5 Purging changed nothing detectable here

`C_NOPURGE` tracks `A_CLEAN` almost exactly on both corpora. Removing purge and
embargo had no measurable effect. That is a finding about *this* dataset — with
a 5-day label on daily bars and expanding folds, purging removes a handful of
rows at each fold boundary — not a general licence to drop it.

### 4.6 Calibration improved a metric while breaking the classifier

Isotonic calibration improved the Brier score from 0.819 to 0.612 and
simultaneously collapsed the model into a **constant predictor**: all 186
eval-fold decisions are `Buy`, at confidences between 0.523 and 0.572.
Uncalibrated, the same model predicted Hold 90 / Sell 54 / Buy 42.

Isotonic regression fitted on ~186 rows of a signal-free model has no
probability mapping to learn, so it fits the calibration fold's class prior.
Sharper probabilities, useless decisions. **One headline metric improved while
the system got worse** — the same argument the verifier makes with four
metrics, arriving independently from the calibration side.

**This reproduces on both corpora.** Re-running the engine on Alpaca gives
Brier 0.8124 → 0.6111 and, again, all 186 decisions `Buy`. The collapse is a
property of the model and the calibration set size, not of the text — which
rules out the most obvious alternative explanation.

### 4.7 The verifier is the strongest evidence in the spike, and its limit is precise

Five of six corruption classes are caught at 1.000 with **zero false
positives** — the verifier never rejects a clean explanation, which rules out
the trivial "reject everything" way of scoring perfectly. Because the
explanation layer here is a deterministic template rather than a language
model, this is fixture-based evidence over 112 controlled corruptions rather
than a sample of one model's behaviour, which is **stronger evidence than a
language model would give**.

The sixth class is a genuine limitation, stated precisely. A single vague
sentence *is* correctly classified as an unverifiable claim, but does not fail
the explanation: one vague line against ~19 correct concrete claims gives an
unverifiable rate of ~0.05, under the 0.15 threshold. That is the specification
behaving as designed — the four-metric scheme is sized to catch *pervasive*
hedging, the failure mode the design names. **The verifier bounds how much of
an explanation can be ungrounded; it does not certify that every sentence earns
its place.**

### 4.8 A test that proved nothing

The attribution track initially computed `base_value = raw_model_output −
sum(shap_values)`, which makes the additivity identity true by construction and
`tests/test_shap_additivity.py` — the one test named for attribution —
vacuous. It was rewritten to take the base value from the explainer's own
per-class `expected_value`, verified to match xgboost's native `pred_contribs`
bias column exactly. A guard now asserts the base value is independent of the
SHAP vector: it yields one distinct value per predicted class, where the old
approach yields 176.

Worth recording as a process finding: **an identity asserted in a test proves
nothing unless its inputs are independently sourced.**

---

## 5. What it changes in the design or plan

1. **Corpus selection is now a gating requirement, not a detail.** FNSPID is
   widely used and its timestamps are 99.78% midnight-defaulted. Any dataset
   for this project must be checked for genuine time-of-day resolution *before*
   any alignment claim is built on it. Alpaca/Benzinga is validated and adopted.
2. **Stop citing the same-bar error as the motivating risk without the
   measurement.** §4.2 shows it produces no detectable leak at this
   granularity. The alignment discipline stays — it is cheap and correct — but
   the thesis must not claim an unquantified danger it has now measured as
   absent.
3. **Leak audits must include a short-window centred control.** Add
   window/horizon overlap to the gate criteria (§4.4).
4. **Gate on signed lift, not absolute lift.** The current pass condition
   treats a no-signal model at −0.07 the same as a leaking one at +0.07. These
   are opposite failures.
5. **Calibration needs a decision-distribution gate**, not Brier alone (§4.6).
6. **The transparent linear baseline is not a formality** — it beat the model
   on CV mean. Every future model must clear it, reported every time.
7. **A single ticker cannot separate "no signal" from "regime shift."** The
   below-chance result is confounded with NVDA's 2018-2023 trajectory.
   Multi-ticker evaluation is required before any predictive claim.
8. **Predictive performance is now the project's open risk.** The harness
   works; the model has nothing to detect. Effort should move to feature and
   label design, not to more evaluation machinery.

---

## 6. Change control

Per the university guide §5.3 and the concept document's change-control section.

| # | Change | Why | Evidence |
| --- | --- | --- | --- |
| 1 | Scope narrowed from AAPL/NVDA/TSLA to **NVDA only** | AAPL and TSLA each missing 2021 entirely; AAPL also 2018-2019 | `artifacts/phase0_report.md` §4, §7 |
| 2 | `D_CENTRED`'s leaked feature changed from centred `dist_sma200` to centred `bollinger_pos` | The original canary was **quiet** (−0.021, PASS). A detector that cannot detect fails its only purpose. The plan document already named `bollinger_pos` as the alternative. | `artifacts/phase2_report.md` §4. Original configuration retained and reported as `D_CENTRED_SMA200` rather than discarded. |
| 3 | `verdict()` returns `BELOW_CHANCE` for negative-lift failures instead of labelling them `LEAK` | Negative lift is not leakage. Same pass condition, same threshold; only the failure label is split by direction. | `artifacts/phase2_report.md` §4 |
| 4 | **Alpaca/Benzinga corpus added alongside FNSPID** | FNSPID cannot measure `E_SAMEBAR_TEXT` (1 disagreeing row of 26 genuinely timestamped). Alpaca gives 749 of 6,767. | `artifacts/alpaca_probe_report.md`. FNSPID is **not** replaced; both are reported and the default corpus is unchanged. |
| 5 | `base_value` sourced from the explainer's `expected_value` rather than by subtraction | The additivity test was vacuous (§4.8) | `artifacts/phase3_report.md` §3 |

On change 2, the guard against result-shopping: the change was made because a
detector must overlap the horizon it guards — a principle that holds regardless
of which way the numbers fell — and both configurations are published.

---

## 7. Reproducing

```bash
uv sync

# Phase 1 — store, calendar, alignment, features (needs network for prices)
uv run python scripts/build_phase1_feature_matrix.py
uv run python scripts/build_alpaca_feature_matrix.py

# Phase 2 — the harness, both corpora
uv run python -m investify.harness.run_spike                    # ~140s
uv run python -m investify.harness.run_spike --corpus alpaca    # ~140s

# Phase 3 — engine, attribution, decision records (both corpora)
uv run python scripts/build_decision_records.py                 # ~7s
uv run python scripts/build_decision_records.py --corpus alpaca # ~6s

# Tests — 119, including the leak canary, which re-runs two arms for real
uv run pytest -q                                                # ~46s

# Phase 4 — the demo
uv run streamlit run app/streamlit_app.py
```

`artifacts/results.json` and `results_alpaca.json` record seed, git commit,
package versions, the corpus manifest hash, the XGBoost configuration and the
feature list alongside every number.

---

## 8. What this spike does not establish

- **Social-register sentiment and divergence features are entirely untested.**
  No social corpus, no CryptoBERT, no hand-labelled benchmark.
- **One ticker, one market.** Every result is NVDA on NYSE hours. The
  below-chance finding in particular is confounded with one stock's history.
- **No language model was involved anywhere.** The explanation layer is a
  deterministic template, so the verifier is evidenced against fixtures rather
  than live generations. Whether it catches the error modes a *distilled model*
  actually makes is untested — the fixtures encode the errors we anticipated.
- **The crypto / continuous-calendar path is unexercised.**
  `Continuous24hCalendar` is fully implemented but has **no tests and is never
  instantiated** by the spike. That it could be written against the
  `SessionCalendar` interface is weak evidence the abstraction is real; that
  nothing has run through it end to end means the abstraction is not
  demonstrated.
- **No predictive claim is supported.** The clean pipeline sits at or below
  chance at both horizons. Nothing here says the approach can forecast returns.
- **The verifier's guarantee is bounded**, not absolute (§4.7): it bounds the
  ungrounded proportion of an explanation and catches every concrete factual
  corruption tested, but does not certify each sentence is substantive.
- **`E_SAMEBAR_TEXT`'s null result is specific to daily bars at 1- and 5-day
  horizons on one corpus.** It does not generalise to intraday bars, where the
  same misalignment would span a far larger fraction of the label window.
- **The 1-month horizon, portfolio logic, position sizing and trading metrics**
  (Sharpe, drawdown) are out of scope and untouched.
