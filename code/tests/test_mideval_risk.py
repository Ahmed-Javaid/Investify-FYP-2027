"""Prototype arithmetic and real-record chronology; no investor validation claim."""
import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.risk_profile import CAPACITY_OPTIONS, score_profile
from investify.risk_comparator import build_comparator, linear_score

HIGH_CAPACITY = {'horizon': '5+ years', 'buffer': '6+ months', 'stability': 'Salaried and stable',
                 'dependants': '0', 'age': '18-30'}


class RiskProfileTests(unittest.TestCase):
    def test_all_1200_capacity_combinations_and_27_tolerance_combinations_are_bounded_and_restrictive(self):
        names = list(CAPACITY_OPTIONS)
        for choices in itertools.product(*(CAPACITY_OPTIONS[name] for name in names)):
            capacity = dict(zip(names, choices))
            for tolerance in itertools.product(range(3), repeat=3):
                profile = score_profile(capacity, tolerance)
                self.assertGreaterEqual(profile.score, 0)
                self.assertLessEqual(profile.score, 1)
                self.assertEqual(profile.score, min(profile.capacity_score, profile.tolerance_score))
                if profile.matched_caps:
                    self.assertEqual(profile.capacity_tier, 'Conservative')
                    self.assertLess(profile.capacity_score, .40)

    def test_no_capacity_cap_and_no_tolerance_axis_can_be_overridden_by_the_other(self):
        profile = score_profile(HIGH_CAPACITY, [0, 0, 0])
        self.assertEqual(profile.tier, 'Conservative')
        self.assertEqual(profile.binding_axis, 'tolerance')
        for factor, answer in (('buffer', 'None'), ('horizon', 'Under 1 year')):
            capacity = dict(HIGH_CAPACITY, **{factor: answer})
            profile = score_profile(capacity, [2, 2, 2])
            self.assertEqual(profile.tier, 'Conservative')
            self.assertTrue(profile.cap_binding)
            self.assertEqual(profile.binding_axis, 'capacity')

    def test_matched_cap_is_distinct_from_a_cap_that_changes_the_score(self):
        capacity = {name: next(iter(options)) for name, options in CAPACITY_OPTIONS.items()}
        capacity['dependants'] = '4+'
        capacity['age'] = '65+'
        profile = score_profile(capacity, [0, 0, 0])
        self.assertTrue(profile.matched_caps)
        self.assertFalse(profile.cap_binding)
        self.assertEqual(profile.capacity_score, 0)

    def test_incomplete_unknown_and_boolean_answers_are_not_defaulted(self):
        for capacity, tolerance in (({}, [1, 1, 1]), (dict(HIGH_CAPACITY, age=None), [1, 1, 1]),
                                    (dict(HIGH_CAPACITY, extra='fixture'), [1, 1, 1]),
                                    (HIGH_CAPACITY, [1, True, 1]), (HIGH_CAPACITY, [1, 1]),
                                    (HIGH_CAPACITY, [1, 1, 3])):
            with self.assertRaises(ValueError):
                score_profile(capacity, tolerance)


class RiskComparatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.comparator = build_comparator(ROOT / 'artifacts/decision_records_alpaca.json', corpus='alpaca')

    def test_both_real_corpora_have_strictly_disjoint_148_38_blocks(self):
        for corpus, filename in (('alpaca', 'decision_records_alpaca.json'), ('fnspid', 'decision_records.json')):
            comparator = build_comparator(ROOT / 'artifacts' / filename, corpus=corpus)
            plan = comparator.manifest
            self.assertEqual(plan['fit_rows'], 148)
            self.assertEqual(len(plan['heldout_sessions']), 38)
            self.assertLess(plan['fit_end'], min(plan['heldout_sessions']))
            self.assertIsNone(plan['predictive_performance'])
            with self.assertRaisesRegex(ValueError, 'scaling-development'):
                comparator.score(plan['development_sessions'][0], score_profile(HIGH_CAPACITY, [2, 2, 2]))

    def test_changing_heldout_feature_values_cannot_change_scaling_statistics(self):
        data = json.loads((ROOT / 'artifacts/decision_records_alpaca.json').read_text())
        for record in data['decision_records'][148:]:
            for name in record['feature_vector']:
                record['feature_vector'][name] *= 100
            for contribution in record['top_k']:
                contribution['value'] = record['feature_vector'][contribution['name']]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'labelled_heldout_perturbation.json'
            path.write_text(json.dumps(data))
            perturbed = build_comparator(path, corpus='alpaca')
        self.assertEqual(perturbed.manifest['scaling'], self.comparator.manifest['scaling'])
        self.assertNotEqual(perturbed.manifest['artifact_sha256'], self.comparator.manifest['artifact_sha256'])

    def test_real_profile_changes_the_separate_score_without_mutating_saved_probabilities(self):
        low = score_profile(HIGH_CAPACITY, [0, 0, 0])
        high = score_profile(HIGH_CAPACITY, [2, 2, 2])
        scores_differ = False
        for session in self.comparator.manifest['heldout_sessions']:
            record = self.comparator.records[session]
            before = record.to_dict()
            conservative = self.comparator.score(session, low)
            aggressive = self.comparator.score(session, high)
            scores_differ |= conservative['profile_conditioned']['score'] != aggressive['profile_conditioned']['score']
            self.assertEqual(conservative['reference'], aggressive['reference'])
            self.assertEqual(record.to_dict(), before)
            self.assertEqual(aggressive['saved_classifier_probabilities'], before['probabilities'])
        self.assertTrue(scores_differ)

    def test_threshold_edges_extreme_weights_and_invalid_inputs(self):
        self.assertEqual(linear_score(-.5, -.5, .5)['decision'], 'Sell')
        self.assertEqual(linear_score(.5, .5, .5)['decision'], 'Hold')
        self.assertEqual(linear_score(-1, 1, 0)['decision'], 'Sell')
        self.assertEqual(linear_score(-1, 1, 1)['decision'], 'Buy')
        for inputs in ((1, 1, -1), (1, 1, 2), (1, float('nan'), .5), (True, 1, .5)):
            with self.assertRaises(ValueError):
                linear_score(*inputs)

    def test_missing_news_is_disclosed_and_missing_technical_refuses_a_decision(self):
        data = json.loads((ROOT / 'artifacts/decision_records_alpaca.json').read_text())
        data['decision_records'][-1]['feature_vector']['mean_polarity'] = None
        for contribution in data['decision_records'][-1]['top_k']:
            if contribution['name'] == 'mean_polarity':
                contribution['value'] = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'labelled_missing_input.json'
            path.write_text(json.dumps(data))
            comparator = build_comparator(path, corpus='alpaca')
            session = comparator.manifest['heldout_sessions'][-1]
            result = comparator.score(session, score_profile(HIGH_CAPACITY, [2, 2, 2]))
            self.assertTrue(result['missing_sentiment'])
            self.assertEqual(result['sentiment_signal'], 0)
            data['decision_records'][-1]['feature_vector']['rsi_14'] = None
            for contribution in data['decision_records'][-1]['top_k']:
                if contribution['name'] == 'rsi_14':
                    contribution['value'] = None
            path.write_text(json.dumps(data))
            comparator = build_comparator(path, corpus='alpaca')
            with self.assertRaisesRegex(ValueError, 'Missing technical'):
                comparator.score(session, score_profile(HIGH_CAPACITY, [2, 2, 2]))

    def test_duplicate_or_mixed_records_and_missing_development_technical_data_are_rejected(self):
        original = json.loads((ROOT / 'artifacts/decision_records_alpaca.json').read_text())
        for kind in ('duplicate', 'mixed', 'missing'):
            data = json.loads(json.dumps(original))
            if kind == 'duplicate':
                data['decision_records'][1] = data['decision_records'][0]
            elif kind == 'mixed':
                data['decision_records'][0]['ticker'] = 'LABELLED_FIXTURE'
            else:
                data['decision_records'][0]['feature_vector']['rsi_14'] = None
                for contribution in data['decision_records'][0]['top_k']:
                    if contribution['name'] == 'rsi_14':
                        contribution['value'] = None
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'labelled_invalid_corpus.json'
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    build_comparator(path, corpus='alpaca')


if __name__ == '__main__':
    unittest.main()
