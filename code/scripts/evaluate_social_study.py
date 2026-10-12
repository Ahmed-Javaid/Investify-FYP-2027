"""Freeze or score a real equity-social study with declared AI or human labels."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.sentiment_selection import PROTOCOL, freeze_plan, evaluate_predictions
from investify.sentiment_receipts import compare_bundles


def read(path):
    def invalid(value):
        raise ValueError(f'Non-finite JSON number: {value}')
    return json.loads(path.read_text(encoding='utf-8-sig'), parse_constant=invalid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', type=Path, default=ROOT / 'artifacts/mid_eval/social_benchmark.json')
    parser.add_argument('--checkpoints', type=Path, help='Array of exact candidate identities/revisions/preprocessing for freezing')
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--predictions', type=Path, help='Array of real per-candidate inference runs')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--publisher-catalog', type=Path)
    parser.add_argument('--receipt-plan', type=Path)
    parser.add_argument('--bundles', type=Path, nargs='+')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve frozen plans/prior reports; use a new output path')
    try:
        benchmark = read(args.benchmark)
        if args.freeze:
            if args.checkpoints is None or args.plan is not None or args.predictions is not None:
                raise ValueError('Freeze requires checkpoint declarations and no plan or prediction input')
            result = freeze_plan(benchmark, read(args.checkpoints))
            status = 'plan_frozen'
        else:
            if args.plan is None or args.publisher_catalog is None or args.receipt_plan is None or not args.bundles or args.checkpoints is not None:
                raise ValueError('Research comparison requires matching V4 original-byte run/receipt bundles; standalone supplied probabilities are insufficient')
            result = compare_bundles(benchmark, read(args.plan), read(args.publisher_catalog), read(args.receipt_plan),
                                     [read(path) for path in args.bundles])
            status = result['status']
    except (OSError, KeyError, TypeError, ValueError) as error:
        status = 'blocked'
        result = {'protocol': PROTOCOL, 'status': status, 'reason': str(error), 'quality_metrics': None,
                  'benchmark_path': str(args.benchmark), 'posts_acquired_by_this_command': 0,
                  'human_annotations_created_by_this_command': 0, 'model_inference_calls': 0,
                  'ai_annotations_created_by_this_command': 0,
                  'scope': 'Schema/metric tooling only. No posts, annotations or model outputs are manufactured.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(f'{status}; report: {args.output}')
    return 0 if status in ('plan_frozen', 'complete') else 1


if __name__ == '__main__':
    raise SystemExit(main())
