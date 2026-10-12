# Investify problem statement and contribution

Project F26-003-Investify was approved with minor modifications. The panel requested clearer contributions, a refined problem statement, and a better explanation of the LLM's user benefit. This is working text for the new mid report and presentation.

## Problem statement

A retail investor evaluating a company must interpret historical price indicators and a large volume of news and social commentary. A Buy, Hold, or Sell label alone does not explain which signals influenced it, how conflicting evidence was handled, how uncertain the result is, or whether the proposed action fits the user's risk constraints. A natural-language explanation can also misstate the values or contributions behind a prediction. Separately, evaluations that use information unavailable at decision time can overstate model quality.

Investify addresses these problems through a temporally controlled evaluation pipeline and understandable explanations tied to recorded model inputs and attributions. It presents the supporting evidence, uncertainty, data limitations, and actual role of the risk profile. Its outputs are educational and advisory. Predictive usefulness is evaluated against explicit baselines, and the system does not execute transactions.

## Contributions and evidence

| Contribution | Team-built work | Evidence and boundary |
| --- | --- | --- |
| Leakage-audited evaluation | Timestamp/store semantics, calendar/as-of rules, causal feature construction, control design, and fault tests. | Measured detection on specified deliberately broken configurations. It is not proof that every possible leak is absent. |
| Verified user-facing explanations | A claim checker, grounded fallback, complete evidence presentation, and a controlled comparison of explanation generators. | Concrete error rejection and user understanding must both be evaluated. Current evidence covers templates/fixtures; LLM generations remain to be tested. |
| News/social disagreement study | Model routing, a labelled equity social benchmark, divergence feature construction, and a pre-registered ablation. | Currently planned. A negative transfer or null ablation is an acceptable finding with its limitations reported. |

Pretrained sentiment models, XGBoost, TreeSHAP, and language-model weights provide inputs and reusable methods. Novelty is not claimed merely for using them. The related-work comparison must justify the differences in verification, experimental controls, and user transparency.

## First mid increment

The new evidence context explains all technical and news features in the stored decision, including their definitions, values, and SHAP effects. It distinguishes model attribution from market causation and raw model score from calibrated probability. It identifies absent social features and the questionnaire's current display-only role. This addresses part of PF-03 and PF-08 while establishing the LLM input contract; PF-02 remains open until a real generator is evaluated.
