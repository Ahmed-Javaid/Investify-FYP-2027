"""Audit global class bounds of retained isotonic maps without fitting or tuning."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "code/artifacts/scientific_runs/alpaca_revision_conservative_20261012_run01/recovery01"


def audit_trace(path):
    payload = path.read_bytes()
    trace = json.loads(payload)
    classes = trace["classes"]
    maps = trace["isotonic_knots"]
    if len(classes) != 3 or set(classes) != {"Buy", "Hold", "Sell"} or len(maps) != 3:
        raise ValueError("Expected the retained three-class isotonic trace")
    bounds = {}
    for mapping in maps:
        name = mapping["class"]
        x, y = mapping["x"], mapping["y"]
        if (name in bounds or name not in classes or mapping["out_of_bounds"] != "clip"
                or len(x) != len(y) or not x
                or any(not math.isfinite(v) for v in x + y)
                or any(v < 0 or v > 1 for v in x + y)
                or any(a >= b for a, b in zip(x, x[1:]))
                or any(a > b for a, b in zip(y, y[1:]))):
            raise ValueError("Invalid monotone clipped calibration map")
        bounds[name] = {"minimum": min(y), "maximum": max(y), "knots": len(x)}
    winner = None
    gap = None
    for name in classes:
        candidate_gap = bounds[name]["minimum"] - max(bounds[other]["maximum"] for other in classes if other != name)
        if candidate_gap > 0:
            winner, gap = name, candidate_gap
    minimum_sum = sum(b["minimum"] for b in bounds.values())
    if minimum_sum <= 0:
        raise ValueError("Cannot establish a positive renormalization denominator for every input")
    observed = trace["calibrated_evaluation"]
    observed_counts = {name: 0 for name in classes}
    for row in observed:
        if len(row) != len(classes) or any(not math.isfinite(v) or v < 0 for v in row):
            raise ValueError("Invalid retained calibrated probabilities")
        observed_counts[classes[max(range(len(classes)), key=lambda i: row[i])]] += 1
    return {"trace_sha256": sha256(payload).hexdigest(), "classes": classes,
            "calibrator_global_bounds": bounds, "unconditionally_dominant_class": winner,
            "minimum_pre_normalization_winner_gap": gap, "minimum_pre_normalization_row_sum": minimum_sum,
            "calibrated_evaluation_rows": len(observed), "observed_class_counts": observed_counts,
            "derivation": "A monotone piecewise-linear map with clipped endpoints stays within its saved y bounds. The winning class minimum strictly exceeds every competing class maximum. Dividing every coordinate by the same positive row sum preserves argmax. The fixed maps therefore select the dominant class for every valid raw probability vector, not only the inspected evaluation rows.",
            "boundary": "Applies to these byte-identified fresh maps only. Does not prove the cause of preserved September maps or justify any held-out threshold/map tuning."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "evidence") or output.exists():
        raise ValueError("Use a new receipt in the project evidence directory")
    result = {"schema": "investify-calibration-global-bounds-v1", "checked_utc": datetime.now(timezone.utc).isoformat(),
              "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
              "model_fitting_executed": False, "threshold_or_label_changes": False,
              "results": {name: audit_trace(BASE / name / "scientific_trace.json") for name in ("engine_frozen_alpaca", "engine_refit_alpaca")}}
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for name, values in result["results"].items():
        print(name, "unconditional winner:", values["unconditionally_dominant_class"],
              "minimum map gap:", round(values["minimum_pre_normalization_winner_gap"], 6))


if __name__ == "__main__":
    main()
