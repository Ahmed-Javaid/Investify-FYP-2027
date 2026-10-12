"""Real-record planning checks; provider fixtures do not enter evaluation files."""
import sys
import json
import copy
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.explain.evaluation import evaluate, evaluation_plan
from investify.explain.local_llm import ExplainerConfig, LocalExplainer, ProviderUnavailable


class EvaluationPlanTests(unittest.TestCase):
    def test_chronological_development_and_evaluation_are_disjoint_and_reproducible(self):
        first, records = evaluation_plan(per_corpus=6)
        second, _ = evaluation_plan(per_corpus=6)
        self.assertEqual(first, second)
        self.assertEqual(len(records), 12)
        for corpus in first['corpora'].values():
            self.assertFalse(set(corpus['development_sessions']) & set(corpus['heldout_sessions']))
            self.assertLess(max(corpus['development_sessions']), min(corpus['heldout_sessions']))
            self.assertTrue(set(corpus['selected_sessions']).issubset(corpus['heldout_sessions']))

    def test_plan_only_never_calls_a_model_or_reports_generation_quality(self):
        client = Mock()
        report = evaluate(LocalExplainer(ExplainerConfig(model='fixture', api_key='labelled-fixture-token'),
                                        client=client), plan_only=True)
        client.complete.assert_not_called()
        self.assertEqual(report['status'], 'plan_only')
        self.assertEqual(report['raw_completions'], 0)
        self.assertIsNone(report['quality_metrics'])
        self.assertTrue(all(r['guided_template']['passed'] for r in report['baselines']))
        self.assertNotIn('labelled-fixture-token', json.dumps(report))

    def test_unavailable_provider_is_blocked_and_no_faithfulness_score_is_invented(self):
        client = Mock()
        client.complete.side_effect = ProviderUnavailable('labelled unavailable fixture')
        plan, _ = evaluation_plan()
        report = evaluate(LocalExplainer(ExplainerConfig(model='fixture'), client=client), declared_plan=plan)
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['raw_completions'], 0)
        self.assertIsNone(report['quality_metrics'])
        self.assertEqual(client.complete.call_count, 1)

    def test_progress_retains_the_completed_failed_example_before_early_exit(self):
        client = Mock()
        client.complete.side_effect = ProviderUnavailable('LABELLED unavailable provider fixture')
        plan, _ = evaluation_plan()
        retained = []
        report = evaluate(LocalExplainer(ExplainerConfig(model='fixture'), client=client),
                          declared_plan=plan, progress=retained.append)
        self.assertEqual(retained, report['results'])
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0]['attempts'][0]['error'], 'LABELLED unavailable provider fixture')
        self.assertTrue(retained[0]['used_template'])

    def test_unconfigured_evaluation_is_blocked_without_provider_calls(self):
        client = Mock()
        report = evaluate(LocalExplainer(client=client))
        client.complete.assert_not_called()
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['examples_evaluated'], 0)

    def test_real_inference_requires_the_previously_saved_plan(self):
        client = Mock()
        with self.assertRaisesRegex(ValueError, 'previously saved'):
            evaluate(LocalExplainer(ExplainerConfig(model='fixture'), client=client))
        client.complete.assert_not_called()

    def test_plan_drift_is_rejected_before_any_provider_request(self):
        plan, _ = evaluation_plan()
        changed = copy.deepcopy(plan)
        changed['contract_source_sha256']['fixture-change'] = 'different'
        client = Mock()
        with self.assertRaisesRegex(ValueError, 'differs'):
            evaluate(LocalExplainer(ExplainerConfig(model='fixture'), client=client), declared_plan=changed)
        client.complete.assert_not_called()
