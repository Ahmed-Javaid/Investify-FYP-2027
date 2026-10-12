"""Complete scientific score/calibration trace and independent numeric replay."""
import base64
import hashlib
import json
from datetime import date
import numpy as np

CLASSES = ('Buy', 'Hold', 'Sell')
MODES = ('frozen_classifier', 'refit_transfer')
CALIBRATION_REPLAY_TOL = 1e-6  # Retained float32 sklearn outputs versus float64 np.interp.


def trace_bytes(trace):
    """One stable UTF-8 serialization for the exported trace byte identity."""
    return json.dumps(trace, sort_keys=True, indent=2, allow_nan=False).encode('utf-8')


def session_dates(values):
    if not values or any(not isinstance(value, str) for value in values):
        raise ValueError('Trace dates must be nonempty canonical ordered ISO sessions')
    try:
        parsed = [date.fromisoformat(value) for value in values]
    except ValueError as error:
        raise ValueError('Trace dates must be canonical ordered ISO sessions') from error
    if any(day.isoformat() != value for day, value in zip(parsed, values)) or any(
            first >= second for first, second in zip(parsed, parsed[1:])):
        raise ValueError('Trace dates must be canonical ordered ISO sessions')
    return parsed


def validate_scaler(snapshot):
    features = snapshot['features']
    if not features or len(set(features)) != len(features) or any(not isinstance(name, str) or not name for name in features):
        raise ValueError('Scaler features must retain unique nonempty ordered names')
    for name in ('mean', 'scale', 'variance'):
        values = snapshot[name]
        if len(values) != len(features) or any(value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value)) for value in values):
            raise ValueError('Scaler statistics must align to features and retain finite numbers or missing nulls')
    for mean, scale, variance in zip(snapshot['mean'], snapshot['scale'], snapshot['variance']):
        if any(value is None for value in (mean, scale, variance)):
            if not all(value is None for value in (mean, scale, variance)):
                raise ValueError('Missing scaler statistics must be retained consistently')
        elif scale <= 0 or variance < 0:
            raise ValueError('Scaler scale/variance must be positive/nonnegative')


def finite_matrix(values, rows):
    matrix = np.asarray(values, dtype=float)
    if rows <= 0 or matrix.shape != (rows, 3) or not np.isfinite(matrix).all():
        raise ValueError('Retain exactly three finite class scores aligned to every row')
    return matrix


def probabilities(values, rows):
    matrix = finite_matrix(values, rows)
    if (matrix < 0).any() or (matrix > 1).any() or not np.allclose(matrix.sum(axis=1), 1, atol=1e-6, rtol=0):
        raise ValueError('Probability trace must be bounded and normalized')
    return matrix


def brier(labels, probability):
    if any(label not in CLASSES for label in labels) or len(labels) != len(probability):
        raise ValueError('Known truth labels and probabilities must align')
    onehot = np.array([[float(label == name) for name in CLASSES] for label in labels])
    return float(np.square(onehot - probability).sum(axis=1).mean())


def replay_calibration(raw, knots):
    if len(knots) != len(CLASSES):
        raise ValueError('Retain exactly three ordered isotonic class mappings')
    outputs = []
    for index, knot in enumerate(knots):
        x, y = np.asarray(knot['x'], dtype=float), np.asarray(knot['y'], dtype=float)
        if x.ndim != 1 or y.ndim != 1 or knot['class'] != CLASSES[index] or len(x) != len(y) or not len(x) or not np.isfinite(x).all() or not np.isfinite(y).all() or (np.diff(x) <= 0).any() or (y < 0).any() or (y > 1).any() or (np.diff(y) < -1e-12).any() or knot.get('out_of_bounds') != 'clip':
            raise ValueError('Isotonic knots must retain exact ordered class/threshold identity')
        outputs.append(np.interp(raw[:, index], x, y))
    values = np.column_stack(outputs)
    totals = values.sum(axis=1)
    if (totals <= 0).any():
        raise ValueError('Isotonic trace collapses to all-zero probability; no uniform replacement')
    return values / totals[:, None]


def model_snapshot(model):
    raw = bytes(model.get_booster().save_raw(raw_format='json'))
    return {'format': 'xgboost_booster_json', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'base64': base64.b64encode(raw).decode('ascii')}


def scaler_snapshot(scaler, columns):
    def numbers(values):
        if np.isinf(np.asarray(values, dtype=float)).any():
            raise ValueError('Infinite scaler statistics cannot be disguised as missing values')
        return [float(value) if np.isfinite(value) else None for value in np.asarray(values, dtype=float)]
    return {'features': list(columns), 'mean': numbers(scaler.mean_), 'scale': numbers(scaler.scale_),
            'variance': numbers(scaler.var_), 'missing_statistics_preserved_as_null': True}


