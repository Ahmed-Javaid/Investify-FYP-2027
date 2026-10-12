"""Tab 2 — Decision.

One decision, end to end: the risk profile, the decision and its calibrated
probability, what drove it, the deterministic explanation, and the per-claim
verifier report. Then the control that matters most for the defence — corrupt
the explanation and watch the verifier reject it and the template take over.

This tab states plainly that the model is degenerate. Every one of the 186
emitted decisions is Buy. A panel member should learn that from the page, not
by clicking through dates and noticing.
"""
import json
import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from app import risk_profile_form, theme  # noqa: E402
from investify.decision_record import DecisionRecord  # noqa: E402
from investify.explain.fixtures import CORRUPTION_KINDS, corrupt  # noqa: E402
from investify.explain.pipeline import emit  # noqa: E402
from investify.explain.template import Explanation, render as render_template  # noqa: E402
from investify.explain.context import build_context  # noqa: E402
from investify.explain.local_llm import ExplainerConfig, LocalExplainer  # noqa: E402
from investify.risk_comparator import build_comparator  # noqa: E402

ARTIFACTS = REPO_ROOT / "artifacts"

# Alpaca first: it is the corpus with genuine publication times, so it is the
# one the decision path should demonstrate. FNSPID stays selectable because
# both are reported -- neither replaces the other.
FRESH_RUN = ARTIFACTS / 'scientific_runs/alpaca_revision_conservative_20261012_run01/recovery01'
CORPUS_RECORDS = {
    'fresh_frozen': ('Fresh Alpaca | frozen classifier', FRESH_RUN / 'engine_frozen_alpaca/decision_records.json'),
    'fresh_refit': ('Fresh Alpaca | refit classifier', FRESH_RUN / 'engine_refit_alpaca/decision_records.json'),
    "alpaca": ("Historical Alpaca / Benzinga", ARTIFACTS / "decision_records_alpaca.json"),
    "fnspid": ("Historical FNSPID", ARTIFACTS / "decision_records.json"),
}

# The five the verifier rejects outright. vague_unverifiable is kept
# selectable but is honestly a non-rejection -- see the note rendered below.
DETECTABLE_KINDS = [k for k in CORRUPTION_KINDS if k != "vague_unverifiable"]

KIND_LABELS = {
    "wrong_probability": "State the wrong probability",
    "wrong_shap_magnitude": "State the wrong contribution size",
    "flipped_direction": "Flip a contribution's direction",
    "promoted_minor_feature": "Promote a minor feature to a headline cause",
    "invented_feature_name": "Invent a feature that does not exist",
    "vague_unverifiable": "Add a vague, unverifiable sentence",
    "text_only_probability": "Wrong displayed probability beside correct JSON",
}


@st.cache_data
def load_records(path_str: str) -> dict:
    payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    if not payload["decision_records"]:
        raise ValueError("No historical decisions in the selected corpus")
    for data in payload["decision_records"]:
        build_context(DecisionRecord.from_dict(data), corpus="validation")
    return payload


def _available_corpora() -> list[str]:
    return [k for k, (_, path) in CORPUS_RECORDS.items() if path.exists()]


def _metric_row(verification) -> None:
    metrics = [
        ("Numeric fidelity", verification.numeric_fidelity, 0.98, "≥ 0.98"),
        ("Directional consistency", verification.directional_consistency, 0.95, "≥ 0.95"),
        ("Claim recall", verification.claim_recall, 0.80, "≥ 0.80"),
        ("Unverifiable rate", verification.unverifiable_rate, 0.15, "≤ 0.15"),
    ]
    cols = st.columns(4)
    for col, (label, value, _threshold, rule) in zip(cols, metrics):
        col.metric(label, f"{value:.3f}", help=f"Pass condition {rule}")


