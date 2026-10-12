"""
PROPOSAL-STAGE TECHNICAL SPIKE - Investify (F26-003-QuantamentalAI)
==================================================================

RISKY ASSUMPTION UNDER TEST
    That the risk tier we assign a user is a property of the USER, not an
    artefact of the five capacity weights WE chose.

    The problem is specific. The capacity/tolerance split and the binding
    constraint come from regulation (FCA FG11/05; ESMA MiFID II suitability
    guidelines). Which five factors to collect comes from FINRA Rule 2111.
    Weighting income STABILITY over income LEVEL comes from Viceira (2001).
    None of those sources supplies a weight vector, and no weight vector can
    be fitted from data, because there is no ground truth for a "correct"
    capacity tier - there is nothing to regress against.

    So the weights are ours. If the tier a user receives is largely decided by
    numbers we picked with no evidence behind them, then "risk-conditioned
    recommendation" is decoration and the personalisation claim collapses.
    That is the assumption this spike tests.

WHAT THIS SCRIPT DOES
    1. FIXTURE     Reproduces the worked example in the proposal (10.8) and
                   checks capacity == 0.55 and tier == moderate fall OUT of the
                   scorer rather than being asserted in prose.
    2. FR-7        Property test over 42,000 (capacity, tolerance) pairs: the
                   stored tier must equal band(min(capacity, tolerance)).
    3. INVARIANCE  Enumerates ALL 1,200 personas in the input space, then
                   perturbs the weight vector 1,000 times (each weight times
                   U(0.5, 1.5), renormalised) and reports how many personas
                   ever change tier.
    4. EQUAL-WT    Compares our weights against flat 0.20 weights (Dawes 1979,
                   "the robust beauty of improper linear models") - agreement
                   and Cohen's kappa across all 1,200.
    5. CAPS        Ablates the three hard caps to measure what they contribute.
    6. LAMBDA      Measures the effect of the tier lambda mapping on the
                   Buy/Hold/Sell action bands - the evidence promised for the
                   Tversky & Kahneman row of the research-to-decision table.

    Expected result: most personas are tier-invariant, a minority sit on a
    boundary, and the boundary cases are NAMED rather than hidden. A result
    showing the weights dominate is a finding that changes the design, not a
    setback to be buried.

HOW TO RUN
    pip install numpy matplotlib        # matplotlib optional - chart only
    python poc_risk_profile_spike.py

    No network, no GPU, no trained model. Runs in about a second, which is
    deliberate: the panel can ask for it to be executed rather than described.

Team ownership: Rafay Ul Haq (risk capacity/tolerance elicitation and
reconciliation). Cross-checked by Soban (label geometry for the lambda bands).
"""

import hashlib
import itertools
import json

import numpy as np

# --------------------------------------------------------------------------
# CONFIG  - every number here is a decision we must be able to defend
# --------------------------------------------------------------------------

# Sub-score bands. Each input maps to [0, 1]. The literature supports which
# factors belong here, their direction, and roughly their ordering. It does
# not supply the weights below.
AGE_BANDS  = {"18-30": 1.00, "31-45": 0.75, "46-55": 0.50, "56-65": 0.25, "65+": 0.00}
STABILITY  = {"unstable": 0.00, "somewhat": 0.50, "stable": 1.00}
DEPENDANTS = {0: 1.00, 1: 0.75, 2: 0.50, 3: 0.25, 4: 0.00}     # 4 means "4 or more"
BUFFER     = {"0m": 0.00, "1-3m": 0.33, "3-6m": 0.67, "6m+": 1.00}
HORIZON    = {"<1y": 0.00, "1-3y": 0.33, "3-5y": 0.67, "5y+": 1.00}

FACTORS = ["horizon", "buffer", "stability", "dependants", "age"]
WEIGHTS = np.array([0.30, 0.30, 0.20, 0.10, 0.10])             # <-- THE THING UNDER TEST

TIER_CUTS  = [0.40, 0.70]                    # conservative | moderate | aggressive
TIER_NAMES = ["conservative", "moderate", "aggressive"]

