# Soban Ahmad: Mid-1 preparation

22I-2460. Assigned share: **one-third**. Focus: **Decision engine, calibration, SHAP and verified explanations**.

This is your assigned preparation and defence work. Study the current implementation, practise its boundaries and record what you personally review or change. The packet does not state that you authored all existing code.

## Presentation and live-demo route

Planned speaking time: **five minutes**, including your live-demo actions. Slide numbers refer to the current twelve-slide deck. Follow the deck order and hand over to the next named presenter.

- Slide 5 (50 seconds): trace offline model artifacts into the validated record and presentation layer.
- Slide 7 (45 seconds): explain candidate checking, retained rejection and separate fallback.
- Slide 8 (40 seconds): show the recorded class/probabilities and SHAP contributions on Decision.
- Slide 8 (80 seconds): Inject wrong probability, then Check explanation. Show rejection and verified fallback, then edit the candidate to clear the old verdict.
- Slide 9 (55 seconds): explain why the retained fresh calibration maps force Buy and why varied output cannot be claimed.
- Slide 12 (30 seconds): state the equal assignments, remaining review and later student/deployment work.

## Code to study

| File | What you should explain |
| --- | --- |
| [code/src/investify/engine.py](../code/src/investify/engine.py) | Model, calibration and attribution orchestration |
| [code/src/investify/decision_record.py](../code/src/investify/decision_record.py) | DecisionRecord probability, class and attribution invariants |
| [code/src/investify/explain/context.py](../code/src/investify/explain/context.py) | build_context and complete feature evidence |
| [code/src/investify/explain/verifier.py](../code/src/investify/explain/verifier.py) | verify and independent visible-prose/JSON checks |
| [code/src/investify/explain/pipeline.py](../code/src/investify/explain/pipeline.py) | emit and independently verified fallback |
| [code/app/presenter_data.py](../code/app/presenter_data.py) | calibration_diagnosis and source-bound diagnostics |
| [code/app/presenter.py](../code/app/presenter.py) | decision_view, candidate_identity and explanation_view |

## Tests and report reading

Read the tests below and explain the failure each one prevents. Existing pass receipts are available; you do not need to rerun paid inference or retrain a model for practice.

- [code/tests/test_calibration_availability.py](../code/tests/test_calibration_availability.py)
- [code/tests/test_shap_additivity.py](../code/tests/test_shap_additivity.py)
- [code/tests/test_mideval_record_validation.py](../code/tests/test_mideval_record_validation.py)
- [code/tests/test_mideval_verifier.py](../code/tests/test_mideval_verifier.py)
- [code/tests/test_emit_pipeline.py](../code/tests/test_emit_pipeline.py)
- [code/tests/test_presenter_ui.py](../code/tests/test_presenter_ui.py)

Supporting reading:

- [report/chapters/chapter5_design.tex](../report/chapters/chapter5_design.tex)
- [report/chapters/chapter6_iteration1.tex](../report/chapters/chapter6_iteration1.tex)
- [deliverables/CALIBRATION_INVESTIGATION.md](../deliverables/CALIBRATION_INVESTIGATION.md)
- [deliverables/LLM_DESIGN.md](../deliverables/LLM_DESIGN.md)

## Facts to keep accurate

- TreeSHAP explains raw model scores. Its values are not calibrated probabilities, causes or expected returns.
- Both fresh calibration modes select Buy on all 186 retained evaluation cases. Global map bounds also force Buy across the raw-probability simplex.
- Frozen raw macro-F1 is 0.3182 and calibrated macro-F1 is 0.2238. The negative result stays in the report.
- Correct factual JSON does not excuse a conflicting visible sentence. A rejected candidate and verified fallback retain separate verdicts.

## Likely defence questions

**Why does calibration produce only Buy?** The Buy map minimum exceeds the other maps' maxima. Positive common normalization preserves the ordering.

**Does a consistent explanation show investment usefulness?** It shows agreement with the recorded inputs. It does not establish causality, predictive skill or user comprehension.

**Why check fallback independently?** Candidate rejection is retained and the replacement must pass its own checks. A failed template check must also surface.

**Is QLoRA complete or required for this Mid-1?** No. It remains a later proposal milestone. The current student is untrained and no student efficacy is claimed.

## Record after practice

- Date and files/functions personally reviewed:
- Demo steps completed and observed results:
- One test boundary explained in your own words:
- Changes personally made, if any:
- Assistance/tools used:
- Questions or failures still needing follow-up:

Also rehearse the entire team route so you can recover if another member needs help. [Shared schedule](MEMBER_PREPARATION_PACK.md).