def _round_for_display(claims: pd.DataFrame) -> pd.DataFrame:
    """Round numeric-looking claim values for projector legibility.

    Display only -- verification already happened at full precision, and the
    tolerances it applied (0.5 percentage points on probabilities, 1e-3 on
    SHAP values) are far coarser than the rounding here, so nothing that was
    checked is hidden by it.
    """
    def fmt(value):
        if value is None:
            return 'null'
        if isinstance(value, bool):
            return json.dumps(value)
        try:
            return f"{float(value):.4f}"
        except (TypeError, ValueError):
            return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)

    out = claims.copy()
    for column in ("claimed", "actual"):
        if column in out.columns:
            out[column] = out[column].map(fmt)
    return out


def _render_evidence_context(record: DecisionRecord, corpus_label: str) -> None:
    context = build_context(record, corpus=corpus_label)
    st.markdown("## Understand the technical and sentiment evidence")
    st.caption(f"{record.ticker} · recorded session {record.session_date} · {record.horizon_days}-session horizon · {corpus_label}")
    st.info(context["data_status"])
    st.write(context["interpretation"])
    for family in ("Technical analysis", "News sentiment", "Unclassified"):
        rows = [r for r in context["features"] if r["family"] == family]
        if not rows:
            continue
        with st.expander(family, expanded=False):
            for row in rows:
                value = f"{row['value']:.4g}" if row["value_available"] else "missing"
                st.markdown(f"**{row['label']} — {value}**")
                st.write(row["meaning"])
                st.caption(f"Model attribution: {row['shap_value']:+.4f} in raw-score units; {row['effect_on_predicted_class']} the {record.decision} class.")
                if row["reference"]:
                    st.markdown(f"[Indicator or model reference]({row['reference']})")
    st.caption(context["coverage"]["social_sentiment"] + ". " + context["coverage"]["risk_conditioning"] + ".")


def _render_guided_explanation(record: DecisionRecord, corpus: str) -> None:
    st.markdown("## Explain the indicators")
    try:
        config = ExplainerConfig(model=os.environ.get("INVESTIFY_LLM_MODEL") or None,
                                 base_url=os.environ.get("INVESTIFY_LLM_BASE_URL", "http://127.0.0.1:1234/v1"),
                                 timeout_seconds=float(os.environ.get("INVESTIFY_LLM_TIMEOUT", "20")),
                                 api_key=os.environ.get("INVESTIFY_LLM_API_KEY") or None)
    except ValueError as error:
        st.warning("The local generator configuration is invalid. The record and verifier remain available.")
        with st.expander("Generator configuration details"):
            st.code(str(error), language=None)
        return
    if config.model is None:
        st.caption("No local LLM is configured. The verified deterministic comparator is available.")
    else:
        st.caption(f"Local model configured: {config.model}. Its connection and generated claims are checked when requested.")
    from investify.explain.local_llm import PROMPT_VERSION
    from investify.explain.verifier import VERIFIER_CONTRACT_VERSION
    identity = (corpus, record.to_json(sort_keys=True), config.model, config.base_url, config.timeout_seconds,
                PROMPT_VERSION, VERIFIER_CONTRACT_VERSION)
    if st.button("Explain selected record", key="generate_explanation"):
        with st.spinner("Building and verifying the explanation…"):
            result = LocalExplainer(config).explain(record, corpus=corpus)
        st.session_state["guided_explanation"] = (identity, result)
    cached = st.session_state.get("guided_explanation")
    if cached and cached[0] == identity:
        result = cached[1]
        st.info(("Verified deterministic explanation. " if result.used_template else "Verified local generation. ")
                + result.reason)
        st.code(result.emitted.text, language=None)
        with st.expander("Generation attempts (unverified raw output)"):
            if not result.attempts:
                st.caption("No model request was made.")
            for attempt in result.attempts:
                st.write(f"Attempt {attempt.number}; served model {attempt.served_model or 'unreported'}; "
                         f"{attempt.elapsed_seconds:.3f} seconds; finish reason {attempt.finish_reason or 'unreported'}.")
                st.write(attempt.error or "Supported claims passed verification.")
                st.code(attempt.raw_output or "No completion returned.", language=None)
    st.caption("The pilot checks supported claims and exact maintained definitions. It does not certify arbitrary market prose.")


