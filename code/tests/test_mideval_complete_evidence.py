"""Adversarial checks of all-feature prose/JSON evidence, beyond top-k."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from investify.decision_record import DecisionRecord
from investify.explain.local_llm import verify_generated
from investify.explain.template import Explanation, render_guided


class CompleteEvidenceTests(unittest.TestCase):
    def setUp(self):
        data = json.loads((ROOT / "artifacts/decision_records_alpaca.json").read_text())
        self.record = DecisionRecord.from_dict(data["decision_records"][0])
        self.guide = render_guided(self.record)

    def test_every_feature_has_a_value_magnitude_direction_and_target_in_both_sources(self):
        result = verify_generated(self.record, self.guide)
        self.assertTrue(result.passed, result.failed_metrics)
        self.assertEqual(len(self.guide.payload['feature_evidence']), 11)
        self.assertEqual(len(self.guide.payload['family_contributions']), 2)

    def test_non_top_k_number_or_direction_cannot_hide_behind_correct_top_k(self):
        name = next(name for name in self.record.feature_names
                    if name not in {c.name for c in self.record.top_k})
        for source in ('text', 'payload'):
            for field in ('value', 'shap_value', 'direction'):
                payload = copy.deepcopy(self.guide.payload)
                text = self.guide.text
                item = next(x for x in payload['feature_evidence'] if x['name'] == name)
                original = item[field]
                changed = ('opposes' if original == 'supports' else 'supports') if field == 'direction' else original + 5
                if source == 'payload':
                    item[field] = changed
                else:
                    line = next(line for line in text.splitlines() if line.startswith(f'Recorded feature {name} '))
                    old = str(original) if field == 'direction' else f'{original:+.4f}' if field == 'shap_value' else f'{original:.4f}'
                    new = str(changed) if field == 'direction' else f'{changed:+.4f}' if field == 'shap_value' else f'{changed:.4f}'
                    text = text.replace(line, line.replace(old, new))
                self.assertFalse(verify_generated(self.record, Explanation(text, payload)).passed, (source, field))

    def test_complete_evidence_cannot_be_replaced_by_duplicate_top_k_or_payload_only(self):
        for source in ('text', 'payload'):
            payload = copy.deepcopy(self.guide.payload)
            text = self.guide.text
            if source == 'payload':
                payload['feature_evidence'][-1] = payload['feature_evidence'][0]
            else:
                text = '\n'.join(line for line in text.splitlines() if not line.startswith('Recorded feature '))
            result = verify_generated(self.record, Explanation(text, payload))
            self.assertFalse(result.passed)
            self.assertIn('feature_evidence_coverage', result.failed_metrics)

    def test_family_total_direction_target_and_coverage_are_independently_checked(self):
        for source in ('text', 'payload'):
            payload = copy.deepcopy(self.guide.payload)
            text = self.guide.text
            if source == 'payload':
                payload['family_contributions'][0]['shap_value'] += 1
            else:
                line = next(line for line in text.splitlines() if line.startswith('Family contribution for '))
                text = text.replace(line, line.replace('for Buy;', 'for Sell;'))
            self.assertFalse(verify_generated(self.record, Explanation(text, payload)).passed)
        payload = copy.deepcopy(self.guide.payload)
        payload['family_contributions'] = []
        self.assertIn('family_evidence_coverage', verify_generated(self.record, Explanation(self.guide.text, payload)).failed_metrics)

    def test_missing_value_and_zero_attribution_are_preserved_instead_of_invented(self):
        payload = self.record.to_dict()
        payload['feature_vector']['unreviewed_fixture'] = None
        payload['shap_values']['unreviewed_fixture'] = 0.0
        record = DecisionRecord.from_dict(payload)
        guide = render_guided(record)
        self.assertTrue(verify_generated(record, guide).passed)
        self.assertIn('Recorded feature unreviewed_fixture (value missing): SHAP +0.0000 for Buy; effect neutral.', guide.text)
        bad = guide.text.replace('(value missing)', '(value 0.0000)')
        self.assertFalse(verify_generated(record, Explanation(bad, guide.payload)).passed)
        bad = guide.text.replace('effect neutral.', 'effect supports.')
        self.assertFalse(verify_generated(record, Explanation(bad, guide.payload)).passed)

    def test_missing_top_k_value_is_supported_in_both_templates(self):
        payload = self.record.to_dict()
        name = payload['top_k'][0]['name']
        payload['feature_vector'][name] = None
        payload['top_k'][0]['value'] = None
        record = DecisionRecord.from_dict(payload)
        guide = render_guided(record)
        self.assertTrue(verify_generated(record, guide).passed)
        json.dumps(guide.payload, allow_nan=False)

    def test_scope_cannot_be_removed_or_changed_into_a_probability_or_causality_claim(self):
        for source in ('text', 'payload'):
            payload = copy.deepcopy(self.guide.payload)
            text = self.guide.text
            if source == 'payload':
                payload['attribution_scope'] = 'SHAP caused the market price move.'
            else:
                text = text.replace(payload['attribution_scope'], '')
            self.assertFalse(verify_generated(self.record, Explanation(text, payload)).passed)

    def test_unknown_nonfinite_or_extra_evidence_fields_fail_closed(self):
        for mutation in ('unknown', 'nonfinite', 'extra'):
            payload = copy.deepcopy(self.guide.payload)
            if mutation == 'unknown':
                payload['feature_evidence'][0]['name'] = 'guaranteed_profit'
            elif mutation == 'nonfinite':
                payload['family_contributions'][0]['shap_value'] = float('nan')
            else:
                payload['feature_evidence'][0]['forecast'] = 42
            self.assertFalse(verify_generated(self.record, Explanation(self.guide.text, payload)).passed)


if __name__ == '__main__':
    unittest.main()
