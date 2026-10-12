"""Auditable social-sentiment selection over declared human or AI references.

This module neither acquires posts nor annotates them nor runs a model. Schema
checks cannot authenticate annotators, model identities or candidate blindness.
No fixture data is shipped as a research benchmark.
"""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit

PROTOCOL = 'mideval-equity-social-selection-v3'
LABELS = ('positive', 'neutral', 'negative')
ANNOTATION_LABELS = (*LABELS, 'exclude')
ANNOTATION_METHODS = ('two_independent_humans', 'model_generated')


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamps must be ISO UTC strings')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError('timestamps must explicitly use UTC')
    return parsed


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def annotation_input(post):
    """The exact blinded input: target equity and original text, never predictions."""
    return {'ticker': post['ticker'], 'text': post['text']}


def _model_runs(selection, acquired):
    runs = selection.get('annotation_runs')
    if not isinstance(runs, list) or not 1 <= len(runs) <= 2:
        raise ValueError('declare one AI annotation run and at most one optional cross-check')
    by_id = {}
    for run in runs:
        required = ('run_id', 'provider', 'model_id', 'identity_source', 'identity_evidence',
                    'prompt_version', 'prompt', 'prompt_sha256', 'raw_output_reference')
        if not isinstance(run, dict) or not all(_text(run.get(key)) for key in required):
            raise ValueError('AI annotations require actual declared model/provider/prompt/run provenance')
        if run['run_id'] in by_id:
            raise ValueError('annotation run identifiers must be distinct')
        if run['identity_source'] not in ('provider_reported', 'session_configuration', 'operator_declared'):
            raise ValueError('record the source of the model identity without claiming authentication')
        if 'model_revision' not in run or run['model_revision'] is not None and not _text(run['model_revision']):
            raise ValueError('record model_revision, explicitly null when unavailable')
        if run['prompt_sha256'] != hashlib.sha256(run['prompt'].encode()).hexdigest():
            raise ValueError('AI annotation prompt hash does not match the retained prompt')
        if run.get('input_contract') != 'ticker_and_original_text_v1' or run.get('candidate_predictions_visible') is not False:
            raise ValueError('declare target/text-only AI input and no candidate prediction exposure')
        started, completed = _timestamp(run['run_started_utc']), _timestamp(run['run_completed_utc'])
        if not acquired <= started <= completed:
            raise ValueError('AI annotation execution must follow acquisition')
        by_id[run['run_id']] = run
    return by_id


def _model_labels(post, runs):
    annotations = post.get('model_annotations')
    if any(key.startswith('annotator_') or key.startswith('annotated_') for key in post):
        raise ValueError('model-generated labels must not masquerade as human annotations')
    if not isinstance(annotations, list) or len(annotations) != len(runs):
        raise ValueError('retain one initial annotation for every declared AI run and post')
    labels, times, seen = [], [], set()
    for item in annotations:
        if (not isinstance(item, dict) or item.get('run_id') not in runs or item['run_id'] in seen
                or item.get('label') not in ANNOTATION_LABELS
                or not all(_text(item.get(key)) for key in ('reason', 'raw_response'))):
            raise ValueError('retain distinct initial AI labels, reasons and raw responses')
        seen.add(item['run_id'])
        run = runs[item['run_id']]
        if item.get('input_sha256') != digest(annotation_input(post)):
            raise ValueError('AI annotation input hash differs from original target/text')
        annotated = _timestamp(item['annotated_at_utc'])
        if not _timestamp(run['run_started_utc']) <= annotated <= _timestamp(run['run_completed_utc']):
            raise ValueError('per-post annotation timestamp must fall inside its run')
        try:
            raw = json.loads(item['raw_response'])
        except (TypeError, ValueError):
            raise ValueError('retain the actual structured AI label response') from None
        if not isinstance(raw, dict) or raw.get('label') != item['label'] or raw.get('reason') != item['reason']:
            raise ValueError('initial AI label/reason contradicts its retained raw response')
        labels.append((item['run_id'], item['label']))
        times.append(annotated)
    return [dict(labels)[key] for key in runs], times


