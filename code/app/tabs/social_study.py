"""Actual benchmark readiness/comparison, with no invented social evidence."""
import json
from collections import Counter
from pathlib import Path

import streamlit as st

from investify.sentiment_selection import validate_benchmark, annotation_agreement, evaluate_predictions
from investify.generative_sentiment import compare as compare_generative
from investify.sentiment_receipts import compare_bundles

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / 'artifacts/mid_eval'


def read_json(path):
    raw = path.read_bytes()
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError('Study input exceeds the five-megabyte viewer limit')
    def invalid(value):
        raise ValueError(f'Non-finite JSON number: {value}')
    return json.loads(raw, parse_constant=invalid)


def recorded_receipt_comparison(benchmark, parent_plan, pointer):
    """Resolve an explicit recorded study entirely inside the study directory."""
    if (not isinstance(pointer, dict) or set(pointer) != {'schema', 'catalog', 'plan', 'bundles'}
            or pointer['schema'] != 'investify-recorded-social-study-v1'
            or not isinstance(pointer['bundles'], list) or len(pointer['bundles']) != 2):
        raise ValueError('A complete recorded two-candidate study pointer is required')
    def resolve(relative):
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError('Study references must be relative project study paths')
        path = (STUDY / relative).resolve()
        if not path.is_relative_to(STUDY.resolve()) or not path.is_file():
            raise ValueError('Recorded study reference is missing or escapes the study directory')
        return path
    catalog = read_json(resolve(pointer['catalog']))
    receipt_plan = read_json(resolve(pointer['plan']))
    bundles = [read_json(resolve(relative)) for relative in pointer['bundles']]
    return compare_bundles(benchmark, parent_plan, catalog, receipt_plan, bundles)


def render_generative(benchmark, parent_plan, *, classifier_ready=False):
    st.markdown('### Local generative sentiment agreement')
    try:
        plan = read_json(STUDY / 'generative_sentiment_plan.json')
        runs = read_json(STUDY / 'generative_sentiment_runs.json')
        result = compare_generative(benchmark, parent_plan, plan, runs)
    except FileNotFoundError:
        st.info('Supplementary original-publisher model comparison is pending verified official weights and new runs.')
        return
    except (OSError, KeyError, TypeError, ValueError) as error:
        st.error('Supplementary comparison invalid. No local-model agreement score is shown.')
        with st.expander('Supplementary study validation details'):
            st.code(str(error), language=None)
        return
    st.caption('This supplementary generative study is separate from the recorded original-classifier comparison.'
               if classifier_ready else 'Hard-label predictions against the same frozen AI references. The CryptoBERT/Cardiff classifier study remains pending.')
    if any(run.get('execution_kind') == 'unit_fixture' for run in runs):
        st.warning('Explicit unit-fixture inputs are being displayed; these are not actual research outcomes.')
    rows = []
    for item in result['results']:
        metrics = item['quality_metrics']
        rows.append({'model': item['model_id'], 'completed': item['completed_posts'], 'status': item['status'],
                     'macro_F1_agreement': metrics['macro_f1'] if metrics else None,
                     'exact_agreement': item['exact_agreement_rate'], 'errors': item['error_posts'], 'missing': item['missing_posts']})
    if rows:
        st.dataframe(rows, hide_index=True, width='stretch')
    if not result['comparison_ready']:
        st.warning('Complete paired generative comparison is unavailable; partial scores do not establish a winner.')
    st.caption(result['limitation'])
    st.download_button('Download local generative agreement evidence', json.dumps(result, indent=2, allow_nan=False),
                       file_name='generative_sentiment_agreement.json', mime='application/json', key='download_generative_study')


