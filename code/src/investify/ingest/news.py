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


def _required_columns(frame, columns, path):
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"News input {path} is missing required columns: {', '.join(missing)}")


def _finish_news(frame, *, source_rows, target_rows, outside_window):
    missing = frame['event_ts'].isna() | frame['headline'].isna()
    blank = frame['headline'].map(lambda value: isinstance(value, str) and not value.strip())
    invalid_count = int((missing | blank).sum())
    frame = frame[~(missing | blank)].copy()
    before_dedup = len(frame)
    frame = frame.drop_duplicates(subset=['ticker', 'headline', 'event_ts'])
    if frame.empty:
        raise ValueError('No usable news remains after timestamp/headline validation and deduplication')
    result = frame.sort_values('event_ts').reset_index(drop=True)
    result.attrs['ingestion_audit'] = {'source_rows': source_rows, 'target_rows': target_rows,
                                      'outside_window_rows': outside_window,
                                      'missing_or_blank_rows': invalid_count,
                                      'duplicate_rows': before_dedup - len(result), 'retained_rows': len(result)}
    result.attrs['snapshot_audit'] = {'consumed_rows': len(result),
                                      'first_event_utc': result['event_ts'].iloc[0].isoformat(),
                                      'last_event_utc': result['event_ts'].iloc[-1].isoformat(),
                                      'outside_window_rows': outside_window}
    return result


def load_ticker_news(path: str, ticker: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    _required_columns(df, ['Stock_symbol', 'Date', 'Article_title', 'Publisher'], path)
    source_rows = len(df)
    df = df[df["Stock_symbol"] == ticker].copy()
    if df.empty:
        raise ValueError(f"no rows found for ticker={ticker!r} in {path}")
    target_rows = len(df)

    df["event_ts"] = pd.to_datetime(df["Date"], format="%Y-%m-%d %H:%M:%S UTC", utc=True)
    df = df.rename(columns={"Article_title": "headline", "Stock_symbol": "ticker", "Publisher": "publisher"})
    return _finish_news(df[["ticker", "headline", "event_ts", "publisher"]],
                        source_rows=source_rows, target_rows=target_rows, outside_window=0)


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
    _required_columns(df, ['ticker', 'headline', 'event_ts'], path)
    source_rows = len(df)
    df = df[df["ticker"] == ticker].copy()
    if df.empty:
        raise ValueError(f"no rows found for ticker={ticker!r} in {path}")
    target_rows = len(df)
    n_dropped = 0

    for raw_timestamp in df['event_ts'].dropna():
        if pd.Timestamp(raw_timestamp).tzinfo is None:
            raise ValueError('Alpaca event_ts requires an explicit Z/UTC offset; no implicit timezone is assumed')
    df["event_ts"] = pd.to_datetime(df["event_ts"], utc=True, format="ISO8601")

    if start is not None or end is not None:
        n_before = len(df)
        # Apply only specified bounds. An omitted end must not exclude the
        # newest row by treating max(event_ts) as an exclusive endpoint.
        if start is not None:
            df = df[df['event_ts'] >= pd.Timestamp(start, tz='UTC')]
        if end is not None:
            df = df[df['event_ts'] < pd.Timestamp(end, tz='UTC') + pd.Timedelta(days=1)]
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

    return _finish_news(df[["ticker", "headline", "event_ts", "publisher"]],
                        source_rows=source_rows, target_rows=target_rows, outside_window=n_dropped)


def map_to_sessions(news_df: pd.DataFrame, calendar: NYSECalendar) -> pd.DataFrame:
    """Assign each row its trading session per the fixed 16:00 ET cutoff."""
    out = news_df.copy()
    out["session"] = out["event_ts"].apply(calendar.session_for)
    return out


def map_to_sessions_samebar(news_df: pd.DataFrame, calendar: NYSECalendar) -> pd.DataFrame:
    """Alternate bucket rule for the historical E_SAMEBAR_TEXT arm.

    The downstream join remains strictly prior-session. Assigning an after-
    close item to its publication date therefore changes its feature lag;
    it does not by itself prove the item enters a price bar before publication.
    Join-level timing must be tested before calling this arm a leakage canary.

    Implements the WRONG rule that a naive, calendar-date-aligned
    pipeline uses: every headline is mapped to the session sharing its
    own calendar date in America/New_York, with no regard for the 16:00
    ET close. An after-close item (e.g. a 16:05 ET headline) therefore
    lands on the session that JUST closed, rather than the next one --
    Contrast with map_to_sessions, which applies the recorded cutoff rule.

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
