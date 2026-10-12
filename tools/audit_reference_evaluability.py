"""Audit frozen AI references, split overlap and comparator interpretation.

No model requests, reference changes or candidate predictions are made.
Similarity thresholds are declared here before computing this diagnostic.
"""
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code/src'))
from investify.sentiment_selection import validate_benchmark, digest, classification_metrics

JACCARD_THRESHOLD = 0.8
MIN_DISTINCT_TOKENS = 5


def tokens(text):
    # Diagnostic fingerprints only. Original annotation/inference text is unchanged.
    text = re.sub(r'https?://\S+', ' URL ', text.lower())
    return set(re.findall(r'[a-z0-9]+', text))


def counts(rows):
    observed = Counter(row['gold_label'] for row in rows)
    return {label: observed[label] for label in ('positive', 'neutral', 'negative')}


def main():
    benchmark_path = ROOT / 'code/artifacts/mid_eval/social_benchmark.json'
    plan_path = ROOT / 'code/artifacts/mid_eval/social_selection_plan.json'
    before = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in (benchmark_path, plan_path)}
    benchmark = json.loads(benchmark_path.read_text(encoding='utf-8'))
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if plan['benchmark_sha256'] != digest(benchmark): raise ValueError('Benchmark differs from original freeze')
    usable = validate_benchmark(benchmark)
    by_id = {row['post_id']: row for row in usable}
    development = [by_id[key] for key in plan['development_post_ids']]
    heldout = [by_id[key] for key in plan['heldout_post_ids']]
    if len(development) + len(heldout) != len(usable) or set(plan['development_post_ids']) & set(plan['heldout_post_ids']):
        raise ValueError('Original split identities overlap or omit usable posts')
    if max(row['published_at_utc'] for row in development) > min(row['published_at_utc'] for row in heldout):
        raise ValueError('Development posts are later than the original held-out boundary')
    development_ids = set(plan['development_post_ids'])
    fingerprints = {row['post_id']: tokens(row['text']) for row in usable}
    flagged = []
    for left, right in combinations(usable, 2):
        a, b = fingerprints[left['post_id']], fingerprints[right['post_id']]
        if min(len(a), len(b)) < MIN_DISTINCT_TOKENS: continue
        similarity = len(a & b) / len(a | b)
        if similarity >= JACCARD_THRESHOLD:
            flagged.append({'left_post_id': left['post_id'], 'right_post_id': right['post_id'],
                            'token_jaccard': similarity,
                            'cross_split': (left['post_id'] in development_ids) != (right['post_id'] in development_ids),
                            'same_reference_label': left['gold_label'] == right['gold_label'],
                            'left_published_utc': left['published_at_utc'], 'right_published_utc': right['published_at_utc']})
    dev_counts = counts(development)
    # Select the deterministic majority label from development only.
    majority = max(dev_counts, key=lambda label: (dev_counts[label], label))
    gold = [row['gold_label'] for row in heldout]
    baseline = classification_metrics(gold, [majority] * len(gold))
    result = {'schema': 'investify-ai-reference-evaluability-v1', 'checked_utc': datetime.now(timezone.utc).isoformat(),
              'benchmark_sha256': digest(benchmark), 'parent_plan_sha256': digest(plan), 'source_files_sha256': before,
              'audit_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'usable_posts': len(usable), 'excluded_posts': len(benchmark['posts']) - len(usable),
              'development': {'posts': len(development), 'counts': dev_counts},
              'heldout': {'posts': len(heldout), 'counts': counts(heldout)},
              'same_calendar_dates_across_split': sorted({row['published_at_utc'][:10] for row in development}
                                                       & {row['published_at_utc'][:10] for row in heldout}),
              'reference_agreement_granularity': {'one_post_exact_agreement_step': 1 / len(heldout),
                  'per_class_recall_steps': {label: 1 / count if count else None for label, count in counts(heldout).items()}},
              'development_majority_reference_comparator': {'selected_label': majority,
                  'selection_uses_heldout_labels': False, 'metrics': baseline,
                  'scope': 'Deterministic development-majority comparator against AI references; not a candidate-model inference result or human-validated accuracy.'},
              'similarity_diagnostic': {'normalization': 'Lowercase; URLs replaced by URL token; sets of ASCII word/number tokens; diagnostic only.',
                  'minimum_distinct_tokens': MIN_DISTINCT_TOKENS, 'jaccard_threshold': JACCARD_THRESHOLD,
                  'flagged_pairs': flagged, 'cross_split_pairs': sum(pair['cross_split'] for pair in flagged),
                  'scope': 'Heuristic review flags, not authenticated duplicate/news-event groups, independent observations or proof of pretraining leakage. Short posts below threshold are not assessed.'},
              'reference_or_split_modified': False, 'candidate_inference_executed': False,
              'independent_human_validation': False, 'statistical_independence_established': False}
    if before != {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (benchmark_path, plan_path)}:
        raise ValueError('Frozen benchmark or plan changed during this audit')
    output = ROOT / 'evidence/reference_evaluability_20261012.json'
    output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(f"Audited {len(usable)} frozen references; {len(flagged)} similarity flags; {result['similarity_diagnostic']['cross_split_pairs']} across split")
    print('Development-majority reference comparator:', majority, baseline)


if __name__ == '__main__': main()
