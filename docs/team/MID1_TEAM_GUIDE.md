# Investify Mid-1 team guide

The revised talk is fourteen slides, 660 seconds (eleven minutes), plus Q&A.
Ahmed Javaid 22I-2530, Rafay Ul Haq 22I-2520 and Soban Ahmad 22I-2460 each have
220 planned seconds, including the shared demonstration. Supervisor: Mr. Irfan
Ullah; no co-supervisor. The actual submission date and batch range remain blank.

## Documents and scope

Use [current delivery](../../deliverables/current_delivery.json) for the selected
report and presentation and [the outline](../../deliverables/presentation_outline.json)
for slide notes. [Demonstration](DEMONSTRATION.md) gives the longer five-minute
practice script. Technical setup/tests are in [Engineering](../technical/ENGINEERING.md),
results/model details in [Research](../technical/RESEARCH.md), and acceptance/panel
responses in [Requirements](../technical/REQUIREMENTS.md).

Implemented: saved historical cases, complete evidence, full profile, confidence
gate, deterministic template, independent text/JSON checking and checked fallback.
Prompted LLM explanations are Mid-2 / Iteration 3; QLoRA is Iteration 4.

## Demo setup

From the repository root, install the recorded viewer in its own environment:

```powershell
git clone https://github.com/Ahmed-Javaid/Investify-FYP-2027.git
cd Investify-FYP-2027
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r code\requirements-demo-runtime.txt
.\.venv\Scripts\python.exe -B tools\restore_ci_checkout.py
.\.venv\Scripts\python.exe -m streamlit run code\app\streamlit_app.py --server.address=127.0.0.1 --server.port=8507 --theme.base=light --browser.gatherUsageStats=false
```

Keep the server terminal open and browse http://127.0.0.1:8507. On the prepared
project laptop use `powershell -File tools\start_guided_demo.ps1`. Supply a prepared
Python with `-PythonExe` on another machine. Use another port if 8507 is occupied.
Recorded viewing needs no API key, GPU or model download. Do not install the
scientific `pyproject.toml` into this viewer environment: its NumPy/pandas bounds
belong to a separate training runtime. Caches/temp/scratch on the project machine
stay under `E:\AI-Tools`; source and deliverables stay in the project.

## Live demonstration

The route is **Overview → Onboarding → Decision → Evidence → Risk profile →
Explanation check**. Select **Alpaca, multiclass calibration (frozen)** and
**2023-12-21**. A session is a stock-market trading day; the horizon is five
observed sessions. The dataset is historical, ending in 2023.

The headline is **No recommendation (Observe)**. Buy is a secondary diagnostic
class, with probabilities near one-third. Confidence is neither an expected
return nor a guarantee. The cautious example has allowance 0 / threshold 80%;
the higher-tolerance example has allowance 1 / threshold 50%. Both remain Observe.

On Evidence, MACD histogram is **0.0963**, SHAP **+0.1874**. Headline count is **10**,
SHAP **−0.1312**; average headline sentiment is **−0.1419**, SHAP **+0.0759**.
Tone and a model's response are different. SHAP is a raw selected-class score
contribution, not a confidence percentage or a cause of a price move.

Accept the unchanged explanation, inject the visible 1.00% error, then check it.
Show the rejected candidate/report and separately checked fallback, which keeps
**Policy outcome: Observe**. Edits, case changes and profile changes invalidate the
old verdict. End with restored record facts and a fresh accepted result.

### The six case selections

| Selection | Meaning |
| --- | --- |
| Alpaca multiclass frozen | Same classifier/scaler; temperature exposes uniform confidence. Main demonstration. |
| Alpaca multiclass refit | Separately recorded later refit with transferred calibration. No retraining on selection. |
| Fresh Alpaca frozen/refit | Original October historical study with the isotonic all-Buy failure. |
| Archived Alpaca / FNSPID | Earlier preserved source comparisons. |

All six contain the same 186 NVDA final evaluation dates. MSFT social posts are
a separate study. The four older cases cannot issue directional suggestions.

## Speaking schedule

| Slide | Topic | Presenter | Seconds |
| ---: | --- | --- | ---: |
| 1 | Title | Ahmed | 20 |
| 2 | Problem | Rafay | 40 |
| 3 | Panel feedback/actions | Ahmed | 45 |
| 4 | Contributions C1–C3 | Soban | 45 |
| 5 | Market background/design | Rafay | 45 |
| 6 | Model inventory | Rafay | 40 |
| 7 | Architecture/LLM layer | Soban | 40 |
| 8 | Requirements/metrics | Ahmed | 40 |
| 9 | Shared live demo | Ahmed 50, Rafay 50, Soban 80 | 180 |
| 10 | Leakage/linear results | Ahmed | 50 |
| 11 | Calibration/abstention | Soban | 30 |
| 12 | Illustrative explanation | Soban | 25 |
| 13 | Testing/CI/CD | Ahmed | 15 |
| 14 | Plan + Q&A transition | Rafay | 45 |
| | Total before Q&A | 220 seconds each | 660 |

