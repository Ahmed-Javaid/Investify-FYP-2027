# Investify proposal feedback and action register

Project: **F26-003-Investify**

Proposal decision: **Approved with Minor Modifications**

The proposal panel requested clearer contributions, a better account of how the LLM helps users, refined problem and model descriptions, explicit evaluation metrics, an improved PoC, greater user transparency, and stronger stock-market understanding. The actions below connect those requests to evidence for the FYP-1 mid evaluation. Existing code supports several actions, but none is recorded as closed until the corresponding revision or demonstration is complete.

Feedback was supplied by the project team on 11 October 2026. The original decision date was not supplied with this text. Older project files use F26-003-QuantamentalAI; new assessment material should use the identifier above.

## Current working evidence - 12 October 2026 continuation

The supplied feedback below is unchanged. The original proposed status column is historical; use this current mapping. Every action still needs applicable team/supervisor review and genuine owners/dates. No action is marked institutionally closed by a passing engineering test.

| ID | Current implementation/evidence | Remaining closure |
| --- | --- | --- |
| PF-01 | [Problem/contribution](../../deliverables/PROBLEM_AND_CONTRIBUTION.md), architecture and closest-work comparison distinguish team-built controls/checking from external models. | Review novelty/comparison claims and align the rendered report/presentation. |
| PF-02 | Local adapter/fallback and fair deterministic comparators exist; six actual assistant-teacher explanations are recorded. [Teacher pilot](../../deliverables/ASSISTANT_TEACHER_PILOT.md). | No real student inference, additional explanatory content or comprehension benefit is established; same sentence-line multisets constrain the pilot. |
| PF-03 | Five technical/six news values, attributions, exact maintained definitions, family totals, missing/zero evidence and raw-score scope are implemented and checked in prose/JSON. [Traceability](../../deliverables/REQUIREMENTS_TRACEABILITY.md). | Integrated social evidence is absent; unrestricted wording and human understanding remain unverified. |
| PF-04 | Revised educational retail-investor problem statement is in the introduction and contribution material. | Team/supervisor agreement and final source/render consistency. |
| PF-05 | Current assistant teacher, planned original Microsoft Phi-3-mini student, Mistral fallback, historical FinBERT, and pending CryptoBERT/Cardiff candidate study are disclosed. Qwen configurations are inactive optional history. | Exact student checkpoint/runtime and actual candidate selection; teacher exact serving identity remains unavailable. No withdrawn variants are reinstated. |
| PF-06 | Scoped prediction/calibration/sentiment/explanation/user/runtime matrix and dated engineering receipts exist. The actual social pilot has 200 acquired posts, 117 usable AI references and 24 held-out references. | Candidate metrics are null; single-pass reliability/human validation, predictor reproduction, user study and student quality remain unmeasured. |
| PF-07 | Corrected payload-over-prose checking, retained rejection evidence, verified fallback, real local interfaces and structural re-run refusal. Portable source/profile retry and request ownership have twelve controlled Node handler cases. [Demo/defence guide](../../deliverables/DEMO_AND_DEFENCE_GUIDE.md). | Supervisor live demonstration, browser review, honest repository/CI evidence and student defence. Node fixtures are not a live model or browser review. |
| PF-08 | Historical/constant-Buy/news-only/profile limitations and candidate/fallback states are displayed and widget-tested. Portable edits/failed-source recovery discard obsolete results while preserving independent current output; [scoped client evidence](../../deliverables/REQUIREMENTS_TRACEABILITY.md). | Full retail-user journey and actual comprehension/suitability evidence; no trading execution or institutional closure. |
| PF-09 | Referenced domain/research notes relate indicators, news, market timing and profile distinctions to design. The guide explains SHAP units and limitations. | Independent content review and each member's genuine defence; no comprehension certification is implied. |

The social methodology changed under user direction from the proposal's hand-label assumption to recorded AI reference annotation. The active teacher changed from an unspecified open-weight provider to this assistant session; factual JSON targets are deterministically assembled as disclosed hybrid supervision. Original proposal commitments remain preserved. QLoRA and the three-way student comparison remain later milestones.

