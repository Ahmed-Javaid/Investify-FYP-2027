"""
INVESTIFY - PROPOSAL-STAGE HIGH-FIDELITY PROTOTYPE
==================================================

Ten screens, fully navigable, real layout, real states, realistic data.

The committee defines the proof of concept as "a high-fidelity functional
prototype ... a skeleton of the finished product without actual implementation
of the functionality behind the interface". The Selection Guide (section 12)
asks for something different: a focused technical spike on the riskiest
assumption, and says plainly that "a polished interface that does not test a
technical or workflow risk is not sufficient by itself".

Those pull in opposite directions, so this project satisfies both rather than
choosing. This file is the prototype the committee asks for. Two paths behind
it run REAL code:

    screens 2-4   risk scoring and the binding constraint  (profile_scoring.py)
    screen 7      the explanation verifier                 (verifier.py)

Screen 7 is the one that matters, and it can be genuinely correct this early
for a specific reason: groundedness here is decidable by symbolic checking, so
the verifier does not need a trained engine - only a decision record, and a
fixture record works exactly as well as a real one. Screen 7 includes a control
that corrupts the stored record live, so the guard can be seen catching a
failure on stage rather than described as working.

The separate technical spikes live in ../poc_leakage_spike.py and
../poc_risk_profile_spike.py and are summarised on screen 10.

RUN
    streamlit run app.py
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

import fixtures as fx
import profile_scoring as ps
import verifier as vf

st.set_page_config(page_title="Investify", page_icon="\U0001F4C8", layout="wide")

# PROJECTOR PALETTE.
#
# The first version used muted teal/amber/maroon. On a laptop those read as a
# considered palette; through a lecture projector they collapse into three
# similar dark smudges, and the maroon and teal become genuinely hard to tell
# apart. These replacements are high-contrast against white, far apart in
# lightness as well as hue (so they survive a projector with a colour cast),
# and blue/orange rather than red/green so they also survive colour-blindness.
BLUE = "#0B5FBF"    # positive / pushes toward the verdict
ORANGE = "#D35400"  # negative / pushes away
RED = "#B3261E"     # failure
GREEN = "#1B7F37"   # pass
GREY = "#5F6368"    # inactive
INK = "#101418"     # axis lines and text

# Bigger type and thicker strokes than the matplotlib defaults, because a chart
# that is comfortable at arm's length is unreadable from the back of a room.
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "font.size": 12, "axes.labelsize": 12.5, "xtick.labelsize": 11.5,
    "ytick.labelsize": 11.5, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "axes.edgecolor": INK,
    "axes.linewidth": 1.2, "lines.linewidth": 2.2,
})

POC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCREENS = [
    ("1. Sign in",              "mocked"),
    ("2. Risk capacity",        "real"),
    ("3. Risk tolerance",       "real"),
    ("4. Profile summary",      "real"),
    ("5. Choose a company",     "mocked"),
    ("6. Recommendation",       "fixture record"),
    ("7. Verifier report",      "REAL - live path"),
    ("8. Follow-up questions",  "scripted"),
    ("9. Degraded state",       "real state machine"),
    ("10. Operator view",       "reads spike output"),
]

DISCLAIMER = ("Research and educational prototype. **Not financial advice.** "
              "No trades are placed. Horizon: 1 week.")


def init():
    d = st.session_state
    d.setdefault("signed_in", False)
    d.setdefault("email", "")
    d.setdefault("capacity", None)
    d.setdefault("gl_answers", [None] * len(ps.GL_ITEMS))
    d.setdefault("gl_index", 0)
    d.setdefault("ticker", "NVDA")
    d.setdefault("feed_up", True)
    d.setdefault("history_days", 2180)
    d.setdefault("corrupt_for", None)
    d.setdefault("corrupt_prob", None)
    d.setdefault("corrupt_rsi_shap", None)


def show(fig):
    """st.pyplot then close. Streamlit reruns the whole script on every
    interaction, so a figure left open leaks one per rerun and matplotlib
    starts warning after twenty."""
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)


# ---------------------------------------------------------------------------
def user_profile():
    """The stored profile, or the fixture default plus a reason why not.

    Returns (risk, complete, note). An INCOMPLETE profile must never be scored
    silently: defaulting unanswered tolerance items to the first option scored
    an untouched questionnaire as raw 13 - the lowest possible tolerance -
    and presented it as a result. That is exactly the "answering from thin
    data" failure FR-12 exists to prevent, on our own screen."""
    d = st.session_state
    if d.capacity is None:
        return dict(fx.DEFAULT_RISK), False, \
            "Risk capacity form not completed (screen 2)."
    missing = sum(1 for a in d.gl_answers if a is None)
    if missing:
        return dict(fx.DEFAULT_RISK), False, \
            (f"{missing} of {len(ps.GL_ITEMS)} risk-tolerance questions "
             f"unanswered (screen 3).")
    cap = d.capacity["capped"]
    raw = ps.gl_raw(d.gl_answers)
    tol = ps.gl_normalise(raw)
    rec = ps.reconcile(cap, tol)
    return ({"tier": rec["tier"], "capacity": round(cap, 4),
             "tolerance": round(tol, 4), "lambda": rec["lambda"]},
            True, None)