def _reference_label(post, labels, times):
    adjudicated = post.get('adjudicated_label')
    if len(set(labels)) > 1:
        if adjudicated not in ANNOTATION_LABELS or not _text(post.get('adjudication_note')):
            raise ValueError('resolve disagreements with an explicit label and documented adjudication')
        if _timestamp(post['adjudicated_at_utc']) < max(times):
            raise ValueError('adjudication must follow all initial annotations')
        if not _text(post.get('adjudicator_id')):
            raise ValueError('AI cross-check disagreements require an explicitly declared adjudicator')
        return adjudicated
    if adjudicated not in (None, labels[0]):
        raise ValueError('adjudication cannot silently override unanimous initial labels')
    return labels[0]


def validate_benchmark(data: dict) -> list[dict]:
    if not isinstance(data, dict) or data.get('protocol') != PROTOCOL:
        raise ValueError('benchmark must declare the social-selection protocol')
    selection = data.get('selection', {})
    if not isinstance(selection, dict):
        raise ValueError('selection must be an object with declared provenance')
    if not all(_text(selection.get(key)) for key in ('sampling_rule', 'access_conditions_reference')):
        raise ValueError('record sampling rules and source access/license conditions')
    method = selection.get('annotation_method')
    if method not in ANNOTATION_METHODS:
        raise ValueError('declare a supported human or model-generated annotation method')
    tickers = selection.get('target_tickers')
    if not isinstance(tickers, list) or not tickers or not all(_text(ticker) for ticker in tickers):
        raise ValueError('predeclare target equity identifiers')
    start, end = _timestamp(selection['window_start_utc']), _timestamp(selection['window_end_utc'])
    declared, acquired = _timestamp(selection['declared_at_utc']), _timestamp(selection['acquired_at_utc'])
    if start > end or declared > acquired:
        raise ValueError('invalid time window or sampling declared after acquisition')
    runs = _model_runs(selection, acquired) if method == 'model_generated' else None
    if method == 'two_independent_humans' and 'annotation_runs' in selection:
        raise ValueError('human and AI annotation provenance must not be mixed under one method')
    posts = data.get('posts')
    if not isinstance(posts, list) or len(posts) < 200:
        raise ValueError('at least 200 acquired posts are required; do not synthesize missing data')
    identifiers, contents, usable = set(), set(), []
    for post in posts:
        if not isinstance(post, dict) or not all(_text(post.get(key)) for key in
                ('post_id', 'source', 'source_url', 'ticker', 'text')):
            raise ValueError('post provenance and original content are required')
        if post.get('source_kind') not in ('reddit', 'stocktwits', 'x', 'other_social'):
            raise ValueError('benchmark inputs must be declared social posts, not news headlines')
        url = urlsplit(post['source_url'])
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
            raise ValueError('source_url must be an ordinary public source reference')
        if post['ticker'] not in tickers:
            raise ValueError('target equity mismatch')
        published = _timestamp(post['published_at_utc'])
        if not start <= published <= end or published > acquired:
            raise ValueError('post publication is outside the predeclared window/acquisition time')
        content = (post['ticker'], ' '.join(post['text'].split()).casefold())
        if post['post_id'] in identifiers or content in contents:
            raise ValueError('deduplicate identifiers and repeated target-equity content before splitting')
        identifiers.add(post['post_id'])
        contents.add(content)
        if runs is not None:
            labels, times = _model_labels(post, runs)
            gold = _reference_label(post, labels, times)
        else:
            if (not all(_text(post.get(key)) for key in ('annotator_a_id', 'annotator_b_id'))
                    or post['annotator_a_id'] == post['annotator_b_id'] or 'model_annotations' in post):
                raise ValueError('retain separate declared human annotator identities')
            a, b = post.get('annotator_a_label'), post.get('annotator_b_label')
            if a not in ANNOTATION_LABELS or b not in ANNOTATION_LABELS:
                raise ValueError('both initial human labels must be retained')
            times = [_timestamp(post[field]) for field in ('annotated_a_at_utc', 'annotated_b_at_utc')]
            if min(times) < acquired:
                raise ValueError('annotation timestamp precedes acquisition')
            adjudicated = post.get('adjudicated_label')
            if a != b:
                if adjudicated not in ANNOTATION_LABELS or not _text(post.get('adjudication_note')):
                    raise ValueError('resolve disagreements with an explicit label and documented adjudication')
                if _timestamp(post['adjudicated_at_utc']) < max(times):
                    raise ValueError('adjudication must follow both initial annotations')
                gold = adjudicated
            else:
                if adjudicated not in (None, a):
                    raise ValueError('adjudication cannot silently override unanimous initial labels')
                gold = a
        if gold == 'exclude':
            if not _text(post.get('exclusion_reason')):
                raise ValueError('excluded posts require a reason')
        else:
            if _text(post.get('exclusion_reason')):
                raise ValueError('an excluded post cannot also enter the usable benchmark')
            usable.append(dict(post, gold_label=gold))
    if len(usable) < 10:
        raise ValueError('insufficient usable adjudicated posts after exclusions')
    return sorted(usable, key=lambda post: (_timestamp(post['published_at_utc']), post['post_id']))


