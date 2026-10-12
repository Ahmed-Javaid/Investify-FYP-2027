"""Verify original publisher model identities and every local weight shard.

The project catalog is a reviewed allowlist, not proof that weights are present.
No network requests or implicit model downloads occur in this module.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[2] / 'artifacts/mid_eval/official_model_catalog.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                   ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def catalog():
    data = json.loads(CATALOG.read_text(encoding='utf-8'))
    if data['schema'] != 'investify-official-publisher-models-v1':
        raise ValueError('Unsupported official publisher catalog')
    return data


def manifest(key):
    try:
        value = catalog()['models'][key]
    except KeyError as error:
        raise ValueError('Model must be declared in the official publisher catalog') from error
    if value['publisher'] != value['repository'].split('/')[0]:
        raise ValueError('Publisher and canonical repository owner differ')
    return value


def model_spec(key):
    value = manifest(key)
    first = value['files'][0]
    return {'model_id': f"{value['repository']}@{value['revision']}:{value['quantization']}",
            'served_alias': value['served_alias'], 'weights_sha256': first['sha256'],
            'weights_filename': first['filename']}


def validate_spec(spec):
    for key in catalog()['models']:
        if spec == model_spec(key):
            return key
    raise ValueError('Use an exact original-publisher model specification from the reviewed catalog')


def verify_local(key, directory):
    value = manifest(key)
    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError('Local model location must be a directory')
    verified = []
    for item in value['files']:
        path = (directory / item['filename']).resolve(strict=True)
        if not path.is_relative_to(directory) or not path.is_file():
            raise ValueError('Weight file escapes the declared model directory')
        if path.stat().st_size != item['size_bytes']:
            raise ValueError(f"Publisher size mismatch: {item['filename']}")
        hasher = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                hasher.update(block)
        if hasher.hexdigest() != item['sha256']:
            raise ValueError(f"Publisher SHA-256 mismatch: {item['filename']}")
        verified.append({**item, 'path': str(path)})
    return {'schema': 'investify-verified-publisher-runtime-v1', 'model_key': key,
            'verified_utc': datetime.now(timezone.utc).isoformat(),
            'publisher_manifest_sha256': digest(value), 'catalog_sha256': digest(catalog()),
            'served_alias': value['served_alias'], 'model_sha256': value['files'][0]['sha256'],
            'model_directory': str(directory), 'verified_files': verified,
            'identity_scope': 'All actual local weight bytes match the inspected official publisher pointers; serving alias alone does not establish weight origin.'}


def verify_runtime(spec, receipt):
    key = validate_spec(spec)
    if (receipt.get('schema') != 'investify-verified-publisher-runtime-v1'
            or receipt.get('model_key') != key
            or receipt.get('publisher_manifest_sha256') != digest(manifest(key))
            or receipt.get('catalog_sha256') != digest(catalog())
            or receipt.get('served_alias') != spec['served_alias']):
        raise ValueError('An actual verified original-publisher runtime receipt is required')
    fresh = verify_local(key, receipt['model_directory'])
    if fresh['verified_files'] != receipt.get('verified_files'):
        raise ValueError('Actual model files differ from the retained runtime receipt')
    return fresh
