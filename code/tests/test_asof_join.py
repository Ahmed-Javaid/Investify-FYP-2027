"""tests/test_asof_join.py -- brief section 5: asserts that every joined
text event_ts is strictly earlier than the OPEN of the session it is
attached to. Also proves the join is backward-only (never same-session,
never nearest-in-time) and respects the max look-back."""
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.calendars import NY_TZ, NYSECalendar  # noqa: E402
from investify.features.assembly import aggregate_session_sentiment, asof_join_features  # noqa: E402


@pytest.fixture(scope="module")
def cal():
    return NYSECalendar()


def session_open_ts(cal, d):
    schedule = cal._cal.schedule(start_date=d, end_date=d)
    return schedule.iloc[0]["market_open"].tz_convert(NY_TZ)


def test_joined_event_ts_strictly_before_session_open(cal):
    sessions = cal._sorted_valid_days[1000:1010]  # 10 consecutive-ish sessions
    price_df = pd.DataFrame({"ticker": "NVDA", "date": sessions})

    # one news row per session, published DURING that session (before its
    # own 16:00 close, so it maps to that same session under our rule)
    news_scored = pd.DataFrame(
        {
            "ticker": "NVDA",
            "session": sessions,
            "event_ts": [pd.Timestamp(f"{s} 10:00:00", tz=NY_TZ) for s in sessions],
            "polarity": [0.1] * len(sessions),
        }
    )

    session_features = aggregate_session_sentiment(news_scored)
    joined = asof_join_features(price_df, session_features, max_lookback_days=7)

    matched = joined.dropna(subset=["latest_event_ts"])
    assert len(matched) > 0, "test is vacuous if nothing matched"

    for _, row in matched.iterrows():
        open_ts = session_open_ts(cal, row["date"])
        assert row["latest_event_ts"] < open_ts, (
            f"joined event_ts {row['latest_event_ts']} is not strictly before "
            f"session {row['date']}'s open {open_ts}"
        )


def test_same_session_text_never_joined_to_its_own_bar(cal):
    """allow_exact_matches=False: a session's own news must never feed
    that same session's feature row (it isn't known until after close)."""
    sessions = cal._sorted_valid_days[1000:1003]
    price_df = pd.DataFrame({"ticker": "NVDA", "date": [sessions[2]]})

    # news ONLY on the price bar's own session -- nothing prior at all
    news_scored = pd.DataFrame(
        {
            "ticker": ["NVDA"],
            "session": [sessions[2]],
            "event_ts": [pd.Timestamp(f"{sessions[2]} 10:00:00", tz=NY_TZ)],
            "polarity": [0.5],
        }
    )
    session_features = aggregate_session_sentiment(news_scored)
    joined = asof_join_features(price_df, session_features, max_lookback_days=7)

    assert joined["mean_polarity"].isna().all(), (
        "same-session news leaked into its own bar's feature row"
    )


def test_max_lookback_respected(cal):
    """News older than max_lookback_days must not be joined."""
    sessions = cal._sorted_valid_days[1000:1020]
    target_session = sessions[15]
    old_session = sessions[0]  # far more than a handful of days back

    price_df = pd.DataFrame({"ticker": "NVDA", "date": [target_session]})
    news_scored = pd.DataFrame(
        {
            "ticker": ["NVDA"],
            "session": [old_session],
            "event_ts": [pd.Timestamp(f"{old_session} 10:00:00", tz=NY_TZ)],
            "polarity": [0.3],
        }
    )
    session_features = aggregate_session_sentiment(news_scored)
    joined = asof_join_features(price_df, session_features, max_lookback_days=3)

    assert joined["mean_polarity"].isna().all(), "news beyond max_lookback_days was joined anyway"


def test_nearest_prior_not_nearest_in_time(cal):
    """A backward as-of join must pick the most recent PRIOR session,
    never a session that comes after the price bar (which a naive
    nearest-in-time join could do)."""
    sessions = cal._sorted_valid_days[1000:1010]
    target = sessions[5]
    prior = sessions[3]
    future = sessions[7]  # closer in index but AFTER target -- must be ignored

    price_df = pd.DataFrame({"ticker": "NVDA", "date": [target]})
    news_scored = pd.DataFrame(
        {
            "ticker": ["NVDA", "NVDA"],
            "session": [prior, future],
            "event_ts": [
                pd.Timestamp(f"{prior} 10:00:00", tz=NY_TZ),
                pd.Timestamp(f"{future} 10:00:00", tz=NY_TZ),
            ],
            "polarity": [0.2, 0.9],
        }
    )
    session_features = aggregate_session_sentiment(news_scored)
    joined = asof_join_features(price_df, session_features, max_lookback_days=10)

    assert joined.iloc[0]["mean_polarity"] == pytest.approx(0.2), (
        "as-of join picked the future session instead of the nearest prior one"
    )
