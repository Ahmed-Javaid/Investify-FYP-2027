"""Validate cached records, user evidence, and the template path without training."""
import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investify.decision_record import DecisionRecord
from investify.source_revision import source_revision
from investify.explain.context import build_context
from investify.explain.pipeline import emit
from investify.explain.verifier import VERIFIER_CONTRACT_VERSION
from investify.explain.local_llm import verify_generated
from investify.explain.template import render_guided


def verify_artifacts() -> dict:
    results = []
    for corpus, filename in [("fnspid", "decision_records.json"), ("alpaca", "decision_records_alpaca.json")]:
        path = ROOT / "artifacts" / filename
        data = json.loads(path.read_text())
        records = [DecisionRecord.from_dict(p) for p in data["decision_records"]]
        if not records:
            raise ValueError(f"No records in {path}")
        for record in records:
            json.dumps(build_context(record, corpus=corpus), allow_nan=False)
            if not emit(record).verification.passed:
                raise ValueError(f"Template failed for {corpus} {record.session_date}")
            if not verify_generated(record, render_guided(record)).passed:
                raise ValueError(f"Guided template failed for {corpus} {record.session_date}")
        counts = dict(Counter(r.decision for r in records))
        results.append({
            "corpus": corpus, "records": len(records), "template_passes": len(records),
            "guided_template_passes": len(records),
            "decision_counts": counts, "constant_predictor": len(counts) == 1,
            "max_shap_residual": max(abs(r.base_value + sum(r.shap_values.values()) - r.raw_model_output) for r in records),
            "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return {
        "checked_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        **source_revision(ROOT),
        "validation_sources_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                ROOT / "src/investify/decision_record.py",
                ROOT / "src/investify/source_revision.py",
                ROOT / "src/investify/explain/context.py",
                ROOT / "src/investify/explain/template.py",
                ROOT / "src/investify/explain/verifier.py",
                ROOT / "src/investify/explain/pipeline.py",
                ROOT / "src/investify/explain/local_llm.py",
                ROOT / "src/investify/explain/evaluation.py",
                ROOT / "src/investify/demo_server.py",
                ROOT / "src/investify/demo_readiness.py",
                ROOT / "src/investify/risk_profile.py",
                ROOT / "src/investify/risk_comparator.py",
                ROOT / "app/risk_profile_form.py",
                ROOT / "app/tabs/decision.py",
                ROOT / "app/streamlit_app.py",
                ROOT / "app/tabs/social_study.py",
                ROOT / "src/investify/sentiment_selection.py",
                ROOT / "src/investify/sentiment_inference.py",
                ROOT / "scripts/evaluate_social_study.py",
                ROOT / "scripts/run_social_inference.py",
                ROOT / "app/mideval_demo.html",
            ]
        },
        "scope": "Committed records, evidence context, numeric and definition-enhanced deterministic templates; no retraining or real LLM generation evaluation",
        "verifier_contract": VERIFIER_CONTRACT_VERSION,
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify_artifacts()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Validated {sum(r['records'] for r in report['results'])} records; report: {args.output}")
