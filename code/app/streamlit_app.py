"""Investify POC demo (brief section 8).

Four views read historical/study artifacts. No model trains or corpus
inference runs at import time. Explanation requests and scientific re-runs
are explicit actions; missing scientific inputs disable the re-run. Profile
and comparator arithmetic uses recorded features, not current market data.

The non-advice notice and the horizon are rendered once here, above the
tabs, so they are visible on every screen regardless of which tab is
open (brief section 8 requires this on every screen).
"""
import sys
from pathlib import Path

import streamlit as st
import yaml

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from app.tabs import decision, leakage_lab, social_study, teacher_study  # noqa: E402
from investify.decision_record import NON_ADVICE_NOTICE  # noqa: E402

st.set_page_config(
    page_title="Investify — mid evaluation",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CONFIG_PATH = REPO_ROOT / "config" / "spike.yaml"


@st.cache_data
def load_config() -> dict:
    if not CONFIG_PATH.exists():
        st.error(f"Missing {CONFIG_PATH}. This file defines the spike's scope and paths.")
        st.stop()
    return yaml.safe_load(CONFIG_PATH.read_text())


cfg = load_config()
ticker = cfg["tickers"][0]
horizon = cfg["labels"]["primary_horizon_days"]

st.markdown(
    """
    <style>
      .investify-banner {
        border: 1px solid rgba(128,128,128,0.35);
        border-left: 4px solid #b45309;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin-bottom: 1.1rem;
        font-size: 0.86rem;
        line-height: 1.45;
      }
      .investify-banner strong { letter-spacing: 0.01em; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Investify — mid-evaluation working demo")
st.caption(
    f"{ticker}, {horizon}-day horizon, {cfg['date_range']['start']} to "
    f"{cfg['date_range']['end']}, seed {cfg['seed']}"
)

st.markdown(
    f"""
    <div class="investify-banner">
      <strong>{horizon}-day horizon.</strong> {NON_ADVICE_NOTICE}
      This demo exists to evidence a leakage-audited evaluation harness and a
      deterministic explanation verifier. It is not a trading system, and the
      model underlying it has no demonstrated predictive signal — see the
      Leakage Lab tab.
    </div>
    """,
    unsafe_allow_html=True,
)

tab_leakage, tab_decision, tab_social, tab_teacher = st.tabs(["Leakage Lab", "Decision", "Social Study", "Teacher Study"])

with tab_leakage:
    leakage_lab.render()

with tab_decision:
    decision.render()

with tab_social:
    social_study.render()

with tab_teacher:
    teacher_study.render()