# Building the record is split into three steps on purpose.
#
# Streamlit reruns the whole script top to bottom, and a widget only returns
# its new value at the line where it is instantiated. Building the record
# ABOVE the sliders therefore reads last run's values, and the page renders one
# interaction behind: the slider says 0.74 while the verifier still reports on
# 0.58, and the screen shows PASS next to a record the operator just corrupted.
# On screen 7 that is the one failure mode that must not exist, so the record
# is anchored before the sliders and applied after them.


def base_record():
    """The record as stored, with no corruption applied."""
    risk, complete, note = user_profile()
    r = fx.record_for(st.session_state.ticker, risk)
    r["profile_complete"] = complete
    r["profile_note"] = note
    return r


def anchor(base):
    """Re-point the corruption controls at this record when the company (or
    its verdict) changes, so the sliders always start from its own values."""
    d = st.session_state
    key = (d.ticker, base["decision"])
    if d.corrupt_for != key:
        d.corrupt_for = key
        d.corrupt_prob = base["probabilities"][base["decision"]]
        d.corrupt_rsi_shap = base["shap"]["rsi_14"]


def apply_corruption(base):
    """Overlay whatever the operator controls currently hold. Call this AFTER
    the sliders have been instantiated."""
    d = st.session_state
    r = json.loads(json.dumps(base))
    r["probabilities"][r["decision"]] = d.corrupt_prob
    r["shap"]["rsi_14"] = d.corrupt_rsi_shap
    # Keep FR-6 additivity exact even after corruption. The failure being
    # demonstrated is explanation-versus-record, not an inconsistent record.
    r["base_value"] = round(
        r["probabilities"][r["decision"]] - sum(r["shap"].values()), 6)
    return r


def live_record():
    """For screens with no operator controls, where ordering cannot bite."""
    base = base_record()
    anchor(base)
    return apply_corruption(base)


def pristine(record, base):
    """True when the record has not been altered on screen 7."""
    return (record["probabilities"][record["decision"]]
            == base["probabilities"][base["decision"]]
            and record["shap"]["rsi_14"] == base["shap"]["rsi_14"])


def explain(record, authored_from=None):
    """Generate, verify, regenerate once, verify, then fall back.

    `authored_from` is the record the explanation was WRITTEN against;
    `record` is the one it is CHECKED against. They are the same thing in
    normal operation and differ only when the operator alters the record on
    screen 7 - which is the whole scenario. Regenerating the prose from the
    altered record instead would simply produce a new, internally consistent
    explanation and the guard would never fire: corrupting the record would
    silently corrupt the explanation to match, which is the opposite of the
    property being demonstrated.

    The screen also claims the explanation is 'regenerated once, then replaced
    by the deterministic template'. That path is implemented here rather than
    asserted in a caption - in a project about not stating things the system
    did not do, a UI claiming a retry the code never performed is the wrong
    kind of irony."""
    src = authored_from or record
    attempts = []

    gen = fx.generation_for(src)
    rep = vf.verify(record, gen)
    attempts.append(("First generation", rep))
    if rep["verdict"] == "PASS":
        return gen["prose"], rep, attempts, False

    gen2 = fx.regeneration_for(src)
    rep2 = vf.verify(record, gen2)
    attempts.append(("Regeneration (one retry)", rep2))
    if rep2["verdict"] == "PASS":
        return gen2["prose"], rep2, attempts, False

    # Built FROM the record, so it is grounded by construction.
    return vf.template_explanation(record), rep2, attempts, True


