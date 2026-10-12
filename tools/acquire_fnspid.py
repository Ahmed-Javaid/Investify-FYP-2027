"""Acquire original publisher FNSPID CSV bytes without Alpaca credentials.

Default: bounded 1 MiB CSV access sample. --full: resumable publisher download
to E: cache, exact full-file hash verification, then the original ticker subset.
Every acquisition uses a new receipt; no historical input is overwritten.
"""
import argparse
import codecs
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'bf9189c41527198897d1af3e17b1a0095279fc45'
FILE = 'Stock_news/nasdaq_exteral_data.csv'
EXPECTED_SIZE = 23232979597
EXPECTED_SHA256 = '1a7a3eb8e6b97ec19f286f2cfca3371542bddb272ab1eb8f36e33ad98fa5c4da'
URL = f'https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/{REVISION}/{FILE}'
FIELDS = ['Date', 'Article_title', 'Stock_symbol', 'Publisher']
MAX_PREFIX = 1024 * 1024


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def select_rows(reader, writer, tickers=None, max_rows=None):
    header = next(reader)
    indices = {name: header.index(name) for name in FIELDS if name in header}
    if len(indices) != len(FIELDS):
        raise ValueError('Publisher CSV does not have the expected news schema')
    writer.writerow(FIELDS)
    counts = Counter()
    year_counts = {}
    midnight_counts = Counter()
    invalid_dates = Counter()
    scanned = malformed = written = 0
    for row in reader:
        scanned += 1
        if len(row) != len(header):
            malformed += 1
            continue
        chosen = [row[indices[name]] for name in FIELDS]
        if not chosen[0].strip() or not chosen[1].strip() or not chosen[2].strip():
            malformed += 1
            continue
        if tickers is not None and chosen[2] not in tickers:
            continue
        writer.writerow(chosen)
        counts[chosen[2]] += 1
        try:
            date = datetime.strptime(chosen[0], '%Y-%m-%d %H:%M:%S UTC')
            year_counts.setdefault(chosen[2], Counter())[str(date.year)] += 1
            if date.hour == date.minute == date.second == 0:
                midnight_counts[chosen[2]] += 1
        except ValueError:
            invalid_dates[chosen[2]] += 1
        written += 1
        if max_rows is not None and written >= max_rows:
            break
    return {'parsed_rows': scanned, 'malformed_or_missing_rows': malformed,
            'rows_written': written, 'ticker_counts': dict(counts),
            'per_year_counts': {ticker: dict(years) for ticker, years in year_counts.items()},
            'midnight_timestamp_counts': dict(midnight_counts),
            'invalid_timestamp_counts': dict(invalid_dates)}


def prefix_rows(body):
    """Keep complete CSV records; never promote a truncated final row as evidence."""
    decoder = codecs.getincrementaldecoder('utf-8-sig')(errors='strict')
    text = decoder.decode(body, final=False)
    reader = csv.reader(io.StringIO(text, newline=''), strict=True)
    rows = []
    incomplete = False
    try:
        for row in reader:
            rows.append(row)
    except csv.Error as error:
        if 'unexpected end of data' not in str(error):
            raise
        incomplete = True
    if not incomplete and text and not text.endswith(('\n', '\r')):
        if len(rows) > 1:
            rows.pop()
        incomplete = True
    return rows, incomplete


