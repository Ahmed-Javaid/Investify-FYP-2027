"""Process-local classifier loader; never repair or modify the unrelated venv.

Invoke with the existing CPython 3.13 base using -I -B. This is a separate
classifier runtime, not the original Python 3.11 scientific lock.
"""
import argparse
import importlib
import json
import os
from pathlib import Path
import runpy
import sys
import hashlib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
EXISTING_PACKAGES = Path('E:/Uni_Stuff/Projects/WeatherForcastAI/CookBookAI/venv/Lib/site-packages')
TEMP = Path('E:/AI-Tools/Temp').resolve()


def make_audit(*, probe, output_root=ROOT.parent, temp_root=TEMP):
    roots = (Path(output_root).resolve(), Path(temp_root).resolve())
    mutations = {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename', 'os.chmod', 'os.chown',
                 'os.utime', 'os.truncate', 'os.chflags', 'os.link', 'os.symlink'}
    def audit(event, values):
        if event in ('socket.connect', 'socket.connect_ex', 'socket.bind', 'urllib.Request'):
            raise PermissionError('Classifier loader is offline; network/socket work is refused')
        paths = []
        if event == 'open':
            path, mode, flags = values
            writing = (isinstance(mode, str) and any(letter in mode for letter in 'wax+')) or bool(
                (flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writing:
                if isinstance(path, int):
                    if path not in (1, 2):
                        raise PermissionError('Unresolved writable file descriptors are refused')
                else:
                    paths = [path]
        elif event in mutations:
            paths = values[:2] if event in ('os.rename', 'os.link', 'os.symlink') else values[:1]
            # Relative dir_fd operations cannot be checked against these roots.
            indexes = {'os.rename': (2, 3), 'os.link': (2, 3), 'os.remove': (1,), 'os.rmdir': (1,),
                       'os.mkdir': (2,), 'os.chmod': (2,), 'os.chown': (3,),
                       'os.utime': (3,), 'os.symlink': (2,)}
            dir_fds = [values[index] for index in indexes.get(event, ()) if index < len(values)]
            if any(isinstance(value, int) and value != -1 for value in dir_fds):
                raise PermissionError('Unresolved directory-descriptor mutations are refused')
        for value in paths:
            if isinstance(value, int):
                raise PermissionError('Unresolved file-descriptor mutations are refused')
            path = Path(os.fsdecode(value)).resolve()
            if probe or not any(path.is_relative_to(root) for root in roots):
                raise PermissionError('Read-only external runtime; writes stay within task outputs/E: Temp')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--study-args', nargs=argparse.REMAINDER)
    parser.add_argument('--convert-args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 13) or not EXISTING_PACKAGES.is_dir():
        raise RuntimeError('Use the verified existing CPython 3.13 base and read-only E: package directory')
    sys.dont_write_bytecode = True
    hf = str(TEMP / 'investify-classifier-hf')
    os.environ.update(TEMP=str(TEMP), TMP=str(TEMP), PYTHONDONTWRITEBYTECODE='1',
                      HF_HOME=hf, HF_HUB_CACHE=hf, HUGGINGFACE_HUB_CACHE=hf, TRANSFORMERS_CACHE=hf,
                      HF_DATASETS_CACHE=hf, HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1',
                      TRANSFORMERS_OFFLINE='1', TORCH_HOME=str(TEMP / 'investify-classifier-torch'),
                      TORCHINDUCTOR_CACHE_DIR=str(TEMP / 'investify-classifier-inductor'),
                      TRITON_CACHE_DIR=str(TEMP / 'investify-classifier-triton'),
                      CUDA_CACHE_PATH=str(TEMP / 'investify-classifier-cuda'),
                      XDG_CACHE_HOME=str(TEMP / 'investify-classifier-cache'), TOKENIZERS_PARALLELISM='false')
    sys.path.insert(0, str(EXISTING_PACKAGES))
    sys.addaudithook(make_audit(probe=args.probe))
    if args.probe:
        versions = {}
        for name in ('torch', 'transformers', 'safetensors', 'tokenizers'):
            module = importlib.import_module(name)
            versions[name] = {'version': module.__version__, 'module_path': module.__file__}
        report = {'python': sys.version.split()[0], 'executable': sys.executable,
                  'checked_utc': datetime.now(timezone.utc).isoformat(),
                  'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'external_packages_read_only': str(EXISTING_PACKAGES), 'imports': versions,
                  'model_loads': 0, 'inference_calls': 0, 'network_calls': 0,
                  'scientific_py311_lock_restored': False,
                  'scope': 'Actual guarded imports only; no install/copy/launcher repair/GPU/model load or inference'}
        print(json.dumps(report, indent=2))
        # Probe audit deliberately forbids writes. The caller can retain stdout
        # as a task receipt; no bypass is added to this guarded process.
        return 0
    if args.receipt:
        raise ValueError('Study outputs are governed by the V4 CLI; use --study-args')
    if args.study_args and args.convert_args:
        raise ValueError('Choose study or conversion arguments, not both')
    script = ROOT / ('scripts/convert_original_cardiff.py' if args.convert_args is not None else 'scripts/social_study_v4.py')
    sys.argv = [str(script), *(args.convert_args if args.convert_args is not None else args.study_args or [])]
    runpy.run_path(str(script), run_name='__main__')


if __name__ == '__main__':
    raise SystemExit(main())
