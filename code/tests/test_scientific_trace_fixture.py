"""Numeric/model-byte trace fixtures are not trained-model results."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.scientific_trace import capture_trace, replay_trace, replay_calibration, trace_bytes, validate_result_trace


class ModelFixture:
    def get_booster(self):
        return self
    def save_raw(self, raw_format):
        assert raw_format == 'json'
        return b'{"LABELLED":"unit fixture, not a trained XGBoost model"}'


def fixture_identity():
    identity = {'execution_kind': 'LABELLED unit fixture, not a scientific run'}
    identity['identity_sha256'] = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return identity


def trace_fixture():
    calibration = pd.DataFrame({'date': pd.to_datetime(['2023-01-02', '2023-01-03']), 'label': ['Buy', 'Hold'],
                                 'label_end': pd.to_datetime(['2023-01-04', '2023-01-05'])})
    evaluation = pd.DataFrame({'date': pd.to_datetime(['2023-01-09', '2023-01-10']), 'label': ['Sell', 'Buy'],
                                'label_end': pd.to_datetime(['2023-01-16', '2023-01-17'])})
    raw = np.array([[.2, .3, .5], [.6, .2, .2]])
    regressors = {index: SimpleNamespace(X_thresholds_=np.array([0., 1.]), Y_thresholds_=np.array([0., 1.]),
                                         y_thresholds_=np.array([0., 1.]), out_of_bounds='clip') for index in range(3)}
    model = ModelFixture()
    scaler = SimpleNamespace(mean_=np.array([0., np.nan]), scale_=np.array([1., np.nan]), var_=np.array([1., np.nan]))
    return capture_trace(calibration_frame=calibration, evaluation_frame=evaluation, label_column='label',
                         raw_calibration=raw, calibration_margins=np.log(raw), raw_evaluation=raw,
                         evaluation_margins=np.log(raw), calibrated_evaluation=raw, calibrators=regressors,
                         calibration_model=model, evaluation_model=model, calibration_scaler=scaler,
                         evaluation_scaler=scaler, columns=['LABELLED feature', 'LABELLED missing feature'],
                         mode='frozen_classifier', endpoint_column='label_end', purpose='unit_fixture',
                         provenance={'scientific_run_identity_sha256': fixture_identity()['identity_sha256'], 'model_version': 'LABELLED FIXTURE MODEL',
                                     'corpus': 'FIXTURE', 'ticker': 'FIXTURE', 'horizon_days': 5})


def test_trace_retains_all_class_arrays_truth_knots_scalers_and_model_bytes():
    trace = trace_fixture()
    assert np.asarray(trace['evaluation']['raw_margins_all_classes']).shape == (2, 3)
    assert trace['evaluation']['truth'] == ['Sell', 'Buy']
    assert trace['calibration_scaler']['mean'][1] is None
    assert trace['calibration_model']['sha256'] == trace['evaluation_model']['sha256']
    assert trace['replay']['purpose'] == 'unit_fixture'
    # Sum-of-class squared errors: (0.38 + 0.24) / 2 = 0.31.
    assert trace['replay']['brier_before'] == pytest.approx(.31)


def test_probability_and_model_byte_tampering_are_independently_rejected():
    trace = trace_fixture()
    trace['calibrated_evaluation'][0] = [.3, .3, .4]
    with pytest.raises(ValueError, match='retained-knot replay'):
        replay_trace(trace)
    trace = trace_fixture()
    trace['evaluation_model']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='model bytes'):
        replay_trace(trace)


def test_all_zero_isotonic_outputs_are_not_uniform_filled():
    trace = trace_fixture()
    knots = copy.deepcopy(trace['isotonic_knots'])
    for knot in knots:
        knot['y'] = [0., 0.]
    with pytest.raises(ValueError, match='all-zero'):
        replay_calibration(np.asarray(trace['evaluation']['raw_probabilities']), knots)


def test_frozen_mode_cannot_claim_different_model_or_scaler_objects():
    trace = trace_fixture()
    trace['same_scaler_object'] = False
    with pytest.raises(ValueError, match='same model/scaler'):
        replay_trace(trace)


def test_truth_date_alignment_and_nonfinite_scores_fail_closed():
    trace = trace_fixture()
    trace['evaluation']['truth'] = ['Buy']
    with pytest.raises(ValueError, match='misaligned'):
        replay_trace(trace)
    trace = trace_fixture()
    trace['evaluation']['raw_margins_all_classes'][0][1] = float('nan')
    with pytest.raises(ValueError, match='finite class scores'):
        replay_trace(trace)


@pytest.mark.parametrize('mutation,reason', [
    (lambda t: t['evaluation_scaler']['mean'].__setitem__(0, 123456.), 'same model/scaler'),
    (lambda t: t['evaluation_scaler']['scale'].pop(), 'align to features'),
    (lambda t: t['evaluation_scaler']['variance'].__setitem__(0, -1.), 'positive/nonnegative'),
    (lambda t: t['calibration']['truth'].__setitem__(0, 'Unknown'), 'truth labels'),
    (lambda t: t['evaluation']['dates'].__setitem__(0, 'not-a-date'), 'ordered ISO'),
    (lambda t: t['evaluation']['dates'].reverse(), 'ordered ISO'),
    (lambda t: t['calibration']['label_end_dates'].__setitem__(1, '2023-01-09'), 'strictly before'),
    (lambda t: t['evaluation']['label_end_dates'].__setitem__(0, '2023-01-08'), 'endpoints must align'),
    (lambda t: t.__setitem__('calibration_mode', 'undeclared'), 'calibration mode'),
    (lambda t: t['evaluation']['raw_margins_all_classes'][0].__setitem__(0, 999.), 'softmax'),
    (lambda t: t['isotonic_knots'].pop(), 'three ordered'),
    (lambda t: t['provenance'].__setitem__('scientific_run_identity_sha256', 'invented'), 'canonical scientific'),
])
def test_consistent_looking_trace_corruptions_cannot_pass_replay(mutation, reason):
    trace = trace_fixture()
    mutation(trace)
    with pytest.raises(ValueError, match=reason):
        replay_trace(trace)


def exported_fixture(trace):
    serialized = trace_bytes(trace)
    binding = trace['provenance']
    digest = binding['scientific_run_identity_sha256']
    provenance = {**binding, 'calibration_mode': trace['calibration_mode'],
                  'data_hashes': {'scientific_run_identity_sha256': digest},
                  'scientific_identity': fixture_identity(),
                  'scientific_trace_sha256': hashlib.sha256(serialized).hexdigest(),
                  'n_calibration_rows': 2, 'n_eval_rows': 2,
                  'metrics': {name: trace['replay'][name] for name in ('brier_before', 'brier_after')}}
    records = []
    for index, day in enumerate(trace['evaluation']['dates']):
        probabilities = trace['calibrated_evaluation'][index]
        chosen = int(np.argmax(probabilities))
        records.append({'session_date': day, 'decision': trace['classes'][chosen],
                        'probabilities': dict(zip(trace['classes'], probabilities)),
                        'raw_model_output': trace['evaluation']['raw_margins_all_classes'][index][chosen],
                        'model_version': binding['model_version'], 'data_hashes': provenance['data_hashes'].copy(),
                        'ticker': binding['ticker'], 'horizon_days': binding['horizon_days']})
    return {'provenance': provenance, 'decision_records': records}, serialized


def test_result_trace_binding_replays_scores_and_explicitly_does_not_claim_model_inference():
    payload, serialized = exported_fixture(trace_fixture())
    report = validate_result_trace(payload, serialized)
    assert report['model_bytes_integrity_passed']
    assert report['score_probability_consistency_passed']
    assert report['label_availability_replay_passed']
    assert not report['model_inference_replayed']


@pytest.mark.parametrize('mutation,reason', [
    (lambda p: p['provenance']['metrics'].__setitem__('brier_before', .9), 'Brier differs'),
    (lambda p: p['provenance'].__setitem__('scientific_trace_sha256', '0' * 64), 'byte identities'),
    (lambda p: p['provenance'].__setitem__('model_version', 'ANOTHER FIXTURE'), 'model/data identity'),
    (lambda p: p['provenance']['scientific_identity'].__setitem__('identity_sha256', 'b' * 64), 'run identities'),
    (lambda p: p['provenance']['scientific_identity'].__setitem__('runtime', 'CORRUPTED'), 'run identities'),
    (lambda p: p['provenance'].__setitem__('n_eval_rows', 3), 'row counts'),
    (lambda p: p['decision_records'].reverse(), 'evaluation dates/order'),
    (lambda p: p['decision_records'][0].__setitem__('raw_model_output', 0.), 'probability/margin'),
    (lambda p: p['decision_records'][0].__setitem__('ticker', 'OTHER'), 'different scientific run'),
    (lambda p: p['decision_records'][0]['data_hashes'].__setitem__('corpus_lineage_status', 'invented'), 'different scientific run'),
])
def test_export_binding_rejects_mismatched_summaries_and_records(mutation, reason):
    payload, serialized = exported_fixture(trace_fixture())
    mutation(payload)
    with pytest.raises(ValueError, match=reason):
        validate_result_trace(payload, serialized)


def test_swapped_trace_from_another_run_is_rejected_even_when_numerically_valid():
    first = trace_fixture()
    payload, _ = exported_fixture(first)
    second = trace_fixture()
    second['provenance']['scientific_run_identity_sha256'] = 'b' * 64
    swapped = trace_bytes(second)
    with pytest.raises(ValueError, match='byte identities'):
        validate_result_trace(payload, swapped)
    payload['provenance']['scientific_trace_sha256'] = hashlib.sha256(swapped).hexdigest()
    with pytest.raises(ValueError, match='run identities'):
        validate_result_trace(payload, swapped)


def test_float32_calibration_roundoff_is_distinct_from_corrupted_probabilities():
    trace = trace_fixture()
    del trace['replay']
    raw = np.asarray(trace['evaluation']['raw_probabilities'], dtype=np.float32)
    trace['calibrated_evaluation'] = (raw / raw.sum(axis=1, keepdims=True)).tolist()
    assert replay_trace(trace)['calibration_numeric_replay_passed']
    trace['calibrated_evaluation'][0][0] += .001
    trace['calibrated_evaluation'][0][2] -= .001
    with pytest.raises(ValueError, match='retained-knot replay'):
        replay_trace(trace)
