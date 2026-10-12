"""Measure live HTTP checks on historical records and labelled corruptions."""
import argparse
import copy
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.source_revision import source_revision


def run_checks(base_url: str) -> dict:
    started = time.perf_counter()

    def request(path, body=None):
        encoded = json.dumps(body).encode('utf-8') if body is not None else None
        req = Request(base_url.rstrip('/') + path, data=encoded,
                      headers={'Content-Type': 'application/json'} if encoded else {})
        with urlopen(req, timeout=10) as response:
            return json.load(response)

    catalog = request('/api/catalog')
    generator = request('/api/explainer-status')
    runtime = request('/health')
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in [ROOT / 'src/investify/demo_server.py',
                               ROOT / 'src/investify/explain/verifier.py',
                               ROOT / 'src/investify/explain/pipeline.py',
                               ROOT / 'app/mideval_demo.html',
                               ROOT / 'src/investify/explain/local_llm.py',
                               ROOT / 'src/investify/explain/template.py',
                               ROOT / 'src/investify/explain/context.py',
                               ROOT / 'src/investify/risk_profile.py',
                               ROOT / 'src/investify/risk_comparator.py',
                               ROOT / 'src/investify/decision_record.py', ROOT / 'app/demo_state.js']}
    if runtime.get('source_sha256') != source_hashes:
        raise AssertionError('Restart the demo after source changes before recording verification')
    checks = []
    for corpus, info in catalog['corpora'].items():
        sessions = info['sessions']
        for session in dict.fromkeys([sessions[0], sessions[len(sessions) // 2], sessions[-1]]):
            data = request(f'/api/record?corpus={corpus}&session={session}')
            template = data['template']
            p = template['payload']
            first = p['contributions'][0]
            candidates = {
                'clean': (template['text'], p),
                'wrong_displayed_probability': (
                    template['text'].replace(f"{p['confidence'] * 100:.2f}%", '1.00%', 1), p),
                'wrong_displayed_direction': (
                    template['text'].replace(f") {first['direction']} the",
                        f") {'opposes' if first['direction'] == 'supports' else 'supports'} the", 1), p),
                'wrong_displayed_feature_value': (
                    template['text'].replace(f"{first['name']} (value {first['value']:.4f})",
                        f"{first['name']} (value {first['value'] + 10:.4f})", 1), p),
                'wrong_displayed_decision': (
                    template['text'].replace(f"horizon): {p['decision']}.",
                        f"horizon): {'Sell' if p['decision'] == 'Buy' else 'Buy'}.", 1), p),
                'missing_notice': (template['text'].replace(p['non_advice_notice'], ''), p),
                'unsupported_sentence': (template['text'] + '\nThe stock will definitely double.', p),
            }
            wrong_payload = copy.deepcopy(p)
            wrong_payload['confidence'] -= 0.05
            candidates['wrong_payload_probability'] = (template['text'], wrong_payload)
            for kind, (text, payload) in candidates.items():
                result = request('/api/verify', {'corpus': corpus, 'session': session,
                                  'text': text, 'payload': payload, 'strict_prose': True})
                expected_pass = kind == 'clean'
                correct = (result['candidate']['passed'] == expected_pass
                           and result['replaced_by_template'] != expected_pass
                           and result['emitted']['passed']
                           and result['text'] == template['text'])
                if not correct:
                    raise AssertionError(f'Unexpected live verification: {corpus} {session} {kind}')
                checks.append({'corpus': corpus, 'session': session, 'case': kind,
                               'candidate_passed': result['candidate']['passed'],
                               'fallback_used': result['replaced_by_template'],
                               'failed_metrics': result['candidate']['failed_metrics'],
                               'check_passed': correct})
            if not generator['configured']:
                guided = request('/api/explain', {'corpus': corpus, 'session': session})
                correct = (guided['status'] == 'template_unconfigured' and guided['used_template']
                           and guided['emitted']['passed'] and not guided['attempts']
                           and 'Feature definition for mean_polarity:' in guided['text']
                           and 'Recorded feature mention_volume' in guided['text']
                           and 'Family contribution for News sentiment' in guided['text'])
                if not correct:
                    raise AssertionError('Unconfigured LLM must return an explicitly labelled verified guide')
                checks.append({'corpus': corpus, 'session': session, 'case': 'unconfigured_guided_fallback',
                               'candidate_passed': None, 'fallback_used': True,
                               'failed_metrics': [], 'check_passed': True})
    capacity = {'horizon': '5+ years', 'buffer': '6+ months', 'stability': 'Salaried and stable',
                'dependants': '0', 'age': '18-30'}
    profile_contract = request('/api/profile-contract')
    if len(profile_contract['capacity_options']) != 5 or len(profile_contract['tolerance_questions']) != 3:
        raise AssertionError('Expected the declared complete prototype profile')
    from urllib.error import HTTPError
    for corpus, info in catalog['corpora'].items():
        session = info['sessions'][-1]
        saved_before = request(f'/api/record?corpus={corpus}&session={session}')
        results = []
        for name, tolerance in (('low_profile_probe', [0, 0, 0]), ('high_profile_probe', [2, 2, 2])):
            result = request('/api/risk-comparator', {'corpus': corpus, 'session': session,
                              'capacity': capacity, 'tolerance': tolerance})
            if result['scaling_rows'] != 148 or not result['scaling_fit_end'] < session:
                raise AssertionError('Risk comparator must use earlier development rows only')
            results.append(result)
            checks.append({'corpus': corpus, 'session': session, 'case': name, 'check_passed': True,
                           'score': result['profile_conditioned']['score']})
        if (results[0]['profile_conditioned']['score'] == results[1]['profile_conditioned']['score']
                or results[0]['reference'] != results[1]['reference']
                or saved_before != request(f'/api/record?corpus={corpus}&session={session}')):
            raise AssertionError('Risk score must change independently of the fixed blend and saved classifier')
        for name, body in (
            ('development_refusal', {'corpus': corpus, 'session': info['sessions'][0],
                                    'capacity': capacity, 'tolerance': [2, 2, 2]}),
            ('incomplete_profile_refusal', {'corpus': corpus, 'session': session,
                                           'capacity': {}, 'tolerance': []}),
        ):
            try:
                request('/api/risk-comparator', body)
            except HTTPError as error:
                if error.code != 400:
                    raise
            else:
                raise AssertionError('Unavailable/incomplete comparator request must be refused')
            checks.append({'corpus': corpus, 'session': body['session'], 'case': name, 'check_passed': True})
    expected_count = 56 if generator['configured'] else 62
    if len(catalog['corpora']) != 2 or len(checks) != expected_count:
        raise AssertionError('Expected both corpora, three sessions each and all declared cases')
    return {'checked_utc': datetime.now(timezone.utc).isoformat(),
            'python': platform.python_version(), 'base_url': base_url,
            **source_revision(ROOT),
            'scope': 'Live Python HTTP endpoints, historical records, labelled corruptions and separate risk-comparator probes. No browser visual QA, retraining, or LLM generations.',
            'verifier_contract': catalog['verifier_contract'],
            'elapsed_seconds': round(time.perf_counter() - started, 3),
            'checks_passed': len(checks), 'checks': checks,
            'generator_configured': generator['configured'],
            'real_model_requests_in_this_check': 0,
            'source_sha256': source_hashes, 'runtime_source_sha256': runtime['source_sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8765')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = run_checks(args.base_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"Live checks passed: {report['checks_passed']}; report: {args.output}")
