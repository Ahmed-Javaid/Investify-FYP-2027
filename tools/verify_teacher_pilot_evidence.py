"""Replay saved real assistant teacher prose and exact training/validation exports."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code/src'))
from investify.explain.teacher_session import import_responses, export_rows, prepare_packets, digest

PILOT = ROOT / 'evidence/teacher_pilot/assistant_20261012'


def main():
    plan = json.loads((PILOT / 'packets/plan.json').read_text(encoding='utf-8'))
    saved = json.loads((PILOT / 'verified/verification.json').read_text(encoding='utf-8'))
    viewer = ROOT / 'code/artifacts/mid_eval/teacher_pilot/assistant_20261012'
    for folder in ('packets', 'raw', 'verified'):
        for path in (PILOT / folder).iterdir():
            mirror = viewer / path.relative_to(PILOT)
            if path.read_bytes() != mirror.read_bytes(): raise ValueError('Viewer teacher evidence differs from the preserved research source')
    if saved['execution_kind'] != 'actual_assistant_session':
        raise ValueError('Unit fixtures cannot be described as actual teacher evidence')
    for packet in prepare_packets(plan):
        actual = json.loads((PILOT / 'packets' / (packet['packet_id'] + '.json')).read_text(encoding='utf-8'))
        if digest(actual) != digest(packet): raise ValueError('Copied teacher packet changed')
    paths = [PILOT / 'raw' / batch['file'] for batch in saved['raw_batches']]
    replay = import_responses(plan, paths, persistence=saved['raw_batches'])
    if replay != saved: raise ValueError('Raw teacher outcomes differ from original verification receipt')
    hashes = {}
    for split in ('train', 'validation'):
        expected = ''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n' for row in export_rows(replay, split))
        path = PILOT / 'verified' / (split + '.jsonl')
        if path.read_text(encoding='utf-8') != expected: raise ValueError('Student export differs from accepted original teacher examples')
        hashes[split] = hashlib.sha256(path.read_bytes()).hexdigest()
    dates = [{item['session_date'] for item in replay['outcomes'] if item['split'] == split} for split in ('train', 'validation')]
    if dates[0] & dates[1] or (dates[0] | dates[1]) & set(plan['heldout_dates']):
        raise ValueError('Training/validation dates or held-out identities overlap')
    if replay['accepted'] != 6 or replay['rejected'] or replay['missing_record_ids']:
        raise ValueError('Pilot differs from the recorded six accepted examples; retain failures and revise its status')
    print('Replayed 6 actual assistant teacher explanations: 4 train, 2 validation; 38 held-out dates excluded; no student training')
    print('Original raw persistence times and exact exported bytes match:', hashes)


if __name__ == '__main__': main()
