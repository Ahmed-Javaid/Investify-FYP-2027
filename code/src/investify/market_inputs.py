"""Explicit price/news snapshot validity and declared-window contracts."""
import numpy as np
import pandas as pd


def price_snapshot(frame, *, ticker, start, end):
    result = frame.copy()
    required = {'date', 'close', 'volume'}
    if not required.issubset(result.columns) or result.empty:
        raise ValueError('Price snapshot requires nonempty date/close/volume fields')
    if 'ticker' in result.columns and not result['ticker'].eq(ticker).all():
        raise ValueError('Price snapshot contains a different ticker than the declared partition')
    dates = pd.to_datetime(result['date'])
    if dates.isna().any() or dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
        raise ValueError('Price sessions must be nonmissing timezone-naive calendar dates')
    if dates.duplicated().any():
        raise ValueError('Duplicate price sessions/revisions are ambiguous; select one immutable snapshot')
    values = result[['close', 'volume']].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values[:, 0] <= 0).any() or (values[:, 1] < 0).any():
        raise ValueError('Price close/volume must be finite, positive/nonnegative respectively')
    mask = dates.between(pd.Timestamp(start), pd.Timestamp(end), inclusive='both')
    result = result.loc[mask].copy()
    result['date'] = dates.loc[mask].dt.date
    result['ticker'] = ticker
    if result.empty:
        raise ValueError('No prices within the declared date range')
    result = result.sort_values('date').reset_index(drop=True)
    result.attrs['snapshot_audit'] = {'received_rows': len(frame), 'outside_window_rows': len(frame) - len(result),
                                      'consumed_rows': len(result), 'first_session': str(result['date'].iloc[0]),
                                      'last_session': str(result['date'].iloc[-1]),
                                      'revision_policy': 'One immutable selected snapshot; ambiguous duplicate sessions refused'}
    return result


def news_snapshot(frame, *, ticker, start, end):
    result = frame.copy()
    if not {'headline', 'event_ts'}.issubset(result.columns) or result.empty:
        raise ValueError('News snapshot requires nonempty headline/event_ts fields')
    if 'ticker' in result.columns and not result['ticker'].eq(ticker).all():
        raise ValueError('News snapshot contains a different ticker than the declared partition')
    for value in result['event_ts']:
        if pd.isna(value) or pd.Timestamp(value).tzinfo is None:
            raise ValueError('Stored news timestamps must be explicit timezone-aware instants')
    times = pd.to_datetime(result['event_ts'], utc=True)
    mask = (times >= pd.Timestamp(start, tz='UTC')) & (times < pd.Timestamp(end, tz='UTC') + pd.Timedelta(days=1))
    result = result.loc[mask].copy()
    result['event_ts'] = times.loc[mask]
    result['ticker'] = ticker
    if result.empty:
        raise ValueError('No stored news within the declared date range')
    result = result.sort_values('event_ts').reset_index(drop=True)
    result.attrs['snapshot_audit'] = {'received_rows': len(frame), 'outside_window_rows': len(frame) - len(result),
                                      'consumed_rows': len(result), 'first_event_utc': result['event_ts'].iloc[0].isoformat(),
                                      'last_event_utc': result['event_ts'].iloc[-1].isoformat()}
    return result


def validate_price_sessions(frame, calendar):
    """Refuse orphan and missing sessions in the consumed immutable snapshot."""
    dates = set(pd.to_datetime(frame['date']).dt.date)
    orphan = sorted(dates - set(calendar._valid_days))
    if orphan:
        raise ValueError(f'Price snapshot contains nontrading/orphan sessions: {orphan[:10]}')
    first, last = min(dates), max(dates)
    expected = {day for day in calendar._valid_days if first <= day <= last}
    missing = sorted(expected - dates)
    if missing:
        raise ValueError(f'Price snapshot misses trading sessions; no interpolation or horizon shortening: {missing[:10]}')
    return {'orphan_sessions': 0, 'missing_sessions': 0,
            'policy': 'Complete observed exchange-session sequence between first and last consumed bar'}
