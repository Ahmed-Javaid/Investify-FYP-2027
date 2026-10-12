"""Prepare frozen assistant teacher packets, or verify/import actual saved prose."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.explain.teacher_session import freeze_plan, prepare_packets, import_responses, export_rows


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    if path.exists(): raise ValueError('Preserve prior teacher evidence; choose a new directory/file')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['prepare', 'import'])
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--raw-batches', type=Path, nargs='+')
    args = parser.parse_args()
    if args.directory.exists(): parser.error('Preserve prior evidence; use a new output directory')
    if args.operation == 'prepare':
        plan = freeze_plan()
        packets = prepare_packets(plan)
        write(args.directory / 'plan.json', plan)
        for packet in packets: write(args.directory / (packet['packet_id'] + '.json'), packet)
        print(f'Prepared {len(plan["selected_records"])} actual development records; no teacher output generated')
    else:
        if args.plan is None or not args.raw_batches: parser.error('Import needs original --plan and --raw-batches')
        report = import_responses(read(args.plan), args.raw_batches)
        write(args.directory / 'verification.json', report)
        for split in ('train', 'validation'):
            rows = export_rows(report, split)
            path = args.directory / (split + '.jsonl')
            path.write_text(''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n' for row in rows), encoding='utf-8')
        print(f'Actual teacher prose: {report["accepted"]} accepted, {report["rejected"]} rejected, {len(report["missing_record_ids"])} missing; no student training')
