"""Validate and freeze actual retained session-generated labels; never generate."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.sentiment_annotation import attach_session_annotations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--batches', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--receipt-output', type=Path, required=True)
    args = parser.parse_args()
    data, receipt = attach_session_annotations(json.loads(args.corpus.read_text(encoding='utf-8')),
                                              json.loads(args.run.read_text(encoding='utf-8')), args.batches)
    if args.output.exists() or args.receipt_output.exists():
        raise ValueError('Preserve existing research artifacts; choose new output filenames')
    for path, value in ((args.output, data), (args.receipt_output, receipt)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print('Actual AI reference labels validated and frozen; no candidate inference or human validation')


if __name__ == '__main__':
    main()