@st.cache_data
def _load_comparator(path: str, corpus: str, artifact_sha256: str):
    comparator = build_comparator(Path(path), corpus=corpus)
    if comparator.manifest['artifact_sha256'] != artifact_sha256:
        raise ValueError('The selected artifact changed while it was loaded')
    return comparator


def _render_risk_comparator(record, corpus, profile):
    st.markdown('## Risk-dependent linear comparator')
    st.caption('A separate retrospective comparator. The saved classifier decision and probabilities do not change.')
    try:
        path = CORPUS_RECORDS[corpus][1]
        comparator = _load_comparator(str(path), corpus, hashlib.sha256(path.read_bytes()).hexdigest())
        manifest = comparator.manifest
        st.write(f"Scaling uses the first {manifest['fit_rows']} saved feature rows, ending {manifest['fit_end']}. "
                 f"Only the later {len(manifest['heldout_sessions'])} sessions are scored, "
                 f"from {manifest['heldout_sessions'][0]} to {manifest['heldout_sessions'][-1]}.")
        if record.session_date not in manifest['heldout_sessions']:
            st.info('This session belongs to the scaling-development block. Select a later held-out date for the comparator.')
            return
        if profile is None:
            st.info('Complete the risk profile to compare its blend with the fixed R = 0.5 reference.')
            return
        result = comparator.score(record.session_date, profile)
    except (OSError, KeyError, TypeError, ValueError, OverflowError) as error:
        st.warning('The risk comparator is unavailable. The recorded classifier result remains available.')
        with st.expander('Comparator validation details'):
            st.code(str(error), language=None)
        return
    cols = st.columns(2)
    cols[0].metric('Fixed blend comparator (R = 0.5)', result['reference']['decision'])
    cols[1].metric(f'Profile blend comparator (R = {profile.score:.3f})', result['profile_conditioned']['decision'])
    st.write(f"C = R × S + (1 − R) × T. S = {result['sentiment_signal']:.4f}; T = {result['technical_signal']:.4f}. "
             f"Fixed score {result['reference']['score']:.4f}; profile score {result['profile_conditioned']['score']:.4f}.")
    st.caption('Sell: C ≤ −0.5; Hold: −0.5 < C ≤ 0.5; Buy: C > 0.5. '
               'Scores are weighted z-scores, not probabilities or expected returns.')
    if result['missing_sentiment']:
        st.warning(result['missing_policy'])
    with st.expander('Comparator inputs and limits'):
        st.table([{'feature': name, 'z_score': value} for name, value in result['scaled_inputs'].items()])
        st.write('The five technical z-scores are averaged with the inherited trend-following sign convention. '
                 'This is a new chronological scaling run, not the original engine CV baseline.')
        st.write('The profile-to-blend mapping is a project assumption. A smaller R gives news less weight; '
                 'it need not produce a more conservative action. Suitability and predictive performance are unvalidated.')
        st.caption('Outcome labels are absent from the saved records, so no accuracy or return metric is reported.')
        st.json({'version': result['version'], 'artifact_sha256': result['artifact_sha256'],
                 'scaling_fit_end': result['scaling_fit_end'], 'profile_version': profile.version})


