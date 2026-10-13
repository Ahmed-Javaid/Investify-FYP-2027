"""Recorded evidence for the presenter UI. No training, downloads or file writes."""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from investify.decision_record import DecisionRecord
from investify.explain.context import build_context
from investify.risk_comparator import build_comparator

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
FRESH = ARTIFACTS / 'scientific_runs/alpaca_revision_conservative_20261012_run01/recovery01'
TEMPERATURE = ARTIFACTS / 'scientific_runs/temperature_calibration_20261013_run01'
SOURCES = {
    'temperature_frozen': ('Alpaca, multiclass calibration (frozen)', TEMPERATURE / 'frozen/decision_records.json'),
    'temperature_refit': ('Alpaca, multiclass calibration (refit)', TEMPERATURE / 'refit/decision_records.json'),
    'fresh_frozen': ('Fresh Alpaca, frozen classifier', FRESH / 'engine_frozen_alpaca/decision_records.json'),
    'fresh_refit': ('Fresh Alpaca, refit classifier', FRESH / 'engine_refit_alpaca/decision_records.json'),
    'alpaca': ('Archived Alpaca', ARTIFACTS / 'decision_records_alpaca.json'),
    'fnspid': ('Archived FNSPID', ARTIFACTS / 'decision_records.json'),
}


def temperature_diagnosis(collection):
    if collection.source not in ('temperature_frozen', 'temperature_refit'):
        raise ValueError('No temperature experiment for this case')
    mode = 'frozen' if collection.source == 'temperature_frozen' else 'refit'
    path = TEMPERATURE / mode / 'experiment.json'
    bindings = read_json(ROOT.parent / 'evidence/temperature_record_bindings_20261014.json')['modes'][mode]
    if sha256(path.read_bytes()).hexdigest() != bindings['experiment_sha256'] or collection.sha256 != bindings['records_sha256']:
        raise ValueError('Temperature diagnosis does not match verified record/experiment bytes')
    result = read_json(path)
    trace = FRESH / ('engine_frozen_alpaca' if mode == 'frozen' else 'engine_refit_alpaca') / 'scientific_trace.json'
    if result['original_trace_sha256'] != sha256(trace.read_bytes()).hexdigest():
        raise ValueError('Temperature diagnosis differs from its original source')
    if result['argmax_preserved_rows'] != len(collection.records):
        raise ValueError('Temperature diagnosis row count differs')
    return result

@dataclass(frozen=True)
class CaseCollection:
    source: str
    sha256: str
    provenance: dict
    records: dict

    def identity(self, session):
        if session not in self.records:
            raise ValueError('Unknown recorded session')
        return f'{self.source}:{session}:{self.sha256}'

def read_json(path):
    data = Path(path).read_bytes()
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('Recorded evidence exceeds the viewer size limit')
    def refuse(value):
        raise ValueError('Non-finite JSON evidence: ' + value)
    return json.loads(data, parse_constant=refuse)

def load_cases(source):
    if source not in SOURCES:
        raise ValueError('Unknown experiment source')
    path = SOURCES[source][1]
    raw = path.read_bytes()
    if source.startswith('temperature_'):
        mode = 'frozen' if source == 'temperature_frozen' else 'refit'
        bindings = read_json(ROOT.parent / 'evidence/temperature_record_bindings_20261014.json')['modes'][mode]
        if sha256(raw).hexdigest() != bindings['records_sha256']:
            raise ValueError('Corrected calibration records differ from their verified identity')
    payload = read_json(path)
    rows = payload['decision_records']
    if not rows:
        raise ValueError('The selected experiment has no recorded decisions')
    records = {}
    for row in rows:
        record = DecisionRecord.from_dict(row)
        build_context(record, corpus=source)
        if record.session_date in records:
            raise ValueError('Duplicate session in a recorded experiment')
        records[record.session_date] = record
    if len({(r.ticker, r.horizon_days, r.model_version) for r in records.values()}) != 1:
        raise ValueError('A case collection must have one ticker, horizon and model')
    if path.read_bytes() != raw:
        raise ValueError('The evidence changed while it was being loaded')
    return CaseCollection(source, sha256(raw).hexdigest(), payload['provenance'], records)

def comparator_for(collection):
    result = build_comparator(SOURCES[collection.source][1], corpus=collection.source)
    if result.manifest['artifact_sha256'] != collection.sha256:
        raise ValueError('Comparator evidence differs from the selected record')
    return result

def social_comparison():
    from app.tabs.social_study import read_json, recorded_receipt_comparison, STUDY
    from investify.sentiment_selection import validate_benchmark
    benchmark = read_json(STUDY / 'social_benchmark.json')
    usable = validate_benchmark(benchmark)
    parent = read_json(STUDY / 'social_selection_plan.json')
    pointer = read_json(STUDY / 'social_latest_study.json')
    comparison = recorded_receipt_comparison(benchmark, parent, pointer)
    return benchmark, usable, comparison

def leakage_results():
    payload = read_json(FRESH / 'harness_alpaca/results_alpaca.json')
    primary = {r['arm']: r for r in payload['results'] if r['horizon_days'] == 5}
    if set(primary) != {'A_CLEAN','B_SHUFFLED','C_NOPURGE','D_CENTRED','D_CENTRED_SMA200','E_SAMEBAR_TEXT'}:
        raise ValueError('The recorded harness comparison is incomplete')
    return payload, primary


def calibration_diagnosis(collection):
    """Bind the fresh-map diagnostic to the selected source's actual trace bytes."""
    if collection.source not in ("fresh_frozen", "fresh_refit"):
        raise ValueError("No fresh-map diagnosis is established for this historical source")
    key = "engine_frozen_alpaca" if collection.source == "fresh_frozen" else "engine_refit_alpaca"
    receipt = read_json(ROOT.parent / "evidence/calibration_global_bounds_20261013.json")
    result = receipt["results"][key]
    trace_path = SOURCES[collection.source][1].parent / "scientific_trace.json"
    trace_bytes = trace_path.read_bytes()
    if sha256(trace_bytes).hexdigest() != result["trace_sha256"]:
        raise ValueError("The diagnostic does not match this experiment's calibration trace")
    trace = json.loads(trace_bytes)
    sample = next(iter(collection.records.values()))
    if (trace["provenance"]["model_version"] != sample.model_version
            or result["calibrated_evaluation_rows"] != len(collection.records)
            or result["unconditionally_dominant_class"] != "Buy"):
        raise ValueError("Calibration diagnostic identity does not match the selected records")
    return result