## Original panel feedback

The following text is preserved as supplied:

> Project: F26-003-Investify
>
> Decision: Approved with Minor Modifications
>
> Comments / Recommended Modifications:
>
> The project is alright; however, they need to make their contribution more apparent. Get more information on how the LLM will actually help. Ideally, the LLM should explain all aspects of technical and sentiment analysis so the user can know why a decision is proposed. Refinement of the problem statement and the kinds of pre-trained models being used is required. Students need to identify their evaluation metrics and clearly mention their contribution. POC needs improvement; add a clear contribution in addition to temporal leakage. Overall, the presentation and work demonstration were good. Greater attention should be given to ensuring transparency for the user throughout the system. Since the system involves financial transactions, users must be fully informed about its limitations, potential risks, and implications at every stage of the process. Need to explore and gather information about the stock market, and understand the underlying mechanisms and factors that drive it.

## Actions and closure evidence

Action IDs organize this feedback; they are not the university handbook's official Form 10 numbering. Owners and dates must be agreed with the team and supervisor before they are represented as commitments.

| ID | Panel request | Action for the mid evaluation | Evidence needed to close | Original status at receipt (superseded above) |
| --- | --- | --- | --- | --- |
| PF-01 | Make the contribution more apparent. | Rewrite the contribution statement and show which components the team designs, implements, and evaluates. Identify the harness and explanation verifier separately from the pretrained/library inputs. | Consistent contribution statement in report and slides; architecture identifies the team-built components; comparison with closest relevant work supports the claimed difference. | Open. Contributions are already described in the proposal, but the panel found the presentation insufficiently clear. |
| PF-02 | Explain how the LLM will actually help. | Specify its inputs, outputs, permitted claims, user benefit, verification/fallback path, and limitations. Compare the intended LLM explanation with the existing template. | LLM design and worked example; a testable evaluation plan; implementation status disclosed. A live prompted pilot is a proposed mid increment, not an already agreed deadline commitment. | Open. Main repo currently has a template and verifier; no language model. |
| PF-03 | Explain technical and sentiment analysis so users understand why a decision is proposed. | Design explanations that cover technical signals, available sentiment signals, their contributions, agreement/conflict, uncertainty, and data age. Provide feature detail beyond the top-k summary when requested. | A worked decision showing both technical and sentiment explanations; traceability to values and attributions; missing social data identified; comprehension task and claim-verification results. | Open. Current template lists top-k feature values and SHAP contributions, without the full proposed explanatory behavior. |
| PF-04 | Refine the problem statement. | Describe the retail-investor task, difficulty interpreting signals, need for understandable and faithful explanations, and leakage risk. Define the educational advisory boundary. Avoid unsupported claims about all existing tools or guaranteed predictive skill. | Revised problem statement aligned with objectives, user tasks, scope, and evaluation. | Open. Proposed wording appears below. |
| PF-05 | Refine the kinds of pretrained models being used. | Create a model/component inventory with checkpoint, task, domain, inputs, outputs, selection rationale, adaptation, evaluation, license/access conditions, and implementation status. | Inventory in report; source references; actual configured checkpoint identifiers; social-model selection evidence; final LLM and teacher choice or explicit pending status. | Open. FinBERT is implemented; CryptoBERT is a candidate; Phi-3-mini is in the proposal; the teacher is unspecified. |
| PF-06 | Identify evaluation metrics. | Publish one evaluation matrix for prediction, calibration, sentiment, explanation faithfulness, leakage controls, system performance, and user comprehension. State datasets, splits, comparators, thresholds, and result status. | Matrix in report and slides; measured results where implementation exists; future measurements labelled as planned; limitations such as constant-Buy calibration disclosed. | Open. Several metrics exist in proposal/code but need a consistent account. |
| PF-07 | Improve the PoC and demonstrate a contribution beyond temporal leakage. | Show the explanation-verification contribution through the live interface, including corruption and fallback. Show a meaningful change since the proposal PoC, with dated code/test evidence. | Live demo and tagged version; factual corruption rejected; grounded fallback shown; progress since proposal explained. If an LLM is shown, label and evaluate its actual generations. | Open. Verifier and corruption demo already exist, but their existence alone does not demonstrate progress since the proposal. |
| PF-08 | Ensure transparency about limitations, risks, and implications throughout the system. | Explain the advisory boundary, data coverage/freshness, model uncertainty, actual risk-profile effect, sentiment limitations, verification limits, and degraded/fallback states at the relevant user steps. | UI review across onboarding, selection, recommendation, explanation, follow-up, and failure paths; test cases and comprehension checks; consistent report and slides. | Open. Current repo discloses model degeneration and display-only risk, but the full journey is unfinished. |
| PF-09 | Understand the stock market and its underlying mechanisms and drivers. | Prepare referenced domain research connecting market mechanics, corporate events, macro/company factors, technical indicators, news/social sentiment, volatility, regimes, and prediction horizons to design decisions. | Project-specific research section, decision log, worked examples, and each member's ability to explain assumptions and limitations. | Open. Existing background must be reviewed and expanded against this request. |

