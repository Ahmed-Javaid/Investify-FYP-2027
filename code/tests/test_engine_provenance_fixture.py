"""Real provenance functions with labelled raw bytes and a fake version seam."""
import ast
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.corpus_lineage import recorded_hash, resolve_lineage


def provenance_functions():
    path = ROOT / 'src/investify/engine.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names = {'_corpus_lineage', '_corpus_manifest_hash', 'model_version_and_data_hashes'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    def identity(cfg, *_):
        return {'identity_sha256': hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()}
    namespace = {'__file__': str(path), 'Path': Path, 'json': json, 'resolve_lineage': resolve_lineage,
                 'recorded_hash': recorded_hash, '_git_commit': lambda: 'f' * 40,
                 'run_identity': identity, 'SPLIT_CONTRACT_VERSION': 'LABELLED FIXTURE CONTRACT'}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[])), str(path), 'exec'), namespace)
    return namespace


@pytest.mark.parametrize('raw_present', [True, False])
def test_provenance_retains_verified_or_declared_only_lineage_without_inventing_actual_hash(tmp_path, raw_present):
    raw = tmp_path / 'LABELLED-original.csv'
    content = b'LABELLED raw lineage fixture; not scientific data'
    digest = hashlib.sha256(content).hexdigest()
    if raw_present:
        raw.write_bytes(content)
    manifest = tmp_path / 'corpus_manifest.json'
    manifest.write_text(json.dumps({'subsets': [{'path': str(raw), 'sha256': digest}]}))
    cfg = {'paths': {'artifacts': str(tmp_path)}, 'default_corpus': 'fnspid',
           'news': {'extracted_path': str(raw)}, 'corpora': {'fnspid': {'loader': 'fnspid'}}}
    functions = provenance_functions()
    with patch.dict(sys.modules, {'xgboost': SimpleNamespace(__version__='LABELLED MOCK VERSION')}):
        frozen, hashes = functions['model_version_and_data_hashes'](dict(cfg, calibration_mode='frozen_classifier'))
        refit, other = functions['model_version_and_data_hashes'](dict(cfg, calibration_mode='refit_transfer'))
    assert frozen != refit
    assert hashes['scientific_run_identity_sha256'] != other['scientific_run_identity_sha256']
    assert hashes['corpus_manifest_sha256'] == digest
    assert hashes['corpus_manifest_file_sha256'] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    if raw_present:
        assert hashes['corpus_lineage_status'] == 'original_raw_subset_bytes_verified'
        assert hashes['corpus_actual_raw_subset_sha256'] == digest
    else:
        assert hashes['corpus_lineage_status'] == 'declared_only_original_raw_subset_missing'
        assert 'corpus_actual_raw_subset_sha256' not in hashes
