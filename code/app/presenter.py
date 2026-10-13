"""One visible workspace at a time. Interactions reuse the verified core modules."""
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import streamlit as st

from app import presenter_data as data
from investify.explain.context import build_context
from investify.explain.template import Explanation, render, render_guided
from investify.explain.pipeline import emit
from investify.risk_profile_gl import CAPACITY_OPTIONS, GL_ITEMS, score_profile, example_answers, apply_risk_policy

PAGES = ('Overview', 'Walkthrough', 'Experiments', 'Design')
STEPS = ('Decision', 'Evidence', 'Risk profile', 'Explanation check')
ASSETS = Path(__file__).parent / 'assets'

def navigate(page, step=None):
    if page not in PAGES:
        raise ValueError('Unknown workspace')
    st.session_state['ui_page'] = page
    if step is not None:
        if step not in STEPS:
            raise ValueError('Unknown walkthrough step')
        st.session_state['ui_step'] = step

def profile_example(index):
    st.session_state['ui_profile_epoch'] = st.session_state.get('ui_profile_epoch', 0) + 1
    values = {'horizon':'5+ years','buffer':'6+ months','stability':'Salaried and stable','dependants':'0','age':'18-30'}
    for key, value in values.items():
        st.session_state['ui_profile_' + key] = value
    answers = example_answers(index)
    for i, (_, options, _) in enumerate(GL_ITEMS):
        st.session_state[f'ui_tolerance_{i}'] = options[answers[i]]
    st.session_state['ui_profile'] = score_profile(values, answers)
    st.session_state['ui_profile_kind'] = 'Fictional example: cautious' if index == 0 else 'Fictional example: higher tolerance'

def clear_profile():
    st.session_state['ui_profile_epoch'] = st.session_state.get('ui_profile_epoch', 0) + 1
    for name in CAPACITY_OPTIONS:
        st.session_state['ui_profile_' + name] = None
    for i in range(len(GL_ITEMS)):
        st.session_state[f'ui_tolerance_{i}'] = None
    st.session_state.pop('ui_profile', None)
    st.session_state.pop('ui_profile_kind', None)

def choose_case():
    with st.expander('Case selection', expanded=False):
        source = st.selectbox('Recorded experiment', list(data.SOURCES),
            format_func=lambda key:data.SOURCES[key][0], key='ui_source')
        try:
            collection = data.load_cases(source)
        except (OSError,KeyError,TypeError,ValueError) as error:
            st.error('Recorded evidence unavailable. No replacement decision is shown.')
            st.caption(str(error))
            return None, None
        sessions = sorted(collection.records)
        if st.session_state.get('ui_session') not in sessions:
            st.session_state['ui_session'] = sessions[-1]
        selected = st.selectbox('Session', sessions, key='ui_session')
        st.caption('This selection loads saved model evidence. It does not fetch or train a model.')
    return collection, collection.records[selected]

def case_caption(collection, record):
    st.caption(f'{record.ticker} / {record.session_date} / {record.horizon_days} trading sessions / {data.SOURCES[collection.source][0]}')

def overview():
    st.markdown('<div class="eyebrow">FYP-1 mid evaluation</div>', unsafe_allow_html=True)
    st.title('A decision you can inspect')
    st.markdown('<p class="summary">Explore one recorded equity decision, see the evidence behind it, and test whether its explanation matches the facts.</p>', unsafe_allow_html=True)
    st.button('Open the decision walkthrough', type='primary', key='ui_begin', on_click=navigate, args=('Walkthrough','Decision'))
    st.divider()
    left, right = st.columns([3,2], gap='large')
    with left:
        st.subheader('The live demonstration')
        st.write('A complete risk profile controls the confidence required for a directional suggestion. An incorrect explanation triggers rejection and checked fallback. Recorded probabilities remain fixed.')
        st.caption('Suggested case: Alpaca multiclass calibration, frozen classifier, 21 December 2023.')
    with right:
        st.subheader('Recorded research')
        st.write('Inspect the leakage experiment, original sentiment-model comparison and teacher construction pilot.')
        st.button('Explore experiments', key='ui_open_experiments', on_click=navigate, args=('Experiments',))
        st.button('View architecture and requirements', key='ui_open_design', on_click=navigate, args=('Design',))
    st.markdown('<div class="quiet-note">The predictor has no established useful signal. Multiclass calibration preserves varied raw classes, but nearly uniform probabilities require abstention.</div>', unsafe_allow_html=True)