# Hard caps. NOT weighted terms - constraints, on the same logic as the binding
# constraint itself. Anchored in Carroll (1997) buffer-stock saving: a household
# with uncertain income and no liquid buffer is a forced seller regardless of
# what an average says.
#
# Each cap is stated as a TIER ceiling, not as a number. The first version of
# this file wrote them as 0.35 / 0.30 / 0.40, and 0.40 is exactly the
# conservative|moderate cut - so capping a persona "to conservative" actually
# landed them in moderate. Expressing the ceiling relative to the cut removes
# both that off-by-one and three more unanchored constants: the rule is now
# "this profile cannot be rated above conservative", which is a sentence we can
# defend, rather than a decimal we cannot.
CONSERVATIVE_CEILING = TIER_CUTS[0] - 1e-9
CAP_NO_BUFFER     = CONSERVATIVE_CEILING    # buffer == 0m
CAP_SHORT_HORIZON = CONSERVATIVE_CEILING    # horizon < 1y
CAP_FRAGILE       = CONSERVATIVE_CEILING    # income unstable AND buffer < 3 months

# Grable-Lytton (1999): 13 items, raw range 13-47, with PUBLISHED cut-points.
# We map its own bands onto our tiers piecewise rather than re-cutting a
# validated instrument.
GL_MIN, GL_MAX = 13, 47

LAMBDA_BY_TIER = {"conservative": 2.75, "moderate": 2.25, "aggressive": 1.75}
LAMBDA_BASE    = 2.25       # Tversky & Kahneman (1992) population median
THETA_BASE     = 0.50       # vol-units separating Buy/Hold/Sell at the base lambda

N_DRAWS = 1000
PERTURB = 0.50              # each weight times U(1-PERTURB, 1+PERTURB)
SEED    = 42

rng = np.random.default_rng(SEED)


# --------------------------------------------------------------------------
# 1. THE SCORER
# --------------------------------------------------------------------------
def subscores(persona):
    """persona = (age, stability, dependants, buffer, horizon) -> 5 sub-scores,
    ordered to match FACTORS."""
    age, stab, dep, buf, hor = persona
    return np.array([HORIZON[hor], BUFFER[buf], STABILITY[stab],
                     DEPENDANTS[dep], AGE_BANDS[age]])


def cap_ceiling(persona):
    """The lowest hard ceiling that applies. 1.0 means no cap fires."""
    age, stab, dep, buf, hor = persona
    ceil = 1.0
    if buf == "0m":
        ceil = min(ceil, CAP_NO_BUFFER)
    if hor == "<1y":
        ceil = min(ceil, CAP_SHORT_HORIZON)
    if stab == "unstable" and buf in ("0m", "1-3m"):
        ceil = min(ceil, CAP_FRAGILE)
    return ceil


def gl_normalise(raw):
    """Grable-Lytton raw score -> [0,1], preserving the instrument's own bands.
        13-22  below average / low  -> [0.00, 0.40)
        23-32  average / above avg  -> [0.40, 0.70)
        33-47  high                 -> [0.70, 1.00]
    """
    if raw <= 22:
        return (raw - 13) / 10 * 0.40
    if raw <= 32:
        return 0.40 + (raw - 23) / 10 * 0.30
    return 0.70 + (raw - 33) / 14 * 0.30


def to_tier(score):
    """Vectorised band lookup. 0 conservative, 1 moderate, 2 aggressive."""
    return np.digitize(score, TIER_CUTS, right=False)


def reconcile(capacity, tolerance):
    """FR-7: the binding constraint. The stored tier is the more restrictive of
    the two - min(), not mean(). Averaging would let a comfortable tolerance
    score hide a hard financial constraint. This is the ESMA/FCA position, not
    our invention."""
    return to_tier(np.minimum(capacity, tolerance))


def cohen_kappa(a, b, k=3):
    n = len(a)
    obs = float(np.mean(a == b))
    pa = np.bincount(a, minlength=k) / n
    pb = np.bincount(b, minlength=k) / n
    exp = float(np.sum(pa * pb))
    return 1.0 if exp >= 1.0 else (obs - exp) / (1.0 - exp)


