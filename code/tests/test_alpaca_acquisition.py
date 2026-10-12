"""Labelled fixtures cover resume, source integrity and revised-text timing."""
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from acquire_alpaca_news import acquire, audit_articles


def article(identity=1, created='2023-01-02T12:34:56Z', updated=None):
    return {'id': identity, 'headline': 'LABELLED fixture headline',
            'created_at': created, 'updated_at': updated or created,
            'symbols': ['NVDA'], 'source': 'LABELLED fixture publisher'}


def response(items, token=None):
    raw = json.dumps({'news': items, 'next_page_token': token}).encode()
    return {'status': 'response_received', 'http_status': 200, 'raw_bytes': raw}


def test_resume_uses_exact_next_token_and_retains_prior_page_bytes(tmp_path):
    directory, first = tmp_path / 'snapshot', tmp_path / 'first.json'
    count = 0
    def interrupted(spec):
        nonlocal count
        count += 1
        return response([article()], 'fixture_token') if count == 1 else {
            'status': 'connection_failed', 'winerror': 10061}
    result = acquire(directory, first, fetch=interrupted, sleeper=lambda _: None)
    assert result['status'] == 'failed'
    page = directory / 'page-000001.json'
    original = page.read_bytes()
    def resumed(spec):
        assert 'page_token=fixture_token' in spec['url']
        return response([article(2)])
    result = acquire(directory, tmp_path / 'resumed.json', resume=True,
                     fetch=resumed, sleeper=lambda _: None)
    assert result['status'] == 'acquired_and_audited'
    assert result['audit']['publication_rows'] == 2
    assert result['requests_this_invocation'] == 1
    assert page.read_bytes() == original


def test_raw_page_tampering_refuses_resume_before_request(tmp_path):
    directory = tmp_path / 'snapshot'
    acquire(directory, tmp_path / 'first.json', maximum_pages=1,
            fetch=lambda _: response([article()], 'fixture_token'), sleeper=lambda _: None)
    page = directory / 'page-000001.json'
    record = json.loads(page.read_text())
    record['payload_text'] = record['payload_text'].replace('LABELLED fixture headline', 'tampered')
    page.write_text(json.dumps(record))
    result = acquire(directory, tmp_path / 'resumed.json', resume=True,
                     fetch=lambda _: pytest.fail('Must not request after tampering'))
    assert result['status'] == 'failed'
    assert result['requests_this_invocation'] == 0
    assert 'hash check' in result['error_message']


def test_revision_uses_update_time_and_excludes_post_window_updates():
    original = article()
    publication, conservative, audit = audit_articles([
        original, original, article(2, updated='2023-01-03T18:00:00Z'),
        article(3, updated='2024-01-02T00:00:00Z'),
        article(4, created='2017-12-31T23:00:00Z', updated='2018-01-02T00:00:00Z')])
    assert len(publication) == 3 and len(conservative) == 2
    assert conservative[1]['event_ts'] == '2023-01-03T18:00:00+00:00'
    assert publication[1]['event_ts'] == '2023-01-02T12:34:56Z'
    assert audit['identical_duplicate_rows'] == 1
    assert audit['outside_publication_window'] == 1
    assert audit['updates_outside_window_excluded_from_conservative'] == 1
    assert audit['revised_after_publication'] == 2


def test_conflicting_versions_are_not_silently_deduplicated():
    with pytest.raises(ValueError, match='Conflicting'):
        audit_articles([article(), dict(article(), headline='LABELLED changed headline')])


@pytest.mark.parametrize('value', ['2023-01-02T12:34:56', None, 'invalid'])
def test_timestamp_must_be_a_real_timezone_aware_instant(value):
    with pytest.raises(ValueError):
        audit_articles([article(created=value)])


def test_completed_snapshot_replays_without_network_and_verifies_csv(tmp_path):
    directory = tmp_path / 'snapshot'
    acquire(directory, tmp_path / 'first.json', fetch=lambda _: response([article()]))
    result = acquire(directory, tmp_path / 'verified.json', resume=True,
                     fetch=lambda _: pytest.fail('Completed snapshot must not refetch'))
    assert result['status'] == 'acquired_and_audited'
    assert result['requests_this_invocation'] == 0
    path = directory / 'revision_conservative.csv'
    path.write_text(path.read_text().replace('LABELLED fixture headline', 'tampered'))
    result = acquire(directory, tmp_path / 'tampered.json', resume=True,
                     fetch=lambda _: pytest.fail('Completed snapshot must not refetch'))
    assert result['status'] == 'failed'
    assert 'derived CSV differs' in result['error_message']


def test_repeated_token_fails_without_unbounded_requests(tmp_path):
    calls = []
    def fetch(spec):
        calls.append(spec)
        return response([article(len(calls))], 'fixture_token')
    result = acquire(tmp_path / 'snapshot', tmp_path / 'receipt.json',
                     fetch=fetch, sleeper=lambda _: None)
    assert result['status'] == 'failed'
    assert len(calls) == 2
    assert 'repeated pagination token' in result['error_message']


def test_provider_echoed_credentials_are_not_saved(tmp_path):
    result = acquire(tmp_path / 'snapshot', tmp_path / 'receipt.json',
                     headers={'APCA-API-KEY-ID': 'LABELLED fixture headline'},
                     fetch=lambda _: response([article()]))
    assert result['status'] == 'failed'
    assert not list((tmp_path / 'snapshot').glob('page-*.json'))
    assert 'LABELLED fixture headline' not in (tmp_path / 'receipt.json').read_text()
