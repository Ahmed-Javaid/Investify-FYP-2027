"""
Risk capacity, risk tolerance, and the binding constraint.  REAL CODE.

This is screen 2, 3 and 4 of the prototype. Nothing here is mocked: the same
functions are exercised by ../poc_risk_profile_spike.py, which enumerates all
1,200 personas and reports how sensitive the tier is to the weights below.

Provenance of each part, because the panel will ask:
  - The capacity/tolerance split and the rule that the more restrictive one
    binds: FCA FG11/05; ESMA MiFID II suitability guidelines. Not our idea.
  - Which five factors to collect: FINRA Rule 2111 customer investment profile.
  - Weighting income STABILITY rather than income LEVEL: Viceira (2001) - it is
    the variance of labour income that reduces risk capacity, not its size.
    This is why the form never asks for a salary.
  - The hard caps: Carroll (1997) buffer-stock saving.
  - The WEIGHTS: ours. No study supplies them and they cannot be fitted,
    because there is no ground truth for a correct capacity tier. Their
    sensitivity is measured in the spike rather than asserted here.
"""

FACTORS = ["horizon", "buffer", "stability", "dependants", "age"]
WEIGHTS = {"horizon": 0.30, "buffer": 0.30, "stability": 0.20,
           "dependants": 0.10, "age": 0.10}

AGE_BANDS = {"18-30": 1.00, "31-45": 0.75, "46-55": 0.50, "56-65": 0.25, "65+": 0.00}
STABILITY = {"Irregular or commission-based": 0.00,
             "Contract or somewhat variable": 0.50,
             "Salaried and stable": 1.00}
DEPENDANTS = {0: 1.00, 1: 0.75, 2: 0.50, 3: 0.25, 4: 0.00}
BUFFER = {"None": 0.00, "1-3 months": 0.33, "3-6 months": 0.67, "6+ months": 1.00}
HORIZON = {"Under 1 year": 0.00, "1-3 years": 0.33,
           "3-5 years": 0.67, "5+ years": 1.00}

TIER_CUTS = [0.40, 0.70]
TIER_NAMES = ["conservative", "moderate", "aggressive"]

# Caps are stated as a TIER ceiling, not as a decimal. Writing them as numbers
# put one of them exactly on the conservative|moderate cut, so capping a
# profile "to conservative" landed it in moderate instead. See the spike.
CONSERVATIVE_CEILING = TIER_CUTS[0] - 0.001   # one display-unit below the cut,
                                             # so a capped score reads as 0.399 rather
                                             # than rounding to 0.40 next to the label
                                             # "conservative" and looking self-contradictory

LAMBDA_BY_TIER = {"conservative": 2.75, "moderate": 2.25, "aggressive": 1.75}
LAMBDA_BASE = 2.25          # Tversky & Kahneman (1992) population median
THETA_BASE = 0.50

GL_MIN, GL_MAX = 13, 47

# Structurally faithful stand-ins for the 13 Grable-Lytton items: same response
# formats and the same 13-47 raw range, paraphrased rather than reproduced. The
# licensed wording is substituted before any real participant sees this - a
# prototype is not a reason to redistribute an instrument.
GL_ITEMS = [
    ("In general, how would you describe your approach to money?",
     ["Very cautious", "Somewhat cautious", "Somewhat willing to take risk",
      "Very willing to take risk"]),
    ("You unexpectedly receive a large sum. What do you do with most of it?",
     ["Put it in a savings account", "Split it between savings and investments",
      "Invest most of it", "Invest all of it in something with high potential"]),
    ("An investment you hold falls 20% in a month. You:",
     ["Sell all of it", "Sell some of it", "Hold and wait", "Buy more"]),
    ("Which describes how you feel about financial decisions?",
     ["I worry about them a lot", "I worry somewhat", "I am generally comfortable",
      "I enjoy them"]),
    ("When you think about the word 'risk', what comes to mind first?",
     ["Loss", "Uncertainty", "Opportunity", "Excitement"]),
    ("Would you accept a bet with a 50% chance to double your money and a 50% "
     "chance to lose half?",
     ["No", "Probably not", "Probably yes", "Yes"]),
    ("How much of your savings would you be comfortable putting at risk?",
     ["None", "A small share", "About half", "Most of it"]),
    ("A friend describes a high-risk, high-return venture. You:",
     ["Avoid it entirely", "Ask a lot of questions first",
      "Consider a small amount", "Take part"]),
    ("Given a choice, would you prefer a certain smaller gain or a chance at a "
     "much larger one?",
     ["Certain smaller gain", "Lean toward the certain gain",
      "Lean toward the chance", "Chance at the larger gain"]),
    ("How experienced are you with investing?",
     ["No experience", "A little", "Moderate", "Considerable"]),
    ("If your investments performed poorly for a full year, you would:",
     ["Move everything to cash", "Move some to cash", "Change nothing",
      "Add more while prices are low"]),
    ("How important is it to you that the value of your savings never falls?",
     ["Extremely important", "Quite important", "Somewhat important",
      "Not important"]),
    ("Which statement fits you best?",
     ["I want to protect what I have", "I want steady, modest growth",
      "I want growth and accept some swings",
      "I want the highest growth available"]),
]