def decision_view(collection, record):
    st.header('Recorded decision')
    case_caption(collection, record)
    left, right = st.columns([1,2], gap='large')
    with left:
        st.metric('Model class', record.decision)
        st.metric('Calibrated probability', f'{record.confidence:.1%}')
        st.caption('Largest recorded class probability, not an expected return or a suitability guarantee.')
    with right:
        probs = pd.DataFrame({'class':list(record.probabilities),'probability':list(record.probabilities.values())})
        st.bar_chart(probs, x='class', y='probability', horizontal=True, height=210, color='#267b86')
    if collection.source.startswith('temperature_'):
        if record.confidence < .5:
            st.warning('Insufficient predictive confidence: no directional recommendation. The raw class is shown for diagnosis.')
        with st.expander('Multiclass calibration and abstention'):
            diagnosis = data.temperature_diagnosis(collection)
            st.write('One positive temperature scales all three margins, preserving the raw class order. It is fitted only on 181 earlier calibration outcomes.')
            st.json({'temperature': diagnosis['fit']['temperature'], 'class_counts': diagnosis['temperature']['class_counts'],
                     'macro_f1': diagnosis['temperature']['macro_f1'], 'brier': diagnosis['temperature']['brier']})
            st.caption('The fit reaches the configured upper bound and probabilities approach one-third. Calibration does not create predictive information.')
    else:
        st.markdown('<div class="quiet-note">This preserved isotonic experiment emits Buy throughout. It is retained as the diagnosed failure, not the active recommendation path.</div>', unsafe_allow_html=True)
    if collection.source in ('fresh_frozen', 'fresh_refit'):
        with st.expander('Why the fresh calibration always chooses Buy'):
            try:
                diagnosis = data.calibration_diagnosis(collection)
                bounds = diagnosis['calibrator_global_bounds']
                floor = bounds['Buy']['minimum']
                ceiling = max(bounds[c]['maximum'] for c in ('Hold', 'Sell'))
                st.write(f'The saved Buy map never outputs below {floor:.4f}, while Hold and Sell never output above {ceiling:.4f}. Dividing all three outputs by the same positive total preserves their ranking. These fixed maps therefore always rank Buy first.')
                st.caption('These bounds describe map outputs before normalization, not the final class probabilities. The result applies to these fresh maps only. Useful prediction remains unestablished.')
            except (OSError, KeyError, TypeError, ValueError) as error:
                st.info('Calibration diagnosis unavailable for this evidence identity.')
                st.caption(str(error))
    st.subheader('Largest recorded contributions')
    context = build_context(record, corpus=collection.source)
    labels = {r['feature']:r['label'] for r in context['features']}
    rows = [{'Feature':labels.get(c.name,c.name),'Raw-score contribution':round(c.shap_value,4),'Effect':c.direction} for c in record.top_k]
    st.dataframe(rows, hide_index=True, width='stretch')
    st.caption('TreeSHAP describes the raw model score. It does not explain an economic cause or the calibrated probability.')

