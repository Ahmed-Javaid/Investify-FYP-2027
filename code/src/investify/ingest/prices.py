"""Daily provider OHLCV with yfinance's client auto_adjust disabled.

This flag alone does not establish that provider historical Close/Volume are
as-traded or free from vendor corporate-action adjustments. The snapshot is
hashed before project normalization, but this ingest does not retain actions
or an adjustment-basis declaration; those require a separate data audit.
Every pull is content-hashed, and every bar is validated
against the real NYSE calendar: brief section 5 requires zero orphan
bars (a bar whose date is not an actual trading session is a data-
quality failure, not something to silently drop).
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from investify.calendars import NY_TZ, NYSECalendar  # noqa: E402


def fetch_prices(ticker: str, start: str, end: str) -> tuple[pd.DataFrame, str]:
    """Fetch daily bars for `ticker` in [start, end). Returns (df,
    snapshot_sha256) where the hash is over the raw retrieved data,
    before any of our own normalisation."""
    raw = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False, actions=False)
    if raw is None or raw.empty:
        raise ValueError(f"yfinance returned no data for {ticker} {start}..{end}")

    # yfinance returns MultiIndex columns (field, ticker) even for a
    # single ticker when using the multi-ticker code path -- flatten.
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    raw = raw.reset_index()
    snapshot_hash = hashlib.sha256(raw.to_csv(index=False).encode("utf-8")).hexdigest()

    df = pd.DataFrame(
        {
            "ticker": ticker,
            "date": pd.to_datetime(raw["Date"]).dt.date,
            "open": raw["Open"].astype(float),
            "high": raw["High"].astype(float),
            "low": raw["Low"].astype(float),
            "close": raw["Close"].astype(float),
            "volume": raw["Volume"].astype("int64"),
        }
    )
    df["event_ts"] = df["date"].apply(lambda d: pd.Timestamp(f"{d} 16:00:00", tz=NY_TZ))
    return df, snapshot_hash


def validate_against_calendar(df: pd.DataFrame, calendar: NYSECalendar) -> None:
    """Assert zero orphan bars -- every bar's date must be a real NYSE
    trading session. Fails loudly rather than silently dropping rows."""
    orphans = sorted({d for d in df["date"] if d not in calendar._valid_days})
    if orphans:
        raise ValueError(
            f"{len(orphans)} orphan price bar(s) found (date not a valid NYSE session): "
            f"{orphans[:10]}{'...' if len(orphans) > 10 else ''}"
        )
