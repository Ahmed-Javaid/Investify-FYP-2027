"""Prototype profile UI with explicit unanswered states and score audit."""
import streamlit as st

from investify.risk_profile import CAPACITY_OPTIONS, CAPACITY_WEIGHTS, TOLERANCE_QUESTIONS, score_profile

LABELS = {'horizon': 'When will you need this money?', 'buffer': 'Emergency expenses buffer',
          'stability': 'Income stability', 'dependants': 'Financial dependants', 'age': 'Age band'}


def render_profile():
    st.caption('Project prototype. These questions, weights and caps are not a validated risk instrument.')
    st.markdown('**Capacity: ability to absorb loss**')
    capacity = {name: st.selectbox(LABELS[name], list(options), index=None,
                                   placeholder='Select an answer', key=f'profile_{name}')
                for name, options in CAPACITY_OPTIONS.items()}
    st.markdown('**Tolerance: willingness to accept risk**')
    tolerance = []
    for index, (question, options) in enumerate(TOLERANCE_QUESTIONS):
        answer = st.radio(question, options, index=None, key=f'profile_tolerance_{index}')
        tolerance.append(options.index(answer) if answer is not None else None)
    if any(answer is None for answer in capacity.values()) or None in tolerance:
        st.info('Complete all eight answers to calculate the prototype profile. No middle answers are assumed.')
        return None
    profile = score_profile(capacity, tolerance)
    st.markdown(f"Capacity **{profile.capacity_tier}**, tolerance **{profile.tolerance_tier}** "
                f"→ profile **{profile.tier}**. Binding axis: {profile.binding_axis}.")
    st.metric('Reconciled profile score R', f'{profile.score:.3f}')
    with st.expander('How the profile was calculated'):
        st.table([{'factor': factor, 'score': profile.factor_scores[factor], 'weight': CAPACITY_WEIGHTS[factor],
                   'contribution': profile.factor_contributions[factor]} for factor in CAPACITY_WEIGHTS])
        st.write(f'Capacity before caps: {profile.capacity_raw:.4f}; after caps: {profile.capacity_score:.4f}. '
                 f'Tolerance: {profile.tolerance_score:.4f}. Reconciled score is the smaller value.')
        st.write('Matched project rules: ' + (', '.join(profile.matched_caps) or 'none') +
                 f'. Cap changed the score: {profile.cap_binding}.')
        st.caption('Tier cuts: 0.40 and 0.70. Capacity caps stay strictly below 0.40. '
                   'The three tolerance questions are stand-ins, not the full Grable–Lytton questionnaire.')
    st.markdown('[Risk ability and willingness reference](https://syndication.finra.org/content/know-your-risk-tolerance)')
    st.caption('The reference supports the distinction between ability and willingness; it does not validate these project weights or caps.')
    return profile
