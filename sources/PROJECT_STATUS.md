# Investify project status and mid evaluation plan

Updated 11 October 2026.

Investify is split across two folders. **`E:\Uni_Stuff\FYP` holds the proposal documents, an earlier prototype, and the new mid-evaluation requirements. `E:\Uni_Stuff\investify_repo` holds Soban's substantially more complete code and experimental evidence.** Use the latter as the development baseline, retain the risk-profile work from this folder, and prepare the mid report against `Mid_Eval`.

## Project identity and intended system

Investify, formerly the Quantamental AI Investment Engine, is FAST NUCES Islamabad Software Engineering project **F26-003-Investify**, as identified in the supplied proposal decision. Older files use F26-003-QuantamentalAI. Supervisor: Mr. Irfan Ullah. Team: Ahmed Javaid (22I-2530), Rafay Ul Haq (22I-2520), and Soban Ahmad (22I-2460). The proposal was **Approved with Minor Modifications**; the [proposal action register](Mid_Eval/PROPOSAL_ACTION_REGISTER.md) preserves the feedback and tracks the required responses.

The intended product gives retail investors an educational Buy/Hold/Sell view for a one-week horizon. It combines technical indicators, news and social sentiment, and a risk profile; attributes predictions with TreeSHAP; and checks explanations against the underlying decision record. The principal contributions are the leakage-audited evaluation harness and deterministic explanation verifier, with a planned experiment on disagreement between news and social sentiment. Predictive profit is not a project claim.

The committed full scope is broader than the current spike: 8–12 US equities, news and social sentiment, genuine risk conditioning, a local language-model explanation layer, deployment, evaluation, and acceptance evidence. Price-only crypto is a future test of the calendar abstraction, rather than a crypto prediction product.

## Locations and file versions

| Purpose | File or folder to use | Status |
| --- | --- | --- |
| Main code baseline | [investify_repo README](../investify_repo/README.md) and [source package](../investify_repo/src/investify/) | Real pipeline, historical experiment artifacts, and a two-tab Streamlit demo. |
| Current experimental findings | [POC_REPORT.md](../investify_repo/POC_REPORT.md) and [artifacts](../investify_repo/artifacts/) | Stronger evidence than this folder's older technical-only leakage spike. |
| Most complete proposal source | [Investify_Proposal_Full.docx](Investify_Proposal_Full.docx) | Revised 10 September at 03:35; best comprehensive document baseline available locally. Its implementation and ownership sections need reconciliation with the repo. |
| Condensed concept source | [Investify_Concept.docx](Investify_Concept.docx) | Revised at the same time; includes the same corrected risk example. |
| Latest editable slide draft | [Investify Updated (1).pptx](<Investify Updated (1).pptx>) | Revised 11 September at 00:36; 15 slides. Slide 7 has no flow diagram; slide 10 has no substantive PoC evidence. Slides 12–13 contain SmartArt and are not empty. |
| Older defence decks | [Full](Investify_Defence_Full.pptx) and [Concept](Investify_Defence_Concept.pptx) | 6 September versions; reference material, not the latest slide draft. |
| New assessment requirements | [Mid_Eval](Mid_Eval/) | Added 11 October; rubric, committee notices, and the official report template. |
| Proposal decision and required modifications | [Proposal action register](Mid_Eval/PROPOSAL_ACTION_REGISTER.md) | Approved with Minor Modifications; panel feedback supplied by the team on 11 October, with open actions and closure evidence. |
| Risk-profile evidence worth retaining | [risk sensitivity spike](poc/poc_risk_profile_spike.py), [results](poc/poc_risk_results.json), and [scoring code](poc/prototype/profile_scoring.py) | More extensive than the repo's display-only risk quiz; not integrated into the main repo. |
| Earlier interface | [ten-screen prototype](poc/prototype/README.md) | Mostly fixtures, with real risk scoring and verification. Retain as reference and for reusable risk work. |
| Latest deferred design note | [staleness gate](FUTURE_WORK_staleness_gate.md) | Identified 11 September and explicitly deferred to FYP-2. |
| Historical material | `old/`, `backup_pre_fix/`, `E:\Projects\FYP` | Earlier proposals, backups, and a July proposal PDF. |

### Copies that can mislead

