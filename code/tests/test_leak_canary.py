"""The crux test (brief section 6).

A leakage detector that has stopped detecting is worse than no detector
at all, because every downstream result silently inherits the trust it
no longer earns. So this test asserts both directions:

  * D_CENTRED -- a feature with a deliberate centred (future-peeking)
    window -- MUST breach the leak threshold with positive lift.
  * A_CLEAN -- the correct pipeline -- must NOT show positive lift above
    the threshold.

It re-runs both arms for real rather than reading artifacts/results.json,
so a stale artifact cannot make a broken canary look healthy. That costs
roughly 30 seconds.

A_CLEAN's 5-day result is asserted in the direction that matters (no
look-ahead) but is NOT asserted to sit within +/-0.03 of chance, because
it does not: it sits significantly BELOW chance. See
artifacts/phase2_report.md. That is a reported finding, not something
this test papers over -- test_a_clean_below_chance_state_is_unchanged
pins the current value so the number cannot drift unnoticed.
"""
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.harness.arms import ARMS, build_all_matrices, clean_row_mask, run_arm  # noqa: E402

HORIZON = 5  # the primary horizon (config/spike.yaml: primary_horizon_days)


@pytest.fixture(scope="module")
def cfg() -> dict:
    return yaml.safe_load(open("config/spike.yaml"))


@pytest.fixture(scope="module")
def arm_results(cfg) -> dict:
    """Run only the two arms this test decides on, at the primary horizon."""
    matrices = build_all_matrices(cfg)
    row_mask = clean_row_mask(matrices["A_CLEAN"], HORIZON, cfg)
    return {
        name: run_arm(ARMS[name], matrices[name], row_mask, HORIZON, cfg)
        for name in ("A_CLEAN", "D_CENTRED")
    }


def test_centred_canary_still_detects(arm_results, cfg):
    """If this fails, the leak canary has gone quiet and NOTHING else in
    the harness can be trusted until it is fixed."""
    d = arm_results["D_CENTRED"]
    threshold = cfg["leakage_control"]["pass_threshold_abs_lift"]

    assert d["verdict"] == "LEAK", (
        f"leak canary went quiet: D_CENTRED verdict is {d['verdict']!r} "
        f"(lift={d['lift']:+.4f}, CI=[{d['ci_lo']:+.4f}, {d['ci_hi']:+.4f}])"
    )
    assert d["lift"] > threshold, (
        f"D_CENTRED lift {d['lift']:+.4f} does not exceed the {threshold} threshold"
    )
    assert d["ci_lo"] > 0, (
        f"D_CENTRED bootstrap CI must exclude zero, got "
        f"[{d['ci_lo']:+.4f}, {d['ci_hi']:+.4f}]"
    )


def test_clean_arm_shows_no_look_ahead(arm_results, cfg):
    """The clean pipeline must not score ABOVE a stratified-random
    baseline. Positive lift here would mean the harness itself leaks."""
    a = arm_results["A_CLEAN"]
    threshold = cfg["leakage_control"]["pass_threshold_abs_lift"]

    assert a["lift"] <= threshold, (
        f"A_CLEAN shows positive lift {a['lift']:+.4f} above the {threshold} "
        f"threshold -- that is a leakage alarm in our own pipeline, to be "
        f"investigated and reported, never tuned away"
    )
    assert a["verdict"] != "LEAK", f"A_CLEAN verdict is {a['verdict']!r}"


def test_canary_separation_is_large(arm_results):
    """The gap between the leaked and clean arms is what makes any later
    positive result interpretable."""
    a, d = arm_results["A_CLEAN"], arm_results["D_CENTRED"]
    separation = d["lift"] - a["lift"]
    assert separation > 0.10, (
        f"leaked and clean arms are only {separation:.4f} apart in lift; "
        f"the canary is too faint to interpret downstream results against"
    )


def test_a_clean_below_chance_state_is_unchanged(arm_results):
    """A_CLEAN sits significantly BELOW chance at the 5-day horizon --
    a model with no usable signal being confidently wrong out-of-sample
    across NVDA's regime shifts, not leakage (an oracle-feature positive
    control confirms the pipeline detects real signal at lift +0.66).

    This is a known, reported failure of the brief's pass condition. The
    value is pinned so it cannot silently drift; if it moves, update
    artifacts/phase2_report.md rather than loosening the bound.
    """
    a = arm_results["A_CLEAN"]
    assert a["verdict"] == "BELOW_CHANCE", f"expected BELOW_CHANCE, got {a['verdict']!r}"
    assert -0.09 < a["lift"] < -0.05, f"A_CLEAN 5d lift moved to {a['lift']:+.4f}"
