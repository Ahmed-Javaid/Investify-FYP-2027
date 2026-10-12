"""Read-only paper-account/news authentication diagnosis; never retain account details."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from probe_market_reacquisition import ROOT, alpaca_credentials, probe


def interpretation(results):
    by_name = {row['source']: row for row in results}
    account, news = by_name['Paper account'], by_name['Market news']
    account_ok = account['status'] == 'response_received' and account.get('http_status') == 200
    news_ok = news['status'] == 'response_received' and news.get('http_status') == 200
    if account_ok and news_ok:
        return 'paper_and_news_access_verified', 'The pair works for this paper account and bounded news request. Continue acquisition under a new snapshot identity.'
    if account_ok:
        return 'paper_credentials_accepted_news_unresolved', 'The paper key pair is accepted. Investigate the news response and data/account access; key validity is established for the paper account.'
    if news_ok:
        return 'news_access_verified_paper_unresolved', 'The pair works for market news. Check that it belongs to this paper account before using the paper trading host.'
    if any(row['status'] == 'connection_failed' for row in results):
        return 'network_prevents_complete_diagnosis', 'Run in normal network-enabled PowerShell. Check its expected proxy/VPN configuration if connections also fail there.'
    if all(row.get('http_status') in (401, 403) for row in results):
        return 'credentials_or_account_rejected', 'Review the redacted provider error code/message and request ID. Audit parsing, endpoint and request headers against an independent client before changing credentials. Continue the original NVDA FNSPID baseline independently; it does not replace the precise-timestamp experiment.'
    return 'provider_responses_need_review', 'Review both endpoint statuses. Rate limits or provider failures require a delayed retry; an authentication rejection requires checking the matching key pair/account.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'evidence/market_reacquisition_20261012') or output.exists():
        raise ValueError('Reserve a new directory under the declared reacquisition evidence root')
    urls = [('Paper account', 'https://paper-api.alpaca.markets/v2/account'),
            ('Market news', 'https://data.alpaca.markets/v1beta1/news?symbols=NVDA&limit=1&include_content=false')]
    if args.plan_only:
        print(json.dumps({'plan_only': True, 'method': 'GET', 'endpoints': urls,
                          'account_data_saved': False, 'credential_values_recorded': False,
                          'requests_executed': 0}))
        return 0
    env_file = ROOT / 'code/.env'
    values, origins = alpaca_credentials(os.environ, env_file.read_text(encoding='utf-8-sig') if env_file.is_file() else '')
    if not all(values.values()):
        raise ValueError('Set both declared Alpaca keys in code/.env before this authentication check')
    headers = {'APCA-API-KEY-ID': values['ALPACA_API_KEY'],
               'APCA-API-SECRET-KEY': values['ALPACA_API_SECRET'], 'Accept': 'application/json'}
    specs = [{'source': name, 'url': url, 'headers': headers, 'maximum_bytes': 128 * 1024}
             for name, url in urls]
    with ThreadPoolExecutor(max_workers=2) as pool:
        raw_results = list(pool.map(probe, specs))
    results = []
    for row in raw_results:
        # Even successful account/news response bytes are discarded, not written to a receipt.
        row.pop('raw_bytes', None)
        keep = ('source', 'url', 'status', 'http_status', 'winerror', 'elapsed_seconds', 'provider_diagnostic')
        results.append({key: row[key] for key in keep if key in row})
    status, next_step = interpretation(results)
    report = {'schema': 'investify-paper-news-auth-diagnosis-v1',
              'checked_utc': datetime.now(timezone.utc).isoformat(),
              'credential_sources': origins, 'credential_values_recorded': False,
              'account_data_saved': False, 'requests_executed': len(results),
              'results': results, 'status': status, 'next_step': next_step,
              'scope': 'Two read-only provider requests. No trading, settings changes, raw account data, historical coverage or scientific run.'}
    output.mkdir(parents=True)
    with (output / 'probe.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    print('Receipt:', output / 'probe.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
