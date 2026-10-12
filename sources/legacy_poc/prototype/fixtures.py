"""
FIXTURE DATA.  MOCKED - and we say so, everywhere it is used.

Section 18 of the proposal is explicit about what is not real at this stage:
the trained engine, the sentiment pipeline, the point-in-time store and the
live feeds are all mocked. Building them properly is the work of two semesters,
and a rushed version would prove nothing about whether the finished one is
correct.

What IS real in this prototype: risk scoring (profile_scoring.py) and the
explanation verifier (verifier.py). Those are the two places a fixture is as
good as the real thing, because neither depends on a trained model.

The NVDA record is the worked example from section 10.8, number for number,
so that the document and the prototype cannot drift apart. Records for the
other tickers are deterministic jitters of it - clearly fixture data, but
enough that selecting a company on screen 5 actually changes screen 6.

TWO PROPERTIES HELD BY CONSTRUCTION
  - FR-6 additivity: base_value is always computed as
    P(decision) - sum(shap), so the attribution vector sums to the model
    output exactly. The first version of this file hard-coded base_value at
    0.41 against a SHAP sum of 0.24 and a P(Hold) of 0.58 - a 0.07
    discrepancy, on a screen that asserts the sum holds. Deriving it removes
    the possibility of that class of error rather than correcting one instance.
  - Trading calendar: session dates are real NYSE sessions. See SESSION_NOTE.
"""

import hashlib

# ---------------------------------------------------------------------------
# The session. Deliberately spans a market holiday.
# ---------------------------------------------------------------------------
# The user asks on Tuesday 8 September 2026. The most recent COMPLETE session
# is Friday 4 September, because Monday 7 September was Labor Day and the
# exchange was shut. An earlier version of this file used 7 September and
# called it "the Monday close", which is exactly the mistake the two-calendar
# layer exists to prevent - so the fixture now exercises it instead.
ASK_DATE = "2026-09-08"          # Tuesday, session not yet closed
SESSION_DATE = "2026-09-04"      # Friday, the last complete session
SESSION_NOTE = ("Monday 7 September was Labor Day and the exchange was closed, "
                "so the most recent complete session is Friday 4 September. "
                "Text published over the long weekend maps forward to the next "
                "tradable session, never back onto Friday's bar.")

UNIVERSE = [
    # ticker, name, articles/day, posts/day, days of history
    ("NVDA", "NVIDIA",            41, 380, 2180),
    ("TSLA", "Tesla",             52, 610, 2180),
    ("AAPL", "Apple",             48, 340, 2180),
    ("MSFT", "Microsoft",         33, 150, 2180),
    ("AMZN", "Amazon",            37, 190, 2180),
    ("META", "Meta Platforms",    31, 210, 2180),
    ("AMD",  "Advanced Micro",    22, 165, 2180),
    ("PLTR", "Palantir",          14,  95,  980),
]
NAMES = {t: n for t, n, *_ in UNIVERSE}

MIN_ARTICLES_PER_DAY = 8      # below this, coverage is too thin to aggregate
MIN_HISTORY_DAYS = 7          # momentum features need a week of scored text

HEADLINES = [
    ("2026-09-04 15:42 ET", "Reuters", "Nvidia expands data-centre partnership "
     "with major cloud provider", "news", +0.62),
    ("2026-09-04 14:10 ET", "Bloomberg", "Analysts raise price targets ahead of "
     "chip demand update", "news", +0.48),
    ("2026-09-04 11:05 ET", "MarketWatch", "Supply chain checks point to steady "
     "shipments this quarter", "news", +0.21),
    ("2026-09-04 16:31 ET", "Reddit r/stocks", "anyone else think this run is "
     "way overextended", "social", -0.41),
    ("2026-09-04 13:58 ET", "StockTwits", "taking profits here, risk/reward is "
     "not there anymore", "social", -0.33),
    ("2026-09-07 09:12 ET", "Reddit r/investing", "valuation is getting hard to "
     "justify at these levels", "social", -0.28),
]

# ---------------------------------------------------------------------------
# The canonical record. Section 10.8, unchanged.
# ---------------------------------------------------------------------------
_NVDA_FEATURES = {
    "rsi_14": 38.2, "macd_hist": -0.41, "dist_sma200": -0.061,
    "bollinger_pos": 0.22, "obv_slope": -0.003,
    "news_polarity": 0.31, "news_mom_3d": 0.12, "news_mom_7d": -0.04,
    "news_volume_z": 1.8, "news_dispersion": 0.44,
    "social_polarity": -0.18, "social_mom_3d": -0.22, "social_mom_7d": -0.15,
    "social_volume_z": 2.6, "social_dispersion": 0.71,
    "divergence_news_social": 0.49,
    "vol_20d": 0.034,
}
_NVDA_SHAP = {
    "divergence_news_social": 0.14,
    "social_mom_3d": 0.09,
    "vol_20d": 0.05,
    "dist_sma200": 0.03,
    "rsi_14": -0.06,
    "news_polarity": -0.02,
    "macd_hist": 0.01,
}
_NVDA_PROBS = {"Buy": 0.34, "Hold": 0.58, "Sell": 0.08}

