"""Reconcile current model roles with the completed teacher pilot; preserve drafts."""
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'evidence/teacher_pilot/assistant_20261012/verified/verification.json'
data = json.loads(RECEIPT.read_text(encoding='utf-8'))
tests = ET.parse(ROOT / 'evidence/current_tests_teacher_20261012.xml')
if data['execution_kind'] != 'actual_assistant_session' or data['accepted'] != 6 or data['rejected'] or data['missing_record_ids']:
    raise ValueError('Current materials require the actual complete teacher pilot, without hidden failures')
if any(tests.findall('.//' + kind) for kind in ('failure', 'error', 'skipped')):
    raise ValueError('Use a complete passing current selected-suite receipt')
count = len(tests.findall('.//testcase'))
ui_count = sum('StreamlitMidEvalTests' in case.get('classname', '') for case in tests.findall('.//testcase'))


def write(relative, text):
    path = ROOT / relative
    history = ROOT / 'planning/history/before_assistant_teacher' / relative
    if path.exists() and not history.exists():
        history.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, history)
    path.write_text(text, encoding='utf-8')


def prepend(relative, paragraph):
    text = (ROOT / relative).read_text(encoding='utf-8-sig')
    if paragraph in text: return
    first, rest = text.split('\n', 1)
    write(relative, first + '\n\n' + paragraph + '\n' + rest)


