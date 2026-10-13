"""Global temperature calibration; positive scaling preserves class ordering."""
from math import exp, fsum, isfinite, log

CLASSES = ('Buy', 'Hold', 'Sell')
VERSION = 'multiclass-temperature-v1'


def _row(values):
    if (not isinstance(values, (tuple, list)) or len(values) != 3
            or any(type(x) not in (int, float) or not isfinite(x) for x in values)):
        raise ValueError('Require three finite class margins')
    return values


def softmax_temperature(margins, temperature=1.0):
    values = _row(margins)
    if type(temperature) not in (int, float) or not isfinite(temperature) or temperature <= 0:
        raise ValueError('Temperature must be finite and positive')
    top = max(values)
    weights = [exp((value - top) / temperature) for value in values]
    total = fsum(weights)
    return [value / total for value in weights]


def negative_log_likelihood(rows, labels, temperature):
    if not rows or len(rows) != len(labels) or any(label not in CLASSES for label in labels):
        raise ValueError('Calibration rows and known labels must align')
    losses = []
    for row, label in zip(rows, labels):
        values = _row(row)
        top = max(values)
        weights = [exp((value - top) / temperature) for value in values]
        losses.append(log(fsum(weights)) + (top - values[CLASSES.index(label)]) / temperature)
    return fsum(losses) / len(losses)


def fit_temperature(rows, labels, dates, label_end_dates, evaluation_start):
    """Use only calibration outcomes available strictly before evaluation."""
    from datetime import date
    if not (len(rows) == len(labels) == len(dates) == len(label_end_dates)) or not rows:
        raise ValueError('Calibration identities and outcomes must align')
    start = date.fromisoformat(evaluation_start)
    if (any(date.fromisoformat(end) >= start for end in label_end_dates)
            or any(date.fromisoformat(day) >= start for day in dates)):
        raise ValueError('Calibration outcomes must precede evaluation')
    if list(dates) != sorted(set(dates)):
        raise ValueError('Calibration dates must be unique and chronological')
    # Fixed bounds/iterations; neither search nor model selection sees eval labels.
    low, high = log(.05), log(1000.0)
    ratio = (5 ** .5 - 1) / 2
    a, b = high - ratio * (high - low), low + ratio * (high - low)
    fa = negative_log_likelihood(rows, labels, exp(a))
    fb = negative_log_likelihood(rows, labels, exp(b))
    for _ in range(120):
        if fa < fb:
            high, b, fb = b, a, fa
            a = high - ratio * (high - low)
            fa = negative_log_likelihood(rows, labels, exp(a))
        else:
            low, a, fa = a, b, fb
            b = low + ratio * (high - low)
            fb = negative_log_likelihood(rows, labels, exp(b))
    value = exp((low + high) / 2)
    return {'version': VERSION, 'temperature': value, 'fit_rows': len(rows),
            'fit_first': dates[0], 'fit_last': dates[-1], 'evaluation_start': evaluation_start,
            'objective': 'Calibration negative log likelihood; bounded log-temperature search',
            'search_bounds': [.05, 1000.0], 'iterations': 120,
            'calibration_nll_before': negative_log_likelihood(rows, labels, 1.0),
            'calibration_nll_after': negative_log_likelihood(rows, labels, value),
            'evaluation_labels_used_for_fit': False,
            'scope': 'Post-analysis calibration correction; preserves raw argmax, not proof of useful prediction.'}
