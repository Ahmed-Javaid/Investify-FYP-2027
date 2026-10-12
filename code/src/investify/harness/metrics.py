"""Scoring for the five-arm leakage harness (brief section 6).

The harness's whole claim -- that A_CLEAN sits at chance and D_CENTRED
leaks loudly -- rests on these numbers being computed honestly. Two
things this module is deliberately strict about:

1. `stratified_random_baseline` draws its class distribution from the
   TRAINING fold only, never the test fold. Scoring the baseline against
   the test distribution would itself be a leak -- exactly the class of
   mistake this spike exists to catch.
2. `macro_f1` is scored over an explicit, fixed `labels=` list (the
   project's three decision classes) so that a class absent from a
   fold's predictions still enters the macro average as a zero instead
   of silently vanishing and inflating the score.

This module intentionally does not import `splits.py` -- it is pure
scoring over label/probability arrays, independent of how folds were
constructed.
"""
import numpy as np
from sklearn.metrics import f1_score

# The project's three decision classes (brief section 2 / labels.py).
# Fixed and explicit -- never inferred from whatever happens to appear
# in a given fold, since that is exactly what would let a missing class
# silently vanish from a macro average instead of counting as zero.
CLASS_LABELS = ("Buy", "Hold", "Sell")


def _require_nonempty(name: str, *arrays) -> None:
    for arr in arrays:
        if len(arr) == 0:
            raise ValueError(f"{name} received an empty input")


def _require_known_labels(name: str, labels) -> None:
    unknown = sorted(set(labels) - set(CLASS_LABELS))
    if unknown:
        raise ValueError(
            f"{name} received labels outside the known class set "
            f"{CLASS_LABELS}: {unknown}"
        )


def macro_f1(y_true, y_pred) -> float:
    """Unweighted mean of per-class F1 over CLASS_LABELS.

    Uses sklearn's f1_score(average="macro") with an explicit `labels=`
    list so a class absent from this fold's true/predicted labels still
    contributes a 0 to the average rather than being dropped (which
    would silently inflate the score). zero_division=0.
    """
    y_true = list(y_true)
    y_pred = list(y_pred)
    _require_nonempty("macro_f1", y_true, y_pred)
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"macro_f1: y_true and y_pred length mismatch "
            f"({len(y_true)} vs {len(y_pred)})"
        )
    _require_known_labels("macro_f1(y_true)", y_true)
    _require_known_labels("macro_f1(y_pred)", y_pred)
    return float(
        f1_score(y_true, y_pred, labels=list(CLASS_LABELS), average="macro", zero_division=0)
    )


def stratified_random_baseline(
    train_labels,          # labels of the TRAINING fold -- the distribution is drawn from here
    test_labels,           # labels of the test fold -- the baseline is SCORED here
    seed: int = 42,
    n_draws: int = 1000,
) -> float:
    """Expected macro-F1 of a stratified-random guesser.

    Class proportions are computed from `train_labels` ONLY. `n_draws`
    random prediction vectors of length len(test_labels) are drawn from
    that (train) distribution with the given seed, each scored against
    `test_labels` via macro_f1, and the mean returned.

    Deliberately never looks at the test-fold class distribution: doing
    so would itself be a leak of test-set information into the baseline.
    """
    train_labels = list(train_labels)
    test_labels = list(test_labels)
    _require_nonempty("stratified_random_baseline(train_labels)", train_labels)
    _require_nonempty("stratified_random_baseline(test_labels)", test_labels)
    _require_known_labels("stratified_random_baseline(train_labels)", train_labels)
    _require_known_labels("stratified_random_baseline(test_labels)", test_labels)

    counts = np.array([train_labels.count(c) for c in CLASS_LABELS], dtype=float)
    proportions = counts / counts.sum()

    rng = np.random.default_rng(seed)
    n_test = len(test_labels)
    scores = np.empty(n_draws, dtype=float)
    for i in range(n_draws):
        draw = rng.choice(CLASS_LABELS, size=n_test, p=proportions)
        scores[i] = macro_f1(test_labels, draw.tolist())
    return float(scores.mean())


