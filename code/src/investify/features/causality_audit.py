"""Actual feature functions on labelled fixtures, never stock-performance evidence."""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from investify.features.assembly import add_backward_only_momentum, asof_join_features
from investify.features.indicators import (
    bollinger_position_centred, compute_indicators, dist_from_sma200_centred,
)
from investify.labels import compute_labels


def run_audit(seed=42):
    """Compare causal features with deliberately centred variants after a shock.

    The same earlier-row invariance criterion must pass the clean functions
    and fail the deliberate variants. No classifier, calendar or model loads.
    """
    rng = np.random.default_rng(seed)
    prices = pd.DataFrame({'date': pd.date_range('2023-01-02', periods=400, freq='B'),
                           'close': 100 + np.cumsum(rng.normal(0, 1, 400)),
                           'volume': rng.integers(1_000_000, 5_000_000, 400)})
    results = []
    for point in (150, 250):
        changed = prices.copy()
        changed.loc[point, 'close'] += 1000
        before = compute_indicators(prices)
        after = compute_indicators(changed)
        clean_equal = before.iloc[:point].equals(after.iloc[:point])
        shock_visible = not before.iloc[point:].equals(after.iloc[point:])
        results.append({'case': 'clean_technical', 'shock_index': point,
                        'earlier_rows_unchanged': clean_equal, 'shock_visible': shock_visible,
                        'check_passed': clean_equal and shock_visible})
        for name, function in (('centred_bollinger', bollinger_position_centred),
                               ('centred_sma200', dist_from_sma200_centred)):
            original = function(prices['close']).iloc[:point]
            mutated = function(changed['close']).iloc[:point]
            # Match NaNs explicitly so warm-up cannot count as a leak.
            differences = ~(original.eq(mutated) | (original.isna() & mutated.isna()))
            indexes = [int(i) for i in differences.index[differences]]
            results.append({'case': name, 'shock_index': point,
                            'earlier_rows_unchanged': not indexes,
                            'deliberate_mutation_detected': bool(indexes),
                            'changed_earlier_row_count': len(indexes),
                            'first_changed_earlier_index': indexes[0] if indexes else None,
                            'check_passed': bool(indexes)})
    sentiments = pd.DataFrame({'ticker': ['NVDA'] * 45, 'session': prices['date'].iloc[:45].tolist(),
                               'mean_polarity': rng.uniform(-1, 1, 45),
                               'mention_volume': rng.integers(1, 20, 45)})
    changed = sentiments.copy()
    changed.loc[25, ['mean_polarity', 'mention_volume']] = [1.0, 1000]
    original, mutated = add_backward_only_momentum(sentiments), add_backward_only_momentum(changed)
    earlier_equal = original.iloc[:25].equals(mutated.iloc[:25])
    visible = not original.iloc[25:].equals(mutated.iloc[25:])
    results.append({'case': 'clean_sentiment_windows', 'shock_index': 25,
                    'earlier_rows_unchanged': earlier_equal, 'shock_visible': visible,
                    'check_passed': earlier_equal and visible})

    # Session keys are fixtures, not exchange-calendar mapping evidence.
    news = pd.DataFrame({'ticker': ['NVDA', 'NVDA', 'OTHER'],
                          'session': pd.to_datetime(['2023-01-02', '2023-01-04', '2023-01-02']),
                          'mean_polarity': [.2, .9, -.8]})
    bars = pd.DataFrame({'ticker': ['NVDA', 'NVDA'],
                          'date': pd.to_datetime(['2023-01-04', '2023-01-13'])})
    joined = asof_join_features(bars, news, max_lookback_days=3)
    results.append({'case': 'strict_prior_and_stale_join',
                    'same_session_ignored': bool(joined.iloc[0]['mean_polarity'] == .2),
                    'stale_news_missing': bool(pd.isna(joined.iloc[1]['mean_polarity'])),
                    'check_passed': bool(joined.iloc[0]['mean_polarity'] == .2
                                         and pd.isna(joined.iloc[1]['mean_polarity']))})
    labels = compute_labels(prices, horizon_days=5)
    within = prices.copy()
    within.loc[105, 'close'] *= 3
    beyond = prices.copy()
    beyond.loc[115, 'close'] *= 3
    within_changed = labels.loc[100, 'label_score'] != compute_labels(within, 5).loc[100, 'label_score']
    beyond_equal = labels.loc[100, 'label_score'] == compute_labels(beyond, 5).loc[100, 'label_score']
    results.append({'case': 'forward_label_horizon', 'horizon_rows': 5,
                    'horizon_price_affects_label': bool(within_changed),
                    'beyond_horizon_does_not_affect_label': bool(beyond_equal),
                    'check_passed': bool(within_changed and beyond_equal)})
    sources = (Path(__file__), Path(__file__).with_name('indicators.py'),
               Path(__file__).with_name('assembly.py'), Path(__file__).parents[1] / 'labels.py')
    code = Path(__file__).resolve().parents[3]
    return {'schema': 'investify-fixture-feature-causality-v1', 'execution_kind': 'labelled_synthetic_fixture',
            'seed': seed, 'price_rows': len(prices), 'checks': results,
            'checks_passed': sum(row['check_passed'] for row in results),
            'all_checks_passed': all(row['check_passed'] for row in results),
            'deliberate_mutations_detected': sum(bool(row.get('deliberate_mutation_detected')) for row in results),
            'source_sha256': {str(p.relative_to(code)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'scope': 'Actual feature/label/join functions on labelled synthetic fixtures; earlier-row invariance '
                     'detects deliberately centred windows. Not historical market data, exchange-calendar mapping, '
                     'trained-model canary lift, full leakage-suite reproduction or predictive performance.',
            'scientific_historical_pipeline_executed': False, 'classifier_fit_executed': False}
