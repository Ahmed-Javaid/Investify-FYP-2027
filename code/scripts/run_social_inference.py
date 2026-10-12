"""Run a frozen social candidate from existing local weights, never download/label."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.sentiment_inference import run_inference
from investify.sentiment_selection import PROTOCOL
from investify.sentiment_receipts import run_bundle


def read(path):
    def invalid(value): raise ValueError(f'Non-finite JSON number: {value}')
    return json.loads(path.read_text(encoding='utf-8-sig'), parse_constant=invalid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--model-id', required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--receipt-output', type=Path, required=True)
    parser.add_argument('--publisher-catalog', type=Path)
    parser.add_argument('--receipt-plan', type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.receipt_output.resolve() or args.output.exists() or args.receipt_output.exists():
        raise ValueError('Preserve prior model runs/receipts; use two distinct new output paths')
    try:
        if args.publisher_catalog is None or args.receipt_plan is None:
            raise ValueError('Actual candidate inference now requires V4 publisher/receipt gates; use social_study_v4.py or supply --publisher-catalog and --receipt-plan')
        bundle = run_bundle(read(args.benchmark), read(args.plan), read(args.publisher_catalog), read(args.receipt_plan),
                            args.model_id, args.snapshot)
        run, receipt = bundle['run'], bundle
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as error:
        receipt = {'protocol': PROTOCOL, 'status': 'blocked', 'reason': str(error),
                   'model_downloads': 0, 'model_outputs': 0, 'quality_metrics': None}
        args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
        args.receipt_output.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print('blocked; no model-run file created; receipt:', args.receipt_output)
        return 1
    for path, data in ((args.output, [run]), (args.receipt_output, receipt)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')
    print(f'Local inference retained {len(run["outputs"])} outcomes; inspect failures and pair all declared candidates before scoring')
    return 0 if all('probabilities' in row for row in run['outputs']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
