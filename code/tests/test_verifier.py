"""Tests for the deterministic verifier (brief §7): explain/template.py,
explain/verifier.py, explain/fixtures.py.

Every `DecisionRecord` here is HAND-CONSTRUCTED via `make_record` below --
a LABELLED FIXTURE, never a real model output (AGENTS.md: synthetic text
is fine for unit tests, never for the real experiment). Likewise every
corrupted explanation comes from `explain/fixtures.py`, whose own
docstring carries the same label.

Two things this suite is deliberately rigorous about, per the task brief:

1. The verifier must ACCEPT clean explanations, not just reject broken
   ones -- a verifier that rejects everything "catches every corruption"
   trivially and is worthless. `test_verifier_confusion_matrix_over_generated_fixtures`
   asserts a zero false-positive rate across every clean fixture generated.
2. If a corruption class is not reliably caught at the whole-explanation
   level, that is reported honestly (see `test_vague_unverifiable_claim_is_flagged_even_if_explanation_still_passes`
   and the confusion matrix's `per_kind["vague_unverifiable"]` entry),
   never hidden by weakening the assertion.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.decision_record import DECISION_CLASSES, DecisionRecord, rank_contributions
from investify.explain import fixtures, template, verifier

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"

# Real feature names from Phase 1 (features/indicators.py, features/sentiment.py,
# features/assembly.py) -- borrowed here only for realism; the fixture module
# itself doesn't care what the names mean, only that they form a closed set.
_REAL_FEATURE_NAMES = (
    "rsi_14",
    "macd_hist",
    "dist_sma200",
    "bollinger_pos",
    "obv_slope",
    "mean_polarity",
    "mom_3d",
    "mom_7d",
    "volume_z",
    "dispersion",
)

CONCRETE_KINDS = (
    "wrong_probability",
    "wrong_shap_magnitude",
    "flipped_direction",
    "promoted_minor_feature",
    "invented_feature_name",
)


def make_record(
    rng: np.random.Generator,
    *,
    ticker: str = "NVDA",
    session_date: str = "2023-06-01",
    horizon_days: int = 5,
    decision: str = "Buy",
    n_features: int = 8,
    k: int = 5,
    seed: int = 42,
) -> DecisionRecord:
    """Hand-constructed, self-consistent DecisionRecord. LABELLED FIXTURE.

    Builds a probability vector with a strict argmax at `decision`, a
    feature/SHAP vector over `n_features` real Phase-1 names with additive
    SHAP (base_value + sum(shap) == raw_model_output), and a faithful
    `top_k` via the frozen `rank_contributions` helper -- so every
    invariant `DecisionRecord.__post_init__` checks holds by construction.
    """
    if n_features > len(_REAL_FEATURE_NAMES):
        raise ValueError(f"n_features={n_features} exceeds the fixture name pool ({len(_REAL_FEATURE_NAMES)})")
    names = list(_REAL_FEATURE_NAMES[:n_features])

    feature_vector = {name: float(rng.normal(0, 1)) for name in names}
    shap_values = {name: float(rng.normal(0, 0.2)) for name in names}
    for name in names:
        # rank_contributions drops exactly-zero contributions; keep every
        # feature eligible so `k` is never silently shrunk.
        if shap_values[name] == 0.0:
            shap_values[name] = 0.01

    base_value = 0.1
    raw_model_output = base_value + sum(shap_values.values())

    others = [c for c in DECISION_CLASSES if c != decision]
    p_decision = 0.5 + float(rng.uniform(0.0, 0.3))
    remainder = 1.0 - p_decision
    split = float(rng.uniform(0.3, 0.7))
    p_other_1 = remainder * split
    p_other_2 = remainder - p_other_1
    probabilities = {decision: p_decision, others[0]: p_other_1, others[1]: p_other_2}

    top_k = rank_contributions(shap_values, feature_vector, k=k)

    return DecisionRecord(
        ticker=ticker,
        session_date=session_date,
        horizon_days=horizon_days,
        decision=decision,
        probabilities=probabilities,
        feature_vector=feature_vector,
        shap_values=shap_values,
        base_value=base_value,
        raw_model_output=raw_model_output,
        top_k=top_k,
        risk_tier="Balanced",
        model_version="fixture-v0",
        data_hashes={"prices": "deadbeef", "news": "cafef00d"},
        seed=seed,
    )


# --- template determinism ----------------------------------------------------


def test_template_render_is_byte_identical_for_same_record():
    rng = np.random.default_rng(21)
    record = make_record(rng, decision="Sell")
    a = template.render(record)
    b = template.render(record)
    assert a.text == b.text
    assert a.payload == b.payload


def test_fixture_generation_is_deterministic():
    rng = np.random.default_rng(99)
    record = make_record(rng, decision="Buy")
    expl = template.render(record)
    a = fixtures.corrupt(record, expl, "wrong_shap_magnitude", np.random.default_rng(7))
    b = fixtures.corrupt(record, expl, "wrong_shap_magnitude", np.random.default_rng(7))
    assert a.explanation.text == b.explanation.text
    assert a.explanation.payload == b.explanation.payload


# --- clean explanations must PASS, in both extraction modes ------------------


def test_clean_explanation_with_payload_passes_all_four_metrics():
    rng = np.random.default_rng(1)
    record = make_record(rng, decision="Buy")
    expl = template.render(record, include_payload=True)
    assert expl.payload is not None

    result = verifier.verify(record, expl.text, expl.payload)
    assert result.passed, result.failed_metrics
    assert result.numeric_fidelity == 1.0
    assert result.directional_consistency == 1.0
    assert result.claim_recall == 1.0
    assert result.unverifiable_rate == 0.0


def test_clean_explanation_prose_only_exercises_the_fallback_path_and_passes():
    """`include_payload=False` forces verifier.verify's regex-over-prose
    path (check 1's fallback) -- this must be a genuinely exercised path,
    not dead code, and it must reach the same verdict as the payload path.
    """
    rng = np.random.default_rng(2)
    record = make_record(rng, decision="Sell")
    expl = template.render(record, include_payload=False)
    assert expl.payload is None

    result = verifier.verify(record, expl.text, expl.payload)
    assert result.passed, result.failed_metrics
    assert result.numeric_fidelity == 1.0
    assert result.directional_consistency == 1.0
    assert result.claim_recall == 1.0
    assert result.unverifiable_rate == 0.0


def test_correct_payload_does_not_override_contradictory_displayed_prose():
    """Mid-eval contract: the record is authoritative over both representations."""
    rng = np.random.default_rng(11)
    record = make_record(rng, decision="Buy")
    expl = template.render(record, include_payload=True)
    corrupted = fixtures.corrupt(record, expl, "wrong_probability", np.random.default_rng(11))

    mismatched = template.Explanation(text=corrupted.explanation.text, payload=expl.payload)
    result = verifier.verify(record, mismatched.text, mismatched.payload)
    assert not result.passed
    assert result.numeric_fidelity < verifier.NUMERIC_FIDELITY_THRESHOLD


# --- one targeted test per check, using the fixture that specifically
# --- exercises it ------------------------------------------------------------


def test_wrong_probability_flagged_by_tolerance_check():
    rng = np.random.default_rng(3)
    record = make_record(rng, decision="Buy")
    expl = template.render(record)
    corrupted = fixtures.corrupt(record, expl, "wrong_probability", np.random.default_rng(3))
    result = verifier.verify(record, corrupted.explanation.text, corrupted.explanation.payload)
    assert not result.passed
    assert "numeric_fidelity" in result.failed_metrics
    bad = [c for c in result.claims if c.kind == "confidence" and c.verdict == verifier.VERIFIABLE_INCORRECT]
    assert bad, "expected the confidence claim to fail tolerance matching"


def test_wrong_shap_magnitude_flagged_by_tolerance_check():
    rng = np.random.default_rng(4)
    record = make_record(rng, decision="Hold")
    expl = template.render(record)
    corrupted = fixtures.corrupt(record, expl, "wrong_shap_magnitude", np.random.default_rng(4))
    result = verifier.verify(record, corrupted.explanation.text, corrupted.explanation.payload)
    assert not result.passed
    assert "numeric_fidelity" in result.failed_metrics
    bad = [c for c in result.claims if c.kind == "shap_magnitude" and c.verdict == verifier.VERIFIABLE_INCORRECT]
    assert bad, "expected a shap_magnitude claim to fail tolerance matching"


def test_flipped_direction_flagged_by_sign_check():
    rng = np.random.default_rng(5)
    record = make_record(rng, decision="Buy")
    expl = template.render(record)
    corrupted = fixtures.corrupt(record, expl, "flipped_direction", np.random.default_rng(5))
    result = verifier.verify(record, corrupted.explanation.text, corrupted.explanation.payload)
    assert not result.passed
    assert "directional_consistency" in result.failed_metrics
    bad = [c for c in result.claims if c.kind == "shap_direction" and c.verdict == verifier.VERIFIABLE_INCORRECT]
    assert bad, "expected a shap_direction claim to fail the sign check"


def test_promoted_minor_feature_flagged_by_rank_check():
    rng = np.random.default_rng(6)
    record = make_record(rng, decision="Hold", n_features=8, k=5)
    expl = template.render(record)
    corrupted = fixtures.corrupt(record, expl, "promoted_minor_feature", np.random.default_rng(6))
    result = verifier.verify(record, corrupted.explanation.text, corrupted.explanation.payload)
    assert not result.passed
    rank_failures = [c for c in result.claims if c.kind == "rank" and c.verdict == verifier.VERIFIABLE_INCORRECT]
    assert rank_failures, "expected a rank claim to fail rank consistency"
    assert "promoted" in rank_failures[0].reason


def test_invented_feature_name_flagged_by_closed_vocabulary_check():
    rng = np.random.default_rng(8)
    record = make_record(rng, decision="Buy")
    expl = template.render(record)
    corrupted = fixtures.corrupt(record, expl, "invented_feature_name", np.random.default_rng(8))
    result = verifier.verify(record, corrupted.explanation.text, corrupted.explanation.payload)
    assert not result.passed
    vocab_failures = [c for c in result.claims if "closed feature vocabulary" in c.reason]
    assert vocab_failures, "expected at least one claim to fail closed-vocabulary validation"
    # the invented name cascades: direction, magnitude and rank all become
    # provably wrong, not merely "unable to check"
    assert all(c.verdict == verifier.VERIFIABLE_INCORRECT for c in vocab_failures)


def test_vague_unverifiable_claim_is_flagged_even_if_explanation_still_passes():
    """Check 6's claim-level classification: the injected filler sentence
    must be found and classified UNVERIFIABLE as an atomic claim, whether
    or not it moves any of the four headline metrics past its threshold
    (see the confusion matrix test / final report for the honest reading
    of whole-explanation detection for this corruption class).
    """
    rng = np.random.default_rng(9)
    record = make_record(rng, decision="Buy")
    expl = template.render(record)
    corrupted = fixtures.corrupt(record, expl, "vague_unverifiable", np.random.default_rng(9))
    result = verifier.verify(record, corrupted.explanation.text, corrupted.explanation.payload)
    vague_claims = [c for c in result.claims if c.kind == "vague"]
    assert len(vague_claims) == 1
    assert vague_claims[0].verdict == verifier.UNVERIFIABLE


# --- ~100-fixture sweep: confusion matrix -------------------------------------


def _fixture_records() -> list[DecisionRecord]:
    configs = [
        (0, dict(ticker="NVDA", decision="Buy", n_features=8, k=5)),
        (1, dict(ticker="NVDA", decision="Sell", n_features=6, k=3)),
        (2, dict(ticker="NVDA", decision="Hold", n_features=10, k=6)),
        (3, dict(ticker="NVDA", decision="Buy", n_features=5, k=4)),
        (4, dict(ticker="NVDA", decision="Sell", n_features=9, k=5)),
        (5, dict(ticker="NVDA", decision="Buy", n_features=7, k=5)),
        (6, dict(ticker="NVDA", decision="Hold", n_features=8, k=4)),
        (7, dict(ticker="NVDA", decision="Sell", n_features=10, k=6)),
    ]
    records = []
    for seed, params in configs:
        rng = np.random.default_rng(seed)
        records.append(make_record(rng, seed=seed, **params))
    return records


def test_verifier_confusion_matrix_over_generated_fixtures():
    records = _fixture_records()
    rows: list[dict] = []

    for i, record in enumerate(records):
        for payload_mode in (True, False):
            expl = template.render(record, include_payload=payload_mode)
            clean_result = verifier.verify(record, expl.text, expl.payload)
            rows.append({"label": "clean", "payload_mode": payload_mode, "passed": clean_result.passed})

            rng = np.random.default_rng(1000 + i * 10 + int(payload_mode))
            for kind in fixtures.CORRUPTION_KINDS:
                corrupted = fixtures.corrupt(record, expl, kind, rng)
                result = verifier.verify(record, corrupted.explanation.text, corrupted.explanation.payload)
                rows.append({"label": kind, "payload_mode": payload_mode, "passed": result.passed})

    assert len(rows) >= 100, f"expected at least 100 generated fixtures, got {len(rows)}"

    tp = sum(1 for r in rows if r["label"] != "clean" and not r["passed"])
    fn = sum(1 for r in rows if r["label"] != "clean" and r["passed"])
    tn = sum(1 for r in rows if r["label"] == "clean" and r["passed"])
    fp = sum(1 for r in rows if r["label"] == "clean" and not r["passed"])

    per_kind = {}
    for kind in ("clean",) + fixtures.CORRUPTION_KINDS:
        kind_rows = [r for r in rows if r["label"] == kind]
        detected = sum(1 for r in kind_rows if not r["passed"])
        n = len(kind_rows)
        per_kind[kind] = {
            "n": n,
            "detected_as_corrupt": detected,
            "detection_rate": None if kind == "clean" else detected / n,
            "clean_pass_rate": (n - detected) / n if kind == "clean" else None,
        }

    matrix = {
        "n_fixtures": len(rows),
        "confusion": {
            "true_positive": tp,
            "false_negative": fn,
            "true_negative": tn,
            "false_positive": fp,
        },
        "per_kind": per_kind,
    }

    # Historical experiment artifacts are not overwritten by a test run.
    report_path = os.environ.get("INVESTIFY_VERIFIER_REPORT")
    if report_path:
        destination = Path(report_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(matrix, indent=2), encoding="utf-8")

    print(f"\nVerifier confusion matrix over {len(rows)} fixtures (clean + 6 corruption kinds x {len(records)} records x 2 payload modes):")
    print(f"  predicted corrupt | actual corrupt=TP={tp:3d}   actual clean=FP={fp:3d}")
    print(f"  predicted clean   | actual corrupt=FN={fn:3d}   actual clean=TN={tn:3d}")
    print("  per-kind detection:")
    for kind, stats in per_kind.items():
        rate = stats["clean_pass_rate"] if kind == "clean" else stats["detection_rate"]
        label = "clean_pass_rate" if kind == "clean" else "detection_rate"
        print(f"    {kind:>24s}: n={stats['n']:3d}  {label}={rate:.3f}")

    # A verifier that rejects everything "catches every corruption"
    # trivially -- this is the check that rules that out.
    assert fp == 0, "verifier rejected at least one clean explanation (false positive)"
    assert per_kind["clean"]["clean_pass_rate"] == 1.0

    # Every corruption that changes a number, a sign, a rank, or a feature
    # identity must be caught every time, in both extraction modes.
    for kind in CONCRETE_KINDS:
        assert per_kind[kind]["detection_rate"] == 1.0, f"{kind} was not reliably detected: {per_kind[kind]}"

    # vague_unverifiable is deliberately NOT asserted here at the
    # whole-explanation level -- see this module's docstring and the
    # final report: a single filler sentence among many correct, concrete
    # claims does not, by this design, move any of the four metrics past
    # its threshold, even though check 6 correctly classifies the
    # sentence itself as UNVERIFIABLE (see the dedicated test above).
    # We only assert the actual rate got recorded, honestly, either way.
    assert per_kind["vague_unverifiable"]["detection_rate"] is not None
