"""Versioned lossless serialization of verified original Cardiff weights.

No inference, training, dtype conversion, alias-key dropping or fallback
unsafe unpickling. Fixture access is Python-only and explicitly labelled.
"""
import hashlib
import json
from pathlib import Path
import platform
import re

ORIGINAL_CARDIFF_BIN_SHA256 = '4d24a3e32a88ed1c4e5b789fc6644e2e767500554e954b27dccf52a8e762cbae'
CONVERSION_PROTOCOL = 'original-cardiff-lossless-safetensors-v1'


def file_hash(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def tensors_equal(original, converted, torch):
    if set(original) != set(converted):
        raise ValueError('Conversion lost or added state-dict keys')
    rows = []
    for name in sorted(original):
        left, right = original[name], converted[name]
        if left.dtype != right.dtype or left.shape != right.shape:
            raise ValueError('Conversion changed tensor dtype or shape')
        a = left.detach().cpu().contiguous().reshape(-1).view(torch.uint8)
        b = right.detach().cpu().contiguous().reshape(-1).view(torch.uint8)
        if not torch.equal(a, b):
            raise ValueError('Conversion changed raw tensor bytes')
        rows.append({'key': name, 'dtype': str(left.dtype), 'shape': list(left.shape),
                     'raw_bytes_sha256': hashlib.sha256(a.numpy().tobytes()).hexdigest()})
    return rows


def dense_state(state, torch):
    if (not isinstance(state, dict) or not state or any(not isinstance(key, str) or not key
            or not isinstance(value, torch.Tensor) or value.layout != torch.strided
            for key, value in state.items())):
        raise ValueError('Only a nonempty dense tensor state dict is convertible')
    return state


def validate_conversion_receipt(receipt, *, expected_converted_sha256, _fixture_source_sha256=None):
    """Validate the disclosed serialization receipt without claiming attestation."""
    expected_source = _fixture_source_sha256 or ORIGINAL_CARDIFF_BIN_SHA256
    purpose = 'unit_fixture' if _fixture_source_sha256 else 'research'
    if (not isinstance(receipt, dict) or receipt.get('protocol') != CONVERSION_PROTOCOL
            or receipt.get('purpose') != purpose or receipt.get('source_bin_sha256') != expected_source
            or receipt.get('converted_sha256') != expected_converted_sha256
            or receipt.get('converter_sha256') != file_hash(Path(__file__))
            or receipt.get('weights_only') is not True or receipt.get('all_keys_dtype_shape_raw_bytes_equal') is not True
            or any(type(receipt.get(key)) is not int or receipt[key] != 0
                   for key in ('dtype_casts', 'keys_dropped', 'model_inference_calls'))
            or any(type(receipt.get(key)) is not int or receipt[key] <= 0
                   for key in ('source_bin_bytes', 'converted_bytes', 'state_dict_keys'))
            or any(not isinstance(receipt.get(key), str) or not receipt[key].strip()
                   for key in ('python', 'torch', 'safetensors'))):
        raise ValueError('A matching original-byte, research-purpose lossless conversion receipt is required')
    rows = receipt.get('tensor_equality')
    if (not isinstance(rows, list) or len(rows) != receipt['state_dict_keys']
            or any(not isinstance(row, dict) or set(row) != {'key', 'dtype', 'shape', 'raw_bytes_sha256'}
                   or not isinstance(row['key'], str) or not row['key']
                   or not isinstance(row['dtype'], str) or not row['dtype'].startswith('torch.')
                   or not isinstance(row['shape'], list) or any(type(size) is not int or size < 0 for size in row['shape'])
                   or not isinstance(row['raw_bytes_sha256'], str)
                   or not re.fullmatch('[0-9a-f]{64}', row['raw_bytes_sha256']) for row in rows)
            or len({row['key'] for row in rows}) != len(rows)):
        raise ValueError('Conversion receipt must retain every unique tensor key/dtype/shape/raw-byte hash')
    return receipt


def convert_original(source, output_directory, *, _fixture_sha256=None):
    source, output_directory = Path(source).resolve(), Path(output_directory).resolve()
    expected = _fixture_sha256 or ORIGINAL_CARDIFF_BIN_SHA256
    if not source.is_file() or file_hash(source) != expected:
        raise ValueError('Original BIN bytes must match the pinned publisher SHA before deserialization')
    if output_directory.exists() or output_directory.is_relative_to(source.parent):
        raise ValueError('Preserve original weights/prior conversions; choose a new separate output directory')
    import torch
    import safetensors
    from safetensors.torch import save_file, load_file
    state = torch.load(str(source), map_location='cpu', weights_only=True)
    dense_state(state, torch)
    # Clone every tensor so save_file keeps every alias key. No cast occurs.
    converted = {key: value.detach().cpu().contiguous().clone() for key, value in state.items()}
    output_directory.mkdir(parents=True)
    target = output_directory / 'model.safetensors'
    save_file(converted, str(target), metadata={'format': 'pt'})
    restored = load_file(str(target), device='cpu')
    equality = tensors_equal(state, restored, torch)
    if file_hash(source) != expected:
        raise ValueError('Original BIN bytes changed during conversion; no completed receipt')
    receipt = {'protocol': CONVERSION_PROTOCOL, 'purpose': 'unit_fixture' if _fixture_sha256 else 'research',
               'source_bin_sha256': expected, 'source_bin_bytes': source.stat().st_size,
               'converted_sha256': file_hash(target), 'converted_bytes': target.stat().st_size,
               'python': platform.python_version(), 'torch': torch.__version__, 'safetensors': safetensors.__version__,
               'state_dict_keys': len(state), 'tensor_equality': equality,
               'all_keys_dtype_shape_raw_bytes_equal': True, 'weights_only': True,
               'dtype_casts': 0, 'keys_dropped': 0, 'model_inference_calls': 0,
               'converter_sha256': file_hash(Path(__file__)),
               'scope': 'Lossless file serialization only; no independent execution attestation, model score or tokenizer/config authentication'}
    validate_conversion_receipt(receipt, expected_converted_sha256=receipt['converted_sha256'],
                                _fixture_source_sha256=_fixture_sha256)
    with (output_directory / 'conversion_receipt.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(receipt, indent=2, allow_nan=False))
    return receipt


def verify_conversion(source, converted, *, expected_converted_sha256, receipt=None, _fixture_source_sha256=None):
    expected_source = _fixture_source_sha256 or ORIGINAL_CARDIFF_BIN_SHA256
    validate_conversion_receipt(receipt, expected_converted_sha256=expected_converted_sha256,
                                _fixture_source_sha256=_fixture_source_sha256)
    if file_hash(source) != expected_source or file_hash(converted) != expected_converted_sha256:
        raise ValueError('Conversion inputs do not match original publisher/declared converted bytes')
    import torch
    from safetensors.torch import load_file
    state = torch.load(str(source), map_location='cpu', weights_only=True)
    dense_state(state, torch)
    equality = tensors_equal(state, load_file(str(converted), device='cpu'), torch)
    if (equality != receipt['tensor_equality'] or Path(source).stat().st_size != receipt['source_bin_bytes']
            or Path(converted).stat().st_size != receipt['converted_bytes']):
        raise ValueError('Retained conversion tensor/size evidence differs from actual bytes')
    if file_hash(source) != expected_source or file_hash(converted) != expected_converted_sha256:
        raise ValueError('Original/converted bytes changed during equality verification')
    return dict(receipt)
