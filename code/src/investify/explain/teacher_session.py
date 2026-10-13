"""Recorded assistant teacher prose with deterministic factual JSON supervision.

This module prepares inputs and verifies/imports actual saved assistant prose.
It never synthesizes teacher responses or invokes an inference provider. Tests
must explicitly identify algorithm-generated responses as unit fixtures.
"""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from investify.decision_record import DecisionRecord
from investify.explain.context import build_context, ATTRIBUTION_SCOPE
from investify.explain.local_llm import verify_generated, response_schema
from investify.explain.template import Explanation, render_guided

ROOT = Path(__file__).resolve().parents[3]
FILES = {'alpaca': 'decision_records_alpaca.json', 'fnspid': 'decision_records.json'}
PROTOCOL = 'investify-recorded-assistant-teacher-v1'
PROMPT_VERSION = 'record-facts-to-complete-controlled-prose-v1'
TEACHER = {'kind': 'current_assistant_session', 'provider': 'OpenAI', 'model_family': 'GPT-6',
           'serving_model_id': None, 'serving_revision': None,
           'identity_source': 'Current assistant system describes an agent based on GPT-6; no serving identity/revision endpoint is exposed.',
           'raw_output_transport': 'Actual assistant-written tool arguments persisted as JSON, not a local/API completion envelope.',
           'decoding_parameters': None, 'token_usage': None, 'per_example_inference_latency_seconds': None}