def annotation_agreement(posts, method='two_independent_humans', run_ids=None):
    if method == 'model_generated':
        run_ids = run_ids or [item['run_id'] for item in posts[0]['model_annotations']]
        if len(run_ids) == 1:
            return {'initial_exact_agreement': None, 'initial_disagreements': None, 'cohens_kappa': None,
                    'note': 'Single AI pass; no cross-check agreement or independent human validation measured.'}
        pairs = [{item['run_id']: item['label'] for item in post['model_annotations']} for post in posts]
        posts = [{'annotator_a_label': pair[run_ids[0]], 'annotator_b_label': pair[run_ids[1]]} for pair in pairs]
    count = len(posts)
    observed = sum(post['annotator_a_label'] == post['annotator_b_label'] for post in posts) / count
    a = Counter(post['annotator_a_label'] for post in posts)
    b = Counter(post['annotator_b_label'] for post in posts)
    chance = sum(a[label] * b[label] for label in ANNOTATION_LABELS) / count**2
    return {'initial_exact_agreement': observed, 'initial_disagreements': round(count * (1 - observed)),
            'cohens_kappa': (observed - chance) / (1 - chance) if chance < 1 else None,
            'note': ('AI pass agreement, not independent human reliability. ' if method == 'model_generated' else '')
                    + 'Initial labels before adjudication; excludes are included as a fourth annotation label. Homogeneous-label kappa is undefined.'}


