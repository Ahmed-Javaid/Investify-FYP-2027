"""Append-only Parquet store, partitioned by asset and date, queried
through DuckDB. Every row carries event_ts (when the thing happened) and
ingest_ts (when we wrote it). Writes are idempotent, keyed by a SHA-256
content hash over the row's identifying fields -- there is no update
path: replaying an ingest produces zero duplicate rows because rows whose
hash already exists are silently skipped, and existing files are never
modified, only added to.
"""
import hashlib
import json
from datetime import UTC, date, datetime
from math import isfinite
from numbers import Integral, Real
import re
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds


HASH_SCHEME = 'canonical-json-v2'
LEGACY_HASH_SCHEME = 'legacy-delimited-v1'


def _canonical_value(value):
    if value is None or pd.isna(value):
        return {'kind': 'missing', 'value': None}
    if isinstance(value, bool):
        return {'kind': 'boolean', 'value': value}
    if isinstance(value, Integral):
        return {'kind': 'integer', 'value': int(value)}
    if isinstance(value, Real):
        if not isfinite(value):
            raise ValueError('Content identity cannot contain infinite numeric values')
        return {'kind': 'number', 'value': float(value)}
    if isinstance(value, datetime):
        instant = pd.Timestamp(value)
        if instant.tzinfo is not None:
            instant = instant.tz_convert('UTC')
        return {'kind': 'timestamp', 'value': instant.isoformat()}
    if isinstance(value, date):
        return {'kind': 'date', 'value': value.isoformat()}
    if isinstance(value, str):
        return {'kind': 'text', 'value': value}
    raise ValueError(f'Unsupported content identity type: {type(value).__name__}')


def content_hash(row: pd.Series, content_cols: list[str], *, hash_scheme=HASH_SCHEME) -> str:
    if hash_scheme == LEGACY_HASH_SCHEME:
        payload = '|'.join(str(row[c]) for c in content_cols)
    elif hash_scheme == HASH_SCHEME:
        payload = json.dumps({'scheme': HASH_SCHEME,
                              'fields': [{'column': c, **_canonical_value(row[c])} for c in content_cols]},
                             ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    else:
        raise ValueError('Unknown content hash scheme')
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AppendOnlyStore:
    def __init__(self, root: Path | str, *, hash_scheme=HASH_SCHEME):
        if hash_scheme not in (HASH_SCHEME, LEGACY_HASH_SCHEME):
            raise ValueError('Unknown content hash scheme')
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.hash_scheme = hash_scheme
        self.last_append_audit = None

    def _table_path(self, table: str) -> Path:
        if not isinstance(table, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]*', table):
            raise ValueError('Use a plain logical table name')
        return self.root / table

    def _contract(self, table, content_cols):
        path = self._table_path(table)
        marker = path / '_content_hash_contract.json'
        expected = {'scheme': self.hash_scheme, 'content_cols': content_cols}
        if marker.exists():
            if json.loads(marker.read_text(encoding='utf-8')) != expected:
                raise ValueError('Existing table identity contract differs; do not mix hash schemes or identity columns')
        elif any(path.rglob('*.parquet')) and self.hash_scheme != LEGACY_HASH_SCHEME:
            raise ValueError('Unversioned historical store: read it unchanged or choose explicit legacy-delimited-v1 compatibility; do not mix V2 hashes')
        return marker, expected

    def _existing_hashes(self, table: str) -> set[str]:
        table_path = self._table_path(table)
        if not table_path.exists() or not any(table_path.rglob("*.parquet")):
            return set()
        dataset = ds.dataset(table_path, format='parquet', partitioning='hive')
        return set(dataset.to_table(columns=['content_hash'])['content_hash'].to_pylist())

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
        if not content_cols or len(set(content_cols)) != len(content_cols):
            raise ValueError('Use nonempty, unique content identity columns')
        missing = set(content_cols + partition_cols) - set(df.columns)
        if missing:
            raise ValueError(f'Missing store columns: {sorted(missing)}')
        marker, contract = self._contract(table, content_cols)
        if df.empty:
            self.last_append_audit = {'received_rows': 0, 'duplicate_rows_within_batch': 0,
                                      'existing_rows_skipped': 0, 'written_rows': 0,
                                      'hash_scheme': self.hash_scheme}
            return 0

        df = df.copy()
        for value in df[event_ts_col]:
            if pd.isna(value) or pd.Timestamp(value).tzinfo is None:
                raise ValueError('Every stored event timestamp must be nonmissing and timezone-aware')
        df[event_ts_col] = pd.to_datetime(df[event_ts_col], utc=True)
        df["content_hash"] = df.apply(lambda r: content_hash(r, content_cols, hash_scheme=self.hash_scheme), axis=1)
        unique = df.drop_duplicates(subset=['content_hash'], keep='first')

        existing = self._existing_hashes(table)
        new_rows = unique[~unique["content_hash"].isin(existing)].copy()
        self.last_append_audit = {'received_rows': len(df), 'duplicate_rows_within_batch': len(df) - len(unique),
                                  'existing_rows_skipped': len(unique) - len(new_rows),
                                  'written_rows': len(new_rows), 'hash_scheme': self.hash_scheme}
        if new_rows.empty:
            return 0

        new_rows["ingest_ts"] = datetime.now(UTC)

        table_path = self._table_path(table)
        table_path.mkdir(parents=True, exist_ok=True)
        if not marker.exists():
            with marker.open('x', encoding='utf-8') as file:
                json.dump(contract, file, indent=2)
        new_rows['content_hash_scheme'] = self.hash_scheme
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
        if not where:
            return ds.dataset(table_path, format='parquet', partitioning='hive').to_table().to_pandas()
        import duckdb  # Optional SQL filter backend; ordinary reads use Arrow.
        glob = str(table_path / "**" / "*.parquet")
        query = f"SELECT * FROM read_parquet('{glob}', hive_partitioning=1)"
        if where:
            query += f" WHERE {where}"
        return duckdb.sql(query).df()

    def row_count(self, table: str) -> int:
        table_path = self._table_path(table)
        if not table_path.exists() or not any(table_path.rglob("*.parquet")):
            return 0
        return ds.dataset(table_path, format='parquet', partitioning='hive').count_rows()
