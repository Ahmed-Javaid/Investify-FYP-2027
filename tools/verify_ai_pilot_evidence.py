"""Audit actual corpus/source/raw-label/freeze identities without generating data."""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code/src'))
sys.path.insert(0, str(ROOT / 'code/scripts'))
# These imports use the explicit checkout paths above, not an installed package.
from investify.sentiment_selection import digest, validate_benchmark, freeze_plan, classification_metrics  # noqa: E402
from investify.sentiment_annotation import attach_session_annotations  # noqa: E402
from prepare_stocknet_pilot import prepare  # noqa: E402


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path,
                    default=ROOT / 'evidence/social_pilot/reference_evidence_verification.json')
parser.add_argument('--saved-only', action='store_true', help='Check retained corpus/labels without external raw acquisition inputs')
args = parser.parse_args()
output = args.output.resolve()
if not output.is_relative_to(ROOT / 'evidence'):
    raise ValueError('AI-reference replay receipts must remain under project evidence')

pilot = ROOT / 'evidence/social_pilot'
source = ROOT / 'sources/stocknet'
if args.saved_only:
    corpus = read(pilot / 'msft_stocknet_unannotated.json')
    source_receipt = None
else:
    corpus, source_receipt = prepare(read(ROOT / 'deliverables/stocknet_source_access_v2.json'),
                                    read(source / 'acquisition_manifest.json'), source)
if corpus != read(pilot / 'msft_stocknet_unannotated.json'):
    raise ValueError('Actual corpus does not reproduce from original preserved source files')
receipt = read(pilot / 'annotation_freeze_receipt.json')
benchmark, imported = attach_session_annotations(corpus, read(pilot / 'annotation_run_completed.json'),
                                                sorted(pilot.glob('raw_labels_batch_*.json')),
                                                batch_receipts=receipt['raw_batches'])
saved = read(ROOT / 'code/artifacts/mid_eval/social_benchmark.json')
if saved != benchmark:
    raise ValueError('Benchmark changed from original text or retained raw AI output batches')
if receipt['benchmark_sha256'] != digest(saved) or receipt['raw_batches'] != imported['raw_batches']:
    raise ValueError('Original raw-label file identities/timestamps or annotation freeze changed')
plan = read(ROOT / 'code/artifacts/mid_eval/social_selection_plan.json')
if plan != freeze_plan(saved, read(ROOT / 'code/artifacts/mid_eval/social_candidates.json'), frozen_utc=plan['frozen_utc']):
    raise ValueError('Frozen study plan no longer matches benchmark/source/candidate identities')
if datetime.fromisoformat(receipt['frozen_utc']) > datetime.fromisoformat(plan['frozen_utc']):
    raise ValueError('Candidate plan predates actual label freeze')
usable = validate_benchmark(saved)
heldout = {post['post_id']: post['gold_label'] for post in usable if post['post_id'] in plan['heldout_post_ids']}
actual = [heldout[key] for key in plan['heldout_post_ids']]
checks = {'source_git_blobs': len(source_receipt['source_files']) if source_receipt else None,
          'original_acquisition_inputs_replayed': not args.saved_only, 'selected_original_posts': len(corpus['posts']),
          'raw_batches': len(imported['raw_batches']), 'complete_input_bound_ai_annotations': len(benchmark['posts']),
          'benchmark_and_plan_match': True, 'labels_frozen_before_candidate_plan': True}
report = {'checked_utc': datetime.now(timezone.utc).isoformat(),
          'status': 'saved_reference_evidence_verified' if args.saved_only else 'actual_reference_evidence_verified',
          'checks': checks, 'benchmark_sha256': digest(saved), 'plan_sha256': digest(plan),
          'annotation_method': 'model_generated', 'usable_posts': len(usable), 'excluded_posts': len(saved['posts']) - len(usable),
          'reference_labels': dict(Counter(post['gold_label'] for post in usable)),
          'development_posts': len(plan['development_post_ids']), 'heldout_posts': len(actual),
          'heldout_labels': dict(Counter(actual)), 'annotation_agreement': plan['annotation_agreement'],
          'majority_neutral_reference_comparator': classification_metrics(actual, ['neutral'] * len(actual)),
          'actual_candidate_runs': len(read(ROOT / 'code/artifacts/mid_eval/social_model_runs.json')),
          'candidate_quality_metrics': None, 'independent_human_validation': False,
          'scope': 'Actual saved source/reference consistency audit, not independent verification of labels, serving-model identity, source rights or model performance.'}
output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
print(f'Verified {len(corpus["posts"])} actual source posts, {len(usable)} usable AI references, source/raw-label/freeze identities; no candidate inference')
