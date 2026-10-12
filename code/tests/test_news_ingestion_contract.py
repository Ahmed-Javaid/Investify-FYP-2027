"""CSV fixtures exercise ingestion contracts without real-corpus substitutions."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.ingest.news import load_alpaca_ticker_news, load_ticker_news


def fixture_csv(tmp_path, rows):
    path = tmp_path / 'LABELLED_fixture.csv'
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_start_only_window_retains_the_newest_row(tmp_path):
    path = fixture_csv(tmp_path, {'ticker': ['NVDA'] * 3, 'headline': ['fixture A', 'fixture B', 'fixture C'],
                                 'event_ts': ['2023-01-01T12:00:00Z', '2023-01-02T12:00:00Z', '2023-01-03T12:00:00Z']})
    loaded = load_alpaca_ticker_news(str(path), 'NVDA', start='2023-01-02')
    assert loaded['headline'].tolist() == ['fixture B', 'fixture C']
    assert loaded.attrs['ingestion_audit']['outside_window_rows'] == 1


def test_end_window_includes_the_entire_declared_utc_date(tmp_path):
    path = fixture_csv(tmp_path, {'ticker': ['NVDA'] * 2, 'headline': ['fixture A', 'fixture B'],
                                 'event_ts': ['2023-01-02T23:59:59Z', '2023-01-03T00:00:00Z']})
    loaded = load_alpaca_ticker_news(str(path), 'NVDA', end='2023-01-02')
    assert loaded['headline'].tolist() == ['fixture A']


@pytest.mark.parametrize('loader', [load_alpaca_ticker_news, load_ticker_news])
def test_missing_required_columns_fail_with_schema_details(tmp_path, loader):
    path = fixture_csv(tmp_path, {'unexpected_column': ['LABELLED fixture']})
    with pytest.raises(ValueError, match='missing required columns'):
        loader(str(path), 'NVDA')


def test_deduplication_and_missing_text_are_accounted_without_changing_raw_input(tmp_path):
    path = fixture_csv(tmp_path, {'ticker': ['NVDA'] * 4 + ['MSFT'],
                                 'headline': ['fixture A', 'fixture A', None, '   ', 'fixture other ticker'],
                                 'event_ts': ['2023-01-02T12:00:00Z'] * 5})
    original = path.read_bytes()
    loaded = load_alpaca_ticker_news(str(path), 'NVDA')
    assert loaded['headline'].tolist() == ['fixture A']
    assert loaded.attrs['ingestion_audit'] == {'source_rows': 5, 'target_rows': 4, 'outside_window_rows': 0,
                                              'missing_or_blank_rows': 2, 'duplicate_rows': 1, 'retained_rows': 1}
    assert path.read_bytes() == original
    assert loaded['publisher'].isna().all()  # No invented wire/publisher identity.


def test_wholly_blank_target_headlines_refuse_an_empty_corpus(tmp_path):
    path = fixture_csv(tmp_path, {'ticker': ['NVDA'], 'headline': ['   '], 'event_ts': ['2023-01-02T12:00:00Z']})
    with pytest.raises(ValueError, match='No usable news'):
        load_alpaca_ticker_news(str(path), 'NVDA')


def test_fnspid_original_headline_and_utc_precision_are_preserved(tmp_path):
    path = fixture_csv(tmp_path, {'Stock_symbol': ['NVDA'], 'Article_title': [' fixture original &amp; text '],
                                 'Date': ['2023-01-02 12:34:56 UTC'], 'Publisher': ['fixture source']})
    loaded = load_ticker_news(str(path), 'NVDA')
    assert loaded.iloc[0]['headline'] == ' fixture original &amp; text '
    assert loaded.iloc[0]['event_ts'] == pd.Timestamp('2023-01-02T12:34:56Z')
    assert loaded.attrs['ingestion_audit']['retained_rows'] == 1


def test_invalid_timestamp_is_not_replaced_with_a_default_time(tmp_path):
    path = fixture_csv(tmp_path, {'ticker': ['NVDA'], 'headline': ['fixture A'], 'event_ts': ['not a timestamp']})
    with pytest.raises(ValueError):
        load_alpaca_ticker_news(str(path), 'NVDA')


def test_naive_alpaca_iso_timestamp_is_not_silently_assumed_to_be_utc(tmp_path):
    path = fixture_csv(tmp_path, {'ticker': ['NVDA'], 'headline': ['fixture A'], 'event_ts': ['2023-01-02T12:00:00']})
    with pytest.raises(ValueError, match='explicit Z/UTC offset'):
        load_alpaca_ticker_news(str(path), 'NVDA')
