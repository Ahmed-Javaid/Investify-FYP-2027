"""
THE DETERMINISTIC EXPLANATION VERIFIER.  REAL CODE - THIS IS THE LIVE PATH.

Screen 7 of the prototype runs this for real. Everything else behind the
interface is mocked and we say so; this is not.

Why it can be real this early, which is the point worth making to the panel:
groundedness here is DECIDABLE BY CODE. The explainer's input is entirely
structured and numeric, so whether a sentence is grounded is a symbolic check
against a record - not a matter of another model's opinion. That means the
verifier does not need a trained engine to be correct. It needs a decision
record, and a fixture record works exactly as well as a real one.

The six checks are section 13 of the proposal:
    1. Numeric extraction          - every number in the text is pulled out
    2. Tolerance matching          - each must match the record within tolerance
    3. Sign and direction          - a feature said to push one way must
    4. Rank consistency            - cited drivers must come from the top
    5. Closed-vocabulary validation- every feature name must exist
    6. Claim-level scoring         - correct / incorrect / unverifiable

One deliberate change from the proposal, and we should own it at the defence.
Section 13 defines claim recall as verifiable claims over total claims, which
makes it exactly 1 - unverifiable_rate. Reporting both then measures one thing
twice, and neither catches the failure the proposal says recall exists to
catch ("an explanation that stays safe by saying almost nothing"). Recall here
is measured against the RECORD instead: of the top-k SHAP drivers, how many did
the explanation actually mention. An explanation that hedges its way to a
perfect groundedness score now fails recall, which is the intended behaviour.
"""

import re

# Per-field tolerances. Declared, not implicit - "within tolerance" is
# meaningless until the tolerance is written down.
TOL_PROBABILITY = 0.005     # 0.5 percentage points
TOL_FEATURE_ABS = 0.005
TOP_K = 5                   # how many SHAP drivers count as "the top"

THRESHOLDS = {
    "numeric_fidelity": 0.98,
    "directional_consistency": 0.95,
    "claim_recall": 0.80,
    "unverifiable_rate": 0.15,      # this one is an upper bound
}

_NUM = re.compile(r"[-+−]?\d+(?:\.\d+)?%?")


def _to_float(tok):
    tok = tok.replace("−", "-")
    if tok.endswith("%"):
        return float(tok[:-1]) / 100.0
    return float(tok)


def extract_numbers(prose):
    """Check 1. Free-prose fallback path. The primary path is the structured
    payload the explainer emits alongside the prose under constrained decoding;
    this exists so that a claim made ONLY in prose still gets caught.

    KNOWN LIMITATION, stated rather than discovered: the orphan sweep below
    accepts a prose number if it matches ANY value in the record, not the
    specific value the sentence is about. A fabricated figure that happens to
    coincide with an unrelated feature therefore passes. Tightening this needs
    the number bound to its referent, which is what the constrained-decoding
    payload does - so the fix is to rely on the payload and treat this sweep as
    a backstop, which is how it is used.
    """
    return [_to_float(m.group()) for m in _NUM.finditer(prose)]


