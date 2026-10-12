"""Generated fixtures for supplementary local inference; never research outputs."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_mideval_ai_annotation import fixture_ai_benchmark
from test_mideval_sentiment_selection import CHECKPOINTS
from investify.sentiment_selection import freeze_plan, digest
from investify.explain.local_llm import Completion, ProviderUnavailable
from investify.generative_sentiment import frozen_plan, run_model, compare
from investify.publisher_models import model_spec

# Catalog identities only; injected responses are explicitly labelled unit fixtures.
# No weight files are loaded, and these rows are never saved as research outcomes.
MODELS = [model_spec(key) for key in ('qwen25', 'qwen3')]


class FixtureClient:
    def __init__(self, alias, fail=False):
        self.alias, self.fail, self.inputs = alias, fail, []

    def complete(self, body):
        self.inputs.append(json.loads(body['messages'][1]['content']))
        if self.fail:
            raise ProviderUnavailable('LABELLED UNIT FIXTURE FAILURE')
        return Completion(json.dumps({'label': 'neutral', 'reason': 'LABELLED UNIT FIXTURE, not real inference'}),
                          served_model=self.alias, finish_reason='stop')


class GenerativeSentimentTests(unittest.TestCase):
    def setUp(self):
        self.benchmark = fixture_ai_benchmark()
        self.parent = freeze_plan(self.benchmark, CHECKPOINTS, frozen_utc='2026-10-04T12:00:00Z')
        self.plan = frozen_plan(self.benchmark, self.parent, MODELS, frozen_utc='2026-10-05T12:00:00Z')

    def run_fixture(self, index=0, fail=False):
        model = MODELS[index]
        client = FixtureClient(model['served_alias'], fail)
        runtime = {'model_sha256': model['weights_sha256'], 'served_alias': model['served_alias']}
        run = run_model(self.benchmark, self.parent, self.plan, model['model_id'],
                        'http://127.0.0.1:1235/v1', runtime, _client=client)
        return run, client

    def test_parent_heldout_set_is_preserved_and_only_target_text_reaches_provider(self):
        run, client = self.run_fixture()
        self.assertEqual([row['post_id'] for row in run['outputs']], self.parent['heldout_post_ids'])
        self.assertTrue(all(set(value) == {'ticker', 'text'} for value in client.inputs))
        self.assertTrue(all('probabilities' not in row for row in run['outputs']))
        self.assertEqual(self.plan['parent_social_plan_sha256'], digest(self.parent))

    def test_complete_hard_label_agreement_is_separate_from_classifier_completion(self):
        runs = [self.run_fixture(index)[0] for index in (0, 1)]
        result = compare(self.benchmark, self.parent, self.plan, runs)
        self.assertTrue(result['comparison_ready'])
        self.assertFalse(result['original_classifier_study_completed'])
        self.assertFalse(result['independent_human_validation'])
        self.assertIsNone(result['deployment_selection'])
        self.assertTrue(all(row['quality_metrics'] is not None for row in result['results']))

    def test_actual_failures_remain_failures_with_null_metrics(self):
        run, _ = self.run_fixture(fail=True)
        result = compare(self.benchmark, self.parent, self.plan, [run])
        self.assertFalse(result['comparison_ready'])
        self.assertIsNone(result['results'][0]['quality_metrics'])
        self.assertEqual(result['results'][0]['error_posts'], 40)
        self.assertTrue(all(row['label'] is None for row in run['outputs']))

    def test_code_prompt_reference_and_runtime_drift_prevent_inference(self):
        for mutation in ('source', 'prompt', 'benchmark', 'weights'):
            data, plan = copy.deepcopy(self.benchmark), copy.deepcopy(self.plan)
            runtime = {'model_sha256': MODELS[0]['weights_sha256'], 'served_alias': MODELS[0]['served_alias']}
            client = FixtureClient('fixture-a')
            if mutation == 'source': plan['source_sha256']['changed'] = 'a' * 64
            elif mutation == 'prompt': plan['prompt'] += ' LABELLED TAMPER'
            elif mutation == 'benchmark': data['posts'][0]['text'] += ' LABELLED TAMPER'
            else: runtime['model_sha256'] = 'c' * 64
            with self.assertRaises(ValueError, msg=mutation):
                run_model(data, self.parent, plan, MODELS[0]['model_id'], 'http://127.0.0.1:1235/v1', runtime, _client=client)
            self.assertFalse(client.inputs)

    def test_saved_response_timing_and_identity_tampering_fail_closed(self):
        for mutation in ('label', 'input', 'time', 'served', 'duplicate', 'policy'):
            run, _ = self.run_fixture()
            row = run['outputs'][0]
            if mutation == 'label': row['label'] = 'positive'
            elif mutation == 'input': row['input_sha256'] = 'a' * 64
            elif mutation == 'time': row['completed_utc'] = '2026-10-01T00:00:00Z'
            elif mutation == 'served': row['served_model'] = 'other fixture'
            elif mutation == 'policy': run['publisher_policy_sha256'] = '0' * 64
            else: run['outputs'].append(row)
            with self.assertRaises(ValueError, msg=mutation): compare(self.benchmark, self.parent, self.plan, [run])

    def test_live_run_refuses_unverified_weights_before_creating_a_provider(self):
        from unittest.mock import patch
        model = MODELS[0]
        runtime = {'model_sha256': model['weights_sha256'], 'served_alias': model['served_alias']}
        with patch('investify.generative_sentiment.LocalChatClient') as provider:
            with self.assertRaisesRegex(ValueError, 'verified original-publisher runtime'):
                run_model(self.benchmark, self.parent, self.plan, model['model_id'],
                          'http://127.0.0.1:1235/v1', runtime)
            provider.assert_not_called()


if __name__ == '__main__':
    unittest.main()
