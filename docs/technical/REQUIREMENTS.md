# Investify requirements and acceptance

Maintained requirements, acceptance checks and proposal responses. The bounded
Mid-1 prototype and full [proposal](../../sources/Investify_Proposal_Full.docx)
have different completion boundaries. Tests/drafts do not establish supervisor
approval or participant acceptance.

## Mid-1 observable acceptance

| Requirement | Acceptance |
| --- | --- |
| Recorded case | Valid case loads; invalid/unavailable input emits no invented replacement. |
| Evidence | All five technical/six news features retain values, meanings, missing status and contributions. |
| Independent checking | Correct JSON cannot conceal wrong prose and correct prose cannot conceal wrong JSON. |
| Recovery | Retain rejection; check fallback separately; surface fallback failure. |
| Current verification | Changing text/settings/case removes the obsolete verdict. |
| Explicit profile | Require five capacity and thirteen tolerance answers; reconcile restrictively with declared caps. |
| Current risk policy | Change the required confidence; preserve model direction and probabilities; abstain on insufficient confidence. |
| Historical comparator | Preserve earlier blend/scaling evidence; refuse development dates and missing technical inputs. |
| Honest study replay | Only complete source/checkpoint/plan-bound outputs receive scores. |

Eighteen engineering IDs have source/test anchors in the unchanged
[manifest](../../code/docs/requirements_traceability.json). The
[dated selected-suite receipt](../../evidence/background_requirements_traceability_20261012_v3.json)
retains its 212-test scope; anchor execution is not a coverage percentage.

<!-- REQUIREMENT_ANCHORS_START -->

Checked 23 IDs against source symbols and 29 passing tests in [the dated input receipt](../../evidence/requirement_anchor_tests_20261014_v11_run01.xml). This is anchor execution, not coverage or institutional acceptance.

[Matching checker receipt](../../evidence/requirements_revision_20261014_v11_run01.json).

