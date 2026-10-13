"""Thirteen-item Grable-Lytton scoring, capacity constraints and risk allowance.

UI wording is concise paraphrase; published item weights/range are retained.
Local wording and the confidence policy have not undergone population validation.
"""
from dataclasses import asdict, dataclass
from math import fsum, nextafter
from investify.risk_profile import CAPACITY_OPTIONS, CAPACITY_WEIGHTS, tier_for_score

VERSION = 'grable-lytton-capacity-policy-v2'
SOURCE = 'https://static.arnaudsylvain.fr/2017/03/The-Grable-and-Lytton-risk-tolerance-scale-15-year-retrospective.pdf'
# Concise paraphrases retain choices, payoff geometry and published weights.
GL_ITEMS = (
    ("Friend's risk description?", ('Speculator', 'Researcher', 'Cautious', 'Avoider'), (4, 3, 2, 1)),
    ('Game-show choice?', ('$1000 certain', '50%: $5000', '25%: $10000', '5%: $100000'), (1, 2, 3, 4)),
    ('Job lost before holiday?', ('Cancel', 'Downgrade', 'Continue', 'Extend'), (1, 2, 3, 4)),
    ('$20000 unexpected: invest where?', ('Deposits', 'Quality bonds', 'Equities'), (1, 2, 3)),
    ('Equity-investing comfort?', ('No comfort', 'Some comfort', 'High comfort'), (1, 2, 3)),
    ('Risk evokes?', ('Downside', 'Ambiguity', 'Potential', 'Excitement'), (1, 2, 3, 4)),
    ('Experts favour hard assets over bonds:', ('Keep bonds', 'Half cash/half assets', 'All assets', 'Borrow for assets'), (1, 2, 3, 4)),
    ('Choose best/worst payoff:', ('+200/0', '+800/-200', '+2600/-800', '+4800/-2400'), (1, 2, 3, 4)),
    ('Extra $1000: gain choice?', ('500 guaranteed', '50% 1000, otherwise 0'), (1, 3)),
    ('Extra $2000: loss choice?', ('500 guaranteed loss', '50% lose 1000, otherwise 0'), (1, 3)),
    ('$100000 inheritance; one allocation?', ('Cash', 'Mixed fund', '15 equities', 'Commodities'), (1, 2, 3, 4)),
    ('$20000: low/medium/high risk mix?', ('60/30/10', '30/40/30', '10/40/50'), (1, 2, 3)),
    ('Trusted geologist; 20% success, payoff 50-100x or 0; stake?', ('No stake', '1 monthly salary', '3 monthly salaries', '6 monthly salaries'), (1, 2, 3, 4)),
)


def tolerance_band(raw):
    if type(raw) is not int or not 13 <= raw <= 47:
        raise ValueError('Grable-Lytton total must be within 13..47')
    return ('Low' if raw <= 18 else 'Below average' if raw <= 22 else
            'Average' if raw <= 28 else 'Above average' if raw <= 32 else 'High')


@dataclass(frozen=True)
class InvestorProfile:
    capacity_raw: float
    capacity_score: float
    tolerance_raw: int
    tolerance_score: float
    tolerance_band: str
    capacity_tier: str
    tolerance_tier: str
    tier: str
    score: float
    binding_axis: str
    matched_caps: tuple
    version: str = VERSION

    def to_dict(self):
        return asdict(self)


def example_answers(level):
    if level not in (0, 1, 2):
        raise ValueError('Example level must be low, middle or high')
    return [min(range(len(weights)), key=lambda i: weights[i]) if level == 0 else
            max(range(len(weights)), key=lambda i: weights[i]) if level == 2 else
            min(range(len(weights)), key=lambda i: abs(weights[i] - 2))
            for _, _, weights in GL_ITEMS]


def score_profile(capacity, answers):
    if not isinstance(capacity, dict) or set(capacity) != set(CAPACITY_OPTIONS):
        raise ValueError('Answer all five capacity questions')
    values = {}
    for key, choices in CAPACITY_OPTIONS.items():
        if capacity[key] not in choices:
            raise ValueError('Invalid or unanswered capacity question: ' + key)
        values[key] = choices[capacity[key]]
    if not isinstance(answers, (list, tuple)) or len(answers) != len(GL_ITEMS):
        raise ValueError('Answer all thirteen tolerance questions')
    points = []
    for answer, (_, options, weights) in zip(answers, GL_ITEMS):
        if type(answer) is not int or not 0 <= answer < len(options):
            raise ValueError('Every tolerance answer must be an explicit valid choice')
        points.append(weights[answer])
    raw_capacity = fsum(values[k] * CAPACITY_WEIGHTS[k] for k in values)
    caps = []
    if capacity['buffer'] == 'None':
        caps.append('No emergency buffer')
    if capacity['horizon'] == 'Under 1 year':
        caps.append('Funds required within one year')
    if capacity['stability'] == 'Irregular or commission-based' and values['buffer'] <= .33:
        caps.append('Variable income and thin buffer')
    capacity_score = min(raw_capacity, nextafter(.4, 0)) if caps else raw_capacity
    raw_tolerance = sum(points)
    tolerance = (raw_tolerance - 13) / 34
    capacity_tier = tier_for_score(capacity_score)
    tolerance_tier = 'Conservative' if raw_tolerance <= 22 else 'Balanced' if raw_tolerance <= 28 else 'Aggressive'
    order = ('Conservative', 'Balanced', 'Aggressive')
    tier = min((capacity_tier, tolerance_tier), key=order.index)
    allowance = min(capacity_score, tolerance)
    axis = 'both' if capacity_score == tolerance else 'capacity' if capacity_score < tolerance else 'tolerance'
    return InvestorProfile(raw_capacity, capacity_score, raw_tolerance, tolerance,
                           tolerance_band(raw_tolerance), capacity_tier, tolerance_tier,
                           tier, allowance, axis, tuple(caps))


def apply_risk_policy(record, profile, *, eligible_model=True):
    """Profile controls abstention, never sentiment weight or market direction."""
    threshold = .80 - .30 * profile.score
    allowed = eligible_model and profile.score > 0 and record.confidence >= threshold
    if not eligible_model:
        action, reason = 'Observe', 'This archived calibration is a diagnosed failure; no directional suggestion is permitted.'
    elif record.decision == 'Hold':
        action, reason = 'Hold', 'The model itself identifies no directional action.'
    elif allowed:
        action, reason = record.decision, 'Model confidence meets this profile confidence requirement.'
    else:
        action, reason = 'Observe', 'Withhold a directional suggestion at this profile allowance/confidence.'
    return {'model_class': record.decision, 'model_probabilities': dict(record.probabilities),
            'profile_action': action, 'risk_allowance': profile.score,
            'minimum_confidence': threshold, 'model_confidence': record.confidence,
            'direction_reversal': False, 'reason': reason, 'profile': profile.to_dict(),
            'scope': 'Transparent project confidence policy; not a brokerage order or validated suitability rule.'}
