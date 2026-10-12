"""Auditable project-prototype profile, not a validated psychometric instrument.

Capacity weights/caps come from the retained proposal prototype. Tolerance is
the existing demo's three stand-in questions, linearly normalized; it is NOT
the complete Grable-Lytton instrument or its validated scoring key. No lambda
parameter is used, so the unresolved tier-lambda specification is not hidden.
"""
from dataclasses import asdict, dataclass
from math import fsum, nextafter

PROFILE_VERSION = "mideval-prototype-profile-v1"
CAPACITY_OPTIONS = {
    "horizon": {"Under 1 year": 0.0, "1-3 years": .33, "3-5 years": .67, "5+ years": 1.0},
    "buffer": {"None": 0.0, "1-3 months": .33, "3-6 months": .67, "6+ months": 1.0},
    "stability": {"Irregular or commission-based": 0.0, "Contract or somewhat variable": .5,
                  "Salaried and stable": 1.0},
    "dependants": {"0": 1.0, "1": .75, "2": .5, "3": .25, "4+": 0.0},
    "age": {"18-30": 1.0, "31-45": .75, "46-55": .5, "56-65": .25, "65+": 0.0},
}
CAPACITY_WEIGHTS = {"horizon": .30, "buffer": .30, "stability": .20, "dependants": .10, "age": .10}
TOLERANCE_QUESTIONS = [
    ("In general, how would your friends describe you as a risk taker?",
     ["Avoids risk where possible", "Takes risk after research", "A real gambler"]),
    ("Your investment falls 20% in a month. You:",
     ["Sell to stop further loss", "Hold and wait", "Buy more at the lower price"]),
    ("Which would you rather have?", ["A certain gain of $1,000",
     "A 50% chance of $5,000 and 50% of nothing", "A 20% chance of $25,000 and 80% of nothing"]),
]


def tier_for_score(score: float) -> str:
    if not 0 <= score <= 1:
        raise ValueError("profile score must be in [0, 1]")
    return "Conservative" if score < .40 else "Balanced" if score < .70 else "Aggressive"


@dataclass(frozen=True)
class RiskProfile:
    capacity_raw: float
    capacity_score: float
    tolerance_score: float
    score: float
    capacity_tier: str
    tolerance_tier: str
    tier: str
    binding_axis: str
    matched_caps: tuple[str, ...]
    cap_binding: bool
    factor_scores: dict[str, float]
    factor_contributions: dict[str, float]
    version: str = PROFILE_VERSION

    def to_dict(self):
        return asdict(self)


def score_profile(capacity: dict, tolerance: list[int] | tuple[int, ...]) -> RiskProfile:
    """Refuse incomplete/unknown answers; never silently fill a middle answer."""
    if not isinstance(capacity, dict) or set(capacity) != set(CAPACITY_OPTIONS):
        raise ValueError("answer all five capacity questions")
    scores = {}
    for factor, options in CAPACITY_OPTIONS.items():
        answer = capacity[factor]
        if not isinstance(answer, str) or answer not in options:
            raise ValueError(f"invalid or unanswered {factor} question")
        scores[factor] = options[answer]
    if (not isinstance(tolerance, (list, tuple)) or len(tolerance) != 3
            or any(type(index) is not int or index not in (0, 1, 2) for index in tolerance)):
        raise ValueError("answer all three tolerance questions with indices 0, 1 or 2")
    contributions = {factor: scores[factor] * weight for factor, weight in CAPACITY_WEIGHTS.items()}
    raw = fsum(contributions.values())
    caps = []
    if capacity['buffer'] == 'None':
        caps.append('No emergency buffer')
    if capacity['horizon'] == 'Under 1 year':
        caps.append('Money needed within one year')
    if capacity['stability'] == 'Irregular or commission-based' and scores['buffer'] <= .33:
        caps.append('Irregular income and a thin buffer')
    capped = min(raw, nextafter(.40, 0)) if caps else raw
    willingness = fsum(tolerance) / 6
    score = min(capped, willingness)
    axis = 'both' if capped == willingness else 'capacity' if capped < willingness else 'tolerance'
    return RiskProfile(raw, capped, willingness, score, tier_for_score(capped), tier_for_score(willingness),
                       tier_for_score(score), axis, tuple(caps), capped < raw, scores, contributions)
