"""tests/test_labels.py -- brief section 5: the label at time t must be
knowable only strictly after t + horizon. Proven by perturbation: the
label depends on close[t+horizon] (must change when that's shocked) but
not on anything beyond t+horizon (must NOT change when a later price is
shocked)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.labels import compute_labels  # noqa: E402

HORIZON = 5


def make_prices(n=100, seed=7):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame({"date": dates, "close": close})


def test_label_depends_on_price_at_t_plus_horizon():
    df = make_prices()
    t = 40
    original = compute_labels(df, horizon_days=HORIZON)

    perturbed_df = df.copy()
    perturbed_df.loc[t + HORIZON, "close"] *= 3.0  # unmissable shock to the future price
    perturbed = compute_labels(perturbed_df, horizon_days=HORIZON)

    assert original.loc[t, "label_score"] != pytest.approx(perturbed.loc[t, "label_score"]), (
        "label at t did not react to a shock at t+horizon -- suggests the "
        "forward-return calculation is not actually using the future price"
    )


def test_label_does_not_depend_on_prices_beyond_t_plus_horizon():
    df = make_prices()
    t = 40
    original = compute_labels(df, horizon_days=HORIZON)

    perturbed_df = df.copy()
    perturbed_df.loc[t + HORIZON + 10, "close"] *= 3.0  # shock well beyond the horizon
    perturbed = compute_labels(perturbed_df, horizon_days=HORIZON)

    assert original.loc[t, "label_score"] == pytest.approx(perturbed.loc[t, "label_score"]), (
        "label at t changed from a shock beyond t+horizon -- it is using more "
        "future information than the label is supposed to require"
    )


def test_label_does_not_depend_on_prices_strictly_before_the_vol_window():
    """Trailing vol uses [t-19, t]; a shock further back than that must
    not move label[t]."""
    df = make_prices(n=150)
    t = 100
    original = compute_labels(df, horizon_days=HORIZON, vol_window_days=20)

    perturbed_df = df.copy()
    perturbed_df.loc[t - 25, "close"] *= 3.0  # outside the 20-day trailing window
    perturbed = compute_labels(perturbed_df, horizon_days=HORIZON, vol_window_days=20)

    assert original.loc[t, "label_score"] == pytest.approx(perturbed.loc[t, "label_score"])


def test_thresholds_are_fixed_constants_not_fitted():
    """Same fixed thresholds must classify consistently across two
    differently-distributed series -- proves the boundary isn't derived
    from each sample's own distribution (e.g. quantiles)."""
    df_a = make_prices(n=100, seed=1)
    df_b = make_prices(n=100, seed=99)
    df_b["close"] = df_b["close"] * 20  # very different scale/volatility

    labels_a = compute_labels(df_a, horizon_days=HORIZON, thresholds=(-0.5, 0.5))
    labels_b = compute_labels(df_b, horizon_days=HORIZON, thresholds=(-0.5, 0.5))

    for labels in (labels_a, labels_b):
        valid = labels.dropna(subset=["label_score"])
        assert (valid.loc[valid["label_score"] > 0.5, "label"] == "Buy").all()
        assert (valid.loc[valid["label_score"] < -0.5, "label"] == "Sell").all()
        between = valid[(valid["label_score"] >= -0.5) & (valid["label_score"] <= 0.5)]
        assert (between["label"] == "Hold").all()
