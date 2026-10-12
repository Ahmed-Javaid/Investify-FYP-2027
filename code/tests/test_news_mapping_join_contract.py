"""Mapping variants plus the actual strict-prior join on labelled session fixtures."""
from datetime import date
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.calendars import NYSECalendar
from investify.features.assembly import aggregate_session_sentiment, asof_join_features
from investify.ingest.news import map_to_sessions, map_to_sessions_samebar


def fixture_calendar():
    module = ModuleType('pandas_market_calendars')
    module.get_calendar = lambda name: SimpleNamespace(valid_days=lambda **kwargs:
        pd.to_datetime(['2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05', '2023-01-06'], utc=True))
    with patch.dict(sys.modules, {'pandas_market_calendars': module}):
        return NYSECalendar('2023-01-01', '2023-01-06')


def test_after_close_samebar_bucket_changes_lag_but_does_not_enter_a_prepublication_bar():
    calendar = fixture_calendar()
    news = pd.DataFrame({'ticker': ['NVDA'], 'headline': ['LABELLED after-close fixture'],
                         'event_ts': [pd.Timestamp('2023-01-03T21:05:00Z')], 'polarity': [.2]})
    bars = pd.DataFrame({'ticker': ['NVDA'] * 3,
                         'date': pd.to_datetime(['2023-01-03', '2023-01-04', '2023-01-05'])})
    cutoff = asof_join_features(bars, aggregate_session_sentiment(map_to_sessions(news, calendar)), 7)
    samebar = asof_join_features(bars, aggregate_session_sentiment(map_to_sessions_samebar(news, calendar)), 7)
    assert cutoff.loc[1, 'mean_polarity'] != .2  # The cutoff bucket waits another session.
    assert samebar.loc[1, 'mean_polarity'] == .2
    assert pd.isna(samebar.loc[0, 'mean_polarity'])  # No contemporaneous-bar attachment.
    for frame in (cutoff, samebar):
        for _, row in frame.dropna(subset=['latest_event_ts']).iterrows():
            fixture_open = pd.Timestamp(f"{row['date'].date()} 09:30:00", tz='America/New_York')
            assert row['latest_event_ts'] < fixture_open


def test_before_cutoff_both_bucket_rules_feed_only_the_later_fixture_session():
    calendar = fixture_calendar()
    news = pd.DataFrame({'ticker': ['NVDA'], 'event_ts': [pd.Timestamp('2023-01-03T19:00:00Z')],
                         'polarity': [.3]})
    assert map_to_sessions(news, calendar).loc[0, 'session'] == date(2023, 1, 3)
    assert map_to_sessions_samebar(news, calendar).loc[0, 'session'] == date(2023, 1, 3)
    bars = pd.DataFrame({'ticker': ['NVDA', 'NVDA'], 'date': pd.to_datetime(['2023-01-03', '2023-01-04'])})
    joined = asof_join_features(bars, aggregate_session_sentiment(map_to_sessions_samebar(news, calendar)), 7)
    assert pd.isna(joined.loc[0, 'mean_polarity'])
    assert joined.loc[1, 'mean_polarity'] == .3
