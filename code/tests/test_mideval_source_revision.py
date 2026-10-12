"""Labelled provenance fixtures and a real ancestor-checkout regression."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.source_revision import source_revision


class SourceRevisionTests(unittest.TestCase):
    def manifest(self, root):
        path = root / 'labelled_fixture.txt'
        path.write_text('Labelled source-bundle unit fixture, not real revision evidence.')
        return {'schema': 'investify-source-revision-v1', 'commit': 'a' * 40,
                'files': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}}

    def test_bundle_without_git_reports_declared_revision_and_checked_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source_revision.json').write_text(json.dumps(self.manifest(root)))
            result = source_revision(root)
            self.assertEqual(result['revision_source'], 'checked_bundle_inventory')
            self.assertEqual(result['bundle_files_verified'], 1)
            self.assertIsNone(result['git_dirty'])

    def test_modified_bundled_file_fails_instead_of_silently_losing_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'source_revision.json').write_text(json.dumps(self.manifest(root)))
            (root / 'labelled_fixture.txt').write_text('Labelled tampering')
            with self.assertRaisesRegex(ValueError, 'missing or modified'):
                source_revision(root)

    def test_review_bundle_reports_uncommitted_source_instead_of_claiming_head_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = self.manifest(root)
            data.update(schema='investify-working-source-revision-v2', working_tree=True)
            (root / 'source_revision.json').write_text(json.dumps(data))
            result = source_revision(root)
            self.assertTrue(result['git_dirty'])
            self.assertEqual(result['revision_source'], 'checked_working_tree_inventory')
            data['working_tree'] = False
            (root / 'source_revision.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError): source_revision(root)

    def test_invalid_or_traversing_inventory_is_refused(self):
        for mutation in ('path', 'commit', 'digest', 'empty'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = self.manifest(root)
                if mutation == 'path': data['files'] = {'../outside_fixture.txt': 'a' * 64}
                elif mutation == 'commit': data['commit'] = 'not a revision'
                elif mutation == 'digest': data['files']['labelled_fixture.txt'] = 'not a hash'
                else: data['files'] = {}
                (root / 'source_revision.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError): source_revision(root)

    def test_directory_without_owned_git_or_manifest_never_inherits_parent_repo_identity(self):
        result = source_revision(ROOT / 'tests')
        self.assertEqual(result['revision_source'], 'unavailable')
        self.assertIsNone(result['git_commit'])


if __name__ == '__main__':
    unittest.main()
