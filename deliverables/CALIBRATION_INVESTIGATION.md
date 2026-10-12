# Saved calibration investigation — 12 October 2026

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