DEFAULT_RISK = {"tier": "moderate", "capacity": 0.55, "tolerance": 0.67,
                "lambda": 2.25}


def _assemble(ticker, feats, shap, probs, risk):
    decision = max(probs, key=probs.get)
    return {
        "ticker": ticker,
        "company": NAMES.get(ticker, ticker),
        "ask_date": ASK_DATE,
        "session_date": SESSION_DATE,
        "session_note": SESSION_NOTE,
        "horizon": "1 week",
        "decision": decision,
        "probabilities": probs,
        # FR-6 by construction: attribution + base == model output, exactly.
        "base_value": round(probs[decision] - sum(shap.values()), 6),
        "features": feats,
        "shap": shap,
        "risk": risk,
        "model_version": "xgb-1w-fixture-0",
        "snapshot_hash": "fixture-not-a-real-run",
        "baseline_agrees": True,
    }


def record_for(ticker="NVDA", risk=None):
    """NVDA is the section 10.8 record verbatim. Other tickers are a
    deterministic jitter of it, seeded from the ticker so the same company
    always shows the same thing. Fixture data, labelled as such on screen."""
    risk = dict(risk or DEFAULT_RISK)
    if ticker == "NVDA":
        return _assemble("NVDA", dict(_NVDA_FEATURES), dict(_NVDA_SHAP),
                         dict(_NVDA_PROBS), risk)

    seed = int(hashlib.sha256(ticker.encode()).hexdigest()[:8], 16)

    def jitter(i, spread):
        """Deterministic pseudo-noise in [-spread, +spread]. A tiny LCG keeps
        this dependency-free; a prototype does not need numpy for six numbers."""
        x = (seed + i * 2654435761) % 2147483647
        return ((x / 2147483647) * 2 - 1) * spread

    # Jitter is MULTIPLICATIVE and bounded, for two reasons that both matter.
    #
    # Signs: a positive scale factor cannot flip a sign, so "social momentum
    # has fallen" and "RSI pushes away from the verdict" stay true for every
    # ticker. An additive jitter flipped them, and every non-NVDA company then
    # failed its own verifier - the explanation was NVDA's narrative wearing
    # another company's numbers.
    #
    # Ranking: SHAP is scaled within +/-15%, which is tight enough that the
    # largest contributor (0.14) cannot be overtaken by the second (0.09), so
    # the "strongest driver" claim holds, and the top-5 set stays the top-5 set
    # so claim recall does not drift.
    #
    # Rounding matches the precision the prose prints at. Otherwise the record
    # holds 33.89, the sentence says "33.9", and the free-prose sweep reports a
    # number that matches nothing - a false alarm from our own formatting.
    DISPLAY_DP = {"rsi_14": 1, "vol_20d": 3, "obv_slope": 3}

    feats = {}
    for i, (k, v) in enumerate(_NVDA_FEATURES.items()):
        feats[k] = round(v * (1 + jitter(i, 0.45)), DISPLAY_DP.get(k, 2))
    feats["divergence_news_social"] = round(
        feats["news_polarity"] - feats["social_polarity"], 2)

    shap = {k: round(v * (1 + jitter(i + 50, 0.15)), 4)
            for i, (k, v) in enumerate(_NVDA_SHAP.items())}

    raw = {"Buy": 0.34 + jitter(90, 0.30),
           "Hold": 0.58 + jitter(91, 0.30),
           "Sell": 0.08 + jitter(92, 0.12)}
    raw = {k: max(v, 0.02) for k, v in raw.items()}
    total = sum(raw.values())
    probs = {k: round(v / total, 4) for k, v in raw.items()}

    rec = _assemble(ticker, feats, shap, probs, risk)
    rec["baseline_agrees"] = (seed % 3 != 0)
    rec["snapshot_hash"] = f"fixture-jitter-{seed:08x}"
    return rec


