"""Recorded research views with a guided, explicit-action mid-evaluation demo."""
import sys
from pathlib import Path
import streamlit as st
import yaml
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))
sys.path.insert(0, str(REPO_ROOT))
from app import demo_flow, theme
from app.tabs import decision, leakage_lab, social_study, teacher_study
from investify.decision_record import NON_ADVICE_NOTICE
st.set_page_config(page_title='Investify | Mid evaluation', page_icon='I', layout='wide', initial_sidebar_state='collapsed')
CONFIG_PATH = REPO_ROOT / 'config/spike.yaml'
@st.cache_data
def load_config():
    if not CONFIG_PATH.exists():
        st.error('The demo scope configuration is unavailable.')
        st.stop()
    return yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8'))
cfg = load_config()
horizon = cfg['labels']['primary_horizon_days']
theme.inject()
st.title('Investify')
st.caption(f"MID EVALUATION | {cfg['tickers'][0]} | {horizon}-session horizon | Recorded 2018-2023 research")
st.markdown(f'<div class="investify-banner"><strong>{horizon}-session horizon.</strong> '
            f'{NON_ADVICE_NOTICE} Results are historical experiments. Useful predictive performance is unproven.</div>', unsafe_allow_html=True)
sections = st.tabs(demo_flow.SECTIONS, key='demo_section', on_change='rerun')
# Keep views mounted so selections survive navigation; recorded evidence only.
with sections[0]: demo_flow.render_start()
with sections[1]: decision.render()
with sections[2]: leakage_lab.render()
with sections[3]: social_study.render()
with sections[4]: teacher_study.render()
demo_flow.render_footer()
