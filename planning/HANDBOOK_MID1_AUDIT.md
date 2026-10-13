# Mid-1 handbook compliance audit - 13 October 2026

The supplied handbook Table 1a (PDF p.11), stage intent (p.27), Forms 2/3 (pp.37-38), report contents (p.23), and design-baseline mapping (pp.56-59) were reviewed together with all four pages of the cohort Mid-Evaluation rubric. The screenshot matches the handbook p.11 table.

Mid-1 is a supervisor-only week-eight formative checkpoint: fifteen minutes and 20% of FYP-1. It asks for an implemented core module beyond the proposal spike, requirements/design, response to proposal actions, early validation including a failure case, and genuine code/member defence. The handbook 45% implementation expectation belongs to Final-1. Its p.57 calls the baseline sequencing proposed for review and gives precedence to cohort stage requirements.

The design list says to select models appropriate to the project. Investify uses domain, component/layer, data-flow, dictionary, activity, sequence, state and deployment models. A file-schema diagram covers actual JSON/Parquet contracts; SQL/ER implementation is not invented.

| ID | Required evidence | Current location | Status |
| --- | --- | --- | --- |
| H01 | Report v1.0 and document control | report/main.tex; appendix_handbook | Draft; signatures/metadata pending |
| H02 | Project vision, scope and stakeholders | chapter1_introduction | Written; stakeholder/supervisor review pending |
| H03 | Related work, research gap and CCP | chapter2_research | Written; genuine source defence pending |
| H04 | Use cases and use-case diagram | chapter4_requirements; mideval_use_cases | Implemented paths documented |
| H05 | SRS: numbered, prioritized FRs/NFRs | chapter4_requirements; appendix_requirements | Draft baseline; acceptance matrix added |
| H06 | Software design specification and rationale | chapter5_design | Revised; code-linked models supplied |
| H07 | Test plan: levels and techniques | chapter8_testing; appendix_test_cases | Current unit/module/system scopes separated |
| H08 | Development and iteration plan | chapter3_iteration_plan; chapter10_fyp2_plan | Revised plan; genuine owners/dates pending |
| H09 | Wireframes | mid1_wireframe.tex; chapter7_ui_manual | Design wireframe present |
| H10 | Actual UI screens and demonstrable flow | app/presenter.py; chapter7_ui_manual | Rebuilt; browser screenshots pending tooling choice |
| H11 | DEI, ethics, privacy and legal statements | chapter1_introduction; appendix_handbook | Written; rights/clearance sign-off not invented |
| H12 | Iteration-1 implemented core module | explain/pipeline.py; risk_comparator.py | Actual live checking/profile logic; tested |
| H13 | Domain/class model | mid1_domain.tex | Actual classes/entities and invariants explained |
| H14 | Component/layer/structure design | mid1_components.tex; mid1_layers.tex | Component/layer models selected; no redundant structure chart |
| H15 | Flow/DFD/data dictionary | mid1_dataflow.tex; SSD dictionary | Selected data-flow model and field rules present |
| H16 | Activity and sequence/SSD | mid1_activity.tex; mid1_sequence.tex | Failure/fallback path and messages present |
| H17 | State/network/interaction behavior | mid1_state.tex | State model selected for stale-check handling; graph/interaction alternatives not required |
| H18 | DB representation/schema/ERD as applicable | mid1_schema.tex; SSD data design | Artifact schema present; no implemented relational DB claimed |
| H19 | Data structures and algorithms | chapter6_iteration1; SSD dictionary | Contracts and steps documented |
| H20 | Comments and naming conventions | presenter_data.py; presenter.py; chapter6 | Snake-case functions and documented invariants |
| H21 | Static code analysis | source-syntax checks; new UI tests | Syntax checked across five changed Python modules |
| H22 | Unit/module tests and test cases | 12 new UI checks; scoped core receipts | Executed scopes retained; overlap not summed |
| H23 | CI/CD and version-control process | .github/workflows/mideval-evidence.yml | Workflow exists; remote CI/CD and member evidence pending |
| H24 | Deployment diagram | mid1_deployment.tex | Actual localhost topology documented |
| H25 | System-level validation/testing | portable HTTP checks; current AppTest | Executed local tests; no external-user acceptance claimed |
| H26 | Configuration/setup and tool manual | chapter7_ui_manual; start_guided_demo.ps1 | Current launch and failure recovery documented |
| H27 | Working code plus live demonstration | app/streamlit_app.py; current UI tests | Live arithmetic/verifier; recorded ML/study outcomes distinguished |
| H28 | Response to proposal actions | appendix_action_register; provided action register | Evidence linked; genuine closure remains pending |
| H29 | Design evolution since proposal | SSD alternatives/evolution; Git history | Earlier UI and verifier choices compared with current code |
| H30 | Code walkthrough and genuine member ownership | deliverables/CODE_WALKTHROUGH.md | Walkthrough prepared; actual member defence not observed |
| H31 | Milestone, delay and recovery record | chapter3; planning/MID_EVAL_PLAN.md | Technical blockers recorded; owners/dates require team input |
| H32 | Requirements/design baseline approval | document control; handbook C.5.1 | Draft only; no stakeholder/supervisor approval claimed |
| H33 | Dependency/API/license register | appendix_handbook; OFFICIAL_MODEL_POLICY | Register started; data-use and clearance review pending |
| H34 | Responsible AI/tool disclosure | chapter9; appendix_handbook | Assistant work disclosed; student review still required |

The earlier 85.75% estimate overstated UI (95%) and report (90%) readiness. The starting reassessment keeps all original weights and other categories, with UI 65% and report 70%, giving **75.75%** before accepting this revision. Later completion must be justified by the rebuilt UI, revised/report-rendered artifacts and deck; no grade or human-review credit follows from automated checks.

Still requiring genuine input: programme session, coordinator and co-supervisor applicability; actual member contributions and code understanding; supervisor/stakeholder baseline and panel-action closure; data-use/license/ethics review where applicable; actual rehearsal. The requested LaTeX/Beamer deck is compiled and visually reviewed. Actual browser screenshots and projector/rehearsal review remain pending. See the current unchanged-weight ledger for the 84.25% reassessment after this revision.

Sources are byte-bound in [the audit receipt](../evidence/handbook_mid1_audit_20261013.json).
