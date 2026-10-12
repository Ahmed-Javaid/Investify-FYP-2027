"""Actual label generation/selection on fixtures, no fitted model performance."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.calibration_split import available_calibration_rows
from investify.labels import compute_labels


def fixture_labels():
    prices = pd.DataFrame({'date': pd.bdate_range('2023-01-02', periods=120),
                           'close': 100 + np.sin(np.arange(120))})
    return prices, compute_labels(prices, horizon_days=5)


def test_calibration_targets_reaching_the_evaluation_block_are_excluded():
    _, labels = fixture_labels()
    selected, report = available_calibration_rows(labels, np.arange(80, 100), labels.loc[100, 'date'],
                                                  endpoint_column='label_end_date')
    assert report['candidate_rows'] == 20
    assert report['available_rows'] == 15
    assert report['removed_rows'] == 5
    assert report['excluded_source_indices'] == list(range(95, 100))
    assert not report['selection_uses_label_values']
    assert selected['label_end_date'].max() < labels.loc[100, 'date']


def test_future_evaluation_price_shock_cannot_change_calibrator_fit_inputs():
    prices, original = fixture_labels()
    changed_prices = prices.copy()
    changed_prices.loc[100, 'close'] *= 3
    changed = compute_labels(changed_prices, horizon_days=5)
    # The future shock actually affects a forbidden historical calibration label.
    assert original.loc[95, 'label_score'] != changed.loc[95, 'label_score']
    inputs, report = available_calibration_rows(original, np.arange(80, 100), original.loc[100, 'date'],
                                               endpoint_column='label_end_date')
    perturbed_inputs, current_report = available_calibration_rows(changed, np.arange(80, 100), changed.loc[100, 'date'],
                                                                 endpoint_column='label_end_date')
    pd.testing.assert_frame_equal(inputs, perturbed_inputs)
    assert report == current_report


def test_calibration_missing_endpoints_are_not_assumed_available():
    _, labels = fixture_labels()
    labels.loc[80, 'label_end_date'] = pd.NaT
    selected, report = available_calibration_rows(labels, np.arange(80, 100), labels.loc[100, 'date'],
                                                  endpoint_column='label_end_date')
    assert 80 not in selected.index
    assert report['removed_rows'] == 6


def test_no_available_calibration_labels_fail_instead_of_fitting_future_outcomes():
    _, labels = fixture_labels()
    with pytest.raises(ValueError, match='No calibration labels'):
        available_calibration_rows(labels, np.arange(95, 100), labels.loc[100, 'date'], endpoint_column='label_end_date')


def test_intraday_or_timezone_cutoffs_do_not_silently_change_session_semantics():
    _, labels = fixture_labels()
    for cutoff in ('2023-05-22T12:00:00', '2023-05-22T00:00:00Z', pd.NaT):
        with pytest.raises(ValueError, match='session date'):
            available_calibration_rows(labels, np.arange(80, 100), cutoff, endpoint_column='label_end_date')
