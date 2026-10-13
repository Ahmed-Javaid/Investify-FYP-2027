"""Replay frozen Windows provenance on either host without editing research code.

Absolute paths in these receipts describe where the original run occurred. The
viewer does not open those paths. Use both path dialects for that metadata check
in a private replay namespace; original code bytes, hashes and metrics stay intact.
"""
import importlib.util
from pathlib import Path, PurePosixPath, PureWindowsPath


def metadata_paths(host_path_type=None):
    base = host_path_type or type(Path())

    class RecordedPath(base):
        def is_absolute(self):
            return PurePosixPath(str(self)).is_absolute() or PureWindowsPath(str(self)).is_absolute()

    return RecordedPath


def compare_recorded_bundles(data, parent, catalog, plan, bundles, *, _metadata_path_type=None):
    # Keep the frozen module and its global namespace untouched, including when
    # several Streamlit sessions compare the same recorded study concurrently.
    source = Path(__file__).with_name('sentiment_receipts.py')
    spec = importlib.util.spec_from_file_location('investify._recorded_social_replay', source)
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    replay.Path = metadata_paths(_metadata_path_type)
    return replay.compare_bundles(data, parent, catalog, plan, bundles)
