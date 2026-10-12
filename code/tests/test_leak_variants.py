"""tests/test_leak_variants.py -- Phase 2 feature-level leak variants for
the D_CENTRED and E_SAMEBAR_TEXT arms (brief section 6).

D_CENTRED: dist_from_sma200_centred() in features/indicators.py recomputes
the SMA-200 distance indicator with a centred rather than trailing window.
This is the permanent leak canary -- it must leak loudly and stay leaking.

E_SAMEBAR_TEXT: map_to_sessions_samebar() in ingest/news.py maps a headline
to the session sharing its own calendar date (America/New_York), rather
than applying the 16:00 ET cutoff -- the mistake published pipelines make
when they align by calendar date instead of publication time.

All price series and headline timestamps in this file are SYNTHETIC
FIXTURES for unit testing only, per CLAUDE.md's rule that synthetic text
never substitutes for real dated headlines in the real experiment.
"""
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.calendars import NY_TZ, NYSECalendar  # noqa: E402
from investify.features.indicators import (  # noqa: E402
    dist_from_sma200,
    dist_from_sma200_centred,
)
from investify.ingest.news import map_to_sessions, map_to_sessions_samebar  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------


def make_price_series(n=400, seed=42):
    """SYNTHETIC FIXTURE -- unit test only, never used in the real run."""
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.Series(close, name="close")


def make_news_df(timestamps):
    """SYNTHETIC FIXTURE -- minimal news_df with the columns map_to_sessions
    and map_to_sessions_samebar operate on."""
    return pd.DataFrame(
        {
            "ticker": ["NVDA"] * len(timestamps),
            "headline": [f"synthetic fixture headline {i}" for i in range(len(timestamps))],
            "event_ts": list(timestamps),
            "publisher": ["fixture_publisher"] * len(timestamps),
        }
    )


@pytest.fixture(scope="module")
def cal():
    return NYSECalendar()


# ---------------------------------------------------------------------------
# 1. D_CENTRED actually leaks (inverse of test_backward_only.py)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("perturb_index", [150, 200, 250])
def test_centred_variant_leaks_into_earlier_rows(perturb_index):
    close = make_price_series()
    original = dist_from_sma200_centred(close)

    perturbed_close = close.copy()
    perturbed_close.loc[perturb_index] += 1000.0  # large, unmissable shock

    perturbed = dist_from_sma200_centred(perturbed_close)

    before = original.iloc[:perturb_index]
    before_perturbed = perturbed.iloc[:perturb_index]

    both_nan = before.isna() & before_perturbed.isna()
    differs = ~both_nan & (before != before_perturbed)
    assert differs.any(), (
        f"perturbing close[{perturb_index}] changed nothing at any index < {perturb_index} -- "
        "the centred variant is not leaking, which defeats its purpose as the leak canary"
    )


def test_trailing_variant_does_not_leak_for_the_same_perturbation():
    """Sanity contrast: the existing trailing indicator must NOT show the
    same backward leak the centred one does, for the identical input."""
    close = make_price_series()
    perturb_index = 200
    original = dist_from_sma200(close)

    perturbed_close = close.copy()
    perturbed_close.loc[perturb_index] += 1000.0
    perturbed = dist_from_sma200(perturbed_close)

    before = original.iloc[:perturb_index]
    before_perturbed = perturbed.iloc[:perturb_index]
    pd.testing.assert_series_equal(before, before_perturbed)


# ---------------------------------------------------------------------------
# 2. centred vs trailing: differ on real-shaped input, agree in the
#    degenerate constant-series case
# ---------------------------------------------------------------------------


def test_centred_and_trailing_differ_on_real_shaped_series():
    close = make_price_series()
    trailing = dist_from_sma200(close)
    centred = dist_from_sma200_centred(close)
    assert not trailing.equals(centred), "centred and trailing variants must diverge on real-shaped input"


def test_centred_and_trailing_agree_on_constant_series():
    """Degenerate case: close is flat, so close == sma everywhere the
    window is fully populated, regardless of whether the window is
    centred or trailing -- both variants must report ~0 wherever defined."""
    close = pd.Series([100.0] * 300)
    trailing = dist_from_sma200(close)
    centred = dist_from_sma200_centred(close)

    trailing_valid = trailing.dropna()
    centred_valid = centred.dropna()
    assert len(trailing_valid) > 0 and len(centred_valid) > 0, "test is vacuous if nothing is defined"
    assert (trailing_valid.abs() < 1e-9).all()
    assert (centred_valid.abs() < 1e-9).all()


