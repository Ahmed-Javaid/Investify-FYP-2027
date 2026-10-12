"""Replay actual fresh-run model bytes, calibration and TreeSHAP independently."""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run, output = args.run_directory.resolve(), args.output.resolve()
    if not run.is_relative_to(ROOT / 'artifacts/scientific_runs'):
        raise ValueError('Use an isolated scientific run')
    if not output.is_relative_to(ROOT.parent / 'evidence') or output.exists():
        raise ValueError('Preserve old receipts; choose a new evidence path')
    os.environ.update(MPLCONFIGDIR='E:/AI-Tools/Temp/investify-scientific-process-cache/matplotlib',
                      NUMBA_CACHE_DIR='E:/AI-Tools/Temp/investify-scientific-process-cache/numba',
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    import numpy as np
    import pandas as pd
    import xgboost as xgb
    import yaml
    from investify.decision_record import DecisionRecord, SHAP_ADDITIVITY_TOL
    from investify.harness.arms import build_all_matrices
    from investify.harness.metrics import macro_f1
    from investify.science_identity import run_identity
    from investify.scientific_trace import validate_result_trace, replay_calibration
    cfg = yaml.safe_load((run / 'recovery_config.yaml').read_text(encoding='utf-8'))
    matrices = build_all_matrices(cfg, corpus='alpaca')
    frame = matrices['A_CLEAN'].copy()
    frame.index = pd.to_datetime(frame['date']).dt.strftime('%Y-%m-%d')
    report = {'schema': 'investify-fresh-science-actual-replay-v1', 'purpose': 'research',
              'checked_utc': datetime.now(timezone.utc).isoformat(), 'config_path': str(run / 'recovery_config.yaml'),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'network_requests': 0, 'modes': {}, 'passed': False}
    for mode, folder in [('frozen_classifier','engine_frozen_alpaca'),('refit_transfer','engine_refit_alpaca')]:
        suffix = '' if cfg.get('default_corpus') == 'alpaca' else '_alpaca'
        result_path = run / folder / ('decision_records' + suffix + '.json')
        trace_path = result_path.with_name('scientific_trace.json')
        payload = json.loads(result_path.read_text(encoding='utf-8'))
        trace_bytes = trace_path.read_bytes()
        trace = json.loads(trace_bytes)
        consistency = validate_result_trace(payload, trace_bytes)
        if run_identity(dict(cfg, calibration_mode=mode), 'alpaca') != payload['provenance']['scientific_identity']:
            raise ValueError('Current source/input/runtime identity differs from the completed ' + mode + ' run')
        records = [DecisionRecord.from_dict(value) for value in payload['decision_records']]
        inference = {}
        for block in ('calibration','evaluation'):
            snapshot = trace[block + '_model']
            booster = xgb.Booster()
            booster.load_model(bytearray(base64.b64decode(snapshot['base64'], validate=True)))
            scaler = trace[block + '_scaler']
            columns = scaler['features']
            selected = frame.loc[trace[block]['dates']]
            if selected[f"label_{cfg['labels']['primary_horizon_days']}d"].astype(str).tolist() != trace[block]['truth']:
                raise ValueError('Reconstructed labels differ from recorded trace')
            endpoints = pd.to_datetime(selected[f"label_end_{cfg['labels']['primary_horizon_days']}d"]).dt.strftime('%Y-%m-%d').tolist()
            if endpoints != trace[block]['label_end_dates']:
                raise ValueError('Reconstructed label endpoints differ from recorded trace')
            raw_features = selected[columns].to_numpy(dtype=float)
            mean = np.asarray(scaler['mean'], dtype=float)
            scale = np.asarray(scaler['scale'], dtype=float)
            scaled = (raw_features - mean) / scale
            dmatrix = xgb.DMatrix(scaled, feature_names=columns)
            margins = booster.predict(dmatrix, output_margin=True)
            probabilities = booster.predict(dmatrix)
            margin_difference = float(np.max(np.abs(margins - np.asarray(trace[block]['raw_margins_all_classes']))))
            probability_difference = float(np.max(np.abs(probabilities - np.asarray(trace[block]['raw_probabilities']))))
            if margin_difference > 1e-6 or probability_difference > 1e-6:
                raise ValueError('Retained model/scaler inference cannot reproduce ' + block + ' scores')
            inference[block] = {'rows': len(selected), 'maximum_margin_difference': margin_difference,
                                'maximum_probability_difference': probability_difference,
                                'model_sha256': snapshot['sha256'], 'model_inference_replayed': True}
            if block == 'evaluation':
                for index, record in enumerate(records):
                    feature = np.asarray([record.feature_vector[name] for name in columns], dtype=float)
                    if not np.allclose(feature, raw_features[index], atol=0, rtol=0, equal_nan=True):
                        raise ValueError('Record feature values differ from actual reconstructed inputs')
                contributions = booster.predict(dmatrix, pred_contribs=True, strict_shape=True)
                maximum_shap, maximum_base, maximum_sum = 0., 0., 0.
                for index, record in enumerate(records):
                    chosen = trace['classes'].index(record.decision)
                    native = contributions[index, chosen]
                    maximum_shap = max(maximum_shap, float(np.max(np.abs(
                        native[:-1] - np.asarray([record.shap_values[name] for name in columns])))))
                    maximum_base = max(maximum_base, abs(float(native[-1]) - record.base_value))
                    maximum_sum = max(maximum_sum, abs(record.base_value + sum(record.shap_values.values()) - record.raw_model_output))
                if max(maximum_shap, maximum_base, maximum_sum) > SHAP_ADDITIVITY_TOL:
                    raise ValueError('Native XGBoost TreeSHAP differs from exported SHAP values/bias/additivity')
                calibrated = replay_calibration(probabilities, trace['isotonic_knots'])
                predicted = [trace['classes'][int(np.argmax(row))] for row in calibrated]
                f1 = macro_f1(trace['evaluation']['truth'], predicted)
                if not np.isclose(f1, payload['provenance']['metrics']['eval_macro_f1_model'], atol=1e-12, rtol=0):
                    raise ValueError('Replayed held-out F1 differs from the result')
                inference['native_treeshap'] = {'maximum_contribution_difference': maximum_shap,
                    'maximum_base_difference': maximum_base, 'maximum_additivity_residual': maximum_sum,
                    'tolerance': SHAP_ADDITIVITY_TOL}
        report['modes'][mode] = {'result_path': str(result_path),
            'result_sha256': hashlib.sha256(result_path.read_bytes()).hexdigest(),
            'trace_sha256': hashlib.sha256(trace_bytes).hexdigest(),
            'trace_consistency': consistency, 'actual_inference_replay': inference,
            'metrics': payload['provenance']['metrics'],
            'decision_counts': dict(Counter(record.decision for record in records)),
            'calibration_availability': payload['provenance']['calibration_label_availability'],
            'held_out_dates': [records[0].session_date, records[-1].session_date]}
    harness_path = run / 'harness_alpaca/results_alpaca.json'
    harness = json.loads(harness_path.read_text(encoding='utf-8'))
    rows = harness['results']
    for horizon in cfg['labels']['horizons_days']:
        scoped = [row for row in rows if row['horizon_days'] == horizon]
        if len(scoped) != 6 or len({row['n_rows'] for row in scoped}) != 1 or len({row['n_folds'] for row in scoped}) != 1:
            raise ValueError('Harness arms do not retain an identical row/fold count')
    report['harness'] = {'path': str(harness_path), 'sha256': hashlib.sha256(harness_path.read_bytes()).hexdigest(),
                         'arms': rows, 'same_row_counts_per_horizon': True}
    report['passed'] = True
    report['scope'] = ('Actual retained XGBoost model/scaler inference on reconstructed genuine snapshot features; '
        'independent native TreeSHAP, isotonic, label endpoint and metric replay. '
        'No historical-byte reproduction, human validation or profitability claim.')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'passed': True, 'modes': {name: {'decision_counts': value['decision_counts'],
          'metrics': value['metrics']} for name,value in report['modes'].items()}}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
