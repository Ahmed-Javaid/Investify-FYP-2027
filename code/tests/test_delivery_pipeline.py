"""Delivery refuses stale/failed CI and preserves frozen input content across checkout."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from restore_ci_checkout import restore
from run_mid1_delivery import check_ci


def sha(data):
    return hashlib.sha256(data).hexdigest()


class DeliveryGuards(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        (self.root / 'code').mkdir()
        (self.root / 'code/module.py').write_bytes(b'value = 1\n')
        self.paths = []
        for job in ('evidence', 'streamlit-ui'):
            folder = self.root / job
            folder.mkdir()
            declaration = json.dumps({'files': {'module.py': sha(b'value = 1\n')}}).encode()
            (folder / 'source_revision.json').write_bytes(declaration)
            value = {'status': 'passed', 'temporary_component_metadata_restored': True,
                     'source': {'repository_commit': 'abc', 'repository_dirty': False,
                                'declared_code_inventory_sha256': sha(declaration)},
                     'platform': 'Windows-local', 'job': job, 'execution_location': 'local_replay',
                     'artifacts_sha256': {'source_revision.json': sha(declaration)}}
            path = folder / 'job_receipt.json'
            path.write_text(json.dumps(value), encoding='utf-8')
            self.paths.append(path)

    def change(self, **changes):
        value = json.loads(self.paths[0].read_text())
        value.update(changes)
        self.paths[0].write_text(json.dumps(value))

    def test_delivery_requires_both_jobs(self):
        self.assertEqual(len(check_ci(self.paths, self.root, 'abc')), 2)
        with self.assertRaises(ValueError):
            check_ci(self.paths[:1], self.root, 'abc')

    def test_failed_job_does_not_deliver(self):
        self.change(status='failed')
        with self.assertRaises(ValueError):
            check_ci(self.paths, self.root, 'abc')

    def test_wrong_commit_does_not_deliver(self):
        with self.assertRaises(ValueError):
            check_ci(self.paths, self.root, 'other')

    def test_changed_source_does_not_deliver(self):
        (self.root / 'code/module.py').write_bytes(b'value = 2\n')
        with self.assertRaises(ValueError):
            check_ci(self.paths, self.root, 'abc')

    def test_changed_log_or_declaration_does_not_deliver(self):
        (self.paths[0].parent / 'source_revision.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):
            check_ci(self.paths, self.root, 'abc')

    def test_hosted_gate_rejects_local_replay(self):
        with self.assertRaises(ValueError):
            check_ci(self.paths, self.root, 'abc', hosted=True)

    def test_duplicate_job_does_not_fill_missing_platform(self):
        with self.assertRaises(ValueError):
            check_ci([self.paths[0], self.paths[0]], self.root, 'abc')

    def test_newline_restore_preserves_reviewed_content(self):
        path = self.root / 'code/module.py'
        self.assertEqual(restore(self.root, {'code/module.py': sha(b'value = 1\r\n')}), 1)
        self.assertEqual(path.read_bytes(), b'value = 1\r\n')
        path.write_bytes(b'value = 2\n')
        with self.assertRaises(ValueError):
            restore(self.root, {'code/module.py': sha(b'value = 1\r\n')})

    def test_binary_change_and_outside_path_are_refused(self):
        (self.root / 'image.png').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            restore(self.root, {'image.png': sha(b'original')})
        with self.assertRaises(ValueError):
            restore(self.root, {'../outside.py': sha(b'value = 1\n')})


if __name__ == '__main__':
    unittest.main()
