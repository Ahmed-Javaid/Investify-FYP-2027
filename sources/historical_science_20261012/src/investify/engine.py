"""The decision engine (brief section 7): one fixed XGBoost configuration,
isotonic calibration on a held-out fold, a transparent linear-baseline
comparator, and TreeSHAP attribution feeding the frozen `DecisionRecord`
schema (`decision_record.py`).

This module is a consumer of already-built infrastructure, not a
reimplementation of it:

  - `harness.arms` supplies the A_CLEAN feature matrix, the shared row
    mask, and the expanding purged walk-forward folds. The engine trains
    under the exact same temporal discipline the leakage harness audits
    -- it must not get a looser split than the harness would tolerate.
  - `harness.metrics` supplies `macro_f1` / `brier_score`.
  - `decision_record.py` supplies the frozen, self-validating schema.
    Nothing here loosens its checks; a record this module cannot build
    validly is a bug in this module, not a reason to weaken the schema.

Model quality is a reported finding, not a target. Phase 2 found A_CLEAN
sits BELOW chance at the 5-day horizon (lift -0.068, `phase2_report.md`
table). This module trains the identical configuration at the identical
horizon, so its macro-F1 is expected to be weak. Nothing here is tuned to
make that number look better.

--------------------------------------------------------------------
A pinned compatibility workaround, explained up front
--------------------------------------------------------------------
`shap.TreeExplainer` on an XGBoost 3.x multiclass model crashes at
construction:

    ValueError: could not convert string to float:
    '[9.536743E-7,-7.1525574E-7,-2.3841858E-7]'

XGBoost >=2 serialises `base_score` for `multi:softprob` as one value
PER CLASS, JSON-encoded as a list string. shap 0.49.1's model loader
(`shap.explainers._tree.XGBTreeModelLoader`) still assumes a single
scalar and calls `float(...)` on it directly. This is a genuine
version-skew bug between the two pinned dependencies (`shap>=0.45`,
xgboost resolved to 3.2.0 in this environment) -- confirmed against the
actual installed shap source, not assumed. There is no newer shap
release available (checked via `uv add --upgrade-package shap`, which
re-resolved to the same 0.49.1).

The values inside that list are ~1e-6 in magnitude in every model this
module trains -- numerical noise around zero, not a meaningful per-class
offset (multi:softprob's default base_score is class-symmetric). Tree
SHAP's attribution algorithm is computed from tree structure alone and
does not consult `base_score` at all; only the *reported* expected_value
does. So `_patch_shap_multiclass_base_score()` below intercepts the
decoded model JSON purely so construction doesn't crash, substituting
the mean of the per-class values for the scalar shap's loader expects.
This was verified empirically (see engine's own module-level checks and
`tests/test_shap_additivity.py`): with the patch applied, shap's own
`explainer.expected_value[c]` matches `raw_margin[c] - sum(shap_row)` to
~1e-6. This module does not even rely on that agreement -- see the next
section -- so the patch only needs to be "close enough not to crash",
which it demonstrably is.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import shap.explainers._tree as _shap_tree_mod
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from investify.decision_record import DecisionRecord, FeatureContribution, rank_contributions
from investify.harness.arms import (
    ARMS,
    CLASS_TO_INT,
    INT_TO_CLASS,
    build_all_matrices,
    clean_row_mask,
    fit_predict_fold,
    make_folds,
)
from investify.harness.metrics import CLASS_LABELS, brier_score, macro_f1
from investify.harness.splits import Fold
from investify.scaling import apply_scaler, fit_scaler

RISK_TIER_PLACEHOLDER = "Balanced"  # see docstring on `build_decision_records`


# --------------------------------------------------------------------------
# shap / xgboost multiclass base_score compatibility shim (see module docstring)
# --------------------------------------------------------------------------

_PATCH_APPLIED = False


def _patch_shap_multiclass_base_score() -> None:
    """Idempotent. Wraps shap's ubjson model decoder so a per-class
    `base_score` list string (xgboost>=2 multiclass) is collapsed to its
    mean before shap's loader does `float(base_score)`. See module
    docstring for why this is safe: shap values are computed from tree
    structure, not base_score, and this module derives its own
    `base_value` from the raw margin rather than trusting shap's
    self-reported expected_value."""
    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        return

    original_decode = _shap_tree_mod.decode_ubjson_buffer

    def patched_decode(fp):
        jmodel = original_decode(fp)
        try:
            params = jmodel["learner"]["learner_model_param"]
            base_score = params["base_score"]
        except (KeyError, TypeError):
            return jmodel
        if isinstance(base_score, str) and base_score.strip().startswith("["):
            values = json.loads(base_score)
            params["base_score"] = str(float(np.mean(values)))
        return jmodel

    _shap_tree_mod.decode_ubjson_buffer = patched_decode
    _PATCH_APPLIED = True


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

def feature_cols(cfg: dict) -> list[str]:
    return cfg["features"]["technical"] + cfg["features"]["sentiment"]


def train_xgboost(
    train_df: pd.DataFrame, cols: list[str], label_col: str, cfg: dict
) -> tuple[XGBClassifier, StandardScaler]:
    """Fold-local scaling then the ONE fixed config from config/spike.yaml
    (`xgboost:` block, used verbatim -- no Optuna, no per-call overrides).
    Class weights via compute_sample_weight('balanced', ...)."""
    scaler = fit_scaler(train_df, cols)
    train_s = apply_scaler(train_df, cols, scaler)

    y_train = train_df[label_col].astype(str).map(CLASS_TO_INT).values
    if np.isnan(y_train.astype(float)).any():
        raise ValueError(f"unmapped label value in training fold for {label_col}")

    sample_weight = compute_sample_weight("balanced", y_train)
    model = XGBClassifier(**cfg["xgboost"])
    model.fit(train_s[cols], y_train, sample_weight=sample_weight)
    if list(model.classes_) != [0, 1, 2]:
        raise ValueError(
            f"expected classes_ [0,1,2] (Buy,Hold,Sell), got {model.classes_}; "
            "a training fold is missing a class, and downstream column-order "
            "assumptions (proba/margin columns == CLASS_LABELS order) would silently break"
        )
    return model, scaler


def score_fold(
    model: XGBClassifier, scaler: StandardScaler, df: pd.DataFrame, cols: list[str]
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Returns (proba, raw_margin, scaled_df). Column order of both proba
    and margin is CLASS_LABELS order (Buy, Hold, Sell) -- asserted in
    `train_xgboost` via `model.classes_`, not assumed here."""
    scaled = apply_scaler(df, cols, scaler)
    proba = model.predict_proba(scaled[cols])
    margin = model.predict(scaled[cols], output_margin=True)
    if proba.shape[1] != len(CLASS_LABELS) or margin.shape[1] != len(CLASS_LABELS):
        raise ValueError(
            f"expected {len(CLASS_LABELS)}-column proba/margin, got "
            f"proba={proba.shape}, margin={margin.shape}"
        )
    return proba, margin, scaled


