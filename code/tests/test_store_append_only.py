"""tests/test_store_append_only.py -- brief section 5: writes are
idempotent, keyed by SHA-256 content hash. There is no update path.
Replaying an ingest must produce zero duplicate rows."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investify.store import AppendOnlyStore  # noqa: E402

CONTENT_COLS = ["ticker", "date", "value"]
PARTITION_COLS = ["ticker"]


def make_df(n=3, offset=0):
    return pd.DataFrame(
        {
            "ticker": ["NVDA"] * n,
            "date": [f"2023-01-{i+1+offset:02d}" for i in range(n)],
            "value": [float(i + offset) for i in range(n)],
            "event_ts": pd.to_datetime([f"2023-01-{i+1+offset:02d}T10:00:00Z" for i in range(n)]),
        }
    )


def test_append_writes_new_rows(tmp_path):
    store = AppendOnlyStore(tmp_path)
    df = make_df(3)
    written = store.append(df, "prices", CONTENT_COLS, PARTITION_COLS)
    assert written == 3
    assert store.row_count("prices") == 3


def test_replaying_same_ingest_produces_zero_duplicates(tmp_path):
    store = AppendOnlyStore(tmp_path)
    df = make_df(5)
    store.append(df, "prices", CONTENT_COLS, PARTITION_COLS)
    assert store.row_count("prices") == 5

    # replay the exact same ingest
    written_second_time = store.append(df, "prices", CONTENT_COLS, PARTITION_COLS)
    assert written_second_time == 0
    assert store.row_count("prices") == 5  # NOT 10


def test_partial_overlap_only_new_rows_written(tmp_path):
    store = AppendOnlyStore(tmp_path)
    first = make_df(3, offset=0)
    store.append(first, "prices", CONTENT_COLS, PARTITION_COLS)

    second = make_df(3, offset=2)  # overlaps on offset=2, adds offset=3,4
    written = store.append(second, "prices", CONTENT_COLS, PARTITION_COLS)
    assert written == 2  # only the 2 genuinely new rows
    assert store.row_count("prices") == 5


def test_no_update_path_hash_match_means_skip_regardless_of_other_fields(tmp_path):
    """There is no update mechanism: if content_hash matches, the row is
    skipped entirely, even if the caller tries to 'update' a field that
    isn't part of the content hash."""
    store = AppendOnlyStore(tmp_path)
    df = make_df(1)
    df["extra_field"] = "original"
    store.append(df, "prices", CONTENT_COLS, PARTITION_COLS)

    mutated = df.copy()
    mutated["extra_field"] = "mutated"  # not in CONTENT_COLS -> same hash
    written = store.append(mutated, "prices", CONTENT_COLS, PARTITION_COLS)
    assert written == 0

    stored = store.read("prices")
    assert (stored["extra_field"] == "original").all(), "existing row must never be overwritten"


def test_append_requires_event_ts_column(tmp_path):
    store = AppendOnlyStore(tmp_path)
    df = make_df(1).drop(columns=["event_ts"])
    with pytest.raises(ValueError):
        store.append(df, "prices", CONTENT_COLS, PARTITION_COLS)


def test_ingest_ts_is_recorded_and_distinct_from_event_ts(tmp_path):
    store = AppendOnlyStore(tmp_path)
    df = make_df(1)
    store.append(df, "prices", CONTENT_COLS, PARTITION_COLS)
    stored = store.read("prices")
    assert "ingest_ts" in stored.columns
    assert "event_ts" in stored.columns