def evidence_view(collection, record):
    st.header('Evidence behind the decision')
    case_caption(collection, record)
    context = build_context(record, corpus=collection.source)
    family = st.radio('Evidence family', ['Technical analysis','News sentiment'], horizontal=True, key='ui_family')
    rows = [r for r in context['features'] if r['family'].lower() == family.lower()]
    if not rows:
        st.info('This evidence family has no supplied feature values.')
        return
    if st.session_state.get('ui_feature') not in [r['feature'] for r in rows]:
        st.session_state['ui_feature'] = rows[0]['feature']
    selected = st.selectbox('Inspect a feature', [r['feature'] for r in rows], format_func=lambda name:next(r['label'] for r in rows if r['feature']==name), key='ui_feature')
    feature = next(r for r in rows if r['feature']==selected)
    left, right = st.columns([1,2], gap='large')
    with left:
        st.metric(feature['label'], f"{feature['value']:.4g}" if feature['value_available'] else 'Missing')
        st.metric('Raw-score contribution', f"{feature['shap_value']:+.4f}")
    with right:
        st.subheader('What this input means')
        st.write(feature['meaning'])
        st.caption(feature['effect_on_predicted_class'] + ' the recorded ' + record.decision + ' class.')
    st.caption('News features come from headlines. The separate social study is absent from this classifier.')
    with st.expander('All eleven feature values and definitions'):
        st.dataframe([{'Feature':r['label'],'Family':r['family'],'Value':r['value'] if r['value_available'] else None,'Contribution':r['shap_value']} for r in context['features']], hide_index=True, width='stretch')
        for r in context['features']:
            st.write(r['label'] + ': ' + r['meaning'])
        st.caption(context['data_status'])
    with st.expander('Record provenance and raw evidence'):
        st.json({'artifact_sha256':collection.sha256,'model':record.model_version,'seed':record.seed,'record':record.to_dict()})

def profile_view(collection, record):
    st.header('Risk capacity and tolerance')
    st.write('The profile sets a risk allowance and confidence requirement. It does not reweight news or reverse the model direction.')
    actions = st.columns([1, 1, 1])
    actions[0].button('Cautious example', key='ui_cautious', on_click=profile_example, args=(0,))
    actions[1].button('Higher-tolerance example', key='ui_tolerant', on_click=profile_example, args=(2,))
    actions[2].button('Clear profile', key='ui_clear_profile', on_click=clear_profile)
    if st.session_state.get('ui_profile_kind'):
        st.caption(st.session_state['ui_profile_kind'] + '. Fictional demonstration answers.')
    with st.expander('Complete the five capacity and thirteen tolerance answers'):
        st.caption('Grable-Lytton item scoring uses concise paraphrases. No unanswered choice is defaulted.')
        with st.form('ui_profile_form'):
            columns = st.columns(2)
            labels = {'horizon': 'When will you need this money?', 'buffer': 'Emergency expenses buffer',
                      'stability': 'Income stability', 'dependants': 'Financial dependants', 'age': 'Age band'}
            capacity = {}
            for i, (name, choices) in enumerate(CAPACITY_OPTIONS.items()):
                capacity[name] = columns[i % 2].selectbox(labels[name], list(choices), index=None, key='ui_profile_' + name)
            answers = []
            for i, (question, options, _) in enumerate(GL_ITEMS):
                answer = st.selectbox(str(i + 1) + '. ' + question, list(options), index=None, key=f'ui_tolerance_{i}')
                answers.append(options.index(answer) if answer is not None else None)
            if st.form_submit_button('Apply profile'):
                st.session_state['ui_profile_epoch'] = st.session_state.get('ui_profile_epoch', 0) + 1
                try:
                    st.session_state['ui_profile'] = score_profile(capacity, answers)
                    st.session_state['ui_profile_kind'] = 'User-entered profile'
                except (TypeError, ValueError):
                    st.session_state.pop('ui_profile', None)
                    st.error('Complete all eighteen answers. No defaults are assumed.')
    profile = st.session_state.get('ui_profile')
    if profile is None:
        st.info('Choose an example or complete all eighteen answers.')
        return
    if getattr(profile, 'version', '') != 'grable-lytton-capacity-policy-v2':
        clear_profile()
        st.info('The profile method changed. Enter the eighteen answers again.')
        return
    result = apply_risk_policy(record, profile, eligible_model=collection.source.startswith('temperature_'))
    left, right = st.columns(2)
    left.metric('Risk allowance R', f'{profile.score:.3f}')
    right.metric('Profile outcome', result['profile_action'])
    st.caption(f'Grable-Lytton total {profile.tolerance_raw}/47 ({profile.tolerance_band}); capacity {profile.capacity_tier}; reconciled tier {profile.tier}.')
    st.caption(f'Required confidence {result["minimum_confidence"]:.1%}; recorded confidence {record.confidence:.1%}; model class {record.decision}.')
    st.write(result['reason'])
    st.caption('Higher allowance lowers the confidence requirement. It never changes Buy to Sell or Sell to Buy. Weak evidence still abstains.')
    with st.expander('Scoring and policy details'):
        st.write('Tolerance = (published item total - 13)/34. R = min(capacity, tolerance). Required confidence = 0.80 - 0.30*R.')
        st.json(result)
        st.caption('Capacity weights, tier reconciliation and the confidence gate are explicit project policies. Local wording and suitability have not been independently validated.')