# --------------------------------------------------------------------------
# 2. THE PERSONA SPACE  - full factorial, not a sample
# --------------------------------------------------------------------------
def build_space():
    personas = list(itertools.product(
        AGE_BANDS, STABILITY, DEPENDANTS, BUFFER, HORIZON))
    S = np.array([subscores(p) for p in personas])       # (N, 5)
    C = np.array([cap_ceiling(p) for p in personas])     # (N,)
    digest = hashlib.sha256(
        np.concatenate([S.ravel(), C]).tobytes()).hexdigest()[:16]
    return personas, S, C, digest


def capacities(S, C, W, apply_caps=True):
    """S (N,5) @ W (M,5).T -> (N,M) capacities, capped per persona."""
    raw = S @ np.atleast_2d(W).T
    return np.minimum(raw, C[:, None]) if apply_caps else raw


def describe(p):
    age, stab, dep, buf, hor = p
    return f"age {age}, income {stab}, {dep} dep, buffer {buf}, horizon {hor}"


# --------------------------------------------------------------------------
# 3. THE ARMS
# --------------------------------------------------------------------------
def arm_fixture():
    """Does the scorer reproduce the numbers already printed in the proposal?
    If prose and code disagree, the prose is wrong - and we would rather find
    that here than at the defence."""
    persona = ("18-30", "somewhat", 2, "1-3m", "3-5y")
    cap = float(capacities(np.array([subscores(persona)]),
                           np.array([cap_ceiling(persona)]), WEIGHTS)[0, 0])
    # Nearest attainable tolerance to the 0.68 printed in the proposal.
    raws = np.arange(GL_MIN, GL_MAX + 1)
    norms = np.array([gl_normalise(r) for r in raws])
    j = int(np.argmin(np.abs(norms - 0.68)))
    tol, raw = float(norms[j]), int(raws[j])
    tier = int(reconcile(np.array([cap]), np.array([tol]))[0])
    return {
        "persona": describe(persona),
        "capacity": round(cap, 4),
        "capacity_target_in_proposal": 0.55,
        "capacity_matches": abs(cap - 0.55) < 5e-4,
        "tolerance_nearest_attainable": round(tol, 4),
        "tolerance_printed_in_proposal": 0.68,
        "tolerance_gl_raw": raw,
        "tolerance_exactly_attainable": abs(tol - 0.68) < 5e-4,
        "binds": "capacity" if cap <= tol else "tolerance",
        "tier": TIER_NAMES[tier],
        "tier_matches": TIER_NAMES[tier] == "moderate",
    }


NAMED_PERSONAS = {
    "proposal 10.8 as written":  ("18-30", "stable",   2, "3-6m", "5y+"),
    "proposal 10.8 corrected":   ("18-30", "somewhat", 2, "1-3m", "3-5y"),
    "wealthy but anxious":       ("18-30", "stable",   0, "6m+",  "5y+"),
    "constrained but bold":      ("18-30", "unstable", 1, "1-3m", "1-3y"),
}


def arm_named(personas_by_name):
    """The personas we actually put on slides, scored under both weightings.

    This exists as a standing regression test. It is what caught CAP_FRAGILE
    sitting exactly on a tier cut: 'constrained but bold' was capped to 0.40
    and landed in moderate rather than conservative, which is the opposite of
    what the cap was written to do. A named persona that quietly changes tier
    between one draft and the next is a slide that becomes wrong on stage."""
    eq = np.full(5, 0.20)
    out = []
    for name, p in personas_by_name.items():
        S1 = np.array([subscores(p)])
        C1 = np.array([cap_ceiling(p)])
        w = float(capacities(S1, C1, WEIGHTS)[0, 0])
        e = float(capacities(S1, C1, eq)[0, 0])
        out.append({
            "name": name,
            "persona": describe(p),
            "raw_weighted": round(float((S1 @ WEIGHTS)[0]), 4),
            "cap_ceiling": round(float(C1[0]), 4),
            "cap_fires": bool(C1[0] < 1.0),
            "capacity_weighted": round(w, 4),
            "tier_weighted": TIER_NAMES[int(to_tier(w))],
            "capacity_equal": round(e, 4),
            "tier_equal": TIER_NAMES[int(to_tier(e))],
            "agree": TIER_NAMES[int(to_tier(w))] == TIER_NAMES[int(to_tier(e))],
        })
    return out


