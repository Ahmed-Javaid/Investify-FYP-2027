"""Resolve preserved raw-subset identities without filename-only substitutions."""
import hashlib
from pathlib import Path
import re


def hash_entries(node):
    rows = []
    if isinstance(node, dict):
        if isinstance(node.get('path'), str) and isinstance(node.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', node['sha256']):
            rows.append({'path': node['path'], 'sha256': node['sha256']})
        for value in node.values():
            rows.extend(hash_entries(value))
    elif isinstance(node, list):
        for value in node:
            rows.extend(hash_entries(value))
    return rows


def recorded_hash(node, target, *, project_base):
    target = (Path(project_base) / Path(target)).resolve()
    matches = {row['sha256'] for row in hash_entries(node)
               if (Path(project_base) / Path(row['path'])).resolve() == target}
    if len(matches) > 1:
        raise ValueError('Manifest assigns conflicting hashes to one resolved path')
    return next(iter(matches)) if matches else None


def resolve_lineage(node, target, *, project_base):
    target = (Path(project_base) / Path(target)).resolve()
    expected = recorded_hash(node, target, project_base=project_base)
    if not target.is_file():
        if expected is None:
            raise FileNotFoundError('External restored raw subset is absent; it cannot be identified by filename')
        return {'expected_raw_subset_sha256': expected, 'actual_raw_subset_sha256': None,
                'status': 'declared_only_original_raw_subset_missing', 'path': str(target)}
    checksum = hashlib.sha256()
    with target.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            checksum.update(chunk)
    actual = checksum.hexdigest()
    if expected is not None and actual != expected:
        raise ValueError('Raw subset bytes differ from the preserved manifest')
    if expected is None:
        matches = {row['sha256'] for row in hash_entries(node) if row['sha256'] == actual}
        if not matches:
            raise ValueError('External restored copy does not match any original raw-subset byte identity')
        expected = actual
    return {'expected_raw_subset_sha256': expected, 'actual_raw_subset_sha256': actual,
            'status': 'original_raw_subset_bytes_verified', 'path': str(target)}
