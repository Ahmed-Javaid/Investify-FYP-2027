# Phase 2 report: the leakage harness and the arms

Run date: 2026-09-10. Ticker NVDA only (scope decision, `phase0_report.md` §7).
Seed 42, 6 expanding folds, 5-day embargo, one fixed XGBoost config.
All numbers below come from `artifacts/results.json` / `results.csv`, produced
by `uv run python -m investify.harness.run_spike`. Nothing here is estimated,
projected or rounded from a run that did not happen.

---

## 1. What was built

| Module | Purpose |
| --- | --- |
| `harness/splits.py` | Expanding purged walk-forward (6 folds, 5-day embargo), shuffled K-fold, no-purge variant |
| `harness/metrics.py` | Macro-F1, train-fold stratified-random baseline, lift, 10,000-resample bootstrap CI, verdict, Brier |
| `harness/arms.py` | The arm configurations; per-arm feature-matrix construction; fold-local scaling; the fixed model |
| `harness/run_spike.py` | Orchestrator → `results.json`, `results.csv`, `arms_lift.png`, provenance |
| `features/indicators.py` | Added `dist_from_sma200_centred`, `bollinger_position_centred` (deliberate leaks) |
| `ingest/news.py` | Added `map_to_sessions_samebar` (deliberate leak) |
| `tests/` | `test_splits.py` (12), `test_metrics.py` (27), `test_leak_variants.py` (12), `test_leak_canary.py` (4) |

Full suite: **84 tests passing**.

### Row set held constant across arms

Every arm trains and tests on an identical row set, pinned to the clean arm:
bars with all five technical indicators and a label at that horizon present
(1,309 rows at 1d, 1,305 at 5d). Bars with no sentiment (the March-2021 sparse
patch found in Phase 0, plus the corpus tail) are **kept**, with the NaNs passed
to XGBoost's native missing-value handling.

This matters more than it looks. If rows with missing sentiment were dropped
instead, `E_SAMEBAR_TEXT` — which re-maps text to different sessions — would
drop a *different* set of rows than `A_CLEAN`, and the arms would no longer
differ only in temporal discipline. The comparison would be quietly invalid.

---

## 2. Results

Lift = macro-F1 − stratified-random baseline drawn from the **training** fold's
class distribution. Pass condition: |lift| ≤ 0.03 with a bootstrap CI
overlapping zero.

| Arm | Horizon | Macro-F1 | SD | Chance | Lift | 95% CI | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A_CLEAN | 1d | 0.3072 | 0.0457 | 0.3314 | −0.0242 | [−0.0589, +0.0073] | PASS |
| B_SHUFFLED | 1d | 0.3597 | 0.0190 | 0.3317 | +0.0280 | [+0.0128, +0.0418] | LEAK |
| C_NOPURGE | 1d | 0.3052 | 0.0480 | 0.3314 | −0.0261 | [−0.0649, +0.0044] | PASS |
| **D_CENTRED** | 1d | 0.3892 | 0.0632 | 0.3314 | **+0.0578** | [+0.0057, +0.1019] | **LEAK** |
| D_CENTRED_SMA200 | 1d | 0.3132 | 0.0446 | 0.3314 | −0.0182 | [−0.0491, +0.0148] | PASS |
| E_SAMEBAR_TEXT | 1d | 0.3228 | 0.0422 | 0.3314 | −0.0086 | [−0.0397, +0.0213] | PASS |
| A_CLEAN | 5d | 0.2604 | 0.0422 | 0.3288 | −0.0684 | [−0.0967, −0.0354] | BELOW_CHANCE |
| B_SHUFFLED | 5d | 0.4557 | 0.0188 | 0.3314 | +0.1242 | [+0.1097, +0.1375] | LEAK |
| C_NOPURGE | 5d | 0.2680 | 0.0341 | 0.3289 | −0.0609 | [−0.0826, −0.0344] | BELOW_CHANCE |
| **D_CENTRED** | 5d | 0.5115 | 0.0562 | 0.3288 | **+0.1827** | [+0.1456, +0.2263] | **LEAK** |
| D_CENTRED_SMA200 | 5d | 0.3078 | 0.0267 | 0.3288 | −0.0209 | [−0.0419, +0.0001] | PASS |
| E_SAMEBAR_TEXT | 5d | 0.2904 | 0.0501 | 0.3288 | −0.0383 | [−0.0762, −0.0044] | BELOW_CHANCE |

