# Investify working project

## Latest checkpoint - guided demo and reviewed report, 13 October 2026

Planning completion is **85.75%, approximately 86%**; see the
[unchanged-weight ledger](planning/MID_EVAL_READINESS.md). The 89-page
[unsigned working report](deliverables/Investify_FYP1_Mid_Report_Working_Draft_20261013.pdf)
is compiled and layout checked. Required institutional facts, signatures and
actual team review remain open.

The Streamlit app now opens with **Start here**, next/previous navigation,
fresh corrected experiment defaults and **three decision stages**. Explicit
fictional profiles make the separate comparator change Hold to Sell on the
21 December case while the recorded classifier stays fixed. Advanced tables,
feature detail and historical reruns are tucked into expanders. **28 focused
checks pass**, including 24 real AppTest cases; this is an overlapping scope,
not an addition to earlier suite totals. Browser visual QA remains unavailable.

Launch from the canonical project root with
`& '.\tools\start_guided_demo.ps1'`; the current session's guided server is
http://127.0.0.1:8507. Read the [six-minute guide](deliverables/DEMO_AND_DEFENCE_GUIDE.md).
The portable interface and prior ZIPs retain their own older evidence snapshots.

Slide content is reconciled, but PPTX export needs the unavailable bundled
presentation runtime. Next work is browser/projector inspection, deck export,
confirmed cover facts, genuine contributions/review/rehearsal, agreed adequacy
criteria and a matching current handover. September raw bytes/exact-lock
reproduction and broader model usefulness remain distinct unresolved limits.
All sections below describe earlier dated checkpoints unless stated otherwise.

## Completed original-classifier study - 13 October 2026

The original CryptoBERT and Cardiff candidates now complete **24/24 held-out
posts each**, without errors or missing predictions. Both publisher snapshots
and every tokenizer/config file are verified. Original Cardiff BIN serialization
preserves all 204 keys/dtypes/shapes/raw bytes; the loader retains its unused
native pooler and proves bitwise classifier-logit parity with/without it.

| Candidate | Macro-F1 agreement | Exact AI-reference agreement | Observed limit |
| --- | ---: | ---: | --- |
| CryptoBERT | 0.256410 | 15/24 (62.5%) | All 24 predictions neutral; positive/negative recall zero |
| Cardiff | 0.601587 | 16/24 (66.7%) | Positive recall 4/7; neutral 11/15; negative 1/2 |

Cardiff is the **exploratory benchmark leader**, not a deployment-approved winner.
The held-out references are AI-generated and contain only two negatives.
No independently human-validated accuracy, significance, NVDA transfer or useful
return prediction follows from these results. Adequacy criteria and genuine
review remain unclosed; deployment_selection stays null.

The Social Study view now recomputes the comparison from the actual raw
output/receipt bundles, with AI-reference/exploratory disclosures. It performs
no model inference. Latest viewer checks: **25 passes, zero skips**, including
21 Streamlit cases and four recorded-selector checks, plus five subtest checks.
Current native-pooler/loader gates have 37 passes plus nine subtests.
The earlier Cardiff refusal and failed viewer receipt remain preserved.
Repeated actual CryptoBERT outputs are identical.

[Current paired review](evidence/social_study_review_20261013.json) and
[raw comparison](code/artifacts/mid_eval/social_study_20261013_run02/comparison/comparison.json).

Readiness is now **83.75%, approximately 84%**. Original weights are unchanged;
social alone rises from 50% to 85%, while other areas retain their preceding
estimates. The report/deck still require compilation/export, visual QA and
institutional/team review. No student training or new teacher-model choice
occurred. The current assistant/Phi-3-mini/Mistral roles remain unchanged.

## Fresh scientific execution - 12 October 2026

The fresh Alpaca baseline/leakage and both calibration runs are now executed and
replayed. Read [current status](planning/CURRENT_STATUS.md) and the
[reviewed scientific summary](evidence/fresh_alpaca_science_summary_20261012_run01.json).
The five-day clean model remains weak and both calibrated modes remain all Buy.
Mid readiness is approximately 79%; institutional rendering, social comparison
and genuine team review remain open. Original September records are preserved.

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

For provider access checks, run [tools/check_market_access.ps1](tools/check_market_access.ps1)
from your normal PowerShell terminal. It preserves the existing network settings,
stores a new dated result and suggests the next step. From this project folder:

```powershell
.\tools\check_market_access.ps1
```

The new local pair now passes both paper-account and market-news authentication
(**200 OK**): [receipt](evidence/market_reacquisition_20261012/paper_auth_20261012T152909983Z/probe.json). A bounded historical check also retrieved
30 NVDA articles, five per year for 2018-2023, all with timezone-aware,
non-midnight publication times: [sample receipt](evidence/market_reacquisition_20261012/historical_news_sample_20261012T153005905951Z/probe.json).

This is a fresh sample, not the complete corpus or a scientific reproduction.
Fourteen articles have updates after creation; retain and audit `updated_at`
before treating current headline text as available at publication. Full
acquisition must use new paths and preserve the frozen historical identities.
The legacy fixed-output pull script needs adaptation before reuse.
Approved outside-sandbox networking works; default sandbox networking remains
restricted. No credentials or account response bodies are retained in receipts.

**Do not download FNSPID.** This is the user's current direction. No FNSPID
request was made in this continuation. Existing acquisition utilities are
retained as historical tooling, not the next action. FNSPID cannot replace the
precise-timestamp experiment; see the retained
[original-source review](evidence/fnspid_source_review_20261012.json).

## Old material

The former `GPT_MIDEVAL` workspace is now [../_archives/workspaces/GPT_MIDEVAL](../_archives/workspaces/GPT_MIDEVAL/). The older loose FYP files are in [../_archives/legacy_fyp_20261012](../_archives/legacy_fyp_20261012/). All 877 moved files retain their sizes and SHA256 hashes. [The archive index](../_archives/ARCHIVE_INDEX.txt) explains the backups.

The original Soban checkout at `E:\Uni_Stuff\investify_repo` remains a historical reference. Earlier code documentation and archived handoffs describe their original dates and scope. [The current handoff](planning/HANDOFF_20261012.md) supersedes their workspace instructions.

Local Git is on `main`, without a configured remote. Caches, temporary files and scratch belong under `E:\AI-Tools`; project deliverables stay here.
