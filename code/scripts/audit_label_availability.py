"""Replay preserved versus corrected purge rules on labelled business-day fixtures."""
import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.harness.splits import SPLIT_CONTRACT_VERSION, expanding_purged_walk_forward


def audit():
    snapshot = ROOT.parent / 'sources/historical_science_20261012'
    manifest = json.loads((snapshot / 'source_hashes.json').read_text(encoding='utf-8-sig'))
    for row in manifest:
        path = (snapshot / row['source'].replace('\\', '/')).resolve()
        if not path.is_relative_to(snapshot) or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Historical scientific source snapshot does not match its preservation manifest')
    old_source = snapshot / 'src/investify/harness/splits.py'
    # Execute only the unchanged preserved Fold/purger definitions. The
    # historical module's unrelated sklearn import remains unavailable.
    parsed = ast.parse(old_source.read_text(encoding='utf-8-sig'))
    definitions = [node for node in parsed.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                   and node.name in ('Fold', 'expanding_purged_walk_forward')]
    namespace = {'np': np, 'pd': pd, 'dataclass': dataclass, '__name__': __name__}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(old_source), 'exec'), namespace)
    legacy = namespace['expanding_purged_walk_forward']
    dates = pd.Series(pd.bdate_range('2023-01-02', periods=140))
    endpoints = dates.shift(-5)
    old = legacy(dates, n_folds=6, embargo_days=5, horizon_days=5)
    current = expanding_purged_walk_forward(dates, n_folds=6, embargo_days=5, horizon_days=5,
                                           label_end_dates=endpoints)
    rows = []
    for historical, corrected in zip(old, current):
        start = dates.iloc[corrected.test_idx[0]]
        if not np.array_equal(historical.test_idx, corrected.test_idx):
            raise ValueError('Purge comparison must preserve the same test-block identities')
        old_bad = [int(i) for i in historical.train_idx if endpoints.iloc[i] >= start]
        new_bad = [int(i) for i in corrected.train_idx if endpoints.iloc[i] >= start]
        rows.append({'fold': corrected.fold_id, 'test_start': start.date().isoformat(),
                     'historical_training_rows': len(historical.train_idx),
                     'corrected_training_rows': len(corrected.train_idx),
                     'historical_overlap_rows': old_bad, 'corrected_overlap_rows': new_bad,
                     'check_passed': bool(old_bad) and not new_bad})
    sources = [Path(__file__), ROOT / 'src/investify/harness/splits.py', ROOT / 'src/investify/labels.py']
    return {'schema': 'investify-label-availability-comparison-v1',
            'checked_utc': datetime.now(timezone.utc).isoformat(),
            'execution_kind': 'labelled_synthetic_business_day_fixture',
            'fixture_calendar': 'Pandas business days; exchange holidays not represented',
            'historical_execution': 'Preserved unchanged Fold/purger AST definitions only; not the full historical runtime',
            'split_contract': SPLIT_CONTRACT_VERSION, 'horizon_observed_rows': 5,
            'rows': rows, 'historical_overlap_total': sum(len(r['historical_overlap_rows']) for r in rows),
            'corrected_overlap_total': sum(len(r['corrected_overlap_rows']) for r in rows),
            'all_checks_passed': all(row['check_passed'] for row in rows),
            'preserved_source_sha256': hashlib.sha256(old_source.read_bytes()).hexdigest(),
            'current_source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'historical_model_rerun': False, 'predictive_metrics': None,
            'scope': 'Actual preserved/corrected purge functions on the same labelled fixture dates and test blocks. '
                     'This establishes the purge-unit mismatch and correction on fixtures; historical overlap extent '
                     'and predictive-metric effects remain unmeasured without original inputs/runtime.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new dated audit receipt')
    report = audit()
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"Labelled purge comparison: historical overlap {report['historical_overlap_total']}; "
          f"corrected overlap {report['corrected_overlap_total']}; historical metrics unrerun")
    return 0 if report['all_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
