"""Fold-local normalisation: every scaler is fit on the training fold
only, never on the full series and never touching test rows. brief
section 5 / tests/test_fold_local_scaling.py: scaler parameters must
differ across folds and must never be derived from test rows.
"""
import pandas as pd
from sklearn.preprocessing import StandardScaler


def fit_scaler(train_df: pd.DataFrame, feature_cols: list[str]) -> StandardScaler:
    scaler = StandardScaler()
    scaler.fit(train_df[feature_cols])
    return scaler


def apply_scaler(df: pd.DataFrame, feature_cols: list[str], scaler: StandardScaler) -> pd.DataFrame:
    out = df.copy()
    out[feature_cols] = scaler.transform(df[feature_cols])
    return out
