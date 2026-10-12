"""Corrupted-explanation generator -- the verifier's evidence (brief §7).

`explain/verifier.py`'s six checks are only as convincing as the fixtures
that exercise them. This module takes a CORRECT, template-rendered
`Explanation` (produced by `explain/template.py` from a real
`DecisionRecord`) and produces a deliberately wrong variant for each of
the six error classes the brief names:

    wrong_probability       -- a class probability moved by 5pp
    wrong_shap_magnitude    -- a feature's SHAP magnitude moved by 0.05,
                                sign (direction) left untouched
    flipped_direction       -- a feature's claimed direction word flipped,
                                its true SHAP value left untouched
    promoted_minor_feature  -- a non-headline feature's claimed rank
                                rewritten to #1
    invented_feature_name   -- a real feature's name swapped for one
                                outside the record's closed vocabulary
    vague_unverifiable      -- an extra sentence appended that carries no
                                checkable claim at all

Every corruption is deterministic given a seeded `numpy.random.Generator`
and touches exactly one fact, leaving everything else in the explanation
correct -- so a corruption that IS caught is caught for the right reason,
not by accident of some other, unrelated mistake.

**These are labelled synthetic fixtures for testing the verifier.** They
are not, and must never be mistaken for, real model output -- the project
rules (CLAUDE.md) permit synthetic text for unit tests only, never in
place of a real generation. `tests/test_verifier.py` is the only consumer
of this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from investify.decision_record import DecisionRecord
from investify.explain.template import Explanation

CORRUPTION_KINDS = (
    "wrong_probability",
    "wrong_shap_magnitude",
    "flipped_direction",
    "promoted_minor_feature",
    "invented_feature_name",
    "vague_unverifiable",
)

# A fixed, deterministic pool -- picked from by index via the seeded rng,
# never by wall-clock or hash-order, so a given seed always reproduces the
# same fixture set.
_VAGUE_SENTENCES = (
    "Overall market sentiment appeared broadly favorable during the period under review.",
    "General conditions were considered reasonably typical for this sector.",
    "Recent trading activity reflected a mix of ordinary influences.",
    "Investors weighed a broad range of factors in reaching this outlook.",
)

_INVENTED_FEATURE_NAMES = (
    "lunar_cycle_index",
    "insider_whisper_score",
    "social_buzz_index",
    "planetary_alignment_score",
)


@dataclass(frozen=True)
class CorruptedExplanation:
    """One corrupted variant, labelled with what was changed and why."""

    kind: str  # one of CORRUPTION_KINDS
    explanation: Explanation
    detail: str  # human-readable note on exactly what changed


def _require_top_k(record: DecisionRecord) -> None:
    if not record.top_k:
        raise ValueError("fixture generation requires a DecisionRecord with a non-empty top_k")


def _clamp_probability_delta(value: float, delta: float) -> float:
    """Push `value` by `delta`, staying inside [0, 1] with margin to spare.

    Always moves AWAY from the nearer edge, so the resulting delta is
    never shrunk by clamping -- important because the fixture must move
    the claim by more than PROB_TOLERANCE regardless of where `value`
    started.
    """
    if value >= 0.5:
        return value - abs(delta)
    return value + abs(delta)


def _rewrite_feature_line(text: str, name: str, transform) -> str:
    """Apply `transform(line) -> line` to the one line naming `name`, and
    leave every other line untouched."""
    prefix = f"{name} (value "
    lines = text.split("\n")
    return "\n".join(transform(line) if line.startswith(prefix) else line for line in lines)


def _payload_with_contribution(payload: dict | None, target_name: str, **updates) -> dict | None:
    """Shallow-copy `payload`, replacing the named contribution's fields."""
    if payload is None:
        return None
    new_contributions = []
    for c in payload["contributions"]:
        if c["name"] == target_name:
            c = dict(c)
            c.update(updates)
        new_contributions.append(c)
    new_payload = dict(payload)
    new_payload["contributions"] = new_contributions
    return new_payload


# --- one corruptor per error class ------------------------------------------


def corrupt_wrong_probability(
    record: DecisionRecord, expl: Explanation, rng: np.random.Generator
) -> CorruptedExplanation:
    """Move the stated decision confidence by 5pp (10x PROB_TOLERANCE)."""
    delta = 0.05
    new_confidence = _clamp_probability_delta(record.confidence, delta)

    lines = expl.text.split("\n")
    new_text = "\n".join(
        f"Calibrated confidence in this decision: {new_confidence * 100:.2f}%."
        if line.startswith("Calibrated confidence")
        else line
        for line in lines
    )

    new_payload = dict(expl.payload) if expl.payload is not None else None
    if new_payload is not None:
        new_payload["confidence"] = new_confidence

    detail = f"confidence rewritten from {record.confidence:.4f} to {new_confidence:.4f}"
    return CorruptedExplanation("wrong_probability", Explanation(new_text, new_payload), detail)


def corrupt_wrong_shap_magnitude(
    record: DecisionRecord, expl: Explanation, rng: np.random.Generator
) -> CorruptedExplanation:
    """Move one feature's SHAP magnitude by 0.05 (50x SHAP_EPSILON), sign preserved."""
    _require_top_k(record)
    contribution = record.top_k[int(rng.integers(0, len(record.top_k)))]
    delta = 0.05
    new_shap = contribution.shap_value + (delta if contribution.shap_value >= 0 else -delta)

    def transform(line: str) -> str:
        sign = "+" if new_shap >= 0 else ""
        return re.sub(
            r"SHAP contribution of [+-]?\d+\.\d+,",
            f"SHAP contribution of {sign}{new_shap:.4f},",
            line,
        )

    new_text = _rewrite_feature_line(expl.text, contribution.name, transform)
    new_payload = _payload_with_contribution(expl.payload, contribution.name, shap_value=new_shap)

    detail = f"{contribution.name} shap_value rewritten from {contribution.shap_value:.4f} to {new_shap:.4f}"
    return CorruptedExplanation("wrong_shap_magnitude", Explanation(new_text, new_payload), detail)


