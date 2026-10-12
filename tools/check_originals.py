"""Check protected original bytes, including explicitly recorded local relocations."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence/originals_preservation_check.json')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'evidence'):
        raise ValueError('Preservation receipts must remain in project evidence')
    manifest = json.loads((ROOT / 'evidence/original_files.sha256.json').read_text(encoding='utf-8-sig'))
    relocation_path = ROOT / 'evidence/workspace_reorganization_20261012.json'
    relocated = {}
    if relocation_path.exists():
        relocation = json.loads(relocation_path.read_text(encoding='utf-8-sig'))
        workspace = Path(manifest['roots']['FYP']).resolve()
        if (relocation['schema'] != 'investify-workspace-relocation-v1'
                or relocation['status'] != 'verified' or not relocation['passed']
                or Path(relocation['workspace']).resolve() != workspace):
            raise ValueError('Original relocation must have a verified matching workspace receipt')
        for entry in relocation['files']:
            old = (workspace / entry['old_relative']).resolve()
            new = (workspace / entry['new_relative']).resolve()
            if not old.is_relative_to(workspace) or not new.is_relative_to(workspace / '_archives'):
                raise ValueError('Relocation escapes its explicit workspace/archive roots')
            if old in relocated:
                raise ValueError('Duplicate original relocation')
            relocated[old] = (new, entry['sha256'])
    changed, moved_count = [], 0
    for entry in manifest['files']:
        original = (Path(manifest['roots'][entry['origin']]) / entry['path']).resolve()
        path = original
        if original in relocated:
            path, recorded_hash = relocated[original]
            if recorded_hash != entry['sha256']:
                raise ValueError('Relocation differs from the protected original hash')
            moved_count += 1
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            changed.append({'original_path': str(original), 'checked_path': str(path)})
    result = {
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'files_checked': len(manifest['files']), 'relocated_originals_checked': moved_count,
        'changed_originals': changed, 'passed': not changed,
        'relocation_receipt': str(relocation_path) if relocated else None,
    }
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f"Checked {len(manifest['files'])} original files ({moved_count} archived); changes: {len(changed)}")
    return 1 if changed else 0


if __name__ == '__main__':
    raise SystemExit(main())
