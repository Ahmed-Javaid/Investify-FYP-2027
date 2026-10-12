"""Executable labelled tensor fixture; not an original-model conversion."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch-directory', type=Path, required=True)
    args = parser.parse_args()
    temp = Path('E:/AI-Tools/Temp').resolve()
    os.environ.update(TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE='1',
                      HF_HOME=str(temp / 'investify-classifier-hf'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    sys.path.insert(0, 'E:/Uni_Stuff/Projects/WeatherForcastAI/CookBookAI/venv/Lib/site-packages')
    sys.path.insert(0, str(ROOT / 'src'))
    import torch
    from investify.model_conversion import convert_original
    base = args.scratch_directory.resolve()
    if not base.is_relative_to(temp) or not base.name.startswith('investify-conversion-fixture-run-') or any(base.iterdir()):
        raise ValueError('Use a new empty task-owned fixture directory under E:/AI-Tools/Temp')
    original_dir = base / 'original'
    original_dir.mkdir()
    source = original_dir / 'LABELLED_fixture.bin'
    tensor = torch.tensor([1., -0., float('nan'), 2.], dtype=torch.float32)
    torch.save({'LABELLED.weight': tensor, 'LABELLED.alias': tensor, 'LABELLED.bias': torch.tensor([.5], dtype=torch.float16)}, source)
    raw = source.read_bytes()
    receipt = convert_original(source, base / 'converted', _fixture_sha256=hashlib.sha256(raw).hexdigest())
    assert receipt['purpose'] == 'unit_fixture'
    assert receipt['all_keys_dtype_shape_raw_bytes_equal']
    assert receipt['state_dict_keys'] == 3 and receipt['keys_dropped'] == 0 and receipt['dtype_casts'] == 0
    assert source.read_bytes() == raw
    (ROOT.parent / 'evidence/background_lossless_conversion_fixture_20261012.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('Actual CPU tensor fixture conversion: 3 keys, all raw bytes/dtypes/shapes equal; no original weights/inference')