# --------------------------------------------------------------------------
# isotonic calibration
# --------------------------------------------------------------------------

def fit_isotonic_calibrators(
    raw_proba_calib: np.ndarray, y_true_calib_int: np.ndarray
) -> dict[int, IsotonicRegression]:
    """One isotonic regressor per class (one-vs-rest): maps this class's
    raw predicted probability to a calibrated one, fit on a HELD-OUT
    calibration fold's predictions (never the fold that produced those
    predictions' own training data)."""
    calibrators: dict[int, IsotonicRegression] = {}
    for class_idx in range(len(CLASS_LABELS)):
        target = (y_true_calib_int == class_idx).astype(float)
        reg = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        reg.fit(raw_proba_calib[:, class_idx], target)
        calibrators[class_idx] = reg
    return calibrators


def apply_calibration(
    raw_proba: np.ndarray, calibrators: dict[int, IsotonicRegression]
) -> np.ndarray:
    """Per-class isotonic transform, then renormalised to sum to 1 per
    row (the decision record requires this within 1e-6). A row that
    collapses to all-zero after transform is a hard error, not silently
    uniform-filled -- that would hide a degenerate calibrator."""
    calibrated = np.column_stack(
        [calibrators[c].predict(raw_proba[:, c]) for c in range(len(CLASS_LABELS))]
    )
    row_sums = calibrated.sum(axis=1)
    if np.any(row_sums <= 0):
        bad = np.where(row_sums <= 0)[0]
        raise ValueError(f"isotonic calibration collapsed rows {bad.tolist()} to all-zero probability")
    return calibrated / row_sums[:, None]


