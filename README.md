# Investify working project

**Work here: `E:\Uni_Stuff\FYP\Investify`.** This is the consolidated project for F26-003-Investify. Start with [current status](planning/CURRENT_STATUS.md) and the [document guide](deliverables/README.md).

## Folder guide

| Folder | What belongs here |
| --- | --- |
| [code](code/) | Active Python implementation, app, tests, configuration and frozen research artifacts. Run code commands from this folder. |
| [report](report/) | Current institutional mid-report draft. Edit `main.tex` and `chapters/`. |
| [deliverables](deliverables/README.md) | Current working write-ups, slide outline, demo preview, evidence PDFs and dated review bundles. |
| [planning](planning/CURRENT_STATUS.md) | Current status, scope, readiness, work plan and continuation instructions. |
| [sources](sources/) | Preserved proposals, official assessment/template material and research inputs. Reference originals rather than overwriting them. |
| [evidence](evidence/) | Test results, hashes, provenance, execution failures and verification receipts. Dated receipts prove their own snapshots. |
| [tools](tools/) | Project maintenance, reproduction, validation and packaging utilities. |
| [original_materials](original_materials/) | Historical copies retained during integration. |

## Which version to open

| Purpose | Use this | Status |
| --- | --- | --- |
| Mid report | [report/main.tex](report/main.tex) | Current editable LaTeX draft; compilation and review remain open. |
| Mid presentation | [presentation_outline.json](deliverables/presentation_outline.json) | Current twelve-slide content and speaker notes; PowerPoint export remains open. |
| Proposal | [Investify_Proposal_Full.docx](sources/Investify_Proposal_Full.docx) | Latest preserved full proposal, revised 10 September. It is a proposal reference, not the mid report. |
| Concept | [Investify_Concept.docx](sources/Investify_Concept.docx) | Latest preserved condensed proposal. September PDF exports predate these Word revisions. |
| Assessment requirements | [Official mid rubric](sources/Mid_Eval/FYP-1-Mid-Assessment-Guidelines-and-Rubrics.pdf) | Institutional source. The supplied report-template PDF is a template example. |
| Demo and defence | [DEMO_AND_DEFENCE_GUIDE.md](deliverables/DEMO_AND_DEFENCE_GUIDE.md) | Walkthrough of implemented behaviour and limitations. |
| Progress and next work | [CURRENT_STATUS.md](planning/CURRENT_STATUS.md) | Current starting point; use dated logs for supporting history. |

## Run the local demo

From `code`:

```powershell
python -B scripts/serve_mideval_demo.py --port 8768
```

Open `http://127.0.0.1:8768`. This runs verification over saved historical decision records. The isolated viewer runtime is `E:\AI-Tools\Temp\investify-ui-py311`; dependency instructions are in [code/README.md](code/README.md).

Alpaca keys belong in Git-ignored `code/.env` as `ALPACA_API_KEY` and `ALPACA_API_SECRET`. The bounded acquisition tool now reads that file; inherited shell values take precedence. Never copy the keys into reports, bundles or chat.

For the current network blocker, run [tools/check_market_access.ps1](tools/check_market_access.ps1)
from your normal PowerShell terminal. It preserves the existing network settings,
stores a new dated result and suggests the next step. From this project folder:

```powershell
.\tools\check_market_access.ps1
```

## Old material

The former `GPT_MIDEVAL` workspace is now [../_archives/workspaces/GPT_MIDEVAL](../_archives/workspaces/GPT_MIDEVAL/). The older loose FYP files are in [../_archives/legacy_fyp_20261012](../_archives/legacy_fyp_20261012/). All 877 moved files retain their sizes and SHA256 hashes. [The archive index](../_archives/ARCHIVE_INDEX.txt) explains the backups.

The original Soban checkout at `E:\Uni_Stuff\investify_repo` remains a historical reference. Earlier code documentation and archived handoffs describe their original dates and scope. [The current handoff](planning/HANDOFF_20261012.md) supersedes their workspace instructions.

Local Git is on `main`, without a configured remote. Caches, temporary files and scratch belong under `E:\AI-Tools`; project deliverables stay here.