def footer():
    st.divider()
    st.caption(DISCLAIMER)


# ---------------------------------------------------------------------------
def screen_signin():
    st.title("Investify")
    st.caption("A leakage-resistant investment advisor whose explanations can "
               "be checked by machine.")
    c1, c2 = st.columns([1, 1.4])
    with c1:
        st.subheader("Create an account")
        st.text_input("Email", key="email", placeholder="you@example.com")
        st.text_input("Password", type="password", placeholder="••••••••")
        if st.button("Create account and continue", type="primary"):
            st.session_state.signed_in = True
            st.success("Account created. Continue to **2. Risk capacity**.")
        st.caption("Account creation is mocked at this stage. No credentials "
                   "are stored and nothing leaves this machine.")
    with c2:
        st.subheader("What this system does")
        st.markdown(
            "- Asks what your finances can absorb, and how you feel about loss\n"
            "- Reads formal news and informal social discussion **separately**\n"
            "- Returns Buy / Hold / Sell for the coming week with an "
            "**honest** confidence figure\n"
            "- Breaks that decision into what drove it\n"
            "- **Checks every sentence of the explanation** against the numbers "
            "that produced it, and refuses to show one that fails")
    footer()


def screen_capacity():
    st.title("2. Risk capacity")
    st.caption("What your finances can absorb. We do not ask for your salary - "
               "Viceira (2001) finds it is the *variability* of income that "
               "reduces capacity, not its size.")
    c1, c2 = st.columns([1, 1])
    with c1:
        age = st.selectbox("Age band", list(ps.AGE_BANDS))
        stab = st.selectbox("How dependable is your income?", list(ps.STABILITY))
        dep = st.number_input("People financially dependent on you", 0, 10, 2)
    with c2:
        buf = st.selectbox("Months of expenses saved as an emergency fund",
                           list(ps.BUFFER), index=1)
        hor = st.selectbox("How long before you might need this money?",
                           list(ps.HORIZON), index=2)
    res = ps.score_capacity(age, stab, dep, buf, hor)
    st.session_state.capacity = res

    st.divider()
    a, b = st.columns([1.3, 1])
    with a:
        st.markdown("**How the score is built**")
        for k in ps.FACTORS:
            st.write(f"`{k:<11}` weight {ps.WEIGHTS[k]:.2f} × "
                     f"sub-score {res['subscores'][k]:.2f} = "
                     f"**{res['contributions'][k]:.3f}**")
        st.write(f"Weighted total: **{res['raw']:.3f}**")
    with b:
        st.metric("Capacity", f"{res['capped']:.3f}",
                  ps.TIER_NAMES[ps.to_tier(res['capped'])])
        if res["cap_fired"]:
            st.warning("**A hard cap applied.** " + " ".join(res["cap_reasons"]))
            st.caption(f"Weighted score was {res['raw']:.3f}; capped to "
                       f"{res['capped']:.3f}. A cap is a constraint, not an "
                       f"average — it cannot be smoothed away.")
        elif res["cap_applies"]:
            st.caption("**A cap rule matched but did not bind.** "
                       + " ".join(res["cap_reasons"])
                       + f" The weighted score ({res['raw']:.3f}) was already "
                         f"below the ceiling, so nothing was lowered.")
    footer()


