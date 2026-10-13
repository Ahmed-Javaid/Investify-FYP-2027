"""Deterministic groundedness verifier for template explanations (brief §7).

Because `explain/template.py`'s only input is a `DecisionRecord` --
entirely structured and numeric -- whether the English it produces is
grounded is decidable by code, not by another model's opinion. This
module is that decision procedure.

Six checks, numbered to match the brief:

  1. Numeric extraction    -- independently from the displayed text and
                               the optional structured payload. A correct
                               payload cannot excuse contradictory prose
                               or supply facts omitted from the display.
  2. Tolerance matching     -- probabilities within `PROB_TOLERANCE`
                               (0.5 percentage points); SHAP magnitudes
                               within `SHAP_EPSILON`.
  3. Sign and direction     -- a claimed "supports"/"opposes" must match
                               the true sign of that feature's recorded
                               SHAP contribution.
  4. Rank consistency       -- a cited feature's claimed rank must equal
                               its true rank in `record.top_k`. A feature
                               absent from `top_k` (never rendered by the
                               template itself, but reachable via a
                               corrupted fixture) fails this check --
                               that is what catches a minor contributor
                               being promoted to a headline cause.
  5. Closed-vocabulary       -- every feature name mentioned must be a
                               member of `record.feature_names`. A name
                               outside that set makes every claim about
                               it provably false (the feature does not
                               exist to have a direction, magnitude or
                               rank), not merely "unable to check".
  6. Claim-level scoring     -- the explanation is decomposed line by
                               line into atomic `Claim`s, each verdicted
                               "verifiable-correct", "verifiable-incorrect"
                               or "unverifiable".

Four metrics are reported, never a single score -- an explanation that
hedges every sentence into unverifiability would score a hollow "100%
fidelity" while conveying nothing, which is exactly the failure mode
`unverifiable_rate` exists to catch on its own:

    numeric_fidelity          pass >= NUMERIC_FIDELITY_THRESHOLD  (0.98)
    directional_consistency   pass >= DIRECTIONAL_CONSISTENCY_THRESHOLD (0.95)
    claim_recall               pass >= CLAIM_RECALL_THRESHOLD      (0.80)
    unverifiable_rate          pass <= UNVERIFIABLE_RATE_THRESHOLD (0.15)

`claim_recall` and `unverifiable_rate` are deliberately NOT complements
of one another (they do not sum to 1): `claim_recall` measures how much
of the record's ground truth the explanation actually, correctly,
covered (catches "said too little, or said it wrong"); `unverifiable_rate`
measures what fraction of what the explanation DID say could not be
checked at all against the record (catches "said a lot, but hollow").
An explanation can fail either independently of the other.
"""
from __future__ import annotations

import re
from math import fsum, isfinite
from dataclasses import dataclass

from investify.decision_record import DECISION_CLASSES, DecisionRecord
from investify.explain.context import FEATURES, ATTRIBUTION_SCOPE, attribution_direction

# --- thresholds (brief §7) --------------------------------------------------

NUMERIC_FIDELITY_THRESHOLD = 0.98
DIRECTIONAL_CONSISTENCY_THRESHOLD = 0.95
CLAIM_RECALL_THRESHOLD = 0.80
UNVERIFIABLE_RATE_THRESHOLD = 0.15

# Probabilities: within 0.5 percentage points (brief §7 check 2), i.e. 0.005
# in fraction terms.
PROB_TOLERANCE_PP = 0.5
PROB_TOLERANCE = PROB_TOLERANCE_PP / 100.0

# SHAP magnitude epsilon. The template prints SHAP values to 4 decimal
# places (max rounding error 5e-5); every corruption fixture perturbs a
# SHAP value by >= 0.01. 1e-3 sits comfortably above the former and well
# below the latter, so it discriminates "rounding" from "wrong" cleanly.
SHAP_EPSILON = 1e-3
FEATURE_VALUE_EPSILON = 1e-3
VERIFIER_CONTRACT_VERSION = "mideval-complete-evidence-v4"

VERIFIABLE_CORRECT = "verifiable-correct"
VERIFIABLE_INCORRECT = "verifiable-incorrect"
UNVERIFIABLE = "unverifiable"

