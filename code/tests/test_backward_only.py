"""tests/test_backward_only.py -- brief section 5: perturb a value at
index t and assert that no feature at any index < t changes. This is
the direct proof that every rolling/EWM window in indicators.py is
strictly causal."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.features.indicators import compute_indicators  # noqa: E402


def make_price_series(n=300, seed=42):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    volume = rng.integers(1_000_000, 5_000_000, n)
    return pd.DataFrame({"close": close, "volume": volume})


@pytest.mark.parametrize("perturb_index", [50, 150, 250])
def test_perturbation_never_changes_earlier_rows(perturb_index):
    df = make_price_series()
    original = compute_indicators(df)

    perturbed_df = df.copy()
    perturbed_df.loc[perturb_index, "close"] += 1000.0  # large, unmissable shock
    perturbed = compute_indicators(perturbed_df)

    before = original.iloc[:perturb_index]
    before_perturbed = perturbed.iloc[:perturb_index]
    pd.testing.assert_frame_equal(before, before_perturbed)


def test_perturbation_does_change_the_row_itself_or_later(perturb_index=150):
    df = make_price_series()
    original = compute_indicators(df)

    perturbed_df = df.copy()
    perturbed_df.loc[perturb_index, "close"] += 1000.0
    perturbed = compute_indicators(perturbed_df)

    after = original.iloc[perturb_index:]
    after_perturbed = perturbed.iloc[perturb_index:]
    # sanity: the perturbation must actually be visible somewhere at/after
    # t, otherwise this test would pass vacuously
    assert not after.equals(after_perturbed), "perturbation had no visible effect anywhere -- test is vacuous"


def test_all_five_indicators_present():
    df = make_price_series()
    out = compute_indicators(df)
    for col in ["rsi_14", "macd_hist", "dist_sma200", "bollinger_pos", "obv_slope"]:
        assert col in out.columns