Chart: `artifacts/arms_lift.png`.

**`verdict` reports failures by direction.** `LEAK` means lift is positive —
the arm beat a random baseline, which for a control is evidence of look-ahead.
`BELOW_CHANCE` means lift is negative. Both fail the brief's pass condition;
collapsing them into one label would misstate the headline result, so they are
reported separately.

---

## 3. What the harness proves, and what it does not

### It detects leakage (evidenced, not asserted)

- **D_CENTRED leaks loudly**: +0.183 at 5 days, six times the 0.03 threshold,
  CI far clear of zero. The canary works.
- **B_SHUFFLED leaks**: +0.124 at 5 days. The brief predicted this arm would be
  invisible at 1 day and visible at 5. It is *mostly* right — at 1 day the lift
  is +0.028, just under the threshold, but its CI ([+0.013, +0.042]) excludes
  zero, so it is flagged. A small real effect, not an invisible one.
- **Positive control**: an oracle feature (the label score itself) injected into
  the clean pipeline scores macro-F1 0.9925, lift **+0.664**. The harness
  converts real signal into detected lift. When an arm shows no lift, that is a
  statement about the arm, not a broken detector.

### A_CLEAN does **not** meet the brief's pass condition at 5 days

A_CLEAN passes at 1 day (−0.024, CI overlapping zero) but at 5 days sits at
−0.068 with a CI excluding zero. The brief said the clean arm "must sit at
chance". It sits *below* chance, significantly.

This was investigated rather than tuned away:

- **Not a pipeline bug.** The oracle control above rules it out.
- **Not the class weighting.** Re-running A_CLEAN with `sample_weight` removed
  moves lift only from −0.068 to −0.059.
- **Regime shift is the mechanism.** Per-fold prediction mixes swing hard against
  the test block — fold 0 predicts 86% Sell into a test period that is 55% Buy.
  A model with no usable signal, trained through one NVDA regime and tested in
  the next, is not merely uninformative; it is confidently wrong, and macro-F1
  punishes confident wrongness below what random guessing achieves.

The honest reading: **at a 5-day horizon on a single volatile ticker, the clean
pipeline has no predictive signal, and the "sits at chance" framing in the brief
is too generous.** A no-signal model is free to land below chance out-of-sample.
This is pinned by `test_a_clean_below_chance_state_is_unchanged` so it cannot
drift silently. C_NOPURGE and E_SAMEBAR_TEXT inherit the same offset.

### C_NOPURGE: purging is not doing the work people assume

C_NOPURGE tracks A_CLEAN almost exactly (−0.061 vs −0.068 at 5d; −0.026 vs
−0.024 at 1d). Removing purge and embargo changed nothing detectable *here*.
That is a finding about this dataset, not a general licence to drop purging —
with a 5-day label on daily bars and expanding folds, the overlap purging
removes is a handful of rows at each fold boundary.

### E_SAMEBAR_TEXT: the arm this spike exists for, and its honest limits