# Claim kinds that feed numeric_fidelity (check 2 + the numeric half of check 4).
_NUMERIC_KINDS = frozenset({"confidence", "probability", "shap_magnitude", "rank", "feature_value", "family_magnitude"})


@dataclass(frozen=True)
class Claim:
    """One atomic, verdicted claim extracted from an explanation."""

    kind: str  # "decision" | "confidence" | "probability" | "shap_direction"
    # | "shap_magnitude" | "rank" | "notice" | "vague"
    subject: str | None  # decision class or feature name, where applicable
    claimed: object
    actual: object
    verdict: str  # VERIFIABLE_CORRECT | VERIFIABLE_INCORRECT | UNVERIFIABLE
    reason: str
    span: str  # the source line, for the demo's per-claim table


@dataclass(frozen=True)
class VerificationResult:
    """The four headline metrics plus the full per-claim breakdown."""

    claims: tuple[Claim, ...]
    numeric_fidelity: float
    directional_consistency: float
    claim_recall: float
    unverifiable_rate: float
    passed: bool
    failed_metrics: tuple[str, ...]

    def as_table(self) -> list[dict]:
        """The per-claim report as plain dicts, for the Phase 4 demo table."""
        return [
            {
                "source": "payload" if c.span.startswith("(payload)") else "displayed text",
                "kind": c.kind,
                "subject": c.subject,
                "claimed": c.claimed,
                "actual": c.actual,
                "verdict": c.verdict,
                "reason": c.reason,
                "span": c.span,
            }
            for c in self.claims
        ]


# --- raw (pre-verdict) claim extraction -------------------------------------


@dataclass(frozen=True)
class _RawClaim:
    kind: str
    subject: str | None
    claimed: object
    span: str


_DECISION_RE = re.compile(
    r"^(?P<ticker>\S+) decision for session (?P<session_date>\S+) "
    r"\((?P<horizon>\d+)-day horizon\): (?P<decision>Buy|Hold|Sell)\.$"
)
_CONFIDENCE_RE = re.compile(
    r"^Calibrated confidence in this decision: (?P<pct>-?\d+\.\d+)%\.$"
)
_PROBABILITY_RE = re.compile(
    r"^Full probability breakdown -- Buy: (?P<buy>-?\d+\.\d+)%, "
    r"Hold: (?P<hold>-?\d+\.\d+)%, Sell: (?P<sell>-?\d+\.\d+)%\.$"
)
_FEATURE_RE = re.compile(
    r"^(?P<name>\S+) \(value (?P<value>-?\d+\.\d+|missing)\) "
    r"(?P<direction>supports|opposes) the (?P<decision>Buy|Hold|Sell) decision "
    r"with a SHAP contribution of (?P<shap>[+-]?\d+\.\d+), "
    r"ranked #(?P<rank>\d+) of (?P<n>\d+)\.$"
)
_DEFINITION_RE = re.compile(r"^Feature definition for (?P<name>\S+): (?P<meaning>.+)$")
_EVIDENCE_RE = re.compile(
    r"^Recorded feature (?P<name>\S+) \(value (?P<value>-?\d+\.\d+|missing)\): "
    r"SHAP (?P<shap>[+-]?\d+\.\d+) for (?P<decision>Buy|Hold|Sell); "
    r"effect (?P<direction>supports|opposes|neutral)\.$"
)
_FAMILY_RE = re.compile(
    r"^Family contribution for (?P<name>.+): SHAP (?P<shap>[+-]?\d+\.\d+) "
    r"for (?P<decision>Buy|Hold|Sell); effect (?P<direction>supports|opposes|neutral)\.$"
)


def _value_claim(value: str) -> float | None:
    return None if value == "missing" else float(value)


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.split("\n") if line.strip()]


