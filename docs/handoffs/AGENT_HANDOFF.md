# Investify agent handoff

Start here for development continuation. Team preparation is in
[MID1_TEAM_GUIDE.md](../team/MID1_TEAM_GUIDE.md), with the short click script in
[DEMONSTRATION.md](../team/DEMONSTRATION.md). Technical references are in
`../technical/`. Keep the root README short and update the existing guides.

## Current state

<!-- MID1_BROWSER_CHECKPOINT_START -->
**100% technical Mid-1 completion** under the user-defined code/report/CI-CD/module scope. This is not whole-FYP completion, useful prediction or a grade. [Retained hosted run](https://github.com/Ahmed-Javaid/Investify-FYP-2027/actions/runs/38475186905) passes all five jobs for the preceding snapshot. Local cleanup checks are kept under `code/artifacts/ci_evidence`; future changes require their own checks.
[Machine status](../../evidence/mid1_technical_completion_current.json).
<!-- MID1_BROWSER_CHECKPOINT_END -->

- Repository: `E:\Uni_Stuff\FYP\Investify`; remote: https://github.com/Ahmed-Javaid/Investify-FYP-2027. Code commands run from `code`.
- Current reviewed report: 82 pages; presentation: 12 slides. [Delivery configuration](../../deliverables/current_delivery.json) selects current review/custody receipts.
- Editable entries: [report/main.tex](../../report/main.tex), [presentation/main.tex](../../presentation/main.tex). Removing unused assets did not alter PDF bytes or actual compiler inputs.
- Demo URL: http://127.0.0.1:8507 while the server runs. Check health before claiming it is running; launch with [start_guided_demo.ps1](../../tools/start_guided_demo.ps1).
- The compact groupmate ZIP contains report, slides, rubric, demonstration handout and preparation/technical guides. Members obtain source from GitHub.

## Scope and remaining work

Temperature calibration preserves raw classes but yields near-uniform confidence,
so the primary viewer abstains. Grable-Lytton scoring uses thirteen tolerance and
five capacity answers; the confidence gate preserves raw direction/probabilities.
The four older failed-calibration cases remain inspectable but cannot produce
directional suggestions.

FinBERT scores headline tone; CryptoBERT/Cardiff are a separate social comparison.
Reference labels, model bytes and frozen source identities remain unchanged.
The frozen explanation context module must stay byte-identical for the recorded
teacher packet to replay. Current assistant is teacher; original Phi-3-mini is
the untrained planned student; Mistral is fallback. New experiments need separate
identities.

Remaining whole-FYP work: divergence integration, population-specific profile
validation, useful prediction/calibration evaluation, student inference and QLoRA
comparison, performance/parity/degraded-operation checks, production hosting and
participant acceptance. Rehearsal, projector checks, signatures and supervisor
review are team tasks outside the technical completion percentage.

Confirmed metadata: FYP-1 Mid-Evaluation, Fall 2026; report date 11 October 2026;
Ahmed Javaid 22I-2530, Rafay Ul Haq 22I-2520, Soban Ahmad 22I-2460; equal delivered
contributions confirmed by the user; supervisor Mr. Irfan Ullah; no co-supervisor;
coordinator omitted. Keep actual execution dates separate. Do not infer student
understanding, institutional approval or predictive usefulness from tests.

Meeting evidence was requested before compilation. No records were supplied;
Appendix F uses the brief no-records statement already allowed by the user.
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
matrix receipts. See [Engineering](../technical/ENGINEERING.md) for commands and scope.

## Cleanup and storage

The user explicitly approved removal after a local commit. Checkpoint **5f6b6ff**
contains the short handout and approval record before deletion. The
[cleanup audit](../../evidence/workspace_cleanup_20261014.json) records 1,317
removed files, approximately 405.8 MiB, 348 published Git recovery identities and
347 unchanged protected files. Current references, six-case data and scientific
inputs remain. Obsolete archives, duplicate exports and retired notes are gone;
tracked earlier versions remain in Git history. This approval supersedes the
old requirement to keep obsolete ZIPs/archives locally.

Cache/temp/scratch: `E:\AI-Tools\Cache`, `Temp`, `Work`. `code/.env` is local/ignored;
never print or package its values. Preserve compatibility junctions. Codex
migration is unfinished unless `E:\AI-Tools\finish-codex.log` says COMPLETE.
