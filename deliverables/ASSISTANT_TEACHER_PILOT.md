# Recorded assistant teacher pilot

The user chose to try the current assistant as teacher before considering Mistral. The active student remains the proposal's **Phi-3-mini** family. No extra Qwen teacher download is required. An exact student checkpoint and its local training setup are still pending. The original proposal is preserved; this teacher choice is a user-directed change from its open-weight-teacher assumption.

## Actual completed work

The assistant wrote **six real explanations** from frozen historical NVDA decision records. All six passed the existing strict verifier: each retains the decision, calibrated probabilities, five ranked contributors, all eleven feature values/attributions/directions/definitions, both family totals, attribution scope and exact advisory notice. Raw teacher prose is stored before import; no deterministic template was substituted as a teacher response. No failed candidate was converted into a success through fallback.

The input packets provide original facts, reviewed definitions and controlled sentence patterns, **without a completed reference answer**. Teacher wording remains constrained to the maintained grammar. The separate deterministic guide is available in the viewer for comparison. Passing this contract does not demonstrate unrestricted natural-language truth, better comprehension, or an advantage over the guide.

The actual literal comparison finds the same sentence-line multiset as the complete deterministic guide in all six outputs, with different ordering. This contract currently prescribes most of the language. The teacher pilot demonstrates fact-to-text assembly and provenance; it does not establish added explanatory content. Original-student behaviour and any adaptation benefit still need measurement. Broader language or follow-up answers would require a separately defined checking/evaluation contract rather than silently weakening this verifier.

The teacher writes prose. The structured JSON payload in each student target is constructed deterministically from the saved record. This is **hybrid supervision**, explicitly recorded in the plan: the factual payload is not claimed as a teacher-generated completion. The verifier checks the actual prose independently, so a correct assembled payload cannot conceal an incorrect sentence.

## Frozen split

Both corpora are grouped by trading date before any teacher response:

| Block | Dates | Records in both corpora | Actual pilot examples |
| --- | ---: | ---: | ---: |
| Training | 118 | 236 | 4 |
| Validation | 30 | 60 | 2 |
| Held-out test | 38 | 76 | 0 |

Selected training dates are 29 March and 15 September 2023; selected validation date is 9 October 2023. Each selected date is represented in both corpora. The previous final 38-date test block is preserved and excluded from teacher packets and training exports. Prior withdrawn local inference explored some held-out examples, so the project does not claim this is a first-ever untouched test declaration.

All 372 saved source decisions, and these six selected examples, are Buy. This pilot establishes a recorded construction/import path; it does not establish Hold/Sell generalization, adequate dataset size or QLoRA efficacy. Original raw science inputs and the constant-Buy issue still need restoration/investigation.

## Teacher provenance

Provider: OpenAI. Identity available to this session: an assistant based on the GPT-6 family. **Exact serving model ID/revision, decoding parameters, token usage and per-example inference latency are unavailable and recorded as null.** These are actual session-generated outputs persisted through tool calls, not fabricated API responses or a claimed pinned checkpoint.

The plan records prompts, input/record/source hashes and source-code identity. Raw file persistence times are retained in hash-bound receipts. Copies and extracted archives replay those original receipts instead of using new file mtimes. Provenance checks establish byte consistency; they do not independently authenticate a hidden serving revision or label the teacher as human.

The current published OpenAI restriction concerns competing models; no provider-specific approval for this FYP is claimed. The user described a bounded university explanation task and instructed use of this assistant. Original teacher/model statements must reflect this decision, rather than silently treating Qwen as the selected teacher or final student.

## Review and reproduce

- [Frozen plan and input packets](../evidence/teacher_pilot/assistant_20261012/packets/plan.json)
- [Actual raw teacher batches](../evidence/teacher_pilot/assistant_20261012/raw/)
- [Verification and exact outcomes](../evidence/teacher_pilot/assistant_20261012/verified/verification.json)
- [Four training examples](../evidence/teacher_pilot/assistant_20261012/verified/train.jsonl)
- [Two validation examples](../evidence/teacher_pilot/assistant_20261012/verified/validation.jsonl)
- [Measured export size and training readiness](../evidence/teacher_dataset_readiness_20261012.json)

From the working root, `python -B GPT_MIDEVAL/tools/verify_teacher_pilot_evidence.py` replays exact source/packet/raw-output/persistence/verifier/export identities. The Streamlit **Teacher Study** tab replays evidence before display, compares actual teacher prose with the deterministic guide and offers separate training/validation downloads. It does not generate new examples or train a model.

Seven explicitly labelled fixture tests check date grouping, missing reference answers, fixture exclusion, rejection of incorrect prose despite correct payloads, freeze tampering, separate exports and copied-file persistence replay. Twenty actual Streamlit widget tests pass, including the new teacher view and its invalid/missing-evidence paths. These tests are engineering checks, not student-model results.

## Next execution

Expand teacher data deliberately after reviewing the pilot and source coverage; keep raw failures and frozen splits. Load an original Microsoft Phi-3-mini checkpoint/tokenizer in a supported isolated training environment, measure the complete input/target token lengths, then run a memory/load smoke test before training. The inspected RTX 3080 has 10,240 MiB; the proposal's 16 GB envelope does not demonstrate feasibility on this machine. Torch, Transformers, PEFT, bitsandbytes, datasets and accelerate are absent from the inspected viewer runtime.

Student baseline inference, QLoRA training and the teacher/original-student/adapted-student comparison remain unexecuted. No fine-tuning benefit, human-understanding result, prediction improvement or investor suitability is claimed. No task currently needs Astra.
