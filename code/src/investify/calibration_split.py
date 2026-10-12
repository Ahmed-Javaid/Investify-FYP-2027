"""Label availability at calibration time, independent of model libraries."""
import pandas as pd

CALIBRATION_AVAILABILITY_VERSION = 'calibration-label-end-before-evaluation-v1'


def available_calibration_rows(frame, candidate_indices, evaluation_start, *, endpoint_column):
    """Use only outcomes observable before the first evaluation session.

    Selection sees dates/endpoints, never label values or prediction scores.
    Date-only outcomes ending on the evaluation session are not known at open.
    """
    cutoff = pd.Timestamp(evaluation_start)
    if pd.isna(cutoff) or cutoff.tzinfo is not None or cutoff != cutoff.normalize():
        raise ValueError('Evaluation cutoff must be a nonmissing timezone-naive session date')
    candidates = frame.iloc[candidate_indices].copy()
    dates = pd.to_datetime(candidates['date'])
    endpoints = pd.to_datetime(candidates[endpoint_column])
    if dates.dt.tz is not None or endpoints.dt.tz is not None:
        raise ValueError('Calibration session/endpoint keys must be timezone-naive dates')
    if ((endpoints <= dates) & endpoints.notna()).any():
        raise ValueError('Calibration label endpoints must follow their feature sessions')
    eligible = endpoints.notna() & (endpoints < cutoff) & (dates < cutoff)
    selected = candidates.loc[eligible].copy()
    report = {'contract': CALIBRATION_AVAILABILITY_VERSION, 'evaluation_start': cutoff.date().isoformat(),
              'candidate_rows': len(candidates), 'available_rows': len(selected),
              'removed_rows': len(candidates) - len(selected),
              'excluded_source_indices': [int(index) for index in candidates.index[~eligible]],
              'selection_uses_label_values': False}
    if selected.empty:
        raise ValueError('No calibration labels are available before the evaluation session')
    return selected, report
