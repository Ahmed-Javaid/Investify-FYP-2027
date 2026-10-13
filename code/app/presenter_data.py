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
SOURCES = {
    'fresh_frozen': ('Fresh Alpaca, frozen classifier', FRESH / 'engine_frozen_alpaca/decision_records.json'),
    'fresh_refit': ('Fresh Alpaca, refit classifier', FRESH / 'engine_refit_alpaca/decision_records.json'),
    'alpaca': ('Archived Alpaca', ARTIFACTS / 'decision_records_alpaca.json'),
    'fnspid': ('Archived FNSPID', ARTIFACTS / 'decision_records.json'),
}

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
