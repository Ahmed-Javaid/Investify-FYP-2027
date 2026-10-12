"""Read-only recovered sklearn isotonic check on labelled numeric fixtures.

Run with CPython 3.13 -I -B and the existing CookBookAI site-packages.
Only the unchanged engine isotonic function bodies and the actual trace
module execute. Classifier/model/scaler objects are explicitly fixture
seams; no market inputs, publisher weights or classifier inference run.
Stdout is JSON. A separate parent process may retain it as new evidence.
"""
import argparse
import ast
import builtins
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace


def install_read_only_guards():
    """Deny Python file mutations and sockets before importing the backend."""
    original_open, original_io_open, original_os_open = builtins.open, io.open, os.open

    def read_only(original):
        def guarded(file, mode='r', *args, **kwargs):
            if any(flag in mode for flag in 'wax+'):
                raise PermissionError('Read-only calibration fixture refuses file writes')
            return original(file, mode, *args, **kwargs)
        return guarded

    def guarded_os_open(file, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise PermissionError('Read-only calibration fixture refuses file writes')
        return original_os_open(file, flags, *args, **kwargs)

    def refuse(*args, **kwargs):
        raise PermissionError('Read-only calibration fixture refuses mutations and network operations')

    class RefusedSocket(socket.socket):
        # Preserve the class interface needed by ssl/asyncio at import time.
        def __new__(cls, *args, **kwargs):
            raise PermissionError('Read-only calibration fixture refuses socket creation')

    builtins.open, io.open, os.open = read_only(original_open), read_only(original_io_open), guarded_os_open
    for name in ('mkdir', 'makedirs', 'remove', 'unlink', 'rmdir', 'rename', 'replace', 'chmod', 'link', 'symlink'):
        setattr(os, name, refuse)
    socket.socket = RefusedSocket
    for name in ('create_connection', 'getaddrinfo', 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr'):
        setattr(socket, name, refuse)


def file_identity(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'sha256': digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-packages', type=Path,
                        default=Path('E:/Uni_Stuff/Projects/WeatherForcastAI/CookBookAI/venv/Lib/site-packages'))
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 13) or not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError('Use the recovered CPython 3.13 interpreter with -I -B')
    if not args.site_packages.is_dir():
        raise FileNotFoundError('Recovered site-packages is absent; no dependency installation is attempted')
    project = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(args.site_packages.resolve()))
    sys.path.insert(0, str(project / 'code/src'))
    install_read_only_guards()

    import numpy as np
    import pandas as pd
    import scipy
    import sklearn
    from sklearn.isotonic import IsotonicRegression
    import sklearn.isotonic as isotonic_source
    import sklearn._isotonic as isotonic_extension
    import scipy.interpolate._interpolate as interpolation_source
    from investify import scientific_trace

    engine = project / 'code/src/investify/engine.py'
    engine_bytes = engine.read_bytes()
    parsed = ast.parse(engine_bytes)
    names = {'fit_isotonic_calibrators', 'apply_calibration'}
    definitions = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in definitions} != names:
        raise ValueError('Expected unchanged engine helper definitions were not found')
    namespace = {'np': np, 'IsotonicRegression': IsotonicRegression, 'CLASS_LABELS': ('Buy', 'Hold', 'Sell')}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(engine), 'exec'), namespace)
    helper_hashes = {node.name: hashlib.sha256(ast.get_source_segment(engine_bytes.decode('utf-8'), node).encode()).hexdigest()
                     for node in definitions}

    calibration = np.array([[.7, .2, .1], [.6, .3, .1], [.3, .4, .3], [.2, .6, .2], [.3, .3, .4],
                            [.1, .2, .7], [.5, .4, .1], [.3, .5, .2], [.2, .3, .5]], dtype=np.float32)
    truth = np.array([0, 0, 1, 1, 2, 2, 0, 1, 2])
    evaluation = np.array([[.57, .3, .13], [.2, .41, .39], [.06, .15, .79]], dtype=np.float32)
    classes = ('Buy', 'Hold', 'Sell')
    regressors = namespace['fit_isotonic_calibrators'](calibration, truth)
    saved = namespace['apply_calibration'](evaluation, regressors)
    knots = [{'class': label, 'x': regressors[index].X_thresholds_.tolist(),
              'y': regressors[index].y_thresholds_.tolist(), 'out_of_bounds': regressors[index].out_of_bounds}
             for index, label in enumerate(classes)]
    maximum_difference = float(np.max(np.abs(saved - scientific_trace.replay_calibration(evaluation.astype(float), knots))))
    cal_dates = pd.bdate_range('2023-01-02', periods=10)
    eval_dates = pd.bdate_range('2023-02-01', periods=4)
    calibration_frame = pd.DataFrame({'date': cal_dates[:-1], 'label': [classes[index] for index in truth],
                                     'label_end': cal_dates[1:]})
    evaluation_frame = pd.DataFrame({'date': eval_dates[:-1], 'label': list(classes), 'label_end': eval_dates[1:]})

    class LabelledModelFixture:
        def get_booster(self):
            return self

        def save_raw(self, raw_format):
            if raw_format != 'json':
                raise ValueError('Unexpected fixture serialization request')
            return b'{"LABELLED":"fixture only; no classifier fit or inference"}'

    model = LabelledModelFixture()
    scaler = SimpleNamespace(mean_=np.array([0.]), scale_=np.array([1.]), var_=np.array([1.]))
    trace = scientific_trace.capture_trace(
        calibration_frame=calibration_frame, evaluation_frame=evaluation_frame, label_column='label',
        raw_calibration=calibration, calibration_margins=np.log(calibration), raw_evaluation=evaluation,
        evaluation_margins=np.log(evaluation), calibrated_evaluation=saved, calibrators=regressors,
        calibration_model=model, evaluation_model=model, calibration_scaler=scaler, evaluation_scaler=scaler,
        columns=['LABELLED_feature'], mode='frozen_classifier', endpoint_column='label_end', purpose='unit_fixture',
        provenance={'scientific_run_identity_sha256': 'c' * 64, 'model_version': 'LABELLED real isotonic backend fixture',
                    'corpus': 'LABELLED_NUMERIC_FIXTURE', 'ticker': 'FIXTURE', 'horizon_days': 1})
    report = scientific_trace.replay_trace(trace)
    if maximum_difference > scientific_trace.CALIBRATION_REPLAY_TOL or report['model_inference_replayed']:
        raise AssertionError('Recovered isotonic fixture replay did not satisfy its declared contract')
    serialized_trace = scientific_trace.trace_bytes(trace)
    result = {
        'schema': 'investify-recovered-isotonic-fixture-v1', 'purpose': 'unit_fixture',
        'execution_kind': 'labelled_numeric_fixture_actual_sklearn_isotonic_helpers',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'runtime': {'executable': sys.executable, 'python': sys.version.split()[0], 'numpy': np.__version__,
                    'pandas': pd.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__,
                    'site_packages': str(args.site_packages.resolve()), 'isolated': True, 'bytecode_disabled': True},
        'source_files': {'probe_script': file_identity(__file__), 'engine': file_identity(engine),
                         'scientific_trace': file_identity(scientific_trace.__file__)},
        'executed_engine_helper_sha256': helper_hashes,
        'backend_implementation_files': {'isotonic_python': file_identity(isotonic_source.__file__),
                                         'isotonic_extension': file_identity(isotonic_extension.__file__),
                                         'scipy_interpolation': file_identity(interpolation_source.__file__)},
        'fixture_definition': {'classes': list(classes), 'calibration_input_dtype': str(calibration.dtype),
                               'calibration_truth_indices': truth.tolist(), 'calibration_raw_probabilities': calibration.tolist(),
                               'evaluation_raw_probabilities': evaluation.tolist(),
                               'knots': knots, 'actual_calibrated_probabilities': saved.tolist(),
                               'actual_calibrated_dtype': str(saved.dtype),
                               'calendar': 'Pandas business-day fixture; not exchange/market evidence',
                               'classifier_and_scaler_state': 'Explicit labelled unit-fixture seams, not fitted models'},
        'full_trace': trace, 'full_trace_serialization_sha256': hashlib.sha256(serialized_trace).hexdigest(),
        'maximum_float32_vs_float64_difference': maximum_difference,
        'declared_absolute_tolerance': scientific_trace.CALIBRATION_REPLAY_TOL,
        'trace_replay_passed': report['calibration_numeric_replay_passed'],
        'actual_isotonic_fit_executed_on_numeric_fixture': True, 'classifier_fit_or_inference_executed': False,
        'historical_market_run_executed': False, 'scientific_python311_lock_restored': False,
        'file_writes_and_python_socket_operations_refused': True,
        'scope': 'Actual recovered sklearn fits three calibration mappings on fixed labelled numeric fixtures and executes '
                 'the unchanged engine helper bodies plus current trace replay. No original market data, publisher model '
                 'weights, classifier/scaler fitting, predictive-quality finding, or supported scientific-lock restoration.'}
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
