"""Cross-validation split generators for the five-arm leakage harness
(brief section 6). Index-based over a date-sorted feature frame: these
functions never see features or labels, only the date column and a
config, and hand back positional indices for the caller to slice with.

Two splitters:

- expanding_purged_walk_forward: the correct splitter. A_CLEAN, D_CENTRED
  and E_SAMEBAR_TEXT run on this with purge=True; C_NOPURGE runs on this
  with purge=False, embargo_days=0 to show what happens when temporal
  discipline is removed but the walk-forward structure is kept.
- shuffled_kfold: the deliberately-wrong splitter B_SHUFFLED uses, to
  demonstrate the overlapping-label leak that ordinary shuffled K-fold
  causes on time series.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold


@dataclass(frozen=True)
class Fold:
    fold_id: int
    train_idx: np.ndarray  # positional indices into the date-sorted frame
    test_idx: np.ndarray


def expanding_purged_walk_forward(
    dates: pd.Series,
    n_folds: int = 6,
    embargo_days: int = 5,
    horizon_days: int = 5,
    purge: bool = True,
) -> list[Fold]:
    if n_folds < 2:
        raise ValueError(f"n_folds must be >= 2, got {n_folds}")
    if not dates.is_monotonic_increasing:
        raise ValueError("dates must be sorted ascending")

    dates = pd.Series(pd.to_datetime(dates.to_numpy())).reset_index(drop=True)
    n_rows = len(dates)

    # Split the full row range into n_folds + 1 contiguous segments: the
    # first is a train-only warm-up period, the remaining n_folds are the
    # chronologically-ordered, non-overlapping test blocks that "cover
    # the back portion of the sample". Fold k trains on every row before
    # its test block (expanding), never on a sliding window.
    segments = np.array_split(np.arange(n_rows), n_folds + 1)
    test_blocks = segments[1:]

    folds = []
    for fold_id, test_idx in enumerate(test_blocks):
        if test_idx.size == 0:
            raise ValueError(
                f"fold {fold_id}: empty test block -- too many folds ({n_folds}) "
                f"for too few rows ({n_rows})"
            )

        test_start_date = dates.iloc[test_idx[0]]
        train_candidate_idx = np.arange(0, test_idx[0])
        if train_candidate_idx.size == 0:
            raise ValueError(
                f"fold {fold_id}: empty train side -- test block starts at row 0"
            )

        train_dates = dates.iloc[train_candidate_idx]
        drop_mask = np.zeros(len(train_candidate_idx), dtype=bool)

        if purge:
            purge_cutoff = test_start_date - pd.Timedelta(days=horizon_days)
            drop_mask |= (train_dates > purge_cutoff).to_numpy()

        embargo_cutoff = test_start_date - pd.Timedelta(days=embargo_days)
        drop_mask |= (train_dates > embargo_cutoff).to_numpy()

        train_idx = train_candidate_idx[~drop_mask]
        if train_idx.size == 0:
            raise ValueError(
                f"fold {fold_id}: purge/embargo removed the entire train side "
                f"(embargo_days={embargo_days}, horizon_days={horizon_days}, purge={purge})"
            )

        folds.append(Fold(fold_id=fold_id, train_idx=train_idx, test_idx=test_idx))

    return folds


def shuffled_kfold(
    n_rows: int,
    n_folds: int = 6,
    seed: int = 42,
) -> list[Fold]:
    if n_folds < 2:
        raise ValueError(f"n_folds must be >= 2, got {n_folds}")

    kf = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    folds = []
    for fold_id, (train_idx, test_idx) in enumerate(kf.split(np.arange(n_rows))):
        if train_idx.size == 0 or test_idx.size == 0:
            raise ValueError(f"fold {fold_id}: empty train or test side")
        folds.append(Fold(fold_id=fold_id, train_idx=train_idx, test_idx=test_idx))

    return folds
