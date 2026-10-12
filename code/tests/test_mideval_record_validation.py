"""Malformed authoritative records must fail before explanations or decisions."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.decision_record import DecisionRecord


class RecordValidationTests(unittest.TestCase):
    def data(self):
        return json.loads((ROOT / 'artifacts/decision_records_alpaca.json').read_text())['decision_records'][0]

    def test_nonfinite_out_of_range_or_boolean_probabilities_are_rejected(self):
        for value in (float('nan'), float('inf'), -.01, 1.01, True):
            data = self.data()
            data['probabilities']['Buy'] = value
            with self.assertRaises(ValueError):
                DecisionRecord.from_dict(data)

    def test_nonfinite_base_margin_and_shap_and_incomplete_vectors_are_rejected(self):
        for field in ('base_value', 'raw_model_output', 'shap_values'):
            data = self.data()
            if field == 'shap_values':
                data[field]['mention_volume'] = float('nan')
            else:
                data[field] = float('nan')
            with self.assertRaises(ValueError):
                DecisionRecord.from_dict(data)
        data = self.data()
        del data['shap_values']['mention_volume']
        with self.assertRaises(ValueError):
            DecisionRecord.from_dict(data)

    def test_invalid_date_horizon_and_feature_input_are_rejected(self):
        for field, value in (('session_date', '2023-02-30'), ('horizon_days', 0), ('horizon_days', True),
                             ('ticker', 'NVDA fictitious'), ('non_advice_notice', '')):
            data = self.data()
            data[field] = value
            with self.assertRaises(ValueError):
                DecisionRecord.from_dict(data)
        for value in ('invented number', True):
            data = self.data()
            data['feature_vector']['mention_volume'] = value
            with self.assertRaises(ValueError):
                DecisionRecord.from_dict(data)

    def test_top_k_cannot_lie_about_values_duplicate_features_or_promote_minor_contributors(self):
        data = self.data()
        data['top_k'][0]['value'] += 1
        with self.assertRaises(ValueError):
            DecisionRecord.from_dict(data)
        data = self.data()
        data['top_k'][1] = dict(data['top_k'][0], rank=2)
        with self.assertRaises(ValueError):
            DecisionRecord.from_dict(data)
        data = self.data()
        name = min(data['shap_values'], key=lambda name: abs(data['shap_values'][name]))
        shap = data['shap_values'][name]
        data['top_k'][-1] = {'name': name, 'value': data['feature_vector'][name], 'shap_value': shap,
                             'rank': 5, 'direction': 'supports' if shap > 0 else 'opposes'}
        with self.assertRaises(ValueError):
            DecisionRecord.from_dict(data)


if __name__ == '__main__':
    unittest.main()
