"""CPU tensor serialization regressions, explicitly not publisher-model evidence.

Run with the existing isolated CPython 3.13 base and existing E: packages.
No inference, training, downloads or unrelated-environment writes occur.
"""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
import shutil
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
try:
    import torch
    from safetensors.torch import save_file, load_file
except ImportError:
    torch = None
from investify.model_conversion import (convert_original, verify_conversion, file_hash,
    tensors_equal, validate_conversion_receipt)


@unittest.skipIf(torch is None, 'CPU tensor fixture needs the explicitly separate classifier runtime')
class LosslessConversionRegressionTests(unittest.TestCase):
    def setUp(self):
        # Windows Python 3.13's mode-0700 TemporaryDirectory can create an ACL
        # inaccessible to this sandbox token. Inherit the E: scratch ACL instead.
        self.root = (Path('E:/AI-Tools/Temp') / ('investify-conversion-regression-fixture-' + uuid.uuid4().hex)).resolve()
        self.assertTrue(self.root.is_relative_to(Path('E:/AI-Tools/Temp').resolve()))
        self.assertTrue(self.root.name.startswith('investify-conversion-regression-fixture-'))
        self.root.mkdir(mode=0o777, exist_ok=False)
        self.addCleanup(shutil.rmtree, self.root)
        self.original = self.root / 'original'
        self.original.mkdir()
        self.source = self.original / 'LABELLED_tensor_fixture.bin'
        shared = torch.tensor([1., -0., float('nan'), 2.], dtype=torch.float32)
        torch.save({'LABELLED.weight': shared, 'LABELLED.alias': shared,
                    'LABELLED.bias': torch.tensor([.5], dtype=torch.float16)}, self.source)
        self.source_bytes = self.source.read_bytes()
        self.source_sha = hashlib.sha256(self.source_bytes).hexdigest()

    def converted(self):
        receipt = convert_original(self.source, self.root / 'converted', _fixture_sha256=self.source_sha)
        return self.root / 'converted' / 'model.safetensors', receipt

    def test_alias_keys_nan_signed_zero_and_dtype_survive_exact_round_trip(self):
        target, receipt = self.converted()
        result = verify_conversion(self.source, target, expected_converted_sha256=receipt['converted_sha256'],
                                   receipt=receipt, _fixture_source_sha256=self.source_sha)
        self.assertEqual(result, receipt)
        self.assertEqual(receipt['purpose'], 'unit_fixture')
        self.assertEqual(receipt['state_dict_keys'], 3)
        self.assertEqual(receipt['dtype_casts'], 0)
        self.assertEqual(receipt['keys_dropped'], 0)
        self.assertEqual(receipt['model_inference_calls'], 0)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)
        with self.assertRaisesRegex(ValueError, 'research-purpose'):
            validate_conversion_receipt(receipt, expected_converted_sha256=receipt['converted_sha256'])

    def test_a_new_hash_cannot_hide_changed_tensor_bytes_in_retained_conversion(self):
        target, receipt = self.converted()
        state = load_file(str(target), device='cpu')
        state['LABELLED.bias'][0] = 1.
        save_file(state, str(target), metadata={'format': 'pt'})
        changed = copy.deepcopy(receipt)
        changed['converted_sha256'] = file_hash(target)
        changed['converted_bytes'] = target.stat().st_size
        with self.assertRaisesRegex(ValueError, 'raw tensor bytes'):
            verify_conversion(self.source, target, expected_converted_sha256=changed['converted_sha256'],
                              receipt=changed, _fixture_source_sha256=self.source_sha)

    def test_receipt_key_size_and_source_hash_tampering_are_refused(self):
        target, receipt = self.converted()
        for field, value in (('source_bin_bytes', receipt['source_bin_bytes'] + 1),
                             ('source_bin_sha256', '0' * 64), ('converter_sha256', '0' * 64),
                             ('purpose', 'research')):
            altered = copy.deepcopy(receipt)
            altered[field] = value
            with self.assertRaises(ValueError, msg=field):
                verify_conversion(self.source, target, expected_converted_sha256=receipt['converted_sha256'],
                                  receipt=altered, _fixture_source_sha256=self.source_sha)
        altered = copy.deepcopy(receipt)
        altered['tensor_equality'][0]['raw_bytes_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'tensor/size evidence'):
            verify_conversion(self.source, target, expected_converted_sha256=receipt['converted_sha256'],
                              receipt=altered, _fixture_source_sha256=self.source_sha)

    def test_original_and_prior_conversion_directories_remain_immutable(self):
        target, receipt = self.converted()
        target_bytes = target.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Preserve original'):
            convert_original(self.source, target.parent, _fixture_sha256=self.source_sha)
        with self.assertRaises(ValueError):
            convert_original(self.source, self.original / 'nested', _fixture_sha256=self.source_sha)
        self.assertEqual(target.read_bytes(), target_bytes)
        self.assertEqual(self.source.read_bytes(), self.source_bytes)

    def test_removed_alias_and_dtype_cast_are_not_lossless(self):
        state = torch.load(str(self.source), map_location='cpu', weights_only=True)
        altered = dict(state)
        altered.pop('LABELLED.alias')
        with self.assertRaisesRegex(ValueError, 'state-dict keys'):
            tensors_equal(state, altered, torch)
        altered = dict(state)
        altered['LABELLED.bias'] = altered['LABELLED.bias'].to(torch.float32)
        with self.assertRaisesRegex(ValueError, 'dtype or shape'):
            tensors_equal(state, altered, torch)

    def test_original_hash_is_rechecked_after_tensor_serialization(self):
        from unittest.mock import patch
        import safetensors.torch
        actual_save = safetensors.torch.save_file
        def changing_source(*args, **kwargs):
            result = actual_save(*args, **kwargs)
            self.source.write_bytes(b'LABELLED mutation during conversion')
            return result
        with patch('safetensors.torch.save_file', side_effect=changing_source):
            with self.assertRaisesRegex(ValueError, 'changed during conversion'):
                convert_original(self.source, self.root / 'converted', _fixture_sha256=self.source_sha)
        self.assertFalse((self.root / 'converted' / 'conversion_receipt.json').exists())
