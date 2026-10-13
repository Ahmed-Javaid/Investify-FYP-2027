# Investify agent handoff

Single continuation entry for agents/maintainers. Team reading belongs in
[MID1_TEAM_GUIDE.md](../team/MID1_TEAM_GUIDE.md); technical references live in
`../technical/`. Keep the root README short; update existing guides instead of
creating another status page or member handout.

## Current state

<!-- MID1_BROWSER_CHECKPOINT_START -->
**Technical scope implemented; hosted CI/CD verification pending** under the user-defined code/report/CI-CD/module scope. This is not whole-FYP completion, useful prediction or a grade. Hosted execution remains pending; configuration is not execution evidence. Later working-tree changes need their own checks.
[Machine status](../../evidence/mid1_technical_completion_current.json).
<!-- MID1_BROWSER_CHECKPOINT_END -->

- Canonical repository: `E:\Uni_Stuff\FYP\Investify`; code commands run from `code`.
- Remote: https://github.com/Ahmed-Javaid/Investify-FYP-2027. Previously published main: `70bf0e3`.
- Documentation and technical revision are locally checked; prior hosted receipts certify their earlier commits.
- Current report: Revised_20261014, 82 pages; current presentation: 12 slides. [Delivery configuration](../../deliverables/current_delivery.json).
- Editable entries: [report/main.tex](../../report/main.tex), [presentation/main.tex](../../presentation/main.tex); current PDF receipts bind the revised sources and reviewed page renders.
- Recorded demo URL: http://127.0.0.1:8507 while the server runs. Check health before claiming it is running; launch with [start_guided_demo.ps1](../../tools/start_guided_demo.ps1).
- The compact team ZIP contains report, presentation, rubric and one team guide. Members obtain source from GitHub.

## Constraints and remaining work

Current assistant is teacher, original Phi-3-mini the untrained planned student,
Mistral fallback. FinBERT scores news; social comparison is separate. Preserve
weak prediction, historical isotonic collapse, current uncertainty/abstention and reference-label limits and absent measured
user benefit. New experiments need new identities; preserve frozen data, labels,
model/source identities, archived outputs and dated evidence.

Remaining whole-FYP work: social/news divergence integration, population-specific profile
validation, useful prediction/calibration evaluation, student inference and
QLoRA comparison, performance/parity/degraded-operation checks, production
hosting, participant acceptance and external installation. Real walkthroughs,
rehearsal/projector review, signatures and supervisor review are team tasks,
excluded from the user's technical completion percentage.

Confirmed metadata: Fall 2026, report date 11 October 2026, existing names/roll
numbers, Mr. Irfan Ullah, no co-supervisor, coordinator omitted. Keep actual
execution dates separate from the report date. Do not infer human acceptance,
institutional review or student authorship from automated checks.

## Active tools

- `package_groupmate_handover.py`: build a new compact ZIP; preserve prior ZIP/receipt pairs.
- `package_source_handover.py`, `verify_source_handover.py`: source/PDF packaging and actual extraction validation; use new filenames/prefixes.
- `code/scripts/run_mid1_ci.py`, `tools/run_mid1_delivery.py`: shared CI and hosted delivery.
- `update_mid1_technical_status.py`: machine status plus this handoff's status block only.
- `verify_requirements_traceability.py`: source/test anchors; Markdown goes into the technical requirements block.
- `verify_documentation_layout.py`: active links, archived identities and protected source/PDF bytes.
- `write_ci_checkout_inventory.py`: refresh reviewed identities after validated changes.
- Build/render/publication tools remain active. Eighteen superseded documentation generators are archived and must not recreate old pages.

Retain the original tracked `code/source_revision.json`: CI checks/restores its
temporary declaration. Newline-only restoration can reproduce reviewed hashes;
actual content drift must fail. Hosted delivery needs a clean same-commit matrix.

## Storage and archives

Cache/temp/scratch: E:\AI-Tools\Cache, Temp, Work. `code/.env` is local/ignored;
never print/package credential values. Publisher weights and raw acquisition
are separate demo/science prerequisites. Preserve compatibility junctions.
Codex migration is unfinished unless E:\AI-Tools\finish-codex.log says COMPLETE.

Older PDF/source ZIP outputs: `deliverables/archive/20261013`. Retired notes,
planning history and generators: [archive index](../archive/20261013_before_consolidation/INDEX.txt).
[Consolidation receipt](../../evidence/documentation_consolidation_20261013.json)
maps former paths to exact archived bytes. Original sources and parent `_archives`
remain preserved. Historical code/docs/CLAUDE instructions describe earlier work;
this handoff and current user instructions govern continuation.

## Revision checkpoint 14 October 2026

New temperature records preserve raw classes but fit near-uniform confidence, so the primary viewer abstains. Grable-Lytton scoring has thirteen tolerance/five capacity inputs and a direction-preserving confidence gate; old blend remains historical. Source/risk/model fields and all original labels remain preserved. CryptoBERT sanity probes produce positive/negative outcomes; the neutral probe fails. Report sources remove draft voice, expand use cases/FRs/tests/metrics, record team-delivered responsibilities and redraw all used diagrams. PDF edit marker ran exactly once for two outputs. Meeting question was asked before compilation; no reply yet. The first and subsequent QA renders use the brief no-records note already allowed by the user. Incorporate actual details if supplied. Focused real browser captures: presenter_browser_20261014_revision05. Shared code validation: revision_20261014_evidence01 and revision_20261014_ui03; anchor XML/receipt: requirement_anchor_tests_20261014. Original PDF and source snapshot remain archived. No new source has been pushed.
