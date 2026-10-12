"""Deterministic English explanation from a decision record (brief section 7).

Grounded by construction: every sentence is generated directly from
`DecisionRecord` fields, never invented, so the explanation cannot state a
number the record does not contain. That is what makes it possible for a
non-LLM verifier (`explain/verifier.py`) to decide groundedness by code
rather than by another model's opinion -- there is no gap between "what
was said" and "what the model actually computed" for this text to fall
into.

Renders two representations of the same claims:

1. `Explanation.payload` -- a structured, JSON-able dict checked
   independently from the displayed text.
2. `Explanation.text` -- controlled English carrying the identical
   numbers, checked whether or not a payload is supplied.
   One sentence per line, so the verifier's line-level claim
   decomposition (check 6) never has to guess where a sentence ends
   inside a decimal number (e.g. "...contribution of +0.1234, ranked...").

Same `DecisionRecord` in -> byte-identical output, always: no randomness,
no model, no formatting that depends on anything but the record's own
fields. `explain/fixtures.py` is the only place deliberately-wrong text
gets produced, and it is clearly labelled as doing so.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from investify.decision_record import DecisionRecord, FeatureContribution
from investify.explain.context import FEATURES, ATTRIBUTION_SCOPE, attribution_direction, build_context

# Fixed formatting widths -- the verifier's prose regexes (explain/verifier.py)
# are written against EXACTLY this output. Changing either format string
# without updating the matching regex will make the fallback path silently
# stop parsing lines it should be reading, so treat this as a two-file change.
_PCT_FMT = "{:.2f}"
_NUM_FMT = "{:.4f}"

_DECISION_CLASSES_IN_ORDER = ("Buy", "Hold", "Sell")


@dataclass(frozen=True)
class Explanation:
    """A rendered explanation: prose, plus (optionally) its structured twin.

    `payload` is `None` exactly when the caller asked for prose-only
    output -- that is the trigger for the verifier's regex fallback path,
    not an accident of a missing field.
    """

    text: str
    payload: dict | None


def _decision_line(record: DecisionRecord) -> str:
    return (
        f"{record.ticker} decision for session {record.session_date} "
        f"({record.horizon_days}-day horizon): {record.decision}."
    )


def _confidence_line(record: DecisionRecord) -> str:
    pct = _PCT_FMT.format(record.confidence * 100)
    return f"Calibrated confidence in this decision: {pct}%."


def _probability_line(record: DecisionRecord) -> str:
    parts = ", ".join(
        f"{cls}: {_PCT_FMT.format(record.probabilities[cls] * 100)}%"
        for cls in _DECISION_CLASSES_IN_ORDER
    )
    return f"Full probability breakdown -- {parts}."


def _feature_line(record: DecisionRecord, contribution: FeatureContribution) -> str:
    value = (_NUM_FMT.format(contribution.value) if contribution.value is not None
             and isfinite(contribution.value) else "missing")
    shap = contribution.shap_value
    sign = "+" if shap >= 0 else ""
    signed_shap = f"{sign}{_NUM_FMT.format(shap)}"
    return (
        f"{contribution.name} (value {value}) {contribution.direction} the "
        f"{record.decision} decision with a SHAP contribution of {signed_shap}, "
        f"ranked #{contribution.rank} of {len(record.top_k)}."
    )


def _notice_line(record: DecisionRecord) -> str:
    return record.non_advice_notice


def render(record: DecisionRecord, *, include_payload: bool = True) -> Explanation:
    """Render the deterministic explanation for `record`.

    Every top-k contributor gets its own line, in the record's own
    rank order -- the template never re-sorts or filters what
    `rank_contributions` already decided.

    `include_payload=False` produces prose only (`payload=None`). This is
    not a debugging knob: it is what exercises the verifier's prose-regex
    fallback path (check 1) instead of its JSON-payload path, and
    `tests/test_verifier.py` calls it explicitly to prove that path is
    real code, not dead code.
    """
    lines = [
        _decision_line(record),
        _confidence_line(record),
        _probability_line(record),
        *[_feature_line(record, c) for c in record.top_k],
        _notice_line(record),
    ]
    text = "\n".join(lines)

    if not include_payload:
        return Explanation(text=text, payload=None)

    payload = {
        "ticker": record.ticker,
        "session_date": record.session_date,
        "horizon_days": record.horizon_days,
        "decision": record.decision,
        "confidence": record.confidence,
        "probabilities": dict(record.probabilities),
        "contributions": [
            {
                "name": c.name,
                "value": c.value if c.value is not None and isfinite(c.value) else None,
                "shap_value": c.shap_value,
                "rank": c.rank,
                "direction": c.direction,
            }
            for c in record.top_k
        ],
        "non_advice_notice": record.non_advice_notice,
    }
    return Explanation(text=text, payload=payload)


def render_guided(record: DecisionRecord) -> Explanation:
    """Deterministic comparator covering every feature and family contribution.

    A local LLM receives the same definitions, so this is a necessary
    comparator for claims about its added value over a numeric template.
    """
    baseline = render(record)
    context = build_context(record, corpus="guided explanation")
    evidence = [{"name": row["feature"], "value": row["value"],
                 "shap_value": row["shap_value"], "direction": row["effect_on_predicted_class"]}
                for row in context["features"]]
    families = [{"name": name, "shap_value": value, "direction": attribution_direction(value)}
                for name, value in context["family_contributions"].items()]
    definitions = [{"name": name, "meaning": FEATURES[name][2]}
                   for name in record.feature_names if name in FEATURES]
    lines = baseline.text.splitlines()
    additional = []
    for item in evidence:
        value = _NUM_FMT.format(item["value"]) if item["value"] is not None else "missing"
        additional.append(f"Recorded feature {item['name']} (value {value}): "
                          f"SHAP {item['shap_value']:+.4f} for {record.decision}; effect {item['direction']}.")
    additional.extend(f"Family contribution for {item['name']}: SHAP {item['shap_value']:+.4f} "
                      f"for {record.decision}; effect {item['direction']}." for item in families)
    additional.extend(f"Feature definition for {item['name']}: {item['meaning']}" for item in definitions)
    additional.append(ATTRIBUTION_SCOPE)
    lines[-1:-1] = additional
    payload = dict(baseline.payload, definitions=definitions, feature_evidence=evidence,
                   family_contributions=families, attribution_scope=ATTRIBUTION_SCOPE)
    return Explanation(text="\n".join(lines), payload=payload)
