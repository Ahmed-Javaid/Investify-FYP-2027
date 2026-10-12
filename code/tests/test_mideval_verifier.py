"""Regression tests on real records; edited explanations are labelled corruptions."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investify.decision_record import DecisionRecord
from investify.explain.pipeline import emit
from investify.explain.template import Explanation, render
from investify.explain.verifier import verify


class MidEvalVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT / "artifacts/decision_records_alpaca.json").read_text())
        cls.record = DecisionRecord.from_dict(data["decision_records"][0])
        cls.clean = render(cls.record)

    def test_correct_payload_cannot_hide_wrong_displayed_probability(self):
        text = self.clean.text.replace(
            f"{self.record.confidence * 100:.2f}%", "1.00%", 1
        )
        result = verify(self.record, text, self.clean.payload)
        self.assertFalse(result.passed)
        self.assertIn("numeric_fidelity", result.failed_metrics)

    def test_correct_payload_cannot_hide_wrong_displayed_direction(self):
        feature = self.record.top_k[0]
        opposite = "opposes" if feature.direction == "supports" else "supports"
        text = self.clean.text.replace(
            f") {feature.direction} the", f") {opposite} the", 1
        )
        self.assertFalse(verify(self.record, text, self.clean.payload).passed)

    def test_wrong_feature_values_in_either_representation_are_rejected(self):
        feature = self.record.top_k[0]
        for source in ("text", "payload"):
            with self.subTest(source=source):
                text, payload = self.clean.text, copy.deepcopy(self.clean.payload)
                if source == "text":
                    text = text.replace(
                        f"{feature.name} (value {feature.value:.4f})",
                        f"{feature.name} (value {feature.value + 10:.4f})",
                    )
                else:
                    payload["contributions"][0]["value"] += 10
                self.assertFalse(verify(self.record, text, payload).passed)

    def test_wrong_feature_target_class_is_rejected(self):
        text = self.clean.text.replace("the Buy decision", "the Sell decision", 1)
        self.assertFalse(verify(self.record, text, self.clean.payload).passed)

    def test_wrong_header_decision_is_rejected_despite_correct_payload(self):
        text = self.clean.text.replace("horizon): Buy.", "horizon): Sell.", 1)
        self.assertFalse(verify(self.record, text, self.clean.payload).passed)

    def test_correct_text_cannot_hide_wrong_payload_probability(self):
        payload = copy.deepcopy(self.clean.payload)
        payload["confidence"] -= 0.05
        self.assertFalse(verify(self.record, self.clean.text, payload).passed)

    def test_payload_cannot_supply_facts_or_notice_absent_from_displayed_text(self):
        for text in ("", "An optimistic outlook.",
                     self.clean.text.replace(self.record.non_advice_notice, ""),
                     "\n".join(self.clean.text.splitlines()[1:])):
            with self.subTest(text=text[:45]):
                self.assertFalse(verify(self.record, text, self.clean.payload).passed)

    def test_malformed_or_nonfinite_payloads_fail_closed(self):
        nonfinite = copy.deepcopy(self.clean.payload)
        nonfinite["confidence"] = math.nan
        boolean = copy.deepcopy(self.clean.payload)
        boolean["contributions"][0]["rank"] = True
        missing = copy.deepcopy(self.clean.payload)
        del missing["probabilities"]["Sell"]
        for payload in ({}, [], {"confidence": 0.5}, nonfinite, boolean, missing):
            with self.subTest(payload_type=type(payload).__name__):
                self.assertFalse(verify(self.record, self.clean.text, payload).passed)

    def test_padding_cannot_dilute_a_known_contradiction(self):
        text = (self.clean.text + "\n") * 100
        text += "Calibrated confidence in this decision: 1.00%."
        result = verify(self.record, text, self.clean.payload)
        self.assertFalse(result.passed)
        self.assertIn("contradictory_claim", result.failed_metrics)

    def test_strict_mode_rejects_unparsed_text_and_preserves_clean_template(self):
        self.assertTrue(verify(self.record, self.clean.text,
                               self.clean.payload, strict_prose=True).passed)
        text = self.clean.text + "\nThe stock will definitely double."
        result = verify(self.record, text, self.clean.payload, strict_prose=True)
        self.assertFalse(result.passed)
        self.assertIn("unsupported_prose", result.failed_metrics)

    def test_fallback_retains_the_rejected_candidate_report(self):
        text = self.clean.text.replace(
            f"{self.record.confidence * 100:.2f}%", "1.00%", 1
        )
        emitted = emit(self.record, Explanation(text, self.clean.payload))
        self.assertTrue(emitted.replaced_by_template)
        self.assertEqual(emitted.text, self.clean.text)
        self.assertTrue(emitted.verification.passed)
        self.assertIsNotNone(emitted.rejected_verification)
        self.assertFalse(emitted.rejected_verification.passed)


if __name__ == "__main__":
    unittest.main()
