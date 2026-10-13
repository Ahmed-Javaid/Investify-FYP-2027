"""Retained Windows model provenance remains valid in a POSIX recorded viewer."""
import json
from pathlib import Path, PurePosixPath
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
# The tests exercise the checkout directly without installing its package.
from investify import sentiment_receipts  # noqa: E402
from investify.recorded_social_replay import compare_recorded_bundles, metadata_paths  # noqa: E402


class RecordedReplayTests(unittest.TestCase):
    def test_windows_and_posix_absolute_metadata_but_not_drive_relative(self):
        paths = metadata_paths(PurePosixPath)
        self.assertFalse(PurePosixPath('E:/original/run.bin').is_absolute())
        for value in ('E:/original/run.bin', r'E:\original\run.bin', '/original/run.bin'):
            self.assertTrue(paths(value).is_absolute())
        for value in ('E:relative.bin', 'relative/run.bin'):
            self.assertFalse(paths(value).is_absolute())

    def test_actual_comparison_on_posix_metadata_replays_exact_frozen_result(self):
        study = ROOT / 'artifacts/mid_eval'
        def read(path):
            return json.loads(path.read_text(encoding='utf-8'))
        pointer = read(study / 'social_latest_study.json')
        result = compare_recorded_bundles(read(study / 'social_benchmark.json'),
                    read(study / 'social_selection_plan.json'), read(study / pointer['catalog']),
                    read(study / pointer['plan']), [read(study / name) for name in pointer['bundles']],
                    _metadata_path_type=PurePosixPath)
        expected = read(study / 'social_study_20261013_run02/comparison/comparison.json')
        self.assertEqual(result, expected)

    def test_replay_does_not_mutate_the_original_module_path_namespace(self):
        original = sentiment_receipts.Path
        self.test_actual_comparison_on_posix_metadata_replays_exact_frozen_result()
        self.assertIs(sentiment_receipts.Path, original)


if __name__ == '__main__':
    unittest.main()