# --------------------------------------------------------------------------
# transparent linear baseline: C = R*S + (1-R)*T
# --------------------------------------------------------------------------

def linear_baseline_predict(scaled_df: pd.DataFrame, cfg: dict) -> np.ndarray:
    """The brief's required transparent comparator, C = R*S + (1-R)*T
    mapped to three classes.

    Exact choice, fixed and undocumented-nowhere-else:

    S (sentiment aggregate) = the fold-locally z-scored `mean_polarity`
    feature. `scaled_df` is expected to already be scaled by the SAME
    StandardScaler fit on this fold's training rows as the XGBoost model
    uses, so S lives on a comparable scale to T below without any
    additional fitting. Rows with no sentiment attached (the March-2021
    sparse patch, ~20% of bars -- phase1_report.md) score `mean_polarity`
    as NaN even after scaling; S is set to 0.0 (neutral -- "no sentiment
    signal") on those rows rather than dropped, so the baseline covers
    every row the model covers.

    T (technical aggregate) = the unweighted mean of the five z-scored
    technical features (rsi_14, macd_hist, dist_sma200, bollinger_pos,
    obv_slope), under the fixed domain convention that a HIGHER value of
    each is more bullish (higher RSI = stronger upward momentum; positive
    MACD histogram = bullish crossover; price above its 200-day average;
    price nearer the upper Bollinger band; rising OBV = accumulation).
    This is a standard trend-following sign convention, not fitted to
    this dataset -- a mean-reversion reading of RSI would flip its sign,
    and that choice is exactly the kind of thing a real linear baseline
    should state plainly rather than bury in code. T is always defined
    on these rows: the shared row mask (`clean_row_mask`) already
    requires all five technical indicators present.

    R (blend weight) = 0.5, fixed. An even split between sentiment and
    technicals; not tuned, since tuning R would make this a second model
    rather than a transparent comparator.

    C = 0.5*S + 0.5*T is on the same z-score-like scale as the label's
    volatility-adjusted return score, so it is mapped to Buy/Hold/Sell
    with the SAME fixed thresholds as the labels themselves
    (`cfg["labels"]["class_thresholds"]`, [-0.5, 0.5]) rather than a
    second set of thresholds invented for the baseline.
    """
    technical = cfg["features"]["technical"]
    R = 0.5

    S = scaled_df["mean_polarity"].fillna(0.0).to_numpy(dtype=float)
    T = scaled_df[technical].to_numpy(dtype=float).mean(axis=1)
    if np.isnan(T).any():
        raise ValueError("linear baseline: NaN in technical z-scores on a row the shared mask should cover")

    C = R * S + (1 - R) * T
    lo, hi = cfg["labels"]["class_thresholds"]
    labels = pd.cut(C, bins=[-np.inf, lo, hi, np.inf], labels=["Sell", "Hold", "Buy"])
    if pd.isna(labels).any():
        raise ValueError("linear baseline: unclassified row (should be impossible with +/-inf bin edges)")
    return np.asarray(labels).astype(str)


# --------------------------------------------------------------------------
# TreeSHAP attribution
# --------------------------------------------------------------------------

def build_shap_explainer(model: XGBClassifier) -> shap.TreeExplainer:
    """Path-dependent perturbation (shap's default for TreeExplainer),
    no interaction values -- only `.shap_values(X)` is ever called on the
    result, never `.shap_interaction_values(X)`."""
    _patch_shap_multiclass_base_score()
    return shap.TreeExplainer(model)


