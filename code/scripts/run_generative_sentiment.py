"""Freeze/run/compare real local generative sentiment baselines, separate from classifiers."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.generative_sentiment import frozen_plan, run_model, compare


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['freeze', 'run', 'compare'])
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--parent-plan', type=Path, required=True)
    parser.add_argument('--models', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--model-id')
    parser.add_argument('--base-url')
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--runs', type=Path, nargs='+')
    parser.add_argument('--journal', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.journal is not None and args.journal.exists():
        raise ValueError('Preserve prior real study output/journal; choose new filenames')
    benchmark, parent = read(args.benchmark), read(args.parent_plan)
    if args.operation == 'freeze':
        result = frozen_plan(benchmark, parent, read(args.models))
    elif args.operation == 'run':
        def progress(row):
            if args.journal is not None:
                args.journal.parent.mkdir(parents=True, exist_ok=True)
                with args.journal.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(row, allow_nan=False) + '\n')
            print(f"Retained {row['post_id']}: {row['label'] or 'failed'}", flush=True)
        result = run_model(benchmark, parent, read(args.plan), args.model_id, args.base_url, read(args.runtime), progress=progress)
    else:
        runs = [read(path) for path in args.runs]
        if any(run.get('execution_kind') != 'verified_official_local' for run in runs):
            raise ValueError('Actual comparison requires verified original-publisher runs, never unit fixtures')
        result = compare(benchmark, parent, read(args.plan), runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print('Saved actual supplementary study artifact:', args.output)


if __name__ == '__main__':
    main()
