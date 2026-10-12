"""The frozen decision record (brief section 7).

Everything downstream -- the template explainer, the verifier, the demo --
reads ONLY this record. That is the whole point of the design: because the
explainer's input is entirely structured and numeric, whether an
explanation is grounded is decidable by code rather than by another
model's opinion.

Two consequences the rest of the codebase depends on:

1. Dataclass fields cannot be reassigned. Nested dictionaries are ordinary
   mappings; downstream code must treat them as read-only. Integration tests
   check that explanation and comparator paths leave them unchanged.
2. The record is self-validating. A record that cannot exist (probabilities
   that do not sum to 1, a decision that is not the argmax, a top-k list
   that disagrees with the SHAP vector it was derived from) raises at
   construction rather than flowing into an explanation.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from math import isfinite
from numbers import Real

DECISION_CLASSES = ("Buy", "Hold", "Sell")
RISK_TIERS = ("Conservative", "Balanced", "Aggressive")

PROB_SUM_TOL = 1e-6
SHAP_ADDITIVITY_TOL = 1e-4

NON_ADVICE_NOTICE = (
    "Research and educational output only. Not investment advice, not a "
    "recommendation to buy or sell any security."
)


def _finite_number(value) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


def _input_value(value) -> bool:
    # Missing inputs may be None or NaN in inherited scientific artifacts.
    return value is None or isinstance(value, Real) and not isinstance(value, bool)


def _same_input(first, second) -> bool:
    left = first if _finite_number(first) else None
    right = second if _finite_number(second) else None
    return left == right


@dataclass(frozen=True)
class FeatureContribution:
    """One feature's contribution to the predicted class."""

    name: str
    value: float | None
    shap_value: float
    rank: int
    direction: str  # "supports" | "opposes"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or any(c.isspace() for c in self.name):
            raise ValueError("contribution name must be a nonempty feature identifier")
        if not _input_value(self.value):
            raise ValueError("contribution value must be numeric or missing")
        if not _finite_number(self.shap_value) or self.shap_value == 0:
            raise ValueError("top-k SHAP contribution must be finite and nonzero")
        if self.direction not in ("supports", "opposes"):
            raise ValueError(
                f"FeatureContribution.direction must be 'supports' or 'opposes', "
                f"got {self.direction!r}"
            )
        if type(self.rank) is not int or self.rank < 1:
            raise ValueError(f"FeatureContribution.rank is 1-based, got {self.rank}")
        # direction must agree with the sign it was derived from, or every
        # downstream directional check is verifying against a lie
        if self.shap_value > 0 and self.direction != "supports":
            raise ValueError(
                f"{self.name}: positive shap_value {self.shap_value} but "
                f"direction={self.direction!r}"
            )
        if self.shap_value < 0 and self.direction != "opposes":
            raise ValueError(
                f"{self.name}: negative shap_value {self.shap_value} but "
                f"direction={self.direction!r}"
            )


