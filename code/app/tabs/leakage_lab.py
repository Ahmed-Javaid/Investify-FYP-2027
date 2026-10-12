"""Tab 1 — Leakage Lab.

Shows that the leakage detector works. The panel should be able to read, from
a projector, which arms breached the threshold and which did not, and then
watch a leak appear live rather than take the table's word for it.

The hero is the canary: a deliberately-leaked feature must show up loudly
while the clean arm does not. Everything else on the page supports that one
reading.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from app import theme  # noqa: E402
from investify.demo_readiness import harness_missing_inputs  # noqa: E402

ARTIFACTS = REPO_ROOT / "artifacts"
CONFIG_PATH = REPO_ROOT / "config" / "spike.yaml"

CORPUS_LABELS = {
    "results": ("FNSPID", "11,708 headlines, 0.22% genuinely timestamped"),
    "results_alpaca": ("Alpaca / Benzinga", "6,767 headlines, 100% genuinely timestamped"),
}


@st.cache_data
def load_results(prefix: str) -> dict | None:
    path = ARTIFACTS / f"{prefix}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


@st.cache_data
def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def _available_corpora() -> list[str]:
    return [p for p in CORPUS_LABELS if (ARTIFACTS / f"{p}.json").exists()]


def _fmt_ci(row: pd.Series) -> str:
    return f"[{row['ci_lo']:+.4f}, {row['ci_hi']:+.4f}]"


def _verdict_style(col: pd.Series) -> list[str]:
    return [
        f"color: {theme.VERDICT_COLORS.get(v, theme.INK)}; font-weight: 600"
        for v in col
    ]


def render() -> None:
    theme.inject()
    cfg = load_config()
    threshold = cfg["leakage_control"]["pass_threshold_abs_lift"]

    available = _available_corpora()
    if not available:
        st.error(
            "No harness results found. Run "
            "`uv run python -m investify.harness.run_spike` to generate "
            "`artifacts/results.json`."
        )
        return

    if len(available) > 1:
        labels = {p: CORPUS_LABELS[p][0] for p in available}
        prefix = st.radio(
            "News corpus",
            available,
            key="leakage_corpus",
            format_func=lambda p: labels[p],
            horizontal=True,
            help="Both corpora are reported. Neither replaces the other — the "
                 "difference between them is itself a finding.",
        )
        st.caption(CORPUS_LABELS[prefix][1])
    else:
        prefix = available[0]

    payload = load_results(prefix)
    results = pd.DataFrame(payload["results"])
    provenance = payload["provenance"]
    st.info("Saved historical experiment results. This table is replayed from artifacts; "
            "a fresh scientific run has not been performed by opening this view.")
    st.warning("The historical splitter used a calendar-day purge for trading-session labels. "
               "A correction now uses each label's actual endpoint before the test session. "
               "Calibration outcomes are also restricted to those available before evaluation. "
               "The saved results have not been rerun with that correction; its effect on "
               "historical performance is unmeasured.")

    primary = cfg["labels"]["primary_horizon_days"]
    at_primary = results[results["horizon_days"] == primary].set_index("arm")

    # --- the hero: does the canary still detect?
    st.markdown(f"## Does the detector still detect? ({primary}-day horizon)")

    canary = at_primary.loc["D_CENTRED"]
    clean = at_primary.loc["A_CLEAN"]
    samebar = at_primary.loc["E_SAMEBAR_TEXT"]

    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            theme.readout(
                "D_CENTRED — deliberate leak",
                f"{canary['lift']:+.3f}",
                canary["verdict"],
                f"A centred 20-day window peeks ~10 days ahead. "
                f"{abs(canary['lift'])/threshold:.0f}× the {threshold} threshold. "
                f"This is the canary: if it ever goes quiet, the build fails.",
            ),
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            theme.readout(
                "A_CLEAN — the control",
                f"{clean['lift']:+.3f}",
                clean["verdict"],
                "The historically designated clean arm is below its stratified-random "
                "comparator in this saved experiment. This does not identify "
                "the cause or establish useful predictive signal.",
            ),
            unsafe_allow_html=True,
        )
    with cols[2]:
        gloss = (
            "Text mapped to the session it published in. On this corpus the "
            "arm is measurable — 749 rows (11.1%) genuinely disagree between "
            "the two rules — and it tracks the clean arm. A real null result."
            if prefix == "results_alpaca"
            else "Not measurable on FNSPID: 26 of 11,708 headlines carry a real "
                 "time of day and exactly 1 maps differently. Absence of "
                 "evidence, not evidence of absence."
        )
        st.markdown(
            theme.readout(
                "E_SAMEBAR_TEXT — the point of the spike",
                f"{samebar['lift']:+.3f}",
                samebar["verdict"],
                gloss,
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="caveat">
          <b>Three verdicts, not two.</b>
          <b style="color:{theme.VERDICT_COLORS['PASS']}">PASS</b> — {theme.VERDICT_MEANING['PASS']}.
          <b style="color:{theme.VERDICT_COLORS['LEAK']}">LEAK</b> — {theme.VERDICT_MEANING['LEAK']}.
          <b style="color:{theme.VERDICT_COLORS['BELOW_CHANCE']}">BELOW CHANCE</b> — {theme.VERDICT_MEANING['BELOW_CHANCE']}.
          Collapsing the last two into one "fail" would misreport the result.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("E_SAMEBAR_TEXT retains a strict-prior as-of join. The bucket change can alter "
               "news lag; the saved difference is not by itself proof of using text before publication.")

    # --- the full table
    st.markdown("## Every arm, both horizons")

    table = results.copy()
    table["macro-F1"] = table.apply(
        lambda r: f"{r['macro_f1']:.4f} ± {r['macro_f1_sd']:.4f}", axis=1
    )
    table["95% CI on lift"] = table.apply(_fmt_ci, axis=1)
    table["lift"] = table["lift"].map(lambda v: f"{v:+.4f}")
    table["chance"] = table["chance"].map(lambda v: f"{v:.4f}")
    display = table[
        ["arm", "horizon_days", "macro-F1", "chance", "lift", "95% CI on lift",
         "verdict", "n_rows", "changes"]
    ].rename(columns={"horizon_days": "horizon (d)", "n_rows": "rows", "changes": "what it changes"})

    st.dataframe(
        display.style.apply(_verdict_style, subset=["verdict"]),
        width='stretch',
        hide_index=True,
        height=460,
    )

    # --- the chart
    chart_name = "arms_lift.png" if prefix == "results" else "arms_lift_alpaca.png"
    chart_path = ARTIFACTS / chart_name
    if chart_path.exists():
        st.image(str(chart_path), width='stretch')
    else:
        st.warning(f"Chart {chart_name} not found. Re-run the harness to regenerate it.")

    # --- watch the leak appear
    st.markdown("## Watch the leak appear")
    st.write(
        f"Rebuilds `D_CENTRED` at the {primary}-day horizon from the historical "
        f"price/news store and cached sentiment scores, then fits six folds "
        f"with the same seed. Duration depends on the restored environment. "
        f"The result is calculated separately from the saved table."
    )

    corpus = provenance.get("corpus", cfg.get("default_corpus", "fnspid"))
    missing = harness_missing_inputs(cfg, corpus, REPO_ROOT)
    if missing:
        st.warning("The live experiment is unavailable until its historical data "
                   "and training environment are restored. Saved results remain available.")
        with st.expander("Re-run prerequisites"):
            st.code("\n".join(missing), language=None)
    st.caption("The prerequisite check inspects file presence/readability and Parquet signatures, "
               "and discovers runtime modules. It does not validate dataset rows, cache coverage "
               "or compatibility with the scientific lock.")
    if st.button("Re-run D_CENTRED now", type="primary", disabled=bool(missing)):
        with st.status("Running six expanding purged folds…", expanded=True) as status:
            try:
                from investify.harness.arms import (
                    ARMS,
                    build_all_matrices,
                    clean_row_mask,
                    run_arm,
                )

                corpus = provenance.get("corpus", cfg.get("default_corpus", "fnspid"))
                st.write(f"Building feature matrices for corpus `{corpus}`…")
                matrices = build_all_matrices(cfg, corpus=corpus)
                row_mask = clean_row_mask(matrices["A_CLEAN"], primary, cfg)
                st.write("Fitting D_CENTRED across folds…")
                live = run_arm(ARMS["D_CENTRED"], matrices["D_CENTRED"], row_mask, primary, cfg)
                status.update(label="Done", state="complete", expanded=False)
            except (ImportError, OSError, ValueError, TypeError, RuntimeError) as error:
                live = None
                status.update(label="Scientific re-run failed", state="error", expanded=True)
                st.error("Scientific re-run failed. No new experiment result is reported; the saved table remains historical.")
                st.code(str(error), language=None)

        if live is not None:
            colour = theme.VERDICT_COLORS.get(live["verdict"], theme.INK)
            st.markdown(
                f"Live result — lift "
                f"<span style='color:{colour};font-weight:600'>{live['lift']:+.4f}</span>, "
                f"95% CI [{live['ci_lo']:+.4f}, {live['ci_hi']:+.4f}], verdict "
                f"<span style='color:{colour};font-weight:600'>{live['verdict']}</span>.",
                unsafe_allow_html=True,
            )
            st.caption(
                f"Per-fold macro-F1: "
                + ", ".join(f"{v:.3f}" for v in live["per_fold_f1"])
            )

    st.markdown("## Feature-level causality demonstration")
    st.info("Labelled synthetic fixtures only. This optional check runs the actual feature, "
            "label and join functions without fitting a classifier. It does not reproduce "
            "the historical market experiment or establish canary prediction lift.")
    if st.button("Run labelled feature checks", key="run_fixture_causality"):
        from investify.features.causality_audit import run_audit
        try:
            st.session_state['fixture_causality_result'] = run_audit()
        except (OSError, ValueError, TypeError, KeyError) as error:
            st.session_state.pop('fixture_causality_result', None)
            st.error(f"The labelled feature check failed: {error}")
    fixture_result = st.session_state.get('fixture_causality_result')
    if fixture_result:
        if fixture_result['all_checks_passed']:
            st.success(f"Labelled fixture checks: {fixture_result['checks_passed']}/"
                       f"{len(fixture_result['checks'])} passed; "
                       f"{fixture_result['deliberate_mutations_detected']} deliberately centred "
                       "window mutations detected.")
        else:
            st.error("A labelled feature check failed. Inspect the retained results; no success is claimed.")
        st.dataframe(fixture_result['checks'], hide_index=True, width='stretch')
        with st.expander("Feature check scope and source identity"):
            st.json(fixture_result)

    # --- provenance
    st.markdown("## Provenance")
    versions = ", ".join(f"{k} {v}" for k, v in provenance["package_versions"].items())
    manifest = provenance.get("corpus_manifest", {})
    manifest_hash = ""
    if isinstance(manifest, dict):
        for key in ("sha256", "file_sha256"):
            if key in manifest:
                manifest_hash = manifest[key]
                break
    st.markdown(
        f"""
        <div class="provenance">
        seed {provenance['seed']} &nbsp;|&nbsp; git {provenance['git_commit'][:12]}<br>
        corpus {provenance.get('corpus', 'fnspid')} &nbsp;|&nbsp;
        {provenance['splits']['n_folds']} folds, {provenance['splits']['embargo_days']}-day embargo<br>
        {versions}<br>
        corpus manifest sha256 {manifest_hash[:32] if manifest_hash else 'see artifacts/corpus_manifest.json'}<br>
        run completed {provenance['run_completed_utc']}
        </div>
        """,
        unsafe_allow_html=True,
    )