def verify(record, generation):
    """record: the decision record. generation: {'prose': str, 'claims': [...]}.

    Returns a full report: per-claim outcomes, the four metrics, and a verdict.
    """
    feats = record["features"]
    shap = record["shap"]
    probs = record["probabilities"]
    vocab = set(feats) | set(shap)

    ranked = sorted(shap.items(), key=lambda kv: -abs(kv[1]))
    top_names = [n for n, _ in ranked[:TOP_K]]

    rows = []
    for c in generation["claims"]:
        kind = c["kind"]
        row = {"text": c["text"], "kind": kind, "check": kind,
               "result": "unverifiable", "detail": ""}

        if kind == "numeric":
            field, stated = c["field"], c["value"]
            if field in probs:
                actual, tol = probs[field], TOL_PROBABILITY
            elif field in feats:
                actual, tol = feats[field], TOL_FEATURE_ABS
            elif field in shap:
                actual, tol = shap[field], TOL_FEATURE_ABS
            else:
                row.update(result="incorrect",
                           detail=f"'{field}' is not in the record (closed vocabulary)")
                rows.append(row)
                continue
            ok = abs(stated - actual) <= tol
            row.update(result="correct" if ok else "incorrect",
                       detail=(f"stated {stated:g} vs record {actual:g} "
                               f"(tolerance {tol:g})"))

        elif kind == "sign":
            # Direction of the ATTRIBUTION: "X pushes toward Hold".
            field, claimed = c["field"], c["direction"]     # 'toward'/'away'
            if field not in shap:
                row.update(result="incorrect",
                           detail=f"'{field}' has no attribution in the record")
            else:
                actual = shap[field]
                truth = "toward" if actual > 0 else "away"
                ok = claimed == truth
                row.update(result="correct" if ok else "incorrect",
                           detail=(f"contribution to {record['decision']} is "
                                   f"{actual:+.3f}, i.e. pushes {truth}; "
                                   f"text says {claimed}"))

        elif kind == "value_sign":
            # Direction of the FEATURE VALUE itself: "social momentum has
            # fallen". A different claim from the one above, and the proposal's
            # worked example contains both - so the verifier needs both. Reading
            # "has fallen" against a SHAP contribution would be a category error.
            field, claimed = c["field"], c["direction"]     # 'rose'/'fell'
            if field not in feats:
                row.update(result="incorrect",
                           detail=f"'{field}' is not a feature in the record")
            else:
                actual = feats[field]
                truth = "rose" if actual > 0 else "fell"
                ok = claimed == truth
                row.update(result="correct" if ok else "incorrect",
                           detail=(f"{field} = {actual:+.3f}, i.e. {truth}; "
                                   f"text says {claimed}"))

        elif kind == "tier":
            claimed = c["value"]
            actual = record["risk"]["tier"]
            ok = claimed == actual
            row.update(result="correct" if ok else "incorrect",
                       detail=f"stored tier is '{actual}'; text says '{claimed}'")

        elif kind == "rank":
            field = c["field"]
            pos = c.get("position", 1)
            if field not in shap:
                row.update(result="incorrect",
                           detail=f"'{field}' has no attribution in the record")
            else:
                actual_pos = [n for n, _ in ranked].index(field) + 1
                ok = actual_pos <= pos
                row.update(result="correct" if ok else "incorrect",
                           detail=(f"'{field}' ranks #{actual_pos} by |SHAP|; "
                                   f"text presents it as #{pos} or better"))

        elif kind == "entity":
            field = c["field"]
            ok = field in vocab
            row.update(result="correct" if ok else "incorrect",
                       detail=(f"'{field}' {'is' if ok else 'is NOT'} in the "
                               f"known feature set"))
        else:
            row["detail"] = "nothing in the record defines this - flagged, not failed"

        rows.append(row)

    # --- free-prose sweep: any number in the text that no claim accounted for
    accounted = {round(c["value"], 6) for c in generation["claims"]
                 if c["kind"] == "numeric"}
    known = ({round(v, 6) for v in feats.values()}
             | {round(v, 6) for v in shap.values()}
             | {round(v, 6) for v in probs.values()})
    orphans = []
    for n in extract_numbers(generation["prose"]):
        if round(n, 6) in accounted or round(n, 6) in known:
            continue
        if any(abs(n - k) <= TOL_FEATURE_ABS for k in known):
            continue
        orphans.append(n)

    # --- metrics
    def _share(kinds):
        sel = [r for r in rows if r["kind"] in kinds]
        if not sel:
            return 1.0, 0
        good = sum(r["result"] == "correct" for r in sel)
        return good / len(sel), len(sel)

    numeric_fidelity, n_num = _share({"numeric"})
    directional, n_dir = _share({"sign", "value_sign"})
    # A claim counts toward recall if it MENTIONS a top driver, even when the
    # claim itself is unverifiable. Recall asks "did the explanation name the
    # things that actually drove the decision"; verifiability is the separate
    # question of whether what it said about them can be checked.
    cited = {c["field"] for c in generation["claims"] if c.get("field") in shap}
    claim_recall = len(cited & set(top_names)) / len(top_names) if top_names else 1.0
    unverifiable_rate = (sum(r["result"] == "unverifiable" for r in rows)
                         / len(rows)) if rows else 0.0

    metrics = {
        "numeric_fidelity": numeric_fidelity,
        "directional_consistency": directional,
        "claim_recall": claim_recall,
        "unverifiable_rate": unverifiable_rate,
    }
    passes = {
        "numeric_fidelity": numeric_fidelity >= THRESHOLDS["numeric_fidelity"],
        "directional_consistency": directional >= THRESHOLDS["directional_consistency"],
        "claim_recall": claim_recall >= THRESHOLDS["claim_recall"],
        "unverifiable_rate": unverifiable_rate <= THRESHOLDS["unverifiable_rate"],
    }
    hard_fail = any(r["result"] == "incorrect" for r in rows) or bool(orphans)

    return {
        "claims": rows,
        "orphan_numbers": orphans,
        "metrics": metrics,
        "passes": passes,
        "counts": {"numeric": n_num, "directional": n_dir, "total": len(rows)},
        "top_drivers": top_names,
        "cited_drivers": sorted(cited & set(top_names)),
        "verdict": "PASS" if (all(passes.values()) and not hard_fail) else "FAIL",
        "hard_fail": hard_fail,
    }


def template_explanation(record):
    """The deterministic fallback. Grounded by construction because it is built
    FROM the record rather than checked against it. This is what the user sees
    when a generated explanation fails twice - never nothing, and never an
    unverified sentence."""
    d = record["decision"]
    p = record["probabilities"][d]
    ranked = sorted(record["shap"].items(), key=lambda kv: -abs(kv[1]))[:3]
    parts = [f"{record['ticker']} is {d} at {p:.0%} confidence "
             f"for the {record['horizon']} horizon."]
    for name, val in ranked:
        way = "toward" if val > 0 else "away from"
        parts.append(f"{name} contributes {val:+.2f}, pushing {way} {d}.")
    parts.append(f"Your risk tier is {record['risk']['tier']}.")
    parts.append("This is a research and educational prototype. Not financial "
                 "advice. No trades are placed.")
    return " ".join(parts)
