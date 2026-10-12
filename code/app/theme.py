"""Shared visual language for the demo.

The design brief is a laboratory instrument, not a trading dashboard. This
demo's job is to let an examination panel read, from a projector, which
experimental arms breached a leakage threshold and which did not. So:

* Colour encodes the verdict and nothing else. Three verdicts get three
  colours because the three-way distinction (PASS / LEAK / BELOW_CHANCE) is
  itself one of the spike's findings -- collapsing leak and below-chance into
  one "fail" colour would misreport the result.
* Numbers are set in tabular figures. Lift, CI bounds and macro-F1 are read
  in columns and must align vertically at distance.
* Everything that is not a number or a verdict stays quiet.
"""
import streamlit as st

INK = "#16202B"
INK_SOFT = "#4A5A6A"
PAPER = "#F7F8F6"
RULE = "#C9D1D9"

VERDICT_COLORS = {
    "PASS": "#0F766E",
    "LEAK": "#C2410C",
    "BELOW_CHANCE": "#A16207",
}

VERDICT_MEANING = {
    "PASS": "does not breach the configured lift and confidence-interval alert rule",
    "LEAK": "above the positive alert threshold; investigate timing",
    "BELOW_CHANCE": "below the negative alert threshold; useful predictive signal unestablished",
}


def inject() -> None:
    """Inject the shared stylesheet. Safe to call from every tab."""
    st.markdown(
        f"""
        <style>


          html, body, [class*="css"] {{
            font-family: 'IBM Plex Sans', system-ui, sans-serif;
          }}
          .stApp {{ background: {PAPER}; }}
          .block-container {{ max-width: 1320px; padding-top: 1.8rem; }}
          .investify-banner {{ background: #fff; border: 1px solid {RULE};
            border-left: 4px solid {VERDICT_COLORS['BELOW_CHANCE']};
            border-radius: 6px; padding: .65rem 1rem; margin: .7rem 0 1rem;
            font-size: .9rem; line-height: 1.5; }}
          .stTabs [role="tab"] {{ font-size: 1rem; font-weight: 600; min-height: 3rem; }}
          .stButton button {{ min-height: 2.7rem; }}
          .stCode pre {{ white-space: pre-wrap; overflow-wrap: anywhere; }}

          h1, h2, h3, h4 {{
            font-family: 'IBM Plex Sans', system-ui, sans-serif;
            color: {INK};
            letter-spacing: -0.011em;
          }}
          h1 {{ font-weight: 600; font-size: 1.9rem; }}
          h2 {{ font-weight: 600; font-size: 1.35rem; margin-top: 0.4rem; }}
          h3 {{ font-weight: 500; font-size: 1.05rem; color: {INK_SOFT}; }}

          /* numeric content aligns in columns at projector distance */
          .stDataFrame, .stTable, code, pre {{
            font-family: 'IBM Plex Mono', ui-monospace, monospace;
            font-variant-numeric: tabular-nums;
          }}

          .readout {{
            border: 1px solid {RULE};
            border-radius: 4px;
            background: #FFFFFF;
            padding: 1rem 1.15rem 1.05rem;
            height: 100%;
          }}
          .readout .arm {{
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.82rem;
            color: {INK_SOFT};
            margin-bottom: 0.35rem;
          }}
          .readout .value {{
            font-family: 'IBM Plex Mono', monospace;
            font-variant-numeric: tabular-nums;
            font-size: 2.1rem;
            font-weight: 500;
            line-height: 1.1;
          }}
          .readout .verdict {{
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 0.45rem;
          }}
          .readout .gloss {{
            font-size: 0.78rem;
            color: {INK_SOFT};
            margin-top: 0.3rem;
            line-height: 1.4;
          }}

          .caveat {{
            border: 1px solid {RULE};
            border-left: 3px solid {VERDICT_COLORS['BELOW_CHANCE']};
            border-radius: 4px;
            background: #FFFDF7;
            padding: 0.75rem 1rem;
            font-size: 0.85rem;
            line-height: 1.5;
            color: {INK};
            margin: 0.6rem 0 1rem;
          }}
          .caveat b {{ font-weight: 600; }}

          .provenance {{
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.76rem;
            color: {INK_SOFT};
            line-height: 1.7;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def readout(arm: str, value: str, verdict: str, gloss: str = "") -> str:
    """One measurement readout: the arm, its lift, and the verdict."""
    color = VERDICT_COLORS.get(verdict, INK)
    gloss_html = f'<div class="gloss">{gloss}</div>' if gloss else ""
    return (
        f'<div class="readout">'
        f'<div class="arm">{arm}</div>'
        f'<div class="value" style="color:{color}">{value}</div>'
        f'<div class="verdict" style="color:{color}">{verdict.replace("_", " ")}</div>'
        f"{gloss_html}"
        f"</div>"
    )


def matplotlib_style() -> dict:
    """rcParams matching the page, so charts do not look pasted in."""
    return {
        "figure.facecolor": "#FFFFFF",
        "axes.facecolor": "#FFFFFF",
        "axes.edgecolor": RULE,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "text.color": INK,
        "xtick.color": INK_SOFT,
        "ytick.color": INK_SOFT,
        "grid.color": "#E6EAEE",
        "font.family": "sans-serif",
        "font.sans-serif": ["IBM Plex Sans", "DejaVu Sans"],
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
