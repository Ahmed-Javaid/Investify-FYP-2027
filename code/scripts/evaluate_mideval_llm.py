"""Prepare a frozen plan or evaluate real local generations; no fixture mode."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investify.explain.evaluation import evaluate
from investify.explain.local_llm import ExplainerConfig, LocalExplainer
from investify.publisher_models import model_spec, verify_runtime, catalog


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', help='Exact identifier of an already available local model')
    parser.add_argument('--base-url', default='http://127.0.0.1:1234/v1')
    parser.add_argument('--timeout', type=float, default=20)
    parser.add_argument('--per-corpus', type=int, default=6)
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--plan', type=Path, help='Previously saved plan/report; required for real inference')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--journal', type=Path, help='New append-only JSONL receipt after each completed example')
    parser.add_argument('--runtime', type=Path, help='Verified original-publisher runtime receipt; required for actual inference')
    args = parser.parse_args()
    runtime = None
    spec = None
    if args.model is not None:
        matches = [model_spec(key) for key in catalog()['models'] if model_spec(key)['served_alias'] == args.model]
        if len(matches) != 1:
            parser.error('Declare an exact original-publisher serving alias from the catalog')
        spec = matches[0]
    if not args.plan_only:
        if args.runtime is None:
            parser.error('Actual inference requires --runtime with verified original-publisher weights')
        runtime = json.loads(args.runtime.read_text(encoding='utf-8-sig'))
        spec = model_spec(runtime['model_key'])
        if args.model != spec['served_alias']:
            parser.error('--model must match the verified publisher runtime alias')
        verify_runtime(spec, runtime)
    if not args.plan_only and args.output.exists():
        parser.error('Preserve prior real evaluation output; choose a new filename')
    if args.journal is not None and args.journal.exists():
        parser.error('Preserve prior evaluation journal; choose a new filename')
    config = ExplainerConfig(model=args.model, base_url=args.base_url, timeout_seconds=args.timeout,
                             api_key=os.environ.get('INVESTIFY_LLM_API_KEY') or None)
    declared_plan = None
    if args.plan:
        saved = json.loads(args.plan.read_text(encoding='utf-8'))
        if not isinstance(saved, dict):
            parser.error('Saved plan must be a JSON object')
        declared_plan = saved.get('plan', saved)
        if not args.plan_only and saved.get('declared_publisher_model') != spec:
            parser.error('Saved plan must predeclare this exact official publisher model identity')
    try:
        def progress(row):
            if args.journal is not None:
                args.journal.parent.mkdir(parents=True, exist_ok=True)
                with args.journal.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(row, allow_nan=False) + '\n')
            print(f"Retained {row['corpus']} / {row['session']}: {row['status']}; attempts={len(row['attempts'])}", flush=True)
        report = evaluate(LocalExplainer(config), per_corpus=args.per_corpus,
                          plan_only=args.plan_only, declared_plan=declared_plan, progress=progress)
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report['declared_publisher_model'] = spec
    if runtime is not None:
        report['publisher_runtime'] = runtime
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(f"{report['status']}: {report['raw_completions']} real completions; report: {args.output}")
    raise SystemExit(0 if report['status'] in {'plan_only', 'evaluated'} else 2)
