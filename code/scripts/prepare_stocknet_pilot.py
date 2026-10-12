"""Prepare a declared real StockNet pilot from preserved author-released files.

No network, labels or price data. Original tweet text/ID/timestamp are retained.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.sentiment_selection import PROTOCOL, digest


def prepare(declaration, manifest, source_root):
    selection = declaration['selection']
    if (declaration['protocol'] != PROTOCOL or selection['annotation_method'] != 'model_generated'
            or selection['target_tickers'] != ['MSFT']
            or manifest['revision'] != declaration['source']['revision']):
        raise ValueError('Source identity or predeclared pilot target changed')
    acquired = datetime.fromisoformat(manifest['completed_utc'].replace('Z', '+00:00'))
    if datetime.fromisoformat(selection['declared_at_utc'].replace('Z', '+00:00')) > acquired:
        raise ValueError('Sampling declaration must precede acquisition')
    start = datetime.fromisoformat(selection['window_start_utc'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(selection['window_end_utc'].replace('Z', '+00:00'))
    selected, rejected, files = [], [], []
    ids, contents = set(), set()
    for entry in sorted(manifest['files'], key=lambda x: x['path']):
        relative = Path(entry['path'])
        if relative.parts[:3] != ('tweet', 'raw', 'MSFT') or len(relative.parts) != 4:
            raise ValueError('Unexpected source path')
        raw = (source_root / 'raw' / 'MSFT' / relative.name).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if blob != entry['git_blob_sha']:
            raise ValueError('Preserved source bytes do not match the fetched GitHub blob')
        files.append({'path': entry['path'], 'git_blob_sha': blob, 'sha256': hashlib.sha256(raw).hexdigest()})
        daily = []
        for line_number, line in enumerate(raw.decode('utf-8').splitlines(), 1):
            item = json.loads(line)
            identifier, text = item.get('id_str'), item.get('text')
            try:
                published = parsedate_to_datetime(item['created_at'])
            except (KeyError, TypeError, ValueError):
                rejected.append({'path': entry['path'], 'line': line_number, 'reason': 'missing/invalid source timestamp'})
                continue
            if (not isinstance(identifier, str) or not identifier.isdigit()
                    or not isinstance(text, str) or not text.strip()
                    or published.utcoffset() is None or published.utcoffset().total_seconds() != 0
                    or not start <= published <= end):
                rejected.append({'path': entry['path'], 'line': line_number, 'post_id': identifier,
                                 'reason': 'missing identifier/text, non-UTC timestamp or outside declared window'})
                continue
            # Source retweets/truncated text remain exact; no link hydration or nested-text substitution.
            daily.append({'post_id': identifier, 'source': 'StockNet author-released Twitter raw corpus',
                          'source_kind': 'x', 'source_url': f'https://twitter.com/i/web/status/{identifier}',
                          'published_at_utc': published.isoformat(), 'ticker': 'MSFT', 'text': text,
                          'source_file': entry['path'], 'source_line': line_number,
                          'source_revision': manifest['revision'], 'source_blob_sha': blob,
                          'source_text_truncated': item.get('truncated'),
                          'is_retweet': 'retweeted_status' in item})
        for post in sorted(daily, key=lambda x: (x['published_at_utc'], x['post_id'])):
            content = ' '.join(post['text'].split()).casefold()
            if post['post_id'] in ids or content in contents:
                rejected.append({'post_id': post['post_id'], 'path': entry['path'], 'reason': 'duplicate ID or target/text'})
                continue
            ids.add(post['post_id'])
            contents.add(content)
            if len(selected) < 200:
                selected.append(post)
            else:
                rejected.append({'post_id': post['post_id'], 'path': entry['path'], 'reason': 'after predeclared first-200 cutoff'})
    if len(selected) != 200:
        raise ValueError('Actual preserved files do not contain the declared 200 unique posts')
    corpus = {'protocol': PROTOCOL, 'selection': dict(selection, acquired_at_utc=manifest['completed_utc']),
              'posts': selected}
    receipt = {'prepared_utc': datetime.now(timezone.utc).isoformat(), 'status': 'prepared_unannotated',
               'corpus_sha256': digest(corpus), 'declaration_sha256': digest(declaration),
               'source_manifest_sha256': digest(manifest), 'acquired_selected_posts': len(selected),
               'source_files': files, 'preparation_exclusions': rejected,
               'label_or_candidate_filtering': False, 'annotations_created': 0,
               'source_scope': 'Historical MSFT tweets from the released corpus, not a fresh platform scrape. Live source availability and pretrained-corpus overlap are unverified.'}
    return corpus, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', required=True, type=Path)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--receipt-output', required=True, type=Path)
    args = parser.parse_args()
    declaration = json.loads(args.declaration.read_text(encoding='utf-8'))
    manifest = json.loads((args.source_root / 'acquisition_manifest.json').read_text(encoding='utf-8'))
    corpus, receipt = prepare(declaration, manifest, args.source_root)
    for path, value in ((args.output, corpus), (args.receipt_output, receipt)):
        if path.exists():
            raise ValueError('Preserve existing research artifacts; choose a new output filename')
    for path, value in ((args.output, corpus), (args.receipt_output, receipt)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(f'Prepared {len(corpus["posts"])} real posts; no annotations or candidate inference')


if __name__ == '__main__':
    main()
