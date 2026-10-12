"""Actual continuous calendar and labelled-session NYSE contract fixtures."""
from datetime import date
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.calendars import Continuous24hCalendar, NYSECalendar


@pytest.mark.parametrize('timestamp,expected', [
    ('2023-01-03T00:00:00Z', date(2023, 1, 3)),
    ('2023-01-03T01:00:00+05:00', date(2023, 1, 2)),
    ('2023-01-02T20:00:00-05:00', date(2023, 1, 3)),
])
def test_continuous_sessions_follow_utc_dates_across_offsets(timestamp, expected):
    assert Continuous24hCalendar().session_for(pd.Timestamp(timestamp)) == expected


def test_continuous_next_session_crosses_weekends_without_an_equity_rule():
    calendar = Continuous24hCalendar()
    friday = pd.Timestamp('2023-01-06T23:59:59Z')
    assert calendar.session_for(friday) == date(2023, 1, 6)
    assert calendar.next_session(friday) == date(2023, 1, 7)


@pytest.mark.parametrize('timestamp', [pd.Timestamp('2023-01-03'), pd.NaT, None])
def test_continuous_missing_or_naive_timestamps_are_refused(timestamp):
    with pytest.raises(ValueError):
        Continuous24hCalendar().session_for(timestamp)


def fixture_nyse(empty=False):
    """Fake package supplies explicit fixture sessions, never exchange evidence."""
    module = ModuleType('pandas_market_calendars')
    sessions = [] if empty else ['2023-01-02', '2023-01-03', '2023-01-04', '2023-01-09', '2023-01-10']
    module.get_calendar = lambda name: SimpleNamespace(valid_days=lambda **kwargs: pd.to_datetime(sessions, utc=True))
    with patch.dict(sys.modules, {'pandas_market_calendars': module}):
        return NYSECalendar('2023-01-01', '2023-01-10')


@pytest.mark.parametrize('timestamp', ['2022-12-31T10:00:00-05:00', '2023-01-11T10:00:00-05:00'])
def test_nyse_fixture_refuses_out_of_coverage_events_instead_of_mapping_to_an_unrelated_first_session(timestamp):
    with pytest.raises(ValueError, match='outside'):
        fixture_nyse().session_for(pd.Timestamp(timestamp))


def test_nyse_fixture_respects_cutoff_and_declared_non_session_days():
    calendar = fixture_nyse()
    assert calendar.session_for(pd.Timestamp('2023-01-03T15:59:59-05:00')) == date(2023, 1, 3)
    assert calendar.session_for(pd.Timestamp('2023-01-03T16:00:00-05:00')) == date(2023, 1, 4)
    assert calendar.session_for(pd.Timestamp('2023-01-07T12:00:00-05:00')) == date(2023, 1, 9)


def test_nyse_fixture_cannot_find_a_future_session_after_coverage_end():
    with pytest.raises(ValueError, match='No valid trading session'):
        fixture_nyse().session_for(pd.Timestamp('2023-01-10T16:00:00-05:00'))


def test_empty_and_reversed_calendar_coverage_fail_loudly():
    with pytest.raises(ValueError, match='No valid sessions'):
        fixture_nyse(empty=True)
    with pytest.raises(ValueError, match='start must not follow'):
        NYSECalendar('2023-01-10', '2023-01-01')
