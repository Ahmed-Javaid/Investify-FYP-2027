"""Bounded normal-network probes of the three declared market-data sources.

Uses inherited urllib routing/proxies unchanged, without retries, package
installation or a large corpus transfer. Newly received bytes are retained
separately; they never become historical/frozen evidence automatically.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, getproxies, urlopen

ROOT = Path(__file__).resolve().parents[1]
START = 1514764800  # 2018-01-01T00:00:00Z
END = 1704067200  # 2024-01-01T00:00:00Z, exclusive


def alpaca_credentials(environment, env_text):
    """Read only the declared key pair; never log values or change the environment."""
    names = ('ALPACA_API_KEY', 'ALPACA_API_SECRET')
    values = {name: environment.get(name, '').strip() for name in names}
    origins = {name: 'inherited_environment' if values[name] else 'missing' for name in names}
    for line in env_text.splitlines():
        line = line.strip()
        if line.startswith('export '):
            line = line[7:].lstrip()
        name, separator, value = line.partition('=')
        name = name.strip()
        if not separator or name not in names or values[name]:
            continue
        value = value.strip()
        if value.startswith(('"', "'")):
            quote = value[0]
            closing = value.find(quote, 1)
            if closing < 0 or (value[closing + 1:].strip() and not value[closing + 1:].strip().startswith('#')):
                raise ValueError('Malformed quoted Alpaca credential in local .env; values are not logged')
            value = value[1:closing]
        else:
            value = value.partition(' #')[0].rstrip()
        values[name] = value
        origins[name] = 'local_env_file' if value else 'missing'
    return values, origins


def probe(specification):
    started = time.monotonic()
    row = {key: value for key, value in specification.items() if key != 'headers'}
    row.update(status='not_started', response_bytes=0, raw_bytes=None)
    try:
        request = Request(row['url'], headers=specification.get('headers', {}))
        with urlopen(request, timeout=8) as response:
            body = response.read(row['maximum_bytes'] + 1)
            row.update(http_status=response.status, response_bytes=len(body),
                       content_type=response.headers.get('Content-Type'),
                       content_length=response.headers.get('Content-Length'),
                       etag=response.headers.get('ETag'), repo_commit=response.headers.get('X-Repo-Commit'))
        if len(body) > row['maximum_bytes']:
            row.update(status='bounded_response_limit_exceeded', response_sha256=hashlib.sha256(body).hexdigest())
        else:
            row.update(status='response_received', response_sha256=hashlib.sha256(body).hexdigest(), raw_bytes=body)
    except HTTPError as error:
        row.update(status='http_error', http_status=error.code,
                   error_type=type(error).__name__, detail='Provider rejected the normal inherited-network request')
    except (URLError, OSError, TimeoutError) as error:
        reason = getattr(error, 'reason', error)
        row.update(status='connection_failed', error_type=type(error).__name__, reason_type=type(reason).__name__,
                   errno=getattr(reason, 'errno', None), winerror=getattr(reason, 'winerror', None),
                   detail='Normal inherited-network request failed; no proxy, routing or security setting was changed')
    row['elapsed_seconds'] = round(time.monotonic() - started, 3)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New dated directory beneath the authorized reacquisition evidence root')
    args = parser.parse_args()
    output = args.output.resolve()
    allowed = ROOT / 'evidence/market_reacquisition_20261012'
    if not output.is_relative_to(allowed) or output.exists():
        raise ValueError('Choose a new directory within evidence/market_reacquisition_20261012')
    env_file = ROOT / 'code/.env'
    credentials, origins = alpaca_credentials(os.environ, env_file.read_text(encoding='utf-8-sig') if env_file.is_file() else '')
    keys_present = all(credentials.values())
    alpaca_headers = ({'APCA-API-KEY-ID': credentials['ALPACA_API_KEY'],
                       'APCA-API-SECRET-KEY': credentials['ALPACA_API_SECRET']} if keys_present else {})
    specifications = [
        {'source': 'Yahoo Finance', 'purpose': 'Bounded genuine NVDA daily-price snapshot request, not yfinance execution',
         'url': 'https://query1.finance.yahoo.com/v8/finance/chart/NVDA?' + urlencode(
             {'period1': START, 'period2': END, 'interval': '1d', 'events': 'div,splits', 'includeAdjustedClose': 'true'}),
         'maximum_bytes': 1024 * 1024},
        {'source': 'Author-released FNSPID', 'purpose': 'Publisher dataset revision/file metadata only; no 23GB CSV transfer',
         'url': 'https://huggingface.co/api/datasets/Zihan1004/FNSPID?blobs=true', 'maximum_bytes': 256 * 1024},
        {'source': 'Alpaca/Benzinga', 'purpose': 'Bounded declared historical news endpoint access check',
         'url': 'https://data.alpaca.markets/v1beta1/news?' + urlencode(
             {'symbols': 'NVDA', 'start': '2018-01-01T00:00:00Z', 'end': '2023-12-31T23:59:59Z',
              'limit': 1, 'sort': 'asc', 'include_content': 'false'}),
         'headers': alpaca_headers, 'maximum_bytes': 128 * 1024},
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(probe, specifications))
    output.mkdir(parents=True)
    for index, row in enumerate(responses):
        body = row.pop('raw_bytes')
        if body is not None:
            path = output / f'source-{index + 1:02d}-response.json'
            with path.open('xb') as stream:
                stream.write(body)
            row['received_bytes_file'] = str(path.relative_to(ROOT))
            try:
                payload = json.loads(body)
                if row['source'] == 'Author-released FNSPID':
                    row['publisher_revision'] = payload.get('sha')
                    row['publisher_file_metadata'] = [file for file in payload.get('siblings', [])
                                                     if file.get('rfilename') in ('README.md', 'Stock_news/nasdaq_exteral_data.csv')]
                    row['metadata_is_not_downloaded_corpus_verification'] = True
                elif row['source'] == 'Yahoo Finance':
                    results = payload.get('chart', {}).get('result') or []
                    row['provider_error'] = payload.get('chart', {}).get('error')
                    row['provider_symbol'] = results[0].get('meta', {}).get('symbol') if len(results) == 1 else None
                    row['reported_daily_bars'] = len(results[0].get('timestamp') or []) if len(results) == 1 else 0
                    row['snapshot_is_new_not_original_yfinance_reproduction'] = True
                else:
                    row['received_articles'] = len(payload.get('news') or [])
                    row['has_more_pages'] = bool(payload.get('next_page_token'))
            except (ValueError, TypeError):
                row['json_valid'] = False
    report = {'schema': 'investify-declared-market-source-probe-v1', 'checked_utc': datetime.now(timezone.utc).isoformat(),
              'source_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'declared_manifest_sha256': hashlib.sha256((ROOT / 'code/artifacts/corpus_manifest.json').read_bytes()).hexdigest(),
              'normal_configured_proxy_present': bool(getproxies()), 'routing_or_proxy_settings_changed': False,
              'credentials': {'alpaca_pair_present': keys_present,
                              'alpaca_inherited_environment_pair_present': all(origin == 'inherited_environment' for origin in origins.values()),
                              'credential_sources': origins, 'local_env_file_present': env_file.is_file(),
                              'credential_values_recorded': False},
              'results': responses, 'large_corpus_transfer_attempted': False,
              'scope': 'Actual current bounded normal-network attempts. Source metadata/public response bytes are not '
                       'a historical reproduction, complete news acquisition, trained-model execution or scientific result.'}
    with (output / 'probe.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
    print(json.dumps({'receipt': str(output / 'probe.json'),
                      'results': [{'source': row['source'], 'status': row['status'],
                                   'http_status': row.get('http_status'), 'winerror': row.get('winerror')} for row in responses]}))


if __name__ == '__main__':
    main()