- `Investify_Proposal_Full.pdf` and `Investify_Concept.pdf` are 6 September exports. They still show the old risk persona and tolerance **0.68**. The revised Word files correct the persona and tolerance to **0.67**.
- `investify_repo/docs/Investify_Concept.docx` also contains those two old values. It differs from this folder's concept source at those corrections.
- `investify_repo/docs/Investify Updated.pdf` is a 6 September export with 14 slides, older than the editable 15-slide draft here.
- `Investify_PoC.zip` predates the latest edit to `poc/prototype/app.py`. The difference is a removed explanatory information box, rather than a new functional module. Work from the loose source files.
- Slide figures under `slides/` were generated after the editable deck was saved. The flow image is not embedded in slide 7.

## Where work stopped

The September 10–11 project discussion was proposal-defence preparation. It progressed from building the ten-screen prototype to reviewing Soban's GitHub project, cloned separately into `E:\Uni_Stuff\investify_repo`. That comparison recommended taking the repo forward and retaining the older risk sensitivity work. The two implementations were not merged.

The final saved design task was a staleness gate: compare a current quote with the last completed session before serving a recommendation, warn or refuse after a material move, and keep the live quote outside the prediction feature vector. The note remains deferred to FYP-2 and is not implemented or incorporated into the proposal.

The last local code commit is **`1dc24e0`**, dated 10 September 2026, titled “Phase 3 on both corpora, Makefile, README, ownership change.” The checkout is clean and has 14 commits, all authored by Soban. Its remote is `https://github.com/Schwifty101/investify.git`. The online branch could not be checked during this reconciliation; this is the latest **local** snapshot, not a claim that GitHub has no newer work.

## What exists in the main code repo

| Area | Implemented evidence | Remaining limitation |
| --- | --- | --- |
| Data and alignment | Append-only store, event and ingestion timestamps, content hashes, NYSE calendar mapping, backward as-of joins, technical indicators, and fold-local scaling. | Historical NVDA spike; continuous-market calendar is implemented but untested and unexercised. Calendar cutoff behavior must be reconciled with the proposal before broader correctness claims. |
| News sentiment | FinBERT scoring and caching; FNSPID and supplemental Alpaca/Benzinga news experiments. | No social corpus, social-model study, divergence features, or pre-registered divergence ablation. Raw data and feature matrices are absent from this clone. |
| Leakage experiments | Clean, shuffled, unpurged, centred-window, long-window, and same-bar-text arms; stored results for both corpora, plus reported canary and oracle controls. | Dataset-specific findings do not establish all leakage guarantees or live/backtest parity. |
| Decision engine | Fixed XGBoost, isotonic calibration, linear comparator, TreeSHAP, and 186 saved decisions per corpus. | No demonstrated predictive signal. All 186 calibrated decisions are Buy in each corpus; risk tier does not condition the model. |
| Explanations | Deterministic template, structured and prose verification, claim reports, corruption demo, and template fallback. | No language model, constrained decoding, QLoRA, or teacher/student comparison. One vague sentence can pass under the allowed unverifiable-rate threshold. |
| Interface | Two-tab Streamlit demo: Leakage Lab and Decision, with a short risk quiz. | Historical artifact viewer; not yet the complete advisory product. |
| Delivery and process | Git history, dependency lockfile, Makefile, tests, and committed artifacts. | No `.github/workflows`, FastAPI service, container, cloud deployment, or clean-host validation in the local checkout. |

The store and news results are substantive implementation. “No predictive signal” is an experimental finding, not evidence that the code is absent. Equally, successful verification of an explanation does not make its underlying prediction useful.

### Verification on 11 October

- The older prototype's test script completed: **59 passed, 0 failed**.
- All **372 saved records** in the main repo loaded through its validating decision schema, and all 372 template explanations passed its current emit/verify path.
- Maximum SHAP additivity residuals were approximately `1.92e-7` for FNSPID and `9.05e-7` for Alpaca.
- Representative corruption checks on both corpora triggered fallback for wrong probability, wrong SHAP magnitude, flipped direction, promoted minor feature, and invented feature name. A single vague sentence remained accepted under the documented rate threshold.
- The full main-repo pytest suite was not rerun: its environment is not installed here and the gitignored raw data/store are absent. The previous September session recorded **100 passed, 6 skipped, 13 errors**, with errors caused by missing feature-store inputs. The README's “119 tests” is a count, not a verified all-green result on this machine.

## What Mid_Eval now requires

The [official rubric](Mid_Eval/FYP-1-Mid-Assessment-Guidelines-and-Rubrics.pdf) describes a supervisor-only checkpoint worth **20% of FYP-1**. It evaluates a live presentation/demo through Form 2 and a written report through Form 3. A proposal-stage demo with little subsequent progress is explicitly flagged.

