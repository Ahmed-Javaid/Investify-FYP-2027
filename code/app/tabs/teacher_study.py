"""Read/replay the actual teacher pilot; no inference or training from the UI."""
import json
from pathlib import Path

import streamlit as st

from investify.explain.teacher_session import import_responses, export_rows, prepare_packets, digest
from investify.explain.template import render_guided
from investify.decision_record import DecisionRecord

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / 'artifacts/mid_eval/teacher_pilot/assistant_20261012'


def read(path):
    raw = path.read_bytes()
    if len(raw) > 5 * 1024 * 1024: raise ValueError('Teacher viewer input exceeds its five-megabyte limit')
    return json.loads(raw)


def load_study():
    plan = read(PILOT / 'packets/plan.json')
    saved = read(PILOT / 'verified/verification.json')
    for packet in prepare_packets(plan):
        if digest(read(PILOT / 'packets' / (packet['packet_id'] + '.json'))) != digest(packet):
            raise ValueError('Retained teacher packet differs from its frozen input')
    paths = [PILOT / 'raw' / batch['file'] for batch in saved['raw_batches']]
    current = import_responses(plan, paths, persistence=saved['raw_batches'])
    if current != saved or current['execution_kind'] != 'actual_assistant_session':
        raise ValueError('Teacher evidence no longer matches actual raw assistant prose')
    prose = {row['record_id']: row['text'] for path in paths for row in read(path)['responses']}
    exports = {}
    for split in ('train', 'validation'):
        exports[split] = ''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n' for row in export_rows(current, split))
        if (PILOT / 'verified' / (split + '.jsonl')).read_text(encoding='utf-8') != exports[split]:
            raise ValueError('Teacher export differs from its accepted raw examples')
    return plan, current, prose, exports


def render():
    st.markdown('## Recorded teacher pilot')
    st.caption('The current assistant writes examples; the planned local student is Phi-3-mini. No student has been trained or evaluated.')
    try:
        plan, result, prose, exports = load_study()
    except FileNotFoundError:
        st.info('Teacher pilot pending. No saved teacher outcomes are available.')
        return
    except (OSError, KeyError, TypeError, ValueError) as error:
        st.error('Teacher evidence invalid. Training examples are not offered for download.')
        with st.expander('Teacher evidence validation details'): st.code(str(error), language=None)
        return
    st.warning('Construction pilot only. All source decisions are Buy; controlled wording passes a bounded verifier. Fine-tuning benefit and user understanding remain unmeasured.')
    st.write('Teacher: OpenAI assistant session, GPT-6 family as system-disclosed. Exact serving model ID and revision are unavailable.')
    st.caption(result['target_construction'])
    cols = st.columns(4)
    cols[0].metric('Accepted teacher examples', result['accepted'])
    cols[1].metric('Rejected teacher examples', result['rejected'])
    cols[2].metric('Training examples', len(export_rows(result, 'train')))
    cols[3].metric('Validation examples', len(export_rows(result, 'validation')))
    st.caption(f"Both corpora share date groups: {len(plan['training_dates'])} training dates, {len(plan['validation_dates'])} validation dates, {len(plan['heldout_dates'])} held-out test dates. Test records are excluded from teacher packets and training exports.")
    rows = [{'record': row['record_id'], 'split': row['split'], 'status': row['status'],
             'numeric_fidelity': row['verification']['numeric_fidelity'],
             'directional_consistency': row['verification']['directional_consistency'],
             'claim_recall': row['verification']['claim_recall'],
             'unverifiable_rate': row['verification']['unverifiable_rate']} for row in result['outcomes']]
    st.dataframe(rows, hide_index=True, width='stretch')
    selected = st.selectbox('Review a teacher example', [row['record_id'] for row in result['outcomes']], key='teacher_record')
    identity = next(row for row in result['outcomes'] if row['record_id'] == selected)
    raw = read(ROOT / 'artifacts' / ('decision_records_alpaca.json' if identity['corpus'] == 'alpaca' else 'decision_records.json'))
    record = next(DecisionRecord.from_dict(row) for row in raw['decision_records'] if row['session_date'] == identity['session_date'])
    # These are immutable evidence views. Refresh both widget states when the
    # record changes so a disabled text area cannot retain another case's text.
    st.session_state['teacher_prose'] = prose[selected]
    st.session_state['teacher_reference'] = render_guided(record).text
    left, right = st.columns(2)
    with left:
        st.text_area('Actual assistant-written prose', height=520, disabled=True, key='teacher_prose')
    with right:
        st.text_area('Deterministic complete guide for comparison', height=520, disabled=True, key='teacher_reference')
    st.caption('The teacher packet supplied facts, definitions and sentence patterns, without a completed answer. The deterministic guide shown here is a separate comparison.')
    for split in ('train', 'validation'):
        st.download_button(f'Download verified teacher {split} examples', exports[split], file_name=f'teacher_{split}.jsonl',
                           mime='application/jsonl', key='download_teacher_' + split)
