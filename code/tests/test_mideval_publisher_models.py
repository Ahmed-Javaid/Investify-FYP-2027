"""Publisher gate tests with explicitly synthetic tiny files, never model runs."""
import copy
import hashlib
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from investify.publisher_models import catalog, model_spec, validate_spec, verify_local, verify_runtime


class PublisherModelTests(unittest.TestCase):
    def fixture(self):
        value = copy.deepcopy(catalog())
        # Two tiny labelled fake shards replace actual pointers only inside a mock.
        blocks = [b'LABELLED UNIT FIXTURE FIRST SHARD', b'LABELLED UNIT FIXTURE SECOND SHARD']
        value['models']['qwen25']['files'] = [
            {'filename': f'LABELLED-fixture-{i}.gguf', 'sha256': hashlib.sha256(block).hexdigest(),
             'size_bytes': len(block)} for i, block in enumerate(blocks)]
        return value, blocks

    def test_only_exact_reviewed_publisher_identity_is_eligible(self):
        for key in ('qwen25', 'qwen3'):
            spec = model_spec(key)
            self.assertEqual(validate_spec(spec), key)
            for field in ('model_id', 'weights_sha256', 'weights_filename', 'served_alias'):
                changed = {**spec, field: 'UNDECLARED UNIT FIXTURE'}
                with self.assertRaises(ValueError): validate_spec(changed)

    def test_all_shards_are_required_and_changed_bytes_fail_before_inference(self):
        value, blocks = self.fixture()
        with tempfile.TemporaryDirectory(prefix='investify-publisher-test-') as directory:
            paths = [Path(directory) / item['filename'] for item in value['models']['qwen25']['files']]
            for path, block in zip(paths, blocks): path.write_bytes(block)
            with patch('investify.publisher_models.catalog', return_value=value):
                receipt = verify_local('qwen25', directory)
                self.assertEqual(len(receipt['verified_files']), 2)
                verify_runtime(model_spec('qwen25'), receipt)
                paths[1].write_bytes(b'X' * len(blocks[1]))
                with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                    verify_runtime(model_spec('qwen25'), receipt)
                paths[1].unlink()
                with self.assertRaises(FileNotFoundError): verify_local('qwen25', directory)

    def test_filename_alias_and_claimed_receipt_do_not_establish_origin(self):
        spec = model_spec('qwen3')
        with self.assertRaisesRegex(ValueError, 'verified original-publisher runtime'):
            verify_runtime(spec, {'model_sha256': spec['weights_sha256'], 'served_alias': spec['served_alias']})
        with self.assertRaises(ValueError): model_spec('unreviewed-model-fixture')

    def test_receipt_replay_requires_the_same_publisher_manifest(self):
        value, blocks = self.fixture()
        with tempfile.TemporaryDirectory(prefix='investify-publisher-test-') as directory:
            for item, block in zip(value['models']['qwen25']['files'], blocks):
                (Path(directory) / item['filename']).write_bytes(block)
            with patch('investify.publisher_models.catalog', return_value=value):
                receipt = verify_local('qwen25', directory)
                changed = copy.deepcopy(receipt)
                changed['publisher_manifest_sha256'] = '0' * 64
                with self.assertRaises(ValueError): verify_runtime(model_spec('qwen25'), changed)


if __name__ == '__main__': unittest.main()