The supplied proposal decision is **Approved with Minor Modifications**. The panel requires clearer contributions beyond temporal leakage, a concrete account of the LLM's user benefit and technical/sentiment explanations, a refined problem statement and pretrained-model inventory, explicit metrics, an improved PoC, user transparency, and deeper stock-market understanding. These are tracked as PF-01 through PF-09 in the [proposal action register](Mid_Eval/PROPOSAL_ACTION_REGISTER.md). Their closure evidence belongs in the mid report and demo; the register distinguishes proposed implementation increments from already committed dates.

The [28 September committee notice](<Mid_Eval/Screenshot 2026-10-11 004215.png>) requires at least one meaningful core module working through the live interface, plus meaningful GitHub branches and automated testing for CI/CD. Existing code gives us a base; the September spike alone is not evidence of progress since the proposal defence.

Form 2 covers proposal actions, iteration progress, the core-module demo, requirements, design evolution, repository/member evidence, testing, and team/tool ownership. Form 3 covers template compliance, research and gap analysis, scope, testable requirements, architecture, data/process/behavior design, implementation documentation, and testing/tool/risk disclosure.

The [LaTeX ZIP](Mid_Eval/F26_FYP1_Mid_Report_LaTeX_Complete.zip) is the editable official template. The accompanying [56-page PDF](Mid_Eval/F26_FYP1_Mid_Report_LaTeX_Complete.pdf) is a placeholder preview, not a completed Investify report. Its ten chapters cover introduction, research, proposal feedback and iteration planning, requirements, design, implementation, testing, development evidence, remaining plan, and conclusion. Appendices cover proposal actions, requirements, tests, repository evidence, diagrams, and meetings.

The [5–6 October notices](<Mid_Eval/Screenshot 2026-10-11 004104.png>) announce the rubric and template, but do not give a submission deadline. The proposal-panel feedback has now been supplied and preserved in the action register; a confirmed deadline is still needed.

## Work to straighten out before the next implementation pass

1. **Address the recorded proposal modifications and reconcile scope.** Work through PF-01 to PF-09 in the proposal action register, agree owners and target dates, and link completed revisions/demos/tests as evidence. Confirm the submission deadline and any additional supervisor instructions. Preserve the original advisory boundary while making the LLM role, evaluation, contribution, and transparency explicit.
2. **Continue from the main repo.** Confirm its current upstream state and reproducible Windows setup. Restore required data through documented acquisition or approved local copies. Keep new environments, caches, and scratch under `E:\AI-Tools\Temp`, `Cache`, and `Work` respectively.
3. **Choose a demonstrable improvement beyond the September spike.** A practical candidate is integrating genuine risk profiling and a labelled degraded response into the real decision path. Another is a completed serving/parity slice. The chosen increment needs requirements, tests, live failure cases, and clear ownership. A calibrated constant-Buy model must be presented with its limitation.
4. **Add working CI/CD and current contribution evidence.** Tests must run on a clean environment; artifact-dependent checks must handle documented inputs explicitly. Use real incremental contributions, branches, milestones, and deployment evidence rather than reconstructing historical authorship.
5. **Resolve ownership before writing the report.** The proposal assigns the harness to Ahmed; the repo records its transfer to Soban, leaving Ahmed deployment. This is a documented discrepancy, not a new allocation agreed in this session. Agree the actual mid-evaluation work and update the proposal-derived tables, slides, and report consistently.
6. **Write the mid report from current evidence.** Extract the official template into a separate report working folder when authoring begins. Connect FR/NFR identifiers to current modules, diagrams, tests, and results. Document Alpaca as a supplemental source and distinguish implementations, fixtures, and planned work.

Risk profiling also needs a specification decision: the proposal fixes lambda at 2.25, while the older scoring/spike code uses tier-dependent 2.75/2.25/1.75. Its Grable–Lytton wording and scoring key are stand-ins. The verifier's recall definition also differs between proposal prose and implementation. Resolve these explicitly when integrating the retained code.

## Full project work beyond the immediate mid evaluation

Social sentiment and its hand-labelled benchmark; divergence ablation; multi-ticker evaluation; genuine risk conditioning; calibration behavior; a tested continuous-market path and remaining horizon evaluation; live/backtest parity; fault handling; FastAPI and deployment; language-model generation and its groundedness comparison; measured NFRs; human verifier validation; participant acceptance sessions; and clean-host handover remain substantial work. The staleness gate retains its existing FYP-2 status unless the team changes that scope explicitly.

Original documents, artifacts, archives, and code were preserved during this reconciliation. This file is the project entry point; it does not record a new implementation milestone or a new team allocation.