def candidate_identity(collection, record, text):
    return collection.identity(record.session_date) + ':' + record.data_hashes.get('profile_digest', 'no-profile') + ':' + record.data_hashes.get('profile_epoch', '0') + ':' + hashlib.sha256(text.encode()).hexdigest()

def set_candidate(collection, record, fail=False):
    base = render(record)
    st.session_state['ui_candidate_text'] = base.text.replace(f'{record.confidence*100:.2f}%','1.00%',1) if fail else base.text
    st.session_state.pop('ui_verification',None)

def explanation_view(collection, record):
    st.header('An explanation must match its evidence')
    case_caption(collection,record)
    record = replace(record, data_hashes=dict(record.data_hashes, profile_epoch=str(st.session_state.get('ui_profile_epoch', 0))))
    profile = st.session_state.get('ui_profile')
    if getattr(profile, 'version', '') == 'grable-lytton-capacity-policy-v2':
        policy = apply_risk_policy(record, profile, eligible_model=collection.source.startswith('temperature_'))
        st.caption('Profile outcome: ' + policy['profile_action'] + '. The model class below is diagnostic; its probabilities are unchanged.')
        profile_digest = hashlib.sha256(json.dumps(profile.to_dict(), sort_keys=True).encode()).hexdigest()
        record = replace(record, risk_tier=profile.tier,
                         data_hashes=dict(record.data_hashes, profile_digest=profile_digest))
    else:
        st.caption('No personal profile is attached. The record risk tier is experiment metadata.')
    record_id = collection.identity(record.session_date) + ':' + record.data_hashes.get('profile_digest', 'no-profile') + ':' + record.data_hashes.get('profile_epoch', '0')
    if st.session_state.get('ui_candidate_record') != record_id:
        st.session_state['ui_candidate_record'] = record_id
        set_candidate(collection,record)
    top = st.columns([1,1])
    top[0].button('Inject wrong probability',key='ui_inject',on_click=set_candidate,args=(collection,record,True))
    top[1].button('Restore record facts',key='ui_restore',on_click=set_candidate,args=(collection,record,False))
    left,right = st.columns(2,gap='large')
    with left:
        st.subheader('Editable candidate')
        text = st.text_area('Explanation to check',height=320,key='ui_candidate_text',label_visibility='collapsed')
        st.caption('The structured payload retains the correct record facts. This makes a displayed-text error observable.')
        if st.button('Check explanation',type='primary',key='ui_verify'):
            try:
                result = emit(record,candidate=Explanation(text,render(record).payload),strict_prose=True)
                st.session_state['ui_verification'] = (candidate_identity(collection,record,text),result)
            except (TypeError,ValueError,RuntimeError) as error:
                st.session_state.pop('ui_verification',None)
                st.error('Checking failed. No verified output is claimed.')
                st.caption(str(error))
    with right:
        st.subheader('Checked output')
        cached = st.session_state.get('ui_verification')
        if not cached or cached[0] != candidate_identity(collection,record,text):
            st.info('Check the current text to produce a verified output. Previous results do not apply after an edit.')
        else:
            result = cached[1]
            if result.replaced_by_template:
                st.error('Candidate rejected')
                st.success('Verified fallback emitted')
                st.caption('The displayed candidate conflicts with the record. The deterministic replacement passes its own check.')
            else:st.success('Candidate accepted')
            st.text(result.text)
            with st.expander('What the verifier checked'):
                report = result.rejected_verification or result.verification
                st.dataframe([{key: (json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else '' if value is None else str(value)) for key, value in row.items()} for row in report.as_table()],hide_index=True,width='stretch')
                st.json({'numeric_fidelity':report.numeric_fidelity,'directional_consistency':report.directional_consistency,'claim_recall':report.claim_recall,'unverifiable_rate':report.unverifiable_rate,'failed_metrics':report.failed_metrics,'fallback_passed':result.verification.passed})
    st.caption('Strict checking supports maintained claim patterns and record values. Arbitrary market prose and human usefulness remain unvalidated.')
    with st.expander('Complete deterministic indicator guide'):
        st.text(render_guided(record).text)
        st.caption('This guide uses the maintained definitions. No local language model is configured or called by opening this view.')
    with st.expander('Optional configured language-model request'):
        from app.tabs.decision import _render_guided_explanation
        _render_guided_explanation(record,collection.source)

