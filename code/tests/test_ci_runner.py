"""Protect source ownership, input admission and temporary CI metadata."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_mid1_ci as ci  # noqa: E402 - import the actual CI entry point.


class CiRunnerGuards(unittest.TestCase):
    def workspace(self, path):
        project = Path(path)
        code = project / 'code'
        code.mkdir()
        (project / '.git').mkdir()
        return project, code

    def commands(self, project, names):
        return [str(project), 'a' * 40, '', '\0'.join(names)]

    def test_missing_owned_repository_cannot_use_an_ancestor_identity(self):
        with tempfile.TemporaryDirectory() as path:
            project, code = self.workspace(path)
            (project / '.git').rmdir()
            with patch.object(ci, 'PROJECT', project), patch.object(ci, 'CODE', code), self.assertRaises(ValueError):
                ci.declare_revision()

    def test_wrong_git_root_is_refused(self):
        with tempfile.TemporaryDirectory() as path:
            project, code = self.workspace(path)
            with patch.object(ci, 'PROJECT', project), patch.object(ci, 'CODE', code), \
                    patch.object(ci.subprocess, 'check_output', return_value=str(project.parent)), self.assertRaises(ValueError):
                ci.declare_revision()

    def test_credentials_are_refused_before_reading_contents(self):
        with tempfile.TemporaryDirectory() as path:
            project, code = self.workspace(path)
            with patch.object(ci, 'PROJECT', project), patch.object(ci, 'CODE', code), \
                    patch.object(ci.subprocess, 'check_output', side_effect=self.commands(project, ['.env'])), self.assertRaises(ValueError):
                ci.declare_revision()

    def test_outside_component_path_is_refused(self):
        with tempfile.TemporaryDirectory() as path:
            project, code = self.workspace(path)
            with patch.object(ci, 'PROJECT', project), patch.object(ci, 'CODE', code), \
                    patch.object(ci.subprocess, 'check_output', side_effect=self.commands(project, ['../other.txt'])), self.assertRaises(ValueError):
                ci.declare_revision()

    def test_unrecognized_metadata_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as path:
            project, code = self.workspace(path)
            (code / 'module.py').write_text('pass\n')
            original = b'{"schema":"different-owner"}'
            (code / 'source_revision.json').write_bytes(original)
            with patch.object(ci, 'PROJECT', project), patch.object(ci, 'CODE', code), \
                    patch.object(ci.subprocess, 'check_output', side_effect=self.commands(project, ['module.py'])), self.assertRaises(ValueError):
                ci.declare_revision()
            self.assertEqual((code / 'source_revision.json').read_bytes(), original)

    def test_changed_metadata_is_preserved_instead_of_deleted(self):
        with tempfile.TemporaryDirectory() as path:
            _, code = self.workspace(path)
            content = b'{"changed":"by another actor"}'
            (code / 'source_revision.json').write_bytes(content)
            with patch.object(ci, 'CODE', code), self.assertRaises(ValueError):
                ci.restore_revision(None, '0' * 64)
            self.assertEqual((code / 'source_revision.json').read_bytes(), content)

    def test_job_declaration_is_removed_or_prior_bytes_restored(self):
        for previous in (None, b'{"previous":"unchanged bytes"}'):
            with self.subTest(previous=previous), tempfile.TemporaryDirectory() as path:
                _, code = self.workspace(path)
                module = code / 'module.py'
                module.write_text('pass\n')
                content = json.dumps({'files': {'module.py': hashlib.sha256(module.read_bytes()).hexdigest()}}).encode()
                (code / 'source_revision.json').write_bytes(content)
                with patch.object(ci, 'CODE', code):
                    self.assertEqual(ci.restore_revision(previous, hashlib.sha256(content).hexdigest()), content)
                if previous is None:
                    self.assertFalse((code / 'source_revision.json').exists())
                else:
                    self.assertEqual((code / 'source_revision.json').read_bytes(), previous)


if __name__ == '__main__':
    unittest.main()
