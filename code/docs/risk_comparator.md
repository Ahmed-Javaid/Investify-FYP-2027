# Prototype risk profile and retrospective comparator

The live Streamlit and portable demos now calculate an explicit capacity/tolerance profile and use its score in a **separate linear comparator**. The saved XGBoost decision, calibrated probabilities and SHAP vector are unchanged. This does not demonstrate personalized classifier predictions, investor suitability or predictive skill.

## Profile contract

All five capacity and three tolerance answers are required. There are no preselected middle answers. Capacity factors and weights retain the old project prototype: horizon 0.30, emergency buffer 0.30, income stability 0.20, dependants 0.10 and age 0.10. The audit shows each factor's score and weighted contribution.

Project capacity rules keep the capacity score strictly below the 0.40 tier boundary when there is no emergency buffer, money is needed within one year, or income is irregular and the buffer is thin. A matched rule and a rule that actually lowers the score are reported separately. Tolerance averages the three inherited stand-in answer indices and divides by two. The reconciled score is the smaller capacity/tolerance score; tier cuts are 0.40 and 0.70. These are project choices, not a validated Grable–Lytton questionnaire or scoring key. No lambda parameter is used; the proposal/legacy lambda discrepancy remains unresolved for later modelling.

The capacity/willingness distinction is supported by [FINRA's risk-tolerance explanation](https://syndication.finra.org/content/know-your-risk-tolerance). [Investor.gov discusses time horizon and risk tolerance](https://www.investor.gov/introduction-investing/getting-started/asset-allocation). Neither source validates the project's numerical weights, caps or profile-to-blend mapping.

## Data and scaling contract

The old engine's training-fold scaler was not saved with the historical records. Averaging raw RSI, price distance and OBV values would mix incomparable units. This increment instead declares a **new retrospective comparator**:

1. Sort each corpus's 186 saved raw feature rows by session.
2. Fit means and population standard deviations on the first 148 rows. Constant feature scale is one; missing development news is excluded from that feature's statistics. Incomplete development technical data is refused.
3. Score only the remaining 38 sessions. A development-date selection cannot emit a comparator decision. Changing held-out inputs cannot change fitted statistics.
4. Technical signal T is the mean of the five technical z-scores under the inherited trend-following signs. News signal S is the z-score of `mean_polarity`. Missing held-out news contributes zero after scaling and is disclosed as an absent signal; missing technical input refuses a decision.
5. Compute C = R×S + (1−R)×T using the reconciled prototype score R, alongside the fixed R=0.5 reference. Preserve the old comparator's boundaries: Sell when C≤−0.5; Hold when −0.5<C≤0.5; Buy when C>0.5.

R weights news against technical evidence. A smaller R need not produce a more conservative action. The score is neither a probability nor an expected return. Outcome labels are absent from the saved records, so this increment reports no accuracy, return or superiority metric. The source artifact hash, fitting dates, inputs, missing-data policy and assumptions are visible/auditable. This scaling run does not reproduce the historical CV baseline.

## Verification

```powershell
python -B -m unittest discover -s tests -p 'test_mideval_risk.py' -v
python -B scripts/verify_risk_comparator.py --output ../evidence/risk_comparator_verification.json
```

Tests enumerate all 1,200 capacity combinations and 27 tolerance combinations, check caps/reconciliation/refusal, perturb held-out features to check scaling isolation, exercise both real corpora and verify no changes to saved predictions. The audit executes 228 row/scenario arithmetic checks: 76 actual held-out rows and three labelled parameter scenarios. These scenarios are not participant answers or human validation evidence.

Profile answers remain in the current UI session/request. The portable server does not log request bodies or store profiles; its API is `/api/risk-comparator`, with available options at `/api/profile-contract`.