def capacity_subscores(age, stability, dependants, buffer, horizon):
    return {
        "horizon": HORIZON[horizon],
        "buffer": BUFFER[buffer],
        "stability": STABILITY[stability],
        "dependants": DEPENDANTS[min(dependants, 4)],
        "age": AGE_BANDS[age],
    }


def capacity_caps(stability, buffer, horizon):
    """Returns (ceiling, [reasons]). A cap is a constraint, not a weighted term:
    an averaged score must not be able to smooth away a forced-seller profile."""
    reasons = []
    ceiling = 1.0
    if buffer == "None":
        ceiling = min(ceiling, CONSERVATIVE_CEILING)
        reasons.append("No emergency fund - a loss would have to be realised.")
    if horizon == "Under 1 year":
        ceiling = min(ceiling, CONSERVATIVE_CEILING)
        reasons.append("Horizon under one year - no time to recover a drawdown.")
    if STABILITY[stability] == 0.0 and buffer in ("None", "1-3 months"):
        ceiling = min(ceiling, CONSERVATIVE_CEILING)
        reasons.append("Irregular income with a thin buffer (Carroll 1997: "
                       "forced-seller profile).")
    return ceiling, reasons


def score_capacity(age, stability, dependants, buffer, horizon):
    subs = capacity_subscores(age, stability, dependants, buffer, horizon)
    raw = sum(WEIGHTS[k] * subs[k] for k in FACTORS)
    ceiling, reasons = capacity_caps(stability, buffer, horizon)
    return {
        "subscores": subs,
        "contributions": {k: WEIGHTS[k] * subs[k] for k in FACTORS},
        "raw": raw,
        "capped": min(raw, ceiling),
        # Two different facts, kept apart. A cap rule can MATCH without
        # BINDING, when the weighted score was already below the ceiling.
        # Reporting "a hard cap applied" in that case would overstate what the
        # constraint did; reporting nothing would hide that the profile met a
        # forced-seller rule at all. So we carry both.
        "cap_applies": bool(reasons),
        "cap_fired": raw > ceiling,
        "cap_reasons": reasons,
    }


def gl_raw(answers):
    """answers: list of 0-based option indices. Mapped onto the instrument's own
    13-47 raw range so its published cut-points still apply."""
    return GL_MIN + sum(answers) * (GL_MAX - GL_MIN) / (len(GL_ITEMS) * 3)


def gl_normalise(raw):
    """Preserve the instrument's published bands rather than re-cutting them:
        13-22 below average -> [0.00, 0.40)
        23-32 average/above -> [0.40, 0.70)
        33-47 high          -> [0.70, 1.00]
    """
    if raw <= 22:
        return (raw - 13) / 10 * 0.40
    if raw <= 32:
        return 0.40 + (raw - 23) / 10 * 0.30
    return 0.70 + (raw - 33) / 14 * 0.30


def gl_band(raw):
    if raw <= 18:
        return "low"
    if raw <= 22:
        return "below average"
    if raw <= 28:
        return "average"
    if raw <= 32:
        return "above average"
    return "high"


def to_tier(score):
    return 0 if score < TIER_CUTS[0] else (1 if score < TIER_CUTS[1] else 2)


def reconcile(capacity, tolerance):
    """FR-7. min(), not mean(). Averaging would let a comfortable tolerance
    score hide a hard financial constraint."""
    binding = "capacity" if capacity <= tolerance else "tolerance"
    score = min(capacity, tolerance)
    tier = TIER_NAMES[to_tier(score)]
    return {"tier": tier, "score": score, "binding": binding,
            "lambda": LAMBDA_BY_TIER[tier],
            "conflict": to_tier(capacity) != to_tier(tolerance)}


def action_bands(lam):
    """Tier -> lambda -> Buy/Sell thresholds in volatility units. Derived from
    the one published constant, not hand-set: a trade is worth taking when the
    expected gain exceeds lambda times the expected loss, so a more loss-averse
    user needs a wider Buy band and exits sooner."""
    return {"theta_buy": THETA_BASE * lam / LAMBDA_BASE,
            "theta_sell": -THETA_BASE * LAMBDA_BASE / lam}
