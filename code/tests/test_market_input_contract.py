"""Price/news snapshot range and ambiguity fixtures, no original-data claim."""
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.market_inputs import price_snapshot, news_snapshot, validate_price_sessions


def prices():
    return pd.DataFrame({'ticker': ['NVDA'] * 3, 'date': ['2017-12-29', '2023-01-03', '2025-01-02'],
                          'close': [10., 20., 30.], 'volume': [100, 200, 300]})


def test_price_window_excludes_out_of_range_bars_with_explicit_consumption_audit():
    result = price_snapshot(prices(), ticker='NVDA', start='2018-01-01', end='2023-12-31')
    assert len(result) == 1
    assert result['close'].tolist() == [20.]
    assert result.attrs['snapshot_audit']['outside_window_rows'] == 2
    assert result.attrs['snapshot_audit']['first_session'] == '2023-01-03'


def test_changed_close_or_volume_revisions_do_not_create_two_bars_for_one_session():
    frame = prices().iloc[[1, 1]].copy()
    frame.iloc[1, frame.columns.get_loc('volume')] = 400
    with pytest.raises(ValueError, match='revisions are ambiguous'):
        price_snapshot(frame, ticker='NVDA', start='2018-01-01', end='2023-12-31')


@pytest.mark.parametrize('column,value', [('close', float('nan')), ('close', 0), ('volume', -1)])
def test_invalid_prices_or_volume_are_refused(column, value):
    frame = prices()
    frame.loc[1, column] = value
    with pytest.raises(ValueError, match='finite'):
        price_snapshot(frame, ticker='NVDA', start='2018-01-01', end='2023-12-31')


def test_ticker_partition_does_not_relabel_different_asset_rows():
    frame = prices()
    frame.loc[1, 'ticker'] = 'MSFT'
    with pytest.raises(ValueError, match='different ticker'):
        price_snapshot(frame, ticker='NVDA', start='2018-01-01', end='2023-12-31')


def test_stored_news_obeys_the_same_declared_window_as_the_csv_branch():
    frame = pd.DataFrame({'ticker': ['NVDA'] * 3, 'headline': ['LABELLED A', 'LABELLED B', 'LABELLED C'],
                           'event_ts': pd.to_datetime(['2017-12-29T12:00:00Z', '2023-01-03T12:00:00Z', '2025-01-02T12:00:00Z'])})
    result = news_snapshot(frame, ticker='NVDA', start='2018-01-01', end='2023-12-31')
    assert result['headline'].tolist() == ['LABELLED B']
    assert result.attrs['snapshot_audit']['outside_window_rows'] == 2


def test_stored_naive_news_time_is_not_assumed_to_be_utc():
    frame = pd.DataFrame({'headline': ['LABELLED A'], 'event_ts': ['2023-01-03T12:00:00']})
    with pytest.raises(ValueError, match='timezone-aware'):
        news_snapshot(frame, ticker='NVDA', start='2018-01-01', end='2023-12-31')


def test_calendar_fixture_rejects_saturday_price_bars_and_missing_sessions():
    from types import SimpleNamespace
    from datetime import date
    calendar = SimpleNamespace(_valid_days={date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4)})
    with pytest.raises(ValueError, match='orphan'):
        validate_price_sessions(pd.DataFrame({'date': ['2023-01-02', '2023-01-07']}), calendar)
    with pytest.raises(ValueError, match='misses trading sessions'):
        validate_price_sessions(pd.DataFrame({'date': ['2023-01-02', '2023-01-04']}), calendar)
    result = validate_price_sessions(pd.DataFrame({'date': ['2023-01-02', '2023-01-03', '2023-01-04']}), calendar)
    assert result['missing_sessions'] == result['orphan_sessions'] == 0
