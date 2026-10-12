"""Fresh Alpaca news snapshots with raw-page replay and revision-aware CSVs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlencode
from probe_market_reacquisition import ROOT, alpaca_credentials, probe

URL = 'https://data.alpaca.markets/v1beta1/news'
PARAMS = {'symbols': 'NVDA', 'start': '2018-01-01T00:00:00Z',
          'end': '2023-12-31T23:59:59.999999Z', 'limit': 50,
          'sort': 'asc', 'include_content': 'false'}
COLUMNS = ['id', 'ticker', 'headline', 'event_ts', 'created_at', 'updated_at',
           'available_at', 'publisher', 'author', 'url', 'n_symbols_tagged']


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Missing or non-string provider timestamp')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Provider timestamp must have an explicit timezone')
    return result.astimezone(timezone.utc)


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def replay_pages(directory, config):
    """Recover the exact continuation from durable pages, refusing tampering."""
    articles, receipts, used_tokens = [], [], set()
    token, complete = None, False
    for index, path in enumerate(sorted(directory.glob('page-*.json')), 1):
        if path.name != f'page-{index:06d}.json' or complete:
            raise ValueError('Noncontiguous pages or page after completed pagination')
        record = json.loads(path.read_text(encoding='utf-8'))
        expected = dict(config['params'])
        if token is not None:
            expected['page_token'] = token
        if record['request_params'] != expected or record['config_sha256'] != digest(json_bytes(config)):
            raise ValueError('Saved page differs from acquisition identity or token chain')
        raw = record['payload_text'].encode('utf-8')
        if digest(raw) != record['response_sha256']:
            raise ValueError('Saved raw provider bytes failed their hash check')
        payload = json.loads(raw)
        if not isinstance(payload.get('news'), list):
            raise ValueError('Provider response has no news list')
        articles.extend(payload['news'])
        receipts.append({'file': path.name, 'sha256': digest(path.read_bytes()),
                         'response_sha256': digest(raw), 'article_count': len(payload['news']),
                         'received_utc': record['received_utc']})
        token = payload.get('next_page_token')
        if token is not None and (not isinstance(token, str) or not token or token in used_tokens):
            raise ValueError('Invalid or repeated pagination token')
        if token is not None:
            used_tokens.add(token)
        complete = token is None
    return articles, receipts, token, complete


def audit_articles(articles):
    """Preserve timestamps and explicitly account for duplicates/exclusions."""
    seen, rows = {}, []
    duplicate_count = outside_count = revised_count = midnight_count = 0
    start, end = timestamp(PARAMS['start']), timestamp(PARAMS['end'])
    for article in articles:
        if not isinstance(article, dict) or type(article.get('id')) not in (int, str):
            raise ValueError('Article requires a stable provider ID')
        identity = str(article['id'])
        representation = digest(json.dumps(article, sort_keys=True, ensure_ascii=False).encode('utf-8'))
        if identity in seen:
            if seen[identity] != representation:
                raise ValueError('Conflicting article versions for the same ID; inspect raw pages')
            duplicate_count += 1
            continue
        seen[identity] = representation
        created, updated = timestamp(article.get('created_at')), timestamp(article.get('updated_at'))
        if updated < created:
            raise ValueError('Article update precedes its publication')
        symbols, headline = article.get('symbols'), article.get('headline')
        if not isinstance(symbols, list) or 'NVDA' not in symbols:
            raise ValueError('Provider returned an article without the requested ticker')
        if not isinstance(headline, str) or not headline.strip():
            raise ValueError('Provider returned a missing or blank headline')
        if not start <= created <= end:
            outside_count += 1
            continue
        available = max(created, updated)
        revised_count += updated > created
        midnight_count += not (created.hour or created.minute or created.second or created.microsecond)
        rows.append({'id': identity, 'ticker': 'NVDA', 'headline': headline,
                     'event_ts': article['created_at'], 'created_at': article['created_at'],
                     'updated_at': article['updated_at'], 'available_at': available.isoformat(),
                     'publisher': article.get('source', ''), 'author': article.get('author', ''),
                     'url': article.get('url', ''), 'n_symbols_tagged': len(symbols)})
    if not rows:
        raise ValueError('No valid in-window articles were received')
    rows.sort(key=lambda row: (timestamp(row['created_at']), row['id']))
    conservative = [dict(row, event_ts=row['available_at']) for row in rows
                    if start <= timestamp(row['available_at']) <= end]
    conservative.sort(key=lambda row: (timestamp(row['event_ts']), row['id']))
    audit = {'received_article_rows': len(articles), 'unique_provider_ids': len(seen),
             'identical_duplicate_rows': duplicate_count, 'outside_publication_window': outside_count,
             'publication_rows': len(rows), 'revised_after_publication': revised_count,
             'midnight_publication_rows': midnight_count, 'conservative_rows': len(conservative),
             'updates_outside_window_excluded_from_conservative': len(rows) - len(conservative),
             'publication_rows_by_year': dict(sorted(Counter(timestamp(row['created_at']).year for row in rows).items())),
             'conservative_rows_by_year': dict(sorted(Counter(timestamp(row['event_ts']).year for row in conservative).items())),
             'first_created_at': rows[0]['created_at'], 'last_created_at': rows[-1]['created_at'],
             'revision_policy': 'Conservative event_ts is max(created_at, updated_at); versions available after the window are excluded.',
             'historical_coverage_exhaustive': False, 'point_in_time_availability_proven': False}
    return rows, conservative, audit


def export_csv(path, rows):
    if path.exists():
        with path.open(encoding='utf-8', newline='') as stream:
            if list(csv.DictReader(stream)) != [{k: str(v) for k, v in row.items()} for row in rows]:
                raise ValueError('Existing derived CSV differs from raw-page replay')
    else:
        with path.open('x', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    return {'path': str(path), 'sha256': digest(path.read_bytes()), 'rows': len(rows)}


def acquire(directory, receipt, *, resume=False, maximum_pages=1000, fetch=probe,
            headers=None, sleeper=time.sleep):
    config = {'schema': 'investify-alpaca-news-snapshot-v1', 'endpoint': URL,
              'params': PARAMS, 'source_sha256': digest(Path(__file__).read_bytes())}
    report = {'schema': 'investify-alpaca-news-acquisition-v1', 'started_utc': now(),
              'snapshot_directory': str(directory), 'config': config, 'resumed': resume,
              'requests_this_invocation': 0, 'fnspid_requests': 0,
              'credential_values_recorded': False, 'routing_settings_changed': False,
              'status': 'started', 'pagination_complete': False,
              'scope': 'Fresh provider snapshot; raw pages and both timestamps preserved. No historical-byte reproduction, model inference or performance claim.'}
    if receipt.exists():
        raise ValueError('Preserve earlier receipts; choose a new filename')
    if resume:
        if json.loads((directory / 'snapshot.json').read_text(encoding='utf-8')) != config:
            raise ValueError('Resume requires the same source and request identity')
    else:
        directory.mkdir(parents=True, exist_ok=False)
        write_new(directory / 'snapshot.json', json_bytes(config))
    try:
        articles, pages, token, complete = replay_pages(directory, config)
        while not complete and len(pages) < maximum_pages:
            params = dict(PARAMS)
            if token is not None:
                params['page_token'] = token
            report['requests_this_invocation'] += 1
            response = fetch({'source': 'Alpaca/Benzinga NVDA', 'url': URL + '?' + urlencode(params),
                              'headers': headers or {}, 'maximum_bytes': 2 * 1024 * 1024})
            if response['status'] != 'response_received' or response.get('http_status') != 200:
                report['provider_failure'] = {key: response[key] for key in
                    ('status', 'http_status', 'winerror', 'provider_diagnostic') if key in response}
                raise ValueError('Provider request failed; durable pages permit resume after resolution')
            raw = response['raw_bytes']
            if any(secret.encode('utf-8') in raw for secret in (headers or {}).values() if secret):
                raise ValueError('Credential redaction check failed; response was not retained')
            payload = json.loads(raw)
            if not isinstance(payload.get('news'), list):
                raise ValueError('Provider response has no news list')
            path = directory / f'page-{len(pages) + 1:06d}.json'
            write_new(path, json_bytes({'request_params': params, 'received_utc': now(),
                      'config_sha256': digest(json_bytes(config)), 'response_sha256': digest(raw),
                      'payload_text': raw.decode('utf-8')}))
            articles, pages, token, complete = replay_pages(directory, config)
            if len(pages) % 20 == 0 or complete:
                print(f'Pages={len(pages)} received_rows={len(articles)} complete={complete}', flush=True)
            if not complete:
                sleeper(0.5)
        report.update(pages=pages, pagination_complete=complete)
        if not complete:
            report['status'] = 'paused_at_page_limit'
        else:
            publication, conservative, audit = audit_articles(articles)
            report.update(status='acquired_and_audited', audit=audit,
                          publication_csv=export_csv(directory / 'publication_time.csv', publication),
                          conservative_csv=export_csv(directory / 'revision_conservative.csv', conservative))
    except (OSError, ValueError, KeyError, TypeError) as error:
        report.update(status='failed', error_type=type(error).__name__,
                      error_message=str(error) if isinstance(error, ValueError) else 'Snapshot processing failed; inspect retained files')
    report['completed_utc'] = now()
    raw_report = json_bytes(report)
    if any(secret.encode('utf-8') in raw_report for secret in (headers or {}).values() if secret):
        raise ValueError('Receipt redaction check failed')
    write_new(receipt, raw_report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--maximum-pages', type=int, default=1000)
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    output, receipt = args.output.resolve(), args.receipt.resolve()
    if not output.is_relative_to(ROOT / 'code/data/raw/snapshots'):
        raise ValueError('New snapshots belong under code/data/raw/snapshots')
    if not receipt.is_relative_to(ROOT / 'evidence/market_reacquisition_20261012'):
        raise ValueError('Use a new receipt under the reacquisition evidence root')
    if not 1 <= args.maximum_pages <= 1000:
        raise ValueError('Maximum pages must be between 1 and 1000')
    if args.plan_only:
        print(json.dumps({'plan_only': True, 'endpoint': URL, 'params': PARAMS,
                          'output': str(output), 'receipt': str(receipt), 'requests': 0}))
        return 0
    values, _ = alpaca_credentials(os.environ, (ROOT / 'code/.env').read_text(encoding='utf-8-sig'))
    if not all(values.values()):
        raise ValueError('Both local Alpaca credentials are required')
    headers = {'APCA-API-KEY-ID': values['ALPACA_API_KEY'],
               'APCA-API-SECRET-KEY': values['ALPACA_API_SECRET']}
    result = acquire(output, receipt, resume=args.resume, maximum_pages=args.maximum_pages, headers=headers)
    print(json.dumps({key: result[key] for key in ('status', 'pagination_complete', 'requests_this_invocation')}, indent=2))
    if 'audit' in result:
        print(json.dumps(result['audit'], indent=2))
    print('Receipt:', receipt)
    return 0 if result['status'] == 'acquired_and_audited' else 2


if __name__ == '__main__':
    raise SystemExit(main())
