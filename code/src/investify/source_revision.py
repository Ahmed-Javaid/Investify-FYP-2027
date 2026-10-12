"""Revision metadata for an owned checkout or a checked source-bundle inventory.

Inventory hashes check included contents, not author/origin authenticity.
Absence of Git is explicit; an ancestor repository must never supply the ID.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path


def source_revision(root: Path) -> dict:
    root = root.resolve()
    if (root / '.git').exists():
        try:
            commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True,
                                             stderr=subprocess.DEVNULL).strip()
            dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True,
                                                 stderr=subprocess.DEVNULL).strip())
            return {'git_commit': commit, 'git_dirty': dirty, 'revision_source': 'owned_git_checkout'}
        except (OSError, subprocess.CalledProcessError):
            return {'git_commit': None, 'git_dirty': None, 'revision_source': 'git_unavailable'}
    manifest_path = root / 'source_revision.json'
    if not manifest_path.exists():
        return {'git_commit': None, 'git_dirty': None, 'revision_source': 'unavailable'}
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    working = isinstance(manifest, dict) and manifest.get('schema') == 'investify-working-source-revision-v2'
    fields = {'schema', 'commit', 'files', 'working_tree'} if working else {'schema', 'commit', 'files'}
    if (not isinstance(manifest, dict) or set(manifest) != fields
            or manifest['schema'] not in ('investify-source-revision-v1', 'investify-working-source-revision-v2')
            or working and manifest.get('working_tree') is not True
            or not isinstance(manifest['commit'], str) or not re.fullmatch('[0-9a-f]{40}', manifest['commit'])
            or not isinstance(manifest['files'], dict) or not manifest['files']):
        raise ValueError('source bundle revision inventory is invalid')
    for relative, expected in manifest['files'].items():
        path = (root / relative).resolve()
        if (not relative or Path(relative).is_absolute() or not path.is_relative_to(root)
                or not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)):
            raise ValueError('source bundle inventory has an unsafe path or invalid digest')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'source bundle file missing or modified: {relative}')
    return {'git_commit': manifest['commit'], 'git_dirty': True if working else None,
            'revision_source': 'checked_working_tree_inventory' if working else 'checked_bundle_inventory',
            'bundle_files_verified': len(manifest['files']),
            'inventory_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