def _match_known_line(line: str, record: DecisionRecord) -> list[_RawClaim] | None:
    """Match one prose line against a known sentence pattern.

    Returns the raw claims that line asserts, or `None` if the line
    matches no known pattern (i.e. it is a candidate "vague" line).
    Notice-line matching is exact string equality against the record's
    own notice, since the template never paraphrases it.
    """
    if line == record.non_advice_notice:
        return [_RawClaim(kind="notice", subject=None, claimed=line, span=line)]
    if line == ATTRIBUTION_SCOPE:
        return [_RawClaim("attribution_scope", None, line, line)]

    m = _EVIDENCE_RE.match(line)
    if m:
        name = m.group("name")
        return [
            _RawClaim("feature_value", name, _value_claim(m.group("value")), line),
            _RawClaim("attribution_target", name, m.group("decision"), line),
            _RawClaim("shap_direction", name, m.group("direction"), line),
            _RawClaim("shap_magnitude", name, float(m.group("shap")), line),
        ]
    m = _FAMILY_RE.match(line)
    if m:
        return [_RawClaim("family_magnitude", m.group("name"), float(m.group("shap")), line),
                _RawClaim("family_direction", m.group("name"), m.group("direction"), line),
                _RawClaim("family_target", m.group("name"), m.group("decision"), line)]

    definition = _DEFINITION_RE.match(line)
    if definition:
        return [_RawClaim(kind="feature_definition", subject=definition.group("name"),
                          claimed=definition.group("meaning"), span=line)]

    m = _DECISION_RE.match(line)
    if m:
        claimed = {
            "ticker": m.group("ticker"),
            "session_date": m.group("session_date"),
            "horizon": int(m.group("horizon")),
            "decision": m.group("decision"),
        }
        return [_RawClaim(kind="decision", subject=None, claimed=claimed, span=line)]

    m = _CONFIDENCE_RE.match(line)
    if m:
        return [
            _RawClaim(
                kind="confidence",
                subject=None,
                claimed=float(m.group("pct")) / 100.0,
                span=line,
            )
        ]

    m = _PROBABILITY_RE.match(line)
    if m:
        return [
            _RawClaim(
                kind="probability",
                subject=cls,
                claimed=float(m.group(key)) / 100.0,
                span=line,
            )
            for cls, key in (("Buy", "buy"), ("Hold", "hold"), ("Sell", "sell"))
        ]

    m = _FEATURE_RE.match(line)
    if m:
        name = m.group("name")
        return [
            _RawClaim(kind="feature_value", subject=name, claimed=_value_claim(m.group("value")), span=line),
            _RawClaim(kind="feature_target", subject=name,
                      claimed={"decision": m.group("decision"), "top_k_count": int(m.group("n"))}, span=line),
            _RawClaim(kind="shap_direction", subject=name, claimed=m.group("direction"), span=line),
            _RawClaim(kind="shap_magnitude", subject=name, claimed=float(m.group("shap")), span=line),
            _RawClaim(kind="rank", subject=name, claimed=int(m.group("rank")), span=line),
        ]

    return None


def _claims_from_prose(text: str, record: DecisionRecord) -> list[_RawClaim]:
    claims: list[_RawClaim] = []
    for line in _lines(text):
        matched = _match_known_line(line, record)
        if matched is not None:
            claims.extend(matched)
    return claims


