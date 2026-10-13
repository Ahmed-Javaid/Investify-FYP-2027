"""Restore reviewed newline bytes in an isolated checkout without changing content."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = {'.py', '.tex', '.cls', '.sty', '.bib', '.json', '.jsonl', '.csv', '.tsv', '.txt',
        '.md', '.yml', '.yaml', '.toml', '.ps1', '.html', '.js', '.mjs', '.css',
        '.xml', '.lock', '.log', '.sh', '.ini', '.cfg', '.svg'}


def restore(root, inventory):
    changed = 0
    for name, expected in inventory.items():
        path = (root / name).resolve()
        if (not path.is_relative_to(root.resolve()) or '.git' in Path(name).parts
                or path.name.startswith('.env') or path.is_symlink()):
            raise ValueError('Unsafe checkout inventory path')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() == expected:
            continue
        if path.suffix.lower() not in TEXT:
            raise ValueError(f'Changed binary input: {name}')
        data.decode('utf-8-sig')
        lf = data.replace(b'\r\n', b'\n')
        candidates = {lf, lf.replace(b'\n', b'\r\n')}
        matches = [value for value in candidates if hashlib.sha256(value).hexdigest() == expected]
        if len(matches) != 1:
            raise ValueError(f'Content changed beyond newline translation: {name}')
        path.write_bytes(matches[0])
        changed += 1
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, default=ROOT / 'code/config/ci_checkout_inventory.json')
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding='utf-8'))
    changed = restore(ROOT, inventory['files'])
    print(f'Checked {len(inventory["files"])} reviewed inputs; restored newline bytes in {changed} files.')


if __name__ == '__main__':
    main()
