"""One visible workspace at a time. Interactions reuse the verified core modules."""
import hashlib
import html
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from app import presenter_data as data
from investify.explain.context import build_context
from investify.explain.template import Explanation, render, render_guided
from investify.explain.pipeline import emit
from investify.risk_profile import CAPACITY_OPTIONS, TOLERANCE_QUESTIONS, score_profile

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
    values = {'horizon':'5+ years','buffer':'6+ months','stability':'Salaried and stable','dependants':'0','age':'18-30'}
    for key, value in values.items():
        st.session_state['ui_profile_' + key] = value
    for i, (_, options) in enumerate(TOLERANCE_QUESTIONS):
        st.session_state[f'ui_tolerance_{i}'] = options[index]
    st.session_state['ui_profile'] = score_profile(values, [index]*3)
    st.session_state['ui_profile_kind'] = 'Fictional example: cautious' if index == 0 else 'Fictional example: higher tolerance'

def clear_profile():
    for name in CAPACITY_OPTIONS:
        st.session_state['ui_profile_' + name] = None
    for i in range(3):
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
        st.write('A risk profile changes a separate comparison. A deliberately wrong explanation triggers rejection and a verified fallback. The recorded model output stays fixed.')
        st.caption('Suggested case: fresh Alpaca, frozen classifier, 21 December 2023.')
    with right:
        st.subheader('Recorded research')
        st.write('Inspect the leakage experiment, original sentiment-model comparison and teacher construction pilot.')
        st.button('Explore experiments', key='ui_open_experiments', on_click=navigate, args=('Experiments',))
        st.button('View architecture and requirements', key='ui_open_design', on_click=navigate, args=('Design',))
    st.markdown('<div class="quiet-note">The current five-session predictor has no established useful signal. All 186 fresh calibrated predictions are Buy. The demonstration exposes these limits.</div>', unsafe_allow_html=True)

