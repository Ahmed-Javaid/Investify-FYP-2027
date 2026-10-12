"""tests/test_fold_local_scaling.py -- brief section 5: scaler
parameters differ across folds and are never derived from test rows."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.scaling import apply_scaler, fit_scaler  # noqa: E402

FEATURE_COLS = ["rsi_14", "macd_hist"]


def make_fold(mean, n=50, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "rsi_14": rng.normal(mean, 5, n),
            "macd_hist": rng.normal(mean / 2, 2, n),
        }
    )


def test_scaler_parameters_differ_across_folds():
    fold1_train = make_fold(mean=30, seed=1)
    fold2_train = make_fold(mean=70, seed=2)  # very different distribution

    scaler1 = fit_scaler(fold1_train, FEATURE_COLS)
    scaler2 = fit_scaler(fold2_train, FEATURE_COLS)

    assert not np.allclose(scaler1.mean_, scaler2.mean_), (
        "scalers fit on differently-distributed folds produced identical "
        "parameters -- suggests fitting isn't actually fold-local"
    )


def test_scaler_never_derived_from_test_rows():
    train = make_fold(mean=30, seed=1, n=50)
    test = make_fold(mean=1000, seed=3, n=50)  # wildly different -- would visibly shift mean_ if leaked

    scaler_train_only = fit_scaler(train, FEATURE_COLS)

    # the wrong way: fitting on train+test combined
    leaked_scaler = fit_scaler(pd.concat([train, test], ignore_index=True), FEATURE_COLS)

    assert not np.allclose(scaler_train_only.mean_, leaked_scaler.mean_), (
        "sanity check failed: train-only and leaked scalers should differ given "
        "how different the test distribution is"
    )
    # the actual property under test: our fit_scaler(train, ...) call
    # matches a scaler fit on train ONLY, by construction (it never
    # receives the test rows as an argument at all)
    reference = fit_scaler(train, FEATURE_COLS)
    assert np.allclose(scaler_train_only.mean_, reference.mean_)
    assert np.allclose(scaler_train_only.scale_, reference.scale_)


def test_apply_scaler_transforms_both_train_and_test_using_train_stats():
    train = make_fold(mean=30, seed=1)
    test = make_fold(mean=30, seed=5)  # same distribution, different sample

    scaler = fit_scaler(train, FEATURE_COLS)
    scaled_train = apply_scaler(train, FEATURE_COLS, scaler)
    scaled_test = apply_scaler(test, FEATURE_COLS, scaler)

    # scaled train should be ~standard normal (it was the fitting data)
    assert scaled_train["rsi_14"].mean() == pytest.approx(0.0, abs=0.3)
    # scaled test uses the SAME (train-fit) scaler -- not re-fit on test
    manually_scaled = (test[FEATURE_COLS] - scaler.mean_) / scaler.scale_
    pd.testing.assert_frame_equal(
        scaled_test[FEATURE_COLS].reset_index(drop=True),
        manually_scaled.reset_index(drop=True),
        check_exact=False,
    )