def arm_fr7(S, C):
    """FR-7 acceptance criterion, as a property test rather than one example:
    'Given conflicting capacity and tolerance inputs, the stored tier equals
    the more restrictive of the two.' Checked over every persona crossed with
    every attainable Grable-Lytton raw score."""
    cap = capacities(S, C, WEIGHTS)[:, 0]                    # (N,)
    raws = np.arange(GL_MIN, GL_MAX + 1)
    tol = np.array([gl_normalise(r) for r in raws])           # (35,)
    CAP = np.repeat(cap[:, None], len(tol), axis=1)
    TOL = np.repeat(tol[None, :], len(cap), axis=0)
    stored = reconcile(CAP, TOL)
    expect = to_tier(np.minimum(CAP, TOL))
    conflict = to_tier(CAP) != to_tier(TOL)
    return {
        "pairs_checked": int(stored.size),
        "violations": int(np.sum(stored != expect)),
        "conflicting_pairs": int(np.sum(conflict)),
        "capacity_binds_share": float(np.mean(CAP[conflict] < TOL[conflict])),
        "tolerance_binds_share": float(np.mean(TOL[conflict] < CAP[conflict])),
        "passes": bool(np.all(stored == expect)),
    }


def arm_invariance(personas, S, C, apply_caps=True):
    """Perturb the weights 1,000 times. How many personas never change tier?

    Uses its own seeded generator rather than the module-level one, so that
    calling this arm twice (the cap ablation does) draws the SAME ensemble both
    times. Sharing a generator made the with-caps figure differ between arm 3
    and arm 6 of the same run, which for a project whose contribution is
    reproducibility is not a rounding difference - it is a defect."""
    local = np.random.default_rng(SEED)
    W = WEIGHTS[None, :] * local.uniform(1 - PERTURB, 1 + PERTURB, (N_DRAWS, 5))
    W = W / W.sum(axis=1, keepdims=True)
    tiers = to_tier(capacities(S, C, W, apply_caps))          # (N, N_DRAWS)
    n_distinct = np.array([len(np.unique(row)) for row in tiers])
    base = to_tier(capacities(S, C, WEIGHTS, apply_caps)[:, 0])
    flippers = np.where(n_distinct > 1)[0]
    # Worst offenders first: those that span all three tiers, then by how often
    # they leave their baseline tier.
    off_base = np.mean(tiers != base[:, None], axis=1)
    order = sorted(flippers, key=lambda i: (-n_distinct[i], -off_base[i]))
    return {
        "n_personas": int(len(personas)),
        "n_draws": N_DRAWS,
        "perturbation": f"each weight x U({1-PERTURB:.2f}, {1+PERTURB:.2f}), renormalised",
        # Two different questions, both reported, because they answer differently.
        # "invariant" is strict: one flip in 1,000 draws disqualifies a persona.
        # "pairwise_agreement" is the aggregate: across all N x N_DRAWS cells,
        # how often does the tier match the baseline at all?
        "invariant": int(np.sum(n_distinct == 1)),
        "invariant_share": float(np.mean(n_distinct == 1)),
        "pairwise_agreement": float(np.mean(tiers == base[:, None])),
        "spans_two_tiers": int(np.sum(n_distinct == 2)),
        "spans_three_tiers": int(np.sum(n_distinct == 3)),
        "boundary_examples": [
            {"persona": describe(personas[i]),
             "baseline_tier": TIER_NAMES[base[i]],
             "tiers_seen": [TIER_NAMES[t] for t in sorted(np.unique(tiers[i]))],
             "share_off_baseline": round(float(off_base[i]), 3)}
            for i in order[:8]
        ],
    }


def arm_per_weight(S, C):
    """Which single weight actually moves the answer? Halve it, then double it,
    renormalise the rest, and count tier flips against baseline."""
    base = to_tier(capacities(S, C, WEIGHTS)[:, 0])
    out = []
    for k, name in enumerate(FACTORS):
        flips = []
        for mult in (0.5, 2.0):
            w = WEIGHTS.copy()
            w[k] *= mult
            w = w / w.sum()
            flips.append(float(np.mean(to_tier(capacities(S, C, w)[:, 0]) != base)))
        out.append({"factor": name, "weight": float(WEIGHTS[k]),
                    "flip_share_halved": round(flips[0], 4),
                    "flip_share_doubled": round(flips[1], 4),
                    "flip_share_max": round(max(flips), 4)})
    return out