def walkthrough():
    collection,record = choose_case()
    if collection is None:return
    step = st.radio('Walkthrough stage',STEPS,horizontal=True,key='ui_step',label_visibility='collapsed')
    {'Decision':decision_view,'Evidence':evidence_view,'Risk profile':profile_view,'Explanation check':explanation_view}[step](collection,record)
    st.divider()
    index = STEPS.index(step)
    left,middle,right = st.columns([1,2,1])
    if index:left.button('Previous',key='ui_previous',on_click=navigate,args=('Walkthrough',STEPS[index-1]),width='stretch')
    middle.caption(f'Step {index+1} of {len(STEPS)}')
    if index<len(STEPS)-1:right.button('Next',key='ui_next',type='primary',on_click=navigate,args=('Walkthrough',STEPS[index+1]),width='stretch')
    else:right.button('Recorded experiments',key='ui_next',on_click=navigate,args=('Experiments',),width='stretch')

def leakage_view():
    st.header('The deliberate leak fires')
    payload,primary = data.leakage_results()
    clean,canary = primary['A_CLEAN'],primary['D_CENTRED']
    cols = st.columns(3)
    cols[0].metric('Clean macro-F1',f"{clean['macro_f1']:.4f}")
    cols[1].metric('Random comparator',f"{clean['chance']:.4f}")
    cols[2].metric('Canary lift',f"{canary['lift']:+.4f}")
    st.write('The centred-window control deliberately looks into the future. The clean five-session arm scores below its random comparator.')
    st.dataframe([{'Arm':'Clean','Lift':clean['lift'],'CI lower':clean['ci_lo'],'CI upper':clean['ci_hi'],'Verdict':clean['verdict']},{'Arm':'Deliberate centred leak','Lift':canary['lift'],'CI lower':canary['ci_lo'],'CI upper':canary['ci_hi'],'Verdict':canary['verdict']}],hide_index=True,width='stretch')
    st.caption('Recorded 12 October experiment, six expanding folds. Revision-conservative timestamps do not prove historical vendor availability.')
    with st.expander('All arms, both horizons and recorded chart'):
        st.dataframe(payload['results'],hide_index=True,width='stretch')
        st.image(str(data.FRESH/'harness_alpaca/arms_lift_alpaca.png'))
        st.caption('The news-bucket change remains a lag ablation, not proven use before publication.')
    with st.expander('Live labelled feature-level failure check'):
        st.caption('Synthetic fixtures only. This checks causality functions without training a model.')
        if st.button('Run feature boundary checks',key='ui_feature_check'):
            from investify.features.causality_audit import run_audit
            result = run_audit()
            if result['all_checks_passed']:st.success(f"{result['checks_passed']}/{len(result['checks'])} checks passed; {result['deliberate_mutations_detected']} deliberately centred mutations detected.")
            else:st.error('A feature boundary check failed.')
            st.dataframe(result['checks'],hide_index=True,width='stretch')