E_SAMEBAR_TEXT does **not** leak. At 5 days it is −0.038 (BELOW_CHANCE, tracking
A_CLEAN's offset); at 1 day, −0.009 (PASS).

The limit that governs how far this can be read (from `phase0_report.md` §3/§7):

- 11,708 NVDA headlines, of which **26** carry a genuine time of day. The rest
  are midnight-defaulted.
- Of those 26, exactly **one** (2020-06-01 23:14 ET) maps to a different session
  under the same-bar rule than under the correct one.
- The re-mapping does still move a lot of data — sentiment features differ on
  **983 of 1,305 bars** — but that is driven by the midnight-UTC default landing
  at ~20:00 ET the *previous* day, so "the session it published in" is the day
  before the stated date. The mechanism firing is a timestamp artifact, not the
  after-close-item case the arm was designed to model.

So the correct statement is: **with date-only timestamps, this spike cannot
measure the magnitude of the same-bar text leak.** Not "the same-bar leak is
small" — the corpus lacks the resolution to answer. That is a data-availability
finding, and it is the single most important input to what Phase 2 changes about
the plan.

### D_CENTRED_SMA200: leak magnitude depends on window/horizon overlap

Reported as its own arm because it is a genuine result. A centred **200-day**
window shows no detectable leak (−0.021 at 5d, PASS) while a centred **20-day**
window leaks at +0.183. Both are equally non-causal. The difference is overlap:
a centred 200-day mean spreads its future content over ~100 days ahead and says
almost nothing about the next 5, while a centred 20-day band peeks ~10 days
ahead and covers the label horizon directly.

Measured on the raw features against the 5-day label score: trailing
dist_sma200 correlates +0.060, centred dist_sma200 −0.242, centred
Bollinger(20) −0.532. The centred 200-day feature *does* carry future
information — it simply is not information about the next five days.

**Implication for the project: "is this feature causal?" is not a
window-independent question when the detector is a downstream performance
metric.** A leak audit that only tests long-window features can pass while
short-window look-ahead goes undetected.

---

## 4. Change control

Per `CLAUDE.md` §Change control and guide §5.3.

**Change:** `D_CENTRED`'s leaked feature changed from centred `dist_sma200` to
centred `bollinger_pos` (20-day window).

**Why:** the first full run had `D_CENTRED` on centred `dist_sma200` and the
canary was **quiet** — lift −0.021 at 5d, verdict PASS. A leak canary that does
not detect fails its only purpose.

**Evidence prompting it:** the diagnosis above — oracle positive control
(+0.664) ruling out a harness fault, and the raw feature/label correlations
showing the centred 200-day feature carries future information that does not
bear on a 5-day label.

**Authority:** `docs/phase2_4_plan.md` already named `bollinger_pos` as an
alternative for this arm ("suggest `dist_sma200` or `bollinger_pos`"), so this
selects between options the plan offered rather than inventing a new one.

**Guard against result-shopping:** the original SMA-200 configuration is
retained and reported as `D_CENTRED_SMA200`, not discarded. The change was made
because a detector must overlap the horizon it guards — a principle that holds
regardless of which way the numbers came out — and both results are published.

**Second change:** `verdict()` now returns `BELOW_CHANCE` for negative-lift
failures instead of labelling them `LEAK`. Same pass condition, unchanged
threshold; only the failure label is split by direction.

---

## 5. What Phase 2 changes for the full project

1. **The 16:00 cutoff rule cannot be validated on FNSPID.** With 26 usable
   timestamps, the alignment discipline the project claims as contribution #1 is
   *implemented and unit-tested* but not *empirically evidenced at scale*.
   Getting a timestamped corpus is now the highest-priority data task for the
   full build, ahead of any modelling work.
2. **Leak audits must include a short-window centred control.** Add a
   window-overlap check to the gate criteria.
3. **Below-chance is a distinct outcome and needs its own gate.** The current
   pass condition treats a no-signal model that lands at −0.07 the same as one
   that leaks at +0.07. The full project should gate on signed lift.
4. **A single ticker is not enough to separate "no signal" from "regime shift".**
   The below-chance result is confounded with NVDA's 2018-2023 trajectory.

---

## 6. Reproducing

```bash
uv run python -m investify.harness.run_spike   # ~140s, 12 arm-runs
uv run pytest tests/test_leak_canary.py -q     # ~29s, re-runs the two crux arms
uv run pytest -q                               # 84 tests, ~41s
```

`results.json` records seed, git commit, package versions, the corpus manifest
hash, the XGBoost config and the feature list alongside every number.
