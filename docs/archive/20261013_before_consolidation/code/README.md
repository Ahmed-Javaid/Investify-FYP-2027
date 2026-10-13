# Investify code and demo

Run the recorded Mid-1 demo with Git and Python 3.11. Initial package installation needs internet. No GPU, API keys or publisher-model downloads are needed for this viewer.

```powershell
git -c core.autocrlf=false clone https://github.com/Ahmed-Javaid/Investify-FYP-2027.git
cd Investify-FYP-2027
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r code\requirements-demo-runtime.txt
.\.venv\Scripts\python.exe -B tools\restore_ci_checkout.py
git config core.autocrlf true
.\.venv\Scripts\python.exe -m streamlit run code\app\streamlit_app.py --server.address=127.0.0.1 --server.port=8507 --browser.gatherUsageStats=false
```

Open http://127.0.0.1:8507 on your own laptop and keep the terminal running. For an existing clone, use `git pull`, restore the reviewed checkout bytes again, and relaunch. Reinstall the pinned requirements when they change. The prepared local E: runtime can instead use `tools/start_guided_demo.ps1` from the project root.

<!-- MID1_BROWSER_CHECKPOINT_START -->
## Current technical Mid-1 completion - 13 October 2026

**100% technical Mid-1 completion**. Completion now means working code, a complete report, working CI/CD and required Mid-1 modules. The earlier **84.25%** mixed preparation estimate is historical and no longer governs current completion. Its original weights and receipts remain preserved in planning history and the archived navigation snapshot.

- [Current report](../deliverables/Investify_FYP1_Mid_Report_Technical_Completion_20261013.pdf): **102 pages**, coordinator omitted, Fall 2026 and report date 11 October 2026 retained. Current source/PDF/render hashes and visual review match.
- [Current presentation](../deliverables/Investify_FYP1_Mid_Presentation_Technical_Completion_20261013.pdf): **12 reviewed LaTeX/Beamer slides**, editable source and synchronized member notes.
- [Required modules and technical scope](../deliverables/MID1_TECHNICAL_COMPLETION.md): ingestion/calendar/features, baseline/leakage, sentiment comparison, decision/calibration/SHAP, profile comparator and explanation/fallback interfaces have execution evidence.
- [CI/CD status](../deliverables/CI_CD_STATUS.md): cross-platform validation followed by gated, extraction-verified source/PDF artifact delivery. [Hosted CI/CD run](https://github.com/Ahmed-Javaid/Investify-FYP-2027/actions/runs/38426650755) passes all five jobs and produces the verified delivery artifact.
- [Equal member packets](../deliverables/MEMBER_PREPARATION_PACK.md): one-third responsibility, four primary slides and five planned speaking minutes each.
- [Team todo](../deliverables/MID1_TEAM_TODO.md): printing/signatures, supervisor review, code walkthrough and rehearsal/projector check remain outside this percentage.

[Verified source archive](../deliverables/archive/20261013/investify_mid1_technical_review_20261013.zip): 792 files, source snapshot **ddf435d**, 168 portable tests, 62 HTTP checks and 372 records validated. Later navigation receipts are a separate increment.

Scientific limits remain explicit: weak prediction, all-Buy calibration, AI-reference sentiment, no measured user benefit and untrained student. QLoRA and production hosting are later milestones. No human review or signature is inferred.
<!-- MID1_BROWSER_CHECKPOINT_END -->

## Implementation

| Path | Purpose |
| --- | --- |
| `app/streamlit_app.py`, `presenter.py` | Overview, decision walkthrough, experiments and design. |
| `src/investify/explain/` | Evidence context, independent claim verification and checked fallback. |
| `src/investify/risk_profile.py`, `risk_comparator.py` | Explicit prototype profile and separate historical comparator. |
| `src/investify/engine.py` | XGBoost, isotonic calibration and TreeSHAP record emission. |
| `src/investify/harness/`, `features/`, `ingest/` | Temporal alignment, causal features, labels and leakage experiments. |
| `artifacts/` | Preserved recorded outcomes, scientific traces and source-bound study evidence. |
| `tests/` | Engineering, UI, source/delivery and scientific checks with distinct scopes. |

The viewer loads recorded predictions; profile arithmetic and explanation checking run live. Fresh calibrated modes remain all Buy. The social study measures agreement with small AI-labelled references; the student is untrained. Full FYP work includes integration, useful model evaluation, student inference/adaptation, production hosting and participant acceptance.

Fresh acquisition/inference needs separate data, credentials, weights and scientific dependencies. Keep `.env`, caches and publisher weights outside committed source. Do not use old `make data` commands as the groupmate demo setup.

The [original PoC report](POC_REPORT.md), [increment documentation](docs/mideval_increment.md), [comparator details](docs/risk_comparator.md) and [social study protocol](docs/social_selection.md) remain available. The old README is preserved under `../deliverables/archive/20261013/navigation_before_cleanup/code/README.md`.
