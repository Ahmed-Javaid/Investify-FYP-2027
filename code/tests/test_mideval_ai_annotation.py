"""Labelled unit fixtures for AI provenance; never research annotations."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_mideval_sentiment_selection import fixture_benchmark, CHECKPOINTS
from investify.sentiment_selection import annotation_input, digest, validate_benchmark, freeze_plan, evaluate_predictions
from investify.sentiment_annotation import packets, attach_session_annotations, ANNOTATION_PROMPT, PROMPT_VERSION


def fixture_ai_benchmark(crosscheck=False):
    data = fixture_benchmark()
    selection = data['selection']
    selection['annotation_method'] = 'model_generated'
    run = {'run_id': 'fixture-ai-a', 'provider': 'Labelled fixture provider', 'model_id': 'fixture/annotator',
           'model_revision': None, 'identity_source': 'session_configuration',
           'identity_evidence': 'Labelled UNIT TEST ONLY; no real provider',
           'prompt_version': 'fixture-v1', 'prompt': 'Labelled fixture sentiment prompt',
           'input_contract': 'ticker_and_original_text_v1', 'candidate_predictions_visible': False,
           'raw_output_reference': 'LABELLED TEST ONLY, not an actual output artifact',
           'run_started_utc': '2026-10-03T11:00:00Z', 'run_completed_utc': '2026-10-03T13:00:00Z'}
    run['prompt_sha256'] = hashlib.sha256(run['prompt'].encode()).hexdigest()
    selection['annotation_runs'] = [run]
    if crosscheck:
        selection['annotation_runs'].append(dict(run, run_id='fixture-ai-b'))
    for post in data['posts']:
        label = post['annotator_a_label']
        for key in list(post):
            if key.startswith(('annotator_', 'annotated_')):
                del post[key]
        post['model_annotations'] = []
        for run in selection['annotation_runs']:
            response = {'label': label, 'reason': 'Labelled fixture explanation'}
            post['model_annotations'].append({'run_id': run['run_id'], **response,
                'raw_response': json.dumps(response), 'input_sha256': digest(annotation_input(post)),
                'annotated_at_utc': '2026-10-03T12:00:00Z'})
    return data


class AIAnnotationTests(unittest.TestCase):
    def imported_fixture(self, directory):
        data = fixture_ai_benchmark()
        run = data['selection'].pop('annotation_runs')[0]
        run.update(prompt=ANNOTATION_PROMPT, prompt_version=PROMPT_VERSION,
                   prompt_sha256=hashlib.sha256(ANNOTATION_PROMPT.encode()).hexdigest())
        labels = {post['post_id']: post.pop('model_annotations')[0]['label'] for post in data['posts']}
        paths = []
        for index, packet in enumerate(packets(data)):
            path = Path(directory) / f'labelled_unit_fixture_{index}.json'
            raw = {'packet_sha256': digest(packet), 'responses': [{'post_id': item['post_id'],
                   'label': labels[item['post_id']], 'reason': 'LABELLED UNIT FIXTURE, no actual inference'} for item in packet['items']]}
            path.write_text(json.dumps(raw), encoding='utf-8')
            paths.append(path)
        run['run_completed_utc'] = (datetime.fromtimestamp(max(path.stat().st_mtime for path in paths), timezone.utc)
                                    + timedelta(seconds=1)).isoformat()
        return data, run, paths

    def test_imported_raw_fixture_outputs_bind_inputs_and_leave_corpus_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus, run, paths = self.imported_fixture(directory)
            original = copy.deepcopy(corpus)
            data, receipt = attach_session_annotations(corpus, run, paths)
            self.assertEqual(corpus, original)
            self.assertEqual(len(validate_benchmark(data)), 200)
            self.assertEqual(receipt['benchmark_sha256'], digest(data))
            self.assertEqual(len(receipt['raw_batches']), 4)
            self.assertEqual(receipt['candidate_inference_calls'], 0)

    def test_missing_duplicate_or_tampered_raw_batches_fail_without_filling_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus, run, paths = self.imported_fixture(directory)
            with self.assertRaises(ValueError): attach_session_annotations(corpus, run, paths[:-1])
            with self.assertRaises(ValueError): attach_session_annotations(corpus, run, paths + paths[:1])
            corpus['posts'][0]['text'] += ' LABELLED INPUT TAMPERING'
            with self.assertRaises(ValueError): attach_session_annotations(corpus, run, paths)

    def test_copied_raw_files_replay_original_hashed_persistence_times(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus, run, paths = self.imported_fixture(directory)
            data, receipt = attach_session_annotations(corpus, run, paths)
            for path in paths:
                os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 86400))
            with self.assertRaises(ValueError): attach_session_annotations(corpus, run, paths)
            replay, _ = attach_session_annotations(corpus, run, paths, batch_receipts=receipt['raw_batches'])
            self.assertEqual(data, replay)
            receipt['raw_batches'][0]['sha256'] = 'LABELLED TAMPERED HASH'
            with self.assertRaises(ValueError):
                attach_session_annotations(corpus, run, paths, batch_receipts=receipt['raw_batches'])

    def test_blinded_packets_exclude_source_metadata_and_predictions(self):
        data = fixture_ai_benchmark()
        data['posts'][0]['candidate_prediction'] = 'LABELLED FIXTURE NEVER EXPOSE'
        data['posts'][0]['source_sentiment'] = 'LABELLED FIXTURE NEVER EXPOSE'
        packet = packets(data)[0]
        self.assertEqual(set(packet['items'][0]), {'post_id', 'ticker', 'text'})
        self.assertNotIn('NEVER EXPOSE', json.dumps(packet))

    def test_one_ai_pass_has_null_agreement_and_explicit_reference_scope(self):
        data = fixture_ai_benchmark()
        plan = freeze_plan(data, CHECKPOINTS, frozen_utc='2026-10-04T12:00:00Z')
        self.assertEqual(len(validate_benchmark(data)), 200)
        self.assertIsNone(plan['annotation_agreement']['initial_exact_agreement'])
        self.assertIsNone(plan['annotation_agreement']['cohens_kappa'])
        self.assertIn('not independently human-validated', plan['reference_scope'])
        self.assertEqual(plan['annotation_models'][0]['model_revision'], None)
        self.assertEqual(evaluate_predictions(data, plan, [])['annotation_method'], 'model_generated')

    def test_model_and_candidate_name_overlap_is_exposed_without_changing_labels(self):
        data = fixture_ai_benchmark()
        data['selection']['annotation_runs'][0]['model_id'] = CHECKPOINTS[0]['model_id']
        plan = freeze_plan(data, CHECKPOINTS, frozen_utc='2026-10-04T12:00:00Z')
        self.assertEqual(len(plan['annotation_candidate_overlap']), 1)
        self.assertEqual(plan['annotation_candidate_overlap'][0]['annotation_revision'], None)

    def test_optional_same_model_crosscheck_does_not_claim_human_independence(self):
        data = fixture_ai_benchmark(True)
        # Reverse per-post item order to verify matching by run ID, not incidental ordering.
        data['posts'][0]['model_annotations'].reverse()
        plan = freeze_plan(data, CHECKPOINTS, frozen_utc='2026-10-04T12:00:00Z')
        self.assertEqual(plan['annotation_agreement']['initial_exact_agreement'], 1)
        self.assertIn('not independent human', plan['annotation_agreement']['note'])

    def test_ai_provenance_tampering_missing_labels_exposure_and_fake_humans_fail(self):
        for mutation in ('prompt', 'input', 'raw', 'missing', 'duplicate', 'time', 'run_time',
                         'exposed', 'human', 'provider', 'identity', 'revision', 'freeze'):
            data = fixture_ai_benchmark(True)
            run = data['selection']['annotation_runs'][0]
            item = data['posts'][0]['model_annotations'][0]
            frozen = '2026-10-04T12:00:00Z'
            if mutation == 'prompt': run['prompt'] += ' tampered'
            elif mutation == 'input': data['posts'][0]['text'] += ' tampered'
            elif mutation == 'raw': item['raw_response'] = '{"label":"negative","reason":"different"}'
            elif mutation == 'missing': data['posts'][0]['model_annotations'].pop()
            elif mutation == 'duplicate': data['posts'][0]['model_annotations'][1] = item
            elif mutation == 'time': item['annotated_at_utc'] = '2026-10-01T12:00:00Z'
            elif mutation == 'run_time': run['run_started_utc'] = '2026-10-01T12:00:00Z'
            elif mutation == 'exposed': run['candidate_predictions_visible'] = True
            elif mutation == 'human': data['posts'][0]['annotator_a_id'] = 'invented person'
            elif mutation == 'provider': run['provider'] = ''
            elif mutation == 'identity': run['identity_source'] = 'verified_by_schema'
            elif mutation == 'revision': del run['model_revision']
            else: frozen = '2026-10-03T12:30:00Z'
            with self.assertRaises(ValueError, msg=mutation):
                freeze_plan(data, CHECKPOINTS, frozen_utc=frozen)

    def test_crosscheck_disagreements_and_exclusions_preserve_initial_raw_labels(self):
        data = fixture_ai_benchmark(True)
        post = data['posts'][0]
        item = post['model_annotations'][1]
        item['label'] = 'negative'
        item['raw_response'] = json.dumps({'label': item['label'], 'reason': item['reason']})
        with self.assertRaises(ValueError): validate_benchmark(data)
        post.update(adjudicated_label='exclude', adjudication_note='Labelled fixture unresolved ambiguity',
                    adjudicator_id='fixture-ai-a', adjudicated_at_utc='2026-10-03T13:30:00Z',
                    exclusion_reason='Labelled fixture disagreement exclusion')
        plan = freeze_plan(data, CHECKPOINTS, frozen_utc='2026-10-04T12:00:00Z')
        self.assertEqual(plan['excluded_posts'], 1)
        self.assertEqual(plan['annotation_agreement']['initial_disagreements'], 1)
        self.assertEqual(post['model_annotations'][0]['label'], 'positive')
        self.assertEqual(post['model_annotations'][1]['label'], 'negative')

    def test_single_ai_exclusion_requires_reason_and_cannot_override_unanimous_label(self):
        data = fixture_ai_benchmark()
        post = data['posts'][0]
        post['adjudicated_label'] = 'exclude'
        with self.assertRaises(ValueError): validate_benchmark(data)
        post['adjudicated_label'] = None
        item = post['model_annotations'][0]
        item['label'] = 'exclude'
        item['raw_response'] = json.dumps({'label': 'exclude', 'reason': item['reason']})
        with self.assertRaises(ValueError): validate_benchmark(data)
        post['exclusion_reason'] = item['reason']
        self.assertEqual(len(validate_benchmark(data)), 199)


if __name__ == '__main__':
    unittest.main()
