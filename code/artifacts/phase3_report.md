# Phase 3 report: engine, attribution, verifier

Run date: 2026-09-10. NVDA only, 5-day primary horizon, seed 42, one fixed
XGBoost config. Every number below comes from a run that actually happened
(`scripts/build_decision_records.py`, `uv run pytest -q`). Full suite: **113
tests passing**.

---

## 1. What was built

| Module | Purpose |
| --- | --- |
| `decision_record.py` | The frozen, self-validating schema everything downstream reads |
| `engine.py` | Fixed XGBoost, isotonic calibration, linear baseline comparator, TreeSHAP |
| `explain/template.py` | Deterministic English from a decision record — no model |
| `explain/verifier.py` | The six checks, four reported metrics, per-claim report |
| `explain/fixtures.py` | Corrupted-explanation generator, one variant per error class |
| `explain/pipeline.py` | The emit seam: verified, or replaced by the template |
| `scripts/build_decision_records.py` | Emits 186 records for the held-out eval fold |

Tests: `test_shap_additivity.py` (9), `test_verifier.py` (12),
`test_emit_pipeline.py` (8), plus Phase 1/2's 84.

---

## 2. Model results — a weak model, reported as such

| Metric | Model | Linear baseline `C = R·S + (1−R)·T` |
| --- | --- | --- |
| CV macro-F1 (6 folds, expanding purged) | 0.2604 ± 0.0422 | 0.2962 ± 0.0919 |
| Eval-fold macro-F1 (fold 5, n=186) | 0.2238 | 0.1495 |

The model's CV macro-F1 (0.2604) matches Phase 2's `A_CLEAN` result to four
decimal places — a cross-check that the engine trains under the harness's exact
fold discipline rather than a looser one.

**The transparent linear baseline beats the XGBoost model on CV mean** (0.2962
vs 0.2604) and loses on the single eval fold. Reported both ways rather than
picking the flattering one. Neither is above chance; Phase 2 established this
pipeline has no predictive signal at 5 days.

### Calibration improved Brier while making the classifier degenerate

| | Brier (eval fold, n=186) | Predicted class distribution |
| --- | --- | --- |
| Before calibration | 0.8191 | Hold 90, Sell 54, Buy 42 |
| After isotonic calibration | **0.6119** | **Buy 186, Hold 0, Sell 0** |

Truth on that fold: Buy 94, Sell 62, Hold 30.

Calibration improved the Brier score by 0.21 and simultaneously collapsed the
model into a constant predictor. Every one of the 186 emitted decisions is
`Buy`, with calibrated confidence in a narrow 0.523–0.572 band.

The mechanism: isotonic regression fitted on ~186 rows of a model with no
signal has nothing to learn a probability mapping *from*, so it fits the
calibration fold's class prior. The eval fold is Buy-heavy, the uncalibrated
model over-predicted Hold, and isotonic duly pushed everything to Buy. Sharper
probabilities, useless decisions.

**This is a result worth keeping.** It is a concrete demonstration that a single
headline metric can improve while the system gets worse — the same argument the
verifier makes with its four metrics, arriving independently from the
calibration side. Not tuned, not hidden.

**Consequence for the demo:** Tab 2's date picker will show `Buy` on every
available date. The demo must say so on screen. It demonstrates the decision
*plumbing* — attribution, template, verification — not a usable signal.

---

## 3. Attribution: additivity is verified, not assumed

TreeSHAP, path-dependent, no interaction values, sliced to the predicted class.

The first implementation computed `base_value = raw_model_output − sum(shap)`.
That makes the additivity identity true by construction and
`tests/test_shap_additivity.py` — the one test the brief names for attribution —
**vacuous**. It was rewritten to take `base_value` from the explainer's own
per-class `expected_value`, so additivity is a property that gets checked.

Confirmed empirically on shap 0.49.1 / xgboost 3.2.0:

- shap's per-class `expected_value` equals xgboost's native `pred_contribs`
  bias column **exactly**; the contribution matrices agree to 0.0.
- `base_value + sum(shap_values)` reproduces the raw margin to **max 1.9e-7**
  across all 186 records, inside the schema's 1e-4 tolerance.