def freeze_plan(data: dict, checkpoints: list[dict], *, frozen_utc: str | None = None) -> dict:
    posts = validate_benchmark(data)
    if not isinstance(checkpoints, list) or len(checkpoints) < 2:
        raise ValueError('declare at least two actual candidate checkpoints and preprocessing rules')
    for item in checkpoints:
        if (not isinstance(item, dict) or set(item) != {'model_id', 'revision', 'preprocessing'}
                or not all(_text(value) for value in item.values())
                or len(item['revision']) != 40 or any(c not in '0123456789abcdef' for c in item['revision'])):
            raise ValueError('checkpoint requires model_id, exact 40-character revision and preprocessing')
    identities = {(item['model_id'], item['revision']) for item in checkpoints}
    if len(identities) != len(checkpoints):
        raise ValueError('candidate checkpoints must be distinct')
    frozen = frozen_utc or datetime.now(timezone.utc).isoformat()
    if any(_timestamp(post[field]) > _timestamp(frozen) for post in data['posts']
           for field in ('annotated_a_at_utc', 'annotated_b_at_utc', 'adjudicated_at_utc') if post.get(field) is not None):
        raise ValueError('plan cannot precede supplied annotations')
    method = data['selection']['annotation_method']
    runs = data['selection'].get('annotation_runs', []) if method == 'model_generated' else []
    if any(_timestamp(run['run_completed_utc']) > _timestamp(frozen) for run in runs):
        raise ValueError('plan cannot precede completed AI annotation runs')
    annotations = [{key: run[key] for key in ('run_id', 'provider', 'model_id', 'model_revision', 'identity_source',
                    'identity_evidence', 'prompt_version', 'prompt_sha256', 'candidate_predictions_visible')} for run in runs]
    overlap = [{'annotation_run_id': run['run_id'], 'candidate_model_id': item['model_id'],
                'candidate_revision': item['revision'], 'annotation_revision': run['model_revision']}
               for run in runs for item in checkpoints if run['model_id'].casefold() == item['model_id'].casefold()]
    split = 4 * len(posts) // 5
    return {'protocol': PROTOCOL, 'frozen_utc': frozen, 'benchmark_sha256': digest(data),
            'evaluator_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'inference_source_sha256': hashlib.sha256(Path(__file__).with_name('sentiment_inference.py').read_bytes()).hexdigest(),
            'split_rule': 'Chronological first floor(4*N/5) usable posts development; remainder held out',
            'development_post_ids': [post['post_id'] for post in posts[:split]],
            'heldout_post_ids': [post['post_id'] for post in posts[split:]],
            'candidate_checkpoints': checkpoints, 'acquired_posts': len(data['posts']),
            'usable_posts': len(posts), 'excluded_posts': len(data['posts']) - len(posts),
            'annotation_method': method, 'annotation_models': annotations,
            'annotation_candidate_overlap': overlap,
            'reference_scope': ('Model-generated reference labels; candidate scores measure agreement with AI labels, not independently human-validated accuracy.'
                                if runs else 'Declared human reference labels; identities/independence are not independently authenticated.'),
            'annotation_agreement': annotation_agreement(data['posts'], method, [run['run_id'] for run in runs]),
            'provenance_scope': 'Model/human identities, source rights, candidate blindness and training-corpus overlap are declared, not authenticated by schema checks. No name match does not establish independence.'}


