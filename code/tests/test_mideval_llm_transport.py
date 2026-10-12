"""Test-only loopback provider checks transport; no actual model is involved."""
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.explain.local_llm import ExplainerConfig, LocalChatClient, ProviderUnavailable


class LocalTransportTests(unittest.TestCase):
    def server(self, status=200):
        requests = []
        class FixtureHandler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass
            def do_POST(self):
                requests.append((self.path, json.loads(self.rfile.read(int(self.headers['Content-Length']))),
                                 self.headers.get('Authorization')))
                raw = json.dumps({'model': 'labelled-provider-fixture', 'choices': [
                    {'message': {'content': '{"labelled_fixture":true}'}, 'finish_reason': 'stop'}]}).encode()
                self.send_response(status)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        server = ThreadingHTTPServer(('127.0.0.1', 0), FixtureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server, requests

    def test_actual_loopback_http_request_and_completion_envelope(self):
        server, requests = self.server()
        config = ExplainerConfig(model='fixture', base_url=f'http://127.0.0.1:{server.server_port}/v1',
                                 api_key='labelled-fixture-token')
        completion = LocalChatClient(config).complete({'model': 'fixture', 'messages': []})
        self.assertEqual(requests[0][0], '/v1/chat/completions')
        self.assertEqual(requests[0][2], 'Bearer labelled-fixture-token')
        self.assertNotIn('labelled-fixture-token', repr(config))
        self.assertEqual(completion.served_model, 'labelled-provider-fixture')
        self.assertEqual(json.loads(completion.content), {'labelled_fixture': True})

    def test_provider_http_failure_is_explicit_and_body_not_exposed(self):
        server, _ = self.server(status=500)
        config = ExplainerConfig(model='fixture', base_url=f'http://127.0.0.1:{server.server_port}/v1')
        with self.assertRaisesRegex(ProviderUnavailable, 'HTTP 500'):
            LocalChatClient(config).complete({'model': 'fixture', 'messages': []})
