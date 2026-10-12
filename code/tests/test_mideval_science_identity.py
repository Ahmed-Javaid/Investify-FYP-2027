"""Read-only science identity fixtures, not original scientific inputs."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.science_identity import input_snapshots, run_identity


class ScienceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='investify-identity-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('prices', 'news'):
            folder = self.root / 'store' / name / 'ticker=FIXTURE'
            folder.mkdir(parents=True)
            (folder / 'fixture.parquet').write_bytes(b'LABELLED hash fixture, not valid market Parquet')
        (self.root / 'cache').mkdir()
        (self.root / 'cache/finbert_scores.parquet').write_bytes(b'LABELLED score-hash fixture')
        (self.root / 'artifacts').mkdir()
        (self.root / 'artifacts/corpus_manifest.json').write_text('{"purpose":"LABELLED fixture"}')
        self.cfg = {'tickers': ['FIXTURE'], 'paths': {'store': str(self.root / 'store'), 'artifacts': str(self.root / 'artifacts')},
                    'news': {'extracted_path': str(self.root / 'absent-original-fixture.csv')},
                    'sentiment': {'cache_dir': str(self.root / 'cache')},
                    'corpora': {'fnspid': {'loader': 'fnspid'}}}

    def test_snapshot_identity_changes_when_consumed_cache_bytes_change(self):
        before = input_snapshots(self.cfg, 'fnspid')
        (self.root / 'cache/finbert_scores.parquet').write_bytes(b'LABELLED changed cache')
        after = input_snapshots(self.cfg, 'fnspid')
        self.assertNotEqual(before['sentiment_scores'], after['sentiment_scores'])
        self.assertEqual(before['prices'], after['prices'])

    def test_config_and_complete_source_closure_are_in_the_run_identity(self):
        before = run_identity(self.cfg, 'fnspid')
        cfg = copy.deepcopy(self.cfg)
        cfg['calibration_mode'] = 'frozen_classifier'
        after = run_identity(cfg, 'fnspid')
        self.assertNotEqual(before['identity_sha256'], after['identity_sha256'])
        for name in ('calibration_split.py', 'features/indicators.py', 'features/assembly.py', 'scaling.py', 'news_cache.py'):
            self.assertIn('src/investify/' + name, before['source_sha256'])
        self.assertIsNotNone(before['input_snapshots'])
        for name in ('src/investify/harness/run_spike.py', 'scripts/build_decision_records.py'):
            self.assertIn(name, before['source_sha256'])

    def test_raw_subset_absence_and_manifest_mutation_are_explicit_identity_changes(self):
        before = run_identity(self.cfg, 'fnspid')
        self.assertEqual(before['input_snapshots']['declared_raw_subset']['status'], 'missing')
        Path(self.cfg['news']['extracted_path']).write_bytes(b'LABELLED restored original')
        restored = run_identity(self.cfg, 'fnspid')
        self.assertNotEqual(before['identity_sha256'], restored['identity_sha256'])
        (self.root / 'artifacts/corpus_manifest.json').write_text('{"purpose":"LABELLED changed fixture"}')
        changed = run_identity(self.cfg, 'fnspid')
        self.assertNotEqual(restored['identity_sha256'], changed['identity_sha256'])

    def test_missing_input_snapshots_are_not_assigned_invented_hashes(self):
        cfg = copy.deepcopy(self.cfg)
        cfg['sentiment']['cache_dir'] = str(self.root / 'absent')
        with self.assertRaises(FileNotFoundError):
            input_snapshots(cfg, 'fnspid')
