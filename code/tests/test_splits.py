"""tests/test_splits.py -- brief section 6: the five-arm leakage harness
depends on these splitters being correct in both directions. A_CLEAN and
C_NOPURGE need expanding_purged_walk_forward to genuinely separate train
from test in time (and to genuinely stop separating them when purge is
switched off); B_SHUFFLED needs shuffled_kfold to genuinely break
temporal order, since that is the leak it exists to demonstrate.

All dates below are synthetic fixtures (a daily calendar, not a real
trading calendar) chosen so that "row index" and "calendar day offset"
coincide 1:1, which makes the purge/embargo day-math easy to check by
hand. No real data is needed for this module.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.harness.splits import (  # noqa: E402
    Fold,
    expanding_purged_walk_forward,
    shuffled_kfold,
)


def make_dates(n=140, start="2020-01-01"):
    """Fixture: one calendar day per row, so date offset == row offset."""
    return pd.Series(pd.date_range(start, periods=n, freq="D"))


# ---------------------------------------------------------------------
# expanding_purged_walk_forward
# ---------------------------------------------------------------------


def test_no_temporal_overlap_between_train_and_test():
    dates = make_dates()
    folds = expanding_purged_walk_forward(dates, n_folds=6, embargo_days=5, horizon_days=5, label_end_dates=dates.shift(-5))

    assert len(folds) == 6
    for fold in folds:
        train_dates = dates.iloc[fold.train_idx]
        test_dates = dates.iloc[fold.test_idx]
        assert train_dates.max() < test_dates.min(), (
            f"fold {fold.fold_id}: train/test overlap in time"
        )


def test_expanding_not_sliding():
    """Expanding property, stated precisely for this implementation: fold
    k's raw (pre-purge) train candidate is every row before its test
    block, so it is monotonically growing with k. Because the purge/
    embargo cutoff date for fold k is itself non-decreasing in k (later
    test blocks start later), any row that survived fold (k-1)'s purge
    also survives fold k's purge. So the *actual* (post-purge) train_idx
    sets are strictly nested: train_idx(fold k-1) is a subset of
    train_idx(fold k) for every k. That is what we assert -- a stronger,
    more precise statement than "size is non-decreasing", and it implies
    that statement too.
    """
    dates = make_dates()
    folds = expanding_purged_walk_forward(dates, n_folds=6, embargo_days=5, horizon_days=5, label_end_dates=dates.shift(-5))

    sizes = [len(f.train_idx) for f in folds]
    assert sizes == sorted(sizes), "train size must be non-decreasing across folds"
    assert len(set(sizes)) > 1, "sanity check: sizes should actually vary, not all be equal"

    for prev, cur in zip(folds, folds[1:]):
        assert set(prev.train_idx.tolist()).issubset(set(cur.train_idx.tolist())), (
            f"fold {prev.fold_id}'s train rows are not a subset of fold {cur.fold_id}'s "
            "-- training set is not expanding"
        )


def test_purge_and_embargo_remove_rows():
    dates = make_dates()

    purged_folds = expanding_purged_walk_forward(
        dates, n_folds=6, embargo_days=5, horizon_days=5, purge=True, label_end_dates=dates.shift(-5)
    )
    nopurge_folds = expanding_purged_walk_forward(
        dates, n_folds=6, embargo_days=0, horizon_days=5, purge=False
    )

    for purged, raw in zip(purged_folds, nopurge_folds):
        assert purged.fold_id == raw.fold_id
        assert len(purged.train_idx) < len(raw.train_idx), (
            f"fold {purged.fold_id}: purge+embargo did not remove any train rows"
        )

        gap_days = (dates.iloc[purged.test_idx].min() - dates.iloc[purged.train_idx].max()).days
        assert gap_days >= max(5, 5), (
            f"fold {purged.fold_id}: gap between train and test is only {gap_days} days, "
            "expected at least max(embargo_days, horizon_days)"
        )


def test_nopurge_matches_raw_walk_forward():
    """purge=False, embargo_days=0 must keep every row strictly before the
    test block -- the raw split C_NOPURGE relies on."""
    dates = make_dates()
    folds = expanding_purged_walk_forward(dates, n_folds=6, embargo_days=0, horizon_days=5, purge=False)

    for fold in folds:
        expected_train = np.arange(0, fold.test_idx.min())
        assert np.array_equal(fold.train_idx, expected_train), (
            f"fold {fold.fold_id}: purge=False, embargo_days=0 should keep every prior row"
        )


def test_blocks_tile_the_tail_without_overlap():
    dates = make_dates()
    folds = expanding_purged_walk_forward(dates, n_folds=6, embargo_days=5, horizon_days=5, label_end_dates=dates.shift(-5))

    all_test_idx = np.concatenate([f.test_idx for f in folds])
    assert len(all_test_idx) == len(set(all_test_idx.tolist())), "test blocks overlap"

    # contiguous: sorted union of test blocks is one unbroken run of positions
    sorted_idx = np.sort(all_test_idx)
    assert np.array_equal(sorted_idx, np.arange(sorted_idx.min(), sorted_idx.max() + 1)), (
        "test blocks do not tile a contiguous tail of the sample"
    )
    # each block itself is internally contiguous and chronologically ordered
    for fold in folds:
        assert np.array_equal(fold.test_idx, np.arange(fold.test_idx.min(), fold.test_idx.max() + 1))
    # blocks appear in increasing chronological order fold 0 -> fold 5
    starts = [f.test_idx.min() for f in folds]
    assert starts == sorted(starts)


# ---------------------------------------------------------------------
# shuffled_kfold
# ---------------------------------------------------------------------


def test_shuffled_kfold_is_deterministic():
    folds_a = shuffled_kfold(n_rows=140, n_folds=6, seed=42)
    folds_b = shuffled_kfold(n_rows=140, n_folds=6, seed=42)

    assert len(folds_a) == len(folds_b) == 6
    for a, b in zip(folds_a, folds_b):
        assert np.array_equal(a.train_idx, b.train_idx)
        assert np.array_equal(a.test_idx, b.test_idx)


def test_shuffled_kfold_breaks_temporal_order():
    """This is the point of B_SHUFFLED: unlike the walk-forward splitter,
    train and test dates must interleave rather than test always sitting
    after train."""
    dates = make_dates()
    folds = shuffled_kfold(n_rows=len(dates), n_folds=6, seed=42)

    interleaved = False
    for fold in folds:
        train_dates = dates.iloc[fold.train_idx]
        test_dates = dates.iloc[fold.test_idx]
        if train_dates.max() > test_dates.min():
            interleaved = True
            break
    assert interleaved, "shuffled_kfold produced a temporally-ordered split -- seed/shuffle broken"


def test_shuffled_kfold_partitions_all_rows():
    folds = shuffled_kfold(n_rows=140, n_folds=6, seed=42)
    all_test_idx = np.concatenate([f.test_idx for f in folds])
    assert np.array_equal(np.sort(all_test_idx), np.arange(140)), (
        "shuffled_kfold test folds should partition every row exactly once"
    )


# ---------------------------------------------------------------------
# loud failure
# ---------------------------------------------------------------------


def test_unsorted_dates_raise():
    dates = make_dates()
    shuffled = dates.sample(frac=1.0, random_state=1).reset_index(drop=True)
    with pytest.raises(ValueError):
        expanding_purged_walk_forward(shuffled, n_folds=6, embargo_days=5, horizon_days=5, label_end_dates=dates.shift(-5))


def test_n_folds_below_two_raises():
    dates = make_dates()
    with pytest.raises(ValueError):
        expanding_purged_walk_forward(dates, n_folds=1, embargo_days=5, horizon_days=5, label_end_dates=dates.shift(-5))
    with pytest.raises(ValueError):
        shuffled_kfold(n_rows=140, n_folds=1, seed=42)


def test_too_many_folds_for_too_few_rows_raises():
    dates = make_dates(n=5)
    with pytest.raises(ValueError):
        expanding_purged_walk_forward(dates, n_folds=6, embargo_days=5, horizon_days=5, label_end_dates=dates.shift(-5))


def test_fold_is_frozen_dataclass():
    fold = Fold(fold_id=0, train_idx=np.array([0, 1]), test_idx=np.array([2, 3]))
    with pytest.raises(Exception):
        fold.fold_id = 1  # frozen -- must not be mutable