def render():
    st.markdown('## Equity-social sentiment study')
    st.caption('This research view validates supplied benchmark evidence. Social sentiment is absent from the saved classifier.')
    st.write('Compare candidate sentiment models on the same held-out posts using a declared AI or human annotation method, '
             'retained initial labels, documented exclusions and a frozen selection.')
    try:
        benchmark = read_json(STUDY / 'social_benchmark.json')
        usable = validate_benchmark(benchmark)
    except FileNotFoundError:
        st.info('Social benchmark pending. No completed annotated corpus has been supplied to this study view.')
        st.caption('Prepared validators and unit fixtures are not social-model study results.')
        return
    except (OSError, KeyError, TypeError, ValueError) as error:
        st.error('Social benchmark invalid. No sentiment-model quality score is shown.')
        with st.expander('Benchmark validation details'):
            st.code(str(error), language=None)
        return
    method = benchmark['selection']['annotation_method']
    agreement = annotation_agreement(benchmark['posts'], method,
                  [run['run_id'] for run in benchmark['selection'].get('annotation_runs', [])])
    cols = st.columns(3)
    cols[0].metric('Supplied acquired posts', len(benchmark['posts']))
    cols[1].metric('Usable reference posts', len(usable))
    value = agreement['initial_exact_agreement']
    cols[2].metric('Initial exact agreement', f'{value:.1%}' if value is not None else 'Not measured')
    if method == 'model_generated':
        st.warning('Model-generated reference labels. Candidate scores measure agreement with AI labels; independent human validation is unmeasured.')
        st.write('Annotation model(s): ' + ', '.join(f"{r['provider']} / {r['model_id']} ({r['identity_source']})"
                 for r in benchmark['selection']['annotation_runs']))
    counts = Counter(post['gold_label'] for post in usable)
    st.write('Usable reference labels: ' + ', '.join(f'{label}: {counts[label]}' for label in ('positive', 'neutral', 'negative'))
             + f". Excluded posts: {len(benchmark['posts']) - len(usable)}.")
    st.caption(agreement['note'])
    st.caption('Annotation identities, source rights and candidate blindness are declared; schema checks cannot authenticate them.')
    try:
        plan = read_json(STUDY / 'social_selection_plan.json')
        runs = read_json(STUDY / 'social_model_runs.json')
        fixture = benchmark['selection'].get('study_purpose') == 'unit_test'
        if fixture:
            st.warning('Explicit unit-fixture study view. These metrics are not actual candidate research outcomes.')
        if not fixture:
            try:
                bundles = read_json(STUDY / 'social_model_bundles_v4.json')
            except FileNotFoundError:
                bundles = []
            try:
                pointer = read_json(STUDY / 'social_latest_study.json')
            except FileNotFoundError:
                pointer = None
            if pointer is not None:
                result = recorded_receipt_comparison(benchmark, plan, pointer)
                st.caption('Recorded original-publisher inference: the displayed metrics are recomputed from hash-bound output/receipt bundles; no model runs in this viewer.')
            elif bundles:
                receipt_plan = read_json(STUDY / 'social_receipt_plan_v4.json')
                catalog = read_json(STUDY / 'social_publisher_catalog_v4.json')
                result = compare_bundles(benchmark, plan, catalog, receipt_plan, bundles)
            elif runs:
                raise ValueError('Standalone candidate probabilities have no verified V4 run/receipt bundle; no research score')
            else:
                result = evaluate_predictions(benchmark, plan, [])
        else:
            result = evaluate_predictions(benchmark, plan, runs)
    except FileNotFoundError:
        st.info('Held-out model comparison pending. The frozen plan and actual candidate outputs are required.')
        return
    except (OSError, KeyError, TypeError, ValueError) as error:
        st.error('Study plan or model outputs invalid. No comparison or automatic selection is shown.')
        with st.expander('Study validation details'):
            st.code(str(error), language=None)
        return
    st.write(f"Held-out posts: {result['heldout_posts']}. Status: {result['status']}.")
    if result['heldout_posts'] < 40:
        st.warning('Fewer than 40 usable held-out posts. Treat any class-level comparison as exploratory.')
    if result['annotation_candidate_overlap']:
        st.warning('An annotation model identity matches a candidate. Shared-model evaluation may inflate agreement.')
    rows = []
    for candidate in result['results']:
        metrics = candidate['quality_metrics']
        rows.append({'model': candidate['model_id'], 'revision': candidate['revision'], 'status': candidate['status'],
                     'coverage': candidate['coverage'], 'macro_F1': metrics['macro_f1'] if metrics else None,
                     'missing': candidate['missing_posts'], 'errors': candidate['error_posts']})
    if rows:
        st.dataframe(rows, hide_index=True, width='stretch')
    if not result['comparison_ready']:
        st.warning('Paired comparison unavailable. Failed or missing outputs are retained; they are not neutral predictions.')
    else:
        st.write('Benchmark leaders: ' + ', '.join(item['model_id'] for item in result['benchmark_leaders']))
    st.caption(result['selection_decision'])
    st.caption(result['limitation'])
    st.download_button('Download study comparison evidence', json.dumps(result, indent=2, allow_nan=False),
                       file_name='social_selection_results.json', mime='application/json', key='download_social_study')
    render_generative(benchmark, plan, classifier_ready=result['comparison_ready'])
