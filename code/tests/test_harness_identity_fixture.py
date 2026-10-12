"""Execute the real identity gate with labelled mock classifier seams."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.corpus_lineage import resolve_lineage


def gate(namespace):
    path = ROOT / 'src/investify/harness/run_spike.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'checked_run_all_arms')
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['checked_run_all_arms']


def test_harness_identity_surrounds_execution_and_returns_the_checked_identity():
    calls = []
    identity = {'fixture': 'LABELLED stable identity; no scientific execution'}
    def identify(*_):
        calls.append('identity')
        return copy.deepcopy(identity)
    def run(*_, **__):
        calls.append('run')
        return [{'fixture': True}]
    results, checked = gate({'run_identity': identify, 'run_all_arms': run})({}, 'fixture')
    assert calls == ['identity', 'run', 'identity']
    assert results == [{'fixture': True}]
    assert checked == identity


@pytest.mark.parametrize('part', ['source_sha256', 'input_snapshots', 'configuration_sha256', 'runtime'])
def test_each_harness_identity_mutation_refuses_results_before_export(part):
    before = {part: 'LABELLED original'}
    after = {part: 'LABELLED changed'}
    snapshots = iter([before, after])
    namespace = {'run_identity': lambda *_: next(snapshots), 'run_all_arms': lambda *_, **__: [{'fixture': True}]}
    with pytest.raises(RuntimeError, match='identity changed'):
        gate(namespace)({}, 'fixture')


@pytest.mark.parametrize('raw_present', [True, False])
def test_harness_export_retains_lineage_and_checks_the_manifest_bytes(tmp_path, raw_present):
    raw = tmp_path / 'LABELLED-source.csv'
    content = b'LABELLED raw subset fixture, not scientific data'
    digest = hashlib.sha256(content).hexdigest()
    if raw_present:
        raw.write_bytes(content)
    manifest = tmp_path / 'corpus_manifest.json'
    manifest.write_text(json.dumps({'subsets': [{'path': str(raw), 'sha256': digest}]}))
    manifest_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    identity = {'input_snapshots': {'corpus_manifest': {'files': {manifest.name: manifest_digest}}}}
    path = ROOT / 'src/investify/harness/run_spike.py'
    tree = ast.parse(path.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'provenance')
    namespace = {'__file__': str(path), 'Path': Path, 'hashlib': hashlib, 'json': json,
                 'resolve_lineage': resolve_lineage, 'git_commit': lambda: 'LABELLED MOCK REVISION',
                 'package_versions': lambda: {'fixture': True}, 'SPLIT_CONTRACT_VERSION': 'LABELLED MOCK CONTRACT',
                 'pd': __import__('pandas')}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    cfg = {'paths': {'artifacts': str(tmp_path)}, 'corpora': {'fixture': {'loader': 'fnspid'}},
           'news': {'extracted_path': str(raw)}, 'seed': 42, 'tickers': ['FIXTURE'], 'date_range': {},
           'xgboost': {}, 'splits': {}, 'leakage_control': {}, 'features': {'technical': [], 'sentiment': []}}
    result = namespace['provenance'](cfg, 'fixture', scientific_identity=identity)
    assert result['corpus_manifest_file_sha256'] == manifest_digest
    lineage = result['corpus_lineage']
    assert lineage['expected_raw_subset_sha256'] == digest
    assert lineage['actual_raw_subset_sha256'] == (digest if raw_present else None)
    assert lineage['status'] == ('original_raw_subset_bytes_verified' if raw_present else 'declared_only_original_raw_subset_missing')
    manifest.write_text('{"LABELLED":"changed after checked run"}')
    with pytest.raises(RuntimeError, match='manifest identity changed'):
        namespace['provenance'](cfg, 'fixture', scientific_identity=identity)
