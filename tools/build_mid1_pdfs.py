"""Compile the requested LaTeX report/deck, retaining native output on E:."""
import argparse
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path('E:/AI-Tools/Temp').resolve()
COMPILER = Path('E:/AI-Tools/Cache/tectonic-0.17.0/tectonic.exe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.run_id):
        raise ValueError('Use a plain dated build identity')
    env = dict(os.environ, TEMP=str(SCRATCH), TMP=str(SCRATCH),
               TECTONIC_CACHE_DIR='E:/AI-Tools/Cache/tectonic-data',
               XDG_CACHE_HOME='E:/AI-Tools/Cache',
               XDG_CONFIG_HOME='E:/AI-Tools/Work/tectonic-config')
    for kind, stem in (('report', 'investify-report-build-'),
                       ('presentation', 'investify-report-build-presentation-')):
        target = (SCRATCH / (stem + args.run_id)).resolve()
        if not target.is_relative_to(SCRATCH) or target.exists():
            raise ValueError('Preserve existing builds')
        target.mkdir()
        result = subprocess.run([str(COMPILER), '--outdir', str(target), '--keep-logs',
                                 '--keep-intermediates', 'main.tex'], cwd=ROOT / kind,
                                env=env, capture_output=True, text=True, timeout=180)
        (target / 'compiler-console.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode or not (target / 'main.pdf').is_file():
            raise RuntimeError(f'{kind} compilation failed: {(result.stdout + result.stderr)[-2000:]}')
        print(f'{kind}: compiled {target / "main.pdf"}')


if __name__ == '__main__':
    main()
