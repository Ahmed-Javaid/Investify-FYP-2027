# Investify mid evaluation workspace

Project **F26-003-Investify**. This is the separate working area for the FYP-1 mid evaluation. Current documents and the original Soban checkout are protected by the [original-file hash manifest](evidence/original_files.sha256.json).

The code in [code](code/) is an independent copy with its original Git history, on branch `gpt/mid-eval`. Its base is `1dc24e0e3962c6ea33fb1325f4590f52a49bb030`. Checking GitHub returned 404 through the connector and a blocked-network error through Git. A newer upstream version has not been verified; see [upstream status](evidence/upstream_status.json).

## Start here

- [Current implementation checkpoint](planning/CHECKPOINT.md).
- [Live local demo and reproduction instructions](code/docs/mideval_increment.md).
- [Local LLM adapter, fallback and frozen evaluation](code/docs/local_llm_pilot.md).
- [Prototype risk profile and separate comparator](code/docs/risk_comparator.md).
- [AI/human social-study tooling](code/docs/social_selection.md) and the [actual AI reference pilot](deliverables/AI_SENTIMENT_PILOT.md); candidate inference remains pending.
- [Working source handover guide](deliverables/HANDOVER_GUIDE.md), [source bundle](deliverables/investify_mideval_source.zip), and its [clean-host receipt](evidence/source_bundle_clean_host_verification.json).
- [12 October uncommitted AI review bundle](deliverables/investify_mideval_ai_review_20261012_v2.zip) and [its clean-host receipt](evidence/ai_review_20261012_v2_clean_host_verification.json): 103 portable tests, 62 live checks, 372 records and the actual source/AI-label/freeze audit pass. The earlier clean-commit source bundle remains preserved.
- [Corpus/source access review](deliverables/SOCIAL_CORPUS_ACCESS.md) and [report metadata checks](deliverables/REPORT_METADATA.md).
- [Twelve-slide content and speaker-note draft](deliverables/presentation_outline.json), with PowerPoint export pending the required authoring runtime.
- [Real social annotation protocol](deliverables/social_annotation_protocol.json), without invented posts or human labels.

- [Work plan and time estimate](planning/MID_EVAL_PLAN.md).
- [Proposal feedback and action register](sources/Mid_Eval/PROPOSAL_ACTION_REGISTER.md), copied from the existing materials.
- [Problem statement and contribution draft](deliverables/PROBLEM_AND_CONTRIBUTION.md).
- [LLM design and remaining implementation](deliverables/LLM_DESIGN.md).
- [Model and evaluation inventory](deliverables/MODELS_AND_EVALUATION.md).
- [Domain research notes](deliverables/DOMAIN_NOTES.md).
- [Working report sources](report/).
- [Standalone evidence preview](deliverables/demo_preview.html).
- [Verification evidence](evidence/demo_artifact_verification.json).

## First implemented increment

`code/src/investify/explain/context.py` builds a JSON-safe evidence description from each frozen decision record. It covers all five technical and six news features, their meanings and recorded attributions, missing values, available sources, and important coverage limitations. It supplies the input contract for the future LLM and a current user-facing explanation layer.

The evidence section is wired into the Streamlit Decision tab. The standalone preview renders the same recorded context without installing the training stack. The live demos also offer an explicit prototype capacity/tolerance profile and separate risk-dependent linear comparator. The saved classifier probabilities and decisions remain unchanged.

Subsequent work corrects the verifier's payload-over-prose gap, checks values/targets/ranks, requires essential visible claims, retains rejection reports and supports strict prose. The guided contract now checks all eleven feature contributions, both family totals, maintained definitions, missing/zero evidence and attribution scope in text and JSON. Malformed authoritative records are rejected before display. Both live interfaces run the actual code.

Verified locally: **136 selected tests passed with no skips**, including **13 actual Streamlit AppTest cases**; **372** numeric/complete-guided records validate; **62** live HTTP and **228** separate comparator arithmetic checks pass. The viewer runtime and HTTP health were restored and checked. The local generator's transport/retry/fallback is tested with labelled fixtures; no actual explainer completion has been obtained. Real evaluation requires the saved selection/data/code plan and reports no quality score with zero completions. Scientific reproduction, browser visual QA, GitHub CI and deployment remain pending.

## Run the portable checks

From `code`:

```powershell
python -B -m unittest discover -s tests -p 'test_mideval*.py' -v
python -B scripts/verify_demo_artifacts.py --output '../evidence/demo_artifact_verification.json'
python -B scripts/export_mideval_preview.py --output '../deliverables/demo_preview.html'
```

For a live demonstration, run `python -B scripts/serve_mideval_demo.py` and open `http://127.0.0.1:8765`. The server serves historical decisions and executes Python verification on submitted explanations. Stop it with Ctrl+C.

The isolated viewer/test runtime is under `E:\AI-Tools\Temp\investify-ui-py311`, frozen in `code/requirements-demo-runtime.txt`. Dependency-source/cache receipts are in `evidence`. Streamlit runs at `http://127.0.0.1:8501`; the portable demo is at `http://127.0.0.1:8765`. This viewer environment is not the locked scientific environment. New caches, environments, temporary files and scratch continue to use `E:\AI-Tools\Cache`, `Temp`, and `Work`.

The GitHub workflow configures portable checks, plan-only evidence generation/artifact retention and a separate Streamlit AppTest job on Windows/Linux, using verified official action release tags. It has not run remotely. Repository access still returns 404. The report now includes preliminary primary research, abstract/executive summary, current engineering/validation, action status, future plan and conclusion. Institutional metadata/signatures, deeper domain/closest-work review, compilation and visual QA remain incomplete.
