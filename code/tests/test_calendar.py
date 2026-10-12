"""tests/test_calendar.py -- brief section 5's required coverage:
Friday 16:05 -> Monday; a market-holiday timestamp -> next open session;
a half-day session; exactly 16:00:00; and a winter/summer pair at the
same UTC hour landing on different sides of the close.

Test dates are discovered dynamically from the real NYSE calendar rather
than hardcoded, so the tests stay correct regardless of which year they
run in and don't depend on memorized holiday dates.
"""
import sys
from datetime import time, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.calendars import CUTOFF_TIME, NY_TZ, NYSECalendar  # noqa: E402


@pytest.fixture(scope="module")
def cal():
    return NYSECalendar()


def test_friday_after_close_maps_to_monday(cal):
    # find a Friday D whose next valid session is the following Monday
    # (i.e. a normal week, no Monday holiday in between)
    for d in cal._sorted_valid_days:
        if d.weekday() != 4:  # Friday
            continue
        next_session = cal._next_valid_day_strictly_after(d)
        if next_session == d + timedelta(days=3):
            friday, monday = d, next_session
            break
    else:
        pytest.fail("could not find a Friday with an uninterrupted following Monday session")

    t = pd.Timestamp(f"{friday} 16:05:00", tz=NY_TZ)
    assert cal.session_for(t) == monday


def test_holiday_maps_to_next_open_session(cal):
    # a weekday that is NOT a valid session is a market holiday
    valid_set = cal._valid_days
    d = min(valid_set) + timedelta(days=1)
    holiday = None
    while d < max(valid_set):
        if d.weekday() < 5 and d not in valid_set:
            holiday = d
            break
        d += timedelta(days=1)
    assert holiday is not None, "could not find a weekday holiday in range"

    expected_next = cal._next_valid_day_strictly_after(holiday)
    t = pd.Timestamp(f"{holiday} 10:00:00", tz=NY_TZ)
    assert cal.session_for(t) == expected_next


def test_half_day_uses_fixed_cutoff_not_actual_close(cal):
    # find a session with an early close (a half-day, e.g. day after
    # Thanksgiving) and prove a timestamp between the ACTUAL close and
    # our FIXED 16:00 cutoff still belongs to that same session.
    schedule = cal._cal.schedule(
        start_date=min(cal._valid_days), end_date=max(cal._valid_days)
    )
    close_local = schedule["market_close"].dt.tz_convert(NY_TZ)
    half_days = schedule.index[close_local.dt.time < CUTOFF_TIME]
    assert len(half_days) > 0, "no half-days found in the calendar range"

    half_day = half_days[0].date()
    actual_close = close_local[half_days[0]].time()
    assert actual_close < time(16, 0, 0)  # sanity: genuinely an early close

    # a timestamp after the real close but before our fixed 16:00 cutoff
    t = pd.Timestamp(f"{half_day} 15:00:00", tz=NY_TZ)
    assert cal.session_for(t) == half_day, (
        "half-day session should still use the fixed 16:00 cutoff, "
        "not the actual (earlier) market close"
    )


def test_exactly_16_00_00_maps_to_next_session(cal):
    # pick any ordinary valid session with a following valid session
    d = cal._sorted_valid_days[100]  # arbitrary mid-range, well clear of edges
    expected_next = cal._next_valid_day_strictly_after(d)
    t = pd.Timestamp(f"{d} 16:00:00", tz=NY_TZ)
    assert cal.session_for(t) == expected_next, "16:00:00 is AT the cutoff, must map to next session"


def test_winter_summer_same_utc_hour_different_side_of_close(cal):
    # UTC 20:30 is 15:30 ET in winter (EST, UTC-5, before cutoff) and
    # 16:30 ET in summer (EDT, UTC-4, after cutoff) -- same UTC instant
    # shape, opposite sides of the close, because of DST.
    winter_day = next(d for d in cal._sorted_valid_days if d.month == 1 and d.year >= 2019)
    summer_day = next(d for d in cal._sorted_valid_days if d.month == 7 and d.year >= 2019)

    t_winter = pd.Timestamp(f"{winter_day} 20:30:00", tz="UTC")
    t_summer = pd.Timestamp(f"{summer_day} 20:30:00", tz="UTC")

    # sanity: confirm the UTC->NY conversion actually lands on the
    # expected sides of the cutoff before asserting session behaviour
    assert t_winter.tz_convert(NY_TZ).time() < CUTOFF_TIME
    assert t_summer.tz_convert(NY_TZ).time() >= CUTOFF_TIME

    assert cal.session_for(t_winter) == winter_day, "winter: before cutoff, same session"
    assert cal.session_for(t_summer) == cal._next_valid_day_strictly_after(summer_day), (
        "summer: at/after cutoff (DST), next session"
    )


def test_session_for_rejects_naive_timestamp(cal):
    with pytest.raises(ValueError):
        cal.session_for(pd.Timestamp("2023-01-10 10:00:00"))


def test_next_session_is_strictly_after_session_for(cal):
    d = cal._sorted_valid_days[200]
    t = pd.Timestamp(f"{d} 10:00:00", tz=NY_TZ)
    session = cal.session_for(t)
    nxt = cal.next_session(t)
    assert nxt > session
    assert nxt == cal._next_valid_day_strictly_after(session)
