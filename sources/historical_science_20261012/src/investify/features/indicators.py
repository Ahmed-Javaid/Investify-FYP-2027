"""Backward-only technical indicators: RSI(14), MACD histogram, distance
from SMA-200, Bollinger position, OBV slope. Every window looks only at
[t-window+1, t] -- pandas rolling()/ewm() are causal by construction as
long as center=False (the default) is never overridden, and OBV is a
cumulative sum from the start of the series. tests/test_backward_only.py
proves this directly by perturbing a single value and checking nothing
before it moves.
"""
import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd_histogram(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line


def dist_from_sma200(close: pd.Series, period: int = 200) -> pd.Series:
    sma = close.rolling(window=period, min_periods=period).mean()
    return (close - sma) / sma


def dist_from_sma200_centred(close: pd.Series, period: int = 200) -> pd.Series:
    """DELIBERATE LEAK -- D_CENTRED arm only. Never call this from the
    clean pipeline.

    Identical to dist_from_sma200 above (same period, same min_periods
    warmup handling) except the rolling mean uses center=True instead of
    the default trailing window. The value at index t is therefore
    contaminated by prices from AFTER t (roughly t+1 .. t+period//2, as
    well as t-period//2+1 .. t-1), a strictly non-causal, future-peeking
    feature. This is the project's permanent leak canary: it must leak
    loudly, and tests/test_leak_canary.py fails the build if it ever
    stops leaking. See tests/test_leak_variants.py for the direct
    perturbation evidence (perturb close at t, watch an earlier index
    change).
    """
    sma = close.rolling(window=period, min_periods=period, center=True).mean()
    return (close - sma) / sma


def bollinger_position(close: pd.Series, period: int = 20, n_std: float = 2.0) -> pd.Series:
    sma = close.rolling(window=period, min_periods=period).mean()
    std = close.rolling(window=period, min_periods=period).std()
    upper = sma + n_std * std
    lower = sma - n_std * std
    band_width = (upper - lower).replace(0, pd.NA)
    return (close - lower) / band_width


def bollinger_position_centred(close: pd.Series, period: int = 20, n_std: float = 2.0) -> pd.Series:
    """DELIBERATE LEAK -- D_CENTRED arm only. Never call this from the
    clean pipeline.

    Identical to bollinger_position above except both rolling windows use
    center=True, so the value at index t is contaminated by prices from
    roughly t+1 .. t+period//2.

    This is the leak canary's feature. The 20-day window is chosen
    deliberately over the 200-day centred SMA variant: a centred window
    only leaks information the LABEL can use if its forward half overlaps
    the label horizon. A centred 200-day mean spreads its future content
    over ~100 days ahead and is therefore near-silent at a 1- or 5-day
    horizon (measured: lift -0.021 at 5d, i.e. no detectable leak),
    whereas a centred 20-day band peeks ~10 days ahead and covers the
    5-day label directly (measured: lift +0.183 at 5d). See
    artifacts/phase2_report.md for the evidence behind this choice.
    """
    sma = close.rolling(window=period, min_periods=period, center=True).mean()
    std = close.rolling(window=period, min_periods=period, center=True).std()
    upper = sma + n_std * std
    lower = sma - n_std * std
    band_width = (upper - lower).replace(0, pd.NA)
    return (close - lower) / band_width


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    direction.iloc[0] = 0
    return (direction * volume).cumsum()


def obv_slope(close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    obv_series = obv(close, volume)
    return (obv_series - obv_series.shift(period)) / period


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """df must be sorted ascending by date and carry close/volume columns.
    Returns a new DataFrame with the 5 indicator columns, same index."""
    out = pd.DataFrame(index=df.index)
    out["rsi_14"] = rsi(df["close"])
    out["macd_hist"] = macd_histogram(df["close"])
    out["dist_sma200"] = dist_from_sma200(df["close"])
    out["bollinger_pos"] = bollinger_position(df["close"])
    out["obv_slope"] = obv_slope(df["close"], df["volume"])
    return out
