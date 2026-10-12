"""Indicator edge cases and cached-score validity on labelled fixtures."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.features.indicators import rsi, compute_indicators
from investify.news_cache import doc_hash, attach_cached_scores


@pytest.mark.parametrize('close,expected', [(np.arange(250) + 100, 100.0),
                                          (500 - np.arange(250), 0.0), (np.ones(250) * 100, 50.0)])
def test_rsi_monotonic_and_flat_completed_windows_have_explicit_values_after_warmup(close, expected):
    result = rsi(pd.Series(close, dtype=float))
    assert result.iloc[:14].isna().all()
    assert result.iloc[14:].eq(expected).all()


def test_rising_price_series_has_complete_technical_rows_after_sma_warmup():
    prices = pd.DataFrame({'close': np.arange(250) + 100.0, 'volume': np.arange(250) + 1000})
    assert compute_indicators(prices).dropna().shape[0] == 51


def cache_fixture():
    return pd.DataFrame({'doc_hash': [doc_hash('LABELLED fixture')], 'positive': [.6],
                          'negative': [.1], 'neutral': [.3], 'polarity': [.5]})


def test_duplicate_cache_keys_cannot_expand_one_headline_into_multiple_scored_rows():
    with pytest.raises(ValueError, match='unique'):
        attach_cached_scores(pd.DataFrame({'headline': ['LABELLED fixture']}), pd.concat([cache_fixture()] * 2, ignore_index=True))


@pytest.mark.parametrize('column,value', [('polarity', .9), ('positive', float('nan')), ('neutral', .8)])
def test_invalid_cache_scores_are_refused_instead_of_used_in_features(column, value):
    cache = cache_fixture()
    cache.loc[0, column] = value
    with pytest.raises(ValueError, match='inconsistent'):
        attach_cached_scores(pd.DataFrame({'headline': ['LABELLED fixture']}), cache)


def test_valid_cache_join_preserves_cardinality_and_exact_headline_text():
    news = pd.DataFrame({'headline': ['LABELLED fixture', 'LABELLED fixture']})
    before = news.copy()
    scored = attach_cached_scores(news, cache_fixture())
    assert len(scored) == 2
    assert scored['headline'].tolist() == news['headline'].tolist()
    assert scored['polarity'].eq(.5).all()
    pd.testing.assert_frame_equal(news, before)


def test_unscored_headlines_do_not_become_neutral_or_disappear():
    with pytest.raises(ValueError, match='no cached FinBERT score'):
        attach_cached_scores(pd.DataFrame({'headline': ['LABELLED absent fixture']}), cache_fixture())
