"""Fixture backend integration only; no real classifier performance evidence."""
import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_mideval_sentiment_selection import fixture_benchmark, CHECKPOINTS
from investify.sentiment_selection import freeze_plan, evaluate_predictions
from investify.sentiment_inference import (run_inference, preprocess, preprocessing_spec,
    mapped_probabilities, validate_loaded_head, LocalModelUnavailable, LocalClassifier)

SPEC = {'text_policy': 'raw', 'max_length': 128,
        'label_mapping': {'0': 'negative', '1': 'neutral', '2': 'positive'}}


class SentimentInferenceTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture_benchmark()
        self.checkpoints = copy.deepcopy(CHECKPOINTS)
        for checkpoint in self.checkpoints:
            checkpoint['preprocessing'] = json.dumps(SPEC, sort_keys=True)
        self.plan = freeze_plan(self.data, self.checkpoints, frozen_utc='2026-10-04T12:00:00Z')

    def backend(self):
        backend = Mock()
        backend.metadata = {'role': 'labelled unit fixture, not a real model'}
        backend.predict.return_value = {'logits': [-1.0, 0.0, 1.0], 'input_tokens': 20, 'truncated': False}
        return backend

    def test_backend_receives_only_heldout_original_text_and_declared_token_ceiling(self):
        backend = self.backend()
        run, receipt = run_inference(self.data, self.plan, self.checkpoints[0]['model_id'], Path('unused_fixture'), _backend=backend)
        self.assertEqual(len(run['outputs']), 40)
        self.assertEqual(backend.predict.call_count, 40)
        by_id = {post['post_id']: post for post in self.data['posts']}
        self.assertEqual([call.args for call in backend.predict.call_args_list],
                         [(by_id[key]['text'], 128) for key in self.plan['heldout_post_ids']])
        self.assertTrue(all('probabilities' in row for row in run['outputs']))
        self.assertEqual(receipt['model_downloads'], 0)
        self.assertEqual(len(receipt['details']), 40)
        self.assertFalse(evaluate_predictions(self.data, self.plan, [run])['comparison_ready'])

    def test_text_and_index_mapping_are_explicit_and_softmax_is_stable(self):
        self.assertEqual(preprocess('@someone hello https://example.test', 'tweet_mentions_urls'), '@user hello http')
        self.assertEqual(preprocess('@someone\noriginal text', 'raw'), '@someone\noriginal text')
        probabilities = mapped_probabilities([1000, 999, 998], SPEC['label_mapping'])
        self.assertGreater(probabilities['negative'], probabilities['positive'])
        self.assertAlmostEqual(sum(probabilities.values()), 1)
        opposite = {'0': 'positive', '1': 'neutral', '2': 'negative'}
        self.assertGreater(mapped_probabilities([1, 0, -1], opposite)['positive'], .5)

    def test_failures_and_nonfinite_logits_are_retained_instead_of_neutral_predictions(self):
        for response in (RuntimeError('labelled fixture failure'), {'logits': [float('nan'), 0, 1], 'input_tokens': 20, 'truncated': False}):
            backend = self.backend()
            if isinstance(response, Exception): backend.predict.side_effect = response
            else: backend.predict.return_value = response
            run, _ = run_inference(self.data, self.plan, self.checkpoints[0]['model_id'], Path('unused_fixture'), _backend=backend)
            self.assertTrue(all('error' in row and 'probabilities' not in row for row in run['outputs']))
            evaluated = evaluate_predictions(self.data, self.plan, [run])
            self.assertIsNone(evaluated['results'][0]['quality_metrics'])
            self.assertEqual(evaluated['results'][0]['error_posts'], 40)

    def test_wrong_plan_or_inference_source_never_reaches_a_backend(self):
        for field in ('benchmark_sha256', 'inference_source_sha256'):
            plan = copy.deepcopy(self.plan)
            plan[field] = 'labelled source tampering'
            backend = self.backend()
            with self.assertRaises(ValueError):
                run_inference(self.data, plan, self.checkpoints[0]['model_id'], Path('unused_fixture'), _backend=backend)
            backend.predict.assert_not_called()

    def test_missing_random_or_semantically_mismapped_classifier_heads_are_refused(self):
        config = SimpleNamespace(num_labels=3, id2label={0: 'Bearish', 1: 'Neutral', 2: 'Bullish'})
        validate_loaded_head(config, {}, SPEC['label_mapping'])
        for info in ({'missing_keys': ['classifier.weight']}, {'mismatched_keys': ['classifier.bias']}, {'error_msgs': ['fixture error']}):
            with self.assertRaises(LocalModelUnavailable): validate_loaded_head(config, info, SPEC['label_mapping'])
        config.id2label = {0: 'Positive', 1: 'Neutral', 2: 'Negative'}
        with self.assertRaises(LocalModelUnavailable): validate_loaded_head(config, {}, SPEC['label_mapping'])
        with self.assertRaises(LocalModelUnavailable):
            validate_loaded_head(SimpleNamespace(num_labels=2, id2label={}), {}, SPEC['label_mapping'])

    def test_actual_loader_refuses_missing_weights_without_a_download(self):
        with self.assertRaises(LocalModelUnavailable):
            LocalClassifier(ROOT / 'labelled_nonexistent_snapshot', 'a' * 40, SPEC['label_mapping'])

    def test_invalid_or_unknown_preprocessing_is_not_guessed(self):
        for value in ('not json', '{}', json.dumps(dict(SPEC, max_length=True)),
                      json.dumps(dict(SPEC, text_policy='guess_from_model_name')),
                      json.dumps(dict(SPEC, label_mapping={'0': 'positive', '1': 'positive', '2': 'negative'}))):
            with self.assertRaises(ValueError): preprocessing_spec(value)
        backend = self.backend()
        with self.assertRaises(ValueError):
            run_inference(self.data, self.plan, 'unknown_fixture_model', Path('unused'), _backend=backend)
        backend.predict.assert_not_called()

    def test_truncation_provenance_is_recorded_and_inconsistent_counts_fail(self):
        backend = self.backend()
        backend.predict.return_value = {'logits': [1, 0, -1], 'input_tokens': 200, 'truncated': True}
        run, receipt = run_inference(self.data, self.plan, self.checkpoints[0]['model_id'], Path('unused_fixture'), _backend=backend)
        self.assertTrue(all(item['truncated'] for item in receipt['details']))
        backend.predict.return_value['truncated'] = False
        run, _ = run_inference(self.data, self.plan, self.checkpoints[0]['model_id'], Path('unused_fixture'), _backend=backend)
        self.assertTrue(all('error' in item for item in run['outputs']))


if __name__ == '__main__':
    unittest.main()
