"""Risk profiling for the demo — display only.

Read the scope note at the top of docs/phase2_4_plan.md: risk profiling is
NOT a model input in this spike. The model's inputs are technical indicators
and sentiment features, nothing else. The tier produced here is shown
alongside a decision and written into the decision record's `risk_tier`
field, and it conditions nothing.

Two axes are asked about separately because they are different things:

* Capacity — what a person's finances can absorb. Objective.
* Tolerance — what a person is willing to sit through. Subjective, measured
  with a subset of the Grable-Lytton instrument.

They are reconciled by taking the MORE RESTRICTIVE of the two. Someone with
a large buffer and no stomach for a drawdown is not an aggressive investor,
and neither is someone with an appetite for risk and rent due next month.
"""
import streamlit as st

from investify.decision_record import RISK_TIERS

TIER_ORDER = {tier: i for i, tier in enumerate(RISK_TIERS)}  # Conservative < Balanced < Aggressive

CAPACITY_QUESTIONS = [
    (
        "How many months of expenses could you cover if your income stopped tomorrow?",
        ["Less than 3", "3 to 6", "More than 6"],
    ),
    (
        "When would you need to withdraw this money?",
        ["Within 2 years", "2 to 7 years", "More than 7 years"],
    ),
    (
        "What share of your total savings would this represent?",
        ["Most of it", "About half", "A small part"],
    ),
]

# Grable-Lytton subset (1999), items on investment risk attitude.
TOLERANCE_QUESTIONS = [
    (
        "In general, how would your friends describe you as a risk taker?",
        ["Avoids risk where possible", "Takes risk after research", "A real gambler"],
    ),
    (
        "Your investment falls 20% in a month. You:",
        ["Sell to stop further loss", "Hold and wait", "Buy more at the lower price"],
    ),
    (
        "Which would you rather have?",
        [
            "A certain gain of $1,000",
            "A 50% chance of $5,000 and 50% of nothing",
            "A 20% chance of $25,000 and 80% of nothing",
        ],
    ),
]


def score_to_tier(score: float) -> str:
    """Map a mean answer index in [0, 2] onto the three tiers."""
    if score < 0.67:
        return "Conservative"
    if score < 1.34:
        return "Balanced"
    return "Aggressive"


def reconcile(capacity_tier: str, tolerance_tier: str) -> str:
    """Take the more restrictive of capacity and tolerance.

    Pure and order-independent, so it can be reasoned about directly:
    reconcile(a, b) == reconcile(b, a), and the result is never higher than
    either input.
    """
    for tier in (capacity_tier, tolerance_tier):
        if tier not in TIER_ORDER:
            raise ValueError(f"unknown risk tier {tier!r}; expected one of {RISK_TIERS}")
    return min((capacity_tier, tolerance_tier), key=lambda t: TIER_ORDER[t])


def _ask(questions: list[tuple[str, list[str]]], key_prefix: str) -> str:
    indices = []
    for i, (question, options) in enumerate(questions):
        choice = st.radio(question, options, key=f"{key_prefix}_{i}", index=1)
        indices.append(options.index(choice))
    return score_to_tier(sum(indices) / len(indices))


def render_quiz() -> tuple[str, str, str]:
    """Render both question sets. Returns (capacity, tolerance, reconciled)."""
    st.markdown("**Capacity** — what your finances can absorb")
    capacity = _ask(CAPACITY_QUESTIONS, "capacity")

    st.markdown("**Tolerance** — what you are willing to sit through")
    tolerance = _ask(TOLERANCE_QUESTIONS, "tolerance")

    return capacity, tolerance, reconcile(capacity, tolerance)
