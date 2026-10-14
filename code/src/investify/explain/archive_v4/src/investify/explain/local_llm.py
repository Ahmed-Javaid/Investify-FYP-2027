"""Local structured-output pilot with checked definitions and bounded fallback.

No inference dependency or default model download. A configured, running local
LM Studio-compatible endpoint is required for real generations. Mock provider
responses belong only in labelled tests, never in evaluation results.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field, replace
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from investify.decision_record import DecisionRecord
from investify.explain.context import FEATURES, build_context
from investify.explain.pipeline import EmittedExplanation
from investify.explain.template import Explanation, render_guided
from investify.explain.verifier import VERIFIABLE_CORRECT, VerificationResult, verify

PROMPT_VERSION = "mideval-local-complete-evidence-v2"
MAX_RESPONSE_BYTES = 256 * 1024


class ProviderUnavailable(RuntimeError):
    """The local service could not return a completion."""


class InvalidGeneration(ValueError):
    """The returned completion does not implement the output contract."""


@dataclass(frozen=True)
class ExplainerConfig:
    model: str | None = None
    base_url: str = "http://127.0.0.1:1234/v1"
    timeout_seconds: float = 20
    max_attempts: int = 2
    max_tokens: int = 4096
    api_key: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        parsed = urlsplit(self.base_url)
        try:
            parsed.port
        except ValueError:
            raise ValueError("The local API URL has an invalid port") from None
        if (parsed.scheme not in {"http", "https"} or
                parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or
                parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("The pilot requires a local loopback API URL without credentials/query")
        if self.model is not None and (not isinstance(self.model, str) or not self.model.strip()):
            raise ValueError("model must be a nonempty exact provider identifier or None")
        if (type(self.timeout_seconds) not in {int, float} or
                not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 60):
            raise ValueError("timeout must be finite and in (0, 60] seconds")
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 2:
            raise ValueError("the pilot permits one or two attempts")
        if type(self.max_tokens) is not int or not 256 <= self.max_tokens <= 4096:
            raise ValueError("max_tokens must be an integer in [256, 4096]")
        if self.api_key is not None and (not isinstance(self.api_key, str) or not self.api_key
                or not self.api_key.isascii() or any(c.isspace() or ord(c) < 32 for c in self.api_key)):
            raise ValueError("The local API token format is invalid")


@dataclass(frozen=True)
class Completion:
    content: str
    served_model: str | None = None
    usage: dict | None = None
    finish_reason: str | None = "stop"


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


class LocalChatClient:
    def __init__(self, config: ExplainerConfig):
        self.config = config

    def complete(self, body: dict) -> Completion:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = "Bearer " + self.config.api_key
        request = Request(self.config.base_url.rstrip("/") + "/chat/completions",
                          data=json.dumps(body, allow_nan=False).encode("utf-8"),
                          headers=headers)
        # Direct local connection: do not forward the prompt through a proxy
        # or follow a service redirect to a different destination.
        from urllib.request import ProxyHandler
        opener = build_opener(ProxyHandler({}), _NoRedirects())
        try:
            with opener.open(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            raise ProviderUnavailable(f"Local provider returned HTTP {error.code}") from None
        except (URLError, TimeoutError, OSError):
            raise ProviderUnavailable("Local model service is unavailable or timed out") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise InvalidGeneration("Provider response exceeded the size limit")
        try:
            data = json.loads(raw)
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise InvalidGeneration("Provider returned no generated text")
            usage = data.get("usage")
            if not isinstance(usage, dict):
                usage = None
            else:
                usage = {key: value for key, value in usage.items()
                         if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
                         and type(value) is int and value >= 0}
            served = data.get("model")
            return Completion(content, served if isinstance(served, str) else None, usage,
                              choice.get("finish_reason"))
        except (KeyError, IndexError, TypeError, ValueError, UnicodeError) as error:
            if isinstance(error, InvalidGeneration):
                raise
            raise InvalidGeneration("Provider returned an invalid completion envelope") from None


def response_schema(record: DecisionRecord) -> dict:
    names = list(record.feature_names)
    number = {"type": "number"}
    nullable_number = {"type": ["number", "null"]}
    contribution = {"type": "object", "additionalProperties": False,
                    "properties": {"name": {"type": "string", "enum": names},
                                   "value": nullable_number, "shap_value": number,
                                   "rank": {"type": "integer", "minimum": 1},
                                   "direction": {"type": "string", "enum": ["supports", "opposes"]}},
                    "required": ["name", "value", "shap_value", "rank", "direction"]}
    definition = {"type": "object", "additionalProperties": False,
                  "properties": {"name": {"type": "string", "enum": names},
                                 "meaning": {"type": "string"}},
                  "required": ["name", "meaning"]}
    evidence = {"type": "object", "additionalProperties": False,
                "properties": {"name": {"type": "string", "enum": names},
                               "value": nullable_number, "shap_value": number,
                               "direction": {"type": "string", "enum": ["supports", "opposes", "neutral"]}},
                "required": ["name", "value", "shap_value", "direction"]}
    family = {"type": "object", "additionalProperties": False,
              "properties": {"name": {"type": "string", "enum":
                                        sorted({FEATURES.get(name, ("Unclassified",))[0] for name in names})},
                             "shap_value": number,
                             "direction": {"type": "string", "enum": ["supports", "opposes", "neutral"]}},
              "required": ["name", "shap_value", "direction"]}
    payload = {"type": "object", "additionalProperties": False,
               "properties": {"ticker": {"type": "string"}, "session_date": {"type": "string"},
                              "horizon_days": {"type": "integer"},
                              "decision": {"type": "string", "enum": ["Buy", "Hold", "Sell"]},
                              "confidence": number,
                              "probabilities": {"type": "object", "additionalProperties": False,
                                                "properties": {name: number for name in ("Buy", "Hold", "Sell")},
                                                "required": ["Buy", "Hold", "Sell"]},
                              "contributions": {"type": "array", "items": contribution},
                              "definitions": {"type": "array", "items": definition},
                              "feature_evidence": {"type": "array", "items": evidence},
                              "family_contributions": {"type": "array", "items": family},
                              "attribution_scope": {"type": "string"},
                              "non_advice_notice": {"type": "string"}},
               "required": ["ticker", "session_date", "horizon_days", "decision", "confidence",
                            "probabilities", "contributions", "definitions", "feature_evidence",
                            "family_contributions", "attribution_scope", "non_advice_notice"]}
    return {"type": "object", "additionalProperties": False,
            "properties": {"text": {"type": "string"}, "payload": payload},
            "required": ["text", "payload"]}


def build_messages(record: DecisionRecord, corpus: str) -> list[dict]:
    guide = render_guided(record)
    return [{"role": "system", "content": (
        "Explain a recorded educational model decision. Return only the requested JSON object, "
        "with text and payload. The decision record is authoritative. Use the exact supported "
        "sentence patterns in the reference text, one sentence per line. You may reorder the "
        "feature and definition lines, but retain every feature value/contribution/direction, "
        "both family totals and attribution scope, all required facts and all reviewed definitions "
        "exactly. Copy definition wording; do not invent market causes, social data, risk "
        "conditioning, live freshness, returns or guarantees. Keep the advisory notice exactly. "
        "SHAP describes the raw model score, not market causation or calibrated probability. "
        "This is a constrained pilot; do not add unrecognised headings or free commentary."
    )}, {"role": "user", "content": json.dumps({"prompt_version": PROMPT_VERSION,
        "evidence": build_context(record, corpus=corpus),
        "reference_text": guide.text, "reference_payload": guide.payload}, allow_nan=False)}]


def parse_candidate(content: str) -> Explanation:
    def invalid_number(_value):
        raise InvalidGeneration("Non-finite JSON numbers are not permitted")
    try:
        data = json.loads(content, parse_constant=invalid_number)
    except (ValueError, TypeError) as error:
        if isinstance(error, InvalidGeneration):
            raise
        raise InvalidGeneration("Completion is not a plain JSON object") from None
    if (not isinstance(data, dict) or set(data) != {"text", "payload"} or
            not isinstance(data["text"], str) or not isinstance(data["payload"], dict) or
            not {"definitions", "feature_evidence", "family_contributions", "attribution_scope"}
                .issubset(data["payload"])):
        raise InvalidGeneration("Completion requires text and the complete guided evidence payload")
    return Explanation(data["text"], data["payload"])


def verify_generated(record: DecisionRecord, candidate: Explanation) -> VerificationResult:
    result = verify(record, candidate.text, candidate.payload, strict_prose=True)
    expected = set(record.feature_names) & set(FEATURES)
    covered = {claim.subject for claim in result.claims
               if claim.kind == "feature_definition" and claim.verdict == VERIFIABLE_CORRECT
               and not claim.span.startswith("(payload)")}
    payload_covered = {claim.subject for claim in result.claims
                       if claim.kind == "feature_definition" and claim.verdict == VERIFIABLE_CORRECT
                       and claim.span.startswith("(payload)")}
    if covered != expected or payload_covered != expected:
        result = replace(result, passed=False,
                         failed_metrics=result.failed_metrics + ("definition_coverage",))
    # Top-k coverage remains a separate, historically comparable metric. The
    # richer pilot must additionally cover ALL evidence in BOTH representations.
    for field, kinds, prefixes, subjects, failure in (
        ("features", {"feature_value", "shap_magnitude", "shap_direction", "attribution_target"},
         ("Recorded feature ", "(payload) evidence "), set(record.feature_names), "feature_evidence_coverage"),
        ("families", {"family_magnitude", "family_direction", "family_target"},
         ("Family contribution for ", "(payload) family "),
         {FEATURES.get(name, ("Unclassified",))[0] for name in record.feature_names}, "family_evidence_coverage"),
    ):
        expected_slots = {(kind, name) for kind in kinds for name in subjects}
        for prefix in prefixes:
            slots = {(claim.kind, claim.subject) for claim in result.claims
                     if claim.span.startswith(prefix) and claim.verdict == VERIFIABLE_CORRECT}
            if not expected_slots.issubset(slots):
                result = replace(result, passed=False, failed_metrics=result.failed_metrics + (failure,))
                break
    scope_claims = [claim for claim in result.claims if claim.kind == "attribution_scope"
                    and claim.verdict == VERIFIABLE_CORRECT]
    if not any(c.span.startswith("(payload)") for c in scope_claims) or not any(
            not c.span.startswith("(payload)") for c in scope_claims):
        result = replace(result, passed=False, failed_metrics=result.failed_metrics + ("attribution_scope",))
    return result


@dataclass(frozen=True)
class GenerationAttempt:
    number: int
    raw_output: str | None
    served_model: str | None
    elapsed_seconds: float
    prompt_sha256: str
    error: str | None
    candidate: Explanation | None = None
    verification: VerificationResult | None = None
    usage: dict | None = None
    finish_reason: str | None = None


@dataclass(frozen=True)
class ExplainerResult:
    emitted: EmittedExplanation
    status: str
    reason: str
    requested_model: str | None
    attempts: tuple[GenerationAttempt, ...]
    used_template: bool
    prompt_version: str = PROMPT_VERSION


class LocalExplainer:
    def __init__(self, config: ExplainerConfig | None = None, *, client=None):
        self.config = config or ExplainerConfig()
        self.client = client or LocalChatClient(self.config)

    def explain(self, record: DecisionRecord, *, corpus: str) -> ExplainerResult:
        attempts = []
        if self.config.model is None:
            return self._fallback(record, "template_unconfigured",
                                  "No local LLM is configured; a verified deterministic explanation is shown", attempts)
        messages = build_messages(record, corpus)
        status = "template_generation_failed"
        reason = "Local generation failed its output contract"
        for number in range(1, self.config.max_attempts + 1):
            started = time.perf_counter()
            prompt_hash = hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()
            completion = None
            candidate = None
            result = None
            error = None
            try:
                completion = self.client.complete({"model": self.config.model, "messages": messages,
                    "temperature": 0, "seed": record.seed, "max_tokens": self.config.max_tokens,
                    "stream": False, "response_format": {"type": "json_schema", "json_schema": {
                        "name": "investify_explanation", "strict": True, "schema": response_schema(record)}}})
                if completion.finish_reason not in (None, "stop"):
                    raise InvalidGeneration("Provider did not complete the generation")
                candidate = parse_candidate(completion.content)
                result = verify_generated(record, candidate)
                if not result.passed:
                    error = "Verification failed: " + ", ".join(result.failed_metrics)
                    status, reason = "template_verification_failed", error
            except ProviderUnavailable as failure:
                error = str(failure)
                status, reason = "template_unavailable", error
            except InvalidGeneration as failure:
                error = str(failure)
                status, reason = "template_generation_failed", error
            attempts.append(GenerationAttempt(number, completion.content if completion else None,
                completion.served_model if completion else None, round(time.perf_counter() - started, 6),
                prompt_hash, error, candidate, result, completion.usage if completion else None,
                completion.finish_reason if completion else None))
            if result is not None and result.passed:
                emitted = EmittedExplanation(candidate, result, False)
                return ExplainerResult(emitted, "generated_verified", "Local generation passed the constrained contract",
                                       self.config.model, tuple(attempts), False)
            if status == "template_unavailable":
                break
            messages = messages + [{"role": "user", "content":
                "The previous attempt failed: " + str(error) + ". Regenerate the complete JSON; "
                "retain all exact recorded facts, supported sentences and reviewed definitions."}]
        return self._fallback(record, status, reason, attempts)

    def _fallback(self, record, status, reason, attempts):
        guide = render_guided(record)
        result = verify_generated(record, guide)
        if not result.passed:
            raise ValueError("The deterministic guided fallback failed verification: " + str(result.failed_metrics))
        last = attempts[-1] if attempts else None
        emitted = EmittedExplanation(guide, result, bool(attempts),
                                     last.candidate if last else None,
                                     last.verification if last else None)
        return ExplainerResult(emitted, status, reason, self.config.model, tuple(attempts), True)
