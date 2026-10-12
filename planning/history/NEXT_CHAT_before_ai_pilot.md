# Restart note: Investify mid evaluation

Prepared 12 October 2026, Asia/Karachi. Continue the existing project; do not restart its implementation.

## User direction

- Continue agent-led development without stopping merely at a milestone. Complete useful independent work while awaiting genuinely missing inputs.
- Continue with the current GPT-6.1 Sol Xhigh setup. Tell the user if a specific task warrants Astra; no escalation has been identified yet.
- The user wants the assistant or Claude to annotate social-post sentiment. Do not assume two human annotators are required for this pilot. Record AI labels honestly as model-generated reference labels, with actual model/prompt/run provenance.
- No actual model labels, posts or experimental results have been produced. Changing the plan did not complete the study.
- The latest rough planning estimate is 65% done, 35% remaining; 12--24 active agent-work hours plus 2--4 human hours for access/facts, review and rehearsal. External waits/computation are extra. Substantial scientific repair could increase agent work to 30--40 hours. These are judgements, not measured completion or guaranteed elapsed times.

## Workspace and preservation

Project root: `E:\Uni_Stuff\FYP`. New deliverables belong under `GPT_MIDEVAL`. The Git repository is `GPT_MIDEVAL\code`, not the project root. On 12 October its working tree was checked clean on `gpt/mid-eval`, HEAD `0a27ed11ae14758895277368f15c16cb72f67c9c`. Assistant commits use `Codex (tool-assisted development) <codex@local>`; nothing has been pushed.

Keep original FYP material and `E:\Uni_Stuff\investify_repo` untouched. The last preservation check covered 224 original files with zero changes. Follow the user's storage instructions: cache/temp/scratch under `E:\AI-Tools\Cache`, `Temp`, `Work`, subject to actual write permissions; project deliverables stay here. Preserve compatibility junctions. Do not claim the separate Codex migration is complete without its COMPLETE log.

Read `CHECKPOINT.md` and the **Revised remaining estimate: agent-led development** section of `MID_EVAL_PLAN.md` next. Earlier human-annotation statements in report/protocol/code describe the prior method and need revision, rather than overriding the user's latest direction.

## Verified implementation, not new research results

Last engineering validation on 11 October: 124 selected tests passed, including 12 actual Streamlit AppTests; 372 saved records and complete guided explanations validated; 62 live HTTP checks passed. The source ZIP separately passed 92 portable tests, 62 HTTP checks and 372 records in a clean venv. These checks are not predictive-performance or participant evidence.

Implemented: complete feature/family explanation context; independent prose/JSON verifier; strict claim contract and verified fallback; local structured LLM adapter/frozen evaluation; explicit prototype risk profile and separate retrospective comparator; social-study validator/evaluator and offline classifier runner; Streamlit/portable demos; CI configuration; report/diagram and 12-slide content drafts; source handover tooling.

Actual LLM completions: zero. Actual social benchmark/annotations/classifier runs: absent. Full scientific environment/raw-store inputs: absent. Current saved classifiers all predict Buy, requiring investigation. Risk comparator arithmetic does not establish suitability or predictive performance. Report PDF/PPTX compilation and visual checks, browser visual QA, remote CI/upstream reconciliation, deployment and institutional/team facts are unfinished.

## Next concrete work

1. Adapt `code/src/investify/sentiment_selection.py`, its tests, CLI/UI and documentation to support an explicit model-generated annotation method alongside the existing human method. It currently enforces `annotation_method: two_independent_humans`. Preserve raw labels, source provenance, disagreements/exclusions and frozen evaluation identities. Record reported model/provider, prompt/version, input hashes and run timing; never fabricate human identities or claim independent human validation. Keep annotation-model and candidate-model identities distinct, and freeze labels before exposing candidate predictions.
2. Obtain an accessible real social-post source and supported inference weights/runtime. Agent labelling may use actual available model access; a second model/pass can cross-check if available. Report candidate agreement with AI reference labels accurately. No generated posts or fixture outputs may become research data.
3. Restore a real explainer runtime and execute the already prepared frozen LLM study. Then reproduce/investigate the scientific all-Buy issue with actual inputs; retain failures and unfavourable results.
4. Finish consistent report/slides and render/visually verify with applicable skills. At last check no native LaTeX compiler or required `@oai/artifact-tool` presentation runtime was available. Missing tooling is an access/setup dependency, not intrinsically manual authoring work.
5. Refresh appropriate validation receipts, report counts, source provenance and the final handover bundle after changes; run remote CI when repository access works. The existing ZIP predates the latest planning edits and is a dated source snapshot.

## Runtime and verification notes

The isolated viewer environment is `E:\AI-Tools\Temp\investify-ui-py311`; it is not the original scientific lock. Prior demos used `http://127.0.0.1:8501` and `http://127.0.0.1:8765`. Recheck services in the new chat; do not assume old tool session IDs survive.

Use `-B` and put pytest cache at `E:/AI-Tools/Temp/investify-pytest-cache`. The code repo contains `tests/test_mideval*.py`, existing `test_verifier.py`/`test_emit_pipeline.py` and `test_streamlit_mideval.py`. Evidence refresh, original preservation and source packaging tools live under `GPT_MIDEVAL/tools`. Run checks appropriate to changes; no need to repeat the entire suite simply to resume.

Human-specific inputs: unavailable private access, assessment date/institutional facts, truthful member contributions/declarations, final understanding/rehearsal/presentation and any genuinely required real participant or supervisor activity. Human labelling of 200 posts is not assumed. Do not invent signatures, approvals, meetings, participants or authorship. No deadline is confirmed. No messages have been sent to corpus authors or others.