def _validate_payload(payload: dict) -> None:
    """Reject malformed model output before extracting claims from it."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    allowed = {"ticker", "session_date", "decision", "horizon_days", "confidence",
               "probabilities", "contributions", "non_advice_notice", "definitions",
               "feature_evidence", "family_contributions", "attribution_scope"}
    if set(payload) - allowed:
        raise ValueError("payload contains unsupported fields")
    for field in ("ticker", "session_date", "decision", "non_advice_notice"):
        if not isinstance(payload[field], str):
            raise ValueError(f"{field} must be text")
    if type(payload["horizon_days"]) is not int:
        raise ValueError("horizon_days must be an integer")

    def number(value):
        if type(value) not in (int, float) or not isfinite(value):
            raise ValueError("numeric claims must be finite numbers")

    number(payload["confidence"])
    probabilities = payload["probabilities"]
    if not isinstance(probabilities, dict) or set(probabilities) != set(DECISION_CLASSES):
        raise ValueError("probabilities must cover exactly Buy, Hold and Sell")
    for value in probabilities.values():
        number(value)
    if not isinstance(payload["contributions"], list):
        raise ValueError("contributions must be a list")
    for contribution in payload["contributions"]:
        if not isinstance(contribution, dict):
            raise ValueError("each contribution must be an object")
        if set(contribution) != {"name", "direction", "value", "shap_value", "rank"}:
            raise ValueError("contribution contains missing or unsupported fields")
        if not isinstance(contribution["name"], str) or not isinstance(contribution["direction"], str):
            raise ValueError("contribution name and direction must be text")
        if contribution["value"] is not None:
            number(contribution["value"])
        number(contribution["shap_value"])
        if type(contribution["rank"]) is not int:
            raise ValueError("contribution rank must be an integer")
    definitions = payload.get("definitions", [])
    if not isinstance(definitions, list):
        raise ValueError("definitions must be a list")
    for definition in definitions:
        if not isinstance(definition, dict) or set(definition) != {"name", "meaning"}:
            raise ValueError("each definition requires exactly name and meaning")
        if not all(isinstance(value, str) for value in definition.values()):
            raise ValueError("definition name and meaning must be text")
    for field, keys in (("feature_evidence", {"name", "value", "shap_value", "direction"}),
                        ("family_contributions", {"name", "shap_value", "direction"})):
        items = payload.get(field, [])
        if not isinstance(items, list):
            raise ValueError(f"{field} must be a list")
        for item in items:
            if not isinstance(item, dict) or set(item) != keys:
                raise ValueError(f"{field} item has missing or unsupported fields")
            if not isinstance(item["name"], str) or not isinstance(item["direction"], str):
                raise ValueError("evidence name and direction must be text")
            number(item["shap_value"])
            if "value" in item and item["value"] is not None:
                number(item["value"])
    if "attribution_scope" in payload and not isinstance(payload["attribution_scope"], str):
        raise ValueError("attribution_scope must be text")


def _claims_from_payload(payload: dict) -> list[_RawClaim]:
    _validate_payload(payload)
    claims = [
        _RawClaim(
            kind="decision",
            subject=None,
            claimed={
                "ticker": payload["ticker"],
                "session_date": payload["session_date"],
                "horizon": payload["horizon_days"],
                "decision": payload["decision"],
            },
            span="(payload) decision",
        ),
        _RawClaim(kind="confidence", subject=None, claimed=payload["confidence"], span="(payload) confidence"),
    ]
    for cls in DECISION_CLASSES:
        claims.append(
            _RawClaim(
                kind="probability",
                subject=cls,
                claimed=payload["probabilities"][cls],
                span=f"(payload) probability[{cls}]",
            )
        )
    for c in payload["contributions"]:
        name = c["name"]
        claims.append(_RawClaim(kind="feature_value", subject=name, claimed=c["value"], span=f"(payload) {name}"))
        claims.append(_RawClaim(kind="shap_direction", subject=name, claimed=c["direction"], span=f"(payload) {name}"))
        claims.append(_RawClaim(kind="shap_magnitude", subject=name, claimed=c["shap_value"], span=f"(payload) {name}"))
        claims.append(_RawClaim(kind="rank", subject=name, claimed=c["rank"], span=f"(payload) {name}"))
    claims.append(_RawClaim(kind="notice", subject=None, claimed=payload["non_advice_notice"], span="(payload) notice"))
    for definition in payload.get("definitions", []):
        claims.append(_RawClaim(kind="feature_definition", subject=definition["name"],
                                claimed=definition["meaning"], span=f"(payload) definition {definition['name']}"))
    for item in payload.get("feature_evidence", []):
        name, span = item["name"], f"(payload) evidence {item['name']}"
        claims.extend([_RawClaim("feature_value", name, item["value"], span),
                       _RawClaim("shap_direction", name, item["direction"], span),
                       _RawClaim("shap_magnitude", name, item["shap_value"], span),
                       _RawClaim("attribution_target", name, payload["decision"], span)])
    for item in payload.get("family_contributions", []):
        name, span = item["name"], f"(payload) family {item['name']}"
        claims.extend([_RawClaim("family_magnitude", name, item["shap_value"], span),
                       _RawClaim("family_direction", name, item["direction"], span),
                       _RawClaim("family_target", name, payload["decision"], span)])
    if "attribution_scope" in payload:
        claims.append(_RawClaim("attribution_scope", None, payload["attribution_scope"], "(payload) scope"))
    return claims


def _vague_claims(text: str, record: DecisionRecord) -> list[_RawClaim]:
    """Lines that match no known sentence pattern at all.

    Always scans the raw prose, independent of whether a payload was
    supplied: a payload describes what the numbers should be, but check 6
    is about what the READER was actually told, and only the text the
    reader sees can carry a vague, unverifiable sentence.
    """
    return [
        _RawClaim(kind="vague", subject=None, claimed=None, span=line)
        for line in _lines(text)
        if _match_known_line(line, record) is None
    ]


# --- verdicting --------------------------------------------------------------


def _verify_decision(raw: _RawClaim, record: DecisionRecord) -> Claim:
    actual = {
        "ticker": record.ticker,
        "session_date": record.session_date,
        "horizon": record.horizon_days,
        "decision": record.decision,
    }
    correct = raw.claimed == actual
    return Claim(
        kind="decision",
        subject=None,
        claimed=raw.claimed,
        actual=actual,
        verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
        reason="" if correct else "ticker/session/horizon/decision mismatch",
        span=raw.span,
    )


def _verify_confidence(raw: _RawClaim, record: DecisionRecord) -> Claim:
    correct = abs(raw.claimed - record.confidence) <= PROB_TOLERANCE
    return Claim(
        kind="confidence",
        subject=None,
        claimed=raw.claimed,
        actual=record.confidence,
        verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
        reason="" if correct else f"outside +/-{PROB_TOLERANCE_PP}pp tolerance",
        span=raw.span,
    )


def _verify_probability(raw: _RawClaim, record: DecisionRecord) -> Claim:
    actual = record.probabilities[raw.subject]
    correct = abs(raw.claimed - actual) <= PROB_TOLERANCE
    return Claim(
        kind="probability",
        subject=raw.subject,
        claimed=raw.claimed,
        actual=actual,
        verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
        reason="" if correct else f"outside +/-{PROB_TOLERANCE_PP}pp tolerance",
        span=raw.span,
    )


def _verify_notice(raw: _RawClaim, record: DecisionRecord) -> Claim:
    correct = raw.claimed == record.non_advice_notice
    return Claim(
        kind="notice",
        subject=None,
        claimed=raw.claimed,
        actual=record.non_advice_notice,
        verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
        reason="" if correct else "non-advice notice text does not match",
        span=raw.span,
    )


def _verify_feature_claim(raw: _RawClaim, record: DecisionRecord) -> Claim:
    """Checks 3 (direction), 4 (rank) and 5 (closed vocabulary) together.

    Vocabulary is checked first: a name outside `record.feature_names`
    makes every claim about it provably false (there is no such feature
    to have a direction, magnitude or rank), so it short-circuits straight
    to VERIFIABLE_INCORRECT rather than UNVERIFIABLE.
    """
    name = raw.subject
    if name not in record.feature_names:
        return Claim(
            kind=raw.kind,
            subject=name,
            claimed=raw.claimed,
            actual=None,
            verdict=VERIFIABLE_INCORRECT,
            reason=f"{name!r} is not in the record's closed feature vocabulary",
            span=raw.span,
        )

    if raw.kind == "feature_definition":
        reviewed = FEATURES.get(name)
        actual = reviewed[2] if reviewed else None
        correct = actual is not None and raw.claimed == actual
        return Claim(kind=raw.kind, subject=name, claimed=raw.claimed, actual=actual,
                     verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
                     reason="" if correct else "definition differs from the reviewed feature meaning",
                     span=raw.span)

    if raw.kind == "feature_value":
        value = record.feature_vector[name]
        actual = value if value is not None and isfinite(value) else None
        correct = (raw.claimed is None if actual is None else
                   raw.claimed is not None and abs(raw.claimed - actual) <= FEATURE_VALUE_EPSILON)
        return Claim(
            kind=raw.kind, subject=name, claimed=raw.claimed, actual=actual,
            verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
            reason="" if correct else "feature value differs from the recorded input",
            span=raw.span,
        )
    if raw.kind == "attribution_target":
        correct = raw.claimed == record.decision
        return Claim(raw.kind, name, raw.claimed, record.decision,
                     VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
                     "" if correct else "attribution target class differs", raw.span)
    if raw.kind == "feature_target":
        actual = {"decision": record.decision, "top_k_count": len(record.top_k)}
        correct = raw.claimed == actual
        return Claim(
            kind=raw.kind, subject=name, claimed=raw.claimed, actual=actual,
            verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
            reason="" if correct else "attribution target class or contributor count differs",
            span=raw.span,
        )

    if raw.kind in ("shap_direction", "shap_magnitude"):
        actual_shap = record.shap_values.get(name)
        if actual_shap is None:
            return Claim(
                kind=raw.kind,
                subject=name,
                claimed=raw.claimed,
                actual=None,
                verdict=VERIFIABLE_INCORRECT,
                reason=f"{name!r} has no recorded SHAP contribution",
                span=raw.span,
            )
        if raw.kind == "shap_direction":
            actual_direction = attribution_direction(actual_shap)
            correct = raw.claimed == actual_direction
            reason = "" if correct else f"true direction is {actual_direction!r}"
            return Claim(
                kind="shap_direction",
                subject=name,
                claimed=raw.claimed,
                actual=actual_direction,
                verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
                reason=reason,
                span=raw.span,
            )
        # shap_magnitude
        correct = abs(raw.claimed - actual_shap) <= SHAP_EPSILON
        reason = "" if correct else f"outside +/-{SHAP_EPSILON} tolerance"
        return Claim(
            kind="shap_magnitude",
            subject=name,
            claimed=raw.claimed,
            actual=actual_shap,
            verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
            reason=reason,
            span=raw.span,
        )

    # rank
    actual_rank = next((c.rank for c in record.top_k if c.name == name), None)
    if actual_rank is None:
        return Claim(
            kind="rank",
            subject=name,
            claimed=raw.claimed,
            actual=None,
            verdict=VERIFIABLE_INCORRECT,
            reason=f"{name!r} is not among the record's top-k contributors",
            span=raw.span,
        )
    correct = raw.claimed == actual_rank
    reason = "" if correct else f"true rank is {actual_rank} (minor contributor promoted)" if raw.claimed < actual_rank else f"true rank is {actual_rank}"
    return Claim(
        kind="rank",
        subject=name,
        claimed=raw.claimed,
        actual=actual_rank,
        verdict=VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
        reason=reason,
        span=raw.span,
    )


def _verify(raw: _RawClaim, record: DecisionRecord) -> Claim:
    if raw.kind == "decision":
        return _verify_decision(raw, record)
    if raw.kind == "confidence":
        return _verify_confidence(raw, record)
    if raw.kind == "probability":
        return _verify_probability(raw, record)
    if raw.kind == "notice":
        return _verify_notice(raw, record)
    if raw.kind in ("shap_direction", "shap_magnitude", "rank", "feature_value", "feature_target", "feature_definition", "attribution_target"):
        return _verify_feature_claim(raw, record)
    if raw.kind.startswith("family_"):
        names = [name for name in record.feature_names
                 if FEATURES.get(name, ("Unclassified",))[0] == raw.subject]
        total = fsum(record.shap_values[name] for name in names)
        actual = (total if raw.kind == "family_magnitude" else attribution_direction(total)
                  if raw.kind == "family_direction" else record.decision)
        correct = bool(names) and (abs(raw.claimed - actual) <= SHAP_EPSILON
                                  if raw.kind == "family_magnitude" else raw.claimed == actual)
        return Claim(raw.kind, raw.subject, raw.claimed, actual if names else None,
                     VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
                     "" if correct else "family attribution or target differs from the recorded vector", raw.span)
    if raw.kind == "attribution_scope":
        correct = raw.claimed == ATTRIBUTION_SCOPE
        return Claim(raw.kind, None, raw.claimed, ATTRIBUTION_SCOPE,
                     VERIFIABLE_CORRECT if correct else VERIFIABLE_INCORRECT,
                     "" if correct else "attribution scope differs", raw.span)
    if raw.kind == "invalid_payload":
        return Claim(kind=raw.kind, subject=None, claimed=raw.claimed, actual=None,
                     verdict=VERIFIABLE_INCORRECT,
                     reason="structured payload does not satisfy the explanation schema",
                     span="(payload) schema")
    if raw.kind == "vague":
        return Claim(
            kind="vague",
            subject=None,
            claimed=None,
            actual=None,
            verdict=UNVERIFIABLE,
            reason="line matches no known claim pattern",
            span=raw.span,
        )
    raise ValueError(f"unknown raw claim kind: {raw.kind!r}")  # fail loudly, never silently drop a claim


# --- ground-truth slot coverage (claim_recall) ------------------------------


def _expected_slots(record: DecisionRecord) -> set[tuple[str, str | None]]:
    """Every fact the template is capable of stating about `record`.

    `claim_recall` is the fraction of these slots the explanation
    actually, correctly, covered -- distinct from `numeric_fidelity`
    (which only scores claims that were MADE, right or wrong).
    """
    slots: set[tuple[str, str | None]] = {
        ("decision", None),
        ("confidence", None),
        ("notice", None),
    }
    for cls in DECISION_CLASSES:
        slots.add(("probability", cls))
    for c in record.top_k:
        slots.add(("feature_value", c.name))
        slots.add(("feature_target", c.name))
        slots.add(("shap_direction", c.name))
        slots.add(("shap_magnitude", c.name))
        slots.add(("rank", c.name))
    return slots


# --- public API --------------------------------------------------------------


def verify(record: DecisionRecord, text: str, payload: dict | None = None,
           *, strict_prose: bool = False) -> VerificationResult:
    """Run all six checks against `text` (and `payload`, if given).

    The displayed prose determines coverage and unverifiable rate. Numeric
    and directional scores use the worse result of prose and payload, so
    duplicating correct claims in one cannot hide mistakes in the other.
    Every known factual contradiction is a hard failure. Strict mode also
    rejects any line outside the supported template grammar; it does not
    claim to verify arbitrary natural-language market commentary.
    """
    prose_claims = tuple(_verify(raw, record) for raw in
                         _claims_from_prose(text, record) + _vague_claims(text, record))
    payload_claims = ()
    if payload is not None:
        try:
            payload_raw = _claims_from_payload(payload)
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            payload_raw = [_RawClaim("invalid_payload", None, str(error), "(payload) schema")]
        payload_claims = tuple(_verify(raw, record) for raw in payload_raw)
    claims = prose_claims + payload_claims

    def fidelity(source, kinds):
        selected = [c for c in source if c.kind in kinds]
        return (sum(c.verdict == VERIFIABLE_CORRECT for c in selected) / len(selected)
                if selected else 1.0)

    sources = (prose_claims, payload_claims) if payload is not None else (prose_claims,)
    numeric_fidelity = min(fidelity(source, _NUMERIC_KINDS) for source in sources)
    directional_consistency = min(fidelity(source, {"shap_direction", "family_direction"}) for source in sources)

    expected = _expected_slots(record)
    covered = {
        (c.kind, c.subject) for c in prose_claims if c.verdict == VERIFIABLE_CORRECT and (c.kind, c.subject) in expected
    }
    claim_recall = len(covered) / len(expected) if expected else 1.0

    unverifiable_rate = (sum(c.verdict == UNVERIFIABLE for c in prose_claims) / len(prose_claims)
                         if prose_claims else 1.0)

    failed_metrics = []
    if numeric_fidelity < NUMERIC_FIDELITY_THRESHOLD:
        failed_metrics.append("numeric_fidelity")
    if directional_consistency < DIRECTIONAL_CONSISTENCY_THRESHOLD:
        failed_metrics.append("directional_consistency")
    if claim_recall < CLAIM_RECALL_THRESHOLD:
        failed_metrics.append("claim_recall")
    if unverifiable_rate > UNVERIFIABLE_RATE_THRESHOLD:
        failed_metrics.append("unverifiable_rate")
    if any(c.verdict == VERIFIABLE_INCORRECT for c in claims):
        failed_metrics.append("contradictory_claim")
    required = {(kind, None) for kind in ("decision", "confidence", "notice")}
    required.update(("probability", cls) for cls in DECISION_CLASSES)
    if not required.issubset(covered):
        failed_metrics.append("missing_required_claims")
    if strict_prose and any(c.verdict == UNVERIFIABLE for c in prose_claims):
        failed_metrics.append("unsupported_prose")

    return VerificationResult(
        claims=claims,
        numeric_fidelity=numeric_fidelity,
        directional_consistency=directional_consistency,
        claim_recall=claim_recall,
        unverifiable_rate=unverifiable_rate,
        passed=not failed_metrics,
        failed_metrics=tuple(failed_metrics),
    )
