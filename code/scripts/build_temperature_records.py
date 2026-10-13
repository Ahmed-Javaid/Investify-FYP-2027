"""Create a new calibration experiment from immutable real model/trace inputs."""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE / 'src'))
from investify.decision_record import DecisionRecord
from investify.multiclass_calibration import CLASSES, fit_temperature, softmax_temperature
from investify.explain.template import render, render_guided
from investify.explain.pipeline import emit


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(labels, probs):
    predicted = [CLASSES[max(range(3), key=lambda i: row[i])] for row in probs]
    scores = []
    for label in CLASSES:
        tp = sum(a == b == label for a, b in zip(labels, predicted))
        fp = sum(a != label and b == label for a, b in zip(labels, predicted))
        fn = sum(a == label and b != label for a, b in zip(labels, predicted))
        scores.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.)
    brier = sum(sum((p - (label == name)) ** 2 for name, p in zip(CLASSES, row))
                for label, row in zip(labels, probs)) / len(labels)
    return {'macro_f1': sum(scores) / 3, 'brier': brier, 'class_counts': dict(Counter(predicted))}


def main():
    import numpy as np
    import xgboost as xgb
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(CODE / 'artifacts/scientific_runs') or output.exists():
        raise ValueError('Use a new scientific experiment directory')
    original = CODE / 'artifacts/scientific_runs/alpaca_revision_conservative_20261012_run01/recovery01'
    summaries = {}
    output.mkdir(parents=True)
    for key, folder in (('frozen', 'engine_frozen_alpaca'), ('refit', 'engine_refit_alpaca')):
        record_path, trace_path = original / folder / 'decision_records.json', original / folder / 'scientific_trace.json'
        recorded, trace = json.loads(record_path.read_text()), json.loads(trace_path.read_text())
        calibration, evaluation = trace['calibration'], trace['evaluation']
        fitted = fit_temperature(calibration['raw_margins_all_classes'], calibration['truth'],
                                 calibration['dates'], calibration['label_end_dates'], evaluation['dates'][0])
        probabilities = [softmax_temperature(row, fitted['temperature'])
                         for row in evaluation['raw_margins_all_classes']]
        snapshot = trace['evaluation_model']
        raw_model = base64.b64decode(snapshot['base64'])
        if hashlib.sha256(raw_model).hexdigest() != snapshot['sha256']:
            raise ValueError('Original model bytes changed')
        booster = xgb.Booster(params={'nthread': 4})
        booster.load_model(bytearray(raw_model))
        columns = trace['evaluation_scaler']['features']
        scaler = trace['evaluation_scaler']
        matrix = np.array([[r['feature_vector'][name] for name in columns] for r in recorded['decision_records']], dtype=float)
        scaled = (matrix - np.array(scaler['mean'])) / np.array(scaler['scale'])
        dm = xgb.DMatrix(scaled, feature_names=columns)
        margins = booster.predict(dm, output_margin=True)
        if not np.allclose(margins, evaluation['raw_margins_all_classes'], atol=1e-6, rtol=0):
            raise ValueError('Original raw model replay differs')
        contributions = booster.predict(dm, pred_contribs=True, strict_shape=True)
        version = 'xgboost-temperature-' + key + '-20261013-v1'
        rows = []
        for index, (old, probs) in enumerate(zip(recorded['decision_records'], probabilities)):
            selected = max(range(3), key=lambda i: probs[i])
            if selected != int(np.argmax(margins[index])):
                raise ValueError('Positive temperature changed the raw argmax')
            row = dict(old, decision=CLASSES[selected], probabilities=dict(zip(CLASSES, probs)), model_version=version)
            values = contributions[index, selected]
            row['shap_values'] = {name: float(value) for name, value in zip(columns, values[:-1])}
            row['base_value'] = float(values[-1])
            row['raw_model_output'] = float(margins[index, selected])
            ranked = sorted(((name, value) for name, value in row['shap_values'].items() if value != 0),
                            key=lambda item: abs(item[1]), reverse=True)[:5]
            row['top_k'] = [{'name': name, 'value': row['feature_vector'][name], 'shap_value': value,
                             'rank': rank, 'direction': 'supports' if value > 0 else 'opposes'}
                            for rank, (name, value) in enumerate(ranked, 1)]
            row['data_hashes'] = dict(old['data_hashes'], original_trace_sha256=sha(trace_path),
                                      temperature_source_sha256=sha(CODE / 'src/investify/multiclass_calibration.py'))
            row['created_utc'] = datetime.now(timezone.utc).isoformat()
            record = DecisionRecord.from_dict(row)
            for explanation in (render(record), render_guided(record)):
                result = emit(record, candidate=explanation, strict_prose=True)
                if result.replaced_by_template or not result.verification.passed:
                    raise ValueError('Corrected decision explanation failed verification')
            rows.append(row)
        result = {'schema': 'investify-temperature-experiment-v1', 'mode': key, 'fit': fitted,
                  'original_records_sha256': sha(record_path), 'original_trace_sha256': sha(trace_path),
                  'builder_sha256': sha(Path(__file__)), 'original_model_sha256': snapshot['sha256'],
                  'raw': metrics(evaluation['truth'], evaluation['raw_probabilities']),
                  'isotonic': metrics(evaluation['truth'], trace['calibrated_evaluation']),
                  'temperature': metrics(evaluation['truth'], probabilities),
                  'evaluation_first': evaluation['dates'][0], 'evaluation_last': evaluation['dates'][-1],
                  'raw_model_replay_passed': True, 'argmax_preserved_rows': len(rows),
                  'native_shap_and_two_explanation_styles_checked': len(rows),
                  'scope': 'Post-analysis engineering correction; same recorded inputs, new calibration identity.'}
        target = output / key
        target.mkdir()
        payload = {'provenance': dict(recorded['provenance'], model_version=version,
                                      calibration_mode='multiclass_temperature', temperature=fitted['temperature'],
                                      original_trace_sha256=sha(trace_path)), 'decision_records': rows}
        (target / 'decision_records.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        (target / 'experiment.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        summaries[key] = result
    (output / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: {'temperature': v['fit']['temperature'], 'metrics': v['temperature']} for k, v in summaries.items()}, indent=2))


if __name__ == '__main__':
    main()