@dataclass(frozen=True)
class DecisionRecord:
    """The single source of truth for one decision.

    `shap_values` and `base_value` are for the PREDICTED class only
    (path-dependent TreeSHAP, no interaction values). Additivity --
    base_value + sum(shap_values) == raw model output for that class --
    is asserted at construction and again by tests/test_shap_additivity.py.
    """

    ticker: str
    session_date: str  # ISO date of the session the decision is FOR
    horizon_days: int
    decision: str
    probabilities: dict[str, float]
    feature_vector: dict[str, float | None]
    shap_values: dict[str, float]
    base_value: float
    raw_model_output: float
    top_k: tuple[FeatureContribution, ...]
    risk_tier: str
    model_version: str
    data_hashes: dict[str, str]
    seed: int
    created_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    non_advice_notice: str = NON_ADVICE_NOTICE

    def __post_init__(self) -> None:
        if not isinstance(self.ticker, str) or not self.ticker or any(c.isspace() for c in self.ticker):
            raise ValueError("ticker must be a nonempty identifier")
        if not isinstance(self.session_date, str) or date.fromisoformat(self.session_date).isoformat() != self.session_date:
            raise ValueError("session_date must be an ISO date")
        if type(self.horizon_days) is not int or self.horizon_days <= 0:
            raise ValueError("horizon_days must be a positive integer")
        if not isinstance(self.non_advice_notice, str) or not self.non_advice_notice.strip():
            raise ValueError("non_advice_notice must be nonempty text")
        if self.decision not in DECISION_CLASSES:
            raise ValueError(
                f"decision must be one of {DECISION_CLASSES}, got {self.decision!r}"
            )
        if self.risk_tier not in RISK_TIERS:
            raise ValueError(
                f"risk_tier must be one of {RISK_TIERS}, got {self.risk_tier!r}"
            )
        if not isinstance(self.probabilities, dict) or set(self.probabilities) != set(DECISION_CLASSES):
            raise ValueError(
                f"probabilities must cover exactly {DECISION_CLASSES}, "
                f"got {sorted(self.probabilities)}"
            )
        if not all(_finite_number(value) and 0 <= value <= 1 for value in self.probabilities.values()):
            raise ValueError("probabilities must be finite numeric values in [0, 1]")
        if not isinstance(self.feature_vector, dict) or not self.feature_vector:
            raise ValueError("feature_vector must be a nonempty object")
        if any(not isinstance(name, str) or not name or any(c.isspace() for c in name)
               or not _input_value(value) for name, value in self.feature_vector.items()):
            raise ValueError("features require nonempty identifiers and numeric or missing values")
        if not isinstance(self.shap_values, dict) or set(self.shap_values) != set(self.feature_vector):
            raise ValueError("SHAP vector must cover exactly the recorded features")
        if not all(_finite_number(value) for value in self.shap_values.values()):
            raise ValueError("SHAP contributions must be finite numeric values")
        if not _finite_number(self.base_value) or not _finite_number(self.raw_model_output):
            raise ValueError("base_value and raw_model_output must be finite numeric values")

        total = sum(self.probabilities.values())
        if abs(total - 1.0) > PROB_SUM_TOL:
            raise ValueError(f"probabilities sum to {total}, not 1.0")

        argmax = max(self.probabilities, key=lambda c: self.probabilities[c])
        if argmax != self.decision:
            raise ValueError(
                f"decision {self.decision!r} is not the argmax of the "
                f"probabilities (argmax is {argmax!r})"
            )

        # the SHAP vector must describe the features that actually exist
        unknown = sorted(set(self.shap_values) - set(self.feature_vector))
        if unknown:
            raise ValueError(f"shap_values names absent from feature_vector: {unknown}")

        additive = self.base_value + sum(self.shap_values.values())
        if abs(additive - self.raw_model_output) > SHAP_ADDITIVITY_TOL:
            raise ValueError(
                f"SHAP additivity violated: base_value + sum(shap) = {additive}, "
                f"raw_model_output = {self.raw_model_output}"
            )

        # top_k must be a faithful, correctly-ordered view of shap_values --
        # the verifier's rank-consistency check depends on this holding
        for contribution in self.top_k:
            if contribution.name not in self.shap_values:
                raise ValueError(f"top_k names {contribution.name!r}, absent from shap_values")
            recorded = self.shap_values[contribution.name]
            if recorded != contribution.shap_value:
                raise ValueError(
                    f"top_k[{contribution.name}] shap_value {contribution.shap_value} "
                    f"disagrees with shap_values[{contribution.name}] {recorded}"
                )
            if not _same_input(contribution.value, self.feature_vector[contribution.name]):
                raise ValueError("top-k value disagrees with its recorded feature input")
        if len({c.name for c in self.top_k}) != len(self.top_k):
            raise ValueError("duplicate top-k feature names")
        ranks = [c.rank for c in self.top_k]
        if ranks != list(range(1, len(self.top_k) + 1)):
            raise ValueError(f"top_k ranks must be 1..n in order, got {ranks}")
        magnitudes = [abs(c.shap_value) for c in self.top_k]
        if magnitudes != sorted(magnitudes, reverse=True):
            raise ValueError(
                f"top_k must be ordered by descending |shap_value|, got {magnitudes}"
            )
        expected = sorted((abs(value) for value in self.shap_values.values() if value != 0), reverse=True)[:len(self.top_k)]
        if magnitudes != expected:
            raise ValueError("top-k must contain the largest recorded contributions")

    @property
    def confidence(self) -> float:
        """Calibrated probability of the decided class."""
        return self.probabilities[self.decision]

    @property
    def feature_names(self) -> tuple[str, ...]:
        """The closed vocabulary the verifier validates feature mentions against."""
        return tuple(self.feature_vector)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_dict(cls, payload: dict) -> DecisionRecord:
        data = dict(payload)
        data["top_k"] = tuple(FeatureContribution(**c) for c in data.get("top_k", ()))
        return cls(**data)


def rank_contributions(
    shap_values: dict[str, float],
    feature_vector: dict[str, float],
    k: int = 5,
) -> tuple[FeatureContribution, ...]:
    """Top-k contributors by absolute SHAP magnitude, ranked 1..k.

    A feature with exactly zero contribution is excluded: it did not push
    the decision either way, and admitting it would let an explanation
    cite a feature that contributed nothing.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    missing = sorted(set(shap_values) - set(feature_vector))
    if missing:
        raise ValueError(f"shap_values names absent from feature_vector: {missing}")

    ordered = sorted(shap_values.items(), key=lambda kv: abs(kv[1]), reverse=True)
    contributions = []
    for rank, (name, shap_value) in enumerate(ordered[:k], start=1):
        if shap_value == 0:
            break
        contributions.append(
            FeatureContribution(
                name=name,
                value=feature_vector[name],
                shap_value=shap_value,
                rank=rank,
                direction="supports" if shap_value > 0 else "opposes",
            )
        )
    return tuple(contributions)
