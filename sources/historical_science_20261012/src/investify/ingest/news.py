"""Adapter over the Phase 0 extracted FNSPID subset: loads the NVDA rows,
normalises columns, and maps each headline to the trading session it
belongs to under the calendar's 16:00 ET cutoff rule.

Phase 0 finding (artifacts/phase0_report.md): ~99.78% of NVDA rows in
this corpus carry no real time-of-day (defaulted to 00:00:00 UTC). Under
the fixed cutoff rule, 00:00:00 UTC converts to an America/New_York time
that is always after 16:00 the prior evening (winter: 19:00 ET previous
day; summer: 20:00 ET previous day) -- so every midnight-defaulted row
deterministically maps to the NEXT session after its calendar date. This
is a systematic, reproducible mapping, not random noise, but it should
not be mistaken for genuine same-day/next-day precision.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from investify.calendars import NY_TZ, NYSECalendar  # noqa: E402


def load_ticker_news(path: str, ticker: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["Stock_symbol"] == ticker].copy()
    if df.empty:
        raise ValueError(f"no rows found for ticker={ticker!r} in {path}")

    df["event_ts"] = pd.to_datetime(df["Date"], format="%Y-%m-%d %H:%M:%S UTC", utc=True)
    df = df.rename(columns={"Article_title": "headline", "Stock_symbol": "ticker", "Publisher": "publisher"})
    df = df[["ticker", "headline", "event_ts", "publisher"]].dropna(subset=["event_ts", "headline"])
    df = df.drop_duplicates(subset=["ticker", "headline", "event_ts"])
    return df.sort_values("event_ts").reset_index(drop=True)


def load_alpaca_ticker_news(
    path: str,
    ticker: str,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Adapter over the Alpaca/Benzinga pull (scripts/pull_alpaca_nvda_news.py).

    Returns exactly the contract `load_ticker_news` returns -- columns
    ticker/headline/event_ts/publisher, deduplicated, sorted by event_ts --
    so every downstream stage is corpus-agnostic.

    The reason this corpus exists alongside FNSPID: 100% of its rows carry a
    genuine second-resolution publication time, against FNSPID's 0.22% (26 of
    11,708). That is the difference between `E_SAMEBAR_TEXT` being measurable
    and not -- 749 of these rows (11.1%) map to a different session under the
    same-bar rule than under the correct next-session rule, against FNSPID's 1.

    `publisher` is empty for every row (the whole feed is the Benzinga wire).
    That is preserved as-is rather than filled in: nothing downstream reads it,
    and inventing a value would misrepresent the source.
    """
    df = pd.read_csv(path)
    df = df[df["ticker"] == ticker].copy()
    if df.empty:
        raise ValueError(f"no rows found for ticker={ticker!r} in {path}")

    df["event_ts"] = pd.to_datetime(df["event_ts"], utc=True, format="ISO8601")

    if start is not None or end is not None:
        n_before = len(df)
        lo = pd.Timestamp(start, tz="UTC") if start is not None else df["event_ts"].min()
        # end is an inclusive calendar date, so admit the whole of that day
        hi = (
            pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
            if end is not None
            else df["event_ts"].max()
        )
        df = df[(df["event_ts"] >= lo) & (df["event_ts"] < hi)]
        n_dropped = n_before - len(df)
        if n_dropped:
            # loud, not silent: the pull contains one 2017 row from an API
            # quirk, and any other out-of-range row is worth knowing about
            print(
                f"load_alpaca_ticker_news: dropped {n_dropped} row(s) outside "
                f"{start}..{end}",
                flush=True,
            )
        if df.empty:
            raise ValueError(f"no rows for ticker={ticker!r} within {start}..{end}")

    if "publisher" not in df.columns:
        df["publisher"] = pd.NA

    df = df[["ticker", "headline", "event_ts", "publisher"]].dropna(
        subset=["event_ts", "headline"]
    )
    df = df.drop_duplicates(subset=["ticker", "headline", "event_ts"])
    return df.sort_values("event_ts").reset_index(drop=True)


def map_to_sessions(news_df: pd.DataFrame, calendar: NYSECalendar) -> pd.DataFrame:
    """Assign each row its trading session per the fixed 16:00 ET cutoff."""
    out = news_df.copy()
    out["session"] = out["event_ts"].apply(calendar.session_for)
    return out


def map_to_sessions_samebar(news_df: pd.DataFrame, calendar: NYSECalendar) -> pd.DataFrame:
    """DELIBERATE LEAK -- E_SAMEBAR_TEXT arm only. Never call this from
    the clean pipeline.

    Implements the WRONG rule that a naive, calendar-date-aligned
    pipeline uses: every headline is mapped to the session sharing its
    own calendar date in America/New_York, with no regard for the 16:00
    ET close. An after-close item (e.g. a 16:05 ET headline) therefore
    lands on the session that JUST closed, rather than the next one --
    this is exactly the look-ahead this arm exists to model. Contrast
    with map_to_sessions above, which implements the correct rule.

    Weekend/holiday handling: a headline published on a non-trading day
    has no same-calendar-date session to land on. This variant maps it
    FORWARD to the next tradable session, matching the naive-pipeline
    behaviour being modelled (bucket by calendar date, then forward-fill
    to the next available trading day) -- not backward, which is the
    correct rule's behaviour and would erase the boundary cases (Friday
    close, weekend-published items) that make the two functions worth
    contrasting. See tests/test_leak_variants.py for the covered cases.

    Output columns, dtypes and index conventions are identical to
    map_to_sessions so the two are drop-in swappable in the assembly
    pipeline.

    Per artifacts/phase0_report.md Sec.3/7: ~99.78% of NVDA rows in the
    extracted corpus carry a midnight-only timestamp, so this variant
    differs from map_to_sessions on only a small number of genuinely
    timestamped real rows (~26 across 2018-2023) -- a small-N
    illustration, not a corpus-wide result. Do not inflate that.
    """
    out = news_df.copy()

    def _samebar_session(ts: pd.Timestamp):
        if ts.tzinfo is None:
            raise ValueError(
                "map_to_sessions_samebar requires a timezone-aware timestamp -- "
                "never assume an implicit UTC or local offset"
            )
        d = ts.tz_convert(NY_TZ).date()
        if calendar._is_valid_session(d):
            return d
        return calendar._next_valid_day_strictly_after(d)

    out["session"] = out["event_ts"].apply(_samebar_session)
    return out