# ---------------------------------------------------------------------------
# The explainer's output: prose PLUS the structured claim payload it emits
# under constrained decoding. Section 13 prefers the payload and keeps prose
# pattern-matching as the fallback, so the fixture carries both.
#
# This is a FUNCTION of the record, not a constant, because that is what a real
# explainer is: it receives a completed decision and renders it. Hard-coding
# "moderate" here meant the sentence about the user's risk tier was true only
# for one user, and stayed on screen unchanged for every other one.
# ---------------------------------------------------------------------------
def generation_for(record):
    tier = record["risk"]["tier"]
    f, s = record["features"], record["shap"]
    d = record["decision"]
    p = record["probabilities"][d]
    top = max(s, key=lambda k: abs(s[k]))
    prose = (
        f"{record['ticker']} leans {d} at {p:.0%} confidence. The strongest "
        f"driver is a disagreement between the two sentiment registers: news "
        f"coverage is mildly positive at {f['news_polarity']:+.2f} while social "
        f"discussion has turned negative at {f['social_polarity']:+.2f}, and "
        f"that divergence pushes toward waiting. Social sentiment momentum has "
        f"fallen over the last three days. RSI at {f['rsi_14']:.1f} is mildly "
        f"oversold and pushes the other way, toward Buy, but not far enough to "
        f"change the verdict. Volatility is elevated. On your {tier} risk "
        f"tier, this is not a signal the system would act on."
    )
    claims = [
        {"text": f"{d} at {p:.0%} confidence",
         "kind": "numeric", "field": d, "value": p},
        {"text": "the strongest driver is the sentiment-register disagreement",
         "kind": "rank", "field": "divergence_news_social", "position": 1},
        {"text": f"news coverage is mildly positive at {f['news_polarity']:+.2f}",
         "kind": "numeric", "field": "news_polarity", "value": f["news_polarity"]},
        {"text": f"social discussion has turned negative at {f['social_polarity']:+.2f}",
         "kind": "numeric", "field": "social_polarity",
         "value": f["social_polarity"]},
        {"text": "that divergence pushes toward waiting",
         "kind": "sign", "field": "divergence_news_social", "direction": "toward"},
        {"text": "social sentiment momentum has fallen over three days",
         "kind": "value_sign", "field": "social_mom_3d", "direction": "fell"},
        {"text": f"RSI at {f['rsi_14']:.1f}",
         "kind": "numeric", "field": "rsi_14", "value": f["rsi_14"]},
        {"text": "RSI pushes the other way, toward Buy",
         "kind": "sign", "field": "rsi_14", "direction": "away"},
        {"text": "volatility is elevated",
         "kind": "unverifiable", "field": "vol_20d"},
        {"text": f"on your {tier} risk tier",
         "kind": "tier", "value": tier},
    ]
    return {"prose": prose, "claims": claims, "top_driver": top}


def regeneration_for(record):
    """The second sample, after a failed verification. In the real system this
    is a fresh generation at the same temperature. Here it is deliberately the
    same output, so the panel sees the path that matters: attempt 1 fails,
    attempt 2 fails, the deterministic template is substituted."""
    return generation_for(record)


NVDA_RECORD = record_for("NVDA")
NVDA_GENERATION = generation_for(NVDA_RECORD)


def follow_ups_for(record, bands):
    d = record["decision"]
    f, s = record["features"], record["shap"]
    r = record["risk"]
    return {
        "Why not Buy?":
            f"Buy sits at {record['probabilities']['Buy']:.0%} against {d} at "
            f"{record['probabilities'][d]:.0%}. The two registers disagree "
            f"(divergence {f['divergence_news_social']:+.2f}, the largest "
            f"single contribution at {s['divergence_news_social']:+.2f} toward "
            f"{d}), and 20-day volatility of {f['vol_20d']:.3f} is contributing "
            f"{s['vol_20d']:+.2f} toward waiting. RSI at {f['rsi_14']:.1f} does "
            f"push toward Buy at {s['rsi_14']:+.2f}, but it is outweighed. "
            f"Nothing here states a number the engine did not produce.",
        "What would change this to a Buy?":
            f"On this record, the divergence term would have to fall. Social "
            f"polarity is {f['social_polarity']:+.2f} against news at "
            f"{f['news_polarity']:+.2f}; if social sentiment recovered toward "
            f"zero the divergence contribution of "
            f"{s['divergence_news_social']:+.2f} toward {d} would shrink. This "
            f"is a description of the record, not a forecast - the system does "
            f"not simulate counterfactuals.",
        "How confident should I be?":
            f"{record['probabilities'][d]:.0%} is a calibrated probability, not "
            f"a score: across the held-out fold, cases the model called at "
            f"{record['probabilities'][d]:.0%} came true about "
            f"{record['probabilities'][d]:.0%} of the time. The transparent "
            f"linear baseline "
            f"{'also says ' + d if record['baseline_agrees'] else 'disagrees'}, "
            f"which {'raises' if record['baseline_agrees'] else 'lowers'} "
            f"confidence.",
        "What does my risk tier change?":
            f"Your tier is {r['tier']}, with a loss-aversion coefficient of "
            f"{r['lambda']}. That sets the Buy threshold at "
            f"{bands['theta_buy']:+.2f} volatility units and the Sell threshold "
            f"at {bands['theta_sell']:+.2f}. A conservative tier needs +0.61 to "
            f"call Buy; an aggressive tier only +0.39.",
    }


LEAK_SUITE = [
    ("as-of join semantics (backward, max look-back)", "pass"),
    ("session mapping: weekend, holiday, half-day", "pass"),
    ("backward-only rolling windows", "pass"),
    ("fold-local scaling (no test rows in any scaler)", "pass"),
    ("negative control @ 1-day label geometry", "at chance"),
    ("negative control @ 5-day label geometry", "at chance"),
    ("leak canary (D_LOOKAHEAD must still fire)", "firing"),
    ("live-vs-backtest parity", "not yet built"),
]