def social_view():
    st.header('Original sentiment models on the same posts')
    benchmark,usable,result = data.social_comparison()
    st.caption(f"{len(benchmark['posts'])} acquired MSFT posts, {len(usable)} usable reference labels, {result['heldout_posts']} held out.")
    if not result['comparison_ready']:
        st.warning('Paired comparison unavailable. Failed/missing outputs are not neutral predictions.')
        return
    rows = [{'Candidate':'CryptoBERT' if c['model_id']=='ElKulako/cryptobert' else 'Cardiff','Macro-F1 agreement':c['quality_metrics']['macro_f1'],'Coverage':f"{c['completed_posts']}/{result['heldout_posts']}",'Errors':c['error_posts']} for c in result['results']]
    st.dataframe(rows,hide_index=True,width='stretch')
    st.bar_chart(pd.DataFrame(rows),x='Candidate',y='Macro-F1 agreement',color='#267b86',height=230)
    st.warning('Reference-label agreement from a single labeling pass. Independent validation is unmeasured; only two held-out references are negative.')
    st.write('Cardiff leads this exploratory comparison. Deployment selection remains open.')
    with st.expander('Original identities, receipts and limits'):
        st.json(result)
        st.download_button('Download recorded comparison',json.dumps(result,indent=2),file_name='recorded_social_comparison.json',mime='application/json',key='ui_social_download')

def teacher_view():
    from app.tabs.teacher_study import load_study
    st.header('Teacher construction pilot')
    plan,result,prose,exports = load_study()
    st.write(f"{result['accepted']} accepted examples: four training and two validation. Phi-3-mini remains untrained.")
    selected = st.selectbox('Archived example',[r['record_id'] for r in result['outcomes']],key='ui_teacher_record')
    st.text(prose[selected])
    st.caption('Actual assistant-written controlled prose, checked against archived records. The exact serving revision is unavailable.')
    with st.expander('Verification and training exports'):
        st.dataframe([{'record':r['record_id'],'split':r['split'],'status':r['status']} for r in result['outcomes']],hide_index=True,width='stretch')
        for split in ('train','validation'):
            st.download_button('Download '+split+' examples',exports[split],file_name='teacher_'+split+'.jsonl',key='ui_teacher_'+split)
    st.warning('All source decisions are Buy. Student-training efficacy and human understanding remain unmeasured.')

def experiments():
    choice = st.radio('Research study',['Leakage audit','Sentiment comparison','Teacher pilot'],horizontal=True,key='ui_study',label_visibility='collapsed')
    try:{'Leakage audit':leakage_view,'Sentiment comparison':social_view,'Teacher pilot':teacher_view}[choice]()
    except (OSError,KeyError,TypeError,ValueError,RuntimeError) as error:
        st.error('Recorded study evidence unavailable or invalid. No substitute score is shown.')
        st.caption(str(error))

def design():
    st.header('Design connected to the code')
    st.write('The live UI reads recorded evidence and calls the same context, profile and verification modules used in the tests.')
    if (ASSETS/'components.svg').exists():st.image(str(ASSETS/'components.svg'))
    with st.expander('Domain model'):
        if (ASSETS/'domain.svg').exists():st.image(str(ASSETS/'domain.svg'))
    with st.expander('Core code walkthrough'):
        st.markdown("""- `decision_record.py`: validates probability, feature and attribution invariants.
- `explain/context.py`: exposes maintained feature meanings and missing-data limits.
- `explain/verifier.py`: checks displayed claims and JSON independently.
- `explain/pipeline.py`: retains rejection and verifies fallback.
- `risk_profile.py` and `risk_comparator.py`: compute an explicitly separate prototype blend.""")
    st.caption('Diagram and code review remains a genuine team/supervisor task. A generated figure or commit count does not establish student ownership.')
