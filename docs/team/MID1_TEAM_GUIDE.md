# Investify Mid-1 team guide

This is the team's single preparation guide: documents, setup, demonstration,
speaking allocation, individual code reading, defence questions and remaining
tasks. Read the shared sections, then your own member section.

For the short presentation script, open [the five-minute demonstration handout](DEMONSTRATION.md).
The explanations below provide the deeper reference when practising or answering questions.

[Demo setup](#demo-setup) | [Live demonstration](#live-demonstration) |
[Speaking schedule](#speaking-schedule) | [Ahmed](#ahmed-javaid) |
[Rafay](#rafay-ul-haq) | [Soban](#soban-ahmad) |
[Questions to practise](#questions-to-practise) | [Team tasks](#team-tasks)

[Six case choices](#the-six-case-selections) | [Sessions](#what-a-session-means) |
[Technical evidence](#evidence-technical-analysis) | [News evidence](#evidence-news-sentiment)

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

Your demonstration proves three things: the evidence behind a historical model
output is inspectable; a complete risk profile controls the confidence needed
for a suggestion; and a wrong explanation is rejected and replaced by a checked
factual explanation. The predictor currently has weak signal. A successful demo
includes its abstention rather than presenting Buy as a useful trading call.

The route is **Overview -> Open the decision walkthrough -> Decision -> Evidence
-> Risk profile -> Explanation check**. Use the stage buttons or **Next**.

### The six case selections

A case selection is a saved experiment version. All six currently concern NVDA
and the same 186 evaluation sessions; these are not six stocks or six live feeds.
Alpaca is the market/news provider, with Benzinga headlines. FNSPID is a different
historical financial-news corpus. FinBERT still scores the headline text.

| Dropdown choice | What it contains | What it is for |
| --- | --- | --- |
| **Alpaca, multiclass calibration (frozen)** | New temperature calibration applied to the classifier/scaler kept fixed between calibration and evaluation. | **Use this for the main demo.** It preserves raw Buy/Hold/Sell classes and exposes low confidence. |
| **Alpaca, multiclass calibration (refit)** | The comparison classifier was trained again using the later available training block; the earlier calibration is transferred. | A research comparison with the frozen mode. Selecting it does not retrain anything. |
| **Fresh Alpaca, frozen classifier** | October historical rerun with the original independent isotonic probability maps. | Demonstrate the diagnosed all-Buy calibration failure if asked. |
| **Fresh Alpaca, refit classifier** | October rerun with refitted classifier and transferred original isotonic maps. | Show that the preserved refit comparison also collapsed to Buy. |
| **Archived Alpaca** | Earlier September experiment using Alpaca news. | Historical baseline and provenance comparison. |
| **Archived FNSPID** | Earlier September experiment using FNSPID news. | Original corpus baseline; timestamp precision/ticker coverage motivated the later source change. |

The first two are the current diagnostic/abstention path. The other four are
preserved historical failed-calibration comparisons; the profile policy refuses
to use them for directional suggestions. You do not need to visit all six during
the presentation. Stay on the first; explain the others from this table if asked.

"Frozen" means the fitted classifier and scaler are unchanged through calibration
and evaluation. "Refit" means a second fit used a later training block during the
offline experiment. It is a calibration-transfer comparison, not automatic
retraining each time someone chooses a session. "Fresh" means the experiment was
recently rerun on historical inputs, not that its market information is current.

### What a session means

A session is one historical stock-market trading day, not a login/chat session.
Choosing **2023-12-21** loads NVDA's saved feature values, probabilities and SHAP
contributions for that decision date. Its prediction horizon is the next **five
trading sessions**, not five calendar days. A Friday/weekend/holiday does not
count as a trading session just because a day passes.

The price study covers 2 January 2018 to 29 December 2023. Earlier data trains
and calibrates the model. The dropdown exposes the 186 evaluation decisions
from 29 March to 21 December 2023. The last decision precedes the final price
because five future trading sessions are needed to construct its outcome label.
Changing the session loads another saved case; it does not fetch a 2026 feed.

### The main demonstration, click by click

1. Open http://127.0.0.1:8507. On **Overview**, click **Open the decision walkthrough**.
2. Expand **Case selection**. Choose **Alpaca, multiclass calibration (frozen)** and **2023-12-21**. Collapse it to give the panel room.
3. On **Decision**, show the Buy/Hold/Sell probability chart and the warning. Say: "The largest raw class is Buy, but all three probabilities are around one-third. The application withholds a directional recommendation because the evidence is weak." The display's 33.3% is neither expected profit nor established accuracy.
4. Open **Evidence**. Select **Technical analysis**, then **MACD histogram**. Show the input value, definition and raw-score contribution. Say: "This value was calculated from the historical price series. SHAP shows how this fitted model used it for this case."
5. In the same Evidence step, select **News sentiment**, then **Average headline sentiment** and **Headline count**. Explain the headline-derived inputs and their model contributions using the examples below. Expand **All eleven feature values and definitions** briefly to show coverage.
6. Open **Risk profile**. Click **Cautious example**, then **Higher-tolerance example**. Point to R and required confidence: 0/80% versus 1/50%. The recorded confidence remains 33.3%, so both examples produce **Observe**. Say: "The profile changes the confidence requirement without changing the model probabilities or reversing its direction." These are labelled fictional examples. The complete form has five capacity and thirteen tolerance answers.
7. Open **Explanation check**. Click **Check explanation** on the unchanged candidate: it should be accepted. Then click **Inject wrong probability** and **Check explanation** again. The candidate says 1.00%; show **Candidate rejected** and **Verified fallback emitted**. The replacement restores **33.34%** and is independently checked.
8. Edit the candidate text after checking. Show that the old verdict no longer applies. Finish with **Restore record facts**, then **Check explanation** to leave a clean accepted state.

The central failure demonstration is step 7. Say: "The correct structured data
cannot hide an incorrect number in the text the user actually sees. We retain
the rejection and check the replacement independently."

Changing a case, text or profile invalidates its old verification. A missing
record or failed checker shows an error rather than a substituted result.

### Evidence: technical analysis

Technical analysis here means five numerical inputs derived from historical
prices and traded volume. It is an evidence-inspection panel, not a candlestick
chart or a screen that acquires new prices. The feature dropdown chooses which
input to explain; it does not select a different model or apply a trading rule.

| Feature shown | Plain meaning |
| --- | --- |
| Relative strength index | Recent price momentum on a 0-100 scale, using fourteen sessions. |
| MACD histogram | Difference between the MACD line and its signal line; a price-momentum measure. |
| Distance from the long-term average | Closing price relative to its trailing 200-session average. A value of 0.2262 corresponds to about 22.62% above that average. |
| Position within the Bollinger bands | Closing price's position between trailing volatility bands; it can fall outside the usual interval. |
| Volume trend | Average fourteen-session change in on-balance volume, which adds/subtracts share volume on rising/falling closes. |

For the recommended case, **MACD histogram is about 0.0963** and its SHAP
contribution is **+0.1874**, supporting the raw Buy score. That is not +18.74%
confidence or profit. **RSI is about 58.82**, but its SHAP contribution is
**-0.0271**, opposing the raw Buy score. A feature's market interpretation and
how this trained model used it are different facts.

Each feature panel answers three questions: what value was supplied; what that
input measures; and whether it supports, opposes or is neutral for the selected
raw class. Positive/negative SHAP means higher/lower raw score relative to the
model's reference prediction. SHAP does not establish a market cause, sum to the
calibrated probability, or validate the prediction's usefulness.

### Evidence: news sentiment

These six inputs come from financial headlines. FinBERT assigns positive,
neutral and negative text probabilities; headline polarity is positive minus
negative probability. Session aggregates and backward-looking changes then
become model inputs. The current feature join uses the most recent prior
completed news session within its allowed lookback. Do not call the displayed
headline count "all news published on the selected decision day."

| Feature shown | Plain meaning |
| --- | --- |
| Average headline sentiment | Average positive-minus-negative FinBERT polarity; a text-tone measure from -1 to +1. |
| Headline count | Number of scored headline rows in the contributing news session. |
| Short sentiment momentum | Trailing three-session average polarity minus polarity three sessions earlier. |
| Longer sentiment momentum | Trailing seven-session average polarity minus polarity seven sessions earlier. |
| Unusual news attention | Headline count relative to its trailing twenty-session mean/standard deviation. This is news volume, not traded share volume. |
| Variation in recent sentiment | Trailing five-session standard deviation of session-average polarity; variation over time, not disagreement among individual headlines. |

For the recommended case, **Average headline sentiment is about -0.1419**:
negative polarity exceeds positive polarity by about 0.142 on average. Its
SHAP contribution is **+0.0759** for the raw Buy class. Explain both honestly:
"The headline tone is mildly negative; this fitted model nevertheless uses
that input as support for its raw Buy score in this case." This is a learned
model relationship, not proof that negative news should cause buying.

**Headline count is 10** and its contribution is **-0.1312**, opposing the raw
Buy score. This is often the easiest news example to demonstrate: show the
actual count, the definition and the model's recorded response.

The purpose is to trace the prediction to the data that entered it. The current
core uses news, not the CryptoBERT/Cardiff social outputs. This panel shows
aggregated inputs; it is not a live headline feed or a source of ten original
article texts.

### How the pieces work together

During the offline experiment: price/news snapshots -> session alignment and
five technical/six news features -> XGBoost raw scores -> probability
calibration -> saved decision record containing probabilities, features,
TreeSHAP and source identities.

During your demo: load that saved record -> show its evidence -> calculate the
current eighteen-answer profile/confidence policy -> check the current visible
explanation -> independently check a deterministic replacement if needed.

The live parts are loading/validation, evidence construction, profile scoring,
confidence gating, text checking, fallback and UI-state invalidation. Model
training, price/news acquisition, FinBERT scoring and research experiments do
not run merely because a page opens. The normal explanation is a deterministic
record-grounded template. The optional configured language-model request is a
separate explicit action; leave it closed during this demo.

### Optional research screens

After the main walkthrough, **Recorded experiments** opens the research views.
These are useful for questions; the core demonstration does not depend on
showing every view.

| Screen | What to show and say |
| --- | --- |
| Leakage audit | Clean macro-F1 0.2843, random comparator 0.3287, deliberate centred-feature lift +0.2104. "The deliberately future-looking control exposes an evaluation fault; its inflated score is invalid." The feature-boundary button runs labelled synthetic checks, not model training. |
| Sentiment comparison | CryptoBERT/Cardiff on the same 24 held-out MSFT references, not NVDA classifier inputs. "FinBERT remains the news model; social candidates are being compared separately." |
| Teacher pilot | Six recorded explanatory examples with train/validation exports. "This demonstrates example construction and checking; Phi-3-mini has not been trained." |
| Design | Code-linked architecture and requirements. Explain the current data/profile/verifier path; later product integrations remain future work. |
| GitHub Actions | The workflow's four Windows/Ubuntu test jobs followed by verified source/PDF delivery. This automates checks and artifact delivery; it does not deploy a production trading service. |

A concise opening line: "We will load one historical decision, inspect its
price/news evidence, calculate the risk confidence requirement, and deliberately
break an explanation to demonstrate rejection and independently checked recovery."

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
