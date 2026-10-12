"""Structural preflight fixtures never stand in for actual scientific inputs."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from investify.demo_readiness import RUNTIME_MODULES, harness_input_report, harness_missing_inputs


class MidEvalReadinessTests(unittest.TestCase):
    CFG = {'tickers': ['NVDA'], 'paths': {'store': 'data/store'},
           'sentiment': {'cache_dir': '.cache/finbert_scores'},
           'corpora': {'alpaca': {'loader': 'alpaca', 'path': 'data/raw/alpaca_nvda_news.csv'},
                       'fnspid': {'loader': 'fnspid'}}}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='investify-readiness-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_fixture(self, relative, data=b'PAR1labelled boundary fixture, not real ParquetPAR1'):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def complete_fixtures(self):
        self.write_fixture('data/store/prices/ticker=NVDA/date=2023-01-01/part.parquet')
        self.write_fixture('.cache/finbert_scores/finbert_scores.parquet')
        self.write_fixture('data/store/news/ticker=NVDA/date=2023-01-01/part.parquet')
        self.write_fixture('data/raw/alpaca_nvda_news.csv', b'headline\nLABELLED FIXTURE\n')

    def report(self, corpus='fnspid'):
        with patch('investify.demo_readiness.find_spec', return_value=object()):
            return harness_input_report(self.CFG, corpus, self.root)

    def test_missing_data_and_runtime_are_reported_for_each_corpus(self):
        with patch('investify.demo_readiness.find_spec', return_value=None):
            for corpus in ('alpaca', 'fnspid'):
                missing = harness_missing_inputs(self.CFG, corpus, self.root)
                self.assertEqual(len(missing), 3 + len(RUNTIME_MODULES))
                self.assertTrue(any('finbert_scores.parquet' in item for item in missing))
                self.assertIn('runtime module: xgboost', missing)

    def test_empty_partition_directories_do_not_enable_a_rerun(self):
        for folder in ('prices', 'news'):
            (self.root / f'data/store/{folder}/ticker=NVDA').mkdir(parents=True)
        report = self.report()
        self.assertFalse(report['preflight_passed'])
        self.assertEqual([row['status'] for row in report['inputs']], ['empty', 'missing', 'empty'])

    def test_present_boundary_fixtures_pass_only_the_structural_preflight(self):
        self.complete_fixtures()
        for corpus in ('alpaca', 'fnspid'):
            report = self.report(corpus)
            self.assertTrue(report['preflight_passed'])
            self.assertFalse(report['scientific_run_executed'])
            self.assertIn('no dataset row/schema/cache-coverage validation', report['scope'])
            self.assertEqual([row['files_checked'] for row in report['inputs']], [1, 1, 1])

    def test_zero_byte_csv_and_cache_are_blocked(self):
        self.complete_fixtures()
        self.write_fixture('data/raw/alpaca_nvda_news.csv', b'')
        self.write_fixture('.cache/finbert_scores/finbert_scores.parquet', b'')
        report = self.report('alpaca')
        self.assertFalse(report['preflight_passed'])
        self.assertEqual([row['status'] for row in report['inputs']], ['available', 'empty', 'empty'])

    def test_truncated_cache_and_invalid_header_are_blocked(self):
        self.complete_fixtures()
        for data in (b'PAR1truncated', b'wrong headerPAR1', b'PAR1PAR1'):
            self.write_fixture('.cache/finbert_scores/finbert_scores.parquet', data)
            report = self.report()
            self.assertFalse(report['preflight_passed'])
            self.assertEqual(report['inputs'][1]['status'], 'invalid_format')

    def test_one_bad_partition_blocks_an_otherwise_nonempty_dataset(self):
        self.complete_fixtures()
        self.write_fixture('data/store/prices/ticker=NVDA/date=2023-01-02/part.parquet', b'corrupt fixture')
        report = self.report()
        self.assertFalse(report['preflight_passed'])
        self.assertEqual(report['inputs'][0]['status'], 'invalid_format')

    def test_wrong_path_types_are_reported(self):
        self.write_fixture('data/store/prices/ticker=NVDA')
        (self.root / '.cache/finbert_scores/finbert_scores.parquet').mkdir(parents=True)
        report = self.report()
        self.assertEqual([row['status'] for row in report['inputs']], ['wrong_type', 'wrong_type', 'missing'])

    def test_permission_failure_keeps_the_rerun_disabled(self):
        self.complete_fixtures()
        with patch.object(Path, 'open', side_effect=PermissionError('LABELLED read-denial fixture')):
            report = self.report()
        self.assertFalse(report['preflight_passed'])
        self.assertTrue(all(row['status'] == 'unreadable' for row in report['inputs']))

    def test_broken_module_discovery_is_a_blocker_instead_of_an_exception(self):
        self.complete_fixtures()
        with patch('investify.demo_readiness.find_spec', side_effect=ValueError('LABELLED invalid spec')):
            report = harness_input_report(self.CFG, 'fnspid', self.root)
        self.assertFalse(report['preflight_passed'])
        self.assertEqual(len(report['blockers']), len(RUNTIME_MODULES))
        self.assertTrue(all('ValueError' in row['detail'] for row in report['runtime']))

    def test_unknown_loader_cannot_be_treated_as_alpaca(self):
        cfg = {**self.CFG, 'corpora': {'unknown': {'loader': 'unsupported', 'path': 'fixture.csv'}}}
        with self.assertRaisesRegex(ValueError, 'Unknown news loader'):
            harness_input_report(cfg, 'unknown', self.root)
