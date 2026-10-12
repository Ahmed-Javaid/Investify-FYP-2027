"""The five experimental arms (brief section 6).

Everything is held constant across arms except temporal discipline:
identical feature list, identical XGBoost configuration, identical seed,
and -- critically -- an identical ROW SET. The row set is pinned to the
clean arm (bars with all five technical indicators and a label present)
and reused verbatim by every other arm, so that an arm which re-maps
text to different sessions cannot quietly train on a different sample
than the control and make itself look better or worse for that reason.

Missing sentiment (303 bars, the March-2021 sparse patch found in Phase
0 plus the corpus tail) is passed to XGBoost's native missing-value
handling rather than dropped, for the same reason: dropping would give
each arm a different row set.

Arms:
  A_CLEAN         nothing changed. Must sit at chance.
  B_SHUFFLED      shuffled K-fold instead of expanding walk-forward.
  C_NOPURGE       walk-forward retained, purge and embargo removed.
  D_CENTRED       bollinger_pos recomputed with a centred window (the canary).
  D_CENTRED_SMA200 dist_sma200 centred -- reported alongside as evidence that
                  leak magnitude depends on window/horizon overlap.
  E_SAMEBAR_TEXT  text mapped to the session it published in, not the next.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from investify.calendars import NYSECalendar
from investify.features.assembly import (
    add_backward_only_momentum,
    aggregate_session_sentiment,
    asof_join_features,
)
from investify.features.indicators import (
    bollinger_position_centred,
    compute_indicators,
    dist_from_sma200_centred,
)
from investify.features.sentiment import doc_hash
from investify.harness.metrics import (
    CLASS_LABELS,
    bootstrap_lift_ci,
    macro_f1,
    stratified_random_baseline,
    verdict,
)
from investify.harness.splits import Fold, expanding_purged_walk_forward, shuffled_kfold
from investify.ingest.news import (
    load_alpaca_ticker_news,
    map_to_sessions,
    map_to_sessions_samebar,
)
from investify.labels import compute_labels
from investify.scaling import apply_scaler, fit_scaler

CLASS_TO_INT = {label: i for i, label in enumerate(CLASS_LABELS)}
INT_TO_CLASS = {i: label for label, i in CLASS_TO_INT.items()}


@dataclass(frozen=True)
class ArmSpec:
    name: str
    centred_indicator: str | None  # None | "bollinger_pos" | "dist_sma200"
    samebar_text: bool
    splitter: str  # "purged" | "shuffled" | "nopurge"
    changes: str


ARMS: dict[str, ArmSpec] = {
    "A_CLEAN": ArmSpec(
        "A_CLEAN", None, False, "purged",
        "Nothing. Correct throughout.",
    ),
    "B_SHUFFLED": ArmSpec(
        "B_SHUFFLED", None, False, "shuffled",
        "Shuffled K-fold instead of expanding walk-forward.",
    ),
    "C_NOPURGE": ArmSpec(
        "C_NOPURGE", None, False, "nopurge",
        "Purge and embargo removed, walk-forward retained.",
    ),
    "D_CENTRED": ArmSpec(
        "D_CENTRED", "bollinger_pos", False, "purged",
        "bollinger_pos computed with a centred rather than trailing window.",
    ),
    "D_CENTRED_SMA200": ArmSpec(
        "D_CENTRED_SMA200", "dist_sma200", False, "purged",
        "dist_sma200 centred instead of trailing (window does not overlap the horizon).",
    ),
    "E_SAMEBAR_TEXT": ArmSpec(
        "E_SAMEBAR_TEXT", None, True, "purged",
        "Text mapped to the same session it published in, not the next.",
    ),
}


# --------------------------------------------------------------------------
# inputs: read from the append-only store and the FinBERT cache, never the
# network. A missing input is an error, never a silently-skipped row.
# --------------------------------------------------------------------------

def load_prices(cfg: dict) -> pd.DataFrame:
    ticker = cfg["tickers"][0]
    path = Path(cfg["paths"]["store"]) / "prices" / f"ticker={ticker}"
    if not path.exists():
        raise FileNotFoundError(f"price store missing at {path}; run scripts/build_phase1_feature_matrix.py first")
    df = pd.read_parquet(path).sort_values("date").reset_index(drop=True)
    df["ticker"] = ticker
    return df.drop(columns=["content_hash", "ingest_ts"], errors="ignore")


def load_news(cfg: dict, corpus: str | None = None) -> pd.DataFrame:
    """Headlines for the chosen corpus, with `session` deliberately absent --
    every arm re-derives it from `event_ts` under its own mapping rule.

    Defaults to the corpus named by `default_corpus` (FNSPID), so the
    committed Phase 2 results and every existing test are unaffected.
    """
    ticker = cfg["tickers"][0]
    corpus = corpus or cfg.get("default_corpus", "fnspid")
    spec = cfg["corpora"][corpus]

    if spec["loader"] == "fnspid":
        path = Path(cfg["paths"]["store"]) / "news" / f"ticker={ticker}"
        if not path.exists():
            raise FileNotFoundError(
                f"news store missing at {path}; run scripts/build_phase1_feature_matrix.py first"
            )
        df = pd.read_parquet(path)
        df["ticker"] = ticker
        return df.drop(columns=["session", "content_hash", "ingest_ts"], errors="ignore")

    if spec["loader"] == "alpaca":
        return load_alpaca_ticker_news(
            spec["path"],
            ticker,
            start=cfg["date_range"]["start"],
            end=cfg["date_range"]["end"],
        )

    raise ValueError(f"unknown loader {spec['loader']!r} for corpus {corpus!r}")


def attach_cached_sentiment(news_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Attach FinBERT polarity from the on-disk cache keyed by document
    hash. The model is never loaded here -- the arms re-aggregate the
    same scores under different session mappings, so re-scoring would be
    both slow and pointless. A headline with no cached score is a hard
    error, not a row to drop."""
    cache_path = Path(cfg["sentiment"]["cache_dir"]) / "finbert_scores.parquet"
    if not cache_path.exists():
        raise FileNotFoundError(f"FinBERT score cache missing at {cache_path}")
    cache = pd.read_parquet(cache_path)[["doc_hash", "polarity"]]

    df = news_df.copy()
    df["doc_hash"] = df["headline"].apply(doc_hash)
    merged = df.merge(cache, on="doc_hash", how="left")
    n_missing = merged["polarity"].isna().sum()
    if n_missing:
        raise ValueError(
            f"{n_missing} headlines have no cached FinBERT score. Re-run the Phase 1 "
            f"scoring pass; the arms must not silently drop unscored text."
        )
    return merged