def screen_tolerance():
    st.title("3. Risk tolerance")
    st.caption("Grable–Lytton Financial Risk Tolerance Scale, 13 items, one "
               "per screen. A validated instrument reused rather than invented.")
    d = st.session_state
    answered = sum(1 for a in d.gl_answers if a is not None)
    i = d.gl_index
    st.progress(answered / len(ps.GL_ITEMS),
                text=f"Question {i+1} of {len(ps.GL_ITEMS)} · "
                     f"{answered} answered")
    q, opts = ps.GL_ITEMS[i]
    st.subheader(q)
    choice = st.radio("Select one", ["— not answered —"] + opts,
                      index=(d.gl_answers[i] + 1) if d.gl_answers[i] is not None
                      else 0,
                      key=f"gl_{i}", label_visibility="collapsed")
    d.gl_answers[i] = None if choice == "— not answered —" else opts.index(choice)

    c1, c2, _ = st.columns([1, 1, 4])
    if c1.button("Back", disabled=(i == 0)):
        d.gl_index = max(0, i - 1)
        st.rerun()
    if c2.button("Next", type="primary", disabled=(i == len(ps.GL_ITEMS) - 1)):
        d.gl_index = min(len(ps.GL_ITEMS) - 1, i + 1)
        st.rerun()

    if answered == len(ps.GL_ITEMS):
        st.success("All 13 answered. Continue to **4. Profile summary**.")
    else:
        st.info(f"{len(ps.GL_ITEMS) - answered} still unanswered. The profile "
                f"stays incomplete until all 13 are answered — an unanswered "
                f"item is not scored as a cautious answer.")

    st.caption("Both the item wording **and the scoring key** here are "
               "structurally faithful stand-ins: same response formats, same "
               "13–47 raw range, same published band cut-points. The licensed "
               "instrument and its per-item point values are substituted "
               "before any real participant sees this.")
    footer()


def screen_summary():
    st.title("4. Profile summary")
    st.caption("The reconciliation, made visible. This screen runs real code.")
    d = st.session_state
    risk, complete, note = user_profile()

    if not complete:
        st.error(f"**Profile incomplete.** {note}")
        st.write("No tier is stored and no personalised recommendation is "
                 "issued. Screens 6 and 7 fall back to a labelled demonstration "
                 "profile until this is finished.")
        st.caption("This is the same rule as the degraded state on screen 9: "
                   "a labelled refusal, never a silent answer from thin data.")
        footer()
        return

    cap, tol = risk["capacity"], risk["tolerance"]
    raw = ps.gl_raw(d.gl_answers)
    rec = ps.reconcile(cap, tol)

    c1, c2, c3 = st.columns(3)
    c1.metric("Risk capacity", f"{cap:.3f}", ps.TIER_NAMES[ps.to_tier(cap)])
    c2.metric("Risk tolerance", f"{tol:.3f}",
              f"{ps.gl_band(raw)} (raw {raw:.0f})")
    c3.metric("Stored tier", rec["tier"].title(), f"λ = {rec['lambda']}")

    fig, ax = plt.subplots(figsize=(9.4, 2.2))
    ax.barh(["capacity", "tolerance"], [cap, tol],
            color=[BLUE if rec["binding"] == "capacity" else GREY,
                   BLUE if rec["binding"] == "tolerance" else GREY], height=0.62)
    for x in ps.TIER_CUTS:
        ax.axvline(x, ls="--", lw=1.4, c=GREY)
    ax.axvline(rec["score"], lw=3.0, c=RED)
    ax.text(rec["score"], 1.62, f"  binds here ({rec['score']:.2f})",
            color=RED, fontsize=12, va="center", fontweight="bold")
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.40, 0.70, 1.0])
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    show(fig)

    if rec["conflict"]:
        st.warning(f"**These disagree.** Your {rec['binding']} is the more "
                   f"restrictive of the two, so it binds and the stored tier "
                   f"is **{rec['tier']}**.")
    else:
        st.success(f"Both point to **{rec['tier']}**. "
                   f"{rec['binding'].title()} binds.")
    st.markdown(
        "We take the **more restrictive** of the two, never the average. "
        "Averaging would let a comfortable tolerance score hide a hard "
        "financial constraint. This is the FCA / ESMA suitability position "
        "(*willing* and *able* are assessed separately, and a recommendation "
        "must satisfy both) — it is not our invention. **FR-7.**")

    b = ps.action_bands(rec["lambda"])
    st.divider()
    st.markdown(f"**What this tier changes.** λ = {rec['lambda']} sets your "
                f"action bands: Buy above **{b['theta_buy']:+.2f}** volatility "
                f"units, Sell below **{b['theta_sell']:+.2f}**. These carry "
                f"through to screen 6.")
    footer()


