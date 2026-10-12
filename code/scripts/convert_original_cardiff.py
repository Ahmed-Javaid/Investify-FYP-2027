"""Lossless conversion only after original published BIN hash verification."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.model_conversion import convert_original

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-bin', type=Path, required=True)
parser.add_argument('--output-directory', type=Path, required=True)
args = parser.parse_args()
output = args.output_directory.resolve()
if not output.is_relative_to(Path('E:/AI-Tools').resolve()):
    raise ValueError('Converted model/cache bytes must remain on E:/AI-Tools')
receipt = convert_original(args.source_bin, output)
print(f"Original Cardiff conversion: {receipt['state_dict_keys']} keys; bitwise equality passed; no inference")