def corrupt_flipped_direction(
    record: DecisionRecord, expl: Explanation, rng: np.random.Generator
) -> CorruptedExplanation:
    """Flip one feature's claimed direction word; its true SHAP value is untouched."""
    _require_top_k(record)
    contribution = record.top_k[int(rng.integers(0, len(record.top_k)))]
    flipped = "opposes" if contribution.direction == "supports" else "supports"

    def transform(line: str) -> str:
        return line.replace(f") {contribution.direction} the", f") {flipped} the")

    new_text = _rewrite_feature_line(expl.text, contribution.name, transform)
    new_payload = _payload_with_contribution(expl.payload, contribution.name, direction=flipped)

    detail = f"{contribution.name} direction flipped from {contribution.direction!r} to {flipped!r} (SHAP value left correct)"
    return CorruptedExplanation("flipped_direction", Explanation(new_text, new_payload), detail)


def corrupt_promoted_minor_feature(
    record: DecisionRecord, expl: Explanation, rng: np.random.Generator
) -> CorruptedExplanation:
    """Rewrite a non-headline feature's claimed rank to #1."""
    _require_top_k(record)
    candidates = [c for c in record.top_k if c.rank != 1]
    if not candidates:
        raise ValueError(
            "promoted_minor_feature fixture requires a record.top_k with more than one feature"
        )
    contribution = candidates[int(rng.integers(0, len(candidates)))]

    def transform(line: str) -> str:
        return re.sub(r"ranked #\d+ of", "ranked #1 of", line)

    new_text = _rewrite_feature_line(expl.text, contribution.name, transform)
    new_payload = _payload_with_contribution(expl.payload, contribution.name, rank=1)

    detail = f"{contribution.name} rank claim promoted from {contribution.rank} to 1"
    return CorruptedExplanation("promoted_minor_feature", Explanation(new_text, new_payload), detail)


def corrupt_invented_feature_name(
    record: DecisionRecord, expl: Explanation, rng: np.random.Generator
) -> CorruptedExplanation:
    """Swap a real feature's name for one outside the record's closed vocabulary."""
    _require_top_k(record)
    contribution = record.top_k[int(rng.integers(0, len(record.top_k)))]
    pool = [n for n in _INVENTED_FEATURE_NAMES if n not in record.feature_names]
    if not pool:
        raise ValueError("no invented feature name is available outside this record's vocabulary")
    fake_name = pool[int(rng.integers(0, len(pool)))]

    prefix = contribution.name
    lines = expl.text.split("\n")
    new_lines = []
    for line in lines:
        if line.startswith(f"{prefix} (value "):
            new_lines.append(fake_name + line[len(prefix):])
        else:
            new_lines.append(line)
    new_text = "\n".join(new_lines)
    new_payload = _payload_with_contribution(expl.payload, contribution.name, name=fake_name)

    detail = f"{contribution.name!r} renamed to invented feature {fake_name!r}"
    return CorruptedExplanation("invented_feature_name", Explanation(new_text, new_payload), detail)


def corrupt_vague_unverifiable(
    record: DecisionRecord, expl: Explanation, rng: np.random.Generator
) -> CorruptedExplanation:
    """Append a filler sentence that carries no checkable claim.

    The payload, if present, is left untouched: the corruption exists
    purely in the prose the reader sees, not in the structured numbers
    (an LLM being vague is a property of what it SAID, not of the
    underlying facts).
    """
    sentence = _VAGUE_SENTENCES[int(rng.integers(0, len(_VAGUE_SENTENCES)))]
    new_text = expl.text + "\n" + sentence
    detail = f"appended an unverifiable filler sentence: {sentence!r}"
    return CorruptedExplanation("vague_unverifiable", Explanation(new_text, expl.payload), detail)


_CORRUPTORS = {
    "wrong_probability": corrupt_wrong_probability,
    "wrong_shap_magnitude": corrupt_wrong_shap_magnitude,
    "flipped_direction": corrupt_flipped_direction,
    "promoted_minor_feature": corrupt_promoted_minor_feature,
    "invented_feature_name": corrupt_invented_feature_name,
    "vague_unverifiable": corrupt_vague_unverifiable,
}


def corrupt(
    record: DecisionRecord, expl: Explanation, kind: str, rng: np.random.Generator
) -> CorruptedExplanation:
    """Dispatch to the corruptor named `kind`. See `CORRUPTION_KINDS`."""
    if kind not in _CORRUPTORS:
        raise ValueError(f"unknown corruption kind {kind!r}; must be one of {CORRUPTION_KINDS}")
    return _CORRUPTORS[kind](record, expl, rng)


def generate_all(
    record: DecisionRecord, expl: Explanation, *, seed: int = 0
) -> list[CorruptedExplanation]:
    """One corrupted variant per entry in `CORRUPTION_KINDS`, deterministic in `seed`."""
    rng = np.random.default_rng(seed)
    return [corrupt(record, expl, kind, rng) for kind in CORRUPTION_KINDS]
