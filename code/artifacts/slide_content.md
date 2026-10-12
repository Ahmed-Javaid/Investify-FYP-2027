# Defence slide — content

One slide. Everything below comes from `artifacts/results.csv` and
`results_alpaca.csv`.

---

## Title

**Can we detect leakage when text meets price bars?**
Investify · F26-003-QuantamentalAI · NVDA, 2018-2023, seed 42, 6 purged folds

---

## The arms table (5-day horizon)

| Arm | What it changes | FNSPID | Alpaca | Verdict |
| --- | --- | --- | --- | --- |
| A_CLEAN | nothing | −0.068 | −0.050 | below chance |
| B_SHUFFLED | shuffled K-fold | +0.124 | +0.110 | **leak** |
| C_NOPURGE | no purge/embargo | −0.061 | −0.050 | below chance |
| **D_CENTRED** | centred 20-day window | **+0.183** | **+0.219** | **leak** |
| D_CENTRED_SMA200 | centred 200-day window | −0.021 | −0.017 | pass |
| **E_SAMEBAR_TEXT** | text joins its own session | −0.038 | **−0.055** | no leak |

Lift = macro-F1 − stratified-random baseline. Threshold 0.03.

## Chart

`artifacts/arms_lift.png` (FNSPID) and `arms_lift_alpaca.png` (Alpaca) —
grouped bars, both horizons, 0.03 threshold drawn, 95% bootstrap CIs.

---

## One sentence on what was disproved

> We assumed same-bar text alignment was a serious hidden leak; on a corpus
> with real publication times — 749 of 6,767 headlines genuinely disagree
> between the two mapping rules — it produces **no detectable leak at all**
> (−0.055 against the clean arm's −0.050), while the detector proves itself on
> the same run by catching a deliberately centred feature at +0.219.

## One sentence on what changed

> Corpus timestamp resolution became a gating requirement rather than a
> detail — FNSPID, a widely-used dataset, is 99.78% midnight-defaulted and
> could not answer the question at all — and the leak audit now requires a
> short-window centred control, because the same non-causal construction leaks
> at +0.183 on a 20-day window and is silent on a 200-day one.

---

## If asked "did anything fail?"

Three things, all reported:

- The clean arm sits **below** chance at 5 days (−0.068), not at it. No signal
  plus regime shift; an oracle-feature control (+0.664 lift) rules out a broken
  harness.
- Isotonic calibration improved Brier 0.819 → 0.612 while collapsing the model
  into a constant `Buy` predictor.
- The verifier catches 5 of 6 corruption classes at 1.000 with zero false
  positives; a lone vague sentence is flagged as unverifiable but does not fail
  the explanation.

## If asked "what is the live demo showing?"

Tab 1 re-runs `D_CENTRED` in ~30 seconds and reproduces +0.1827 exactly.
Tab 2 corrupts an explanation and shows the verifier rejecting it and the
deterministic template taking over.
