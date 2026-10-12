"""
Tests for the two parts of the prototype that run real code.

A project whose contribution is "we test rather than assert" should not ship a
verifier with no tests. These are deliberately small and dependency-free:

    python test_prototype.py

No pytest, no fixtures framework. Exit code 0 means everything passed.
"""

import json
import sys

import fixtures as fx
import profile_scoring as ps
import verifier as vf

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append((name, detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}"
          + (f"   [{detail}]" if detail and not cond else ""))


def corrupt(record, path, value):
    r = json.loads(json.dumps(record))
    d = r
    for k in path[:-1]:
        d = d[k]
    d[path[-1]] = value
    return r


# ---------------------------------------------------------------------------
print("\nFR-6 — attribution must sum to the model output, for every ticker")
for t, *_ in fx.UNIVERSE:
    r = fx.record_for(t)
    lhs = r["base_value"] + sum(r["shap"].values())
    rhs = r["probabilities"][r["decision"]]
    check(f"{t}: base + sum(shap) == P({r['decision']})",
          abs(lhs - rhs) < 1e-6, f"{lhs:.6f} vs {rhs:.6f}")

print("\nFixture integrity")
n = fx.record_for("NVDA")
check("NVDA matches section 10.8 (rsi 38.2, news +0.31, social -0.18)",
      n["features"]["rsi_14"] == 38.2
      and n["features"]["news_polarity"] == 0.31
      and n["features"]["social_polarity"] == -0.18)
check("NVDA verdict is Hold at 58%",
      n["decision"] == "Hold" and n["probabilities"]["Hold"] == 0.58)
check("probabilities sum to 1", abs(sum(n["probabilities"].values()) - 1) < 1e-6)
check("session date is not the Labor Day holiday",
      n["session_date"] == "2026-09-04", n["session_date"])
check("record_for is deterministic",
      fx.record_for("TSLA") == fx.record_for("TSLA"))

print("\nEvery ticker must verify — not just the one on the slide")
for t, *_ in fx.UNIVERSE:
    r = fx.record_for(t)
    rep = vf.verify(r, fx.generation_for(r))
    check(f"{t}: generated explanation verifies", rep["verdict"] == "PASS",
          "; ".join(c["detail"] for c in rep["claims"]
                    if c["result"] == "incorrect") or str(rep["orphan_numbers"]))

print("\nEvery risk tier must reach the record and the explanation")
for tier in ps.TIER_NAMES:
    risk = {"tier": tier, "capacity": 0.3, "tolerance": 0.3,
            "lambda": ps.LAMBDA_BY_TIER[tier]}
    r = fx.record_for("NVDA", risk)
    g = fx.generation_for(r)
    claimed = [c for c in g["claims"] if c["kind"] == "tier"][0]["value"]
    check(f"{tier}: record, prose and claim all agree",
          r["risk"]["tier"] == tier and claimed == tier
          and f"your {tier} risk tier" in g["prose"]
          and vf.verify(r, g)["verdict"] == "PASS")

print("\nVerifier — the happy path")
gen = fx.generation_for(n)
rep = vf.verify(n, gen)
check("verdict is PASS", rep["verdict"] == "PASS")
check("numeric fidelity 1.00", rep["metrics"]["numeric_fidelity"] == 1.0)
check("directional consistency 1.00",
      rep["metrics"]["directional_consistency"] == 1.0)
check("claim recall meets its floor", rep["metrics"]["claim_recall"] >= 0.80)
check("unverifiable rate within bound",
      rep["metrics"]["unverifiable_rate"] <= 0.15)
check("no orphan numbers in the prose", rep["orphan_numbers"] == [])

print("\nVerifier — each check must catch its own corruption")
cases = [
    ("numeric: P(Hold) 0.58 -> 0.72",
     ["probabilities", "Hold"], 0.72, "numeric_fidelity"),
    ("numeric: news_polarity 0.31 -> 0.55",
     ["features", "news_polarity"], 0.55, "numeric_fidelity"),
    ("sign: rsi_14 attribution -0.06 -> +0.06",
     ["shap", "rsi_14"], 0.06, "directional_consistency"),
    ("value_sign: social_mom_3d -0.22 -> +0.22",
     ["features", "social_mom_3d"], 0.22, "directional_consistency"),
    ("tier: moderate -> aggressive",
     ["risk", "tier"], "aggressive", None),
]
for label, path, value, metric in cases:
    bad = corrupt(n, path, value)
    r = vf.verify(bad, gen)
    caught = any(c["result"] == "incorrect" for c in r["claims"])
    check(label, r["verdict"] == "FAIL" and caught)
    if metric:
        check(f"    -> {metric} degraded", r["metrics"][metric] < 1.0,
              f"{r['metrics'][metric]:.2f}")

