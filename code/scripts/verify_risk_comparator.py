"""Audit arithmetic on actual held-out rows and labelled prototype scenarios.

No participant profiles, outcome labels, accuracy or investment performance
are synthesized. The scenarios are deterministic parameter probes.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.risk_comparator import build_comparator
from investify.risk_profile import score_profile


def audit():
    capacity = {'horizon': '5+ years', 'buffer': '6+ months', 'stability': 'Salaried and stable',
                'dependants': '0', 'age': '18-30'}
    profiles = {name: score_profile(capacity, [index] * 3)
                for name, index in (('low_willingness_probe', 0), ('middle_willingness_probe', 1),
                                    ('high_willingness_probe', 2))}
    corpora = {}
    checks = 0
    for corpus, filename in (('alpaca', 'decision_records_alpaca.json'), ('fnspid', 'decision_records.json')):
        comparator = build_comparator(ROOT / 'artifacts' / filename, corpus=corpus)
        manifest = comparator.manifest
        rows = []
        for session in manifest['heldout_sessions']:
            record = comparator.records[session]
            before = record.to_dict()
            scores = {}
            for name, profile in profiles.items():
                result = comparator.score(session, profile)
                assert result['scaling_fit_end'] < session
                assert record.to_dict() == before
                assert result['saved_classifier_probabilities'] == before['probabilities']
                scores[name] = result['profile_conditioned']
                checks += 1
            rows.append({'session': session, 'saved_classifier': record.decision,
                         'technical_signal': result['technical_signal'], 'sentiment_signal': result['sentiment_signal'],
                         'reference': result['reference'], 'profile_probes': scores})
        corpora[corpus] = {'manifest': manifest, 'heldout_rows': len(rows), 'rows': rows,
                          'parameter_probe_action_counts': {
                              name: dict(Counter(row['profile_probes'][name]['decision'] for row in rows))
                              for name in profiles}}
    paths = ['src/investify/risk_profile.py', 'src/investify/risk_comparator.py', 'scripts/verify_risk_comparator.py']
    return {'checked_utc': datetime.now(timezone.utc).isoformat(), 'checks_passed': checks,
            'scope': 'Arithmetic, chronology and immutability using actual saved features and labelled profile probes',
            'human_profiles_used': 0, 'outcome_labels_available': False, 'accuracy_or_return_metrics': None,
            'profiles': {name: profile.to_dict() for name, profile in profiles.items()}, 'corpora': corpora,
            'source_sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(f"Comparator arithmetic checks passed: {report['checks_passed']}; report: {args.output}")
