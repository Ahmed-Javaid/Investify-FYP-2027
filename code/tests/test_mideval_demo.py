"""Exercise the real local HTTP interface, including corrupt and missing inputs."""
import http.client
import json
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investify.demo_server import DemoCatalog, make_server


class MidEvalDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {'Content-Type': 'application/json'} if body is not None else {}
        connection.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = connection.getresponse()
        status, data = response.status, response.read()
        connection.close()
        return status, data

    def record(self):
        status, data = self.request('GET', '/api/catalog')
        self.assertEqual(status, 200)
        session = json.loads(data)['corpora']['alpaca']['sessions'][0]
        status, data = self.request('GET', f'/api/record?corpus=alpaca&session={session}')
        self.assertEqual(status, 200)
        return session, json.loads(data)

    def test_live_catalog_and_page_serve_both_corpora(self):
        status, data = self.request('GET', '/health')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)['records'], 372)
        status, data = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'Candidate explanation', data)

    def test_clean_explanation_passes_the_live_endpoint(self):
        session, data = self.record()
        status, raw = self.request('POST', '/api/verify', {
            'corpus': 'alpaca', 'session': session, **data['template']})
        result = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertTrue(result['candidate']['passed'])
        self.assertFalse(result['replaced_by_template'])
        self.assertEqual(result['text'], data['template']['text'])

    def test_corrupt_prose_with_correct_json_is_replaced_live(self):
        session, data = self.record()
        text = data['template']['text'].replace(
            f"{data['template']['payload']['confidence'] * 100:.2f}%", '1.00%', 1)
        status, raw = self.request('POST', '/api/verify', {
            'corpus': 'alpaca', 'session': session,
            'text': text, 'payload': data['template']['payload']})
        result = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertFalse(result['candidate']['passed'])
        self.assertTrue(result['replaced_by_template'])
        self.assertTrue(result['emitted']['passed'])
        self.assertEqual(result['text'], data['template']['text'])

    def test_missing_record_and_malformed_request_report_unavailability(self):
        for path in ['/api/record?corpus=alpaca&session=1900-01-01',
                     '/api/record?corpus=unknown&session=2023-01-01']:
            status, data = self.request('GET', path)
            self.assertEqual(status, 400)
            self.assertIn('error', json.loads(data))
        status, _ = self.request('POST', '/api/verify', {'text': None})
        self.assertEqual(status, 400)

    def test_absent_corpus_is_disclosed_without_synthetic_replacement(self):
        with patch.object(Path, 'read_text', side_effect=FileNotFoundError('missing fixture input')):
            catalog = DemoCatalog()
        self.assertFalse(catalog.records)
        self.assertEqual(set(catalog.summary()['unavailable']), {'alpaca', 'fnspid'})
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            catalog.get('alpaca', '2023-01-01')

    def test_arbitrary_files_are_not_served(self):
        status, _ = self.request('GET', '/../../PROJECT_STATUS.md')
        self.assertEqual(status, 404)

    def test_explainer_status_discloses_no_configured_model(self):
        status, raw = self.request('GET', '/api/explainer-status')
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(raw)['configured'])

    def test_guided_explanation_falls_back_explicitly_when_no_model_is_configured(self):
        session, _ = self.record()
        status, raw = self.request('POST', '/api/explain', {'corpus': 'alpaca', 'session': session})
        result = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertEqual(result['status'], 'template_unconfigured')
        self.assertTrue(result['used_template'])
        self.assertTrue(result['emitted']['passed'])
        self.assertEqual(result['attempts'], [])
        self.assertIn('Feature definition for mean_polarity:', result['text'])
        self.assertIn('Recorded feature mention_volume', result['text'])

    def test_profile_contract_has_explicit_options_and_no_assumed_answers(self):
        status, raw = self.request('GET', '/api/profile-contract')
        contract = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertEqual(len(contract['capacity_options']), 5)
        self.assertEqual(len(contract['tolerance_questions']), 3)
        self.assertIn('not a validated', contract['notice'])

    def test_profile_changes_only_separate_live_comparator_and_development_rows_are_refused(self):
        _, raw = self.request('GET', '/api/catalog')
        catalog = json.loads(raw)
        capacity = {'horizon': '5+ years', 'buffer': '6+ months', 'stability': 'Salaried and stable',
                    'dependants': '0', 'age': '18-30'}
        for corpus, info in catalog['corpora'].items():
            session = info['sessions'][-1]
            before = self.request('GET', f'/api/record?corpus={corpus}&session={session}')[1]
            results = []
            for tolerance in ([0, 0, 0], [2, 2, 2]):
                status, raw = self.request('POST', '/api/risk-comparator',
                                          {'corpus': corpus, 'session': session,
                                           'capacity': capacity, 'tolerance': tolerance})
                self.assertEqual(status, 200)
                result = json.loads(raw)
                self.assertEqual(result['scaling_rows'], 148)
                self.assertLess(result['scaling_fit_end'], session)
                results.append(result)
            self.assertNotEqual(results[0]['profile_conditioned']['score'], results[1]['profile_conditioned']['score'])
            self.assertEqual(results[0]['reference'], results[1]['reference'])
            self.assertEqual(before, self.request('GET', f'/api/record?corpus={corpus}&session={session}')[1])
            status, raw = self.request('POST', '/api/risk-comparator',
                                      {'corpus': corpus, 'session': info['sessions'][0],
                                       'capacity': capacity, 'tolerance': [2, 2, 2]})
            self.assertEqual(status, 400)
            self.assertIn('scaling-development', json.loads(raw)['error'])

    def test_profile_endpoint_refuses_incomplete_or_unknown_claims(self):
        session, _ = self.record()
        for request in ({'corpus': 'alpaca', 'session': session, 'capacity': {}, 'tolerance': []},
                        {'corpus': 'alpaca', 'session': session, 'capacity': {}, 'tolerance': [], 'defaults': True},
                        None, []):
            status, raw = self.request('POST', '/api/risk-comparator', request if request is not None else {})
            self.assertEqual(status, 400)
            self.assertIn('error', json.loads(raw))


if __name__ == '__main__':
    unittest.main()
