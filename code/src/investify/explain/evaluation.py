"""Frozen chronological evaluation plan and real-provider result accounting."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from investify.decision_record import DecisionRecord
from investify.source_revision import source_revision
from investify.explain.local_llm import LocalExplainer, PROMPT_VERSION, verify_generated
from investify.explain.template import render, render_guided
from investify.explain.verifier import VERIFIER_CONTRACT_VERSION, verify

ROOT = Path(__file__).resolve().parents[3]
FILES = {'alpaca': 'decision_records_alpaca.json', 'fnspid': 'decision_records.json'}


def evaluation_plan(*, per_corpus: int = 6, artifacts: Path = ROOT / 'artifacts') -> tuple[dict, list]:
    if type(per_corpus) is not int or not 1 <= per_corpus <= 38:
        raise ValueError('per_corpus must be an integer from 1 to 38')
    manifest = {}
    selected = []
    for corpus, filename in FILES.items():
        path = artifacts / filename
        data = json.loads(path.read_text(encoding='utf-8'))
        records = sorted((DecisionRecord.from_dict(p) for p in data['decision_records']),
                         key=lambda record: record.session_date)
        cutoff = int(len(records) * 0.8)
        development, heldout = records[:cutoff], records[cutoff:]
        if not development or len(heldout) < per_corpus:
            raise ValueError('Insufficient saved records for the declared chronological split')
        dates = [r.session_date for r in records]
        if len(set(dates)) != len(dates):
            raise ValueError('Duplicate sessions in the single-ticker evaluation corpus')
        indices = ([len(heldout) // 2] if per_corpus == 1 else
                   [i * (len(heldout) - 1) // (per_corpus - 1) for i in range(per_corpus)])
        sample = [heldout[i] for i in indices]
        selected.extend((corpus, record) for record in sample)
        manifest[corpus] = {
            'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'development_sessions': [r.session_date for r in development],
            'heldout_sessions': [r.session_date for r in heldout],
            'selected_sessions': [r.session_date for r in sample],
            'selected_record_sha256': {r.session_date: hashlib.sha256(
                json.dumps(r.to_dict(), sort_keys=True, allow_nan=False).encode()).hexdigest() for r in sample},
        }
    plan = {'protocol': 'chronological-explainer-pilot-v1', 'development_fraction': 0.8,
            'purpose': 'Prompt-development/evaluation separation over saved model evaluation records; no retraining',
            'prompt_version': PROMPT_VERSION, 'verifier_contract': VERIFIER_CONTRACT_VERSION,
            'examples_selected': len(selected), 'per_corpus': per_corpus, 'corpora': manifest,
            'contract_source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                      for path in [ROOT / 'src/investify/explain/local_llm.py',
                                                   ROOT / 'src/investify/explain/template.py',
                                                   ROOT / 'src/investify/explain/context.py',
                                                   ROOT / 'src/investify/explain/verifier.py',
                                                   ROOT / 'src/investify/explain/pipeline.py',
                                                   ROOT / 'src/investify/decision_record.py',
                                                   ROOT / 'src/investify/source_revision.py',
                                                   ROOT / 'src/investify/publisher_models.py',
                                                   ROOT / 'artifacts/mid_eval/official_model_catalog.json',
                                                   ROOT / 'scripts/evaluate_mideval_llm.py', Path(__file__)]}}
    return plan, selected


def score(result) -> dict:
    return {'passed': result.passed, 'numeric_fidelity': result.numeric_fidelity,
            'directional_consistency': result.directional_consistency,
            'claim_recall': result.claim_recall, 'unverifiable_rate': result.unverifiable_rate,
            'failed_metrics': list(result.failed_metrics)}


def evaluate(explainer: LocalExplainer, *, per_corpus: int = 6, plan_only: bool = False,
             declared_plan: dict | None = None, progress=None) -> dict:
    plan, records = evaluation_plan(per_corpus=per_corpus)
    if not plan_only and explainer.config.model is not None:
        if declared_plan is None:
            raise ValueError('Real inference requires a previously saved evaluation plan')
        if declared_plan != plan:
            raise ValueError('Saved evaluation plan differs from current data, selection or contract source')
    baselines = []
    for corpus, record in records:
        numeric, guided = render(record), render_guided(record)
        baselines.append({'corpus': corpus, 'session': record.session_date,
                          'numeric_template': score(verify(record, numeric.text, numeric.payload, strict_prose=True)),
                          'guided_template': score(verify_generated(record, guided)),
                          'reviewed_definitions': len(guided.payload['definitions'])})
    report = {'checked_utc': datetime.now(timezone.utc).isoformat(),
              **source_revision(ROOT),
              'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in [Path(__file__), ROOT / 'src/investify/explain/local_llm.py',
                                             ROOT / 'src/investify/explain/template.py', ROOT / 'src/investify/explain/verifier.py',
                                             ROOT / 'src/investify/explain/context.py']},
              'scope': 'Constrained local explanation pilot; no model retraining, predictive-skill claim or human comprehension measurement',
              'configuration': {'requested_model': explainer.config.model,
                                'base_url': explainer.config.base_url,
                                'timeout_seconds': explainer.config.timeout_seconds,
                                'max_attempts': explainer.config.max_attempts,
                                'max_tokens': explainer.config.max_tokens},
              'plan': plan, 'baselines': baselines, 'results': [],
              'declared_plan_matched': declared_plan == plan if declared_plan is not None else False,
              'quality_metrics': None, 'raw_completions': 0, 'examples_evaluated': 0,
              'evaluation_complete': False}
    if plan_only or explainer.config.model is None:
        report.update(status='plan_only' if plan_only else 'blocked',
                      reason='No model requests made' if plan_only else 'No local model configured')
        return report
    for corpus, record in records:
        result = explainer.explain(record, corpus=corpus)
        report['results'].append({
            'corpus': corpus, 'session': record.session_date, 'status': result.status,
            'reason': result.reason, 'used_template': result.used_template,
            'emitted': score(result.emitted.verification), 'emitted_text': result.emitted.text,
            'attempts': [{'number': a.number, 'raw_output': a.raw_output, 'served_model': a.served_model,
                          'elapsed_seconds': a.elapsed_seconds, 'prompt_sha256': a.prompt_sha256,
                          'error': a.error, 'usage': a.usage,
                          'finish_reason': a.finish_reason,
                          'verification': score(a.verification) if a.verification else None}
                         for a in result.attempts]})
        if progress is not None:
            progress(report['results'][-1])
        if result.status == 'template_unavailable':
            break
    rows = report['results']
    attempts = [a for r in rows for a in r['attempts']]
    report['examples_evaluated'] = len(rows)
    report['raw_completions'] = sum(a['raw_output'] is not None for a in attempts)
    report['evaluation_complete'] = len(rows) == len(records)
    if not report['raw_completions']:
        report.update(status='blocked', reason='No real model completion returned; no quality metrics reported')
        return report
    first = [r['attempts'][0] for r in rows if r['attempts']]
    report['quality_metrics'] = {
        'scope': 'Recorded examples only; partial runs are not a complete benchmark',
        'first_attempt_contract_pass_rate': sum(bool(a['verification'] and a['verification']['passed']) for a in first) / len(first),
        'accepted_generation_rate': sum(not r['used_template'] for r in rows) / len(rows),
        'fallback_rate': sum(r['used_template'] for r in rows) / len(rows),
        'all_emitted_outputs_pass': all(r['emitted']['passed'] for r in rows),
    }
    report.update(status='evaluated' if report['evaluation_complete'] else 'partial',
                  reason='Real local completions and all failed attempts are recorded')
    return report