- Additivity holds against the **raw margin**, not the calibrated probability.

`test_base_value_is_independent_of_the_shap_vector` guards the regression: a
per-class `expected_value` is constant across rows, so the test asserts each
predicted class carries exactly one distinct base value. Under the old
subtraction approach the same records produce **176 distinct values** — the
guard discriminates the two implementations rather than passing vacuously.

### One environment bug fixed

`shap.TreeExplainer(model)` crashes at construction on xgboost 3.2.0 multiclass
models: xgboost ≥2 serialises `base_score` per-class for `multi:softprob`, but
shap 0.49.1's loader expects a scalar
(`ValueError: could not convert string to float: '[9.5e-07,-7.2e-07,-2.4e-07]'`).
No newer shap resolves. Worked around with a narrow, idempotent monkeypatch that
collapses the per-class list to its mean purely so loading succeeds.

The patch is inert with respect to attribution, and that is now evidenced rather
than asserted: per-class bias values recovered through the patched loader
(`[-0.0662, +0.0441, −0.0291]`) match xgboost's own unpatched `pred_contribs`
bias column exactly.

---

## 4. Verifier: the strongest evidence in the spike

112 fixtures — 8 hand-built records × 2 payload modes × (clean + 6 corruption
classes), seed-deterministic. `artifacts/verifier_confusion_matrix.json`.

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
| **vague_unverifiable** | **0.000** |
| clean (pass rate) | 1.000 |

**Zero false positives.** The verifier never rejects a clean explanation, in
either payload or prose-only mode — which rules out the trivial "reject
everything" way of scoring perfectly. Four metrics on clean explanations:
numeric fidelity 1.0, directional consistency 1.0, claim recall 1.0,
unverifiable rate 0.0.

### The one class it does not catch, and why that is defensible

A single injected vague sentence is **always correctly classified as an
unverifiable claim** — check 6 works. It never fails the explanation, because
one vague line against ~19 correct concrete claims gives an unverifiable rate of
~0.05, well under the brief's own 0.15 threshold.

This is the specification behaving as written. The four-metric scheme is sized
to catch *pervasive* hedging — the failure mode the brief actually names, "a
model that speaks vaguely enough to make every claim unverifiable" — and an
isolated filler sentence in an otherwise fully-grounded explanation is not that.
The honest limitation to state at the defence: **the verifier bounds how much of
an explanation can be ungrounded; it does not guarantee every sentence earns its
place.**

The test for this class asserts only that a detection rate was recorded, not
that it hit a target. The test was not weakened to hide the result.

---

## 5. The emit seam

`explain/pipeline.py::emit()` — a candidate explanation is verified and, on
failure, replaced by the deterministic template. In this spike the template is
also the only generator, so the fallback never fires in production use. It is
built and tested anyway because the full project swaps in a QLoRA-distilled
generator, at which point this is the only thing between a hallucinated
explanation and the user.

`test_emit_pipeline.py` runs against **real** decision records and asserts every
detectable corruption class is replaced rather than emitted, that what is
emitted always verifies, and that the non-advice notice always survives. If the
deterministic template ever fails its own verifier, that raises loudly rather
than being quietly returned.

---

## 6. What Phase 3 changes for the full project

1. **Calibration needs a decision-distribution gate, not just Brier.** A metric
   improved while the classifier collapsed to a constant. Add a degenerate-output
   check to the acceptance criteria.
2. **The linear baseline is not a formality.** It beat the model on CV mean.
   Whatever the full project builds must clear it, and the comparison must be
   reported every time.
3. **Additivity tests must be checked for vacuity.** The first version passed
   while proving nothing. Any identity asserted in a test needs its inputs to be
   independently sourced.
4. **The verifier's guarantee should be stated precisely in the thesis**: it
   bounds ungrounded *proportion*, and catches every concrete factual corruption
   class tested. It does not certify that each sentence is individually
   substantive.

---

## 7. Reproducing

```bash
uv run python scripts/build_decision_records.py   # ~7s -> artifacts/decision_records.json
uv run pytest -q                                  # 113 tests, ~50s
```