def classification_metrics(actual, predicted):
    matrix = {gold: {label: 0 for label in LABELS} for gold in LABELS}
    for gold, label in zip(actual, predicted, strict=True):
        matrix[gold][label] += 1
    classes = {}
    for label in LABELS:
        true_positive = matrix[label][label]
        support = sum(matrix[label].values())
        called = sum(matrix[gold][label] for gold in LABELS)
        precision = true_positive / called if called else 0.0
        recall = true_positive / support if support else 0.0
        classes[label] = {'precision': precision, 'recall': recall, 'support': support,
                          'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0.0}
    return {'macro_f1': sum(item['f1'] for item in classes.values()) / 3,
            'per_class': classes, 'confusion_matrix_gold_rows': matrix,
            'convention': 'Unweighted macro over all three classes; zero denominators -> zero.'}


def evaluate_predictions(data: dict, plan: dict, predictions: list[dict]) -> dict:
    expected = freeze_plan(data, plan['candidate_checkpoints'], frozen_utc=plan['frozen_utc'])
    if expected != plan:
        raise ValueError('benchmark, code, selection or candidate identities changed after the frozen plan')
    plan_hash = digest(plan)
    heldout = plan['heldout_post_ids']
    gold = {post['post_id']: post['gold_label'] for post in validate_benchmark(data)}
    candidates = {(item['model_id'], item['revision']): item for item in plan['candidate_checkpoints']}
    if not isinstance(predictions, list):
        raise ValueError('model runs must be a list')
    results, seen = [], set()
    for run in predictions:
        fields = {'model_id', 'revision', 'preprocessing', 'plan_sha256', 'benchmark_sha256',
                  'run_started_utc', 'run_completed_utc', 'outputs'}
        if not isinstance(run, dict) or set(run) != fields:
            raise ValueError('model run has missing or unsupported provenance fields')
        identity = (run.get('model_id'), run.get('revision'))
        if identity not in candidates or identity in seen or run.get('preprocessing') != candidates[identity]['preprocessing']:
            raise ValueError('unexpected, duplicate or differently preprocessed model run')
        seen.add(identity)
        if run.get('plan_sha256') != plan_hash or run.get('benchmark_sha256') != plan['benchmark_sha256']:
            raise ValueError('model outputs must name the matching frozen plan and benchmark')
        if _timestamp(run['run_started_utc']) < _timestamp(plan['frozen_utc']) or _timestamp(run['run_completed_utc']) < _timestamp(run['run_started_utc']):
            raise ValueError('model execution must follow plan freezing')
        rows = run.get('outputs')
        if not isinstance(rows, list):
            raise ValueError('retain per-post outputs, including failures')
        by_id = {}
        errors = 0
        for row in rows:
            if not isinstance(row, dict) or row.get('post_id') not in heldout or row['post_id'] in by_id:
                raise ValueError('unknown/development/duplicate post in held-out outputs')
            if set(row) == {'post_id', 'error'} and _text(row['error']):
                errors += 1
                by_id[row['post_id']] = None
                continue
            if set(row) != {'post_id', 'probabilities'}:
                raise ValueError('each output requires probabilities or an explicit failure')
            probabilities = row['probabilities']
            if (not isinstance(probabilities, dict) or set(probabilities) != set(LABELS)
                    or any(type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 1 for value in probabilities.values())
                    or abs(sum(probabilities.values()) - 1) > 1e-6):
                raise ValueError('sentiment probabilities must be finite, bounded and sum to one')
            by_id[row['post_id']] = max(LABELS, key=probabilities.get)
        completed = sum(value is not None for value in by_id.values())
        complete = completed == len(heldout)
        results.append({'model_id': identity[0], 'revision': identity[1], 'completed_posts': completed,
                        'error_posts': errors, 'missing_posts': len(heldout) - len(by_id),
                        'coverage': completed / len(heldout), 'status': 'complete' if complete else 'partial',
                        'raw_run_sha256': digest(run),
                        'quality_metrics': classification_metrics([gold[key] for key in heldout], [by_id[key] for key in heldout]) if complete else None})
    complete = len(seen) == len(candidates) and all(result['status'] == 'complete' for result in results)
    leaders = []
    if complete:
        best = max(result['quality_metrics']['macro_f1'] for result in results)
        leaders = sorted(({'model_id': result['model_id'], 'revision': result['revision'], 'macro_f1': best}
                          for result in results if result['quality_metrics']['macro_f1'] == best),
                         key=lambda item: (item['model_id'], item['revision']))
    return {'protocol': PROTOCOL, 'status': 'complete' if complete else 'partial' if results else 'blocked',
            'plan_sha256': plan_hash, 'benchmark_sha256': plan['benchmark_sha256'],
            'heldout_posts': len(heldout), 'annotation_agreement': plan['annotation_agreement'],
            'annotation_method': plan['annotation_method'], 'reference_scope': plan['reference_scope'],
            'annotation_models': plan['annotation_models'], 'annotation_candidate_overlap': plan['annotation_candidate_overlap'],
            'results': results, 'comparison_ready': complete,
            'benchmark_leaders': leaders, 'deployment_selection': None,
            'selection_decision': 'Adequacy threshold, news-only fallback and final selection require predeclared criteria and human review.',
            'raw_model_runs': predictions,
            'limitation': 'A small held-out sentiment selection study does not establish equity-return prediction, significance, suitability or deployment readiness.'}
