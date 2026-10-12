# Saved calibration investigation — 12 October 2026

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

The new audit reproduces the constant-Buy observation directly from both saved record files: 186 Buy decisions per corpus, 372 total. Each corpus has only ten distinct calibrated probability vectors. These are measured summaries of existing artifacts, not a new model fit or reproduced performance experiment.

| Saved corpus | Buy probability range | Recorded raw Buy margin range |
| --- | --- | --- |
| FNSPID | 0.5227272511–0.5721393228 | −2.1474192142–0.9230304956 |
| Alpaca/Benzinga | 0.4582493901–0.5716829896 | −2.1019465923–1.2608309984 |

Calibrated probabilities remain highest for Buy even when Buy is below 0.5; this is a three-class argmax, not a 0.5 binary threshold. The varying recorded raw margins rule out the narrower claim that the *saved raw Buy score* is constant. Only the predicted class's raw margin was retained, so the other two raw margins/probabilities and uncalibrated argmax decisions cannot be reconstructed from these files.

The preserved historical `run_engine` implementation fitted one-vs-rest isotonic mappings to fold 4 scores from `calib_model`, then applied them to a separately refitted fold 5 `eval_model`. The latter's training set included earlier calibration rows. This was a cross-fit/refit arrangement; transfer of probability mappings between its fitted classifiers remains unverified. A separate continuation audit subsequently reproduced label-availability defects on fixtures. Neither that finding nor the mapping-transfer assumption establishes the historical cause of constant-Buy output. Small-sample isotonic fitting, class priors and weak signal remain hypotheses. The saved audit and its source hashes describe the historical implementation, not a fitted run of current source.

The saved historical baseline, original source snapshot and metrics remain unchanged. Current working source defaults to `frozen_classifier`, reusing the same classifier/scaler on separate chronological calibration and evaluation blocks; its explicit `refit_transfer` comparator uses corrected label/calibration availability boundaries. Mocked orchestration tests establish object reuse and boundary handling, not an actual fit or scientific result. See [the current correction record](SCIENCE_CORRECTIONS_20261012.md).

Once genuine inputs and the supported scientific runtime are restored, compare those current modes on matching chronological evaluation identities while preserving the historical baseline separately. Retain full raw/calibrated scores, truth labels, calibration class counts, fitted knots and model/scaler/input hashes. Report all class distributions, macro-F1 and Brier together. Include an appropriate fixed class-prior comparator; do not equate macro-F1 chance with a universal 1/3 or tune thresholds on this evaluation fold to obtain varied decisions.

Required inputs are missing: raw/store prices/news, the original FinBERT cache, full labels and calibration score arrays, trained model/scaler artifacts, and the scientific dependencies. `evidence/calibration_audit_20261012.json` retains source hashes, exact measured summaries and inherited historical metrics clearly marked as unrecomputed. This audit does not establish useful stock prediction or investor suitability.
