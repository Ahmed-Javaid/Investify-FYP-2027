"""Explicitly generated UNIT-TEST fixtures, never acquired posts/human evidence."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.sentiment_selection import (LABELS, PROTOCOL, digest, validate_benchmark,
    freeze_plan, annotation_agreement, evaluate_predictions)


def fixture_benchmark():
    posts = []
    for index in range(200):
        label = LABELS[index % 3]
        posts.append({'post_id': f'fixture-{index:03d}', 'source': 'Labelled unit-test social fixture',
                      'source_kind': 'other_social', 'source_url': f'https://example.test/fixture/{index}',
                      'published_at_utc': '2023-01-01T12:00:00Z', 'ticker': 'FIXTURE',
                      'text': f'LABELLED UNIT TEST CONTENT {index}; not an acquired social post.',
                      'annotator_a_id': 'fixture-a', 'annotator_b_id': 'fixture-b',
                      'annotator_a_label': label, 'annotator_b_label': label,
                      'annotated_a_at_utc': '2026-10-03T12:00:00Z', 'annotated_b_at_utc': '2026-10-03T12:00:00Z',
                      'adjudicated_label': None, 'exclusion_reason': None})
    return {'protocol': PROTOCOL, 'selection': {'sampling_rule': 'LABELLED UNIT TEST ONLY',
            'access_conditions_reference': 'Fixture content; no real corpus rights implied',
            'annotation_method': 'two_independent_humans', 'target_tickers': ['FIXTURE'],
            'window_start_utc': '2023-01-01T00:00:00Z', 'window_end_utc': '2023-01-02T00:00:00Z',
            'declared_at_utc': '2026-10-01T12:00:00Z', 'acquired_at_utc': '2026-10-02T12:00:00Z'}, 'posts': posts}


CHECKPOINTS = [{'model_id': f'fixture/candidate-{letter}', 'revision': letter * 40, 'preprocessing': 'Fixture identity transform'}
               for letter in ('a', 'b')]


class SentimentSelectionTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture_benchmark()
        self.plan = freeze_plan(self.data, CHECKPOINTS, frozen_utc='2026-10-04T12:00:00Z')

    def runs(self):
        gold = {post['post_id']: post['gold_label'] for post in validate_benchmark(self.data)}
        return [{**checkpoint, 'plan_sha256': digest(self.plan), 'benchmark_sha256': self.plan['benchmark_sha256'],
                 'run_started_utc': '2026-10-05T12:00:00Z', 'run_completed_utc': '2026-10-05T12:01:00Z',
                 'outputs': [{'post_id': key, 'probabilities': {label: float(label == gold[key]) for label in LABELS}}
                             for key in self.plan['heldout_post_ids']]} for checkpoint in CHECKPOINTS]

    def test_fixed_160_40_selection_is_disjoint_reproducible_and_label_order_independent(self):
        self.assertEqual(len(self.plan['development_post_ids']), 160)
        self.assertEqual(len(self.plan['heldout_post_ids']), 40)
        self.assertFalse(set(self.plan['development_post_ids']) & set(self.plan['heldout_post_ids']))
        changed = copy.deepcopy(self.data)
        for post in changed['posts']:
            post['annotator_a_label'] = post['annotator_b_label'] = 'neutral'
        altered = freeze_plan(changed, CHECKPOINTS, frozen_utc=self.plan['frozen_utc'])
        self.assertEqual(self.plan['heldout_post_ids'], altered['heldout_post_ids'])
        self.assertNotEqual(self.plan['benchmark_sha256'], altered['benchmark_sha256'])

    def test_incomplete_provenance_duplicate_posts_and_news_inputs_are_refused(self):
        for mutation in ('small', 'identity', 'duplicate', 'content', 'news', 'timestamp'):
            data = copy.deepcopy(self.data)
            if mutation == 'small': data['posts'] = data['posts'][:199]
            elif mutation == 'identity': data['posts'][0]['annotator_b_id'] = 'fixture-a'
            elif mutation == 'duplicate': data['posts'][1]['post_id'] = data['posts'][0]['post_id']
            elif mutation == 'content': data['posts'][1]['text'] = data['posts'][0]['text']
            elif mutation == 'news': data['posts'][0]['source_kind'] = 'news_headline'
            else: data['posts'][0]['published_at_utc'] = '2023-01-01T12:00:00'
            with self.assertRaises(ValueError, msg=mutation): validate_benchmark(data)

    def test_disagreements_require_adjudication_and_exclusions_remain_explicit(self):
        data = copy.deepcopy(self.data)
        data['posts'][0]['annotator_b_label'] = 'negative'
        with self.assertRaises(ValueError): validate_benchmark(data)
        data['posts'][0].update(adjudicated_label='exclude', adjudication_note='Labelled fixture ambiguity',
                                adjudicated_at_utc='2026-10-03T13:00:00Z')
        with self.assertRaises(ValueError): validate_benchmark(data)
        data['posts'][0]['exclusion_reason'] = 'Labelled fixture unresolved ambiguity'
        self.assertEqual(len(validate_benchmark(data)), 199)
        plan = freeze_plan(data, CHECKPOINTS, frozen_utc=self.plan['frozen_utc'])
        self.assertEqual(plan['excluded_posts'], 1)
        self.assertNotIn(data['posts'][0]['post_id'], plan['development_post_ids'] + plan['heldout_post_ids'])

    def test_agreement_uses_initial_labels_and_homogeneous_kappa_is_undefined(self):
        self.assertEqual(annotation_agreement(self.data['posts'])['cohens_kappa'], 1)
        data = copy.deepcopy(self.data)
        for post in data['posts']: post['annotator_a_label'] = post['annotator_b_label'] = 'neutral'
        self.assertIsNone(annotation_agreement(data['posts'])['cohens_kappa'])

    def test_real_scoring_path_requires_complete_paired_outputs_and_keeps_ties_explicit(self):
        result = evaluate_predictions(self.data, self.plan, self.runs())
        self.assertTrue(result['comparison_ready'])
        self.assertEqual(len(result['benchmark_leaders']), 2)
        self.assertTrue(all(run['quality_metrics']['macro_f1'] == 1 for run in result['results']))
        self.assertIsNone(result['deployment_selection'])
        self.assertEqual(result['raw_model_runs'], self.runs())

    def test_missing_and_failed_predictions_are_not_neutral_or_dropped_for_a_score(self):
        runs = self.runs()
        runs[0]['outputs'].pop()
        runs[1]['outputs'][0] = {'post_id': runs[1]['outputs'][0]['post_id'], 'error': 'Labelled fixture timeout'}
        result = evaluate_predictions(self.data, self.plan, runs)
        self.assertEqual(result['status'], 'partial')
        self.assertFalse(result['comparison_ready'])
        self.assertEqual(result['benchmark_leaders'], [])
        self.assertTrue(all(run['quality_metrics'] is None for run in result['results']))
        self.assertEqual(result['results'][0]['missing_posts'], 1)
        self.assertEqual(result['results'][1]['error_posts'], 1)

    def test_changed_benchmark_code_or_plan_cannot_reuse_saved_outputs(self):
        for field in ('benchmark_sha256', 'evaluator_source_sha256', 'heldout_post_ids'):
            plan = copy.deepcopy(self.plan)
            plan[field] = [] if field == 'heldout_post_ids' else 'labelled tampering'
            with self.assertRaises(ValueError): evaluate_predictions(self.data, plan, self.runs())
        data = copy.deepcopy(self.data)
        data['posts'][0]['text'] += ' Labelled edit.'
        with self.assertRaises(ValueError): evaluate_predictions(data, self.plan, self.runs())

    def test_unknown_development_duplicate_or_invalid_probability_outputs_fail_closed(self):
        for mutation in ('unknown', 'development', 'duplicate', 'nonfinite', 'wrong_plan', 'early_run'):
            runs = self.runs()
            if mutation == 'unknown': runs[0]['outputs'][0]['post_id'] = 'unknown fixture'
            elif mutation == 'development': runs[0]['outputs'][0]['post_id'] = self.plan['development_post_ids'][0]
            elif mutation == 'duplicate': runs[0]['outputs'][1] = runs[0]['outputs'][0]
            elif mutation == 'nonfinite': runs[0]['outputs'][0]['probabilities']['positive'] = float('nan')
            elif mutation == 'wrong_plan': runs[0]['plan_sha256'] = 'wrong fixture'
            else: runs[0]['run_started_utc'] = '2026-10-01T12:00:00Z'
            with self.assertRaises(ValueError, msg=mutation): evaluate_predictions(self.data, self.plan, runs)

    def test_no_runs_or_one_candidate_never_manufactures_a_model_selection(self):
        result = evaluate_predictions(self.data, self.plan, [])
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['comparison_ready'])
        self.assertEqual(result['benchmark_leaders'], [])
        result = evaluate_predictions(self.data, self.plan, self.runs()[:1])
        self.assertFalse(result['comparison_ready'])
        self.assertEqual(result['benchmark_leaders'], [])


if __name__ == '__main__':
    unittest.main()
