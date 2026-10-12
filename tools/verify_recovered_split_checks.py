"""Run unchanged shuffled-split test bodies with the recovered real sklearn.

This read-only Python 3.13 probe emits JSON to stdout. It does not install,
repair an environment, call pytest, fit a classifier or use market inputs.
"""
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = Path('E:/Uni_Stuff/Projects/WeatherForcastAI/CookBookAI/venv/Lib/site-packages')
SELECTED = ('test_shuffled_kfold_is_deterministic', 'test_shuffled_kfold_breaks_temporal_order',
            'test_shuffled_kfold_partitions_all_rows')


def refuse_mutations(event, values):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.bind', 'urllib.Request',
                 'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename', 'os.chmod', 'os.chown',
                 'os.utime', 'os.truncate', 'os.link', 'os.symlink'):
        raise PermissionError('Read-only/offline split-check process')
    if event == 'open':
        path, mode, flags = values
        writing = (isinstance(mode, str) and any(letter in mode for letter in 'wax+')) or bool(
            (flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and path not in (1, 2):
            raise PermissionError('Read-only split-check process')


def main():
    if sys.version_info[:2] != (3, 13) or not PACKAGES.is_dir():
        raise RuntimeError('Use the existing CPython 3.13 base and read-only E: package files')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(PACKAGES))
    sys.path.insert(0, str(ROOT / 'code/src'))
    sys.addaudithook(refuse_mutations)
    import numpy as np
    import pandas as pd
    import scipy
    import sklearn
    from investify.harness.splits import shuffled_kfold
    test_source = ROOT / 'code/tests/test_splits.py'
    split_source = ROOT / 'code/src/investify/harness/splits.py'
    tree = ast.parse(test_source.read_text(encoding='utf-8'), filename=str(test_source))
    bodies = [node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name in (*SELECTED, 'make_dates')]
    if {node.name for node in bodies} != set((*SELECTED, 'make_dates')):
        raise ValueError('The declared unchanged test function bodies are unavailable')
    namespace = {'np': np, 'pd': pd, 'shuffled_kfold': shuffled_kfold}
    exec(compile(ast.Module(body=bodies, type_ignores=[]), str(test_source), 'exec'), namespace)
    checks = []
    for name in SELECTED:
        try:
            namespace[name]()
            checks.append({'function': name, 'passed': True})
        except Exception as error:
            checks.append({'function': name, 'passed': False, 'error_type': type(error).__name__, 'error': str(error)})
    report = {'schema': 'investify-recovered-split-function-checks-v1',
              'checked_utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version.split()[0],
              'executable': sys.executable, 'runner': 'Direct unchanged AST function-body execution; not pytest',
              'runtime': {name: {'version': module.__version__, 'path': module.__file__}
                          for name, module in (('numpy', np), ('pandas', pd), ('scipy', scipy), ('sklearn', sklearn))},
              'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in (Path(__file__), test_source, split_source)},
              'checks': checks, 'passed': all(check['passed'] for check in checks),
              'pytest_executed': False, 'scientific_py311_lock_restored': False,
              'market_inputs_used': False, 'classifier_fits': 0, 'model_inference_calls': 0,
              'scope': 'Three existing shuffled-split assertions on labelled synthetic dates/indices, using real sklearn. '
                       'Earlier deselected Py311 test receipts remain unchanged; this is a separate partial-runtime check.'}
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
