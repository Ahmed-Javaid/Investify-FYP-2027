"""Inspect a bounded pip cache for compatible science wheels; never install."""
import argparse
import email
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

TARGETS = {'numpy', 'pandas', 'scipy', 'scikit-learn', 'xgboost', 'shap', 'torch',
           'transformers', 'pandas-market-calendars', 'exchange-calendars',
           'safetensors', 'peft', 'bitsandbytes', 'datasets', 'accelerate'}
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--limit', type=int, default=5000)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'evidence') or output.exists() or not 1 <= args.limit <= 20000:
        raise ValueError('Use a new evidence path and a bounded 1..20000 file limit')
    from packaging.tags import sys_tags, parse_tag
    supported = set(sys_tags())
    inspected, rows, errors = 0, [], []
    truncated = False
    for path in args.cache.rglob('*'):
        if not path.is_file() or path.suffix not in ('.body', '.whl'):
            continue
        if inspected >= args.limit:
            truncated = True
            break
        inspected += 1
        try:
            with path.open('rb') as stream:
                if stream.read(4) != b'PK\x03\x04':
                    continue
            with zipfile.ZipFile(path) as wheel:
                metadata = [n for n in wheel.namelist() if n.endswith('.dist-info/METADATA')]
                wheelinfo = [n for n in wheel.namelist() if n.endswith('.dist-info/WHEEL')]
                if len(metadata) != 1 or len(wheelinfo) != 1:
                    continue
                info = email.message_from_bytes(wheel.read(metadata[0]))
                name = info.get('Name', '').lower().replace('_', '-')
                if name not in TARGETS:
                    continue
                tags = email.message_from_bytes(wheel.read(wheelinfo[0])).get_all('Tag', [])
                compatible = any(supported & parse_tag(tag) for tag in tags)
                rows.append({'path': str(path), 'name': name, 'version': info.get('Version'),
                             'wheel_tags': tags, 'compatible_with_inspected_interpreter': compatible,
                             'bytes': path.stat().st_size,
                             'origin_authenticated': False})
        except (OSError, ValueError, zipfile.BadZipFile, KeyError) as error:
            errors.append({'path': str(path), 'error': f'{type(error).__name__}: {error}'})
    receipt = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'cache': str(args.cache.resolve()),
               'files_inspected': inspected, 'file_limit': args.limit, 'search_truncated': truncated,
               'candidate_wheels': rows, 'errors': errors, 'installation_executed': False,
               'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'scope': 'Read-only ZIP wheel metadata/tag discovery in one declared cache, not source/publisher '
                        'authentication or dependency-lock restoration. Cache is preserved; no inferred model weights.'}
    output.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(f'Cache audit: {inspected} files; {len(rows)} target wheels; '
          f"{sum(row['compatible_with_inspected_interpreter'] for row in rows)} interpreter-compatible; no installation")


if __name__ == '__main__':
    main()
