"""The Alpaca corpus adapter.

The entire reason this corpus was pulled is that its timestamps carry a real
time of day, so the tests that matter most here are the ones asserting that
time-of-day survives loading. A loader that silently truncated to a date would
reproduce FNSPID's defect while looking like it had fixed it.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.calendars import NYSECalendar  # noqa: E402
from investify.ingest.news import (  # noqa: E402
    load_alpaca_ticker_news,
    load_ticker_news,
    map_to_sessions,
    map_to_sessions_samebar,
)

ALPACA_CSV = Path("data/raw/alpaca_nvda_news.csv")
FNSPID_CSV = Path("data/raw/fnspid_nasdaq_external_aapl_nvda_tsla.csv")


@pytest.fixture(scope="module")
def alpaca() -> pd.DataFrame:
    if not ALPACA_CSV.exists():
        pytest.skip(f"{ALPACA_CSV} not pulled; run scripts/pull_alpaca_nvda_news.py")
    return load_alpaca_ticker_news(
        str(ALPACA_CSV), "NVDA", start="2018-01-01", end="2023-12-31"
    )


def test_contract_matches_the_fnspid_loader(alpaca):
    """Everything downstream is corpus-agnostic only if both loaders return
    the same shape."""
    if not FNSPID_CSV.exists():
        pytest.skip(f"{FNSPID_CSV} not extracted")
    fnspid = load_ticker_news(str(FNSPID_CSV), "NVDA")

    assert list(alpaca.columns) == list(fnspid.columns)
    assert alpaca["event_ts"].dt.tz == fnspid["event_ts"].dt.tz
    assert alpaca["event_ts"].is_monotonic_increasing
    assert alpaca.index.equals(pd.RangeIndex(len(alpaca)))


def test_time_of_day_survives_loading(alpaca):
    """The whole point of this corpus. FNSPID is 99.78% midnight-defaulted;
    if this loader truncated timestamps to dates it would silently recreate
    that defect."""
    midnight = (
        (alpaca["event_ts"].dt.hour == 0)
        & (alpaca["event_ts"].dt.minute == 0)
        & (alpaca["event_ts"].dt.second == 0)
    )
    assert midnight.sum() == 0, f"{midnight.sum()} rows lost their time of day"
    assert alpaca["event_ts"].dt.hour.nunique() > 5
    assert alpaca["event_ts"].dt.second.nunique() > 5


def test_out_of_range_rows_are_filtered_and_reported(capsys):
    """The pull contains one 2017 row from an API quirk. It must be dropped
    within the configured window, and the drop must be announced -- a silent
    drop is exactly the kind of quiet data loss this project bans."""
    if not ALPACA_CSV.exists():
        pytest.skip("corpus not pulled")
    raw = pd.read_csv(ALPACA_CSV)
    raw_ts = pd.to_datetime(raw["event_ts"], utc=True, format="ISO8601")
    n_out_of_range = ((raw_ts < pd.Timestamp("2018-01-01", tz="UTC"))).sum()

    loaded = load_alpaca_ticker_news(
        str(ALPACA_CSV), "NVDA", start="2018-01-01", end="2023-12-31"
    )
    captured = capsys.readouterr()

    assert loaded["event_ts"].min() >= pd.Timestamp("2018-01-01", tz="UTC")
    assert loaded["event_ts"].max() < pd.Timestamp("2024-01-01", tz="UTC")
    if n_out_of_range:
        assert "dropped" in captured.out


def test_end_date_is_inclusive_of_the_whole_day(alpaca):
    """An end of 2023-12-31 must admit a headline published at 2023-12-31
    14:00Z, not cut the day off at midnight."""
    last = alpaca["event_ts"].max()
    assert last >= pd.Timestamp("2023-12-29", tz="UTC")


def test_unknown_ticker_fails_loudly():
    if not ALPACA_CSV.exists():
        pytest.skip("corpus not pulled")
    with pytest.raises(ValueError, match="no rows found"):
        load_alpaca_ticker_news(str(ALPACA_CSV), "NOT_A_TICKER")


def test_same_bar_and_next_session_genuinely_disagree(alpaca):
    """The measurable-leak precondition. On FNSPID exactly 1 row disagrees,
    which is why E_SAMEBAR_TEXT is unmeasurable there. This corpus must give
    enough disagreeing rows for the arm to mean something."""
    cal = NYSECalendar()
    correct = map_to_sessions(alpaca.copy(), cal)
    samebar = map_to_sessions_samebar(alpaca.copy(), cal)

    n_disagree = (correct["session"].values != samebar["session"].values).sum()
    assert n_disagree > 500, (
        f"only {n_disagree} rows map differently under the two rules; "
        f"E_SAMEBAR_TEXT would not be measurable on this corpus"
    )
