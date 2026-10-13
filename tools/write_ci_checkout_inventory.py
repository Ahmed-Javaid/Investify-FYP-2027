"""Record current reviewed source/artifact bytes for cross-platform CI checkouts."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'code/config/ci_checkout_inventory.json'


def main():
    names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z', '--cached', '--others',
                                     '--exclude-standard'], text=True).split('\0')
    files = {}
    for name in names:
        if not name or name == OUTPUT.relative_to(ROOT).as_posix():
            continue
        path = (ROOT / name).resolve()
        if (not path.is_relative_to(ROOT) or path.name.startswith('.env')
                or path.suffix in ('.gguf', '.safetensors', '.pyc')):
            raise ValueError('Unexpected private/cache path in source inventory')
        if name.startswith(('code/', 'report/', 'presentation/', 'evidence/')) and path.is_file():
            if path.name == 'README.md' or name == 'code/source_revision.json':
                continue
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({'schema': 'investify-ci-checkout-bytes-v1',
                                 'scope': 'Restore newline-only Git checkout translations; changed content is rejected.',
                                 'files': files}, indent=2) + '\n', encoding='utf-8')
    print(f'Recorded {len(files)} reviewed source/artifact byte identities.')


if __name__ == '__main__':
    main()
