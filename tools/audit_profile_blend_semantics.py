"""Describe actual profile-blend direction changes without suitability claims."""
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code/scripts'))
from verify_risk_comparator import audit

source = audit()
corpora = {}
for name, corpus in source['corpora'].items():
    transitions = Counter()
    slopes = Counter()
    changed, examples = [], []
    for row in corpus['rows']:
        probes = row['profile_probes']
        low, high = probes['low_willingness_probe'], probes['high_willingness_probe']
        transitions[(low['decision'], high['decision'])] += 1
        slope = row['sentiment_signal'] - row['technical_signal']
        slopes['positive' if slope > 0 else 'negative' if slope < 0 else 'zero'] += 1
        detail = {'session': row['session'], 'T': row['technical_signal'], 'S': row['sentiment_signal'],
                  'dC_dR': slope, 'R0': low, 'R1': high, 'saved_classifier': row['saved_classifier']}
        examples.append(detail)
        if low['decision'] != high['decision']:
            changed.append(detail)
    corpora[name] = {'heldout_rows': corpus['heldout_rows'], 'source_artifact_sha256': corpus['manifest']['artifact_sha256'],
                     'score_slope_counts': dict(slopes), 'R0_to_R1_action_counts':
                     [{'R0': low, 'R1': high, 'rows': count} for (low, high), count in sorted(transitions.items())],
                     'changed_action_rows': len(changed), 'all_rows': examples,
                     'first_lower_R_Buy_example': next((row for row in examples if row['R0']['decision'] == 'Buy'
                                                           and row['R1']['decision'] != 'Buy'), None)}
report = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'status': 'actual_saved_feature_semantics_audited',
          'formula': 'C(R)=T+R*(S-T); derivative dC/dR=S-T',
          'corpora': corpora, 'human_profiles_used': 0, 'outcome_labels_used': 0, 'suitability_or_return_metrics': None,
          'source_sha256': source['source_sha256'],
          'conclusion': 'R changes relative news/technical weighting. Lower R is not a constraint on exposure, expected loss, volatility or the direction/intensity of Buy/Hold/Sell. Risk-tier naming must not imply validated conservative behavior.',
          'design_decision': 'Keep the separate prototype explicit. Preserve saved classifier decisions. Treat allocation/position sizing, horizon-dependent asset risk and validated risk-questionnaire semantics as separate unfinished requirements; do not assert that blend arithmetic implements suitability.'}
output = ROOT / 'evidence/profile_blend_semantics_20261012.json'
if output.exists():
    raise ValueError('Preserve the prior actual audit receipt')
output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
print({name: {'slopes': corpus['score_slope_counts'], 'changed_actions': corpus['changed_action_rows'],
              'transitions': corpus['R0_to_R1_action_counts'],
              'first_lower_R_Buy': corpus['first_lower_R_Buy_example']['session'] if corpus['first_lower_R_Buy_example'] else None}
       for name, corpus in corpora.items()})
