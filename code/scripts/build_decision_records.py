"""Phase 3 engine entrypoint: train, calibrate, attribute, and emit one
DecisionRecord (decision_record.py) per bar in the held-out evaluation
fold, to artifacts/decision_records.json. Also writes
artifacts/reliability_curve.png (brier before/after isotonic
calibration) and prints the engine's report -- cross-validated macro-F1
(model vs. the transparent linear baseline), the single eval-fold
macro-F1 both actually decide on, Brier before/after, and record count.

`risk_tier` on every emitted record is the fixed placeholder "Balanced"
(engine.RISK_TIER_PLACEHOLDER). This spike's model takes no risk input --
see the scope note at the top of docs/phase2_4_plan.md: risk profiling
is a Phase 4 demo-only concept (the quiz), never a model feature. The
placeholder exists purely so the record is well-formed; the demo's quiz
supplies the real value for display, not this script.

Network-free: reads prices/news/sentiment from data/store and
.cache/finbert_scores, exactly like harness/run_spike.py.

Usage:
    uv run python scripts/build_decision_records.py                  # default corpus
    uv run python scripts/build_decision_records.py --corpus alpaca

Each corpus writes its own records and reliability curve, so the two can be
compared rather than one silently overwriting the other.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify import engine  # noqa: E402
from investify.harness.splits import SPLIT_CONTRACT_VERSION  # noqa: E402
from investify.scientific_trace import trace_bytes, validate_result_trace  # noqa: E402

parser = argparse.ArgumentParser(description="Emit decision records for one corpus.")
parser.add_argument("--corpus", default=None, help="news corpus (config: corpora.*)")
parser.add_argument('--output-directory', type=Path, required=True,
                    help='New directory for corrected-run records/figures; historical artifacts remain unchanged')
parser.add_argument('--config', type=Path, default=Path('config/spike.yaml'))
parser.add_argument('--calibration-mode', choices=['frozen_classifier', 'refit_transfer'], default='frozen_classifier')
args = parser.parse_args()

t0 = time.time()
cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))
artifacts = args.output_directory.resolve()
if artifacts.exists():
    raise ValueError('Preserve prior scientific outputs; choose a new output directory')
artifacts.mkdir(parents=True)

corpus = args.corpus or cfg.get("default_corpus", "fnspid")
if corpus not in cfg["corpora"]:
    raise ValueError(f"unknown corpus {corpus!r}; known: {sorted(cfg['corpora'])}")
suffix = "" if corpus == cfg.get("default_corpus", "fnspid") else f"_{corpus}"

print(
    f"=== Training engine on {cfg['tickers'][0]}, corpus {corpus!r}, primary horizon "
    f"{cfg['labels']['primary_horizon_days']}d, seed {cfg['seed']} ===",
    flush=True,
)

result = engine.run_engine(
    cfg,
    reliability_curve_path=artifacts / f"reliability_curve{suffix}.png",
    corpus=corpus,
    calibration_mode=args.calibration_mode,
)
serialized_trace = trace_bytes(result.scientific_trace)

payload = {
    "provenance": {
        "model_version": result.model_version,
        "data_hashes": result.data_hashes,
        "seed": cfg["seed"],
        "corpus": corpus,
        "ticker": cfg["tickers"][0],
        "horizon_days": cfg["labels"]["primary_horizon_days"],
        "split_contract": SPLIT_CONTRACT_VERSION,
        "label_availability": "Full-price-sequence label endpoints carried through the feature mask; strictly before test session",
        "scientific_source_sha256": {str(path.relative_to(Path(__file__).resolve().parents[1])):
                                      hashlib.sha256(path.read_bytes()).hexdigest() for path in
                                      (Path(__file__), Path(engine.__file__),
                                       Path(engine.__file__).parent / 'harness/splits.py',
                                       Path(engine.__file__).parent / 'harness/arms.py',
                                       Path(engine.__file__).with_name('labels.py'))},
        "calibration_fold_id": result.calibration_fold_id,
        "eval_fold_id": result.eval_fold_id,
        "n_calibration_rows": result.n_calibration_rows,
        "calibration_label_availability": result.calibration_availability,
        "calibration_mode": args.calibration_mode,
        "scientific_identity": result.scientific_identity,
        "input_consumption_audit": result.input_consumption_audit,
        "scientific_trace_file": "scientific_trace.json",
        "scientific_trace_sha256": hashlib.sha256(serialized_trace).hexdigest(),
        "n_eval_rows": result.n_eval_rows,
        "feature_cols": engine.feature_cols(cfg),
        "xgboost_config": cfg["xgboost"],
        "metrics": {
            "cv_macro_f1_mean": result.cv_macro_f1_mean,
            "cv_macro_f1_sd": result.cv_macro_f1_sd,
            "cv_macro_f1_per_fold": result.cv_macro_f1_per_fold,
            "baseline_cv_macro_f1_mean": result.baseline_cv_macro_f1_mean,
            "baseline_cv_macro_f1_sd": result.baseline_cv_macro_f1_sd,
            "baseline_cv_macro_f1_per_fold": result.baseline_cv_macro_f1_per_fold,
            "eval_macro_f1_model": result.eval_macro_f1_model,
            "eval_macro_f1_baseline": result.eval_macro_f1_baseline,
            "brier_before": result.brier_before,
            "brier_after": result.brier_after,
        },
        "run_completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    },
    "decision_records": [r.to_dict() for r in result.records],
}

validate_result_trace(payload, serialized_trace)
(artifacts / 'scientific_trace.json').write_bytes(serialized_trace)
out_path = artifacts / f"decision_records{suffix}.json"
out_path.write_text(json.dumps(payload, indent=2, default=str))

print(f"\n=== Engine report ===")
print(f"Cross-validated macro-F1 (6-fold expanding purged walk-forward, primary horizon):")
print(f"  model:    {result.cv_macro_f1_mean:.4f} +/- {result.cv_macro_f1_sd:.4f}")
print(f"  baseline: {result.baseline_cv_macro_f1_mean:.4f} +/- {result.baseline_cv_macro_f1_sd:.4f}")
print(f"Held-out eval fold (fold {result.eval_fold_id}, n={result.n_eval_rows}), calibrated decisions:")
print(f"  model macro-F1:    {result.eval_macro_f1_model:.4f}")
print(f"  baseline macro-F1: {result.eval_macro_f1_baseline:.4f}")
print(f"Brier score on eval fold: before={result.brier_before:.4f}  after={result.brier_after:.4f}")
print(f"Calibration fitted on fold {result.calibration_fold_id} (n={result.n_calibration_rows}), "
      f"never on the eval fold above.")
print(f"\n{len(result.records)} decision records written -> {out_path}")
print(f"Reliability curve -> {artifacts / f'reliability_curve{suffix}.png'}")
print(f"model_version = {result.model_version}")
print(f"=== DONE in {time.time() - t0:.1f}s ===")
