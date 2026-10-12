"""Volatility-adjusted forward-return labels, mapped to 3 classes at
fixed thresholds. Thresholds are constants (brief section 5: not fitted
to the data), passed in explicitly rather than derived from any
distribution.

label[t] = f(close[t-19..t] for trailing vol, close[t] and close[t+horizon]
for the forward return) -- it cannot be computed with only data known as
of time t, which is the whole point: it is only knowable strictly after
t + horizon. tests/test_label_leakage.py proves this by perturbation.
"""
import numpy as np
import pandas as pd


def compute_labels(
    price_df: pd.DataFrame,
    horizon_days: int,
    vol_window_days: int = 20,
    thresholds: tuple[float, float] = (-0.5, 0.5),
) -> pd.DataFrame:
    df = price_df.sort_values("date").reset_index(drop=True).copy()

    forward_return = df["close"].shift(-horizon_days) / df["close"] - 1
    daily_return = df["close"].pct_change()
    trailing_vol = daily_return.rolling(window=vol_window_days, min_periods=vol_window_days).std()

    score = forward_return / trailing_vol.replace(0, np.nan)

    lo, hi = thresholds
    label = pd.cut(score, bins=[-np.inf, lo, hi, np.inf], labels=["Sell", "Hold", "Buy"])

    df["forward_return"] = forward_return
    # Preserve the actual endpoint before any downstream feature/label mask.
    # Shifting dates after rows have been dropped would change its meaning.
    df["label_end_date"] = df["date"].shift(-horizon_days)
    df["trailing_vol"] = trailing_vol
    df["label_score"] = score
    df["label"] = label
    return df