def capture_trace(*, calibration_frame, evaluation_frame, label_column, raw_calibration, calibration_margins,
                  raw_evaluation, evaluation_margins, calibrated_evaluation, calibrators, calibration_model,
                  evaluation_model, calibration_scaler, evaluation_scaler, columns, mode, endpoint_column,
                  provenance, purpose='research'):
    def block(frame, raw, margins):
        return {'dates': [str(value)[:10] for value in frame['date']], 'truth': frame[label_column].astype(str).tolist(),
                'label_end_dates': [str(value)[:10] for value in frame[endpoint_column]],
                'raw_probabilities': probabilities(raw, len(frame)).tolist(),
                'raw_margins_all_classes': finite_matrix(margins, len(frame)).tolist()}
    knots = [{'class': label, 'x': calibrators[index].X_thresholds_.tolist(),
              'y': calibrators[index].y_thresholds_.tolist(), 'out_of_bounds': calibrators[index].out_of_bounds}
             for index, label in enumerate(CLASSES)]
    trace = {'schema': 'investify-scientific-trace-v2', 'purpose': purpose, 'classes': list(CLASSES),
             'provenance': dict(provenance),
             'calibration_mode': mode, 'calibration': block(calibration_frame, raw_calibration, calibration_margins),
             'evaluation': block(evaluation_frame, raw_evaluation, evaluation_margins), 'isotonic_knots': knots,
             'calibrated_evaluation': probabilities(calibrated_evaluation, len(evaluation_frame)).tolist(),
             'calibration_scaler': scaler_snapshot(calibration_scaler, columns),
             'evaluation_scaler': scaler_snapshot(evaluation_scaler, columns),
             'calibration_model': model_snapshot(calibration_model), 'evaluation_model': model_snapshot(evaluation_model),
             'same_classifier_object': calibration_model is evaluation_model,
             'same_scaler_object': calibration_scaler is evaluation_scaler,
             'scope': 'Actual retained model bytes/scalers/full class scores/truth/knots when run on genuine inputs; '
                      'trace consistency is not execution attestation or predictive usefulness'}
    trace['replay'] = replay_trace(trace)
    return trace


def replay_trace(trace):
    if trace.get('schema') != 'investify-scientific-trace-v2' or trace.get('calibration_mode') not in MODES:
        raise ValueError('Use the declared trace schema and calibration mode')
    if trace['classes'] != list(CLASSES):
        raise ValueError('Trace class order changed')
    calibration, evaluation = trace['calibration'], trace['evaluation']
    for block in (calibration, evaluation):
        dates = session_dates(block['dates'])
        endpoints = session_dates(block['label_end_dates'])
        if len(block['truth']) != len(block['dates']) or len(set(block['dates'])) != len(block['dates']):
            raise ValueError('Trace rows/truth/dates are misaligned or duplicated')
        if len(endpoints) != len(dates) or any(end <= start for start, end in zip(dates, endpoints)):
            raise ValueError('Trace label endpoints must align and follow their feature sessions')
        if any(label not in CLASSES for label in block['truth']):
            raise ValueError('Trace truth labels must belong to the declared class order')
        raw = probabilities(block['raw_probabilities'], len(dates))
        margins = finite_matrix(block['raw_margins_all_classes'], len(dates))
        exponentials = np.exp(margins - margins.max(axis=1, keepdims=True))
        if not np.allclose(raw, exponentials / exponentials.sum(axis=1, keepdims=True), atol=1e-6, rtol=0):
            raise ValueError('Raw probabilities differ from multiclass-margin softmax replay')
    if calibration['dates'][-1] >= evaluation['dates'][0] or max(calibration['label_end_dates']) >= evaluation['dates'][0]:
        raise ValueError('Calibration outcomes must be available strictly before evaluation starts')
    binding = trace['provenance']
    digest = binding.get('scientific_run_identity_sha256')
    if not isinstance(digest, str) or len(digest) != 64 or any(character not in '0123456789abcdef' for character in digest):
        raise ValueError('Trace must retain a canonical scientific run identity')
    if any(not isinstance(binding.get(name), str) or not binding[name] for name in ('model_version', 'corpus', 'ticker')) or type(binding.get('horizon_days')) is not int or binding['horizon_days'] <= 0:
        raise ValueError('Trace must retain model/corpus/ticker/horizon identity')
    for name in ('calibration_scaler', 'evaluation_scaler'):
        validate_scaler(trace[name])
    if trace['calibration_scaler']['features'] != trace['evaluation_scaler']['features']:
        raise ValueError('Calibration and evaluation must retain the same ordered feature set')
    raw = probabilities(evaluation['raw_probabilities'], len(evaluation['dates']))
    expected = replay_calibration(raw, trace['isotonic_knots'])
    saved = probabilities(trace['calibrated_evaluation'], len(evaluation['dates']))
    if not np.allclose(expected, saved, atol=CALIBRATION_REPLAY_TOL, rtol=0):
        raise ValueError('Stored calibrated probabilities differ from retained-knot replay tolerance')
    for name in ('calibration_model', 'evaluation_model'):
        payload = base64.b64decode(trace[name]['base64'], validate=True)
        if trace[name].get('format') != 'xgboost_booster_json' or not payload or type(trace[name]['bytes']) is not int or len(payload) != trace[name]['bytes'] or hashlib.sha256(payload).hexdigest() != trace[name]['sha256']:
            raise ValueError('Retained model bytes differ from their hash/size')
    if trace['calibration_mode'] == 'frozen_classifier' and not (trace['same_classifier_object'] is True and trace['same_scaler_object'] is True
                                                               and trace['calibration_model']['sha256'] == trace['evaluation_model']['sha256']
                                                               and trace['calibration_scaler'] == trace['evaluation_scaler']):
        raise ValueError('Frozen mode must retain the same model/scaler')
    if trace['calibration_mode'] == 'refit_transfer' and (trace['same_classifier_object'] is not False or trace['same_scaler_object'] is not False):
        raise ValueError('Refit mode must record distinct classifier/scaler objects')
    report = {'brier_before': brier(evaluation['truth'], raw), 'brier_after': brier(evaluation['truth'], saved),
            'calibration_class_counts': {name: calibration['truth'].count(name) for name in CLASSES},
            'evaluation_class_counts': {name: evaluation['truth'].count(name) for name in CLASSES},
            'model_bytes_integrity_passed': True, 'score_probability_consistency_passed': True,
            'calibration_numeric_replay_passed': True, 'label_availability_replay_passed': True,
            'calibration_absolute_tolerance': CALIBRATION_REPLAY_TOL,
            'model_inference_replayed': False, 'purpose': trace['purpose']}
    if 'replay' in trace and trace['replay'] != report:
        raise ValueError('Saved trace replay summary differs from recomputed evidence')
    return report


