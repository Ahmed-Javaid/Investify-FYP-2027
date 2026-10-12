"""The verified-or-template seam (brief section 7): an unverified
explanation must never be emitted.

Runs against REAL decision records from artifacts/decision_records.json
where available, so this is not only exercised on fixtures.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.decision_record import DecisionRecord  # noqa: E402
from investify.explain.fixtures import CORRUPTION_KINDS, corrupt  # noqa: E402
from investify.explain.pipeline import emit  # noqa: E402
from investify.explain.template import render  # noqa: E402

RECORDS_PATH = Path("artifacts/decision_records.json")


@pytest.fixture(scope="module")
def real_records() -> list[DecisionRecord]:
    if not RECORDS_PATH.exists():
        pytest.skip(f"{RECORDS_PATH} not built; run scripts/build_decision_records.py")
    payload = json.loads(RECORDS_PATH.read_text())
    return [DecisionRecord.from_dict(r) for r in payload["decision_records"][:20]]


def test_template_is_emitted_and_verifies_on_real_records(real_records):
    for record in real_records:
        emitted = emit(record)
        assert emitted.verification.passed
        assert not emitted.replaced_by_template
        assert record.decision in emitted.text


def test_a_passing_candidate_is_emitted_unchanged(real_records):
    record = real_records[0]
    candidate = render(record)
    emitted = emit(record, candidate=candidate)
    assert not emitted.replaced_by_template
    assert emitted.text == candidate.text


@pytest.mark.parametrize("kind", [k for k in CORRUPTION_KINDS if k != "vague_unverifiable"])
def test_a_failing_candidate_is_replaced_by_the_template(real_records, kind):
    """Every corruption class the verifier detects must be swapped out for
    the template rather than reaching the user."""
    import numpy as np

    record = real_records[0]
    clean = render(record)
    corrupted = corrupt(record, clean, kind, np.random.default_rng(42))

    emitted = emit(record, candidate=corrupted.explanation)

    assert emitted.replaced_by_template, f"{kind} was emitted instead of being replaced"
    assert emitted.text == clean.text
    assert emitted.rejected_candidate is not None
    assert emitted.verification.passed  # what we DID emit is verified


def test_emitted_text_always_carries_the_non_advice_notice(real_records):
    for record in real_records[:5]:
        assert "Not investment advice" in emit(record).text