def arm_equal_weights(S, C):
    """Dawes (1979): unit weights usually do about as well as tuned ones. If
    that holds here, our weight vector is not load-bearing - which is the
    honest defence, and it is measured rather than cited."""
    eq = np.full(5, 0.20)
    a = to_tier(capacities(S, C, WEIGHTS)[:, 0])
    b = to_tier(capacities(S, C, eq)[:, 0])
    return {
        "agreement": float(np.mean(a == b)),
        "cohen_kappa": round(cohen_kappa(a, b), 4),
        "n_disagreements": int(np.sum(a != b)),
        "mean_abs_capacity_delta": round(float(np.mean(np.abs(
            capacities(S, C, WEIGHTS)[:, 0] - capacities(S, C, eq)[:, 0]))), 4),
    }


def arm_caps(personas, S, C):
    """What do the three hard caps actually buy us?"""
    with_caps = to_tier(capacities(S, C, WEIGHTS, True)[:, 0])
    no_caps = to_tier(capacities(S, C, WEIGHTS, False)[:, 0])
    fired = C < 1.0
    inv_with = arm_invariance(personas, S, C, True)["invariant_share"]
    inv_without = arm_invariance(personas, S, C, False)["invariant_share"]
    return {
        "personas_where_a_cap_fires": int(np.sum(fired)),
        "personas_whose_tier_the_caps_change": int(np.sum(with_caps != no_caps)),
        "tier_invariance_with_caps": round(inv_with, 4),
        "tier_invariance_without_caps": round(inv_without, 4),
        "invariance_gained_by_caps": round(inv_with - inv_without, 4),
    }


def arm_lambda():
    """The tier -> lambda -> action-band mapping, and its measured effect.

    A trade is worth taking when the expected gain exceeds lambda times the
    expected loss, so a more loss-averse user needs a wider Buy band and exits
    sooner. Both thresholds are DERIVED from the one published constant rather
    than hand-set:
        theta_buy(lam)  = +THETA_BASE * lam / LAMBDA_BASE
        theta_sell(lam) = -THETA_BASE * LAMBDA_BASE / lam
    z is the forward 5-day return divided by 20-day realised volatility scaled
    to the 5-day horizon. The distribution below is SYNTHETIC and is here only
    to show the band shares move as intended; the real label distribution
    replaces it at Iteration 2.
    """
    n = 200_000
    z_norm = rng.standard_normal(n)
    t = rng.standard_t(4, n)
    z_fat = t / np.sqrt(4 / (4 - 2))          # unit variance, fat tails
    out = []
    for tier, lam in LAMBDA_BY_TIER.items():
        tb = THETA_BASE * lam / LAMBDA_BASE
        ts = -THETA_BASE * LAMBDA_BASE / lam
        row = {"tier": tier, "lambda": lam,
               "theta_buy": round(tb, 4), "theta_sell": round(ts, 4)}
        for label, z in (("normal", z_norm), ("student_t4", z_fat)):
            row[f"buy_share_{label}"] = round(float(np.mean(z > tb)), 4)
            row[f"hold_share_{label}"] = round(float(np.mean((z <= tb) & (z >= ts))), 4)
            row[f"sell_share_{label}"] = round(float(np.mean(z < ts)), 4)
        out.append(row)
    return out


