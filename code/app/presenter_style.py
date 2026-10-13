"""Small offline stylesheet for a focused projector-friendly research demo."""
import streamlit as st

def inject():
    st.markdown("""<style>
    .stApp { background: #f8fafc; color: #172b43; }
    .block-container { max-width: 1180px; padding-top: 1.6rem; padding-bottom: 1.2rem; }
    h1,h2,h3 { color:#172b43; letter-spacing:-.02em; font-family:Arial,sans-serif; }
    h1 { font-size:2.4rem !important; font-weight:700; }
    h2 { font-size:1.65rem !important; }
    h3 { font-size:1.15rem !important; }
    p,li { font-family:Arial,sans-serif; line-height:1.55; }
    .brand { font-size:1.4rem; font-weight:750; letter-spacing:-.04em; }
    .brand-dot { display:inline-block; height:9px; width:9px; margin-right:9px; border-radius:50%; background:#267b86; }
    .eyebrow { color:#597084; font-size:.82rem; font-weight:650; text-transform:uppercase; letter-spacing:.07em; }
    .summary { font-size:1.08rem; max-width:700px; color:#425a70; }
    .quiet-note { padding:.65rem .85rem; border-left:3px solid #ac6a24; background:#fff9ed;
                  color:#694510; border-radius:3px; font-size:.85rem; margin:.8rem 0; }
    .scope-line { color:#597084; font-size:.79rem; border-top:1px solid #d9e2ea; padding-top:.7rem; margin-top:1.4rem; }
    [data-testid="stMetric"] { padding:.7rem 0; }
    [data-testid="stMetricValue"] { font-size:1.8rem; }
    .stButton button { min-height:2.7rem; border-radius:6px; font-weight:600; }
    .stCode pre { white-space:pre-wrap; overflow-wrap:anywhere; }
    [data-testid="stToolbar"] { visibility:hidden; }
    </style>""", unsafe_allow_html=True)
