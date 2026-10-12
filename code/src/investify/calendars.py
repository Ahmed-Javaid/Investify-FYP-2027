"""Session calendars: map an arbitrary event timestamp to the trading
session (calendar date) it is allowed to influence, under a fixed 16:00
America/New_York cutoff.

Rule (brief section 5): a text record with event_ts at or after 16:00
America/New_York maps to the NEXT tradable session. Before that time, it
maps to the CURRENT session. The cutoff is fixed at 16:00 regardless of
whether that session's actual close was earlier (half-days) -- this is a
deliberate simplification, exercised explicitly by
tests/test_calendar.py's half-day case.

Real timezone database throughout (zoneinfo via pandas tz_convert), never
a fixed UTC offset -- the same UTC instant falls on different sides of the
cutoff in winter vs. summer (DST), which is exactly what
tests/test_calendar.py's winter/summer case checks.
"""
from abc import ABC, abstractmethod
from datetime import date, time

import pandas as pd

NY_TZ = "America/New_York"
CUTOFF_TIME = time(16, 0, 0)


class SessionCalendar(ABC):
    """Interface: map a timestamp to the trading session it belongs to."""

    @abstractmethod
    def session_for(self, timestamp: pd.Timestamp) -> date:
        """The trading session (calendar date) this timestamp maps to."""

    @abstractmethod
    def next_session(self, timestamp: pd.Timestamp) -> date:
        """The next tradable session strictly after session_for(timestamp)."""


class NYSECalendar(SessionCalendar):
    def __init__(self, valid_days_start: str = "2000-01-01", valid_days_end: str = "2030-12-31"):
        self._coverage_start = pd.Timestamp(valid_days_start).date()
        self._coverage_end = pd.Timestamp(valid_days_end).date()
        if self._coverage_start > self._coverage_end:
            raise ValueError("Calendar coverage start must not follow its end")
        import pandas_market_calendars as mcal
        self._cal = mcal.get_calendar("NYSE")
        # dates only, tz-naive, sorted -- cheap to hold a wide range in memory
        self._valid_days = {
            d.date() for d in self._cal.valid_days(start_date=valid_days_start, end_date=valid_days_end)
        }
        self._sorted_valid_days = sorted(self._valid_days)
        if not self._sorted_valid_days:
            raise ValueError("No valid sessions in the declared NYSE coverage window")

    def _is_valid_session(self, d: date) -> bool:
        return d in self._valid_days

    def _next_valid_day_strictly_after(self, d: date) -> date:
        import bisect

        idx = bisect.bisect_right(self._sorted_valid_days, d)
        if idx >= len(self._sorted_valid_days):
            raise ValueError(
                f"No valid trading session found after {d} -- extend valid_days_end when constructing NYSECalendar"
            )
        return self._sorted_valid_days[idx]

    def session_for(self, timestamp: pd.Timestamp) -> date:
        if timestamp is None or pd.isna(timestamp):
            raise ValueError("session_for requires a nonmissing timestamp")
        if timestamp.tzinfo is None:
            raise ValueError(
                "session_for requires a timezone-aware timestamp -- "
                "never assume an implicit UTC or local offset"
            )
        t_ny = timestamp.tz_convert(NY_TZ)
        d = t_ny.date()
        if not self._coverage_start <= d <= self._coverage_end:
            raise ValueError(f"Event date {d} is outside the declared NYSE calendar coverage window")
        if self._is_valid_session(d) and t_ny.time() < CUTOFF_TIME:
            return d
        return self._next_valid_day_strictly_after(d)

    def next_session(self, timestamp: pd.Timestamp) -> date:
        current = self.session_for(timestamp)
        return self._next_valid_day_strictly_after(current)


class Continuous24hCalendar(SessionCalendar):
    """Continuous 24-hour market calendar (brief section 2's crypto path).

    UTC rollover/timezone/refusal unit contracts are now exercised separately.
    The NVDA-only historical experiment does not run a continuous-market
    pipeline. These unit checks do not establish end-to-end crypto results.
    The optional NYSE calendar package is loaded only by NYSECalendar.

    Session = UTC calendar date; cutoff is midnight UTC per the concept
    doc's continuous-market design."""

    def session_for(self, timestamp: pd.Timestamp) -> date:
        if timestamp is None or pd.isna(timestamp):
            raise ValueError("session_for requires a nonmissing timestamp")
        if timestamp.tzinfo is None:
            raise ValueError("session_for requires a timezone-aware timestamp")
        return timestamp.tz_convert("UTC").date()

    def next_session(self, timestamp: pd.Timestamp) -> date:
        from datetime import timedelta

        return self.session_for(timestamp) + timedelta(days=1)