def screen_selector():
    st.title("5. Choose a company")
    st.caption("A deliberately small universe, chosen so the data behind every "
               "decision is dense enough to mean something.")
    rows = []
    for t, name, arts, posts, days in fx.UNIVERSE:
        ok = arts >= fx.MIN_ARTICLES_PER_DAY
        rows.append({"Ticker": t, "Company": name,
                     "Articles/day": arts, "Social posts/day": posts,
                     "History (days)": days,
                     "Coverage": "dense" if arts >= 30 else
                                 ("adequate" if ok else "too thin")})
    st.dataframe(rows, use_container_width=True, hide_index=True)

    tickers = [r["Ticker"] for r in rows]
    st.session_state.ticker = st.selectbox(
        "Company", tickers, index=tickers.index(st.session_state.ticker))
    st.caption("Coverage density is shown per name because it is the reason "
               "the universe is curated. If a company has two articles on a "
               "day, mean polarity is noise; if it has forty, it is a "
               "measurement. This list is mocked.")
    st.success(f"**{st.session_state.ticker}** selected — screens 6, 7 and 8 "
               f"now show this company.")
    footer()


def screen_recommendation():
    st.title("6. Recommendation")
    base = base_record()
    anchor(base)
    r = apply_corruption(base)
    st.caption(f"{r['company']} ({r['ticker']}) · asked {r['ask_date']} · "
               f"most recent complete session: **{r['session_date']}** · "
               f"horizon {r['horizon']}")
    st.info(f"📅 {r['session_note']}")

    if not r["profile_complete"]:
        st.warning(f"**Demonstration profile in use.** {r['profile_note']} "
                   f"The tier below is not yours.")

    # Short labels: at four columns on a projector, "Calibrated confidence"
    # and "Moderate" both truncate to an ellipsis, which is worse than useless
    # on the one row the room is actually reading.
    # Unequal widths: "Moderate"/"conservative" overflow an equal quarter.
    c1, c2, c3, c4 = st.columns([1, 1, 1.15, 1.5])
    c1.metric("Verdict", r["decision"])
    c2.metric("Confidence", f"{r['probabilities'][r['decision']]:.0%}")
    c3.metric("Baseline", "agrees" if r["baseline_agrees"] else "disagrees")
    c4.metric("Tier", r["risk"]["tier"].title(), f"λ = {r['risk']['lambda']}")

    bands = ps.action_bands(r["risk"]["lambda"])
    st.write("**Class probabilities** · "
             + " · ".join(f"{k} {v:.2f}" for k, v in r["probabilities"].items()))
    st.caption(f"Calibrated with isotonic regression, so a reported "
               f"{r['probabilities'][r['decision']]:.0%} means "
               f"{r['probabilities'][r['decision']]:.0%}. On your "
               f"**{r['risk']['tier']}** tier the action bands are Buy above "
               f"{bands['theta_buy']:+.2f} and Sell below "
               f"{bands['theta_sell']:+.2f} volatility units — a more "
               f"loss-averse tier needs a larger expected move to justify "
               f"buying.")

    st.divider()
    st.subheader("What drove it")
    ranked = sorted(r["shap"].items(), key=lambda kv: abs(kv[1]))
    fig, ax = plt.subplots(figsize=(9.4, 3.9))
    ax.barh([k for k, _ in ranked], [v for _, v in ranked],
            color=[BLUE if v > 0 else ORANGE for _, v in ranked], height=0.68)
    ax.axvline(0, c=INK, lw=1.4)
    ax.set_xlabel(f"TreeSHAP contribution to {r['decision']}")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    show(fig)

    total = sum(r["shap"].values())
    st.caption(f"Blue pushes toward the verdict, orange pushes away. "
               f"Base value {r['base_value']:+.3f} + contributions "
               f"{total:+.3f} = {r['base_value'] + total:.3f}, the model "
               f"output — the additivity property **FR-6** tests on every "
               f"emitted decision.")

    st.divider()
    st.subheader("Explanation")
    text, report, attempts, used_template = explain(r, base)
    st.markdown(f"> {text}")
    if used_template:
        st.error(f"The generated explanation **failed verification** on "
                 f"{len(attempts)} attempts and was replaced by the "
                 f"deterministic template. See screen 7.")
    else:
        st.success("Verified — every claim checked against the record. "
                   "See screen 7.")
    footer()