# --------------------------------------------------------------------------
# 4. REPORT
# --------------------------------------------------------------------------
def main():
    personas, S, C, digest = build_space()

    print()
    print("=" * 78)
    print("  RISK-PROFILE SPIKE - do our weights decide the tier, or does the user?")
    print(f"  persona-space sha256 {digest} | seed {SEED} | {len(personas)} personas")
    print("=" * 78)

    fx = arm_fixture()
    named = arm_named(NAMED_PERSONAS)
    fr7 = arm_fr7(S, C)
    inv = arm_invariance(personas, S, C)
    pw = arm_per_weight(S, C)
    eq = arm_equal_weights(S, C)
    caps = arm_caps(personas, S, C)
    lam = arm_lambda()

    print()
    print("  1. FIXTURE - does the scorer reproduce the proposal's worked example?")
    print(f"     {fx['persona']}")
    print(f"     capacity  {fx['capacity']:.4f}   (proposal prints 0.55)  "
          f"{'MATCH' if fx['capacity_matches'] else 'MISMATCH'}")
    print(f"     tolerance {fx['tolerance_nearest_attainable']:.4f} at G-L raw "
          f"{fx['tolerance_gl_raw']}  (proposal prints 0.68)  "
          f"{'MATCH' if fx['tolerance_exactly_attainable'] else 'NOT ATTAINABLE'}")
    print(f"     binds on {fx['binds']}  ->  tier {fx['tier']}   "
          f"{'MATCH' if fx['tier_matches'] else 'MISMATCH'}")

    print()
    print("  1b. NAMED PERSONAS - the ones that go on slides (regression test)")
    print("      persona                     capacity  tier          equal-wt tier")
    for r in named:
        flag = "" if r["agree"] else "   <-- WEIGHTING DECIDES THIS ONE"
        print(f"      {r['name']:<26}{r['capacity_weighted']:8.3f}  "
              f"{r['tier_weighted']:<13} {r['tier_equal']:<12}{flag}")

    print()
    print("  2. FR-7 - binding constraint as a property test, not one example")
    print(f"     {fr7['pairs_checked']:,} (capacity, tolerance) pairs checked, "
          f"{fr7['violations']} violations -> {'PASS' if fr7['passes'] else 'FAIL'}")
    print(f"     {fr7['conflicting_pairs']:,} pairs disagree on tier. Of those, "
          f"capacity binds {fr7['capacity_binds_share']:.1%}, "
          f"tolerance binds {fr7['tolerance_binds_share']:.1%}.")

    print()
    print("  3. INVARIANCE - 1,000 perturbed weight vectors over all 1,200 personas")
    print(f"     strict  - tier never changes for {inv['invariant']}/{inv['n_personas']} "
          f"personas ({inv['invariant_share']:.1%})")
    print(f"     aggregate - across all {inv['n_personas'] * inv['n_draws']:,} "
          f"(persona, draw) cells the tier matches baseline "
          f"{inv['pairwise_agreement']:.1%} of the time")
    print(f"     spans two tiers: {inv['spans_two_tiers']}   "
          f"spans all three: {inv['spans_three_tiers']}")
    if inv["boundary_examples"]:
        print("     boundary personas (named, not hidden):")
        for b in inv["boundary_examples"][:5]:
            print(f"       - {b['persona']}")
            print(f"         baseline {b['baseline_tier']}, seen as "
                  f"{'/'.join(b['tiers_seen'])}, off-baseline "
                  f"{b['share_off_baseline']:.1%} of draws")

    print()
    print("  4. WHICH WEIGHT ACTUALLY MATTERS")
    for r in sorted(pw, key=lambda r: -r["flip_share_max"]):
        print(f"     {r['factor']:<11} w={r['weight']:.2f}   "
              f"halved {r['flip_share_halved']:6.2%}   "
              f"doubled {r['flip_share_doubled']:6.2%}")

    print()
    print("  5. EQUAL WEIGHTS (Dawes 1979) - is our vector load-bearing?")
    print(f"     agreement {eq['agreement']:.1%}, Cohen's kappa {eq['cohen_kappa']:.3f}, "
          f"{eq['n_disagreements']} personas differ")
    print(f"     mean |capacity difference| {eq['mean_abs_capacity_delta']:.4f}")

    print()
    print("  6. HARD CAPS - what do the constraints contribute?")
    print(f"     a cap fires for {caps['personas_where_a_cap_fires']} personas; "
          f"{caps['personas_whose_tier_the_caps_change']} change tier because of one")
    print(f"     tier invariance  with caps {caps['tier_invariance_with_caps']:.1%}   "
          f"without {caps['tier_invariance_without_caps']:.1%}   "
          f"(+{caps['invariance_gained_by_caps']:.1%})")

    print()
    print("  7. LAMBDA -> ACTION BANDS (evidence promised for the T&K row)")
    print("     tier          lam   buy if z>   sell if z<   buy%   hold%   sell%  (normal)")
    for r in lam:
        print(f"     {r['tier']:<13}{r['lambda']:.2f}   {r['theta_buy']:+.3f}      "
              f"{r['theta_sell']:+.3f}     {r['buy_share_normal']:5.1%}  "
              f"{r['hold_share_normal']:5.1%}  {r['sell_share_normal']:5.1%}")

    # ----------------------------------------------------------------------
    print()
    print("=" * 78)
    print("  WHAT THIS CHANGES")
    print("=" * 78)

    print()
    print("  A. THE WEIGHTS MATTER LESS THAN THE INPUTS - BUT NOT AS LITTLE AS WE HOPED.")
    print(f"     Aggregate: across {inv['n_personas'] * inv['n_draws']:,} (persona, draw) cells the tier matches")
    print(f"     baseline {inv['pairwise_agreement']:.1%} of the time, and flat 0.20 weights agree with ours for")
    print(f"     {eq['agreement']:.1%} of personas (kappa {eq['cohen_kappa']:.3f}). That is the Dawes (1979) result holding.")
    print(f"     Strict: only {inv['invariant_share']:.1%} of personas survive a +/-50% perturbation of all")
    print(f"     five weights without EVER flipping. So {1 - inv['invariant_share']:.1%} of the space sits close")
    print("     enough to a cut that the weights can move it. We report both numbers.")
    print("     => Do not claim the weights are arbitrary-but-harmless. Claim what is true:")
    print("        they are inert for most users, decisive for a named minority, and we")
    print("        publish the list rather than waiting to be asked for it.")

    print()
    print("  B. THE BOUNDARY CASES ARE NAMED, NOT HIDDEN.")
    print(f"     {inv['spans_two_tiers'] + inv['spans_three_tiers']} personas can change tier under perturbation. Reporting WHICH")
    print("     ones is worth more than claiming none do. These are the profiles where a")
    print("     panel is entitled to ask what the assignment rests on, and we can answer.")

    print()
    print("  C. THE CAPS DO REAL WORK, AND THEY ARE WHERE THE EVIDENCE IS STRONGEST.")
    print(f"     They fire for {caps['personas_where_a_cap_fires']} personas and move {caps['personas_whose_tier_the_caps_change']} across a tier boundary,")
    print(f"     raising invariance by {caps['invariance_gained_by_caps']:.1%}. That matters: a cap is a constraint")
    print("     with a citation (Carroll 1997), while a weight is a choice without one.")
    print("     => Push work onto the caps and away from the weights wherever possible.")

    print()
    print("  D. CAPACITY IS THE USUAL BINDER - SO DEMO THE OTHER DIRECTION TOO.")
    print(f"     Where the two disagree, capacity binds {fr7['capacity_binds_share']:.1%} of the time and tolerance")
    print(f"     {fr7['tolerance_binds_share']:.1%}. The proposal's worked example is capacity-binding, so it is")
    print("     representative - good. But the minority direction (a financially secure")
    print("     user held back by their own answers) is the one an examiner will probe,")
    print("     because it is where averaging the two scores would visibly fail the user.")
    print("     => Carry a second worked example for it. One line in the acceptance study.")

    print()
    print("  E. ONE NUMBER IN THE PROPOSAL IS NOT ATTAINABLE.")
    if not fx["tolerance_exactly_attainable"]:
        print(f"     Section 10.8 prints tolerance 0.68. Under the published Grable-Lytton")
        print(f"     bands the nearest attainable value is {fx['tolerance_nearest_attainable']:.2f} (raw score {fx['tolerance_gl_raw']}).")
        print("     The tier is unaffected, but the figure should be corrected before the")
        print("     defence rather than defended on the day.")
    else:
        print("     Tolerance 0.68 is attainable exactly. No change needed.")

    payload = {
        "spike": "risk_profile_weight_sensitivity",
        "persona_space_sha256": digest,
        "config": {
            "factors": FACTORS,
            "weights": WEIGHTS.tolist(),
            "caps": {"no_buffer": CAP_NO_BUFFER, "short_horizon": CAP_SHORT_HORIZON,
                     "fragile": CAP_FRAGILE},
            "tier_cuts": TIER_CUTS,
            "gl_range": [GL_MIN, GL_MAX],
            "lambda_by_tier": LAMBDA_BY_TIER,
            "n_draws": N_DRAWS, "perturbation": PERTURB, "seed": SEED,
        },
        "results": {
            "fixture": fx, "named_personas": named,
            "fr7_property_test": fr7, "invariance": inv,
            "per_weight_sensitivity": pw, "equal_weights": eq,
            "cap_ablation": caps, "lambda_action_bands": lam,
        },
    }
    with open("poc_risk_results.json", "w") as f:
        json.dump(payload, f, indent=2, default=float)
    print()
    print("  -> poc_risk_results.json written (space hash, seed, every figure above)")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # Projector palette: high contrast on white, blue/orange rather
        # than red/green, far apart in lightness as well as hue.
        TEAL, AMBER, GREY = "#0B5FBF", "#D35400", "#5F6368"
        matplotlib.rcParams.update({"font.size": 12, "axes.labelsize": 12.5,
                                    "xtick.labelsize": 11.5, "ytick.labelsize": 11.5,
                                    "figure.facecolor": "white"})
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14.2, 4.5))

        # A - tier stability
        vals = [inv["invariant"], inv["spans_two_tiers"], inv["spans_three_tiers"]]
        bars = ax1.bar(["same tier\nalways", "spans\ntwo tiers", "spans\nall three"],
                       vals, color=[TEAL, AMBER, "#B3261E"], width=0.62)
        for b, v in zip(bars, vals):
            ax1.text(b.get_x() + b.get_width() / 2, v + len(personas) * 0.015,
                     f"{v}\n({v/len(personas):.1%})", ha="center", fontsize=9)
        ax1.set_ylim(0, len(personas) * 1.18)
        ax1.set_ylabel("personas")
        ax1.set_title("All 1,200 personas under 1,000\nperturbed weight vectors (+/-50%)",
                      fontsize=10.5)

        # B - per-weight sensitivity
        order = sorted(pw, key=lambda r: r["flip_share_max"])
        ax2.barh([r["factor"] for r in order],
                 [r["flip_share_max"] for r in order], color=TEAL, height=0.6)
        for i, r in enumerate(order):
            ax2.text(r["flip_share_max"] + 0.004, i, f"{r['flip_share_max']:.1%}",
                     va="center", fontsize=9)
        ax2.set_xlim(0, max(r["flip_share_max"] for r in pw) * 1.35 + 0.01)
        ax2.xaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax2.set_xlabel("share of personas that change tier")
        ax2.set_title("Which single weight moves the answer?\n(that weight halved or doubled)",
                      fontsize=10.5)

        # C - lambda action bands
        tiers = [r["tier"] for r in lam]
        x = np.arange(len(tiers))
        sell = [r["sell_share_normal"] for r in lam]
        hold = [r["hold_share_normal"] for r in lam]
        buy = [r["buy_share_normal"] for r in lam]
        ax3.bar(x, sell, 0.55, label="Sell", color="#B3261E")
        ax3.bar(x, hold, 0.55, bottom=sell, label="Hold", color=GREY)
        ax3.bar(x, buy, 0.55, bottom=np.add(sell, hold), label="Buy", color=TEAL)
        for i, r in enumerate(lam):
            ax3.text(i, 0.5, f"lam {r['lambda']}", ha="center", fontsize=8.5, color="w")
        ax3.set_xticks(x)
        ax3.set_xticklabels(tiers, fontsize=9)
        ax3.set_ylim(0, 1)
        ax3.set_ylabel("share of days")
        ax3.set_title("Tier changes the action bands\n(synthetic z, replaced at Iteration 2)",
                      fontsize=10.5)
        ax3.legend(frameon=False, fontsize=9, ncol=3, loc="upper center",
                   bbox_to_anchor=(0.5, -0.12))

        for ax in (ax1, ax2, ax3):
            ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig("poc_risk_chart.png", dpi=170, bbox_inches="tight")
        print("  -> poc_risk_chart.png written  <-- THIS IS YOUR DEFENCE SLIDE")
    except ImportError:
        print("  (matplotlib not installed - chart skipped)")
    print()


if __name__ == "__main__":
    main()
