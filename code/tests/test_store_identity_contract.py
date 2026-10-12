"""Actual temporary Parquet writes with labelled fixtures, never restored data."""
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.store import AppendOnlyStore, content_hash, HASH_SCHEME, LEGACY_HASH_SCHEME


def fixtures():
    return pd.DataFrame({'ticker': ['NVDA', 'NVDA'], 'headline': ['LABELLED A', 'LABELLED B'],
                          'event_ts': pd.to_datetime(['2023-01-02T12:00:00Z'] * 2)})


def test_duplicate_rows_within_first_batch_are_written_once_and_replay_is_idempotent(tmp_path):
    store = AppendOnlyStore(tmp_path)
    batch = pd.concat([fixtures(), fixtures()], ignore_index=True)
    assert store.append(batch, 'news', ['ticker', 'headline', 'event_ts'], ['ticker']) == 2
    assert store.last_append_audit['duplicate_rows_within_batch'] == 2
    assert store.row_count('news') == 2
    assert store.append(batch, 'news', ['ticker', 'headline', 'event_ts'], ['ticker']) == 0
    assert store.last_append_audit['existing_rows_skipped'] == 2


def test_new_appends_leave_all_preexisting_parquet_bytes_unchanged(tmp_path):
    store = AppendOnlyStore(tmp_path)
    store.append(fixtures().iloc[:1], 'news', ['ticker', 'headline', 'event_ts'], ['ticker'])
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*.parquet')}
    assert store.append(fixtures(), 'news', ['ticker', 'headline', 'event_ts'], ['ticker']) == 1
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in before.items())


def test_canonical_hash_separates_delimiter_collisions_and_field_types():
    left, right = pd.Series({'a': 'x|y', 'b': 'z'}), pd.Series({'a': 'x', 'b': 'y|z'})
    assert content_hash(left, ['a', 'b'], hash_scheme=LEGACY_HASH_SCHEME) == content_hash(right, ['a', 'b'], hash_scheme=LEGACY_HASH_SCHEME)
    assert content_hash(left, ['a', 'b']) != content_hash(right, ['a', 'b'])
    assert content_hash(pd.Series({'a': 1}), ['a']) != content_hash(pd.Series({'a': '1'}), ['a'])


def test_changed_scheme_or_identity_columns_cannot_mix_with_an_existing_table(tmp_path):
    store = AppendOnlyStore(tmp_path)
    store.append(fixtures(), 'news', ['ticker', 'headline', 'event_ts'], ['ticker'])
    with pytest.raises(ValueError, match='identity contract differs'):
        store.append(fixtures(), 'news', ['ticker', 'event_ts'], ['ticker'])
    with pytest.raises(ValueError, match='identity contract differs'):
        AppendOnlyStore(tmp_path, hash_scheme=LEGACY_HASH_SCHEME).append(fixtures(), 'news', ['ticker', 'headline', 'event_ts'], ['ticker'])


def test_unversioned_historical_store_requires_explicit_legacy_compatibility_for_append(tmp_path):
    old = AppendOnlyStore(tmp_path, hash_scheme=LEGACY_HASH_SCHEME)
    old.append(fixtures(), 'news', ['ticker', 'headline', 'event_ts'], ['ticker'])
    marker = tmp_path / 'news/_content_hash_contract.json'
    marker.unlink()  # Only a labelled disposable fixture marker.
    before = {p: p.read_bytes() for p in tmp_path.rglob('*.parquet')}
    current = AppendOnlyStore(tmp_path)
    assert len(current.read('news')) == 2  # Read existing bytes without migration.
    with pytest.raises(ValueError, match='Unversioned historical store'):
        current.append(fixtures(), 'news', ['ticker', 'headline', 'event_ts'], ['ticker'])
    assert old.append(fixtures(), 'news', ['ticker', 'headline', 'event_ts'], ['ticker']) == 0
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize('timestamp', [None, pd.NaT, '2023-01-02T12:00:00'])
def test_missing_or_naive_events_cannot_be_persisted(tmp_path, timestamp):
    frame = fixtures().iloc[:1].copy()
    frame['event_ts'] = timestamp
    with pytest.raises(ValueError, match='timezone-aware'):
        AppendOnlyStore(tmp_path).append(frame, 'news', ['ticker', 'headline', 'event_ts'], ['ticker'])
    assert not list(tmp_path.rglob('*.parquet'))


def test_new_table_declares_the_hash_scheme_and_source_dataframe_is_unchanged(tmp_path):
    frame = fixtures()
    before = frame.copy(deep=True)
    store = AppendOnlyStore(tmp_path)
    store.append(frame, 'news', ['ticker', 'headline', 'event_ts'], ['ticker'])
    marker = json.loads((tmp_path / 'news/_content_hash_contract.json').read_text())
    assert marker['scheme'] == HASH_SCHEME
    assert store.read('news')['content_hash_scheme'].eq(HASH_SCHEME).all()
    pd.testing.assert_frame_equal(frame, before)


def test_empty_batch_has_no_files_and_a_zero_row_audit(tmp_path):
    store = AppendOnlyStore(tmp_path)
    assert store.append(fixtures().iloc[:0], 'news', ['ticker', 'headline', 'event_ts'], ['ticker']) == 0
    assert store.last_append_audit['written_rows'] == 0
    assert not list(tmp_path.rglob('*.parquet'))