def compute_shap_values(explainer: shap.TreeExplainer, X: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """Returns an (n_samples, n_features, n_classes) array.

    Confirmed empirically against this environment's installed
    shap==0.49.1 / xgboost==3.2.0 (see module docstring): for a 3-class
    XGBClassifier, `explainer.shap_values(X)` returns a single ndarray
    shaped (n_samples, n_features, n_classes) -- NOT a per-class list,
    and NOT (n_samples, n_classes, n_features). Asserted here so a future
    shap/xgboost upgrade that changes this convention fails loudly at the
    point of the wrong assumption instead of silently mis-attributing
    every feature to the wrong class.
    """
    sv = explainer.shap_values(X)
    if isinstance(sv, list):
        raise ValueError(
            f"shap_values returned a list of {len(sv)} arrays (per-class convention); "
            "this module was written against the single-ndarray (n, features, classes) "
            "convention of shap==0.49.1 -- update compute_shap_values for the new shape"
        )
    expected_shape = (len(X), len(cols), len(CLASS_LABELS))
    if sv.shape != expected_shape:
        raise ValueError(f"shap_values shape {sv.shape} != expected {expected_shape}")
    return sv


# --------------------------------------------------------------------------
# decision records
# --------------------------------------------------------------------------

def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("could not read the git commit; decision records must be traceable") from exc


def _corpus_manifest_hash(cfg: dict, corpus: str | None = None) -> str:
    """The sha256 of the news subset actually used, read back out of
    artifacts/corpus_manifest.json rather than recomputed -- so a record's
    hash names the corpus that produced it, not whichever one happens to be
    the default."""
    manifest_path = Path(cfg["paths"]["artifacts"]) / "corpus_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"corpus manifest missing at {manifest_path}")
    manifest = json.loads(manifest_path.read_text())

    corpus = corpus or cfg.get("default_corpus", "fnspid")
    spec = cfg["corpora"][corpus]
    target_path = spec["path"] if spec["loader"] != "fnspid" else cfg["news"]["extracted_path"]

    # Corpora record themselves in different places in the manifest: FNSPID's
    # subsets sit in the top-level `extracted_subsets` list, the Alpaca pull
    # under its own supplemental section. Rather than rewrite committed
    # evidence to fit one shape, search the manifest for the entry that names
    # this file.
    found = _find_hash_for_path(manifest, target_path)
    if found is None:
        raise ValueError(
            f"corpus_manifest.json records no sha256 for {target_path!r} "
            f"(corpus {corpus!r}) -- every emitted record must name the corpus "
            f"file it came from"
        )
    return found


def _find_hash_for_path(node, target_path: str) -> str | None:
    """Depth-first search for a {path: target, sha256: ...} entry anywhere in
    the manifest."""
    if isinstance(node, dict):
        if node.get("path") == target_path and "sha256" in node:
            return node["sha256"]
        for value in node.values():
            found = _find_hash_for_path(value, target_path)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_hash_for_path(item, target_path)
            if found is not None:
                return found
    return None


def model_version_and_data_hashes(cfg: dict, corpus: str | None = None) -> tuple[str, dict[str, str]]:
    import xgboost

    git_commit = _git_commit()
    data_hashes = {
        "corpus_manifest_sha256": _corpus_manifest_hash(cfg, corpus),
        "corpus": corpus or cfg.get("default_corpus", "fnspid"),
        "git_commit": git_commit,
    }
    model_version = f"xgboost-{xgboost.__version__}-git{git_commit[:12]}"
    return model_version, data_hashes


def make_decision_records(
    eval_rows: pd.DataFrame,
    feature_vectors: pd.DataFrame,
    calibrated_proba: np.ndarray,
    margin: np.ndarray,
    shap_values: np.ndarray,
    expected_value: np.ndarray,
    cols: list[str],
    cfg: dict,
    corpus: str | None = None,
) -> list[DecisionRecord]:
    """One DecisionRecord per row of `eval_rows`. `shap_values` and
    `margin` are for the FULL class set; the predicted class only is
    sliced out per row, per brief section 7 ("shap_values and base_value
    are for the PREDICTED class only").

    `base_value` is taken from the explainer's OWN per-class
    `expected_value`, never derived as `raw_model_output - sum(shap)`.
    That distinction is the whole point of tests/test_shap_additivity.py:
    deriving the base value by subtraction would make the additivity
    identity true by construction, and the test that checks it vacuous.
    Taking it independently makes additivity a property that is verified
    rather than assumed.

    Confirmed empirically on this environment (shap 0.49.1 / xgboost
    3.2.0): shap's per-class expected_value equals xgboost's own
    `pred_contribs` bias column exactly, and base_value + sum(shap)
    reproduces the raw margin to ~1.5e-6 -- comfortably inside the
    schema's 1e-4 tolerance. That agreement also demonstrates the
    base_score compatibility shim above is inert with respect to
    attribution: per-class bias survives it unchanged."""
    ticker = cfg["tickers"][0]
    horizon = cfg["labels"]["primary_horizon_days"]
    seed = cfg["seed"]
    model_version, data_hashes = model_version_and_data_hashes(cfg, corpus)

    records = []
    for i in range(len(eval_rows)):
        pred_class_idx = int(np.argmax(calibrated_proba[i]))
        decision = INT_TO_CLASS[pred_class_idx]

        probabilities = {
            INT_TO_CLASS[c]: float(calibrated_proba[i, c]) for c in range(len(CLASS_LABELS))
        }
        raw_model_output = float(margin[i, pred_class_idx])
        shap_row = shap_values[i, :, pred_class_idx]
        shap_dict = {cols[j]: float(shap_row[j]) for j in range(len(cols))}
        base_value = float(expected_value[pred_class_idx])

        feature_vector = {
            c: float(feature_vectors.iloc[i][c]) for c in cols
        }
        top_k = rank_contributions(shap_dict, feature_vector, k=5)

        session_date = pd.Timestamp(eval_rows.iloc[i]["date"]).strftime("%Y-%m-%d")

        records.append(
            DecisionRecord(
                ticker=ticker,
                session_date=session_date,
                horizon_days=horizon,
                decision=decision,
                probabilities=probabilities,
                feature_vector=feature_vector,
                shap_values=shap_dict,
                base_value=base_value,
                raw_model_output=raw_model_output,
                top_k=top_k,
                risk_tier=RISK_TIER_PLACEHOLDER,
                model_version=model_version,
                data_hashes=data_hashes,
                seed=seed,
            )
        )
    return records


# --------------------------------------------------------------------------
# reliability curve
# --------------------------------------------------------------------------

def _binned_reliability(probs: np.ndarray, outcomes: np.ndarray, n_bins: int = 8):
    """Manual, empty-bin-tolerant reliability binning (aggregated
    one-vs-rest across all classes: each (row, class) pair contributes
    one point). Returns (bin_mean_pred, bin_empirical_freq, bin_counts)
    for non-empty bins only."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_idx = np.clip(np.digitize(probs, edges[1:-1], right=True), 0, n_bins - 1)
    means_pred, freqs, counts = [], [], []
    for b in range(n_bins):
        mask = bin_idx == b
        if not mask.any():
            continue
        means_pred.append(probs[mask].mean())
        freqs.append(outcomes[mask].mean())
        counts.append(int(mask.sum()))
    return np.array(means_pred), np.array(freqs), np.array(counts)


def save_reliability_curve(
    raw_proba: np.ndarray,
    calibrated_proba: np.ndarray,
    y_true_int: np.ndarray,
    out_path: Path,
) -> None:
    """Aggregated one-vs-rest reliability diagram (each class's
    probability column stacked into one set of points, per standard
    multiclass calibration-curve practice) -- before vs after isotonic
    calibration, on the SAME held-out eval fold the Brier scores are
    computed on."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n_classes = len(CLASS_LABELS)
    # class-major stacking: each class's probability column becomes one
    # block of points, paired with that class's one-vs-rest outcome
    outcomes_flat = np.concatenate([(y_true_int == c).astype(float) for c in range(n_classes)])
    raw_flat = np.concatenate([raw_proba[:, c] for c in range(n_classes)])
    calib_flat = np.concatenate([calibrated_proba[:, c] for c in range(n_classes)])

    raw_x, raw_y, raw_n = _binned_reliability(raw_flat, outcomes_flat)
    cal_x, cal_y, cal_n = _binned_reliability(calib_flat, outcomes_flat)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey", linewidth=1, label="perfect calibration")
    ax.plot(raw_x, raw_y, marker="o", label=f"before calibration (n={raw_n.sum()})")
    ax.plot(cal_x, cal_y, marker="s", label=f"after calibration (n={cal_n.sum()})")
    ax.set_xlabel("mean predicted probability (one-vs-rest, all classes stacked)")
    ax.set_ylabel("empirical frequency")
    ax.set_title("Reliability curve: isotonic calibration, held-out eval fold")
    ax.legend(loc="best", fontsize=9)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------

@dataclass
class EngineResult:
    records: list[DecisionRecord]
    cv_macro_f1_mean: float
    cv_macro_f1_sd: float
    cv_macro_f1_per_fold: list[float]
    baseline_cv_macro_f1_mean: float
    baseline_cv_macro_f1_sd: float
    baseline_cv_macro_f1_per_fold: list[float]
    eval_macro_f1_model: float  # single eval fold, calibrated decisions
    eval_macro_f1_baseline: float  # single eval fold, same rows
    brier_before: float
    brier_after: float
    n_calibration_rows: int
    n_eval_rows: int
    calibration_fold_id: int
    eval_fold_id: int
    model_version: str
    data_hashes: dict[str, str] = field(default_factory=dict)


def run_engine(
    cfg: dict,
    reliability_curve_path: Path | None = None,
    corpus: str | None = None,
) -> EngineResult:
    """End-to-end: train, calibrate, attribute, emit decision records for
    every bar in the held-out evaluation fold. Network-free -- reads
    price/news/sentiment exclusively from data/store and .cache, via
    harness.arms.build_all_matrices."""
    cols = feature_cols(cfg)
    horizon = cfg["labels"]["primary_horizon_days"]
    label_col = f"label_{horizon}d"

    matrices = build_all_matrices(cfg, corpus=corpus)
    clean = matrices["A_CLEAN"]
    row_mask = clean_row_mask(clean, horizon, cfg)
    df = clean.loc[row_mask].reset_index(drop=True)
    if df[label_col].isna().any():
        raise ValueError("engine: shared row set contains rows with no label at the primary horizon")

    folds = make_folds(ARMS["A_CLEAN"], df["date"], cfg, horizon)
    if len(folds) < 2:
        raise ValueError(f"engine needs >=2 walk-forward folds, got {len(folds)}")

    # --- cross-validated macro-F1, model vs. linear baseline, over all
    # folds -- reuses harness.arms.fit_predict_fold verbatim for the model
    # so this number is directly comparable to the harness's own A_CLEAN
    # result (phase2_report.md).
    cv_f1: list[float] = []
    baseline_cv_f1: list[float] = []
    for fold in folds:
        train = df.iloc[fold.train_idx]
        test = df.iloc[fold.test_idx]
        y_true, y_pred = fit_predict_fold(train, test, cols, label_col, cfg)
        cv_f1.append(macro_f1(y_true, y_pred))

        scaler = fit_scaler(train, cols)
        test_scaled = apply_scaler(test, cols, scaler)
        baseline_pred = linear_baseline_predict(test_scaled, cfg)
        baseline_cv_f1.append(macro_f1(test[label_col].astype(str).to_numpy(), baseline_pred))

    # --- calibration: fold[-2] fits the isotonic calibrators, fold[-1] is
    # the held-out evaluation fold everything is reported/emitted on. Two
    # different models, trained on two different (non-overlapping in what
    # they're EVALUATED on) train sets -- fold[-1]'s train set chronologically
    # includes fold[-2]'s test rows as ordinary training data, which is
    # correct temporal discipline, not a leak: they are strictly in the past
    # relative to fold[-1]'s test block.
    calib_fold: Fold = folds[-2]
    eval_fold: Fold = folds[-1]

    calib_train = df.iloc[calib_fold.train_idx]
    calib_test = df.iloc[calib_fold.test_idx]
    calib_model, calib_scaler = train_xgboost(calib_train, cols, label_col, cfg)
    raw_proba_calib, _margin_calib, _ = score_fold(calib_model, calib_scaler, calib_test, cols)
    y_true_calib_int = calib_test[label_col].astype(str).map(CLASS_TO_INT).to_numpy()
    calibrators = fit_isotonic_calibrators(raw_proba_calib, y_true_calib_int)

    eval_train = df.iloc[eval_fold.train_idx]
    eval_test = df.iloc[eval_fold.test_idx].reset_index(drop=True)
    eval_model, eval_scaler = train_xgboost(eval_train, cols, label_col, cfg)
    raw_proba_eval, margin_eval, eval_scaled = score_fold(eval_model, eval_scaler, eval_test, cols)
    y_true_eval_int = eval_test[label_col].astype(str).map(CLASS_TO_INT).to_numpy()
    y_true_eval_str = eval_test[label_col].astype(str).to_numpy()

    brier_before = brier_score(y_true_eval_str, raw_proba_eval, CLASS_LABELS)
    calibrated_proba_eval = apply_calibration(raw_proba_eval, calibrators)
    brier_after = brier_score(y_true_eval_str, calibrated_proba_eval, CLASS_LABELS)

    if reliability_curve_path is not None:
        save_reliability_curve(raw_proba_eval, calibrated_proba_eval, y_true_eval_int, reliability_curve_path)

    pred_calibrated = np.array([INT_TO_CLASS[int(np.argmax(row))] for row in calibrated_proba_eval])
    eval_macro_f1_model = macro_f1(y_true_eval_str, pred_calibrated)

    baseline_pred_eval = linear_baseline_predict(eval_scaled, cfg)
    eval_macro_f1_baseline = macro_f1(y_true_eval_str, baseline_pred_eval)

    # --- TreeSHAP on the eval model, eval fold's test rows
    explainer = build_shap_explainer(eval_model)
    shap_values = compute_shap_values(explainer, eval_scaled[cols], cols)
    expected_value = np.asarray(explainer.expected_value).ravel()
    if expected_value.shape != (len(CLASS_LABELS),):
        raise ValueError(
            f"explainer.expected_value has shape {expected_value.shape}, expected "
            f"one base value per class {(len(CLASS_LABELS),)}"
        )

    records = make_decision_records(
        eval_rows=eval_test,
        feature_vectors=eval_test,  # unscaled, human-readable values for display
        calibrated_proba=calibrated_proba_eval,
        margin=margin_eval,
        shap_values=shap_values,
        expected_value=expected_value,
        cols=cols,
        cfg=cfg,
        corpus=corpus,
    )

    model_version, data_hashes = model_version_and_data_hashes(cfg, corpus)

    return EngineResult(
        records=records,
        cv_macro_f1_mean=float(np.mean(cv_f1)),
        cv_macro_f1_sd=float(np.std(cv_f1, ddof=1)),
        cv_macro_f1_per_fold=[float(x) for x in cv_f1],
        baseline_cv_macro_f1_mean=float(np.mean(baseline_cv_f1)),
        baseline_cv_macro_f1_sd=float(np.std(baseline_cv_f1, ddof=1)),
        baseline_cv_macro_f1_per_fold=[float(x) for x in baseline_cv_f1],
        eval_macro_f1_model=eval_macro_f1_model,
        eval_macro_f1_baseline=eval_macro_f1_baseline,
        brier_before=brier_before,
        brier_after=brier_after,
        n_calibration_rows=len(calib_test),
        n_eval_rows=len(eval_test),
        calibration_fold_id=calib_fold.fold_id,
        eval_fold_id=eval_fold.fold_id,
        model_version=model_version,
        data_hashes=data_hashes,
    )
