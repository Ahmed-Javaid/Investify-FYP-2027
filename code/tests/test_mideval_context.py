"""Integration checks against committed experiment records; no raw corpus needed."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investify.decision_record import DecisionRecord
from investify.explain.context import build_context
from investify.explain.pipeline import emit
from investify.explain.template import Explanation, render


class MidEvalContextTests(unittest.TestCase):
    def record(self, corpus="alpaca"):
        suffix = "_alpaca" if corpus == "alpaca" else ""
        data = json.loads((ROOT / "artifacts" / f"decision_records{suffix}.json").read_text())
        return DecisionRecord.from_dict(data["decision_records"][0])

    def test_all_real_records_keep_their_facts_and_validate(self):
        for corpus, filename in [("fnspid", "decision_records.json"), ("alpaca", "decision_records_alpaca.json")]:
            data = json.loads((ROOT / "artifacts" / filename).read_text())
            self.assertEqual(len(data["decision_records"]), 186)
            for payload in data["decision_records"]:
                with self.subTest(corpus=corpus, date=payload["session_date"]):
                    record = DecisionRecord.from_dict(payload)
                    before = record.to_dict()
                    context = build_context(record, corpus=corpus)
                    json.dumps(context, allow_nan=False)
                    self.assertEqual({r["feature"] for r in context["features"]}, set(record.feature_vector))
                    self.assertEqual(context["probabilities"], record.probabilities)
                    self.assertEqual(context["decision"], record.decision)
                    self.assertAlmostEqual(sum(context["family_contributions"].values()) + context["base_value"], record.raw_model_output, places=4)
                    self.assertTrue(emit(record).verification.passed)
                    self.assertEqual(record.to_dict(), before)

    def test_coverage_discloses_news_only_and_display_only_risk(self):
        context = build_context(self.record(), corpus="alpaca")
        self.assertEqual(context["coverage"]["technical_features"], 5)
        self.assertEqual(context["coverage"]["news_features"], 6)
        self.assertIn("Not present", context["coverage"]["social_sentiment"])
        self.assertIn("does not condition", context["coverage"]["risk_conditioning"])

    def test_missing_value_is_not_invented(self):
        payload = self.record().to_dict()
        payload["feature_vector"]["mention_volume"] = float("nan")
        # This feature is not among the first record's top-k contributors.
        context = build_context(DecisionRecord.from_dict(payload), corpus="alpaca")
        row = next(r for r in context["features"] if r["feature"] == "mention_volume")
        self.assertIsNone(row["value"])
        self.assertFalse(row["value_available"])
        json.dumps(context, allow_nan=False)

    def test_unknown_feature_stays_visible_without_a_fabricated_definition(self):
        payload = self.record().to_dict()
        payload["feature_vector"]["unreviewed_feature"] = 12.0
        payload["shap_values"]["unreviewed_feature"] = 0.0
        context = build_context(DecisionRecord.from_dict(payload), corpus="alpaca")
        row = next(r for r in context["features"] if r["feature"] == "unreviewed_feature")
        self.assertEqual(row["family"], "Unclassified")
        self.assertEqual(row["effect_on_predicted_class"], "neutral")
        self.assertIn("not been reviewed", row["meaning"])

    def test_corrupt_confidence_is_replaced_with_a_verified_template(self):
        record = self.record()
        clean = render(record)
        payload = copy.deepcopy(clean.payload)
        payload["confidence"] -= 0.05
        text = clean.text.replace(f"{record.confidence * 100:.2f}%", f"{payload['confidence'] * 100:.2f}%", 1)
        emitted = emit(record, Explanation(text=text, payload=payload))
        self.assertTrue(emitted.replaced_by_template)
        self.assertTrue(emitted.verification.passed)
        self.assertEqual(emitted.text, clean.text)


if __name__ == "__main__":
    unittest.main()
