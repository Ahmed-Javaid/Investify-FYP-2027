"""Merge original/revised source into a new canonical workspace after backup."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

WORKSPACE = Path('E:/Uni_Stuff/FYP').resolve()
CURRENT = WORKSPACE / 'GPT_MIDEVAL'
ORIGINAL = Path('E:/Uni_Stuff/investify_repo').resolve()
DESTINATION = WORKSPACE / 'Investify'
SKIP = {'.git', '__pycache__', '.pytest_cache', '.cache', 'node_modules', '.venv'}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def git(root, *arguments):
    return subprocess.check_output(['git', '-C', str(root), *arguments],
                                   env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))


def tracked(root, working=False):
    arguments = ['ls-files', '-z']
    if working:
        arguments += ['--cached', '--others', '--exclude-standard']
    return {name for name in git(root, *arguments).decode('utf-8').split('\0') if name}


def copy(source, target, inventory):
    source = source.resolve(strict=True)
    if not target.resolve().is_relative_to(DESTINATION):
        raise ValueError('Destination escaped canonical workspace')
    if not (source.is_relative_to(WORKSPACE) or source.is_relative_to(ORIGINAL)):
        raise ValueError('Unexpected external source')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    expected = sha(source)
    if sha(target) != expected:
        raise ValueError('Merged copy failed byte verification')
    inventory[target.relative_to(DESTINATION).as_posix()] = expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup-receipt', type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.backup_receipt.read_text(encoding='utf-8'))
    backup = Path(receipt['archive']).resolve()
    if not receipt['passed'] or not backup.is_relative_to(WORKSPACE / '_archives') or sha(backup) != receipt['archive_sha256']:
        raise ValueError('A verified matching pre-merge backup is required')
    if DESTINATION.exists():
        raise ValueError('Canonical destination already exists; preserve it before another merge')
    DESTINATION.mkdir()
    inventory = {}
    revised = tracked(CURRENT / 'code', working=True)
    deleted = set(git(CURRENT / 'code', 'diff', '--name-only', '--diff-filter=D').decode('utf-8').splitlines())
    original_only, overridden = [], []
    for relative in sorted(tracked(ORIGINAL) - deleted):
        source = ORIGINAL / relative
        if not source.is_file() or source.suffix.lower() in ('.pyc', '.gguf', '.safetensors', '.bin'):
            continue
        if relative not in revised:
            copy(source, DESTINATION / 'code' / relative, inventory)
            original_only.append(relative)
    for relative in sorted(revised):
        source = CURRENT / 'code' / relative
        if source.is_file():
            if (ORIGINAL / relative).is_file() and sha(source) != sha(ORIGINAL / relative):
                overridden.append(relative)
            copy(source, DESTINATION / 'code' / relative, inventory)
    for directory, folders, names in os.walk(CURRENT, followlinks=False):
        directory = Path(directory)
        folders[:] = [name for name in folders if name not in SKIP
                      and not (directory == CURRENT and name == 'code')
                      and not (directory / name).is_symlink()]
        for name in names:
            source = directory / name
            if source.suffix.lower() in ('.zip', '.pyc', '.gguf', '.safetensors', '.bin') or name == 'source_revision.json':
                continue
            copy(source, DESTINATION / source.relative_to(CURRENT), inventory)
    for source in WORKSPACE.iterdir():
        if source.name in {'GPT_MIDEVAL', 'Investify', '_archives'}:
            continue
        entries = source.rglob('*') if source.is_dir() else [source]
        for old in entries:
            if old.is_file():
                copy(old, DESTINATION / 'original_materials/FYP' / old.relative_to(WORKSPACE), inventory)
    base = git(CURRENT / 'code', 'rev-parse', 'HEAD').decode().strip()
    code_inventory = {name.removeprefix('code/'): value for name, value in inventory.items() if name.startswith('code/')}
    (DESTINATION / 'code/source_revision.json').write_text(json.dumps(
        {'schema': 'investify-working-source-revision-v2', 'commit': base, 'working_tree': True,
         'files': code_inventory}, indent=2), encoding='utf-8')
    ignore = ('**/.git/\n**/__pycache__/\n**/*.pyc\n**/.pytest_cache/\n**/.cache/\n**/.venv/\n'
              '**/.env\n**/.env.*\n**/*.gguf\n**/*.safetensors\n**/*.bin\n**/*.zip\n'
              'code/data/raw/\ncode/data/store/\noriginal_materials/\n'
              'sources/stocknet/\nevidence/social_pilot/source/\n')
    (DESTINATION / '.gitignore').write_text(ignore, encoding='utf-8')
    lineage = {'merged_utc': datetime.now(timezone.utc).isoformat(), 'canonical_project': str(DESTINATION),
               'backup': receipt, 'original_checkout': str(ORIGINAL),
               'original_commit': git(ORIGINAL, 'rev-parse', 'HEAD').decode().strip(),
               'revised_source': str(CURRENT), 'revised_base_commit': base,
               'precedence': 'Revised files override matching original code; original-only tracked source retained.',
               'original_only_code': original_only, 'overridden_original_code': overridden,
               'files_sha256': inventory, 'old_sources_modified': False,
               'scope': 'Tool-assisted local integration; old Git history is preserved in the backup. '
                        'Archived code source_revision retains its captured base identity; canonical Git is separate. '
                        'No student authorship, new model results, data rights or publication inferred.'}
    (DESTINATION / 'MERGE_MANIFEST.json').write_text(json.dumps(lineage, indent=2), encoding='utf-8')
    print(json.dumps({'project': str(DESTINATION), 'verified_copies': len(inventory),
                      'original_only_code': len(original_only), 'updated_code_files': len(overridden),
                      'old_sources_modified': False}, indent=2))


if __name__ == '__main__':
    main()
