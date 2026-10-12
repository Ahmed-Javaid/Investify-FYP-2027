"""Recheck pinned publisher pointers and optionally download exact model shards.

Uses the configured network/proxy normally. Never changes proxy settings, model
weights, existing files, or publisher identity to get past a failed connection.
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investify.publisher_models import manifest, verify_local


def parse_pointer(raw):
    text = raw.decode('ascii')
    match = re.fullmatch(r'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n?', text)
    if match is None:
        raise ValueError('Expected an exact publisher Git LFS pointer')
    return match.group(1), int(match.group(2))


def acquire(key, directory, download=False):
    value = manifest(key)
    receipt = {'schema': 'investify-official-acquisition-v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
               'model_key': key, 'publisher_manifest': value, 'download_requested': download,
               'pointer_checks': [], 'status': 'blocked', 'error': None, 'runtime': None}
    try:
        base = f"https://huggingface.co/{value['repository']}"
        # Check every shard before creating or downloading any model file.
        for item in value['files']:
            url = f"{base}/raw/{value['revision']}/{item['filename']}"
            with urllib.request.urlopen(url, timeout=10) as response:
                raw = response.read(1025)
            sha, size = parse_pointer(raw)
            if (sha, size) != (item['sha256'], item['size_bytes']):
                raise ValueError('Pinned publisher pointer differs from reviewed identity; refreeze before inference')
            receipt['pointer_checks'].append({'url': url, 'filename': item['filename'], 'sha256': sha, 'size_bytes': size})
        receipt['status'] = 'pointers_verified'
        if download:
            directory = Path(directory).resolve()
            temp_root = Path('E:/AI-Tools/Temp').resolve()
            if not directory.is_relative_to(temp_root):
                raise ValueError('Model cache must remain under E:/AI-Tools/Temp in this permission profile')
            directory.mkdir(parents=True, exist_ok=True)
            if any((directory / item['filename']).exists() for item in value['files']):
                raise ValueError('Existing model files are preserved; verify them separately')
            for item in value['files']:
                target = directory / item['filename']
                partial = target.with_suffix('.gguf.partial')
                hasher = hashlib.sha256()
                size = 0
                url = f"{base}/resolve/{value['revision']}/{item['filename']}"
                with partial.open('xb') as stream, urllib.request.urlopen(url, timeout=30) as response:
                    while True:
                        block = response.read(8 * 1024 * 1024)
                        if not block: break
                        size += len(block)
                        if size > item['size_bytes']: raise ValueError('Download exceeds declared publisher size')
                        stream.write(block)
                        hasher.update(block)
                if size != item['size_bytes'] or hasher.hexdigest() != item['sha256']:
                    raise ValueError('Downloaded bytes differ from official publisher pointer; partial file retained')
                partial.rename(target)
            receipt['runtime'] = verify_local(key, directory)
            receipt['status'] = 'downloaded_verified'
    except (OSError, ValueError) as error:
        receipt['status'] = 'blocked'
        receipt['error'] = f'{type(error).__name__}: {error}'
    receipt['completed_utc'] = datetime.now(timezone.utc).isoformat()
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-key', required=True)
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Preserve earlier acquisition receipts; choose a new filename')
    if args.download and args.directory is None: parser.error('--download requires --directory')
    result = acquire(args.model_key, args.directory, args.download)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(result['status'], result['error'] or args.model_key)
    raise SystemExit(2 if result['status'] == 'blocked' else 0)