# --------------------------------------------------------------------------
# per-arm feature matrices
# --------------------------------------------------------------------------

def build_arm_matrix(
    spec: ArmSpec,
    prices: pd.DataFrame,
    scored_news: pd.DataFrame,
    cfg: dict,
    calendar: NYSECalendar,
) -> pd.DataFrame:
    """Rebuild the feature matrix under this arm's feature variants. The
    splitter is NOT applied here -- arms that differ only in splitting
    produce an identical matrix."""
    mapper = map_to_sessions_samebar if spec.samebar_text else map_to_sessions
    news = mapper(scored_news, calendar)

    session_sentiment = aggregate_session_sentiment(news)
    session_sentiment = add_backward_only_momentum(session_sentiment)

    indicators = compute_indicators(prices)
    if spec.centred_indicator == "bollinger_pos":
        # deliberate feature-level look-ahead: the leak canary
        indicators["bollinger_pos"] = bollinger_position_centred(prices["close"]).values
    elif spec.centred_indicator == "dist_sma200":
        indicators["dist_sma200"] = dist_from_sma200_centred(
            prices["close"], period=cfg["technical_indicators"]["sma_period"]
        ).values
    elif spec.centred_indicator is not None:
        raise ValueError(f"unknown centred_indicator {spec.centred_indicator!r} for arm {spec.name}")

    priced = pd.concat(
        [prices.reset_index(drop=True), indicators.reset_index(drop=True)], axis=1
    )
    joined = asof_join_features(
        priced, session_sentiment, max_lookback_days=cfg["as_of_join"]["max_lookback_days"]
    )

    for horizon in cfg["labels"]["horizons_days"]:
        labels = compute_labels(
            joined[["date", "close"]],
            horizon_days=horizon,
            vol_window_days=cfg["labels"]["volatility_window_days"],
            thresholds=tuple(cfg["labels"]["class_thresholds"]),
        )
        joined[f"label_{horizon}d"] = labels["label"].values

    return joined.sort_values("date").reset_index(drop=True)


def clean_row_mask(clean_matrix: pd.DataFrame, horizon: int, cfg: dict) -> np.ndarray:
    """The row set every arm shares, derived once from the CLEAN arm:
    bars with all five technical indicators present and a label at this
    horizon. Sentiment NaNs are deliberately kept (XGBoost handles them
    natively) so that re-mapping text cannot change which rows an arm
    trains on."""
    technical = cfg["features"]["technical"]
    mask = clean_matrix[technical].notna().all(axis=1) & clean_matrix[f"label_{horizon}d"].notna()
    return mask.values


# --------------------------------------------------------------------------
# folds and fitting
# --------------------------------------------------------------------------

def make_folds(spec: ArmSpec, dates: pd.Series, cfg: dict, horizon: int) -> list[Fold]:
    n_folds = cfg["splits"]["n_folds"]
    if spec.splitter == "shuffled":
        return shuffled_kfold(n_rows=len(dates), n_folds=n_folds, seed=cfg["seed"])
    if spec.splitter == "nopurge":
        return expanding_purged_walk_forward(
            dates, n_folds=n_folds, embargo_days=0, horizon_days=horizon, purge=False
        )
    if spec.splitter == "purged":
        return expanding_purged_walk_forward(
            dates,
            n_folds=n_folds,
            embargo_days=cfg["splits"]["embargo_days"],
            horizon_days=horizon,
            purge=True,
        )
    raise ValueError(f"unknown splitter {spec.splitter!r} for arm {spec.name}")


