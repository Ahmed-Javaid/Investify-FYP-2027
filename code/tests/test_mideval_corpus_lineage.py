"""Manifest path and moved-copy byte identity fixtures, no original data."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.corpus_lineage import recorded_hash, resolve_lineage


class CorpusLineageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='investify-lineage-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / 'project/data/raw/fixture.csv'
        self.original.parent.mkdir(parents=True)
        self.raw = b'LABELLED raw subset identity fixture\n'
        self.original.write_bytes(self.raw)
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.manifest = {'subsets': [{'path': 'data/raw/fixture.csv', 'sha256': self.digest}]}

    def test_relative_manifest_matches_absolute_effective_configuration(self):
        self.assertEqual(recorded_hash(self.manifest, self.original, project_base=self.root / 'project'), self.digest)
        self.assertEqual(resolve_lineage(self.manifest, self.original, project_base=self.root / 'project')['status'],
                         'original_raw_subset_bytes_verified')

    def test_external_moved_copy_is_identified_by_original_bytes_not_name(self):
        moved = self.root / 'restore/different_name.csv'
        moved.parent.mkdir()
        moved.write_bytes(self.raw)
        result = resolve_lineage(self.manifest, moved, project_base=self.root / 'project')
        self.assertEqual(result['actual_raw_subset_sha256'], self.digest)

    def test_tampered_absolute_or_external_copy_is_refused(self):
        self.original.write_bytes(b'LABELLED wrong bytes')
        with self.assertRaisesRegex(ValueError, 'preserved manifest'):
            resolve_lineage(self.manifest, self.original, project_base=self.root / 'project')
        moved = self.root / 'fixture.csv'
        moved.write_bytes(b'LABELLED same filename, different bytes')
        with self.assertRaisesRegex(ValueError, 'original raw-subset'):
            resolve_lineage(self.manifest, moved, project_base=self.root / 'project')

    def test_absent_original_is_declared_only_but_absent_external_cannot_borrow_identity(self):
        self.original.unlink()
        result = resolve_lineage(self.manifest, self.original, project_base=self.root / 'project')
        self.assertIsNone(result['actual_raw_subset_sha256'])
        self.assertEqual(result['status'], 'declared_only_original_raw_subset_missing')
        with self.assertRaises(FileNotFoundError):
            resolve_lineage(self.manifest, self.root / 'restore/fixture.csv', project_base=self.root / 'project')
