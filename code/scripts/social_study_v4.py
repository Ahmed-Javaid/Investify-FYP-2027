"""New-directory-only receipt-bound social inference; preserved V3 stays intact."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.sentiment_receipts import PROTOCOL, freeze_receipt_plan, run_bundle, compare_bundles, read_json


def read(path):
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError('Study JSON exceeds its five-megabyte limit')
    return read_json(path)


def reserve_output(args):
    """Refuse all input/output aliases before reserving a new task directory."""
    directory = args.output_directory.resolve()
    if not directory.is_relative_to(ROOT.parent.resolve()) or directory.exists():
        raise ValueError('Preserve prior outputs; reserve a new directory under GPT_MIDEVAL')
    inputs = [args.benchmark, args.parent_plan, args.catalog, args.plan, *(args.bundles or [])]
    for value in inputs:
        if value is not None:
            path = value.resolve()
            if path == directory or path.is_relative_to(directory):
                raise ValueError('Study outputs collide with an input file/directory')
    if args.snapshot:
        snapshot = args.snapshot.resolve()
        if directory.is_relative_to(snapshot) or snapshot.is_relative_to(directory):
            raise ValueError('Study outputs must stay separate from an original model snapshot')
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--freeze', action='store_true')
    actions.add_argument('--run', action='store_true')
    actions.add_argument('--compare', action='store_true')
    parser.add_argument('--benchmark', type=Path, default=ROOT / 'artifacts/mid_eval/social_benchmark.json')
    parser.add_argument('--parent-plan', type=Path, default=ROOT / 'artifacts/mid_eval/social_selection_plan.json')
    parser.add_argument('--catalog', type=Path, default=ROOT / 'artifacts/mid_eval/social_publisher_catalog_v4.json')
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--model-id')
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--bundles', type=Path, nargs='+')
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args(argv)
    directory = reserve_output(args)  # Reserve before any model call.
    try:
        data, parent, catalog = read(args.benchmark), read(args.parent_plan), read(args.catalog)
        if args.freeze:
            if args.plan or args.snapshot or args.model_id or args.bundles:
                raise ValueError('Freeze has no run/plan/bundle inputs')
            result = freeze_receipt_plan(data, parent, catalog)
            name, status = 'plan.json', 'plan_frozen'
        elif args.run:
            if not args.plan or not args.snapshot or not args.model_id or args.bundles:
                raise ValueError('Run requires a V4 plan, declared model and genuine local snapshot')
            result = run_bundle(data, parent, catalog, read(args.plan), args.model_id, args.snapshot)
            name = 'bundle.json'
            status = 'run_retained' if all('probabilities' in row for row in result['run']['outputs']) else 'partial'
        else:
            if not args.plan or not args.bundles or args.snapshot or args.model_id:
                raise ValueError('Compare requires a V4 plan and original run/receipt bundles')
            result = compare_bundles(data, parent, catalog, read(args.plan), [read(path) for path in args.bundles])
            name, status = 'comparison.json', result['status']
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as error:
        result = {'protocol': PROTOCOL, 'status': 'blocked', 'reason': str(error),
                  'quality_metrics': None, 'model_downloads': 0,
                  'scope': 'Failure retained; no fabricated model outputs, publisher metadata or study winner'}
        name, status = 'failure.json', 'blocked'
    with (directory / name).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False))
    print(f'Social V4: {status}; {directory / name}; hash/receipt binding is not independent execution attestation')
    return 0 if status in ('plan_frozen', 'run_retained', 'complete') else 1


if __name__ == '__main__':
    raise SystemExit(main())
