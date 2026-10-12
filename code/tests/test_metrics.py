"""tests/test_metrics.py -- brief section 6: scoring for the five-arm
leakage harness. These numbers are the harness's whole claim, so every
semantic (train-distribution baseline, class-absent-still-counts-as-zero,
CI convention, verdict rule) is pinned down here before metrics.py exists.

All arrays below are small synthetic fixtures built for this test file
only -- no real data is needed for a metrics module.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.harness.metrics import (  # noqa: E402
    bootstrap_lift_ci,
    brier_score,
    macro_f1,
    stratified_random_baseline,
    verdict,
)

CLASSES = ["Buy", "Hold", "Sell"]


# ---------------------------------------------------------------------------
# macro_f1
# ---------------------------------------------------------------------------


def test_macro_f1_perfect_prediction_is_one():
    y_true = ["Buy", "Hold", "Sell", "Buy", "Hold", "Sell"]
    y_pred = list(y_true)
    assert macro_f1(y_true, y_pred) == pytest.approx(1.0)


def test_macro_f1_hand_computed_example():
    # fixture: 6 samples, 3 classes.
    # y_true = Buy, Buy, Hold, Hold, Sell, Sell
    # y_pred = Buy, Hold, Hold, Hold, Sell, Buy
    #
    # Confusion by class:
    #   Buy:  TP=1 (idx0), FN=1 (idx1 predicted Hold), FP=0
    #         precision = 1/1 = 1.0, recall = 1/2 = 0.5
    #         F1_Buy = 2*1.0*0.5/(1.0+0.5) = 1.0/1.5 = 0.6666...
    #   Hold: TP=2 (idx2,idx3), FN=0, FP=1 (idx1's true label was Buy)
    #         precision = 2/3 = 0.6666..., recall = 2/2 = 1.0
    #         F1_Hold = 2*(2/3)*1.0/((2/3)+1.0) = (4/3)/(5/3) = 0.8
    #   Sell: TP=1 (idx4), FN=1 (idx5 predicted Buy), FP=1 (idx5's pred)
    #         precision = 1/2 = 0.5, recall = 1/2 = 0.5
    #         F1_Sell = 2*0.5*0.5/(0.5+0.5) = 0.5
    #
    # macro F1 = (0.666666... + 0.8 + 0.5) / 3 = 1.966666.../3 = 0.655555...
    y_true = ["Buy", "Buy", "Hold", "Hold", "Sell", "Sell"]
    y_pred = ["Buy", "Hold", "Hold", "Hold", "Sell", "Buy"]
    expected = ((2 / 3) + 0.8 + 0.5) / 3
    assert macro_f1(y_true, y_pred) == pytest.approx(expected, abs=1e-9)


def test_macro_f1_missing_class_counts_as_zero_not_dropped():
    # Only Buy and Hold appear in this fold at all -- Sell is entirely
    # absent from both true and predicted labels. Without an explicit
    # `labels=` list, sklearn would silently average over 2 classes
    # instead of 3, inflating the score.
    y_true = ["Buy", "Buy", "Hold", "Hold"]
    y_pred = ["Buy", "Hold", "Hold", "Hold"]
    # Buy: TP=1, FN=1, FP=0 -> P=1.0, R=0.5 -> F1=0.6666...
    # Hold: TP=2, FN=0, FP=1 -> P=2/3, R=1.0 -> F1=0.8
    # Sell: never predicted, never true -> F1=0 by convention (zero_division=0)
    expected = ((2 / 3) + 0.8 + 0.0) / 3
    assert macro_f1(y_true, y_pred) == pytest.approx(expected, abs=1e-9)
    # sanity: this is strictly less than what you'd get averaging only
    # the 2 classes that actually appear
    two_class_avg = ((2 / 3) + 0.8) / 2
    assert macro_f1(y_true, y_pred) < two_class_avg


# ---------------------------------------------------------------------------
# stratified_random_baseline
# ---------------------------------------------------------------------------


def test_stratified_baseline_balanced_lands_near_one_third():
    rng = np.random.default_rng(0)
    train_labels = rng.choice(CLASSES, size=3000, p=[1 / 3, 1 / 3, 1 / 3]).tolist()
    test_labels = rng.choice(CLASSES, size=500, p=[1 / 3, 1 / 3, 1 / 3]).tolist()
    baseline = stratified_random_baseline(train_labels, test_labels, seed=42, n_draws=1000)
    assert baseline == pytest.approx(1 / 3, abs=0.03)


def test_stratified_baseline_imbalanced_but_matched_still_near_one_third():
    # Mathematical property of stratified-random guessing, not a bug:
    # when predictions are drawn i.i.d. from the SAME distribution the
    # true labels came from, precision_i and recall_i both converge to
    # p_i for every class i (independence of draw and truth), so
    # F1_i ~= p_i and macro-F1 ~= mean(p_i) = 1/3 for 3 classes no
    # matter how skewed that shared distribution is. Macro-F1 baselines
    # are famously insensitive to skew in this matched-distribution
    # case -- what they DO react to is a train/test *mismatch* (see
    # test_stratified_baseline_tracks_train_distribution_not_test
    # below), which is the actual anti-leak property this function
    # exists to preserve.
    rng = np.random.default_rng(0)
    train_labels = rng.choice(CLASSES, size=3000, p=[0.05, 0.9, 0.05]).tolist()
    test_labels = rng.choice(CLASSES, size=500, p=[0.05, 0.9, 0.05]).tolist()
    baseline = stratified_random_baseline(train_labels, test_labels, seed=42, n_draws=1000)
    assert baseline == pytest.approx(1 / 3, abs=0.03)


def test_stratified_baseline_tracks_train_distribution_not_test():
    # anti-leak property: the draw distribution comes from train_labels
    # ONLY. Holding train_labels fixed and changing test_labels'
    # distribution must not change which distribution predictions are
    # drawn from -- only the scoring target changes.
    rng = np.random.default_rng(1)
    train_labels = rng.choice(CLASSES, size=2000, p=[0.05, 0.9, 0.05]).tolist()

    test_a = rng.choice(CLASSES, size=400, p=[0.05, 0.9, 0.05]).tolist()  # matches train
    test_b = rng.choice(CLASSES, size=400, p=[0.45, 0.1, 0.45]).tolist()  # very different

    baseline_a = stratified_random_baseline(train_labels, test_a, seed=42, n_draws=2000)
    baseline_b = stratified_random_baseline(train_labels, test_b, seed=42, n_draws=2000)

    # if the baseline leaked the test distribution, both would score
    # near their own matching distribution (both would be "high"); since
    # the draw distribution is fixed by train (skewed to Hold) but test_b
    # is skewed away from Hold, scoring against test_b should be markedly
    # worse than scoring against test_a.
    assert baseline_a > baseline_b + 0.05


def test_stratified_baseline_deterministic_same_seed():
    train_labels = ["Buy", "Hold", "Sell"] * 50
    test_labels = ["Buy", "Hold", "Sell"] * 20
    b1 = stratified_random_baseline(train_labels, test_labels, seed=7, n_draws=500)
    b2 = stratified_random_baseline(train_labels, test_labels, seed=7, n_draws=500)
    assert b1 == b2


# ---------------------------------------------------------------------------
# bootstrap_lift_ci
# ---------------------------------------------------------------------------


def test_bootstrap_lift_ci_brackets_mean_lift():
    per_fold_f1 = [0.5, 0.52, 0.48, 0.51, 0.49, 0.50]
    per_fold_baseline = [0.33, 0.34, 0.33, 0.33, 0.33, 0.34]
    lifts = [f - b for f, b in zip(per_fold_f1, per_fold_baseline)]
    mean_lift = np.mean(lifts)
    lo, hi = bootstrap_lift_ci(per_fold_f1, per_fold_baseline, n_resamples=5000, seed=42)
    assert lo <= mean_lift <= hi


def test_bootstrap_lift_ci_centred_on_zero_contains_zero():
    # fixture: per-fold lifts of [-0.01, 0.01, -0.02, 0.02, 0.0, 0.01]
    per_fold_baseline = [0.33] * 6
    per_fold_f1 = [b + d for b, d in zip(per_fold_baseline, [-0.01, 0.01, -0.02, 0.02, 0.0, 0.01])]
    lo, hi = bootstrap_lift_ci(per_fold_f1, per_fold_baseline, n_resamples=5000, seed=42)
    assert lo <= 0.0 <= hi


def test_bootstrap_lift_ci_centred_well_above_threshold_excludes_zero():
    # fixture: per-fold lifts clustered tightly around 0.15, far above the
    # 0.03 control threshold and with tiny spread -- CI should exclude 0.
    per_fold_baseline = [0.33] * 6
    per_fold_f1 = [b + d for b, d in zip(per_fold_baseline, [0.14, 0.15, 0.16, 0.15, 0.14, 0.16])]
    lo, hi = bootstrap_lift_ci(per_fold_f1, per_fold_baseline, n_resamples=5000, seed=42)
    assert lo > 0.0


def test_bootstrap_lift_ci_deterministic_same_seed():
    per_fold_f1 = [0.5, 0.52, 0.48, 0.51]
    per_fold_baseline = [0.33, 0.34, 0.33, 0.33]
    ci1 = bootstrap_lift_ci(per_fold_f1, per_fold_baseline, n_resamples=2000, seed=99)
    ci2 = bootstrap_lift_ci(per_fold_f1, per_fold_baseline, n_resamples=2000, seed=99)
    assert ci1 == ci2


# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------


def test_verdict_small_lift_ci_overlapping_zero_is_pass():
    assert verdict(lift=0.01, ci_lo=-0.02, ci_hi=0.03, threshold=0.03) == "PASS"


def test_verdict_small_lift_ci_excluding_zero_is_leak():
    # lift itself is under threshold, but the CI does not bracket zero
    # -- the pass condition requires BOTH.
    assert verdict(lift=0.01, ci_lo=0.005, ci_hi=0.02, threshold=0.03) == "LEAK"


def test_verdict_large_lift_ci_overlapping_zero_is_leak():
    assert verdict(lift=0.10, ci_lo=-0.01, ci_hi=0.20, threshold=0.03) == "LEAK"


def test_verdict_large_lift_ci_excluding_zero_is_leak():
    assert verdict(lift=0.15, ci_lo=0.10, ci_hi=0.20, threshold=0.03) == "LEAK"


# ---------------------------------------------------------------------------
# brier_score
# ---------------------------------------------------------------------------


def test_brier_score_perfectly_confident_correct_is_zero():
    y_true = ["Buy", "Hold", "Sell"]
    proba = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    assert brier_score(y_true, proba, classes=CLASSES) == pytest.approx(0.0, abs=1e-12)


def test_brier_score_hand_computed_example():
    # fixture: 2 samples, 3 classes (Buy, Hold, Sell).
    # sample 0: true=Buy,  proba=[0.5, 0.3, 0.2], one-hot=[1,0,0]
    #   sum((1-0.5)^2 + (0-0.3)^2 + (0-0.2)^2) = 0.25 + 0.09 + 0.04 = 0.38
    # sample 1: true=Sell, proba=[0.2, 0.2, 0.6], one-hot=[0,0,1]
    #   sum((0-0.2)^2 + (0-0.2)^2 + (1-0.6)^2) = 0.04 + 0.04 + 0.16 = 0.24
    # mean = (0.38 + 0.24) / 2 = 0.31
    y_true = ["Buy", "Sell"]
    proba = np.array(
        [
            [0.5, 0.3, 0.2],
            [0.2, 0.2, 0.6],
        ]
    )
    expected = (0.38 + 0.24) / 2
    assert brier_score(y_true, proba, classes=CLASSES) == pytest.approx(expected, abs=1e-9)


# ---------------------------------------------------------------------------
# loud failure cases
# ---------------------------------------------------------------------------


def test_macro_f1_raises_on_empty_input():
    with pytest.raises(ValueError):
        macro_f1([], [])


def test_stratified_random_baseline_raises_on_empty_train_labels():
    with pytest.raises(ValueError):
        stratified_random_baseline([], ["Buy", "Hold"], seed=42)


def test_stratified_random_baseline_raises_on_empty_test_labels():
    with pytest.raises(ValueError):
        stratified_random_baseline(["Buy", "Hold"], [], seed=42)


def test_bootstrap_lift_ci_raises_on_length_mismatch():
    with pytest.raises(ValueError):
        bootstrap_lift_ci([0.5, 0.6], [0.3], seed=42)


def test_bootstrap_lift_ci_raises_on_empty_input():
    with pytest.raises(ValueError):
        bootstrap_lift_ci([], [], seed=42)


def test_brier_score_raises_on_rows_not_summing_to_one():
    y_true = ["Buy", "Hold"]
    proba = np.array(
        [
            [0.5, 0.3, 0.1],  # sums to 0.9, not 1.0
            [0.0, 1.0, 0.0],
        ]
    )
    with pytest.raises(ValueError):
        brier_score(y_true, proba, classes=CLASSES)


def test_brier_score_raises_on_empty_input():
    with pytest.raises(ValueError):
        brier_score([], np.empty((0, 3)), classes=CLASSES)


def test_brier_score_raises_on_unknown_label():
    y_true = ["Buy", "Unknown"]
    proba = np.array(
        [
            [0.5, 0.3, 0.2],
            [0.3, 0.3, 0.4],
        ]
    )
    with pytest.raises(ValueError):
        brier_score(y_true, proba, classes=CLASSES)


def test_macro_f1_raises_on_unknown_label():
    with pytest.raises(ValueError):
        macro_f1(["Buy", "NotAClass"], ["Buy", "Hold"])


def test_verdict_distinguishes_below_chance_from_leak():
    """A negative lift whose CI excludes zero is a model performing WORSE
    than a stratified-random guesser -- not evidence of look-ahead. Both
    fail the brief's pass condition, but reporting them under one label
    would misstate the spike's headline result."""
    assert verdict(-0.068, -0.097, -0.035) == "BELOW_CHANCE"
    assert verdict(0.124, 0.110, 0.138) == "LEAK"
    # sign is what separates them; both are equally far from the threshold
    assert verdict(-0.20, -0.30, -0.10) == "BELOW_CHANCE"
    assert verdict(0.20, 0.10, 0.30) == "LEAK"
