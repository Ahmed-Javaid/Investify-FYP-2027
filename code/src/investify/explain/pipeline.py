"""The emit path for the supported-claim verification contract.

The rule is "any explanation failing verification is replaced by the
deterministic template, so an unverified explanation is never emitted."
The numeric template is the historical baseline. Candidates and labelled
corruptions exercise this verified-or-template seam. The local pilot in
local_llm.py adds bounded generation retries and a verified comparator
with maintained feature definitions; QLoRA remains a later milestone.

`emit()` therefore takes an optional `candidate` explanation. Given one,
it verifies it and falls back to the template if it fails. Given none,
it renders and verifies the template itself, which must always pass --
if the template ever fails its own verifier, something is wrong with one
of them, and that is raised rather than quietly returned.
"""
from dataclasses import dataclass

from investify.decision_record import DecisionRecord
from investify.explain.template import Explanation, render
from investify.explain.verifier import VerificationResult, verify


@dataclass(frozen=True)
class EmittedExplanation:
    """What the demo renders: the text, the per-claim verifier report
    behind it, and whether a candidate was rejected on the way."""

    explanation: Explanation
    verification: VerificationResult
    replaced_by_template: bool
    rejected_candidate: Explanation | None = None
    rejected_verification: VerificationResult | None = None

    @property
    def text(self) -> str:
        return self.explanation.text


def emit(record: DecisionRecord, candidate: Explanation | None = None,
         *, strict_prose: bool = False, policy_action: str | None = None) -> EmittedExplanation:
    """Verify `candidate` and emit it, or fall back to the deterministic
    template. With no candidate, emit the verified template directly.

    strict_prose=True also rejects unparsed lines. Default mode retains
    the documented unverifiable-rate allowance; passing it does not
    certify arbitrary natural-language statements.
    """
    if candidate is not None:
        result = verify(record, candidate.text, candidate.payload, strict_prose=strict_prose, policy_action=policy_action)
        if result.passed:
            return EmittedExplanation(
                explanation=candidate,
                verification=result,
                replaced_by_template=False,
            )
        fallback = render(record, policy_action=policy_action)
        fallback_result = verify(record, fallback.text, fallback.payload, policy_action=policy_action)
        _assert_template_verifies(record, fallback_result)
        return EmittedExplanation(
            explanation=fallback,
            verification=fallback_result,
            replaced_by_template=True,
            rejected_candidate=candidate,
            rejected_verification=result,
        )

    explanation = render(record, policy_action=policy_action)
    result = verify(record, explanation.text, explanation.payload, policy_action=policy_action)
    _assert_template_verifies(record, result)
    return EmittedExplanation(
        explanation=explanation,
        verification=result,
        replaced_by_template=False,
    )


def _assert_template_verifies(record: DecisionRecord, result: VerificationResult) -> None:
    """The deterministic template is grounded by construction. If it fails
    its own verifier, one of the two is broken and the failure must be
    loud -- silently emitting it would defeat the entire mechanism."""
    if not result.passed:
        raise ValueError(
            f"the deterministic template failed verification for "
            f"{record.ticker} {record.session_date}: failed metrics "
            f"{result.failed_metrics}. The template is grounded by construction, "
            f"so this indicates a bug in template.py or verifier.py, not a bad "
            f"explanation."
        )