def render() -> None:
    theme.inject()

    available = _available_corpora()
    if not available:
        st.error(
            "No decision records found. Run "
            "`uv run python scripts/build_decision_records.py --corpus alpaca` "
            "to generate `artifacts/decision_records_alpaca.json`."
        )
        return

    if len(available) > 1:
        corpus = st.radio(
            "News corpus",
            available,
            key="decision_corpus",
            format_func=lambda k: CORPUS_RECORDS[k][0],
            horizontal=True,
            help="The decision, its attribution and its explanation are all "
                 "rebuilt from the selected corpus.",
        )
    else:
        corpus = available[0]

    try:
        payload = load_records(str(CORPUS_RECORDS[corpus][1]))
        records = [DecisionRecord.from_dict(r) for r in payload["decision_records"]]
        provenance = payload["provenance"]
    except (OSError, KeyError, TypeError, ValueError) as error:
        st.error("The selected historical decisions are unavailable or invalid. No decision is shown.")
        with st.expander("Input validation details"):
            st.code(str(error), language=None)
        return
    by_date = {r.session_date: r for r in records}
    horizon = records[0].horizon_days

    decisions = pd.Series([r.decision for r in records]).value_counts().to_dict()
    only_class = len(decisions) == 1

    # read from this corpus's own run rather than hardcoding one corpus's figures
    metrics = provenance.get("metrics", {})
    brier_before = f"{metrics['brier_before']:.3f}" if "brier_before" in metrics else "—"
    brier_after = f"{metrics['brier_after']:.3f}" if "brier_after" in metrics else "—"

    if corpus.startswith('fresh_'):
        st.info('Recorded fresh experiment | 12 October 2026 | observed label-end purge and availability-safe calibration. '
                'News revisions use max(created_at, updated_at); historical availability is unproven. No training runs on this screen.')
    if only_class:
        detail = ('The fresh replay attributes the collapse to the learned isotonic maps: Buy is highest on every evaluation row. '
                  'Refitting is not required for the collapse. This does not establish the cause of the older saved runs.'
                  if corpus.startswith('fresh_') else
                  'These preserved historical metrics have not been recomputed by this viewer; their original collapse cause is unestablished.')
        st.markdown(
            f"""
            <div class="caveat">
              <b>This model is degenerate, and the demo shows it on purpose.</b>
              All {len(records)} decisions in the evaluation fold are
              <b>{next(iter(decisions))}</b>. Recorded Brier score:
              {brier_before} to {brier_after}. {detail}
              The clean pipeline has no demonstrated predictive signal at this horizon;
              see the Leakage Lab tab.
              <br><br>
              What this tab demonstrates is the <b>decision plumbing</b> — attribution,
              deterministic explanation, and claim-level verification — not a
              usable trading signal.
            </div>
            """,
            unsafe_allow_html=True,
        )

    profile_stage, evidence_stage, explanation_stage = st.tabs(['1. Profile + decision', '2. Evidence', '3. Explanation + verification'])
    with profile_stage:
        left, right = st.columns([1, 2], gap="large")

        with left:
            st.markdown("## Risk profile")
            st.caption(
                "The profile controls a separate linear comparator. It does not condition "
                "the saved classifier or its calibrated probabilities."
            )
            profile = risk_profile_form.render_profile()

        with right:
            st.markdown("## Decision")
            dates = sorted(by_date)
            chosen = st.select_slider(
                f"Session date ({len(dates)} sessions in the evaluation fold)",
                options=dates,
                key="decision_session",
                value=dates[-1],
            )
            record = by_date[chosen]

            head = st.columns([1, 1, 2])
            head[0].metric(f"{record.ticker} — {horizon}-day view", record.decision)
            head[1].metric("Calibrated probability", f"{record.confidence:.1%}")
            head[2].markdown(
                "Probability breakdown  \n"
                + "  \n".join(
                    f"`{cls:<5}` {p:.1%}" for cls, p in record.probabilities.items()
                )
            )

            st.markdown("### Why the model produced this class")
            contributions = pd.DataFrame(
                [
                    {
                        "feature": c.name,
                        "contribution": c.shap_value,
                        "value": c.value,
                        "direction": c.direction,
                    }
                    for c in record.top_k
                ]
            )
            st.caption(
                f"TreeSHAP contributions toward the predicted class "
                f"(**{record.decision}**), ranked by magnitude. Base value "
                f"{record.base_value:+.4f}; contributions and base value sum to the "
                f"raw model output {record.raw_model_output:+.4f}."
            )
            st.bar_chart(
                contributions.set_index("feature")["contribution"],
                horizontal=True,
                color=theme.VERDICT_COLORS["PASS"],
            )
            with st.expander('Exact feature values and contributions'):
                st.dataframe(contributions, hide_index=True, width='stretch')

        st.divider()

        _render_risk_comparator(record, corpus, profile)
    with evidence_stage:
        _render_evidence_context(record, CORPUS_RECORDS[corpus][0])
        st.divider()
    with explanation_stage:
        _render_guided_explanation(record, corpus)
        st.divider()

        # --- explanation + verification
        st.markdown("## Explanation, and whether it can be trusted")
        strict_prose = st.toggle(
            "Reject unsupported sentences", value=True, key="strict_prose",
            help="Only supported claim sentences are accepted. When disabled, the "
                 "existing unverifiable-claim rate threshold applies.",
        )

        corrupt_it = st.toggle(
            "Corrupt this explanation",
            key="corrupt_explanation",
            help="Injects a specific error and runs it through the same emit path.",
        )

        if corrupt_it:
            kind = st.selectbox(
                "Error to inject",
                list(CORRUPTION_KINDS) + ["text_only_probability"],
                key="corruption_kind",
                index=CORRUPTION_KINDS.index(DETECTABLE_KINDS[2])
                if DETECTABLE_KINDS[2] in CORRUPTION_KINDS
                else 0,
                format_func=lambda k: KIND_LABELS.get(k, k),
            )
            clean = render_template(record)
            if kind == "text_only_probability":
                candidate = Explanation(
                    text=clean.text.replace(f"{record.confidence * 100:.2f}%", "1.00%", 1),
                    payload=clean.payload,
                )
            else:
                candidate = corrupt(record, clean, kind, np.random.default_rng(record.seed)).explanation
            emitted = emit(record, candidate=candidate, strict_prose=strict_prose)

            if emitted.replaced_by_template:
                st.markdown(
                    f"<span style='color:{theme.VERDICT_COLORS['LEAK']};font-weight:600'>"
                    f"Rejected.</span> The corrupted explanation failed verification "
                    f"({', '.join(emitted.rejected_verification.failed_metrics)}) "
                    f"and was replaced by the deterministic template. The emitted explanation "
                    f"below is the verified fallback; the rejected text remains available for review.",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<span style='color:{theme.VERDICT_COLORS['BELOW_CHANCE']};font-weight:600'>"
                    f"Not rejected — and this is a real limitation, shown honestly.</span> "
                    f"The injected sentence <i>is</i> correctly classified as an unverifiable "
                    f"claim, but alongside the supported concrete claims it gives an "
                    f"unverifiable rate of {emitted.verification.unverifiable_rate:.2f}, under "
                    f"the 0.15 threshold. The verifier bounds how much of an explanation can be "
                    f"ungrounded; it does not certify that every sentence earns its place.",
                    unsafe_allow_html=True,
                )

            with st.expander("The corrupted text that was checked", expanded=False):
                st.code(candidate.text, language=None)
        else:
            emitted = emit(record)

        st.markdown("### What is shown to the user")
        st.code(emitted.text, language=None)

        st.markdown("### Candidate verifier report" if corrupt_it else "### Verifier report")
        shown_report = emitted.rejected_verification or emitted.verification
        _metric_row(shown_report)
        if emitted.replaced_by_template:
            st.caption("These scores describe the rejected candidate. The displayed fallback passed verification.")
        st.caption(
            "All four are reported. Coverage comes from displayed prose; numeric "
            "and directional scores use the worse result of prose and JSON. Known "
            "contradictions always fail. This checks supported claims, not arbitrary market prose."
        )

        table = shown_report.as_table()
        claims = pd.DataFrame(table) if not isinstance(table, pd.DataFrame) else table
        st.dataframe(
            _round_for_display(claims),
            hide_index=True,
            width='stretch',
            height=320,
        )

        st.caption(
            f"Model {provenance.get('model_version', 'unknown')}, seed {record.seed}. "
            f"{record.non_advice_notice}"
        )
