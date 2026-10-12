"""Feature/join regressions on synthetic fixtures; require the viewer NumPy/Pandas."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.features.assembly import add_backward_only_momentum, asof_join_features
from investify.features.assembly import aggregate_session_sentiment
from investify.features.causality_audit import run_audit


@pytest.mark.parametrize('seed', [42, 17])
def test_actual_causal_features_pass_and_centred_mutations_fail_the_same_invariance_criterion(seed):
    report = run_audit(seed)
    assert report['all_checks_passed']
    assert report['deliberate_mutations_detected'] == 4
    assert report['execution_kind'] == 'labelled_synthetic_fixture'
    assert not report['scientific_historical_pipeline_executed']
    assert not report['classifier_fit_executed']


def test_news_join_is_per_ticker_and_strictly_prior_at_the_lookback_boundary():
    bars = pd.DataFrame({'ticker': ['NVDA', 'MSFT'], 'date': pd.to_datetime(['2023-01-05', '2023-01-05'])})
    news = pd.DataFrame({'ticker': ['NVDA', 'MSFT', 'NVDA'],
                         'session': pd.to_datetime(['2023-01-02', '2023-01-02', '2023-01-05']),
                         'mean_polarity': [.2, -.8, .9]})
    joined = asof_join_features(bars, news, max_lookback_days=3).set_index('ticker')
    assert joined.loc['NVDA', 'mean_polarity'] == .2
    assert joined.loc['MSFT', 'mean_polarity'] == -.8
    assert asof_join_features(bars, news, max_lookback_days=2)['mean_polarity'].isna().all()


def test_sentiment_shock_does_not_cross_ticker_groups_or_change_earlier_features():
    fixtures = pd.DataFrame({'ticker': ['NVDA'] * 12 + ['MSFT'] * 12,
                             'session': list(pd.date_range('2023-01-02', periods=12)) * 2,
                             'mean_polarity': [i / 20 for i in range(12)] * 2,
                             'mention_volume': [i + 1 for i in range(12)] * 2})
    baseline = add_backward_only_momentum(fixtures)
    changed = fixtures.copy()
    changed.loc[8, ['mean_polarity', 'mention_volume']] = [-1.0, 1000]
    result = add_backward_only_momentum(changed)
    other_ticker = baseline['ticker'] == 'MSFT'
    earlier = (baseline['ticker'] == 'NVDA') & (baseline['session'] < fixtures.loc[8, 'session'])
    later = (baseline['ticker'] == 'NVDA') & ~earlier
    pd.testing.assert_frame_equal(baseline.loc[other_ticker], result.loc[other_ticker])
    pd.testing.assert_frame_equal(baseline.loc[earlier], result.loc[earlier])
    assert not baseline.loc[later].equals(result.loc[later])


def test_production_shaped_datetime_bars_join_python_date_news_sessions_with_different_inferred_units():
    bars = pd.DataFrame({'ticker': ['NVDA'], 'date': pd.DatetimeIndex(['2023-01-04'])})
    news = pd.DataFrame({'ticker': ['NVDA'], 'session': [pd.Timestamp('2023-01-03').date()],
                         'event_ts': [pd.Timestamp('2023-01-03T14:00:00Z')], 'polarity': [.2]})
    session_features = aggregate_session_sentiment(news)
    joined = asof_join_features(bars, session_features, max_lookback_days=3)
    assert joined.loc[0, 'mean_polarity'] == .2
    assert joined.loc[0, 'latest_event_ts'] == pd.Timestamp('2023-01-03T14:00:00Z')


@pytest.mark.parametrize('bad_key', [pd.NaT, pd.Timestamp('2023-01-04T12:00:00'), pd.Timestamp('2023-01-04T00:00:00Z')])
def test_asof_join_refuses_missing_intraday_or_timezone_session_keys(bad_key):
    bars = pd.DataFrame({'ticker': ['NVDA'], 'date': [bad_key]})
    news = pd.DataFrame({'ticker': ['NVDA'], 'session': [pd.Timestamp('2023-01-03')], 'mean_polarity': [.2]})
    with pytest.raises(ValueError, match='session keys'):
        asof_join_features(bars, news, max_lookback_days=3)
