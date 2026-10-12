"""Read-only structural preflight for the historical harness re-run.

This never loads a model or claims that a dataset/schema/scientific lock has
been reproduced. Empty directories and malformed files cannot enable a run.
"""
from importlib.util import find_spec
from pathlib import Path


RUNTIME_MODULES = (
    "numpy", "pandas", "scipy", "sklearn", "xgboost",
    "pandas_market_calendars", "pyarrow",
)


def _input_status(name: str, path: Path, kind: str) -> dict:
    result = {"name": name, "path": str(path), "kind": kind,
              "status": "available", "files_checked": 0}
    try:
        if not path.exists():
            result.update(status="missing", detail="Input is absent")
            return result
        if kind == "parquet_dataset":
            if not path.is_dir():
                result.update(status="wrong_type", detail="Expected a partition directory")
                return result
            files = sorted(path.rglob("*.parquet"))
            if not files:
                result.update(status="empty", detail="No Parquet partitions found")
                return result
        else:
            if not path.is_file():
                result.update(status="wrong_type", detail="Expected a file")
                return result
            files = [path]
        for file in files:
            if not file.is_file() or file.stat().st_size == 0:
                result.update(status="empty", detail=f"Empty or non-file input: {file}")
                return result
            with file.open("rb") as stream:
                if kind in ("parquet_dataset", "parquet_file"):
                    if file.stat().st_size <= 8 or stream.read(4) != b"PAR1":
                        result.update(status="invalid_format", detail=f"Missing Parquet header: {file}")
                        return result
                    stream.seek(-4, 2)
                    if stream.read(4) != b"PAR1":
                        result.update(status="invalid_format", detail=f"Missing Parquet footer: {file}")
                        return result
                else:
                    stream.read(1)  # Check read access; CSV schema is a later load check.
            result["files_checked"] += 1
    except OSError as error:
        result.update(status="unreadable", detail=f"{type(error).__name__}: {error}")
    return result


def harness_input_report(cfg: dict, corpus: str, root: Path) -> dict:
    ticker = cfg["tickers"][0]
    spec = cfg["corpora"][corpus]
    if spec["loader"] not in ("fnspid", "alpaca"):
        raise ValueError(f"Unknown news loader: {spec['loader']!r}")
    paths = [
        ("prices", Path(cfg["paths"]["store"]) / "prices" / f"ticker={ticker}", "parquet_dataset"),
        ("cached_sentiment", Path(cfg["sentiment"]["cache_dir"]) / "finbert_scores.parquet", "parquet_file"),
        ("news", Path(cfg["paths"]["store"]) / "news" / f"ticker={ticker}", "parquet_dataset")
        if spec["loader"] == "fnspid" else ("news", Path(spec["path"]), "csv_file"),
    ]
    inputs = [_input_status(name, (root / path).resolve(), kind) for name, path, kind in paths]
    runtime = []
    for module in RUNTIME_MODULES:
        try:
            runtime.append({"module": module, "discoverable": find_spec(module) is not None})
        except (ImportError, AttributeError, ValueError, OSError) as error:
            runtime.append({"module": module, "discoverable": False,
                            "detail": f"{type(error).__name__}: {error}"})
    blockers = [f"{item['name']}: {item['status']} - {item['path']} ({item['detail']})"
                for item in inputs if item["status"] != "available"]
    blockers += [f"runtime module: {item['module']}" for item in runtime if not item["discoverable"]]
    return {"schema": "investify-harness-preflight-v2", "corpus": corpus,
            "inputs": inputs, "runtime": runtime, "blockers": blockers,
            "preflight_passed": not blockers,
            "scope": "Read access, nonempty input files, Parquet boundary signatures and module discovery only; "
                     "no dataset row/schema/cache-coverage validation, dependency import or scientific-lock verification",
            "scientific_run_executed": False}


def harness_missing_inputs(cfg: dict, corpus: str, root: Path) -> list[str]:
    return harness_input_report(cfg, corpus, root)["blockers"]
