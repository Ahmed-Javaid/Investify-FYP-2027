"""Phase 2 entrypoint: run all five arms at both horizons, write
artifacts/results.json + results.csv + the grouped bar chart with the
0.03 threshold line, and record enough provenance (seed, snapshot
hashes, corpus manifest hash, package versions, git commit) that the
numbers can be traced back to the run that produced them.

Usage:
    uv run python -m investify.harness.run_spike               # default corpus
    uv run python -m investify.harness.run_spike --corpus alpaca

Each corpus writes to its own artefact prefix (config: corpora.<name>.
results_prefix), so a second corpus never overwrites the first's committed
evidence.
"""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

from investify.harness.arms import ARMS, run_all_arms
from investify.harness.splits import SPLIT_CONTRACT_VERSION
from investify.science_identity import run_identity
from investify.corpus_lineage import resolve_lineage

RESULT_COLUMNS = [
    "corpus", "arm", "horizon_days", "changes", "n_rows", "n_folds",
    "macro_f1", "macro_f1_sd", "chance", "lift", "ci_lo", "ci_hi",
    "threshold", "verdict",
]


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("could not read the git commit; results must be traceable") from exc


def package_versions() -> dict[str, str]:
    import numpy
    import sklearn
    import xgboost

    return {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": numpy.__version__,
        "scikit-learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
    }


def provenance(cfg: dict, corpus: str, *, scientific_identity: dict | None = None) -> dict:
    manifest_path = Path(cfg["paths"]["artifacts"]) / "corpus_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"corpus manifest missing at {manifest_path}")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    if scientific_identity is not None and scientific_identity['input_snapshots']['corpus_manifest']['files'][manifest_path.name] != manifest_digest:
        raise RuntimeError('Corpus manifest identity changed before provenance export; no result is accepted')
    specification = cfg['corpora'][corpus]
    target = cfg['news']['extracted_path'] if specification['loader'] == 'fnspid' else specification['path']
    lineage = resolve_lineage(manifest, target, project_base=Path(__file__).resolve().parents[3])

    return {
        "seed": cfg["seed"],
        "corpus": corpus,
        "corpus_spec": cfg["corpora"][corpus],
        "tickers": cfg["tickers"],
        "date_range": cfg["date_range"],
        "git_commit": git_commit(),
        "package_versions": package_versions(),
        "corpus_manifest": manifest,
        "corpus_manifest_file_sha256": manifest_digest,
        "corpus_lineage": lineage,
        "xgboost_config": cfg["xgboost"],
        "splits": cfg["splits"],
        "split_contract": SPLIT_CONTRACT_VERSION,
        "scientific_identity": scientific_identity if scientific_identity is not None else run_identity(cfg, corpus),
        "label_availability": "Exact observed-row endpoint computed on full prices before feature filtering; strictly before test session",
        "scientific_source_sha256": {str(path.relative_to(Path(__file__).resolve().parents[3])):
                                      hashlib.sha256(path.read_bytes()).hexdigest()
                                      for path in (Path(__file__), Path(__file__).with_name('splits.py'),
                                                   Path(__file__).with_name('arms.py'),
                                                   Path(__file__).parents[1] / 'labels.py')},
        "leakage_control": cfg["leakage_control"],
        "feature_cols": cfg["features"]["technical"] + cfg["features"]["sentiment"],
        "run_completed_utc": pd.Timestamp.now(tz='UTC').isoformat(),
    }


def write_chart(results_df: pd.DataFrame, cfg: dict, out_path: Path) -> None:
    """Grouped bar chart of lift per arm per horizon, with the 0.03
    threshold drawn as a line."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    threshold = cfg["leakage_control"]["pass_threshold_abs_lift"]
    arms = list(ARMS.keys())
    horizons = sorted(results_df["horizon_days"].unique())

    x = np.arange(len(arms))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10, 5.5))

    for i, horizon in enumerate(horizons):
        sub = results_df[results_df["horizon_days"] == horizon].set_index("arm").loc[arms]
        offset = (i - (len(horizons) - 1) / 2) * width
        yerr = np.vstack([
            (sub["lift"] - sub["ci_lo"]).clip(lower=0).values,
            (sub["ci_hi"] - sub["lift"]).clip(lower=0).values,
        ])
        ax.bar(
            x + offset, sub["lift"].values, width,
            yerr=yerr, capsize=4,
            label=f"{horizon}-day horizon",
        )

    ax.axhline(threshold, color="crimson", linestyle="--", linewidth=1.2,
               label=f"leak threshold (+{threshold})")
    ax.axhline(-threshold, color="crimson", linestyle="--", linewidth=1.2)
    ax.axhline(0, color="black", linewidth=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(arms, rotation=15, ha="right")
    ax.set_ylabel("lift (macro-F1 − stratified-random baseline)")
    ax.set_title(
        f"Leakage harness: lift by arm, {cfg['tickers'][0]}, "
        f"{cfg['splits']['n_folds']} folds, seed {cfg['seed']}\n"
        "error bars = 95% bootstrap CI on lift"
    )
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def checked_run_all_arms(cfg: dict, corpus: str) -> tuple[list[dict], dict]:
    """Refuse results if executed source/config/input/runtime bytes changed."""
    before = run_identity(cfg, corpus)
    results = run_all_arms(cfg, corpus=corpus)
    after = run_identity(cfg, corpus)
    if before != after:
        raise RuntimeError('Scientific source/config/input/runtime identity changed during the harness run; no result is accepted')
    return results, after


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the leakage harness.")
    parser.add_argument(
        "--corpus",
        default=None,
        help="news corpus to run against (config: corpora.*); defaults to default_corpus",
    )
    parser.add_argument('--output-directory', type=Path,
                        help='New run directory; never overwrite the historical artifact prefix')
    parser.add_argument('--config', type=Path, default=Path('config/spike.yaml'))
    args = parser.parse_args(argv)

    t0 = time.time()
    cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))
    corpus = args.corpus or cfg.get("default_corpus", "fnspid")
    if corpus not in cfg["corpora"]:
        raise ValueError(f"unknown corpus {corpus!r}; known: {sorted(cfg['corpora'])}")
    prefix = cfg["corpora"][corpus]["results_prefix"]

    if args.output_directory is None:
        raise ValueError('Choose a new --output-directory for the corrected split contract; historical results are preserved')
    artifacts = args.output_directory.resolve()
    if artifacts.exists():
        raise ValueError('Preserve prior runs; the output directory must be new')
    artifacts.mkdir(parents=True)

    print(f"=== Running {len(ARMS)} arms x {len(cfg['labels']['horizons_days'])} horizons "
          f"on corpus {corpus!r} (seed {cfg['seed']}, {cfg['splits']['n_folds']} folds) ===",
          flush=True)

    results, scientific_identity = checked_run_all_arms(cfg, corpus)

    payload = {"provenance": provenance(cfg, corpus, scientific_identity=scientific_identity), "results": results}
    results_df = pd.DataFrame(results)[RESULT_COLUMNS]
    results_df.to_csv(artifacts / f"{prefix}.csv", index=False)
    (artifacts / f"{prefix}.json").write_text(json.dumps(payload, indent=2, default=str))

    chart_name = "arms_lift.png" if prefix == "results" else f"arms_lift_{corpus}.png"
    write_chart(results_df, cfg, artifacts / chart_name)

    print(results_df.to_string(index=False, float_format=lambda v: f"{v: .4f}"), flush=True)
    print(f"\n=== DONE in {time.time()-t0:.1f}s -> {artifacts}/{prefix}.json, {prefix}.csv, "
          f"{chart_name} ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