The three-minute slide-9 demo is a shortened version of the five-minute practice
handout. Ahmed opens onboarding and evidence; Rafay demonstrates profile thresholds;
Soban explains Observe and the corruption/recovery check. Q&A is outside 660 seconds.

## Ahmed Javaid

Study [calendars](../../code/src/investify/calendars.py),
[feature assembly](../../code/src/investify/features/assembly.py),
[splits](../../code/src/investify/harness/splits.py),
[arms](../../code/src/investify/harness/arms.py),
[causality audit](../../code/src/investify/features/causality_audit.py), and
[CI runner](../../code/scripts/run_mid1_ci.py). Read report Chapters 3, 6.7, 7 and
Appendix D. Practise `test_backward_only.py`, `test_leak_canary.py`,
`test_label_availability.py`, `test_ci_runner.py` and `test_delivery_pipeline.py`.

Be ready to explain strict-prior joins, five observed-session endpoints versus
the extra calendar-day gap, why a centred window fires and why other fault
variants need not show inflation. CV XGBoost **0.2843 ± 0.0537** versus linear
**0.2796 ± 0.0559** is not the raw frozen final-case **0.3182** result. The clean
random comparator is **0.3287**. Gate A is partial; Gate B is not passed.

## Rafay Ul Haq

Study [presenter](../../code/app/presenter.py),
[case/study data](../../code/app/presenter_data.py),
[risk scoring](../../code/src/investify/risk_profile_gl.py),
[sentiment selection](../../code/src/investify/sentiment_selection.py), and
[inference](../../code/src/investify/sentiment_inference.py). Read report Chapters
1–2, profile/transparency requirements and the social methods/results in Chapter 7.
Practise `test_presenter_ui.py`, `test_mideval_calibration_risk_v2.py`,
`test_mideval_ai_annotation.py` and `test_recorded_social_study.py`.

Explain the five capacity/thirteen tolerance answers, restrictive caps and
`tau = 0.80 − 0.30 R`. No profile changes XGBoost probabilities. FinBERT is the
news model; CryptoBERT/Cardiff executed the same frozen **24-post** held-out
MSFT set, scoring **0.2564 / 0.6016** macro-F1 against AI references. Their
deployment selection and independent human validity remain open.

## Soban Ahmad

Study [record](../../code/src/investify/decision_record.py),
[temperature](../../code/src/investify/multiclass_calibration.py),
[context](../../code/src/investify/explain/context.py),
[template](../../code/src/investify/explain/template.py),
[verifier](../../code/src/investify/explain/verifier.py),
[pipeline](../../code/src/investify/explain/pipeline.py), and
[fixtures](../../code/src/investify/explain/fixtures.py). Read report Chapters 5,
6.6–6.10 and the metric definitions in Chapter 7. Practise
`test_mideval_verifier.py`, `test_mideval_complete_evidence.py`,
`test_mideval_policy_explanation.py` and `test_mideval_teacher_session.py`.

Explain why isotonic emits all Buy, why **T = 1000 / Brier ≈ 0.6667** means
near-uniform confidence, and why the future LLM is a separate layer. The
current verifier parses template grammar only. The illustrative slide is
hypothetical; it is not system output. Teacher: OpenAI GPT-6 assistant;
six recorded examples with deterministic JSON targets. Phi-3-mini and Mistral
remain planned, and QLoRA is Iteration 4.

## Questions to practise

- Which results run live, and which were saved offline?
- Why does a positive SHAP contribution differ from positive news tone?
- How can correct JSON accompany false prose, and why does the candidate fail?
- Why do both profile extremes abstain on all real temperature cases?
- What do the proposal gates require, and which conditions remain unmet?
- Why is the current verifier unable to check arbitrary fluent prose?
- What changes when the date/profile/text changes?
- What exactly are C1, C2 and planned C3, and how are they evaluated?

## Team tasks

Practise the full 660-second route and the longer click script. Use real records
for meeting logs, confirm submission/batch information, and obtain actual signatures
and supervisor review. Test the projector and network/installation before the
session. These activities have not been performed by the automated checks.
