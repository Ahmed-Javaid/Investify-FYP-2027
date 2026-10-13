# Investify Mid-1 demo and defence guide - 13 October 2026

The rebuilt Streamlit UI opens on **Overview** and executes one workspace at a time. The four Walkthrough steps keep the selected record and profile. Recorded model evidence is distinct from live profile arithmetic and explanation checking.

## Launch

Current local session: **http://127.0.0.1:8507**. The task-owned server was restarted for the light theme (launcher PID 30916) and its health endpoint returned HTTP 200. Browser/projector review remains pending. For another launch from the project root, use `& '.\tools\start_guided_demo.ps1'`. The launcher keeps caches/temp on E:, disables telemetry and refuses an occupied port. Use `-Port` or `-PythonExe` when needed, and Ctrl+C for a foreground launch. Session hosting is not guaranteed unattended.

## Four-minute live route

These are planned rehearsal allocations, not measured participant timings. In the Beamer deck, pause at slide 8. From Overview choose **Open the decision walkthrough**. Leave **Fresh Alpaca - frozen classifier** and **2023-12-21** selected inside the collapsed Case selection control.

| Step | Action | Observable result and defence point |
| --- | --- | --- |
| Decision, 40 sec | Inspect the class, probability chart and largest contributions. | The retained class is Buy. TreeSHAP values explain raw scores, not calibrated probabilities, causality or returns. Both fresh calibration modes remain all Buy. |
| Evidence, 40 sec | Choose Technical analysis and one feature, then News sentiment and one feature. | Each has its recorded value, definition and contribution. All eleven inputs are available in details. Social features remain separate. |
| Risk profile, 60 sec | Click **Cautious example**, then **Higher-tolerance example**, then **Clear profile**. | Explicit fictional R=0 and R=1 profiles change the separate comparator from Hold to Sell while XGBoost stays Buy. Clear removes the profile result. Eight custom answers are optional and have no defaults. Suitability/performance remain unvalidated. |
| Explanation check, 80 sec | Click **Inject wrong probability**, then **Check explanation**. Edit the text after checking. | Visible confidence becomes 1.00% beside correct JSON. The verifier rejects the candidate and independently verifies fallback. Editing hides the old verdict. A changed source/session resets the candidate. |

The primary UI has twelve passing actual widget cases. The combined 40-test receipt includes those twelve, 24 preserved legacy UI cases and four study selectors. Do not call all forty new-UI tests or sum overlapping scopes as research evidence.

## Optional research and design questions

On **Experiments**, select one study: Leakage audit, Sentiment comparison or Teacher pilot. The clean five-session F1 is 0.2843 versus random 0.3287. The deliberately centred canary lift is +0.2104 and is a labelled leakage failure. Original CryptoBERT/Cardiff agreement is 0.2564/0.6016 on the same 24 AI references, with only two negative labels. Cardiff leads the exploratory benchmark while final selection remains open. The teacher pilot contains six actual assistant prose examples, four training and two validation. Phi-3-mini remains untrained.

On **Design**, connect diagrams to concrete functions using [the code walkthrough](CODE_WALKTHROUGH.md). Generated diagrams/commits do not establish a member's authorship or understanding.

## Failure and recovery

An invalid/unavailable input shows an error and withholds replacement classes or study scores. A profile session in the scaling-development block refuses comparator scoring. Candidate and fallback verdicts stay separate. The clean template button restores recorded facts. Never repair a failure by silently selecting another artifact or by changing frozen research labels.

The portable historical interface remains separately available from `code`: `python -B scripts/serve_mideval_demo.py --port 8768`. It retains its older scope. It does not provide the rebuilt Streamlit layout.

## Before assessment

Inspect the real browser/projector layout and rehearse within the handbook's recommended fifteen minutes. Each member needs an actual file/function walkthrough and contribution record. Confirm cover metadata, assessment date and applicable review/approval details. The [twelve-slide Beamer PDF](Investify_FYP1_Mid_Presentation_20261013.pdf) and [revised report](Investify_FYP1_Mid_Report_Handbook_Revision_20261013.pdf) are compiled and reviewed working drafts.

Evidence: [new UI delivery](../evidence/presenter_revision_delivery_20261013.json), [combined UI scope](../evidence/presenter_and_legacy_ui_tests_20261013.xml), [fresh science](../evidence/fresh_alpaca_science_summary_20261012_run01.json), [paired sentiment](../evidence/social_study_review_20261013.json).
