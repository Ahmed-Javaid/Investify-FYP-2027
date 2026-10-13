# Investify Mid-1 team guide

This is the team's single preparation guide: documents, setup, demonstration,
speaking allocation, individual code reading, defence questions and remaining
tasks. Read the shared sections, then your own member section.

[Demo setup](#demo-setup) | [Live demonstration](#live-demonstration) |
[Speaking schedule](#speaking-schedule) | [Ahmed](#ahmed-javaid) |
[Rafay](#rafay-ul-haq) | [Soban](#soban-ahmad) |
[Questions to practise](#questions-to-practise) | [Team tasks](#team-tasks)

## Documents and scope

| Document | Current file |
| --- | --- |
| Report, 82 pages | [Report PDF](../../deliverables/Investify_FYP1_Mid_Report_Revised_20261014.pdf) |
| Presentation, 12 slides | [Presentation PDF](../../deliverables/Investify_FYP1_Mid_Presentation_Revised_20261014.pdf) |
| Committee requirements and marking | [Official Mid-1 rubric](../../sources/Mid_Eval/FYP-1-Mid-Assessment-Guidelines-and-Rubrics.pdf) |

FYP-1 Mid-Evaluation, Fall 2026. Ahmed Javaid (22I-2530), Rafay Ul Haq (22I-2520)
and Soban Ahmad (22I-2460); supervisor Mr. Irfan Ullah; no co-supervisor.
Coordinator omitted. Report date: 11 October 2026; actual revision/test dates
remain in the evidence.

The working core checks explanations against recorded decisions, rejects
contradictions, checks fallback and presents supporting feature evidence. The
complete profile score and confidence gate calculate live alongside fixed recorded probabilities.
Whole-FYP integration, useful model evaluation, student inference/adaptation,
production hosting and participant acceptance remain unfinished.

The team's 100% technical Mid-1 definition covers code, authored report,
hosted CI/CD and demonstration modules. It is not whole-FYP completion or a
predicted grade. The committee still assesses live behaviour and understanding.

## Demo setup

Install Git and Python 3.11. In PowerShell:

```powershell
git -c core.autocrlf=false clone https://github.com/Ahmed-Javaid/Investify-FYP-2027.git
cd Investify-FYP-2027
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r code\requirements-demo-runtime.txt
.\.venv\Scripts\python.exe -B tools\restore_ci_checkout.py
git config core.autocrlf true
.\.venv\Scripts\python.exe -m streamlit run code\app\streamlit_app.py --server.address=127.0.0.1 --server.port=8507 --browser.gatherUsageStats=false
```

Open http://127.0.0.1:8507 on your own laptop; keep the terminal open. An existing
clone uses `git pull`, the restoration command and launch command. Reinstall
requirements if changed. Choose another port if occupied. Initial installation
needs internet; this recorded demo needs no GPU, API keys or model downloads.

The prepared project laptop can launch from the repository root with
`& .\tools\start_guided_demo.ps1`, using its existing E: environment. Open an
already running server directly. Ctrl+C stops a foreground launch.

## Live demonstration

Pause at slide 8. From Overview choose **Open the decision walkthrough**.
Select **Alpaca, multiclass calibration (frozen)**, NVDA, **2023-12-21**.

| Step | Action | Explain |
| --- | --- | --- |
| Decision, 40 seconds | Show class, probabilities and contributions. | New temperature records preserve raw Buy/Hold/Sell classes, with confidence near one-third; the UI abstains. SHAP explains raw scores. |
| Evidence, 40 seconds | Inspect one technical and one news feature. | Show values, meanings and contributions; all eleven inputs remain available. |
| Risk profile, 60 seconds | Cautious example, Higher-tolerance example, Clear profile. | Fictional profiles change allowance R and required confidence, while the raw model stays fixed. Both abstain on weak real evidence; Clear removes the profile. |
| Explanation, 80 seconds | Inject wrong probability, Check explanation, then edit. | Visible 1.00% fails despite correct JSON. Fallback passes independently. Editing removes the old verdict. |

Profile arithmetic, checking, fallback and state handling run live. Predictions
and research outcomes are recorded. Opening the app does not train, acquire
current news or rerun the studies. Invalid evidence withholds a replacement
decision; development-block sessions refuse comparator scoring.

## Speaking schedule

Each member delivered their assigned Mid-1 module part and has one-third delivery,
integration and defence responsibility, four primary slides and five minutes
including the demo. Continue studying the code and record practice/review details.

| Slide | Presenter | Seconds |
| --- | --- | ---: |
| 1 | Ahmed | 30 |
| 2 | Rafay | 60 |
| 3 | Ahmed | 60 |
| 4 | Ahmed | 70 |
| 5 | Soban | 50 |
| 6 | Rafay | 60 |
| 7 | Soban | 45 |
| 8 | Shared demo; Rafay opens | 240 |
| 9 | Soban | 55 |
| 10 | Ahmed | 100 |
| 11 | Rafay | 100 |
| 12 | Soban | 30 |

Slide 8: Rafay opens for 20 seconds, Soban shows Decision for 40, Ahmed shows
Evidence for 40, Rafay shows Risk for 60 and Soban checks Explanation for 80.
Totals: 300 seconds each, 900 overall. Shorten after rehearsal if questions must
fit inside the fifteen-minute slot.

| Member | Proposal responsibility |
| --- | --- |
| Ahmed | Point-in-time harness, leakage tests, dual timestamps, parity and deployment. |
| Rafay | Risk profiling, sentiment, degraded operation, acceptance and frontend. |
| Soban | Decision engine, calibration, SHAP, verifier and later QLoRA. |

## Ahmed Javaid

22I-2530. Focus: **Temporal integrity, evaluation harness and leakage**. Assigned preparation share: one-third.

### Presentation and live-demo route

- Slide 1 (30 seconds): introduce the confirmed team and supervisor.
- Slide 3 (60 seconds): bound the recorded prototype and distinguish later milestones.
- Slide 4 (70 seconds): show the Mid-1 evidence and distinguish checks from approval.
- Slide 8 (40 seconds): on Evidence, select one technical feature and one news feature. Identify their recorded value and contribution.
- Slide 10 (100 seconds): explain the chronological experiment, purge boundary, clean result and deliberately leaky canary.

### Code to study

| File | What you should explain |
| --- | --- |
| [code/src/investify/harness/splits.py](../../code/src/investify/harness/splits.py) | Chronological split and purge rules |
| [code/src/investify/features/causality_audit.py](../../code/src/investify/features/causality_audit.py) | Available-at and future-information checks |
| [code/src/investify/labels.py](../../code/src/investify/labels.py) | Five-session targets and label availability |
| [code/src/investify/harness/arms.py](../../code/src/investify/harness/arms.py) | Clean arm and deliberately leaky canary |
| [code/app/presenter.py](../../code/app/presenter.py) | evidence_view and leakage_view |
| [code/scripts/run_mid1_ci.py](../../code/scripts/run_mid1_ci.py) | Shared CI runner, source guards and job receipts |

### Tests and report reading

- [code/tests/test_splits.py](../../code/tests/test_splits.py)
- [code/tests/test_asof_join.py](../../code/tests/test_asof_join.py)
- [code/tests/test_purge_label_availability.py](../../code/tests/test_purge_label_availability.py)
- [code/tests/test_leak_canary.py](../../code/tests/test_leak_canary.py)
- [code/tests/test_ci_runner.py](../../code/tests/test_ci_runner.py)

Supporting reading:

- [report/chapters/chapter3_iteration_plan.tex](../../report/chapters/chapter3_iteration_plan.tex)
- [report/chapters/chapter6_iteration1.tex](../../report/chapters/chapter6_iteration1.tex)
- [report/chapters/chapter8_testing.tex](../../report/chapters/chapter8_testing.tex)
- [Engineering: CI/CD](../technical/ENGINEERING.md#cicd-and-tests)

### Facts to keep accurate

- A feature must be available before the decision. A label can depend on later prices but must not enter the feature vector or an earlier fit.
- The clean five-session macro-F1 is 0.2843 versus the training-distribution random comparator at 0.3287.
- The centred canary has lift +0.2104 because it deliberately uses future information. It is a leakage demonstration.
- Hosted Windows/Ubuntu CI and artifact delivery passed. Production hosting remains later work; these are engineering checks, not prediction-quality evidence.

### Likely defence questions

**Why is a chronological split insufficient by itself?** Labels can cross the fit/evaluation boundary. Explain the purge and when a target becomes available.

**Why keep the leaky result?** It demonstrates detection of a known failure and is explicitly excluded from valid predictive claims.

**What is the difference between session time and availability time?** Session time identifies the market interval. Availability time determines when an input could actually be used.

**What CI/CD exists?** The portable and UI jobs pass on both Windows and Ubuntu; a fifth job delivers the extraction-checked source/PDF artifact. Production hosting remains later work.

## Rafay Ul Haq

22I-2520. Focus: **Interface, risk profile, social sentiment and recovery**. Assigned preparation share: one-third.

### Presentation and live-demo route

- Slide 2 (60 seconds): explain the problem and evidence-based explanations.
- Slide 6 (60 seconds): relate cases, validated records, feature context and file schema.
- Slide 8 (20 seconds): open Overview, then Open the decision walkthrough. Select Alpaca, multiclass calibration (frozen), and 2023-12-21.
- Slide 8 (60 seconds): choose Cautious example, Higher-tolerance example, then Clear profile. Show allowance and confidence threshold changing while raw probabilities remain fixed; both profiles abstain on this weak case.
- Slide 11 (100 seconds): explain the sentiment comparison and recorded teacher pilot with their sample/reference limits.

### Code to study

| File | What you should explain |
| --- | --- |
| [code/app/presenter.py](../../code/app/presenter.py) | navigate, profile_example, clear_profile, profile_view and social_view |
| [code/app/presenter_data.py](../../code/app/presenter_data.py) | load_cases and social_comparison |
| [code/src/investify/risk_profile_gl.py](../../code/src/investify/risk_profile_gl.py) | score_profile, InvestorProfile and apply_risk_policy |
| [code/src/investify/risk_comparator.py](../../code/src/investify/risk_comparator.py) | build_comparator and HistoricalComparator.score |
| [code/src/investify/sentiment_receipts.py](../../code/src/investify/sentiment_receipts.py) | compare_bundles and frozen candidate identities |
| [code/src/investify/explain/teacher_session.py](../../code/src/investify/explain/teacher_session.py) | Recorded teacher examples and their bounded scope |

### Tests and report reading

- [code/tests/test_presenter_ui.py](../../code/tests/test_presenter_ui.py)
- [code/tests/test_mideval_risk.py](../../code/tests/test_mideval_risk.py) (historical comparator)
- [code/tests/test_mideval_calibration_risk_v2.py](../../code/tests/test_mideval_calibration_risk_v2.py) (current scoring/policy and calibration)
- [code/tests/test_recorded_social_study.py](../../code/tests/test_recorded_social_study.py)
- [code/tests/test_mideval_sentiment_receipts.py](../../code/tests/test_mideval_sentiment_receipts.py)
- [code/tests/test_mideval_teacher_session.py](../../code/tests/test_mideval_teacher_session.py)

Supporting reading:

- [report/chapters/chapter4_requirements.tex](../../report/chapters/chapter4_requirements.tex)
- [report/chapters/chapter7_ui_manual.tex](../../report/chapters/chapter7_ui_manual.tex)
- [Research: models/results](../technical/RESEARCH.md#contribution-and-models)
- [Shared demo route](MID1_TEAM_GUIDE.md#live-demonstration)

### Facts to keep accurate

- The fictional examples now use all thirteen tolerance items. R=0 requires 80% confidence and R=1 requires 50%; both withhold a direction on the actual near-uniform case.
- Clearing the profile removes its result. The questionnaire does not silently supply personal answers.
- Original CryptoBERT/Cardiff macro-F1 is 0.2564/0.6016 on the same 24 held-out reference labels, including only two negative examples.
- There are six recorded assistant-teacher examples, four training and two validation. The original Phi-3-mini student remains untrained.

### Likely defence questions

**Does the profile change XGBoost probabilities?** No. It changes the required confidence through the current risk policy, while class/probabilities stay fixed. The earlier weighted blend remains a historical comparator.

**Why is Cardiff not finally selected?** This small reference-label benchmark supports exploratory comparison. Adequacy criteria and appropriate independent or supervisor review remain open.

**Are social features used by the core classifier?** The social study remains separate from the current news-based core.

**What happens if a source is invalid?** The interface reports the error and withholds substitute results. Do not silently select a different artifact.

## Soban Ahmad

22I-2460. Focus: **Decision engine, calibration, SHAP and verification**. Assigned preparation share: one-third.

### Presentation and live-demo route

- Slide 5 (50 seconds): trace offline model artifacts into the validated record and presentation layer.
- Slide 7 (45 seconds): explain candidate checking, retained rejection and separate fallback.
- Slide 8 (40 seconds): show the recorded class/probabilities and SHAP contributions on Decision.
- Slide 8 (80 seconds): Inject wrong probability, then Check explanation. Show rejection and verified fallback, then edit the candidate to clear the old verdict.
- Slide 9 (55 seconds): explain the original isotonic collapse, rank-preserving temperature correction and insufficient-confidence abstention.
- Slide 12 (30 seconds): state equal delivered responsibilities, continuing practice and later student/deployment work.

### Code to study

| File | What you should explain |
| --- | --- |
| [code/src/investify/multiclass_calibration.py](../../code/src/investify/multiclass_calibration.py) | Calibration-only temperature fit, stable softmax and raw-order preservation |
| [code/src/investify/engine.py](../../code/src/investify/engine.py) | Model, calibration and attribution orchestration |
| [code/src/investify/decision_record.py](../../code/src/investify/decision_record.py) | DecisionRecord probability, class and attribution invariants |
| [code/src/investify/explain/context.py](../../code/src/investify/explain/context.py) | build_context and complete feature evidence |
| [code/src/investify/explain/verifier.py](../../code/src/investify/explain/verifier.py) | verify and independent visible-prose/JSON checks |
| [code/src/investify/explain/pipeline.py](../../code/src/investify/explain/pipeline.py) | emit and independently verified fallback |
| [code/app/presenter_data.py](../../code/app/presenter_data.py) | calibration_diagnosis, temperature_diagnosis and source-bound diagnostics |
| [code/app/presenter.py](../../code/app/presenter.py) | decision_view, candidate_identity and explanation_view |

### Tests and report reading

- [code/tests/test_calibration_availability.py](../../code/tests/test_calibration_availability.py)
- [code/tests/test_shap_additivity.py](../../code/tests/test_shap_additivity.py)
- [code/tests/test_mideval_record_validation.py](../../code/tests/test_mideval_record_validation.py)
- [code/tests/test_mideval_verifier.py](../../code/tests/test_mideval_verifier.py)
- [code/tests/test_emit_pipeline.py](../../code/tests/test_emit_pipeline.py)
- [code/tests/test_presenter_ui.py](../../code/tests/test_presenter_ui.py)

Supporting reading:

- [report/chapters/chapter5_design.tex](../../report/chapters/chapter5_design.tex)
- [report/chapters/chapter6_iteration1.tex](../../report/chapters/chapter6_iteration1.tex)
- [Research: calibration](../technical/RESEARCH.md#executed-prediction-and-calibration)
- [Research: explanation study](../technical/RESEARCH.md#explanation-design-and-teacher-pilot)

### Facts to keep accurate

- TreeSHAP explains raw model scores. Its values are not calibrated probabilities, causes or expected returns.
- The original independent isotonic maps force Buy; new global-temperature records preserve 40/51/95 raw classes in frozen mode but nearly uniform confidence requires abstention.
- Frozen raw/temperature macro-F1 is 0.3182; original isotonic is 0.2238. The negative result stays in the report.
- Correct factual JSON does not excuse a conflicting visible sentence. A rejected candidate and verified fallback retain separate verdicts.

### Likely defence questions

**Why did isotonic calibration produce only Buy?** The original Buy map minimum exceeds the other maps' maxima. The new temperature transformation preserves raw order, but its upper-bound fit reveals weak confidence; explain the abstention guard.

**Does a consistent explanation show investment usefulness?** It shows agreement with the recorded inputs. It does not establish causality, predictive skill or user comprehension.

**Why check fallback independently?** Candidate rejection is retained and the replacement must pass its own checks. A failed template check must also surface.

**Is QLoRA complete or required for this Mid-1?** No. It remains a later proposal milestone. The current student is untrained and no student efficacy is claimed.

## Questions to practise

**What are our acceptance criteria?** Valid cases load; all available features
are inspectable; wrong prose/JSON fails; fallback is checked separately; missing
inputs show an error; edits/case changes clear the verdict; all eighteen profile
answers change allowance/confidence requirements without reversing model direction. Full proposal targets remain separate.
[Requirements](../technical/REQUIREMENTS.md).

**Where is FinBERT? Why compare Cardiff/CryptoBERT?** FinBERT still scores news.
The other models are social candidates. Crypto training does not establish
equity-tweet transfer, so both were evaluated on the same 24 MSFT reference-labelled posts.
Cardiff leads this small exploratory study; deployment selection and social
integration into NVDA remain open.

**What are the dropdowns and old dates?** Six recorded experiment versions:
temperature-corrected frozen/refit, original fresh frozen/refit and archived
Alpaca/FNSPID. Fresh means newly executed
historical work. The selected window is 2018-2023, with 186 evaluation decisions
from 29 March-21 December 2023. Prices end 29 December; five-session outcome
labels leave 21 December as the final evaluated date. No live 2026 feed exists.

**What is the risk formula?** The current R is a risk allowance, not a news weight. Thirteen Grable-Lytton scores sum to 13..47; normalized tolerance is (G-13)/34. R is the smaller capacity/tolerance allowance. Required confidence is 0.80-0.30R. Higher allowance never reverses Buy/Sell direction, and near-uniform evidence still abstains. The old weighted linear blend is only a historical comparator.

**Do tests establish a useful prediction?** They check implementation behaviour.
Clean five-session macro-F1 is 0.2843 versus random 0.3287; original isotonic cases are
all Buy; the new correction preserves classes but reveals weak confidence. Defend the implementation and negative findings without claiming
investment usefulness. [Research](../technical/RESEARCH.md).

**What does CI/CD automate?** Four Windows/Ubuntu portable/UI jobs, then a fifth
source/PDF packaging and extraction check. Hosted runs passed. It does not
train models, update market data, automatically render PDFs or provide production
hosting. [Engineering](../technical/ENGINEERING.md#cicd-and-tests).

**What proposal feedback did we address?** Contribution/problem/model clarity,
LLM benefit, technical/sentiment explanations, metrics, improved PoC, transparency
and market understanding. Evidence includes complete context, corrected checks,
failure recovery, actual studies and disclosed limits. LLM benefit, broader
integration and human comprehension remain unfinished.
[Responses](../technical/REQUIREMENTS.md#proposal-feedback).

**Where are we in the whole FYP?** At the first checkpoint, with some later
components built early. Mid-1 covers foundations/baseline/leakage/social selection
and thin UI; Final-1 engine/SHAP/divergence/service; Mid-2 prompted explainer,
NFR/parity/degraded-operation checks; Final-2 QLoRA, broader evaluation and user
acceptance. One of four iterations does not imply 25% of the effort.

## Team tasks

- Review report statements; print and sign required pages.
- Review scope, requirements/design and proposal responses with the supervisor.
- Explain assigned functions and a meaningful test boundary independently.
- Complete a timed rehearsal and projector check.
- Record ongoing practice/review, questions and submission arrangements.
- Agree model/profile adequacy criteria before final selection/deployment.

These tasks stay outside the team's technical completion percentage; the
committee still assesses understanding, coordination and live demonstration.

### Practice record

| Member/date | Files/functions reviewed | Demo/test boundary explained | Personal changes and assistance | Follow-up |
| --- | --- | --- | --- | --- |
| Ahmed | | | | |
| Rafay | | | | |
| Soban | | | | |