def validate_result_trace(result, serialized_trace):
    """Cross-check one result against the exact accompanying trace bytes."""
    trace = json.loads(serialized_trace.decode('utf-8'))
    provenance = result['provenance']
    if hashlib.sha256(serialized_trace).hexdigest() != provenance['scientific_trace_sha256']:
        raise ValueError('Result and trace byte identities differ')
    report = replay_trace(trace)
    for name in ('model_version', 'corpus', 'ticker', 'horizon_days'):
        if provenance[name] != trace['provenance'][name]:
            raise ValueError('Result and trace model/data identity differ')
    digest = trace['provenance']['scientific_run_identity_sha256']
    identity = provenance['scientific_identity']
    recomputed_identity = hashlib.sha256(json.dumps({name: value for name, value in identity.items() if name != 'identity_sha256'}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if provenance['data_hashes']['scientific_run_identity_sha256'] != digest or identity['identity_sha256'] != digest or recomputed_identity != digest or provenance['calibration_mode'] != trace['calibration_mode']:
        raise ValueError('Result and trace scientific run identities differ')
    for name in ('brier_before', 'brier_after'):
        if not np.isclose(provenance['metrics'][name], report[name], atol=1e-12, rtol=0):
            raise ValueError('Result Brier differs from trace replay')
    if provenance['n_calibration_rows'] != len(trace['calibration']['dates']) or provenance['n_eval_rows'] != len(trace['evaluation']['dates']):
        raise ValueError('Result and trace row counts differ')
    records = result['decision_records']
    if [record['session_date'] for record in records] != trace['evaluation']['dates']:
        raise ValueError('Result and trace evaluation dates/order differ')
    for index, record in enumerate(records):
        expected = trace['calibrated_evaluation'][index]
        chosen = int(np.argmax(expected))
        if record['decision'] != CLASSES[chosen] or not np.allclose([record['probabilities'][label] for label in CLASSES], expected, atol=1e-12, rtol=0) or not np.isclose(record['raw_model_output'], trace['evaluation']['raw_margins_all_classes'][index][chosen], atol=1e-12, rtol=0):
            raise ValueError('Result decision/probability/margin differs from trace')
        if record['model_version'] != provenance['model_version'] or record['data_hashes'] != provenance['data_hashes'] or record['ticker'] != provenance['ticker'] or record['horizon_days'] != provenance['horizon_days']:
            raise ValueError('Decision record belongs to a different scientific run')
    return report
