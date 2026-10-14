"""SHAP additivity (brief section 7): for every decision the engine
emits, base_value + sum(shap_values) must equal raw_model_output within
tolerance. This is checked twice, deliberately:

1. `DecisionRecord.__post_init__` already asserts it at construction --
   so every record in `engine.run_engine(...).records` has already
   passed once, implicitly, just by existing.
2. This test recomputes the identity independently, from the record's
   own public fields, for EVERY emitted record -- not a sample, and not
   trusting that construction-time success is the only evidence.

It also proves the schema's guard is load-bearing rather than a no-op:
constructing a record with a deliberately corrupted base_value, using
otherwise-real field values from an actual trained model, must raise.

Uses the real trained model and real NVDA data end-to-end (via
`engine.run_engine`), never synthetic SHAP numbers -- this is exactly
the kind of "every number comes from a run that actually happened" case
AGENTS.md is strict about.
"""
import dataclasses
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify import engine  # noqa: E402
from investify.decision_record import SHAP_ADDITIVITY_TOL, DecisionRecord  # noqa: E402


@pytest.fixture(scope="module")
def cfg() -> dict:
    return yaml.safe_load(open(Path(__file__).parent.parent / "config" / "spike.yaml"))


@pytest.fixture(scope="module")
def engine_result(cfg):
    # Trains two real XGBoost models (calibration fold + eval fold),
    # fits isotonic calibrators, runs TreeSHAP, and builds every decision
    # record for the held-out evaluation fold. No reliability-curve path
    # given -- that artifact is produced by scripts/build_decision_records.py,
    # not needed for this test.
    return engine.run_engine(cfg)


def test_at_least_one_record_emitted(engine_result):
    assert len(engine_result.records) > 0


def test_additivity_holds_for_every_emitted_decision(engine_result):
    """Recomputes base_value + sum(shap_values) == raw_model_output for
    every record independently of the schema's own constructor check."""
    residuals = []
    for record in engine_result.records:
        additive = record.base_value + sum(record.shap_values.values())
        residual = abs(additive - record.raw_model_output)
        residuals.append(residual)
        assert residual <= SHAP_ADDITIVITY_TOL, (
            f"{record.ticker} {record.session_date}: base_value + sum(shap) = {additive}, "
            f"raw_model_output = {record.raw_model_output}, residual = {residual}"
        )
    # Sanity: the check above should not be vacuously true because the
    # tolerance is huge relative to the actual numbers involved.
    assert max(residuals) < 1e-4
    assert max(residuals) > 0  # exact float equality would be suspicious, not reassuring


def test_base_value_is_independent_of_the_shap_vector(engine_result):
    """The additivity test is only meaningful if base_value was obtained
    INDEPENDENTLY of the SHAP vector it is checked against.

    If base_value were derived as raw_model_output - sum(shap_values),
    additivity would hold by construction to float precision and the test
    above would prove nothing about TreeSHAP. It must instead come from
    the explainer's own per-class expected_value -- which, being a
    property of the trained model rather than of this row, is shared by
    every record predicting the same class.
    """
    by_class: dict[str, set[float]] = {}
    for record in engine_result.records:
        by_class.setdefault(record.decision, set()).add(round(record.base_value, 12))

    for decision, base_values in by_class.items():
        assert len(base_values) == 1, (
            f"records predicting {decision!r} carry {len(base_values)} distinct base "
            f"values; a per-class expected_value must be constant across rows, so this "
            f"indicates base_value is being derived per-row from the SHAP vector"
        )


def test_shap_values_cover_exactly_the_feature_vector(engine_result, cfg):
    cols = engine.feature_cols(cfg)
    for record in engine_result.records:
        assert set(record.shap_values) == set(cols)
        assert set(record.feature_vector) == set(cols)


def test_top_k_is_a_faithful_view_of_shap_values(engine_result):
    for record in engine_result.records:
        assert len(record.top_k) <= 5
        magnitudes = [abs(c.shap_value) for c in record.top_k]
        assert magnitudes == sorted(magnitudes, reverse=True)
        for contribution in record.top_k:
            assert record.shap_values[contribution.name] == pytest.approx(
                contribution.shap_value, abs=SHAP_ADDITIVITY_TOL
            )


def test_probabilities_sum_to_one_and_match_decision(engine_result):
    for record in engine_result.records:
        assert sum(record.probabilities.values()) == pytest.approx(1.0, abs=1e-6)
        assert record.decision == max(record.probabilities, key=record.probabilities.get)


def test_corrupted_base_value_is_rejected(engine_result):
    """The schema's additivity guard must actually be load-bearing: a
    record built from real, otherwise-valid fields but with a corrupted
    base_value must fail to construct."""
    real_record = engine_result.records[0]
    corrupted_base_value = real_record.base_value + 1.0  # far outside SHAP_ADDITIVITY_TOL

    with pytest.raises(ValueError, match="SHAP additivity violated"):
        dataclasses.replace(real_record, base_value=corrupted_base_value)


def test_corrupted_base_value_far_exceeds_tolerance(engine_result):
    """Guards against a future accidental tolerance-widening making the
    corruption above too small to matter: the corruption must be many
    times the tolerance, not a hair over it."""
    real_record = engine_result.records[0]
    assert 1.0 > SHAP_ADDITIVITY_TOL * 100


def test_valid_reconstruction_of_a_real_record_does_not_raise(engine_result):
    """Companion to the corruption test: proves the guard isn't so strict
    that even a faithful round-trip of real data fails to construct --
    otherwise the rejection above would be meaningless (everything rejects)."""
    real_record = engine_result.records[0]
    rebuilt = dataclasses.replace(real_record)
    assert rebuilt.base_value == real_record.base_value
    assert isinstance(rebuilt, DecisionRecord)