def full_source(cache):
    cache = cache.resolve()
    if not cache.is_relative_to(Path('E:/AI-Tools/Cache').resolve()):
        raise ValueError('Full source cache must remain under E:/AI-Tools/Cache')
    cache.mkdir(parents=True, exist_ok=True)
    final = cache / 'nasdaq_exteral_data.csv'
    partial = cache / 'nasdaq_exteral_data.csv.part'
    if final.exists():
        if final.stat().st_size != EXPECTED_SIZE or sha(final) != EXPECTED_SHA256:
            raise ValueError('Existing publisher cache fails its expected size/hash; preserve it for diagnosis')
        return final
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > EXPECTED_SIZE:
        raise ValueError('Existing partial cache exceeds the publisher size')
    if shutil.disk_usage(cache).free < EXPECTED_SIZE - offset + 32 * 1024 * 1024:
        raise ValueError('Insufficient free E: cache space for the remaining publisher bytes')
    if offset < EXPECTED_SIZE:
        headers = {'Accept-Encoding': 'identity', 'User-Agent': 'Investify-academic-acquisition/1.0'}
        if offset:
            headers['Range'] = f'bytes={offset}-'
        with urlopen(Request(URL, headers=headers), timeout=60) as response:
            if offset and (response.status != 206 or not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-')):
                raise ValueError('Provider did not honor exact resume offset; existing partial bytes are preserved')
            if not offset and response.status != 200:
                raise ValueError('Expected a complete original publisher response')
            started, last_progress = time.monotonic(), 0.0
            with partial.open('ab' if partial.exists() else 'xb') as stream:
                total = offset
                while total < EXPECTED_SIZE:
                    block = response.read(min(1024 * 1024, EXPECTED_SIZE - total))
                    if not block:
                        raise ValueError('Publisher transfer ended early; rerun --full to resume the retained partial cache')
                    stream.write(block)
                    total += len(block)
                    elapsed = time.monotonic() - started
                    if elapsed - last_progress >= 10:
                        print(f'FNSPID transfer: {total / 1e9:.2f}/{EXPECTED_SIZE / 1e9:.2f} GB', flush=True)
                        last_progress = elapsed
                if response.read(1):
                    raise ValueError('Publisher response exceeds its pinned size')
    if partial.stat().st_size != EXPECTED_SIZE or sha(partial) != EXPECTED_SHA256:
        raise ValueError('Publisher full-file size/hash mismatch; the partial cache is retained and not accepted')
    partial.rename(final)
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true', help='Download/verify the 23.2 GB publisher file and extract AAPL/NVDA/TSLA')
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--tickers', default='AAPL,NVDA,TSLA')
    parser.add_argument('--cache', type=Path, default=Path('E:/AI-Tools/Cache/FNSPID') / EXPECTED_SHA256)
    args = parser.parse_args()
    tickers = set(args.tickers.split(','))
    if not tickers or any(not re.fullmatch(r'[A-Z][A-Z0-9.]{0,9}', ticker) for ticker in tickers):
        raise ValueError('Supply explicit comma-separated stock symbols')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'evidence/market_reacquisition_20261012' / ('fnspid_' + stamp)
    report = {'schema': 'investify-fnspid-acquisition-v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'publisher_revision': REVISION, 'publisher_file': FILE, 'url': URL,
              'expected_full_size': EXPECTED_SIZE, 'expected_full_sha256': EXPECTED_SHA256,
              'mode': 'full_verified_subset' if args.full else 'bounded_csv_sample',
              'alpaca_credentials_used': False, 'maximum_sample_bytes': MAX_PREFIX if not args.full else None,
              'full_source_hash_verified': False, 'usable_for_nvda_pipeline': False,
              'intraday_timestamp_quality_verified': False,
              'intended_role': 'Restore the original NVDA FNSPID baseline, not replace the precise-timestamp corpus',
              'known_original_limitations': 'AAPL/TSLA missing years; sparse NVDA daily news; about 99.78% NVDA midnight-defaulted timestamps. Publication-timing claims require a separate validated corpus.',
              'historical_inputs_overwritten': False, 'requested_tickers': sorted(tickers)}
    if args.plan_only:
        report.update(plan_only=True, requests_executed=0)
        print(json.dumps(report, indent=2))
        return 0
    output.mkdir(parents=True, exist_ok=False)
    receipt = output / 'receipt.json'
    report['status'] = 'started'
    def save():
        receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')
    save()
    csv.field_size_limit(64 * 1024 * 1024)
    try:
        if args.full:
            source = full_source(args.cache)
            before = source.stat()
            target = ROOT / 'code/data/raw/fnspid_reacquired' / stamp / 'fnspid_aapl_nvda_tsla.csv'
            target.parent.mkdir(parents=True, exist_ok=False)
            with source.open('r', encoding='utf-8-sig', newline='') as stream, target.open('x', encoding='utf-8', newline='') as destination:
                counts = select_rows(csv.reader(stream, strict=True), csv.writer(destination, lineterminator='\n'), tickers)
            after = source.stat()
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns or sha(source) != EXPECTED_SHA256:
                raise ValueError('Verified source changed during extraction')
            if counts['rows_written'] == 0:
                raise ValueError('No requested ticker rows extracted from the verified source')
            nvda_years = set(counts['per_year_counts'].get('NVDA', {}))
            report.update(full_source_hash_verified=True, full_source_cache=str(source),
                          usable_for_nvda_pipeline=set(map(str, range(2018, 2024))).issubset(nvda_years) and not counts['invalid_timestamp_counts'].get('NVDA', 0),
                          status='verified_full_source_subset')
        else:
            headers = {'Range': f'bytes=0-{MAX_PREFIX - 1}', 'Accept-Encoding': 'identity',
                       'User-Agent': 'Investify-academic-acquisition/1.0'}
            with urlopen(Request(URL, headers=headers), timeout=30) as response:
                report['http_status'] = response.status
                report['content_range'] = response.headers.get('Content-Range')
                if response.status not in (200, 206):
                    raise ValueError('Unexpected publisher response')
                if response.status == 206 and not (report['content_range'] or '').startswith('bytes 0-'):
                    raise ValueError('Provider returned a non-prefix range')
                body = response.read(MAX_PREFIX)
            prefix = output / 'publisher_prefix.csv.part'
            prefix.write_bytes(body)
            rows, incomplete = prefix_rows(body)
            target = output / 'complete_sample_rows.csv'
            with target.open('x', encoding='utf-8', newline='') as destination:
                counts = select_rows(iter(rows), csv.writer(destination, lineterminator='\n'), max_rows=100)
            if counts['rows_written'] == 0:
                raise ValueError('No complete news records in the bounded publisher CSV sample')
            report.update(prefix_bytes=len(body), prefix_sha256=hashlib.sha256(body).hexdigest(),
                          incomplete_final_record_excluded=incomplete, status='actual_csv_access_sampled',
                          scope='Bounded original CSV access sample, potentially other tickers; not full NVDA coverage or pipeline restoration.')
        report.update(counts=counts, extracted_csv=str(target.relative_to(ROOT)), extracted_csv_sha256=sha(target),
                      finished_utc=datetime.now(timezone.utc).isoformat())
        save()
        print(json.dumps(report, indent=2))
        print('Receipt:', receipt)
        return 0
    except (OSError, ValueError, csv.Error, UnicodeError, StopIteration) as error:
        report.update(status='failed_incomplete', error_type=type(error).__name__, detail=str(error)[:1024],
                      finished_utc=datetime.now(timezone.utc).isoformat())
        save()
        print(json.dumps(report, indent=2))
        print('Next step: run in normal PowerShell; for a paused full transfer rerun --full to resume cached publisher bytes.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