# ---------------------------------------------------------------------------
# 3. same-bar mapping is wrong in the specific, intended way
# ---------------------------------------------------------------------------


def test_friday_after_close_samebar_stays_friday_correct_rule_moves_to_monday(cal):
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
    news_df = make_news_df([t])

    samebar = map_to_sessions_samebar(news_df, cal)
    correct = map_to_sessions(news_df, cal)

    assert samebar["session"].iloc[0] == friday, "same-bar variant must join the after-close item to the closing bar"
    assert correct["session"].iloc[0] == monday, "correct rule must defer the after-close item to Monday"


def test_exactly_16_00_00_samebar_ignores_the_cutoff(cal):
    d = cal._sorted_valid_days[100]
    t = pd.Timestamp(f"{d} 16:00:00", tz=NY_TZ)
    news_df = make_news_df([t])

    samebar = map_to_sessions_samebar(news_df, cal)
    correct = map_to_sessions(news_df, cal)

    assert samebar["session"].iloc[0] == d, "same-bar variant ignores time-of-day entirely, so 16:00:00 stays same-day"
    assert correct["session"].iloc[0] == cal._next_valid_day_strictly_after(d), (
        "16:00:00 is AT the cutoff -- correct rule must defer to the next session"
    )


def test_winter_summer_dst_samebar_ignores_cutoff_entirely(cal):
    # UTC 20:30 is 15:30 ET in winter (before cutoff) and 16:30 ET in
    # summer (at/after cutoff) -- same UTC instant shape, opposite sides
    # of the close under the correct rule, because of DST. The same-bar
    # variant does not look at time-of-day at all, so both map to their
    # own calendar date regardless of season.
    winter_day = next(d for d in cal._sorted_valid_days if d.month == 1 and d.year >= 2019)
    summer_day = next(d for d in cal._sorted_valid_days if d.month == 7 and d.year >= 2019)

    t_winter = pd.Timestamp(f"{winter_day} 20:30:00", tz="UTC")
    t_summer = pd.Timestamp(f"{summer_day} 20:30:00", tz="UTC")
    news_df = make_news_df([t_winter, t_summer])

    samebar = map_to_sessions_samebar(news_df, cal)
    correct = map_to_sessions(news_df, cal)

    assert samebar["session"].iloc[0] == winter_day
    assert samebar["session"].iloc[1] == summer_day, "same-bar variant is season-blind: both winter and summer stay same-day"

    assert correct["session"].iloc[0] == winter_day, "winter: before cutoff, correct rule keeps same session"
    assert correct["session"].iloc[1] == cal._next_valid_day_strictly_after(summer_day), (
        "summer: DST pushes 20:30 UTC at/after the 16:00 ET cutoff, correct rule defers to next session"
    )


# ---------------------------------------------------------------------------
# 4. weekend / holiday published item -- documented choice, asserted
#    explicitly: maps FORWARD to the next tradable session (matching the
#    naive calendar-date-alignment behaviour this variant models).
# ---------------------------------------------------------------------------


def test_weekend_published_item_maps_forward_to_next_session(cal):
    d = cal._sorted_valid_days[100]
    saturday = d
    while saturday.weekday() != 5:
        saturday += timedelta(days=1)
    expected_next = cal._next_valid_day_strictly_after(saturday)

    t = pd.Timestamp(f"{saturday} 10:00:00", tz=NY_TZ)
    news_df = make_news_df([t])
    samebar = map_to_sessions_samebar(news_df, cal)

    assert samebar["session"].iloc[0] == expected_next


def test_holiday_published_item_maps_forward_to_next_session(cal):
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
    news_df = make_news_df([t])
    samebar = map_to_sessions_samebar(news_df, cal)

    assert samebar["session"].iloc[0] == expected_next


# ---------------------------------------------------------------------------
# 5. output schema parity
# ---------------------------------------------------------------------------


def test_output_schema_matches_map_to_sessions(cal):
    d = cal._sorted_valid_days[500]
    t = pd.Timestamp(f"{d} 10:00:00", tz=NY_TZ)
    news_df = make_news_df([t])

    correct = map_to_sessions(news_df, cal)
    samebar = map_to_sessions_samebar(news_df, cal)

    assert list(correct.columns) == list(samebar.columns)
    assert (correct.dtypes == samebar.dtypes).all(), "dtypes must match so the two are drop-in swappable"
    assert type(correct["session"].iloc[0]) is type(samebar["session"].iloc[0])
