# Investify demo and defence guide - 13 October 2026

The guided Streamlit demo opens on **Start here**. It uses the fresh corrected Alpaca records by default, with preserved historical experiments still selectable. Opening a screen loads recorded evidence; profile arithmetic and verifier actions run interactively. It does not train a model, fetch market data or run social-model inference.

## Launch

Work in `E:\Uni_Stuff\FYP\Investify`. The current session has a task-owned server at **http://127.0.0.1:8507** (PID 27172); its health endpoint returned HTTP 200. Browser visual QA is unavailable in this session, so no screenshot/projector review is claimed. The 28 focused checks include 24 real Streamlit AppTest cases and four recorded-study selector cases.

For a later launch, use PowerShell:

```powershell
& '.\tools\start_guided_demo.ps1'
```

The launcher uses the restored E: viewer environment, keeps temp/cache on E:, binds localhost and disables usage telemetry. It refuses an occupied port. Supply `-Port` or `-PythonExe` for another free port or a separately prepared compatible interpreter. Use Ctrl+C to stop a foreground launch. The existing port 8507 is session execution, not guaranteed unattended hosting.

## Suggested six-minute route

These times are rehearsal allocations, not observed participant timings. Keep strict-prose verification enabled.

| Step | Action | Observable result and defence point |
| --- | --- | --- |
| Start | Click **Start the walkthrough**. | Opens Decision; Next/Previous moves between the five main views while keeping selections. |
| Profile and decision, 2 min | Keep **Fresh Alpaca - frozen classifier** and **2023-12-21**. Load **Example: cautious**, then **Example: higher tolerance**. | Explicitly fictional answers produce R=0 and R=1. The separate comparator changes **Hold to Sell**. The recorded classifier stays Buy with unchanged probabilities; prototype weighting is unvalidated. Clear answers removes the profile comparator. |
| Evidence, 30 sec | Open **2. Evidence**; expand one technical and one news family. | Values, definitions and contributions belong to the selected record. Social features are absent from the classifier. Raw-score SHAP is not a probability or proof of an economic cause. |
| Explanation and check, 90 sec | Open **3. Explanation + verification**. Click **Explain selected record**. Toggle corruption and choose **Wrong displayed probability beside correct JSON**. | With no local LLM configured, the guide is labelled deterministic. The corrupted visible confidence becomes 1.00% while JSON stays correct: the verifier rejects it and emits independently checked fallback text. The candidate report and fallback status are separate. Turn corruption off to show the clean case. |
| Leakage Lab, 1 min | Click Next; keep the fresh corrected experiment. Compare the three readouts, then optionally open all results. | The clean five-day F1 is 0.2843 versus the random comparator 0.3287; the deliberate centred-window canary has lift +0.2104. The news-lag ablation does not prove a publication-time leak. Optional feature checks run nine labelled synthetic checks and detect four mutations without training. |
| Social Study, 30 sec | Click Next; show paired original-candidate scores and AI-reference disclosure. | Both complete the same 24 posts. CryptoBERT F1 agreement is 0.2564, Cardiff 0.6016. Cardiff is exploratory leader; two negative references and no independent human validation prevent a deployment-quality claim. |
| Teacher Study, 30 sec | Click Next; inspect an actual example and the four/two exports. | Six assistant-written explanations form a construction pilot. Exact serving revision is unavailable. Phi-3-mini is planned and untrained; Mistral is fallback and QLoRA belongs to the later milestone. |

## Failure paths and evidence boundary

Change session or source to demonstrate that verification follows the current record. Do not silently switch to a different record if an input is unavailable. If a study input is invalid, the view reports an error and withholds scores/downloads. Historical canary reruns are under an Advanced expander and remain subject to their actual input/environment checks.

The fresh news snapshot uses max(created_at, updated_at), which does not prove point-in-time availability. Both fresh calibration modes still produce 186 Buy decisions; a lower Brier score against the raw model does not establish useful classification or an advantage over the simple class-prior comparator. Show these limitations alongside the working explanation pipeline.

The portable historical interface remains available separately: from `code`, run `python -B scripts/serve_mideval_demo.py --port 8768` and use its printed URL. It lacks the new guided Streamlit navigation and fresh-result selectors; its older receipts certify their own snapshots.

## Before assessment

A person must inspect the browser/projector layout, rehearse the route and confirm that each member can explain their actual work. Record genuine contributions and questions; do not assign ownership from an assumed table. Confirm the assessment date and institutional cover fields. Export and inspect the twelve-slide presentation when the required presentation runtime is available. The compiled institutional report is an unsigned working draft.

Evidence: [focused UI tests](../evidence/guided_demo_ui_tests_20261013_run02.xml), [guided-demo receipt](../evidence/guided_demo_review_20261013.json), [fresh science review](../evidence/fresh_alpaca_science_summary_20261012_run01.json), [paired social review](../evidence/social_study_review_20261013.json).