def bootstrap_lift_ci(
    per_fold_f1: list[float],
    per_fold_baseline: list[float],
    n_resamples: int = 10000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Bootstrap confidence interval on mean lift across folds.

    Per-fold lift is per_fold_f1[i] - per_fold_baseline[i]. The per-fold
    lift values are resampled with replacement n_resamples times, the
    mean is taken each time, and the (alpha/2, 1-alpha/2) percentile
    bounds of that bootstrap distribution are returned. Seeded and
    deterministic for a fixed seed.
    """
    per_fold_f1 = list(per_fold_f1)
    per_fold_baseline = list(per_fold_baseline)
    _require_nonempty("bootstrap_lift_ci(per_fold_f1)", per_fold_f1)
    _require_nonempty("bootstrap_lift_ci(per_fold_baseline)", per_fold_baseline)
    if len(per_fold_f1) != len(per_fold_baseline):
        raise ValueError(
            f"bootstrap_lift_ci: per_fold_f1 and per_fold_baseline length "
            f"mismatch ({len(per_fold_f1)} vs {len(per_fold_baseline)})"
        )

    lifts = np.asarray(per_fold_f1, dtype=float) - np.asarray(per_fold_baseline, dtype=float)
    n = len(lifts)

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_resamples, n))
    resample_means = lifts[idx].mean(axis=1)

    lo, hi = np.percentile(resample_means, [100 * (alpha / 2), 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def verdict(lift: float, ci_lo: float, ci_hi: float, threshold: float = 0.03) -> str:
    """Verdict for an arm, in the direction the lift actually points.

    Rule (brief section 6): an arm PASSes only when BOTH hold -- the
    absolute lift is at most `threshold`, AND the bootstrap CI on lift
    overlaps zero (ci_lo <= 0 <= ci_hi). A small lift whose CI still
    excludes zero is a real (if small) effect; a large lift whose CI
    happens to bracket zero is too noisy to accept as a control pass.

    Failing arms are split by DIRECTION, because the two mean opposite
    things and conflating them would misreport the spike's headline
    result:

      LEAK          lift is positive -- the arm scores ABOVE a
                    stratified-random baseline, which for a control is
                    evidence of look-ahead.
      BELOW_CHANCE  lift is negative -- the arm scores BELOW the
                    baseline. That is not leakage; it is a model with no
                    usable signal being confidently wrong out-of-sample
                    (e.g. trained through one regime, tested in another).
                    It still fails the brief's pass condition and must be
                    reported as a failure, not smoothed over.
    """
    lift_ok = abs(lift) <= threshold
    ci_ok = ci_lo <= 0 <= ci_hi
    if lift_ok and ci_ok:
        return "PASS"
    return "LEAK" if lift > 0 else "BELOW_CHANCE"


def brier_score(y_true, proba: np.ndarray, classes) -> float:
    """Multiclass Brier score.

    Mean over samples of the sum of squared differences between the
    one-hot true label and the predicted probability vector. `classes`
    gives the column order of `proba`.
    """
    y_true = list(y_true)
    proba = np.asarray(proba, dtype=float)
    classes = list(classes)

    _require_nonempty("brier_score(y_true)", y_true)
    if proba.ndim != 2 or proba.shape[0] == 0:
        raise ValueError("brier_score: proba must be a non-empty 2D array")
    if len(y_true) != proba.shape[0]:
        raise ValueError(
            f"brier_score: y_true and proba row count mismatch "
            f"({len(y_true)} vs {proba.shape[0]})"
        )
    if proba.shape[1] != len(classes):
        raise ValueError(
            f"brier_score: proba has {proba.shape[1]} columns but "
            f"{len(classes)} classes were given"
        )
    _require_known_labels("brier_score(y_true)", y_true)

    unknown_classes = sorted(set(classes) - set(CLASS_LABELS))
    if unknown_classes:
        raise ValueError(
            f"brier_score: classes contains labels outside the known "
            f"class set {CLASS_LABELS}: {unknown_classes}"
        )

    row_sums = proba.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=1e-6):
        bad = np.where(~np.isclose(row_sums, 1.0, atol=1e-6))[0]
        raise ValueError(
            f"brier_score: proba rows must sum to ~1; rows {bad.tolist()} do not "
            f"(sums={row_sums[bad].tolist()})"
        )

    class_index = {c: i for i, c in enumerate(classes)}
    one_hot = np.zeros_like(proba)
    for row, label in enumerate(y_true):
        one_hot[row, class_index[label]] = 1.0

    return float(np.sum((one_hot - proba) ** 2, axis=1).mean())
