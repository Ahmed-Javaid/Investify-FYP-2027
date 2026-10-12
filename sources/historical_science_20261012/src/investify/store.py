"""Append-only Parquet store, partitioned by asset and date, queried
through DuckDB. Every row carries event_ts (when the thing happened) and
ingest_ts (when we wrote it). Writes are idempotent, keyed by a SHA-256
content hash over the row's identifying fields -- there is no update
path: replaying an ingest produces zero duplicate rows because rows whose
hash already exists are silently skipped, and existing files are never
modified, only added to.
"""
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds


def content_hash(row: pd.Series, content_cols: list[str]) -> str:
    payload = "|".join(str(row[c]) for c in content_cols)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AppendOnlyStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _table_path(self, table: str) -> Path:
        return self.root / table

    def _existing_hashes(self, table: str) -> set[str]:
        table_path = self._table_path(table)
        if not table_path.exists() or not any(table_path.rglob("*.parquet")):
            return set()
        glob = str(table_path / "**" / "*.parquet")
        rows = duckdb.sql(
            f"SELECT DISTINCT content_hash FROM read_parquet('{glob}', hive_partitioning=1)"
        ).fetchall()
        return {r[0] for r in rows}

    def append(
        self,
        df: pd.DataFrame,
        table: str,
        content_cols: list[str],
        partition_cols: list[str],
        event_ts_col: str = "event_ts",
    ) -> int:
        """Append new rows to `table`, deduped by SHA-256 over
        `content_cols`. Rows whose hash already exists in the store are
        skipped. Returns the number of rows actually written."""
        if event_ts_col not in df.columns:
            raise ValueError(f"append requires an '{event_ts_col}' column on every row")

        df = df.copy()
        df["content_hash"] = df.apply(lambda r: content_hash(r, content_cols), axis=1)

        existing = self._existing_hashes(table)
        new_rows = df[~df["content_hash"].isin(existing)].copy()
        if new_rows.empty:
            return 0

        new_rows["ingest_ts"] = datetime.now(UTC)

        table_path = self._table_path(table)
        arrow_table = pa.Table.from_pandas(new_rows, preserve_index=False)
        ds.write_dataset(
            arrow_table,
            base_dir=str(table_path),
            format="parquet",
            partitioning=partition_cols,
            partitioning_flavor="hive",
            existing_data_behavior="overwrite_or_ignore",
            basename_template=f"part-{uuid4().hex}-{{i}}.parquet",
        )
        return len(new_rows)

    def read(self, table: str, where: str | None = None) -> pd.DataFrame:
        table_path = self._table_path(table)
        if not table_path.exists() or not any(table_path.rglob("*.parquet")):
            return pd.DataFrame()
        glob = str(table_path / "**" / "*.parquet")
        query = f"SELECT * FROM read_parquet('{glob}', hive_partitioning=1)"
        if where:
            query += f" WHERE {where}"
        return duckdb.sql(query).df()

    def row_count(self, table: str) -> int:
        table_path = self._table_path(table)
        if not table_path.exists() or not any(table_path.rglob("*.parquet")):
            return 0
        glob = str(table_path / "**" / "*.parquet")
        return duckdb.sql(f"SELECT COUNT(*) FROM read_parquet('{glob}', hive_partitioning=1)").fetchone()[0]
