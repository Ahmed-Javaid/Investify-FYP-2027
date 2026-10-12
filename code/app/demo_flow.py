"""Presenter navigation and explicit fictional profiles; no research runs."""
import streamlit as st
SECTIONS = ('Start here', 'Decision', 'Leakage Lab', 'Social Study', 'Teacher Study')

def navigate(section):
    if section not in SECTIONS:
        raise ValueError('Unknown demo section')
    st.session_state['demo_section'] = section

def reset_profile():
    for key in list(st.session_state):
        if key.startswith('profile_'):
            del st.session_state[key]
    st.session_state.pop('demo_profile_example', None)

def example_profile(tolerance):
    """User-triggered fictional answers; never participant data."""
    reset_profile()
    capacity = {'horizon': '5+ years', 'buffer': '6+ months', 'stability': 'Salaried and stable',
                'dependants': '0', 'age': '18-30'}
    from investify.risk_profile import TOLERANCE_QUESTIONS
    for name, value in capacity.items():
        st.session_state['profile_' + name] = value
    for index, (_, options) in enumerate(TOLERANCE_QUESTIONS):
        st.session_state[f'profile_tolerance_{index}'] = options[tolerance]
    st.session_state['demo_profile_example'] = 'Cautious' if tolerance == 0 else 'Higher tolerance'

def render_start():
    st.markdown('## From evidence to a checked explanation')
    st.write('A short walkthrough of one recorded NVDA case, followed by the experiments that test its limits.')
    cols = st.columns(3)
    with cols[0]:
        st.markdown('### 1. Explore a decision')
        st.write('Choose a session, load a labelled example profile, and compare the separate risk blend.')
    with cols[1]:
        st.markdown('### 2. Test the explanation')
        st.write('Read the evidence, inject a wrong probability, and watch the verifier replace it with checked text.')
    with cols[2]:
        st.markdown('### 3. Explain the research')
        st.write('Show the deliberate leakage control, compare the two sentiment models, and review the teacher pilot.')
    st.button('Start the walkthrough', type='primary', key='start_walkthrough', on_click=navigate, args=('Decision',))
    st.divider()
    st.markdown('### What is interactive?')
    st.write('Profile scoring, the separate comparator, explanation verification and fallback run when you interact. '
             'The market and social model results are recorded experiments; opening a screen does not train or run those models.')
    st.info('The fresh 12 October Alpaca run is the default. Its five-day clean arm is below the random comparator '
            'and all 186 calibrated decisions are Buy. Present this as an evaluated prototype with an unresolved prediction problem.')
    with st.expander('Suggested 6-minute route'):
        st.markdown("""1. **Decision (2 min):** keep 21 December 2023; load Cautious, then Higher tolerance. The separate comparator changes while the recorded classifier stays fixed.
2. **Decision (1 min):** click Explain selected record; toggle Corrupt this explanation and choose Wrong displayed probability beside correct JSON. Show rejection and verified fallback.
3. **Leakage Lab (1 min):** contrast the deliberate future-looking canary with the clean arm. Open the full results only if asked.
4. **Social Study (1 min):** compare the original candidates and explain why AI-label agreement does not establish human accuracy or stock-market transfer.
5. **Teacher Study (1 min):** show an actual accepted example and the four/two exports. Student adaptation remains later work.""")

def render_footer():
    current = st.session_state.get('demo_section', SECTIONS[0])
    index = SECTIONS.index(current)
    st.divider()
    left, middle, right = st.columns([1, 2, 1])
    if index:
        left.button('Previous: ' + SECTIONS[index - 1], key='demo_previous', on_click=navigate,
                    args=(SECTIONS[index - 1],), width='stretch')
    middle.caption(f'Walkthrough {index + 1} / {len(SECTIONS)} | {current}')
    if index < len(SECTIONS) - 1:
        right.button('Next: ' + SECTIONS[index + 1], key='demo_next', type='primary',
                     on_click=navigate, args=(SECTIONS[index + 1],), width='stretch')
