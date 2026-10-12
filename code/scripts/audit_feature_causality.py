"""Run the labelled fixture feature-causality audit without model/data restoration."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.features.causality_audit import run_audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve dated receipts; use a new filename')
    report = run_audit()
    report['checked_utc'] = datetime.now(timezone.utc).isoformat()
    report['runtime'] = {'python': sys.version.split()[0], 'executable': sys.executable}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(f"Labelled fixture audit: {report['checks_passed']}/{len(report['checks'])} checks; "
          f"{report['deliberate_mutations_detected']} deliberate centred mutations detected; no classifier fit")
    return 0 if report['all_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
