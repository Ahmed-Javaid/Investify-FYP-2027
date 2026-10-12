"""Wrong-original-hash refusal is portable; no Torch/model load is required."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.model_conversion import convert_original


class ModelConversionTests(unittest.TestCase):
    def test_substitute_bin_is_rejected_before_deserialization_or_output_creation(self):
        with tempfile.TemporaryDirectory(prefix='investify-original-bin-fixture-') as directory:
            root = Path(directory)
            original = root / 'LABELLED_wrong_original.bin'
            original.write_bytes(b'LABELLED substitute, not original publisher weights')
            with self.assertRaisesRegex(ValueError, 'before deserialization'):
                convert_original(original, root / 'converted')
            self.assertFalse((root / 'converted').exists())
