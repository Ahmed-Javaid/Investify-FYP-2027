"""Policy-aware template and independent prose/payload verification regressions."""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investify.decision_record import DecisionRecord
from investify.explain.template import Explanation, render, render_guided
from investify.explain.verifier import verify
from investify.explain.pipeline import emit

class PolicyExplanationTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'artifacts/decision_records_alpaca.json'
        self.record = DecisionRecord.from_dict(json.loads(path.read_text())['decision_records'][0])

    def test_numeric_and_guided_templates_state_and_verify_the_trusted_policy(self):
        for renderer in (render, render_guided):
            for action in ('Observe', 'Hold', 'Buy', 'Sell'):
                output = renderer(self.record, policy_action=action)
                self.assertIn('Policy outcome: ' + action + '.', output.text)
                self.assertIn('diagnostic class for session', output.text)
                self.assertTrue(verify(self.record, output.text, output.payload,
                                       policy_action=action, strict_prose=True).passed)

    def test_wrong_prose_or_payload_policy_cannot_override_the_trusted_outcome(self):
        output = render(self.record, policy_action='Observe')
        wrong_payload = copy.deepcopy(output.payload)
        wrong_payload['policy_outcome'] = 'Buy'
        for text, payload in ((output.text.replace('Policy outcome: Observe.', 'Policy outcome: Buy.'), output.payload),
                              (output.text, wrong_payload)):
            self.assertFalse(verify(self.record, text, payload, policy_action='Observe').passed)

    def test_payload_cannot_hide_a_missing_displayed_policy_line(self):
        output = render(self.record, policy_action='Observe')
        self.assertFalse(verify(self.record, output.text.replace('Policy outcome: Observe.\n', ''),
                                output.payload, policy_action='Observe').passed)

    def test_a_policy_claim_without_trusted_policy_context_is_rejected(self):
        output = render(self.record, policy_action='Observe')
        self.assertFalse(verify(self.record, output.text, output.payload).passed)

    def test_rejected_policy_keeps_failed_report_and_checked_policy_fallback(self):
        output = render(self.record, policy_action='Observe')
        candidate = Explanation(output.text.replace('Policy outcome: Observe.', 'Policy outcome: Buy.'), output.payload)
        result = emit(self.record, candidate, policy_action='Observe', strict_prose=True)
        self.assertTrue(result.replaced_by_template)
        self.assertFalse(result.rejected_verification.passed)
        self.assertTrue(result.verification.passed)
        self.assertIn('Policy outcome: Observe.', result.text)

    def test_all_supported_corruptions_are_rejected_in_strict_policy_mode(self):
        # Cover the fixture categories without requiring NumPy in portable CI.
        output = render(self.record, policy_action='Observe')
        mutations = {
            'wrong_probability': lambda p: p.update(confidence=0.99),
            'wrong_shap_magnitude': lambda p: p['contributions'][0].update(shap_value=99.0),
            'flipped_direction': lambda p: p['contributions'][0].update(
                direction='opposes' if p['contributions'][0]['direction'] == 'supports' else 'supports'),
            'promoted_minor_feature': lambda p: p['contributions'][1].update(rank=1),
            'invented_feature_name': lambda p: p['contributions'][0].update(name='invented_feature'),
        }
        for kind, mutate in mutations.items():
            with self.subTest(kind=kind):
                payload = copy.deepcopy(output.payload)
                mutate(payload)
                self.assertFalse(verify(self.record, output.text, payload,
                                        policy_action='Observe', strict_prose=True).passed)
        self.assertFalse(verify(self.record, output.text + '\nUncheckable market narrative.',
                                output.payload, policy_action='Observe', strict_prose=True).passed)

    def test_historical_default_template_keeps_the_frozen_teacher_pilot_replayable(self):
        from investify.explain.teacher_session import prepare_packets
        base = Path(__file__).resolve().parents[1] / 'artifacts/mid_eval/teacher_pilot/assistant_20261012/packets'
        plan = json.loads((base / 'plan.json').read_text())
        for packet in prepare_packets(plan):
            self.assertEqual(json.loads(json.dumps(packet)), json.loads((base / (packet['packet_id'] + '.json')).read_text()))
        self.assertNotIn('policy_outcome', render(self.record).payload)

if __name__ == '__main__':
    unittest.main()