def screen_verifier():
    st.title("7. Verifier report")
    st.markdown("### :green[This screen runs real code.]")
    st.caption("Everything else behind this interface is mocked. This is not. "
               "Groundedness here is decidable by symbolic checking, so the "
               "verifier needs only a decision record — a fixture record works "
               "exactly as well as a real one.")

    base = base_record()
    anchor(base)

    with st.expander("⚙ Operator control — corrupt the stored record live",
                     expanded=True):
        st.caption(f"This is the demonstration. Change a value the explanation "
                   f"already committed to, and watch the guard catch it. "
                   f"Currently showing **{base['ticker']}**, verdict "
                   f"**{base['decision']}**.")
        # Explicit value= plus write-back, rather than a pre-seeded key=.
        # Seeding session_state and then passing key= to the widget let the two
        # drift apart: the slider rendered at its minimum while the verifier
        # still read the seeded value, so the screen could show PASS next to a
        # corrupted record. On the one screen that has to be trustworthy in
        # front of a panel, that is the worst possible bug.
        c1, c2, c3 = st.columns([2, 2, 1])
        prob = c1.slider(
            f"Stored P({base['decision']}) in the decision record", 0.00, 1.00,
            value=float(st.session_state.corrupt_prob), step=0.01,
            help="The explanation states the original figure. Move this and "
                 "the numeric check must fail.")
        rsi = c2.slider(
            "Stored SHAP contribution of rsi_14", -0.20, 0.20,
            value=float(st.session_state.corrupt_rsi_shap), step=0.01,
            help="The explanation says RSI pushes toward Buy, i.e. away from "
                 "the verdict. Make this positive and the sign check must fail.")
        st.session_state.corrupt_prob = prob
        st.session_state.corrupt_rsi_shap = rsi
        c3.write("")
        if c3.button("Reset record"):
            st.session_state.corrupt_for = None      # forces re-anchor
            st.rerun()

        # Only now, with the sliders' current values in hand.
        r = apply_corruption(base)
        if not pristine(r, base):
            st.warning("The stored record has been altered. The explanation "
                       "below was written against the original.")

    text, report, attempts, used_template = explain(r, base)

    st.divider()
    m, p = report["metrics"], report["passes"]
    cols = st.columns(4)
    # Short enough not to ellipsis at four columns on a projector.
    labels = [("numeric_fidelity", "Numeric fidelity", "≥ 0.98"),
              ("directional_consistency", "Direction", "≥ 0.95"),
              ("claim_recall", "Claim recall", "≥ 0.80"),
              ("unverifiable_rate", "Unverifiable", "≤ 0.15")]
    for col, (key, label, bound) in zip(cols, labels):
        col.metric(label, f"{m[key]:.2f}",
                   f"{'pass' if p[key] else 'FAIL'} ({bound})",
                   delta_color="normal" if p[key] else "inverse")

    st.write("**Attempts**")
    for name, rep in attempts:
        (st.success if rep["verdict"] == "PASS" else st.error)(
            f"{name} — **{rep['verdict']}**")
    if used_template:
        st.error("Both attempts failed. Replaced by the deterministic "
                 "template, which is grounded by construction. An unverified "
                 "explanation is never emitted.")
        st.markdown("**What the user sees instead:**")
        st.markdown(f"> {text}")
    else:
        st.success("**PASS** — this explanation is released to the user.")

    st.divider()
    st.subheader("Claim by claim")
    icon = {"correct": "✅", "incorrect": "❌", "unverifiable": "⚠️"}
    st.dataframe(
        [{"": icon[c["result"]], "Claim": c["text"], "Check": c["kind"],
          "Result": c["result"], "Detail": c["detail"]}
         for c in report["claims"]],
        use_container_width=True, hide_index=True)

    if report["orphan_numbers"]:
        st.error(f"Numbers in the prose that match nothing in the record: "
                 f"{report['orphan_numbers']}")

    c1, c2 = st.columns(2)
    c1.caption(f"**Top {len(report['top_drivers'])} drivers by |SHAP|:** "
               + ", ".join(report["top_drivers"]))
    c2.caption(f"**Cited by the explanation:** "
               + ", ".join(report["cited_drivers"]))
    st.info("A groundedness score alone is gameable: a model that speaks "
            "vaguely enough to make every claim unverifiable scores a perfect "
            "1.0 while saying nothing. Acceptance is stated over all four "
            "measures, never the headline number alone.")
    st.caption("**What this does and does not prove.** The claim payload here "
               "is authored by us, not emitted by a language model, so this "
               "demonstrates that the *checker* is correct — not yet that it "
               "catches a real model. That is the right scope for proposal "
               "stage: the verifier is built first, and the explainer is "
               "measured against it afterwards.")
    footer()


