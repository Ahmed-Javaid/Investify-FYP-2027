"""Preserve the pre-merge workspace/original checkout with byte verification."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import zipfile

WORKSPACE = Path('E:/Uni_Stuff/FYP').resolve()
ORIGINAL = Path('E:/Uni_Stuff/investify_repo').resolve()


def checksum(stream):
    value = hashlib.sha256()
    for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
        value.update(chunk)
    return value.hexdigest()


def files(root, prefix):
    excluded = [WORKSPACE / '_archives', WORKSPACE / 'Investify',
                WORKSPACE / 'GPT_MIDEVAL/evidence/market_reacquisition_20261012']
    for directory, folders, names in os.walk(root, followlinks=False):
        directory = Path(directory)
        folders[:] = [name for name in folders if not (directory / name).is_symlink()
                      and not ((directory / name).stat().st_file_attributes & 0x400)
                      and not any((directory / name).resolve().is_relative_to(item) for item in excluded)]
        for name in sorted(names):
            source = directory / name
            if source.is_symlink() or source.stat().st_file_attributes & 0x400:
                raise ValueError('A linked file requires explicit snapshot treatment: ' + str(source))
            yield source, prefix + '/' + source.relative_to(root).as_posix()


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = WORKSPACE / '_archives' / ('Investify_before_merge_' + stamp + '.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    receipt = destination.with_suffix('.json')
    entries = [*files(WORKSPACE, 'FYP'), *files(ORIGINAL, 'investify_repo')]
    manifest = {'captured_utc': datetime.now(timezone.utc).isoformat(), 'files': {},
                'roots': {'FYP': str(WORKSPACE), 'investify_repo': str(ORIGINAL)},
                'excluded': ['New canonical Investify directory', 'Backup output directory',
                             'Concurrent new market acquisition receipts'],
                'scope': 'Private local pre-merge backup, including existing Git history; no publication'}
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
        for source, name in entries:
            with source.open('rb') as incoming, bundle.open(name, 'w') as outgoing:
                digest = hashlib.sha256()
                size = 0
                for chunk in iter(lambda: incoming.read(4 * 1024 * 1024), b''):
                    outgoing.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            manifest['files'][name] = {'sha256': digest.hexdigest(), 'bytes': size}
        bundle.writestr('snapshot_manifest.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(destination) as bundle:
        for source, name in entries:
            expected = manifest['files'][name]['sha256']
            with bundle.open(name) as stream:
                if checksum(stream) != expected:
                    raise ValueError('Backup entry verification failed: ' + name)
            with source.open('rb') as stream:
                if checksum(stream) != expected:
                    raise ValueError('Source changed during backup; do not merge: ' + name)
    with destination.open('rb') as stream:
        digest = checksum(stream)
    result = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'archive': str(destination),
              'archive_sha256': digest, 'files': len(entries), 'zip_bytes': destination.stat().st_size,
              'archive_entry_hashes_verified': True, 'source_hashes_rechecked': True,
              'passed': True, 'scope': manifest['scope']}
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