PROMPT = '''Act as the teacher for a small university explanation-model pilot. The supplied historical decision record and reviewed definitions are authoritative. Write the complete explanation text from those facts. Do not produce a stock prediction, introduce a market cause, infer user suitability, invent social sentiment, claim live freshness, or expose hidden reasoning. Use the controlled sentence patterns below so the existing strict verifier can check each displayed claim. Supply one sentence per line, no extra headings. Interleave each feature's recorded evidence with its definition to make the evidence readable. Include all eleven features, both family totals, all top-ranked contributions, the full class distribution, attribution scope and the exact notice. The packet does not contain a completed answer.
Sentence patterns (substitute actual facts; percentages use two decimals, values and signed SHAP use four decimals):
{ticker} decision for session {session_date} ({horizon_days}-day horizon): {decision}.
Calibrated confidence in this decision: {confidence_percent}%.
Full probability breakdown -- Buy: {Buy_percent}%, Hold: {Hold_percent}%, Sell: {Sell_percent}%.
{feature} (value {value_or_missing}) {supports_or_opposes} the {decision} decision with a SHAP contribution of {signed_shap}, ranked #{rank} of {top_k_count}.
Recorded feature {feature} (value {value_or_missing}): SHAP {signed_shap} for {decision}; effect {supports_opposes_or_neutral}.
Feature definition for {feature}: {exact_reviewed_meaning}
Family contribution for {family}: SHAP {signed_family_shap} for {decision}; effect {supports_opposes_or_neutral}.
Copy the exact attribution-scope disclosure and advisory notice. The output is JSON containing record_id and text for each matching packet record. Do not output a completed factual payload: the program constructs that separately from the saved record, and this hybrid supervision is explicitly disclosed.'''
STUDENT_INSTRUCTION = '''Explain the supplied historical educational decision using only its recorded facts and reviewed definitions. Return a JSON object with text and payload under the supplied response schema. Use the supplied controlled sentence patterns. Preserve every feature value, attribution, direction, definition, family total, ranked contributor, class probability, attribution scope and advisory notice. Do not invent causes, social observations, risk conditioning, live freshness, returns or guarantees.'''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                   allow_nan=False).encode('utf-8')).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def _time(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None or result.utcoffset().total_seconds() != 0:
        raise ValueError('Teacher times must be explicitly UTC')
    return result


def _records(artifacts):
    records, hashes = {}, {}
    for corpus, filename in FILES.items():
        path = Path(artifacts) / filename
        raw = path.read_bytes()
        hashes[corpus] = hashlib.sha256(raw).hexdigest()
        rows = [DecisionRecord.from_dict(item) for item in json.loads(raw)['decision_records']]
        rows.sort(key=lambda row: row.session_date)
        if not rows or len({row.session_date for row in rows}) != len(rows):
            raise ValueError('Need unique recorded sessions in each historical corpus')
        if len({(row.ticker, row.horizon_days) for row in rows}) != 1:
            raise ValueError('Each teacher corpus must use one declared ticker/horizon')
        records[corpus] = {row.session_date: row for row in rows}
    if set(records['alpaca']) != set(records['fnspid']):
        raise ValueError('Group both corpora by the same dates; do not silently intersect away missing sessions')
    return records, hashes


def _sources():
    paths = [Path(__file__), ROOT / 'src/investify/decision_record.py',
             ROOT / 'src/investify/explain/context.py', ROOT / 'src/investify/explain/template.py',
             ROOT / 'src/investify/explain/verifier.py', ROOT / 'src/investify/explain/local_llm.py',
             ROOT / 'scripts/record_teacher_session.py']
    return {str(path.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def freeze_plan(artifacts=ROOT / 'artifacts', *, frozen_utc=None):
    records, hashes = _records(artifacts)
    dates = sorted(records['alpaca'])
    development_end = 4 * len(dates) // 5
    training_end = 4 * development_end // 5
    training, validation, heldout = dates[:training_end], dates[training_end:development_end], dates[development_end:]
    if min(len(training), len(validation), len(heldout)) < 2:
        raise ValueError('Insufficient distinct dates for teacher training/validation/test separation')
    # Declare six examples before any teacher outputs: two training dates and
    # the validation midpoint, each represented in BOTH corpora.
    chosen = [('train', training[0]), ('train', training[-1]), ('validation', validation[len(validation) // 2])]
    selected = []
    for split, date in chosen:
        for corpus in FILES:
            record = records[corpus][date]
            selected.append({'record_id': f'{corpus}:{record.ticker}:{date}:{record.horizon_days}d',
                             'corpus': corpus, 'session_date': date, 'split': split,
                             'record_sha256': digest(record.to_dict())})
    frozen = frozen_utc or utc()
    _time(frozen)
    return {'protocol': PROTOCOL, 'frozen_utc': frozen, 'teacher': TEACHER,
            'student': {'proposal_model_family': 'Microsoft Phi-3-mini', 'exact_checkpoint': None,
                        'qlora_executed': False},
            'source_artifact_sha256': hashes, 'source_code_sha256': _sources(),
            'split_rule': 'Group both historical corpora by trading date; first 80% dates are development, first 80% of development dates train, remaining development dates validation; final 20% unchanged held-out test.',
            'training_dates': training, 'validation_dates': validation, 'heldout_dates': heldout,
            'selected_records': selected, 'teacher_prompt_version': PROMPT_VERSION,
            'teacher_prompt': PROMPT, 'teacher_prompt_sha256': hashlib.sha256(PROMPT.encode()).hexdigest(),
            'student_instruction': STUDENT_INSTRUCTION,
            'target_construction': 'Hybrid supervision: actual assistant-generated prose plus factual structured payload deterministically built from the original record. Both are checked, but the payload is not claimed as teacher-generated.',
            'source_decision_counts': {corpus: dict(Counter(row.decision for row in rows.values())) for corpus, rows in records.items()},
            'limitation': 'Six-example exploratory construction pilot on saved constant-Buy NVDA records. Not sufficient for QLoRA efficacy, generalization across decision classes, comprehension, predictive skill or suitability claims. Some held-out examples were explored in earlier withdrawn inference runs; this is not a first-ever untouched test declaration.'}


def verify_plan(plan, artifacts=ROOT / 'artifacts'):
    expected = freeze_plan(artifacts, frozen_utc=plan['frozen_utc'])
    if plan.get('source_code_sha256') != expected['source_code_sha256']:
        archive = Path(__file__).parent / 'archive_v4'
        original = json.loads((archive / 'source_hashes.json').read_text(encoding='utf-8'))
        if plan.get('source_code_sha256') != original:
            raise ValueError('Teacher source identity is neither current nor the retained v4 source')
        for name, recorded in original.items():
            snapshot = archive / name
            if hashlib.sha256(snapshot.read_bytes()).hexdigest() != recorded:
                raise ValueError('Retained teacher source bytes changed')
        # Default render/verify behavior remains compatible with this retained grammar.
        # Policy-aware explanations are a new engineering path, never old study outputs.
        expected['source_code_sha256'] = original
    if plan != expected:
        raise ValueError('Teacher data, grouped splits, selected records, prompt, identity or source changed after freezing')


def student_input(record, corpus):
    return {'prompt_version': PROMPT_VERSION, 'evidence': build_context(record, corpus=corpus),
            'ranked_contributors': record.to_dict()['top_k'], 'response_schema': response_schema(record),
            'controlled_sentence_patterns': PROMPT.split('Sentence patterns', 1)[1].split('Copy the exact', 1)[0],
            'attribution_scope': ATTRIBUTION_SCOPE}


def prepare_packets(plan, artifacts=ROOT / 'artifacts'):
    verify_plan(plan, artifacts)
    records, _ = _records(artifacts)
    packets = []
    for index in range(0, len(plan['selected_records']), 2):
        selected = plan['selected_records'][index:index + 2]
        rows = []
        for identity in selected:
            record = records[identity['corpus']][identity['session_date']]
            rows.append({'record_id': identity['record_id'], 'record_sha256': identity['record_sha256'],
                         'split': identity['split'], 'input': student_input(record, identity['corpus'])})
        packet = {'protocol': PROTOCOL, 'plan_sha256': digest(plan), 'packet_id': f'batch-{index // 2 + 1:02}',
                  'teacher_prompt': PROMPT, 'records': rows}
        packet['packet_sha256'] = digest(packet)
        packets.append(packet)
    return packets


def import_responses(plan, raw_paths, artifacts=ROOT / 'artifacts', *, persistence=None, _allow_fixture=False):
    verify_plan(plan, artifacts)
    records, _ = _records(artifacts)
    packets = {item['packet_sha256']: item for item in prepare_packets(plan, artifacts)}
    selected = {item['record_id']: item for item in plan['selected_records']}
    replay = {item['file']: item for item in persistence} if persistence is not None else None
    batches, seen_packets, outcomes = [], set(), {}
    for raw_path in raw_paths:
        path = Path(raw_path)
        raw = path.read_bytes()
        def invalid(value): raise ValueError(f'Non-finite teacher JSON: {value}')
        data = json.loads(raw, parse_constant=invalid)
        if (not isinstance(data, dict) or set(data) != {'protocol', 'packet_sha256', 'generation_kind', 'responses'}
                or data['protocol'] != PROTOCOL or data['packet_sha256'] not in packets
                or data['packet_sha256'] in seen_packets):
            raise ValueError('Raw teacher batch must identify one exact unused prepared packet')
        if data['generation_kind'] != 'actual_assistant_session' and not (
                _allow_fixture and data['generation_kind'] == 'labelled_unit_fixture'):
            raise ValueError('Research import requires actual assistant prose; test fixtures are never research outcomes')
        seen_packets.add(data['packet_sha256'])
        packet = packets[data['packet_sha256']]
        expected = {row['record_id'] for row in packet['records']}
        if (not isinstance(data['responses'], list) or any(not isinstance(row, dict) for row in data['responses'])
                or len(data['responses']) != len(expected)
                or {row.get('record_id') for row in data['responses']} != expected):
            raise ValueError('Each raw teacher batch must exactly cover its two packet records')
        checksum = hashlib.sha256(raw).hexdigest()
        timestamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        if replay is not None:
            if path.name not in replay: raise ValueError('Missing original raw-batch persistence receipt')
            entry = replay[path.name]
            if entry['sha256'] != checksum or entry['packet_sha256'] != data['packet_sha256']:
                raise ValueError('Copied raw teacher batch differs from original hash-bound persistence receipt')
            timestamp = entry['persisted_utc']
        if _time(timestamp) < _time(plan['frozen_utc']):
            raise ValueError('Teacher output must follow its prepared frozen plan')
        batches.append({'file': path.name, 'sha256': checksum, 'packet_sha256': data['packet_sha256'],
                        'persisted_utc': timestamp, 'generation_kind': data['generation_kind']})
        for row in data['responses']:
            if set(row) != {'record_id', 'text'} or not isinstance(row['text'], str) or not row['text'].strip():
                raise ValueError('Every teacher response must retain actual nonempty prose and exact record identity')
            identity = selected[row['record_id']]
            record = records[identity['corpus']][identity['session_date']]
            fixed_payload = render_guided(record).payload
            result = verify_generated(record, Explanation(row['text'], fixed_payload))
            outcome = {**identity, 'input_sha256': digest(student_input(record, identity['corpus'])),
                       'raw_prose_sha256': hashlib.sha256(row['text'].encode()).hexdigest(),
                       'raw_batch_file': path.name, 'persisted_utc': timestamp,
                       'status': 'accepted' if result.passed else 'rejected',
                       'verification': {'passed': result.passed, 'numeric_fidelity': result.numeric_fidelity,
                           'directional_consistency': result.directional_consistency, 'claim_recall': result.claim_recall,
                           'unverifiable_rate': result.unverifiable_rate, 'failed_metrics': list(result.failed_metrics)},
                       'student_example': None}
            if result.passed:
                target = {'text': row['text'], 'payload': fixed_payload}
                outcome['student_example'] = {'messages': [
                    {'role': 'system', 'content': STUDENT_INSTRUCTION},
                    {'role': 'user', 'content': json.dumps(student_input(record, identity['corpus']), ensure_ascii=False, allow_nan=False)},
                    {'role': 'assistant', 'content': json.dumps(target, ensure_ascii=False, allow_nan=False)}]}
            outcomes[row['record_id']] = outcome
    ordered = [outcomes[item['record_id']] for item in plan['selected_records'] if item['record_id'] in outcomes]
    return {'protocol': PROTOCOL, 'plan_sha256': digest(plan), 'teacher': TEACHER,
            'execution_kind': 'labelled_unit_fixture' if any(item['generation_kind'] == 'labelled_unit_fixture' for item in batches) else 'actual_assistant_session',
            'raw_batches': batches, 'selected_records': len(selected), 'supplied_records': len(ordered),
            'accepted': sum(item['status'] == 'accepted' for item in ordered),
            'rejected': sum(item['status'] == 'rejected' for item in ordered),
            'missing_record_ids': [key for key in selected if key not in outcomes],
            'outcomes': ordered, 'target_construction': plan['target_construction'],
            'timestamp_scope': 'Raw file persistence times, not measured inference latency; copied files replay hash-bound original timestamps.',
            'qlora_executed': False, 'student_model_evaluated': False, 'limitation': plan['limitation']}


def export_rows(report, split):
    if split not in {'train', 'validation'}: raise ValueError('Only training and validation teacher targets are exported')
    return [item['student_example'] for item in report['outcomes']
            if item['split'] == split and item['status'] == 'accepted']