def screen_followup():
    st.title("8. Follow-up questions")
    st.caption("Answered from the same verified record. A follow-up is not "
               "free chat — it re-enters the same verified path.")
    r = live_record()
    bands = ps.action_bands(r["risk"]["lambda"])
    st.caption(f"Showing **{r['ticker']}** on a **{r['risk']['tier']}** "
               f"profile.")
    for q, a in fx.follow_ups_for(r, bands).items():
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.write(a)
    st.chat_input("Ask about this recommendation (scripted at this stage)")
    st.caption("Responses are scripted fixtures rendered from the record. The "
               "language model is the system's mouth, not its brain — it never "
               "decides anything.")
    footer()


def screen_degraded():
    st.title("9. Degraded state")
    st.caption("What the user sees when a feed is down or history is thin. "
               "A labelled refusal, never a stale answer presented as fresh. "
               "This state machine is real. **FR-12.**")
    # Same explicit-value pattern as screen 7 - never key= alongside a
    # pre-seeded session_state entry.
    c1, c2 = st.columns(2)
    feed_up = c1.toggle("Live news feed reachable",
                        value=bool(st.session_state.feed_up))
    days = c2.slider("Days of accumulated scored headlines", 0, 30,
                     value=min(int(st.session_state.history_days), 30))
    st.session_state.feed_up = feed_up
    st.session_state.history_days = days

    st.divider()
    if not feed_up:
        st.error("**Degraded — live feed unavailable.**")
        st.write(f"Serving the last good cached features, from "
                 f"**{fx.SESSION_DATE} close**. The data behind this view is "
                 f"stale. No recommendation is issued.")
    elif days < fx.MIN_HISTORY_DAYS:
        st.error(f"**Degraded — insufficient history.** {days} days of scored "
                 f"headlines; {fx.MIN_HISTORY_DAYS} are required.")
        st.write("The 3-day and 7-day sentiment momentum features cannot be "
                 "computed yet. This instance will answer once it has enough "
                 "history. It will not answer from thin data.")
    else:
        st.success(f"**Healthy.** Feed reachable, {days} days of scored "
                   f"headlines available.")

    _, complete, note = user_profile()
    if not complete:
        st.warning(f"**Profile incomplete.** {note} This is the third degraded "
                   f"path, and it behaves the same way: label it, do not "
                   f"guess.")
    footer()


