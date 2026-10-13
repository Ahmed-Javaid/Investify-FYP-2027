# Rafay Ul Haq: Mid-1 preparation

22I-2520. Assigned share: **one-third**. Focus: **Interface, risk profile, social sentiment and recovery**.

This is your assigned preparation and defence work. Study the current implementation, practise its boundaries and record what you personally review or change. The packet does not state that you authored all existing code.

## Presentation and live-demo route

Planned speaking time: **five minutes**, including your live-demo actions. Slide numbers refer to the current twelve-slide deck. Follow the deck order and hand over to the next named presenter.

- Slide 2 (60 seconds): explain the problem and evidence-based explanations.
- Slide 6 (60 seconds): relate cases, validated records, feature context and file schema.
- Slide 8 (20 seconds): open Overview, then Open the decision walkthrough. Keep Fresh Alpaca - frozen classifier and 2023-12-21 selected.
- Slide 8 (60 seconds): choose Cautious example, Higher-tolerance example, then Clear profile. Show the separate comparator change while the classifier stays Buy.
- Slide 11 (100 seconds): explain the sentiment comparison and recorded teacher pilot with their sample/reference limits.

## Code to study

| File | What you should explain |
| --- | --- |
| [code/app/presenter.py](../code/app/presenter.py) | navigate, profile_example, clear_profile, profile_view and social_view |
| [code/app/presenter_data.py](../code/app/presenter_data.py) | load_cases and social_comparison |
| [code/src/investify/risk_profile.py](../code/src/investify/risk_profile.py) | score_profile and RiskProfile |
| [code/src/investify/risk_comparator.py](../code/src/investify/risk_comparator.py) | build_comparator and HistoricalComparator.score |
| [code/src/investify/sentiment_receipts.py](../code/src/investify/sentiment_receipts.py) | compare_bundles and frozen candidate identities |
| [code/src/investify/explain/teacher_session.py](../code/src/investify/explain/teacher_session.py) | Recorded teacher examples and their bounded scope |

## Tests and report reading

Read the tests below and explain the failure each one prevents. Existing pass receipts are available; you do not need to rerun paid inference or retrain a model for practice.

- [code/tests/test_presenter_ui.py](../code/tests/test_presenter_ui.py)
- [code/tests/test_mideval_risk.py](../code/tests/test_mideval_risk.py)
- [code/tests/test_recorded_social_study.py](../code/tests/test_recorded_social_study.py)
- [code/tests/test_mideval_sentiment_receipts.py](../code/tests/test_mideval_sentiment_receipts.py)
- [code/tests/test_mideval_teacher_session.py](../code/tests/test_mideval_teacher_session.py)

Supporting reading:

- [report/chapters/chapter4_requirements.tex](../report/chapters/chapter4_requirements.tex)
- [report/chapters/chapter7_ui_manual.tex](../report/chapters/chapter7_ui_manual.tex)
- [deliverables/MODELS_AND_EVALUATION.md](../deliverables/MODELS_AND_EVALUATION.md)
- [deliverables/DEMO_AND_DEFENCE_GUIDE.md](../deliverables/DEMO_AND_DEFENCE_GUIDE.md)

## Facts to keep accurate

- The profile examples are fictional inputs. R=0 produces Hold and R=1 Sell in the separate retrospective comparator on the demonstrated case.
- Clearing the profile removes its result. The questionnaire does not silently supply personal answers.
- Original CryptoBERT/Cardiff macro-F1 is 0.2564/0.6016 on the same 24 held-out AI references, including only two negative examples.
- There are six recorded assistant-teacher examples, four training and two validation. The original Phi-3-mini student remains untrained.

## Likely defence questions

**Does the profile change XGBoost probabilities?** No. It changes a separate prototype comparator and leaves the recorded classifier output fixed.

**Why is Cardiff not finally selected?** This small AI-reference benchmark supports exploratory comparison. Adequacy criteria and appropriate independent or supervisor review remain open.

**Are social features used by the core classifier?** The social study remains separate from the current news-based core.

**What happens if a source is invalid?** The interface reports the error and withholds substitute results. Do not silently select a different artifact.

## Record after practice

- Date and files/functions personally reviewed:
- Demo steps completed and observed results:
- One test boundary explained in your own words:
- Changes personally made, if any:
- Assistance/tools used:
- Questions or failures still needing follow-up:

Also rehearse the entire team route so you can recover if another member needs help. [Shared schedule](MEMBER_PREPARATION_PACK.md).
