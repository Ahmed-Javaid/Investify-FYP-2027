"""Labelled teacher fixtures; no actual model generation or neural training."""
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.explain.teacher_session import (
    freeze_plan, prepare_packets, verify_plan, import_responses, export_rows, digest, _records, PROTOCOL)
from investify.explain.template import render_guided


class TeacherSessionTests(unittest.TestCase):
    def setUp(self):
        self.plan = freeze_plan(frozen_utc='2026-10-12T00:00:00Z')
        self.packets = prepare_packets(self.plan)

    def raw_fixture(self, directory, index=0):
        records, _ = _records(ROOT / 'artifacts')
        packet = self.packets[index]
        responses = []
        for item in packet['records']:
            identity = next(row for row in self.plan['selected_records'] if row['record_id'] == item['record_id'])
            record = records[identity['corpus']][identity['session_date']]
            responses.append({'record_id': item['record_id'], 'text': render_guided(record).text})
        raw = {'protocol': PROTOCOL, 'packet_sha256': packet['packet_sha256'],
               'generation_kind': 'labelled_unit_fixture', 'responses': responses}
        path = Path(directory) / (packet['packet_id'] + '-LABELLED-FIXTURE.json')
        path.write_text(json.dumps(raw), encoding='utf-8')
        os.utime(path, (1791849600, 1791849600))  # 13 October, after fixture freeze.
        return path, raw

    def test_grouped_splits_preserve_the_previous_heldout_dates(self):
        self.assertEqual([len(self.plan[key]) for key in ('training_dates', 'validation_dates', 'heldout_dates')], [118, 30, 38])
        self.assertLess(max(self.plan['training_dates']), min(self.plan['validation_dates']))
        self.assertLess(max(self.plan['validation_dates']), min(self.plan['heldout_dates']))
        self.assertFalse(set(self.plan['training_dates']) & set(self.plan['heldout_dates']))
        for date in {row['session_date'] for row in self.plan['selected_records']}:
            rows = [row for row in self.plan['selected_records'] if row['session_date'] == date]
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({row['split'] for row in rows}), 1)

    def test_teacher_packet_has_facts_patterns_and_no_completed_reference_answer(self):
        self.assertEqual(len(self.packets), 3)
        for packet in self.packets:
            self.assertEqual(packet['packet_sha256'], digest({key: value for key, value in packet.items() if key != 'packet_sha256'}))
            self.assertNotIn('reference_text', json.dumps(packet))
            self.assertNotIn('reference_payload', json.dumps(packet))
            self.assertNotIn('student_example', json.dumps(packet))
        self.assertIsNone(self.plan['teacher']['serving_model_id'])
        self.assertIsNone(self.plan['teacher']['serving_revision'])
        self.assertFalse(self.plan['student']['qlora_executed'])

    def test_fixtures_cannot_be_imported_as_research_outcomes(self):
        with tempfile.TemporaryDirectory(prefix='investify-teacher-fixture-') as directory:
            path, _ = self.raw_fixture(directory)
            with self.assertRaisesRegex(ValueError, 'test fixtures are never research'):
                import_responses(self.plan, [path])
            report = import_responses(self.plan, [path], _allow_fixture=True)
            self.assertEqual(report['execution_kind'], 'labelled_unit_fixture')

    def test_correct_payload_cannot_mask_wrong_teacher_prose(self):
        with tempfile.TemporaryDirectory(prefix='investify-teacher-fixture-') as directory:
            path, raw = self.raw_fixture(directory)
            raw['responses'][0]['text'] = raw['responses'][0]['text'].replace('5-day horizon): Buy.', '5-day horizon): Sell.')
            path.write_text(json.dumps(raw), encoding='utf-8')
            os.utime(path, (1791849600, 1791849600))
            report = import_responses(self.plan, [path], _allow_fixture=True)
            self.assertEqual(report['rejected'], 1)
            self.assertIsNone(report['outcomes'][0]['student_example'])
            self.assertEqual(len(export_rows(report, 'train')), 1)
            self.assertEqual(len(report['missing_record_ids']), 4)

    def test_source_prompt_and_split_drift_are_refused_before_import(self):
        for kind in ('source', 'teacher', 'prompt', 'split'):
            plan = copy.deepcopy(self.plan)
            if kind == 'source': plan['source_code_sha256']['UNDECLARED_FIXTURE'] = '0' * 64
            elif kind == 'teacher': plan['teacher']['serving_revision'] = 'invented-fixture-revision'
            elif kind == 'prompt': plan['teacher_prompt'] += 'altered fixture'
            else: plan['training_dates'].append(plan['heldout_dates'][0])
            with self.assertRaises(ValueError, msg=kind): verify_plan(plan)

    def test_actual_exports_keep_validation_out_of_training_and_disclose_hybrid_targets(self):
        with tempfile.TemporaryDirectory(prefix='investify-teacher-fixture-') as directory:
            paths = [self.raw_fixture(directory, index)[0] for index in range(3)]
            report = import_responses(self.plan, paths, _allow_fixture=True)
            self.assertEqual(report['accepted'], 6)
            self.assertEqual(len(export_rows(report, 'train')), 4)
            self.assertEqual(len(export_rows(report, 'validation')), 2)
            self.assertIn('not claimed as teacher-generated', report['target_construction'])
            self.assertFalse(report['qlora_executed'])
            train_dates = {json.loads(row['messages'][1]['content'])['evidence']['session_date'] for row in export_rows(report, 'train')}
            validation_dates = {json.loads(row['messages'][1]['content'])['evidence']['session_date'] for row in export_rows(report, 'validation')}
            self.assertFalse(train_dates & validation_dates)

    def test_copied_files_replay_hash_bound_original_persistence_times(self):
        with tempfile.TemporaryDirectory(prefix='investify-teacher-fixture-') as directory:
            path, _ = self.raw_fixture(directory)
            before = import_responses(self.plan, [path], _allow_fixture=True)
            os.utime(path, (946684800, 946684800))
            with self.assertRaises(ValueError): import_responses(self.plan, [path], _allow_fixture=True)
            after = import_responses(self.plan, [path], persistence=before['raw_batches'], _allow_fixture=True)
            self.assertEqual(before, after)


if __name__ == '__main__': unittest.main()
