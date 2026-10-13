"""Check consolidated guide links, exact archived notes and reviewed PDF sources."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ('README.md', 'docs/team/MID1_TEAM_GUIDE.md', 'docs/technical/ENGINEERING.md',
             'docs/technical/RESEARCH.md', 'docs/technical/REQUIREMENTS.md',
             'docs/handoffs/AGENT_HANDOFF.md')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def headings(path):
    counts, result = {}, set()
    for text in re.findall(r'^#{1,6}\s+(.+?)\s*$', path.read_text(encoding='utf-8'), re.M):
        base = re.sub(r'[^\w\- ]', '', text.lower()).replace(' ', '-')
        count = counts.get(base, 0)
        result.add(base + ('-' + str(count) if count else ''))
        counts[base] = count + 1
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check-preservation', action='store_true',
                        help='Compare source/evidence to the consolidation operation baseline')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != ROOT / 'evidence' or output.exists():
        raise ValueError('Use a new receipt directly under project evidence')
    receipt = json.loads((ROOT / 'evidence/documentation_consolidation_20261013.json').read_text())
    failures, links = [], 0
    for name in DOCUMENTS:
        path = ROOT / name
        if not path.is_file():
            failures.append('Missing active document: ' + name)
            continue
        for target in re.findall(r'\[[^\]]+\]\(([^)\n]+)\)', path.read_text(encoding='utf-8')):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            destination, _, fragment = unquote(target).partition('#')
            resolved = (path.parent / destination).resolve() if destination else path
            links += 1
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                failures.append(name + ': ' + target)
            elif fragment and resolved.suffix == '.md' and fragment not in headings(resolved):
                failures.append('Missing section: ' + name + ': ' + target)
            elif fragment and resolved.suffix == '.py' and re.fullmatch(r'L\d+', fragment):
                if int(fragment[1:]) > len(resolved.read_text(encoding='utf-8-sig').splitlines()):
                    failures.append('Missing source line: ' + target)
    for row in receipt['moved_files'] + receipt['control_document_backups']:
        path = (ROOT / row['to']).resolve()
        if not path.is_relative_to(ROOT / 'docs/archive') or not path.is_file() or sha(path) != row['sha256']:
            failures.append('Changed archived bytes: ' + row['to'])
    protected = 0
    if args.check_preservation:
        for name, digest in receipt['protected_files_sha256'].items():
            path = ROOT / name
            protected += 1
            if not path.is_file() or sha(path) != digest:
                failures.append('Changed during consolidation: ' + name)
    for folder in ('deliverables', 'planning', 'code', 'report', 'presentation'):
        path = ROOT / folder
        if folder == 'deliverables' and list(path.glob('*.md')):
            failures.append('Loose deliverable Markdown was recreated')
        if (path / 'README.md').exists():
            failures.append('Duplicate folder README was recreated: ' + folder)
    config = json.loads((ROOT / 'deliverables/current_delivery.json').read_text())
    for kind in ('report', 'presentation'):
        review = json.loads((ROOT / config[kind + '_receipt']).read_text())
        if sha(ROOT / review['output']) != review['pdf_sha256']:
            failures.append('Changed reviewed PDF: ' + kind)
        for name, digest in review['compiled_source_files'].items():
            if sha(ROOT / name) != digest:
                failures.append('Changed reviewed PDF source: ' + name)
    value = {'schema': 'investify-consolidated-documentation-validation-v1',
             'checked_utc': datetime.now(timezone.utc).isoformat(), 'active_documents': DOCUMENTS,
             'local_links_checked': links,
             'archived_files_checked': len(receipt['moved_files']) + len(receipt['control_document_backups']),
             'protected_files_checked': protected,
             'reviewed_pdf_sources_unchanged': not any('Changed reviewed PDF' in item for item in failures),
             'failures': failures, 'passed': not failures}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    print(f'Documentation: {len(DOCUMENTS)} entries, {links} links, {protected} protected files; {len(failures)} failures')
    if failures:
        print('\n'.join(failures))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