def decision_view(collection, record):
    st.header('Recorded decision')
    case_caption(collection, record)
    left, right = st.columns([1,2], gap='large')
    with left:
        st.metric('Model class', record.decision)
        st.metric('Calibrated probability', f'{record.confidence:.1%}')
        st.caption('Probability of the recorded class, not an expected return.')
    with right:
        probs = pd.DataFrame({'class':list(record.probabilities),'probability':list(record.probabilities.values())})
        st.bar_chart(probs, x='class', y='probability', horizontal=True, height=210, color='#267b86')
    st.markdown('<div class="quiet-note">All 186 fresh calibrated decisions are Buy. Better calibration loss alone does not establish useful predictions.</div>', unsafe_allow_html=True)
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
    st.header('A profile changes the comparison')
    st.write('The profile weights a separate technical/news blend. It leaves the recorded classifier unchanged.')
    actions = st.columns([1,1,1,2])
    actions[0].button('Cautious example', key='ui_cautious', on_click=profile_example, args=(0,))
    actions[1].button('Higher-tolerance example', key='ui_tolerant', on_click=profile_example, args=(2,))
    actions[2].button('Clear profile', key='ui_clear_profile', on_click=clear_profile)
    if st.session_state.get('ui_profile_kind'):
        st.caption(st.session_state['ui_profile_kind'] + '. These answers are demonstration scenarios, not participant observations.')
    with st.expander('Enter or edit the eight answers'):
        with st.form('ui_profile_form'):
            columns = st.columns(2)
            labels = {'horizon':'When will you need this money?','buffer':'Emergency expenses buffer','stability':'Income stability','dependants':'Financial dependants','age':'Age band'}
            capacity = {}
            for i,(name,options) in enumerate(CAPACITY_OPTIONS.items()):
                capacity[name] = columns[i%2].selectbox(labels[name],list(options),index=None,key='ui_profile_'+name)
            tolerance = []
            for i,(question,options) in enumerate(TOLERANCE_QUESTIONS):
                answer = st.selectbox(question,options,index=None,key=f'ui_tolerance_{i}')
                tolerance.append(options.index(answer) if answer is not None else None)
            if st.form_submit_button('Apply profile'):
                try:
                    st.session_state['ui_profile'] = score_profile(capacity,tolerance)
                    st.session_state['ui_profile_kind'] = 'User-entered prototype profile'
                except (TypeError,ValueError) as error:
                    st.session_state.pop('ui_profile',None)
                    st.error('Complete all eight answers. No defaults are assumed.')
    profile = st.session_state.get('ui_profile')
    if profile is None:
        st.info('Choose a labelled example or enter all eight answers to compare profiles.')
        return
    st.caption(f'Capacity {profile.capacity_tier}, tolerance {profile.tolerance_tier}; reconciled R = {profile.score:.3f}. Binding axis: {profile.binding_axis}.')
    try:
        comparator = data.comparator_for(collection)
        if record.session_date not in comparator.manifest['heldout_sessions']:
            st.info('This session belongs to the scaling-development block. Choose a later session to score the comparator.')
            return
        result = comparator.score(record.session_date,profile)
    except (OSError,KeyError,TypeError,ValueError,OverflowError) as error:
        st.error('Profile comparison unavailable. The recorded decision remains unchanged.')
        st.caption(str(error));return
    left,right = st.columns(2)
    left.metric('Fixed comparison, R = 0.5',result['reference']['decision'])
    right.metric(f'Profile comparison, R = {profile.score:.3f}',result['profile_conditioned']['decision'])
    st.caption(f"Recorded classifier: {record.decision}, probability {record.confidence:.1%}. It does not use this prototype profile.")
    table = [{'Comparison':name,'News term':item['sentiment_term'],'Technical term':item['technical_term'],'Total score':item['score']} for name,item in [('Fixed',result['reference']),('Profile',result['profile_conditioned'])]]
    st.dataframe(table,hide_index=True,width='stretch')
    st.caption('Weighted z-scores, not probabilities or expected returns. Suitability and predictive performance are unvalidated.')
    with st.expander('Calculation and scaling details'):
        st.write('C = R*S + (1-R)*T. Sell at C <= -0.5; Hold at -0.5 < C <= 0.5; Buy at C > 0.5.')
        st.write('R changes the news weight. A smaller R need not produce a more conservative action.')
        st.json({'fit_end':comparator.manifest['fit_end'],'fit_rows':comparator.manifest['fit_rows'],'profile':profile.to_dict(),'scaled_inputs':result['scaled_inputs']})
        if result['missing_sentiment']:st.warning(result['missing_policy'])

def candidate_identity(collection, record, text):
    return collection.identity(record.session_date) + ':' + hashlib.sha256(text.encode()).hexdigest()

def set_candidate(collection, record, fail=False):
    base = render(record)
    st.session_state['ui_candidate_text'] = base.text.replace(f'{record.confidence*100:.2f}%','1.00%',1) if fail else base.text
    st.session_state.pop('ui_verification',None)

def explanation_view(collection, record):
    st.header('An explanation must match its evidence')
    case_caption(collection,record)
    record_id = collection.identity(record.session_date)
    if st.session_state.get('ui_candidate_record') != record_id:
        st.session_state['ui_candidate_record'] = record_id
        set_candidate(collection,record)
    top = st.columns([1,1,3])
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
                st.dataframe(report.as_table(),hide_index=True,width='stretch')
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
    st.caption(f"{len(benchmark['posts'])} acquired MSFT posts, {len(usable)} usable AI references, {result['heldout_posts']} held out.")
    if not result['comparison_ready']:
        st.warning('Paired comparison unavailable. Failed/missing outputs are not neutral predictions.')
        return
    rows = [{'Candidate':'CryptoBERT' if c['model_id']=='ElKulako/cryptobert' else 'Cardiff','Macro-F1 agreement':c['quality_metrics']['macro_f1'],'Coverage':f"{c['completed_posts']}/{result['heldout_posts']}",'Errors':c['error_posts']} for c in result['results']]
    st.dataframe(rows,hide_index=True,width='stretch')
    st.bar_chart(pd.DataFrame(rows),x='Candidate',y='Macro-F1 agreement',color='#267b86',height=230)
    st.warning('Agreement with AI references. Independent human validation is unmeasured, and the held-out set has only two negative references.')
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
