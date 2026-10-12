"""Synthetic business-session endpoints expose calendar-day purge errors."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.harness.splits import expanding_purged_walk_forward
from investify.labels import compute_labels


def fixtures():
    dates = pd.Series(pd.bdate_range('2023-01-02', periods=140))
    return dates, dates.shift(-5)


def test_every_training_label_endpoint_is_strictly_before_its_test_block():
    dates, endpoints = fixtures()
    for fold in expanding_purged_walk_forward(dates, label_end_dates=endpoints):
        assert (endpoints.iloc[fold.train_idx] < dates.iloc[fold.test_idx[0]]).all()
        assert endpoints.iloc[fold.train_idx].notna().all()


def test_calendar_day_purge_would_retain_labels_that_reach_the_test_block():
    dates, endpoints = fixtures()
    for fold in expanding_purged_walk_forward(dates, label_end_dates=endpoints):
        start = dates.iloc[fold.test_idx[0]]
        historical_candidates = np.arange(fold.test_idx[0])
        historical_kept = historical_candidates[(dates.iloc[historical_candidates] <= start - pd.Timedelta(days=5)).to_numpy()]
        assert (endpoints.iloc[historical_kept] >= start).any()
        assert not (endpoints.iloc[fold.train_idx] >= start).any()


def test_endpoint_on_test_session_is_not_available_at_its_open():
    dates, endpoints = fixtures()
    for fold in expanding_purged_walk_forward(dates, embargo_days=0, label_end_dates=endpoints):
        equality_rows = np.flatnonzero((endpoints == dates.iloc[fold.test_idx[0]]).to_numpy())
        assert len(equality_rows) == 1
        assert equality_rows[0] not in fold.train_idx


def test_endpoints_are_computed_before_feature_rows_are_dropped():
    full_dates, _ = fixtures()
    prices = pd.DataFrame({'date': full_dates, 'close': 100 + np.sin(np.arange(140))})
    labels = compute_labels(prices, horizon_days=5)
    assert labels.loc[40, 'label_end_date'] == prices.loc[45, 'date']
    filtered = labels.iloc[[i for i in range(25, 130) if i % 3 != 0]].reset_index(drop=True)
    assert not filtered['label_end_date'].equals(filtered['date'].shift(-5))
    for fold in expanding_purged_walk_forward(filtered['date'], n_folds=3,
                                              label_end_dates=filtered['label_end_date']):
        assert (filtered['label_end_date'].iloc[fold.train_idx] < filtered['date'].iloc[fold.test_idx[0]]).all()


def test_missing_or_misaligned_endpoints_are_refused_instead_of_inferred_from_filtered_rows():
    dates, endpoints = fixtures()
    for wrong in (None, endpoints.iloc[:-1]):
        with pytest.raises(ValueError, match='aligned label_end_dates'):
            expanding_purged_walk_forward(dates, label_end_dates=wrong)


def test_unknown_endpoints_are_excluded_from_training():
    dates, endpoints = fixtures()
    endpoints.iloc[0] = pd.NaT
    for fold in expanding_purged_walk_forward(dates, label_end_dates=endpoints):
        assert 0 not in fold.train_idx


def test_backdated_or_disordered_endpoints_cannot_pass_the_purge():
    dates, endpoints = fixtures()
    wrong = endpoints.copy()
    wrong.iloc[10] = dates.iloc[10]
    with pytest.raises(ValueError, match='later than'):
        expanding_purged_walk_forward(dates, label_end_dates=wrong)
    wrong = endpoints.copy()
    wrong.iloc[0] = endpoints.iloc[15]
    with pytest.raises(ValueError, match='chronologically ordered'):
        expanding_purged_walk_forward(dates, label_end_dates=wrong)


def test_deliberate_nopurge_control_keeps_overlapping_labels():
    dates, endpoints = fixtures()
    for fold in expanding_purged_walk_forward(dates, purge=False, embargo_days=0):
        assert (endpoints.iloc[fold.train_idx] >= dates.iloc[fold.test_idx[0]]).any()


def test_duplicate_dates_and_invalid_horizon_or_embargo_fail_loudly():
    dates, endpoints = fixtures()
    duplicate = dates.copy()
    duplicate.iloc[1] = duplicate.iloc[0]
    with pytest.raises(ValueError, match='unique'):
        expanding_purged_walk_forward(duplicate, label_end_dates=endpoints)
    for kwargs in ({'horizon_days': 0}, {'horizon_days': True}, {'embargo_days': -1}):
        with pytest.raises(ValueError):
            expanding_purged_walk_forward(dates, label_end_dates=endpoints, **kwargs)