## Proposed problem statement

A retail investor evaluating a company must interpret price indicators and a large volume of financial news and social discussion. A Buy, Hold, or Sell label alone does not explain which signals influenced it, how conflicting signals were handled, how uncertain the result is, or whether it fits the investor's risk constraints. A fluent explanation can also misstate the values or contributions behind a prediction, while an evaluation using information unavailable at decision time can overstate model quality.

Investify addresses these problems through a temporally controlled evaluation pipeline and understandable explanations tied to recorded model inputs and attributions. It will show the supporting evidence, uncertainty, data limitations, and effect of the user's risk profile. Its outputs are educational and advisory; predictive usefulness must be evaluated against explicit baselines, and the system does not execute financial transactions.

This wording is a proposed revision for the next report/proposal update, not an edit already applied to the Word documents.

## Proposed explanation contribution and LLM role

The contribution beyond temporal leakage is a **claim-verification and fallback process for user-facing decision explanations**. The LLM translates a structured decision record into understandable language; the team-built verifier checks supported numeric, directional, rank, and feature-name claims against that record. The controlled evaluation measures both faithfulness and whether users understand the evidence and limitations.

Using an LLM or generating text from SHAP is not, by itself, a claim of novelty. The research comparison must establish what the verification design, error handling, and evaluation add beyond the closest prior work.

The proposed path is:

1. Read the decision record: company, session, horizon, probabilities, feature values, available sentiment features, SHAP contributions, model/data references, and the risk profile's actual effect.
2. Explain the technical evidence in ordinary language, including conflicting indicators and the distinction between feature values and their contribution to this prediction.
3. Explain the available sentiment evidence: source/register, polarity, volume, momentum, and any news/social disagreement. The present news-only implementation must not claim social evidence exists.
4. Explain why the recorded decision was selected, how uncertain it is, and what the data and model do not establish.
5. Verify factual claims; on failure use the documented retry/fallback policy. General educational descriptions of indicators need referenced domain content and separate review: the numeric verifier alone cannot certify every market explanation.
6. Let the user inspect additional feature details and ask grounded follow-ups without supplying invented causes or certainty.

Coverage of both technical and sentiment aspects is a design requirement from the feedback. It does not mean every feature must be described as decisive. A feature can be present, missing, or have little influence; those states must be represented faithfully. SHAP explains the model's behavior and does not prove what caused a market price move.

The existing deterministic template is the initial comparison baseline. A prompted LLM pilot could demonstrate the requested user benefit at mid; the panel feedback does not explicitly require completing QLoRA, the teacher/student comparison, or the whole language-model research program at this milestone. Any schedule acceleration must be agreed and recorded.

## Evaluation matrix to refine in the report

The panel asked us to identify metrics; it did not prescribe the thresholds below. Existing thresholds are project commitments from the proposal/code. New study measures are labelled as proposed.

