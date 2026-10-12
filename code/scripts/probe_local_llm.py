"""Read local model availability without loading/downloading a model or generating."""
import argparse
import http.client
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investify.explain.local_llm import ExplainerConfig


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:1234/v1')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = ExplainerConfig(base_url=args.base_url, timeout_seconds=2,
                             api_key=os.environ.get('INVESTIFY_LLM_API_KEY') or None)
    url = urlsplit(config.base_url)
    connection_type = http.client.HTTPSConnection if url.scheme == 'https' else http.client.HTTPConnection
    connection = connection_type(url.hostname, url.port, timeout=2)
    report = {'checked_utc': datetime.now(timezone.utc).isoformat(), 'base_url': config.base_url,
              'models': [], 'real_completions': 0, 'quality_metrics': None,
              'scope': 'Read-only local model list; no load, download, or inference request'}
    try:
        headers = {'Authorization': 'Bearer ' + config.api_key} if config.api_key else {}
        connection.request('GET', url.path.rstrip('/') + '/models', headers=headers)
        response = connection.getresponse()
        body = response.read(65537)
        if response.status != 200 or len(body) > 65536:
            raise ValueError(f'Local model list unavailable (HTTP {response.status})')
        data = json.loads(body)
        models = data['data']
        if not isinstance(models, list):
            raise ValueError('Local provider returned an invalid model list')
        report.update(status='available', models=[m['id'] for m in models
                      if isinstance(m, dict) and isinstance(m.get('id'), str)],
                      reason='Model identifiers returned; generation capability still untested')
    except (OSError, ValueError, KeyError, http.client.HTTPException) as error:
        report.update(status='unavailable', reason=f'{type(error).__name__}: {error}')
    finally:
        connection.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"{report['status']}: {len(report['models'])} local model identifiers; no generations")
