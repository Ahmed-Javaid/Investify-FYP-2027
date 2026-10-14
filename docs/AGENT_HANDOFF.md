# Investify agent handoff

Start here for development continuation. Team preparation is in
[TEAM_GUIDE.md](TEAM_GUIDE.md), with the short click script in
[DEMONSTRATION.md](DEMONSTRATION.md). Technical references are the sibling
[ENGINEERING.md](ENGINEERING.md), [RESEARCH.md](RESEARCH.md) and
[REQUIREMENTS.md](REQUIREMENTS.md); every guide now sits flat in `docs/`. Keep
the root README short and update the existing guides.

## Current state

<!-- MID1_BROWSER_CHECKPOINT_START -->
The **v1.1 audit revision** follows the official ten-chapter template and addresses PF-01--PF-09 with explicit implementation/evaluation status. Current report: 95 pages; deck: 14 slides, 660 planned seconds. Both local CI jobs pass: 183 portable tests, 7 guards, and UI scopes 24/19/4. The 23 requirements have 29 passing selected anchors; 9 delivery guards pass. Implementation commit 8bd6e09 was pushed in PR 1; Actions run 38487127348 passed all five jobs. The final delivery update and mid1-v1.1 tag resolve the revised release source. Older hosted runs certify their own earlier snapshots.
[Selected delivery](../deliverables/current_delivery.json) · [Local evidence receipt](../evidence/mid1_v11_20261014_final_evidence_run01/job_receipt.json) · [UI receipt](../evidence/mid1_v11_20261014_final_ui_run01/job_receipt.json).
<!-- MID1_BROWSER_CHECKPOINT_END -->

- Repository: `E:\Uni_Stuff\FYP\Investify`; remote: https://github.com/Ahmed-Javaid/Investify-FYP-2027. Code commands run from `code`.
- Current reviewed report: 95 pages; presentation: 14 slides. [Delivery configuration](../deliverables/current_delivery.json) selects current review/custody receipts.
- Editable entries: [report/main.tex](../report/main.tex), [presentation/main.tex](../presentation/main.tex). Removing unused assets did not alter PDF bytes or actual compiler inputs.
- Demo URL: http://127.0.0.1:8507 while the server runs. Check health before claiming it is running; launch with [start_guided_demo.ps1](../tools/start_guided_demo.ps1).
- The compact groupmate ZIP contains report, slides, rubric, demonstration handout and preparation/technical guides. Members obtain source from GitHub.

## Scope and remaining work

Temperature calibration preserves raw classes but yields near-uniform confidence,
so the primary viewer abstains. Grable-Lytton scoring uses thirteen tolerance and
five capacity answers; the confidence gate preserves raw direction/probabilities.
The four older failed-calibration cases remain inspectable but cannot produce
directional suggestions.

FinBERT scores headline tone; CryptoBERT/Cardiff are a separate social comparison.
Reference labels, model bytes and frozen source identities remain unchanged.
Template/checker use the policy-aware v5 grammar; retained archive_v4 sources keep original teacher packet replay tested. The frozen explanation context module must stay byte-identical for the recorded
teacher packet to replay. Current assistant is teacher; original Phi-3-mini is
the untrained planned student; Mistral is fallback. New experiments need separate
identities.

Remaining whole-FYP work: divergence integration, population-specific profile
validation, useful prediction/calibration evaluation, student inference and QLoRA
comparison, performance/parity/degraded-operation checks, production hosting and
participant acceptance. Rehearsal, projector checks, signatures and supervisor
review are team tasks outside the technical completion percentage.

Confirmed metadata: FYP-1 Mid-Evaluation, Fall 2026; actual submission date and batch/session have not been supplied and remain blank;
Ahmed Javaid 22I-2530, Rafay Ul Haq 22I-2520, Soban Ahmad 22I-2460; equal delivered
contributions confirmed by the user; supervisor Mr. Irfan Ullah; no co-supervisor;
coordinator omitted. Keep actual execution dates separate. Do not infer student
understanding, institutional approval or predictive usefulness from tests.

Meeting evidence was requested before compilation. No records were supplied;
Appendix F has an explicitly empty meeting form. The latest user direction is to leave unconfirmed fields blank, without HUMAN todo markers.
Incorporate actual details if later supplied.

## Tools and validation