| Area | Metrics or checks | Comparison and current boundary |
| --- | --- | --- |
| Prediction | Macro-F1, per-class precision/recall, lift over stratified-random baseline, comparison with the transparent linear baseline. | Held-out purged walk-forward evaluation. Current NVDA spike supports no predictive-skill claim; keep the reported null result and decision-class distribution visible. |
| Calibration | Brier score and reliability curve, accompanied by decision-class distribution. | Before/after calibration on the stated folds. Improved Brier does not resolve the current constant-Buy behavior. |
| Sentiment | Original proposal: roughly 200 hand-labelled posts. Current user-directed method: 200 acquired posts, 117 usable AI references and 24 held-out posts; candidate macro-F1/per-class agreement/confusion matrix pending. | CryptoBERT versus a social-domain alternative; retain reference/candidate provenance and exclusions. Scores against AI labels are not independently human-validated accuracy. News-only fallback remains a proposal branch if neither transfers adequately. |
| Explanation faithfulness | Numeric fidelity >= 0.98; directional consistency >= 0.95; claim recall >= 0.80; unverifiable-claim rate <= 0.15; closed-vocabulary/rank checks; corruption detection and false positives. | Score raw generations as well as emitted outputs. Existing evidence is template/fixture-based; future LLM outputs require their own evaluation. Define recall consistently before comparing implementations. |
| Leakage controls | Alignment/session tests, backward windows, fold-local scaling, controlled leak detection, and control lift/confidence intervals. | Include deliberately broken configurations and distinguish a leak, chance-level behavior, and below-chance predictive performance. Reconcile Gate A wording with the newer spike findings. |
| User understanding | Correct interpretation of the decision, leading driver, uncertainty, and limitations; task completion, time, assistance, and errors. | Existing acceptance-study plan supplies these measures. A small early check is proposed for mid; the full participant study remains in the later schedule. |
| System performance | Applicable latency, memory, scoring-throughput, and reproducible-install checks from the NFRs. | Record the environment and measured scope. Full NFR validation is a later proposal milestone; do not present planned bounds as measurements. |

## Effect on the mid evaluation checklist

In addition to the official live demo, report, requirements/design, tests, GitHub CI/CD, and contribution evidence, the mid material must now explicitly address PF-01 through PF-09:

- A revised problem and contribution statement.
- An LLM design and worked technical/sentiment explanation, with implementation status and a comparison/evaluation plan.
- A clear model/component inventory.
- An explicit evaluation matrix and current results.
- An improved PoC demonstrating the contribution beyond leakage and progress since proposal.
- Transparency requirements and corresponding UI/test evidence.
- Referenced stock-market research that supports actual design choices.
- This action register with agreed owners, target dates, status, and evidence links added as work completes.

The original first-mid engineering commitments remain: ingestion, calendar mapping, technical indicators, news sentiment, social-model selection, an end-to-end linear baseline, leakage tests/mutation demonstration, a working interface slice, and baselined requirements/design. Feedback expands the required clarification and evidence; it is not an instruction to treat every later FYP deliverable as already due.

The feedback's reference to financial transactions needs explicit scope clarification. The existing proposal excludes trading, order execution, and brokerage integration. Keep that boundary clear while explaining that users could still make real financial decisions based on what they read. Do not infer a new transaction-execution requirement from this sentence.

## Source files

- [Current proposal](../Investify_Proposal_Full.docx).
- [Official mid rubric](FYP-1-Mid-Assessment-Guidelines-and-Rubrics.pdf).
- [Official report template](F26_FYP1_Mid_Report_LaTeX_Complete.zip).
- [Preserved historical implementation findings](../../code/POC_REPORT.md).
- [Current isolated explanation code](../../code/src/investify/explain/).
- [Project status and file map](../PROJECT_STATUS.md).

This register records the supplied decision and proposed responses. It does not mark the modifications as completed, change the approved trading boundary, choose new checkpoints, or assign new team responsibilities.