current = f'''## Current teacher workflow - 12 October 2026

Latest user direction: use the current assistant as teacher first; Mistral is a fallback. The active student remains the proposal's Phi-3-mini family, with exact original checkpoint and local training setup pending. No Qwen teacher download is required. Earlier Qwen pilot declarations below are historical/inactive, not the selected teacher or final student.

Actual assistant teacher pilot: six saved NVDA explanations, all six accepted by the existing strict verifier, four training/two validation examples. The program assembles the factual JSON payload from the original record; the prose is actually assistant-generated. This hybrid construction is disclosed. Packets supplied facts/definitions/patterns without a completed answer. Exact serving ID/revision, token usage, decoding and per-example latency are unavailable, not invented.

Both corpora are grouped by trading date: 118 training dates, 30 validation dates, 38 unchanged held-out test dates. Test records are excluded from teacher packets and exports. All actual source decisions are Buy; the six-example pilot does not establish sufficient data, Hold/Sell generalization, QLoRA benefit or user comprehension. Original social AI references remain unchanged and their classifier study is separate.

Current checks: {count} selected tests, zero skips, including {ui_count} Streamlit cases. Teacher Study displays/replays actual examples and offers separate exports. tools/verify_teacher_pilot_evidence.py reproduces exact raw-output/source/persistence/verifier/export identities, including copied-file replay. No student inference/training occurred. The inspected RTX 3080 has 10,240 MiB and the viewer lacks Torch/Transformers/PEFT/bitsandbytes/datasets/accelerate. Exact tokenizer lengths and a training-memory smoke test are prerequisites, not measured outcomes.

Read deliverables/ASSISTANT_TEACHER_PILOT.md and evidence/teacher_pilot/assistant_20261012. Preserve all 224 originals, original source/label freezes and dated bundles. Current source changes remain uncommitted; no push/publication. No specific task needs Astra. Continue beyond this checkpoint without treating six examples as a completed student study.

### Earlier checkpoint, superseded for active teacher/student roles
'''
prepend('planning/NEXT_CHAT.md', current)
prepend('planning/CHECKPOINT.md', current)
prepend('planning/MID_EVAL_PLAN.md', '''## Current teacher work

The user chose the current assistant as teacher first, with Mistral as a fallback. Six actual explanations pass the current bounded verifier and produce four training/two validation examples with date-grouped splits. The proposal's Phi-3-mini remains the student family; no final checkpoint, student baseline inference or QLoRA training is complete. Do not require the previously proposed Qwen teacher download. Dataset expansion, exact tokenizer/context/VRAM measurement and a supported training runtime precede student training. See deliverables/ASSISTANT_TEACHER_PILOT.md. Earlier model-specific pilot choices below are superseded.''')
prepend('deliverables/OFFICIAL_MODEL_POLICY.md', '''## Active model roles

The user instructed use of the current OpenAI assistant session as teacher before considering Mistral. Six actual teacher examples now exist. Phi-3-mini remains the proposal's student family; its exact original Microsoft checkpoint is pending. No additional Qwen teacher download is required. Qwen entries/commands below describe earlier optional local inference experiments and are inactive for the selected teacher/student workflow.

Use original publisher weights for the student baseline. The project's later QLoRA adapter is the proposed adaptation and must be versioned/disclosed separately from unchanged original weights. The user exclusion of third-party modified variants does not erase the project's own planned QLoRA study. No provider-specific approval is claimed; the bounded university scope and current assistant choice are recorded in the teacher pilot.''')
prepend('deliverables/MODELS_AND_EVALUATION.md', '''## Active teacher and student

Current assistant session: actual teacher, six accepted controlled-prose examples with null exact serving identity/revision. Phi-3-mini: planned local student, exact Microsoft checkpoint and training setup pending. Original and QLoRA-adapted student comparison is unexecuted. Four training/two validation examples are a construction pilot, with factual JSON targets assembled from original records and disclosed separately. Earlier Qwen pilot selections below are inactive. See ASSISTANT_TEACHER_PILOT.md.''')
prepend('deliverables/LLM_DESIGN.md', '''## Active teacher workflow

The user chose the current assistant as teacher first. Its six actual controlled-prose explanations pass the current verifier; exact serving model ID/revision is unavailable. Student examples combine that actual prose with a deterministic factual payload from the original record, explicitly as hybrid supervision. Grouped date splits preserve the 38-date held-out test block; four examples are training and two validation. No student inference or QLoRA has run.

The proposal's Phi-3-mini remains the student family. The original open-weight teacher assumption is changed under the user's latest instruction; the original proposal is preserved. Qwen is not required as an additional teacher or chosen final student. Compare the recorded teacher, original student and QLoRA-adapted student only after the student checkpoint/runtime/tokenizer and adequate data are established. Keep numeric and complete-guided deterministic comparators. See ASSISTANT_TEACHER_PILOT.md. Earlier Qwen-specific pilot text below is historical/inactive.''')
prepend('code/docs/local_llm_pilot.md', '''## Current assistant teacher pilot

The selected teacher is the current assistant session, with six actual accepted explanations. The planned student remains Phi-3-mini; Qwen-specific local commands below are earlier optional experiments, not a required teacher download. The session teacher does not use this loopback client. See ../../deliverables/ASSISTANT_TEACHER_PILOT.md and the Teacher Study tab. Original/QLoRA student inference and training remain pending; zero local/API student completions must not be confused with the six actual session-generated teacher explanations.''')
prepend('code/docs/mideval_increment.md', f'''## Recorded teacher increment

The Teacher Study tab replays six actual assistant explanations and separate four-training/two-validation exports, with date grouping and no held-out test inputs. No student model is trained or evaluated. Current selected suite: {count} passes, zero skips, including {ui_count} Streamlit cases. The teacher's exact serving identity/revision is unavailable; the factual JSON payload is constructed from original records, while the prose is assistant-generated. See ../../deliverables/ASSISTANT_TEACHER_PILOT.md.''')
prepend('code/README.md', f'''Current teacher increment: six actual assistant-written explanations pass the bounded verifier; four training/two validation examples are exported. Teacher Study replays their source/prompt/raw-output/persistence checks. Phi-3-mini remains the student family, with no student baseline inference or QLoRA yet. Qwen is not a required teacher download. Current selected suite: {count} passes, including {ui_count} Streamlit cases. See ../deliverables/ASSISTANT_TEACHER_PILOT.md.''')
prepend('README.md', f'''Current teacher workflow: **this assistant is the teacher; Phi-3-mini remains the planned student**. Six actual explanations pass the verifier, with four training/two validation examples and excluded held-out test dates. No Qwen teacher download is required. No student inference/QLoRA has run. Read [the recorded teacher pilot](deliverables/ASSISTANT_TEACHER_PILOT.md). Current selected suite: {count} passes, zero skips, including {ui_count} Streamlit cases. Earlier model-selection notes and the four-page evidence brief describe prior snapshots.''')