print("\nVerifier — closed vocabulary and the template")
ghost = {"prose": "The frobnicator index is 9.9.",
         "claims": [{"text": "frobnicator index", "kind": "entity",
                     "field": "frobnicator_index"}]}
check("a fabricated feature name is rejected",
      vf.verify(n, ghost)["verdict"] == "FAIL")
tmpl = vf.template_explanation(n)
check("template names the verdict and confidence",
      "Hold" in tmpl and "58%" in tmpl)
check("template carries the non-advice notice",
      "Not financial advice" in tmpl)

print("\nRisk scoring")
c = ps.score_capacity("18-30", "Contract or somewhat variable", 2,
                      "1-3 months", "3-5 years")
check("section 10.8 persona scores 0.550",
      abs(c["capped"] - 0.550) < 5e-4, f"{c['capped']:.4f}")
check("that persona is moderate",
      ps.TIER_NAMES[ps.to_tier(c["capped"])] == "moderate")

frag = ps.score_capacity("18-30", "Irregular or commission-based", 1,
                         "1-3 months", "1-3 years")
check("fragile profile matches a cap rule", frag["cap_applies"])
check("that rule does not bind here (score already below the ceiling)",
      not frag["cap_fired"], f"raw {frag['raw']:.4f}")
check("fragile profile is conservative either way",
      ps.TIER_NAMES[ps.to_tier(frag["capped"])] == "conservative",
      f"{frag['capped']:.4f}")

# A profile the cap must actually lower: strong on every factor except that
# the income is irregular and there is no buffer at all.
forced = ps.score_capacity("18-30", "Irregular or commission-based", 0,
                           "None", "5+ years")
check("no-buffer profile is genuinely capped", forced["cap_fired"],
      f"raw {forced['raw']:.4f} -> {forced['capped']:.4f}")
check("a capped profile lands BELOW the moderate cut, not on it",
      ps.TIER_NAMES[ps.to_tier(forced["capped"])] == "conservative",
      f"{forced['capped']:.4f}")

check("binding constraint takes the minimum",
      ps.reconcile(0.90, 0.30)["tier"] == "conservative"
      and ps.reconcile(0.30, 0.90)["tier"] == "conservative")
check("binding side is reported correctly",
      ps.reconcile(0.90, 0.30)["binding"] == "tolerance"
      and ps.reconcile(0.30, 0.90)["binding"] == "capacity")

print("\nGrable-Lytton band mapping")
check("raw 13 -> 0.00", abs(ps.gl_normalise(13) - 0.0) < 1e-9)
check("raw 47 -> 1.00", abs(ps.gl_normalise(47) - 1.0) < 1e-9)
check("below-average band stays under the moderate cut",
      ps.gl_normalise(22) < 0.40, f"{ps.gl_normalise(22):.3f}")
check("above-average band stays under the aggressive cut",
      ps.gl_normalise(32) < 0.70, f"{ps.gl_normalise(32):.3f}")
check("high band starts at the aggressive cut",
      abs(ps.gl_normalise(33) - 0.70) < 1e-9)
check("normalisation is monotonic",
      all(ps.gl_normalise(x) <= ps.gl_normalise(x + 1) for x in range(13, 47)))

print("\nAction bands follow lambda")
cons = ps.action_bands(ps.LAMBDA_BY_TIER["conservative"])
aggr = ps.action_bands(ps.LAMBDA_BY_TIER["aggressive"])
check("a conservative tier needs a larger move to Buy",
      cons["theta_buy"] > aggr["theta_buy"])
check("a conservative tier exits sooner",
      cons["theta_sell"] > aggr["theta_sell"])

# ---------------------------------------------------------------------------
print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
if FAILED:
    for name, detail in FAILED:
        print(f"  FAILED: {name}  {detail}")
sys.exit(1 if FAILED else 0)
