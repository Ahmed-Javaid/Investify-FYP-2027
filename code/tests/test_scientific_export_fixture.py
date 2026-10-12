"""Actual export entrypoint with explicit fixture engine/model results only."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import runpy
import sys
import time
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.scientific_trace import trace_bytes, validate_result_trace


def execute_fixture(tmp_path, monkeypatch, *, bad_brier=False, existing=False):
    fixture_helpers = runpy.run_path(str(ROOT / 'tests/test_scientific_trace_fixture.py'), run_name='LABELLED_EXPORT_FIXTURE')
    trace = fixture_helpers['trace_fixture']()
    payload, _ = fixture_helpers['exported_fixture'](trace)
    binding = trace['provenance']
    calls = []
    result = SimpleNamespace(records=[SimpleNamespace(to_dict=lambda row=row: copy.deepcopy(row))
                                     for row in payload['decision_records']],
                             model_version=binding['model_version'], data_hashes=payload['provenance']['data_hashes'],
                             calibration_fold_id=4, eval_fold_id=5, n_calibration_rows=2, n_eval_rows=2,
                             calibration_availability={'purpose': 'LABELLED unit fixture'},
                             scientific_identity=payload['provenance']['scientific_identity'],
                             input_consumption_audit={'purpose': 'LABELLED unit fixture'}, scientific_trace=trace,
                             brier_before=.9 if bad_brier else trace['replay']['brier_before'],
                             brier_after=trace['replay']['brier_after'])
    for name in ('cv_macro_f1_mean', 'cv_macro_f1_sd', 'baseline_cv_macro_f1_mean', 'baseline_cv_macro_f1_sd',
                 'eval_macro_f1_model', 'eval_macro_f1_baseline'):
        setattr(result, name, 0.)
    for name in ('cv_macro_f1_per_fold', 'baseline_cv_macro_f1_per_fold'):
        setattr(result, name, [0.] * 6)
    def run(*_, **kwargs):
        calls.append(kwargs)
        return result
    engine = SimpleNamespace(__file__=str(ROOT / 'src/investify/engine.py'), run_engine=run,
                             feature_cols=lambda _: trace['evaluation_scaler']['features'])
    cfg = {'seed': 42, 'tickers': ['FIXTURE'], 'labels': {'primary_horizon_days': 5},
           'xgboost': {'purpose': 'LABELLED mock backend; no classifier fit'},
           'default_corpus': 'FIXTURE', 'corpora': {'FIXTURE': {'purpose': 'LABELLED unit fixture'}}}
    config = tmp_path / 'LABELLED-config.yaml'
    config.write_text(yaml.safe_dump(cfg))
    output = tmp_path / 'LABELLED-export'
    if existing:
        output.mkdir()
        (output / 'preserve.txt').write_text('LABELLED preexisting evidence')
    monkeypatch.setattr(sys, 'argv', ['LABELLED-export-entrypoint', '--config', str(config), '--output-directory', str(output)])
    path = ROOT / 'scripts/build_decision_records.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    # Isolate imports of the unavailable scientific engine; all top-level
    # export/control-flow statements and the real binding validator execute.
    tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
    namespace = {'__file__': str(path), 'argparse': argparse, 'hashlib': hashlib, 'json': json,
                 'sys': sys, 'time': time, 'Path': Path, 'yaml': yaml, 'engine': engine,
                 'SPLIT_CONTRACT_VERSION': 'LABELLED FIXTURE CONTRACT',
                 'trace_bytes': trace_bytes, 'validate_result_trace': validate_result_trace}
    exec(compile(tree, str(path), 'exec'), namespace)
    return output, calls


def test_actual_export_roundtrip_binds_the_exact_trace_and_replays_its_records(tmp_path, monkeypatch):
    output, calls = execute_fixture(tmp_path, monkeypatch)
    assert len(calls) == 1
    assert calls[0]['calibration_mode'] == 'frozen_classifier'
    payload = json.loads((output / 'decision_records.json').read_text())
    serialized = (output / 'scientific_trace.json').read_bytes()
    assert payload['provenance']['scientific_trace_sha256'] == hashlib.sha256(serialized).hexdigest()
    assert validate_result_trace(payload, serialized)['purpose'] == 'unit_fixture'


def test_inconsistent_engine_summary_cannot_publish_result_or_trace(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match='Brier differs'):
        execute_fixture(tmp_path, monkeypatch, bad_brier=True)
    output = tmp_path / 'LABELLED-export'
    assert not (output / 'decision_records.json').exists()
    assert not (output / 'scientific_trace.json').exists()


def test_existing_export_directory_is_refused_without_changing_its_evidence(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match='Preserve prior scientific outputs'):
        execute_fixture(tmp_path, monkeypatch, existing=True)
    assert (tmp_path / 'LABELLED-export/preserve.txt').read_text() == 'LABELLED preexisting evidence'
    assert list((tmp_path / 'LABELLED-export').iterdir()) == [tmp_path / 'LABELLED-export/preserve.txt']
