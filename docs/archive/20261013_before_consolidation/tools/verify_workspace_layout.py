"""Verify the project map, local guide links, archived bytes and code preservation."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'evidence') or output.exists():
        raise ValueError('Choose a new receipt under project evidence')
    mapping = json.loads((ROOT / 'PROJECT_MAP.json').read_text(encoding='utf-8'))
    relocation = json.loads((ROOT / 'evidence/workspace_reorganization_20261012.json').read_text(encoding='utf-8-sig'))
    if mapping['active_project'] != 'Investify' or relocation['status'] != 'verified' or not relocation['passed']:
        raise ValueError('Project identity or verified relocation is missing')
    failures = []
    references = [*mapping['documents'], *mapping['archives']]
    for reference in references:
        path = (WORKSPACE / reference['path']).resolve()
        if not path.is_relative_to(WORKSPACE) or not path.exists():
            failures.append(reference['path'])
    for entry in relocation['files']:
        path = (WORKSPACE / entry['new_relative']).resolve()
        if (not path.is_relative_to(WORKSPACE / '_archives') or not path.is_file()
                or path.stat().st_size != entry['bytes'] or sha(path) != entry['sha256']):
            failures.append(entry['new_relative'])
    for move in relocation['moves']:
        old = (WORKSPACE / move['old_relative']).resolve()
        if old.exists():
            failures.append('Old active-looking path still exists: ' + move['old_relative'])
    guides = ['README.md', 'deliverables/README.md', 'planning/CURRENT_STATUS.md',
              'planning/HANDOFF_20261012.md', 'planning/NEXT_CHAT.md']
    checked_links = 0
    for relative in guides:
        path = ROOT / relative
        for link in re.findall(r'\[[^\]]+\]\((<[^>]+>|[^)\n]+)\)', path.read_text(encoding='utf-8')):
            link = link.strip('<>')
            if re.match(r'[a-z]+://', link) or link.startswith('#'):
                continue
            target = (path.parent / link.split('#', 1)[0]).resolve()
            checked_links += 1
            if not target.is_relative_to(WORKSPACE) or not target.exists():
                failures.append(relative + ': ' + link)
    merge = json.loads((ROOT / 'MERGE_MANIFEST.json').read_text(encoding='utf-8'))
    code_files = {name: digest for name, digest in merge['files_sha256'].items() if name.startswith('code/')}
    for name, digest in code_files.items():
        if not (ROOT / name).is_file() or sha(ROOT / name) != digest:
            failures.append('Code changed from integration snapshot: ' + name)
    receipt = {
        'schema': 'investify-workspace-layout-verification-v1',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'active_project': str(ROOT), 'mapped_references_checked': len(references),
        'guide_links_checked': checked_links, 'archived_files_checked': len(relocation['files']),
        'integration_code_files_checked': len(code_files),
        'root_entries': sorted(path.name for path in WORKSPACE.iterdir()),
        'failures': failures, 'passed': not failures,
        'scope': 'Local organization and unchanged code/archive bytes; not scientific reproduction or submission approval.',
    }
    output.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(f"Layout: {len(references)} references, {checked_links} links, {len(relocation['files'])} archived files, "
          f"{len(code_files)} unchanged code files; {len(failures)} failures")
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
