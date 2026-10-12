"""Actual orchestration definitions with labelled mock model seams.

AST isolation avoids claiming absent XGBoost/sklearn/SHAP imports ran. No
model fit, inference, original market-data run or quality score is evidence
from these fixtures. The function bodies and temporal helpers are real.
"""
import ast
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.calibration_split import available_calibration_rows
from investify.harness.splits import Fold, expanding_purged_walk_forward
from investify.labels import compute_labels


def definitions(path, names, namespace):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names]
    module = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
    exec(compile(module, str(path), 'exec'), namespace)


def orchestration(mode, *, mutation=False):
    technical = ['rsi_14', 'macd_hist', 'dist_sma200', 'bollinger_pos', 'obv_slope']
    dates = pd.bdate_range('2023-01-02', periods=180)
    prices = pd.DataFrame({'date': dates, 'close': 100 + np.sin(np.arange(180))})
    labels = compute_labels(prices, horizon_days=5)
    matrix = labels.copy()
    matrix['label_5d'] = matrix['label']
    matrix['label_end_5d'] = matrix['label_end_date']
    for name in technical:
        matrix[name] = 1.0
    matrix.loc[45, 'rsi_14'] = np.nan  # Exercise the actual shared feature mask.
    matrix['mean_polarity'] = .1
    cfg = {'features': {'technical': technical, 'sentiment': ['mean_polarity']},
           'labels': {'primary_horizon_days': 5, 'class_thresholds': [-.5, .5]},
           'splits': {'n_folds': 6, 'embargo_days': 5}, 'seed': 42, 'tickers': ['FIXTURE']}
    fits, scores, calibration_targets, emitted = [], [], [], []
    def fit(frame, *_):
        model, scaler = object(), object()
        fits.append((model, scaler, frame.copy()))
        return model, scaler
    def score(model, scaler, frame, cols):
        scores.append((model, scaler, frame.copy()))
        return np.tile([.6, .2, .2], (len(frame), 1)), np.zeros((len(frame), 3)), frame.copy()
    def calibrate(probabilities, targets):
        calibration_targets.append((probabilities.copy(), targets.copy()))
        return 'LABELLED MOCK CALIBRATOR'
    def records(**kwargs):
        emitted.append(kwargs)
        return []  # No fixture records can become a scientific output.
    namespace = {'__name__': __name__, 'dataclass': dataclass, 'field': field, 'np': np, 'pd': pd, 'Path': Path,
                 'Fold': Fold, 'CLASS_LABELS': ('Buy', 'Hold', 'Sell'),
                 'CLASS_TO_INT': {'Buy': 0, 'Hold': 1, 'Sell': 2}, 'INT_TO_CLASS': {0: 'Buy', 1: 'Hold', 2: 'Sell'},
                 'ARMS': {'A_CLEAN': SimpleNamespace(splitter='purged')},
                 'expanding_purged_walk_forward': expanding_purged_walk_forward,
                 'build_all_matrices': lambda *_args, **_kwargs: {'A_CLEAN': matrix},
                 'fit_predict_fold': lambda train, test, *_: (test['label_5d'].astype(str).to_numpy(), ['Hold'] * len(test)),
                 'macro_f1': lambda *_: 0.0, 'brier_score': lambda *_: 0.0,
                 'fit_scaler': lambda *_: object(), 'apply_scaler': lambda frame, *_: frame.copy(),
                 'train_xgboost': fit, 'score_fold': score, 'fit_isotonic_calibrators': calibrate,
                 'apply_calibration': lambda probabilities, _: probabilities,
                 'available_calibration_rows': available_calibration_rows,
                 'build_shap_explainer': lambda model: SimpleNamespace(expected_value=[0, 0, 0]),
                 'compute_shap_values': lambda _, frame, cols: np.zeros((len(frame), len(cols), 3)),
                 'make_decision_records': records,
                 'run_identity': lambda *_: {'identity_sha256': 'a' * 64, 'execution_kind': 'LABELLED MOCK ORCHESTRATION; no real run identity'},
                 'capture_trace': lambda **_: {'purpose': 'unit_fixture', 'real_model_bytes': False},
                 'model_version_and_data_hashes': lambda *_: ('LABELLED MOCK MODEL', {'fixture': 'not scientific'})}
    if mutation:
        identities = iter([{'fixture_identity': 'before'}, {'fixture_identity': 'changed'}])
        namespace['run_identity'] = lambda *_: next(identities)
    definitions(ROOT / 'src/investify/harness/arms.py', {'make_folds', 'clean_row_mask'}, namespace)
    definitions(ROOT / 'src/investify/engine.py', {'EngineResult', 'feature_cols', 'linear_baseline_predict', 'run_engine'}, namespace)
    result = namespace['run_engine'](cfg, calibration_mode=mode)
    return result, fits, scores, calibration_targets, emitted


def test_frozen_mode_reuses_the_exact_classifier_and_scaler_for_calibration_and_evaluation():
    result, fits, scores, _, emitted = orchestration('frozen_classifier')
    assert len(fits) == 1
    assert len(scores) == 2
    assert scores[0][0] is scores[1][0] is fits[0][0]
    assert scores[0][1] is scores[1][1] is fits[0][1]
    assert result.records == []
    assert len(emitted) == 1


def test_explicit_refit_comparator_fits_distinct_models_and_scalers():
    _, fits, scores, _, _ = orchestration('refit_transfer')
    assert len(fits) == 2
    assert scores[0][0] is not scores[1][0]
    assert scores[0][1] is not scores[1][1]


def test_full_price_endpoints_survive_feature_mask_and_calibration_selection_before_scoring():
    result, fits, scores, targets, emitted = orchestration('frozen_classifier')
    calibration_frame, evaluation_frame = scores[0][2], scores[1][2]
    cutoff = evaluation_frame['date'].iloc[0]
    assert 45 not in calibration_frame.index
    assert (calibration_frame['label_end_5d'] < cutoff).all()
    assert (fits[0][2]['label_end_5d'] < calibration_frame['date'].iloc[0]).all()
    assert result.calibration_availability['removed_rows'] > 0
    assert len(targets[0][1]) == result.n_calibration_rows == len(calibration_frame)
    full_dates = pd.Series(pd.bdate_range('2023-01-02', periods=180))
    full_endpoint_map = dict(zip(full_dates, full_dates.shift(-5)))
    for frame in (fits[0][2], calibration_frame, evaluation_frame):
        assert frame['label_end_5d'].tolist() == [full_endpoint_map[date] for date in frame['date']]
    pd.testing.assert_series_equal(emitted[0]['eval_rows']['label_end_5d'], evaluation_frame['label_end_5d'])


def test_unknown_calibration_mode_is_refused():
    with pytest.raises(ValueError, match='frozen_classifier'):
        orchestration('undeclared')


def test_identity_change_during_orchestration_refuses_a_result():
    with pytest.raises(RuntimeError, match='identity changed'):
        orchestration('frozen_classifier', mutation=True)
