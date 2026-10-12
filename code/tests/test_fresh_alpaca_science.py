"""Receipt gate refusals on labelled tiny files; no market/model inference."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_fresh_alpaca_science import verified_inputs, PUBLISHER, REVISION


class FreshScienceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='investify-fresh-admission-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.price = self.root / 'price.json'
        self.news = self.root / 'news.csv'
        self.price.write_bytes(b'LABELLED price byte fixture, not market input')
        self.news.write_bytes(b'LABELLED news byte fixture, not a corpus')
        self.model = self.root / 'model'
        self.model.mkdir()
        files = []
        for name in ('config.json','tokenizer_config.json','special_tokens_map.json','vocab.txt','model.safetensors'):
            path = self.model / name
            path.write_bytes(b'LABELLED counterfeit publisher fixture')
            files.append({'filename': name, 'size_bytes': path.stat().st_size,
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'publisher_identity_verified': True})
        self.prices = {'schema': 'investify-fresh-alpaca-prices-v1',
                       'results': [{'source':'split','http_status':200,'pagination_complete':True,
                                    'response_file':str(self.price),
                                    'response_sha256':hashlib.sha256(self.price.read_bytes()).hexdigest()}]}
        self.news_report = {'status':'acquired_and_audited','pagination_complete':True,
                            'conservative_csv':{'path':str(self.news),'sha256':hashlib.sha256(self.news.read_bytes()).hexdigest()},
                            'audit':{'revision_policy':'LABELLED timing fixture'}}
        self.model_report = {'publisher':PUBLISHER,'revision':REVISION,'status':'downloaded_and_hash_verified',
                             'directory':str(self.model),'files':files}

    def check(self):
        receipts = []
        for name, value in [('price_receipt.json',self.prices),('news_receipt.json',self.news_report),
                            ('model_receipt.json',self.model_report)]:
            path = self.root / name
            path.write_text(json.dumps(value),encoding='utf-8')
            receipts.append(path)
        return verified_inputs(*receipts)

    def test_incomplete_pagination_refused(self):
        self.news_report['pagination_complete'] = False
        with self.assertRaisesRegex(ValueError,'completed'):
            self.check()

    def test_unfinished_news_status_refused(self):
        self.news_report['status'] = 'paused_at_page_limit'
        with self.assertRaisesRegex(ValueError,'completed'):
            self.check()

    def test_mutated_price_bytes_refused(self):
        self.price.write_bytes(b'LABELLED changed price fixture')
        with self.assertRaisesRegex(ValueError,'no longer match'):
            self.check()

    def test_mutated_news_bytes_refused(self):
        self.news.write_bytes(b'LABELLED changed news fixture')
        with self.assertRaisesRegex(ValueError,'no longer match'):
            self.check()

    def test_wrong_publisher_refused(self):
        self.model_report['publisher'] = 'LABELLED/unofficial'
        with self.assertRaisesRegex(ValueError,'original FinBERT'):
            self.check()

    def test_unpinned_revision_refused(self):
        self.model_report['revision'] = 'main'
        with self.assertRaisesRegex(ValueError,'original FinBERT'):
            self.check()

    def test_missing_model_file_refused(self):
        self.model_report['files'].pop()
        with self.assertRaisesRegex(ValueError,'complete five-file'):
            self.check()

    def test_relabelled_model_with_self_consistent_receipt_is_refused(self):
        # Booleans and a valid checksum of unrelated weights cannot establish
        # original-publisher identity.
        with self.assertRaisesRegex(ValueError,'pinned publisher hashes'):
            self.check()


if __name__ == '__main__':
    unittest.main()
