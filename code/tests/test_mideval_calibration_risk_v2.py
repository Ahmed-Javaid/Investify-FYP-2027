"""Calibration availability and risk direction/abstention contracts."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE / 'src'))
from investify.multiclass_calibration import fit_temperature, softmax_temperature
from investify.risk_profile_gl import GL_ITEMS, apply_risk_policy, example_answers, score_profile

CAPACITY = {'horizon': '5+ years', 'buffer': '6+ months', 'stability': 'Salaried and stable',
            'dependants': '0', 'age': '18-30'}


class CalibrationRiskV2Tests(unittest.TestCase):
    def test_real_calibration_replay_preserves_all_raw_classes_and_probabilities(self):
        directory = CODE / 'artifacts/scientific_runs/temperature_calibration_20261013_run01'
        old = CODE / 'artifacts/scientific_runs/alpaca_revision_conservative_20261012_run01/recovery01'
        for mode, folder in (('frozen', 'engine_frozen_alpaca'), ('refit', 'engine_refit_alpaca')):
            trace = json.loads((old / folder / 'scientific_trace.json').read_text())
            records = json.loads((directory / mode / 'decision_records.json').read_text())['decision_records']
            result = json.loads((directory / mode / 'experiment.json').read_text())
            classes = set()
            for margins, record in zip(trace['evaluation']['raw_margins_all_classes'], records):
                probabilities = softmax_temperature(margins, result['fit']['temperature'])
                self.assertAlmostEqual(sum(probabilities), 1)
                self.assertEqual(list(record['probabilities'].values()), probabilities)
                self.assertEqual(record['decision'], ('Buy', 'Hold', 'Sell')[max(range(3), key=margins.__getitem__)])
                classes.add(record['decision'])
            self.assertEqual(classes, {'Buy', 'Hold', 'Sell'})

    def test_calibration_refuses_unavailable_labels(self):
        with self.assertRaisesRegex(ValueError, 'precede evaluation'):
            fit_temperature([[1., 0., -1.]], ['Buy'], ['2023-01-01'], ['2023-01-10'], '2023-01-10')

    def test_softmax_handles_extreme_margins_and_refuses_invalid_temperature(self):
        probabilities = softmax_temperature([10000., 9999., -10000.], 2.)
        self.assertAlmostEqual(sum(probabilities), 1.)
        self.assertGreater(probabilities[0], probabilities[1])
        for value in (0, -1, True, float('nan')):
            with self.assertRaises(ValueError):
                softmax_temperature([1., 0., -1.], value)

    def test_thirteen_published_item_scores_have_exact_minimum_and_maximum(self):
        self.assertEqual(len(GL_ITEMS), 13)
        low, high = score_profile(CAPACITY, example_answers(0)), score_profile(CAPACITY, example_answers(2))
        self.assertEqual((low.tolerance_raw, high.tolerance_raw), (13, 47))
        self.assertEqual((low.score, high.score), (0., 1.))
        self.assertEqual((low.tolerance_band, high.tolerance_band), ('Low', 'High'))

    def test_incomplete_or_boolean_tolerance_answers_are_refused(self):
        for answers in ([], [0] * 3, [None] * 13, [False] * 13):
            with self.assertRaises(ValueError):
                score_profile(CAPACITY, answers)

    def test_capacity_caps_bind_despite_high_tolerance(self):
        capacity = dict(CAPACITY, buffer='None')
        profile = score_profile(capacity, example_answers(2))
        self.assertLess(profile.score, .4)
        self.assertEqual(profile.tier, 'Conservative')
        self.assertEqual(profile.binding_axis, 'capacity')

    def test_risk_allowance_changes_abstention_without_reversing_direction(self):
        for direction in ('Buy', 'Sell'):
            probabilities = {'Buy': .1, 'Hold': .2, 'Sell': .1}
            probabilities[direction] = .7
            record = SimpleNamespace(decision=direction, confidence=.7, probabilities=probabilities)
            before = copy.deepcopy(probabilities)
            low = apply_risk_policy(record, score_profile(CAPACITY, example_answers(0)))
            high = apply_risk_policy(record, score_profile(CAPACITY, example_answers(2)))
            self.assertEqual(low['profile_action'], 'Observe')
            self.assertEqual(high['profile_action'], direction)
            self.assertFalse(high['direction_reversal'])
            self.assertLess(high['minimum_confidence'], low['minimum_confidence'])
            self.assertEqual(probabilities, before)

    def test_actual_low_confidence_abstains_for_both_profile_extremes(self):
        from investify.decision_record import DecisionRecord
        path = CODE / 'artifacts/scientific_runs/temperature_calibration_20261013_run01/frozen/decision_records.json'
        for row in json.loads(path.read_text())['decision_records']:
            record = DecisionRecord.from_dict(row)
            for level in (0, 2):
                result = apply_risk_policy(record, score_profile(CAPACITY, example_answers(level)))
                self.assertEqual(result['profile_action'], 'Hold' if record.decision == 'Hold' else 'Observe')
                self.assertEqual(result['model_probabilities'], record.probabilities)


if __name__ == '__main__':
    unittest.main()