| ID / acceptance | Source and named passing regression | Evidence boundary |
| --- | --- | --- |
| MID-FR-01: Load saved decisions and refuse invalid inputs | [DecisionRecord.from_dict](../../code/src/investify/decision_record.py#L224)<br>[RecordValidationTests.test_nonfinite_out_of_range_or_boolean_probabilities_are_rejected](../../code/tests/test_mideval_record_validation.py#L16) | Saved records only; no live-data ingestion result. |
| MID-FR-02: Display all technical/news values, attributions, meanings and coverage | [build_context](../../code/src/investify/explain/context.py#L42)<br>[MidEvalContextTests.test_all_real_records_keep_their_facts_and_validate](../../code/tests/test_mideval_context.py#L23) | Social features and live freshness remain absent. |
| MID-FR-03: Check visible prose independently of structured claims | [verify](../../code/src/investify/explain/verifier.py#L672)<br>[MidEvalVerifierTests.test_correct_payload_cannot_hide_wrong_displayed_probability](../../code/tests/test_mideval_verifier.py#L25) | Supported grammar; no unrestricted semantic verification. |
| MID-FR-04: Reject contradictions and missing essential visible claims | [verify](../../code/src/investify/explain/verifier.py#L672)<br>[MidEvalVerifierTests.test_payload_cannot_supply_facts_or_notice_absent_from_displayed_text](../../code/tests/test_mideval_verifier.py#L68) | Known contradictions are hard failures; default vague-sentence acceptance is disclosed. |
| MID-FR-05: Retain failed candidate reporting separately from verified fallback | [emit](../../code/src/investify/explain/pipeline.py#L39)<br>[MidEvalVerifierTests.test_fallback_retains_the_rejected_candidate_report](../../code/tests/test_mideval_verifier.py#L101) | Fallback success does not relabel the candidate as successful. |
| MID-FR-06: Reject unsupported sentences in strict mode | [verify](../../code/src/investify/explain/verifier.py#L672)<br>[MidEvalVerifierTests.test_strict_mode_rejects_unparsed_text_and_preserves_clean_template](../../code/tests/test_mideval_verifier.py#L93) | Strict mode checks the maintained grammar. |
| MID-FR-07: Block re-runs when data/runtime preflight fails | [harness_input_report](../../code/src/investify/demo_readiness.py#L57)<br>[MidEvalReadinessTests.test_empty_partition_directories_do_not_enable_a_rerun](../../code/tests/test_mideval_readiness.py#L48)<br>[StreamlitMidEvalTests.test_leakage_view_labels_saved_results_and_limits_preflight_claims](../../code/tests/test_streamlit_mideval.py#L50) | Structural preflight is not row/schema/cache-coverage or scientific-lock validation. |
| MID-FR-08: Bound explicitly configured generator requests and label fallback | [LocalExplainer.explain](../../code/src/investify/explain/local_llm.py#L275)<br>[verify_runtime](../../code/src/investify/publisher_models.py#L78)<br>[LocalLLMTests.test_unavailable_provider_fails_fast_with_explicit_fallback](../../code/tests/test_mideval_local_llm.py#L115)<br>[PublisherModelTests.test_all_shards_are_required_and_changed_bytes_fail_before_inference](../../code/tests/test_mideval_publisher_models.py#L32) | Provider fixtures are engineering evidence; no real local/student inference. |
| MID-FR-09: Check maintained definitions in prose and JSON | [verify_generated](../../code/src/investify/explain/local_llm.py#L209)<br>[LocalLLMTests.test_wrong_reviewed_definitions_in_text_or_json_are_rejected](../../code/tests/test_mideval_local_llm.py#L55) | Matching maintained definitions is not independent domain review. |
| MID-FR-10: Require frozen evaluation identities and retain null scores without outputs | [evaluate](../../code/src/investify/explain/evaluation.py#L73)<br>[EvaluationPlanTests.test_plan_drift_is_rejected_before_any_provider_request](../../code/tests/test_mideval_llm_evaluation.py#L72) | Plan-only and unavailable-provider receipts are not model quality. |
| MID-FR-11: Require all-feature, family and attribution-scope coverage | [verify_generated](../../code/src/investify/explain/local_llm.py#L209)<br>[CompleteEvidenceTests.test_every_feature_has_a_value_magnitude_direction_and_target_in_both_sources](../../code/tests/test_mideval_complete_evidence.py#L21) | SHAP explains raw predicted-class score, not calibrated probability or market causation. |
| MID-FR-12: Require complete capacity and thirteen tolerance answers; expose restrictive reconciliation | [score_profile](../../code/src/investify/risk_profile_gl.py#L65)<br>[CalibrationRiskV2Tests.test_incomplete_or_boolean_tolerance_answers_are_refused](../../code/tests/test_mideval_calibration_risk_v2.py#L54)<br>[CalibrationRiskV2Tests.test_capacity_caps_bind_despite_high_tolerance](../../code/tests/test_mideval_calibration_risk_v2.py#L59) | Published scoring with concise UI paraphrases; local suitability remains unvalidated. |
| MID-FR-13: Fit separate comparator scaling on earlier rows and refuse invalid inputs | [build_comparator](../../code/src/investify/risk_comparator.py#L73)<br>[RiskComparatorTests.test_changing_heldout_feature_values_cannot_change_scaling_statistics](../../code/tests/test_mideval_risk.py#L77) | Retrospective saved-feature comparator, not the original ingestion-to-linear baseline. |
| MID-FR-14: Risk allowance changes abstention without reversing model direction or mutating probabilities | [apply_risk_policy](../../code/src/investify/risk_profile_gl.py#L102)<br>[CalibrationRiskV2Tests.test_risk_allowance_changes_abstention_without_reversing_direction](../../code/tests/test_mideval_calibration_risk_v2.py#L66) | Project confidence gate; not a validated brokerage/suitability rule. |
| MID-FR-15: Validate declared annotation provenance and freeze social references | [validate_benchmark](../../code/src/investify/sentiment_selection.py#L115)<br>[AIAnnotationTests.test_one_ai_pass_has_null_agreement_and_explicit_reference_scope](../../code/tests/test_mideval_ai_annotation.py#L105) | Actual AI-reference pilot exists; no second pass, human validation or reliability score. |
| MID-FR-16: Require complete paired held-out outputs before sentiment comparison | [evaluate_predictions](../../code/src/investify/sentiment_selection.py#L274)<br>[SentimentSelectionTests.test_no_runs_or_one_candidate_never_manufactures_a_model_selection](../../code/tests/test_mideval_sentiment_selection.py#L129) | Original candidates executed on the frozen 24-post held-out set; agreement is against AI references, not independently human-validated accuracy. Deployment selection remains open. |
| MID-FR-17: Load declared local classifier weights and retain raw/error outcomes | [run_inference](../../code/src/investify/sentiment_inference.py#L127)<br>[SentimentInferenceTests.test_actual_loader_refuses_missing_weights_without_a_download](../../code/tests/test_mideval_sentiment_inference.py#L88) | Original candidates executed on the frozen 24-post held-out set; agreement is against AI references, not independently human-validated accuracy. Deployment selection remains open. |
| MID-FR-18: Preserve teacher prose/provenance and separate verified training/validation exports | [import_responses](../../code/src/investify/explain/teacher_session.py#L159)<br>[TeacherSessionTests.test_actual_exports_keep_validation_out_of_training_and_disclose_hybrid_targets](../../code/tests/test_mideval_teacher_session.py#L87)<br>[StreamlitMidEvalTests.test_actual_teacher_view_replays_examples_and_preserves_student_pending_state](../../code/tests/test_streamlit_mideval.py#L284) | Six actual all-Buy teacher examples; factual JSON assembled; no student inference/QLoRA or measured user benefit. |
| MID-FR-19: Fit multiclass calibration only on available earlier outcomes and preserve raw class order | [fit_temperature](../../code/src/investify/multiclass_calibration.py#L37)<br>[softmax_temperature](../../code/src/investify/multiclass_calibration.py#L15)<br>[CalibrationRiskV2Tests.test_calibration_refuses_unavailable_labels](../../code/tests/test_mideval_calibration_risk_v2.py#L35)<br>[CalibrationRiskV2Tests.test_real_calibration_replay_preserves_all_raw_classes_and_probabilities](../../code/tests/test_mideval_calibration_risk_v2.py#L19) | Post-analysis temperature diagnosis; T reaches 1000 and confidence is near one-third, so the policy abstains. |
| MID-FR-20: All thirteen tolerance item scores retain the published minimum/maximum | [score_profile](../../code/src/investify/risk_profile_gl.py#L65)<br>[CalibrationRiskV2Tests.test_thirteen_published_item_scores_have_exact_minimum_and_maximum](../../code/tests/test_mideval_calibration_risk_v2.py#L47) | Scoring correctness, not population-specific psychometric validation. |
| MID-FR-21: Onboarding states purpose, risks and no trade execution | [onboarding_view](../../code/app/presenter.py#L94)<br>[PresenterUiTests.test_onboarding_precedes_the_decision_and_discloses_purpose_risks_and_status](../../code/tests/test_presenter_ui.py#L179) | Current historical UI only; participant understanding is unmeasured. |
| MID-FR-22: Every result step shows advisory status, confidence, date/horizon and limits | [walkthrough](../../code/app/presenter.py#L294)<br>[PresenterUiTests.test_each_walkthrough_step_has_advisory_date_horizon_and_limits](../../code/tests/test_presenter_ui.py#L188) | Walkthrough result steps; later service responses need the same acceptance. |
| MID-FR-23: Observe headlines and verified explanations preserve the trusted policy | [decision_view](../../code/app/presenter.py#L103)<br>[PresenterUiTests.test_walkthrough_renders_only_the_selected_step](../../code/tests/test_presenter_ui.py#L33)<br>[PresenterUiTests.test_abstaining_explanation_and_fallback_keep_policy_outcome](../../code/tests/test_presenter_ui.py#L199) | Raw class remains diagnostic; current template grammar only. |

<!-- REQUIREMENT_ANCHORS_END -->

## Full proposal acceptance

The fifteen original FRs cover append-only dual timestamps/deduplication,
session mapping, backward as-of joins, fold-local scaling, calibrated five-session
decisions, additive SHAP, restrictive profiles, verified explanations/claim
reports, recurring controls/canary, live/backtest parity, operational degraded
states, provenance, notices/horizons and external clean-host installation.

Explanation targets: numeric fidelity >=0.98, directional consistency >=0.95,
claim recall >=0.80, unverifiable rate <=0.15 and zero contradictory emitted
claims across 200 held-out explanations. The checker exists; the complete
generated-model evaluation is unfinished. User comprehension remains separate.

Original NFR bounds remain unmeasured in their specified environments: decision
path <800 ms p95; sentiment >=150 documents/s on 16 GB GPU; CPU TreeSHAP <50 ms;
inference memory <4 GB; later QLoRA within four GPU hours; explanation including
verification <5 seconds; nightly ingest <30 minutes; walk-forward/search <90
minutes. The inspected GPU has 10,240 MiB. Bounded adapter timeout/retries do not
establish the five-second whole-request target.

## Proposal feedback

Approved with Minor Modifications. Exact supplied feedback remains in the
[source action register](../../sources/Mid_Eval/PROPOSAL_ACTION_REGISTER.md).

| ID | Request | Current response and remaining work |
| --- | --- | --- |
| PF-01 | Contribution clarity | Separate controls/verifier/context from imported components; closest-work comparison and evaluation status are in report Section 2.5; divergence remains planned. |
| PF-02 | LLM benefit | Inputs/outputs, permitted claims, illustrative example and comparison plan defined; prompted LLM Mid-2, QLoRA Iteration 4. |
| PF-03 | Technical/sentiment explanation | Available values/definitions/contributions and checks; social integration and arbitrary prose validation remain. |
| PF-04 | Refined problem | Educational interpretation, uncertainty and factual consistency; actual baseline agreement remains. |
| PF-05 | Model clarity | FinBERT news, paired social candidates, assistant teacher, Phi-3-mini student/Mistral fallback; student inference and final social selection remain. |
| PF-06 | Metrics | Prediction/calibration, leakage, social agreement, explanation, runtime/user measures separated; adequacy criteria still need agreement. |
| PF-07 | Improved PoC | Full evidence, independent checking, retained rejection, verified fallback, stale-state reset and browser review; member defence/rehearsal remain. |
| PF-08 | Transparency | Historical/all-Buy/news-only/profile/AI-reference limits; full journey and comprehension remain. |
| PF-09 | Market understanding | Price formation/drivers, eleven formulas, news absorption, regimes and corporate actions connect to design in the revised market-background section. |

## Iterations and committee requirements

| Proposal stage | Commitment | Current position |
| --- | --- | --- |
| Mid-1, week 7 | Data/calendar/features, social selection, baseline/leakage and thin UI. | First-checkpoint evidence exists; deviations and review stay explicit. |
| Final-1, week 12 | Engine/calibration/SHAP, divergence, service and deployment. | Engine/SHAP built early; usable calibration, divergence and deployment remain. |
| Mid-2, week 18 | Prompted explainer/data, measured NFRs, parity/degraded operation and acceptance preparation. | Guard groundwork exists; full evaluation/integration remains. |
| Final-2, week 24 | QLoRA comparison, broad evaluation, participant sessions, external installation. | Mostly future work. |

The committee describes Mid-1 around week eight: supervisor-only, formative,
20% of FYP-1, meaningful live core module with failure/edge behaviour. Form 2:
proposal actions 10, iteration progress 10, demo 25, requirements 10, design 15,
repository/member evidence 10, tests 10, presentation/ownership 10. Report review
is separate; no fixed whole-FYP implementation percentage is set for Mid-1.

The [rubric](../../sources/Mid_Eval/FYP-1-Mid-Assessment-Guidelines-and-Rubrics.pdf)
and [handbook](../../sources/BS-FYP-Handbook-2026_DRAFT.pdf) require appropriate
report/design/test/setup evidence. Models must reflect actual file-based
contracts; an invented relational database is unnecessary. Real signatures,
understanding and review remain team activities.

## Transparency and proposal mapping

MID-FR-21 requires onboarding purpose/risks/no trades. MID-FR-22 requires result
status, confidence, date/horizon and limits. MID-FR-23 requires an Observe headline
and trusted policy consistency in template, candidate and fallback. The current
manifest maps them to actual presenter acceptance tests. The complete FR-1..15
to MID-FR mapping and deviations are in report Appendix B and Table 3.2.
