"""Focused Mid-1 presentation workspace. Only the selected page executes."""
import sys
from pathlib import Path
import streamlit as st
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))
from app import presenter, presenter_style
st.set_page_config(page_title='Investify - Mid-1',page_icon='I',layout='wide',initial_sidebar_state='collapsed')
presenter_style.inject()
brand,nav = st.columns([1,3],vertical_alignment='center')
brand.markdown('<div class="brand"><span class="brand-dot"></span>Investify</div>',unsafe_allow_html=True)
page = nav.segmented_control('Workspace',presenter.PAGES,default='Overview',key='ui_page',label_visibility='collapsed',width='stretch')
st.caption("Recorded five-session research. Educational output only. No investment advice or order execution.")
st.divider()
{'Overview':presenter.overview,'Walkthrough':presenter.walkthrough,'Experiments':presenter.experiments,'Design':presenter.design}[page or 'Overview']()
st.markdown('<div class="scope-line">Five trading-session horizon. Research and educational output only. No investment advice or order execution. Recorded model results do not establish useful predictive performance.</div>',unsafe_allow_html=True)