- `package_groupmate_handover.py`: compact document/practice ZIP using current reviewed PDFs and the preserved rubric.
- `package_source_handover.py`, `verify_source_handover.py`: source/PDF packaging and actual isolated extraction validation.
- `code/scripts/run_mid1_ci.py`, `tools/run_mid1_delivery.py`: portable/UI CI and verified hosted artifact delivery.
- `verify_requirements_traceability.py`: requirements and test/source anchors.
- `verify_documentation_layout.py --check-preservation`: links, reviewed PDF/source identities and the cleanup's 347 protected files.
- `write_ci_checkout_inventory.py`: refresh cross-platform reviewed identities after final edits and new tracked receipts.
- `update_mid1_technical_status.py`: machine status and this handoff's status block.
- Build/render/publication tools remain active; retired generators must not recreate obsolete pages.

Preserve exact tracked `code/source_revision.json` bytes. CI temporarily declares
source identity and restores them; run local shared CI jobs sequentially because
they use this same file. Hosted delivery requires four passing, clean, same-commit
matrix receipts. See [Engineering](ENGINEERING.md) for commands and scope.

## Cleanup and storage

The user explicitly approved removal after a local commit. Checkpoint **5f6b6ff**
contains the short handout and approval record before deletion. The
[cleanup audit](../evidence/workspace_cleanup_20261014.json) records 1,317
removed files, approximately 405.8 MiB, 348 published Git recovery identities and
347 unchanged protected files. Current references, six-case data and scientific
inputs remain. Obsolete archives, duplicate exports and retired notes are gone;
tracked earlier versions remain in Git history. This approval supersedes the
old requirement to keep obsolete ZIPs/archives locally.

A second approved pass on 15 October 2026 removed the documentation and receipt
clutter that survived the first one. The six consolidated guides moved flat into
`docs/`, `code/CLAUDE.md` folded into [AGENTS.md](../AGENTS.md), and 311
superseded artifacts left `evidence/` and `deliverables/` for one
[artifact index](../evidence/receipt_index.json) that records each one's name,
date, schema, result and SHA-256 against commit `5caa00c`: 243 flat single-use
receipts, then nine superseded CI run directories (68 files, 6.98 MiB, including
four copies of one 2.04 MiB `standalone-preview.html`). `evidence/` went from 266
flat files to 26 plus five live directories. `deliverables/` also lost the two
dead intermediate `*_v1_1_20261014` PDFs between the protected `*_Revised` pair
and the current `*_release` pair, and two stale Git-ignored groupmate packs that
`package_groupmate_handover.py` regenerates. Nothing in the repository read any
removed artifact, the 347 protected identities stayed unchanged, and `evidence/`
still holds every receipt that code, documents, tools or the delivery
configuration cite — including the retained `mid1_v11_20261014_final_*_run01`
pair that evidences the current CI state. The
checks were `evidence/documentation_layout_20261015_cleanup_final.json` (named
rather than linked, since a layout receipt cannot cite itself) and
[traceability](../evidence/requirements_traceability_20261015_cleanup_run02.json).
Pass the anchor receipt explicitly to the traceability tool: its default
`--tests evidence/current_tests.xml` predates several requirement anchors.

Cache/temp/scratch: `E:\AI-Tools\Cache`, `Temp`, `Work`. `code/.env` is local/ignored;
never print or package its values. Preserve compatibility junctions. Codex
migration is unfinished unless `E:\AI-Tools\finish-codex.log` says COMPLETE.

## Audit revision continuation

The requested `E:\AI-Tools\Work\investify-mid1-v11\CONTINUE.md` was absent.
The user then supplied the audit prompt in full and authorized report/deck/UI/docs,
PDF review/delivery, feature-branch commit, PR, passing Actions, merge and tag
`mid1-v1.1`. The existing `feature/mid1-report-revision` branch and edits were retained.
Current workspace write access succeeded without escalation; revision scratch
writes were denied, while `E:\AI-Tools\Temp` was writable. Scratch scripts/builds/renders
are under that Temp directory. Missing cached TeX font and headless Edge tests
required scoped approved execution; no original scientific output or existing
evidence JSON was changed.

Use the report's Section 3.2 action/status table and 8.11 limitations. C1 harness
and C2 template verifier are implemented; C3 divergence is planned. Gate A is
partial and Gate B not passed. T=1000 produces near-uniform confidence/Brier
about 0.6667, and every real temperature case stays Observe. Prompted LLM is
Iteration 3 / Mid-2; QLoRA is Iteration 4. The retained teacher is OpenAI GPT-6,
with no exact serving revision. Official template PDF was used; the ZIP named
in the audit was unavailable. Signatures, submission date/batch and meetings
remain blank. The institutional class/logo and 256 pre-revision scientific,
evidence and metadata identities were verified unchanged.
