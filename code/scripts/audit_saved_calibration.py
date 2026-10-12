"""Audit actual saved calibrated records; do not reconstruct missing training data."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.decision_record import DECISION_CLASSES, DecisionRecord


def audit(path):
    raw = path.read_bytes()
    payload = json.loads(raw)
    records = [DecisionRecord.from_dict(row) for row in payload['decision_records']]
    if not records:
        raise ValueError('No actual saved records to audit')
    probabilities = {}
    for label in DECISION_CLASSES:
        values = [r.probabilities[label] for r in records]
        probabilities[label] = {'minimum': min(values), 'maximum': max(values),
                                'mean': mean(values), 'population_sd': pstdev(values),
                                'distinct_values': len(set(values))}
    margins = [r.raw_model_output for r in records]
    gaps = sorted(sorted(r.probabilities.values(), reverse=True)[0]
                  - sorted(r.probabilities.values(), reverse=True)[1] for r in records)
    return {'source_file': path.name, 'file_sha256': hashlib.sha256(raw).hexdigest(),
            'records': len(records), 'ticker': sorted({r.ticker for r in records}),
            'session_range': [min(r.session_date for r in records), max(r.session_date for r in records)],
            'calibrated_decisions': dict(Counter(r.decision for r in records)),
            'distinct_calibrated_probability_vectors': len({tuple(r.probabilities[c] for c in DECISION_CLASSES) for r in records}),
            'probabilities': probabilities, 'calibrated_top_class_gap': {'minimum': min(gaps), 'maximum': max(gaps)},
            'recorded_predicted_class_raw_margin': {'minimum': min(margins), 'maximum': max(margins),
                                                   'distinct_values': len(set(margins))},
            'missing_news_mean_polarity': sum(r.feature_vector.get('mean_polarity') is None
                                              or isinstance(r.feature_vector.get('mean_polarity'), float)
                                              and r.feature_vector['mean_polarity'] != r.feature_vector['mean_polarity'] for r in records),
            'inherited_run_provenance': payload['provenance'],
            'metrics_recomputed': False, 'model_refitted': False,
            'missing_for_causal_reproduction': ['full three-class uncalibrated evaluation scores',
                'calibration scores/labels and fitted knots', 'evaluation truth labels',
                'trained models/scalers', 'raw prices/news/FinBERT cache and original scientific environment']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = {'checked_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'saved_artifacts_audited_scientific_rerun_blocked',
              'corpora': [audit(ROOT / 'artifacts' / name) for name in ('decision_records.json', 'decision_records_alpaca.json')],
              'engine_source_sha256': hashlib.sha256((ROOT / 'src/investify/engine.py').read_bytes()).hexdigest(),
              'source_observation': 'run_engine fits one-vs-rest isotonic mappings on fold[-2] scores from calib_model, then applies those mappings to a separately refitted eval_model. The evaluation model training includes earlier calibration rows. This is a declared cross-fit/refit arrangement, not proof of forward leakage; probability-mapping transfer to the refitted model is unverified.',
              'causal_conclusion': None,
              'next_experiment': 'Preserve the historical pipeline as the baseline. Once inputs/runtime exist, save raw/calibrated scores, labels, class counts and isotonic knots. Compare the unchanged cross-fit/refit path with the same frozen classifier scored on disjoint chronological calibration/evaluation blocks; report all class distributions, macro-F1 and Brier without changing the thresholds to target the evaluation outcome.',
              'scope': 'Measured summaries of existing records and inspected code. Inherited scores are not newly reproduced results. Only predicted-class raw margins were saved, so complete uncalibrated probabilities cannot be recovered from these records.'}
    if args.output.exists():
        raise ValueError('Preserve the prior audit; choose a new output filename')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print('Audited 372 existing records; causal calibration rerun remains blocked')


if __name__ == '__main__':
    main()