teacher_section = r'''\section{Recorded Assistant Teacher Construction Pilot}
Under the user's latest direction, the current assistant supplies teacher examples before an alternative API is considered. The planned student remains Phi-3-mini; no additional Qwen teacher download is required. Six actual explanations were written from frozen historical NVDA records, and all six pass the current strict verifier. Input packets contain facts, reviewed definitions and controlled sentence patterns without a completed reference answer.

The supervision is hybrid: prose is actually assistant-generated, while the factual JSON payload is assembled deterministically from the original record. Both are checked, but the payload is not claimed as a teacher completion. Exact serving model ID/revision, decoding, token usage and per-example inference latency are unavailable and recorded as null.

Both corpora share date groups: 118 training dates, 30 validation dates and 38 preserved held-out test dates. The actual pilot has four training and two validation examples; test records are excluded. All saved source decisions are Buy, so neither class generalization nor adequate QLoRA data is established. Some held-out examples were previously explored; no first-ever untouched-test claim is made. Copied evidence replays original hash-bound raw persistence times and exact exports.

Original-student inference, QLoRA training, student quality and user understanding remain unmeasured. The inspected GPU has 10,240 MiB; the proposal's 16 GB envelope does not establish current-machine feasibility. Required training libraries, exact student checkpoint/tokenizer and measured token/VRAM budgets remain pending. Earlier Qwen-specific local pilot choices are inactive for the selected teacher/student workflow.
'''
for chapter in ('chapter6_iteration1.tex', 'chapter8_testing.tex', 'chapter9_development_evidence.tex'):
    relative = 'report/chapters/' + chapter
    text = (ROOT / relative).read_text(encoding='utf-8-sig')
    if teacher_section not in text: write(relative, text + '\n' + teacher_section)
for chapter in ('04_abstract.tex', '06_executive_summary.tex', 'conclusion.tex'):
    relative = 'report/chapters/' + chapter
    text = (ROOT / relative).read_text(encoding='utf-8-sig')
    addition = '\nThe current assistant teacher construction pilot records six actual verified explanations with four training and two validation examples; the planned Phi-3-mini student remains untrained. Exact teacher serving revision is unavailable, factual JSON supervision is assembled from original records, and no fine-tuning efficacy or human-understanding result is claimed.\n'
    if addition not in text: write(relative, text + addition)

relative = 'deliverables/presentation_outline.json'
deck = json.loads((ROOT / relative).read_text(encoding='utf-8'))
slide = deck['slides'][6]
slide['title'] = 'Teacher and student explanation study'
slide['table']['rows'] = [
    ['Complete guided template', 'Deterministic facts, definitions and scope', 'All 372 records validate'],
    ['Current assistant teacher', 'Six actual controlled-prose examples; factual JSON assembled from records', '6 accepted; 4 training / 2 validation'],
    ['Original Phi-3-mini student', 'Prompted student before adaptation', 'Exact checkpoint/runtime/inference pending'],
    ['QLoRA-adapted Phi-3-mini', 'Same student trained on accepted examples', 'Not trained; efficacy unmeasured']]
slide['speaker_notes'] = 'The user selected the current assistant as teacher; an additional Qwen teacher download is not required. The original open-weight teacher assumption is changed, with the original proposal preserved. Raw prose is actually assistant-generated, the structured payload is deterministic hybrid supervision. Both are checked. Exact teacher serving revision is unavailable. Training and validation are grouped by trading date, and the final 38-date test block is excluded. Six all-Buy examples do not establish adequate training data, student performance or human understanding.'
slide['sources'] = ['deliverables/ASSISTANT_TEACHER_PILOT.md', 'evidence/teacher_pilot/assistant_20261012/packets/plan.json',
                    'evidence/teacher_pilot/assistant_20261012/verified/verification.json']
deck['slides'][7]['table']['rows'][-1] = ['Actual assistant teacher prose', '6 explanations verified', 'Student/QLoRA outcomes remain unmeasured']
deck['slides'][10]['body'] = [line for line in deck['slides'][10]['body'] if 'original publisher weights' not in line]
deck['slides'][10]['body'].append('Expand recorded teacher data; establish original Phi-3-mini tokenizer/runtime and measured memory budget before QLoRA.')
write(relative, json.dumps(deck, indent=2, ensure_ascii=False))
print(f'Reconciled active teacher/student roles; {count} selected passes, {ui_count} Streamlit cases; prior drafts preserved')