def screen_operator():
    st.title("10. Operator view")
    st.caption("Leakage suite status and the proposal-stage spikes.")

    st.subheader("Leakage control suite")
    st.dataframe([{"Control": c, "Status": s} for c, s in fx.LEAK_SUITE],
                 use_container_width=True, hide_index=True)
    st.caption(":orange[**This table is a fixture** — the planned control set, "
               "not a live CI readout. The suite is built across Iterations 1–3. "
               "The two sections below are real: they read the spike result "
               "files on disk.]")

    st.divider()
    st.subheader("Spike 1 — leakage detection")
    path = os.path.join(POC_DIR, "poc_results.json")
    if os.path.exists(path):
        data = json.load(open(path))
        st.caption(f"snapshot `{data['snapshot_sha256']}` · seed "
                   f"{data['config']['seed']} · "
                   f"{len(data['config']['tickers'])} tickers")
        rows = []
        for h, arms in data["results"].items():
            for a in arms:
                rows.append({"Horizon": f"{h}d", "Arm": a["config"],
                             "macro-F1": round(a["macro_f1"], 4),
                             "Chance": round(a["chance_f1"], 4),
                             "Lift": round(a["lift_over_chance"], 4)})
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.warning("**An assumption was disproved.** We assumed the 1-day "
                   "negative control would catch all leakage. It does not — "
                   "fold-overlap leakage is invisible at 1 day because 1-day "
                   "labels do not overlap. Controls must run at the label "
                   "geometry of the primary horizon. Gate A was amended.")
    else:
        st.info("poc_results.json not found — run ../poc_leakage_spike.py")

    st.divider()
    st.subheader("Spike 2 — risk-profile weight sensitivity")
    path2 = os.path.join(POC_DIR, "poc_risk_results.json")
    if os.path.exists(path2):
        d2 = json.load(open(path2))["results"]
        inv, eq, caps = d2["invariance"], d2["equal_weights"], d2["cap_ablation"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("FR-7 property test",
                  "PASS" if d2["fr7_property_test"]["passes"] else "FAIL",
                  f"{d2['fr7_property_test']['pairs_checked']:,} pairs")
        c2.metric("Tier invariance (strict)", f"{inv['invariant_share']:.1%}",
                  f"{inv['n_draws']} weight draws")
        c3.metric("Agreement with equal weights", f"{eq['agreement']:.1%}",
                  f"κ = {eq['cohen_kappa']}")
        c4.metric("Invariance gained by caps",
                  f"+{caps['invariance_gained_by_caps']:.1%}",
                  f"{caps['personas_where_a_cap_fires']} personas capped")
        st.caption("The weights are inert for most users and decisive for a "
                   "named minority. The boundary personas are listed in the "
                   "results file rather than left to be discovered.")
    else:
        st.info("poc_risk_results.json not found — run "
                "../poc_risk_profile_spike.py")
    footer()


RENDER = {
    "1. Sign in": screen_signin,
    "2. Risk capacity": screen_capacity,
    "3. Risk tolerance": screen_tolerance,
    "4. Profile summary": screen_summary,
    "5. Choose a company": screen_selector,
    "6. Recommendation": screen_recommendation,
    "7. Verifier report": screen_verifier,
    "8. Follow-up questions": screen_followup,
    "9. Degraded state": screen_degraded,
    "10. Operator view": screen_operator,
}


def main():
    init()
    st.sidebar.title("Investify")
    st.sidebar.caption("F26-003-QuantamentalAI · proposal-stage prototype")
    choice = st.sidebar.radio("Screen", [s for s, _ in SCREENS],
                              label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption("**What is real behind each screen**")
    for name, kind in SCREENS:
        mark = "🟢" if kind.startswith("REAL") else (
            "🔵" if kind in ("real", "real state machine") else "⚪")
        st.sidebar.caption(f"{mark} {name.split('. ')[1]} — *{kind}*")
    st.sidebar.divider()
    st.sidebar.caption("The user journey does not announce which parts are "
                       "mocked. This panel does, because the examiner is "
                       "entitled to know and the user is not being misled.")
    RENDER[choice]()


if __name__ == "__main__":
    main()
