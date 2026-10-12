"""Labelled provider fixtures test integration; they are not LLM evaluation data."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investify.decision_record import DecisionRecord
from investify.explain.local_llm import (Completion, ExplainerConfig, InvalidGeneration,
    LocalExplainer, ProviderUnavailable, parse_candidate, verify_generated)
from investify.explain.template import render_guided
from investify.explain.verifier import verify


class FixtureClient:
    """Test-only completions, deliberately never used by evaluation scripts."""
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result


class LocalLLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT / 'artifacts/decision_records_alpaca.json').read_text())
        cls.record = DecisionRecord.from_dict(data['decision_records'][0])
        cls.guide = render_guided(cls.record)

    def completion(self, text=None, payload=None):
        return Completion(json.dumps({'text': text if text is not None else self.guide.text,
                                     'payload': payload if payload is not None else self.guide.payload}),
                          'labelled-fixture-model', {'completion_tokens': 123})

    def test_guided_template_passes_for_every_real_record_without_mutation(self):
        for filename in ('decision_records.json', 'decision_records_alpaca.json'):
            data = json.loads((ROOT / 'artifacts' / filename).read_text())
            for payload in data['decision_records']:
                record = DecisionRecord.from_dict(payload)
                before = record.to_dict()
                guide = render_guided(record)
                self.assertTrue(verify_generated(record, guide).passed)
                self.assertEqual(len(guide.payload['definitions']), 11)
                self.assertEqual(record.to_dict(), before)

    def test_wrong_reviewed_definitions_in_text_or_json_are_rejected(self):
        for source in ('text', 'payload'):
            text, payload = self.guide.text, copy.deepcopy(self.guide.payload)
            if source == 'text':
                text = text.replace(payload['definitions'][0]['meaning'], 'Guaranteed profit.', 1)
            else:
                payload['definitions'][0]['meaning'] = 'Guaranteed profit.'
            self.assertFalse(verify(self.record, text, payload, strict_prose=True).passed)

    def test_definition_coverage_requires_visible_and_structured_meanings(self):
        payload = copy.deepcopy(self.guide.payload)
        payload['definitions'] = payload['definitions'][:-1]
        candidate = parse_candidate(self.completion(payload=payload).content)
        result = verify_generated(self.record, candidate)
        self.assertFalse(result.passed)
        self.assertIn('definition_coverage', result.failed_metrics)

    def test_unconfigured_model_uses_verified_guide_without_contacting_a_provider(self):
        client = FixtureClient([])
        result = LocalExplainer(client=client).explain(self.record, corpus='alpaca')
        self.assertEqual(result.status, 'template_unconfigured')
        self.assertTrue(result.used_template)
        self.assertTrue(result.emitted.verification.passed)
        self.assertEqual(result.emitted.text, self.guide.text)
        self.assertEqual(client.requests, [])

    def test_configured_provider_output_is_actually_verified_and_provenance_retained(self):
        client = FixtureClient([self.completion()])
        result = LocalExplainer(ExplainerConfig(model='fixture/requested'), client=client).explain(
            self.record, corpus='alpaca')
        self.assertEqual(result.status, 'generated_verified')
        self.assertFalse(result.used_template)
        self.assertEqual(result.attempts[0].served_model, 'labelled-fixture-model')
        self.assertEqual(result.attempts[0].usage['completion_tokens'], 123)
        request = client.requests[0]
        self.assertTrue(request['response_format']['json_schema']['strict'])
        self.assertIn('News sentiment', request['messages'][1]['content'])

    def test_failed_candidate_is_retained_when_retry_succeeds(self):
        wrong = self.guide.text.replace(f'{self.record.confidence * 100:.2f}%', '1.00%', 1)
        client = FixtureClient([self.completion(text=wrong), self.completion()])
        result = LocalExplainer(ExplainerConfig(model='fixture'), client=client).explain(
            self.record, corpus='alpaca')
        self.assertEqual(result.status, 'generated_verified')
        self.assertEqual(len(result.attempts), 2)
        self.assertFalse(result.attempts[0].verification.passed)
        self.assertTrue(result.attempts[1].verification.passed)
        self.assertIn('previous attempt failed', client.requests[1]['messages'][-1]['content'])

    def test_two_bad_candidates_fall_back_with_the_failed_report_preserved(self):
        wrong = self.guide.text + '\nThe stock will definitely double.'
        client = FixtureClient([self.completion(text=wrong), self.completion(text=wrong)])
        result = LocalExplainer(ExplainerConfig(model='fixture'), client=client).explain(
            self.record, corpus='alpaca')
        self.assertEqual(result.status, 'template_verification_failed')
        self.assertTrue(result.used_template)
        self.assertEqual(len(client.requests), 2)
        self.assertFalse(result.emitted.rejected_verification.passed)
        self.assertTrue(result.emitted.verification.passed)

    def test_unavailable_provider_fails_fast_with_explicit_fallback(self):
        client = FixtureClient([ProviderUnavailable('labelled unavailable fixture')])
        result = LocalExplainer(ExplainerConfig(model='fixture'), client=client).explain(
            self.record, corpus='alpaca')
        self.assertEqual(result.status, 'template_unavailable')
        self.assertTrue(result.used_template)
        self.assertEqual(len(client.requests), 1)
        self.assertIsNone(result.attempts[0].raw_output)

    def test_bad_json_retries_then_falls_back_without_inventing_a_generation(self):
        client = FixtureClient([Completion('not JSON'), Completion('```json\n{}\n```')])
        result = LocalExplainer(ExplainerConfig(model='fixture'), client=client).explain(
            self.record, corpus='alpaca')
        self.assertEqual(result.status, 'template_generation_failed')
        self.assertEqual(len(result.attempts), 2)
        self.assertTrue(result.used_template)
        self.assertIsNone(result.attempts[1].candidate)

    def test_remote_urls_invalid_budgets_and_nonfinite_json_are_rejected(self):
        for kwargs in ({'base_url': 'https://example.com/v1'}, {'timeout_seconds': float('nan')},
                       {'max_attempts': 3}, {'max_attempts': True}, {'max_tokens': 0}):
            with self.assertRaises(ValueError):
                ExplainerConfig(**kwargs)
        with self.assertRaises(InvalidGeneration):
            parse_candidate('{"text":"fixture", "payload":{"definitions":[],"confidence":NaN}}')

    def test_unknown_structured_claim_fields_are_not_silently_ignored(self):
        payload = copy.deepcopy(self.guide.payload)
        payload['guaranteed_return'] = 100
        self.assertFalse(verify(self.record, self.guide.text, payload).passed)

    def test_truncated_output_is_retained_and_rejected_before_fallback(self):
        truncated = Completion('{"text":"labelled partial fixture', 'fixture', None, 'length')
        client = FixtureClient([truncated, truncated])
        result = LocalExplainer(ExplainerConfig(model='fixture'), client=client).explain(
            self.record, corpus='alpaca')
        self.assertTrue(result.used_template)
        self.assertEqual(result.status, 'template_generation_failed')
        self.assertEqual(result.attempts[0].raw_output, truncated.content)
        self.assertEqual(result.attempts[0].finish_reason, 'length')


if __name__ == '__main__':
    unittest.main()