def fit_predict_fold(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_cols: list[str],
    label_col: str,
    cfg: dict,
) -> tuple[np.ndarray, np.ndarray]:
    """Fold-local scaling, then the one fixed XGBoost config. Returns
    (y_true, y_pred) as Buy/Hold/Sell strings."""
    scaler = fit_scaler(train, feature_cols)
    train_s = apply_scaler(train, feature_cols, scaler)
    test_s = apply_scaler(test, feature_cols, scaler)

    y_train = train[label_col].astype(str).map(CLASS_TO_INT).values
    y_test = test[label_col].astype(str).values
    if np.isnan(y_train.astype(float)).any():
        raise ValueError(f"unmapped label value in training fold for {label_col}")

    sample_weight = compute_sample_weight("balanced", y_train)
    model = XGBClassifier(**cfg["xgboost"])
    model.fit(train_s[feature_cols], y_train, sample_weight=sample_weight)

    y_pred_int = model.predict(test_s[feature_cols])
    y_pred = np.array([INT_TO_CLASS[int(i)] for i in y_pred_int])
    return y_test, y_pred


def run_arm(
    spec: ArmSpec,
    matrix: pd.DataFrame,
    row_mask: np.ndarray,
    horizon: int,
    cfg: dict,
) -> dict:
    """Run one arm at one horizon over the shared row set. Returns the
    result row that goes into results.json / results.csv."""
    feature_cols = cfg["features"]["technical"] + cfg["features"]["sentiment"]
    label_col = f"label_{horizon}d"

    df = matrix.loc[row_mask].reset_index(drop=True)
    if df[label_col].isna().any():
        raise ValueError(
            f"{spec.name} h={horizon}d: shared row set contains rows with no label. "
            f"The mask is built from the clean arm and must hold for every arm."
        )

    folds = make_folds(spec, df["date"], cfg, horizon)

    per_fold_f1: list[float] = []
    per_fold_baseline: list[float] = []
    for fold in folds:
        train = df.iloc[fold.train_idx]
        test = df.iloc[fold.test_idx]
        y_true, y_pred = fit_predict_fold(train, test, feature_cols, label_col, cfg)
        per_fold_f1.append(macro_f1(y_true, y_pred))
        per_fold_baseline.append(
            stratified_random_baseline(
                train[label_col].astype(str).values, y_true, seed=cfg["seed"]
            )
        )

    mean_f1 = float(np.mean(per_fold_f1))
    sd_f1 = float(np.std(per_fold_f1, ddof=1))
    chance = float(np.mean(per_fold_baseline))
    lift = mean_f1 - chance
    ci_lo, ci_hi = bootstrap_lift_ci(
        per_fold_f1,
        per_fold_baseline,
        n_resamples=cfg["leakage_control"]["bootstrap_resamples"],
        seed=cfg["seed"],
    )
    threshold = cfg["leakage_control"]["pass_threshold_abs_lift"]

    return {
        "arm": spec.name,
        "horizon_days": horizon,
        "changes": spec.changes,
        "n_rows": int(len(df)),
        "n_folds": len(folds),
        "macro_f1": mean_f1,
        "macro_f1_sd": sd_f1,
        "chance": chance,
        "lift": lift,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "threshold": threshold,
        "verdict": verdict(lift, ci_lo, ci_hi, threshold=threshold),
        "per_fold_f1": [float(x) for x in per_fold_f1],
        "per_fold_baseline": [float(x) for x in per_fold_baseline],
    }


def build_all_matrices(cfg: dict, corpus: str | None = None) -> dict[str, pd.DataFrame]:
    """Build every arm's feature matrix once. Arms that differ only in
    splitting share one matrix object."""
    calendar = NYSECalendar()
    prices = load_prices(cfg)
    scored_news = attach_cached_sentiment(load_news(cfg, corpus=corpus), cfg)

    matrices: dict[str, pd.DataFrame] = {}
    by_variant: dict[tuple[bool, bool], pd.DataFrame] = {}
    for name, spec in ARMS.items():
        key = (spec.centred_indicator, spec.samebar_text)
        if key not in by_variant:
            by_variant[key] = build_arm_matrix(spec, prices, scored_news, cfg, calendar)
        matrices[name] = by_variant[key]
    return matrices


def run_all_arms(cfg: dict, corpus: str | None = None) -> list[dict]:
    """Every arm at both horizons, over one shared row set per horizon."""
    matrices = build_all_matrices(cfg, corpus=corpus)
    clean = matrices["A_CLEAN"]

    results: list[dict] = []
    for horizon in cfg["labels"]["horizons_days"]:
        row_mask = clean_row_mask(clean, horizon, cfg)
        for name, spec in ARMS.items():
            row = run_arm(spec, matrices[name], row_mask, horizon, cfg)
            row["corpus"] = corpus or cfg.get("default_corpus", "fnspid")
            results.append(row)
    return results
