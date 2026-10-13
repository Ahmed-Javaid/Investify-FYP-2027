"""Package reviewed Mid-1 documents and practice guides; source comes from GitHub."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import posixpath
import re
import subprocess
from urllib.parse import quote
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/Ahmed-Javaid/Investify-FYP-2027'
GUIDES = {'docs/team/MID1_TEAM_GUIDE.md': 'TEAM_GUIDE.md',
          'docs/technical/ENGINEERING.md': 'technical/ENGINEERING.md',
          'docs/technical/RESEARCH.md': 'technical/RESEARCH.md',
          'docs/technical/REQUIREMENTS.md': 'technical/REQUIREMENTS.md'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != ROOT / 'deliverables' or output.suffix != '.zip' or output.exists():
        raise ValueError('Choose a new ZIP directly under project deliverables')
    receipt_path = ROOT / 'evidence' / (output.stem + '_receipt.json')
    if receipt_path.exists():
        raise ValueError('Preserve earlier package receipts')
    config = json.loads((ROOT / 'deliverables/current_delivery.json').read_text())
    contents = {}
    source_files = {}
    page_counts = {}
    aliases = {}
    for kind, alias in (('report', 'Investify_Report.pdf'),
                        ('presentation', 'Investify_Presentation.pdf')):
        reviewed = json.loads((ROOT / config[kind + '_receipt']).read_text())
        page_counts[kind] = reviewed['pages']
        relative = reviewed['output']
        path = (ROOT / relative).resolve()
        if path.parent != ROOT / 'deliverables' or not reviewed['all_pages_visually_checked']:
            raise ValueError('Use the currently reviewed PDFs')
        raw = path.read_bytes()
        if sha(raw) != reviewed['pdf_sha256']:
            raise ValueError('Reviewed PDF changed: ' + relative)
        contents[alias] = raw
        source_files[relative] = sha(raw)
        aliases[relative] = alias
    rubric = 'sources/Mid_Eval/FYP-1-Mid-Assessment-Guidelines-and-Rubrics.pdf'
    raw = (ROOT / rubric).read_bytes()
    audit = json.loads((ROOT / 'evidence/handbook_mid1_audit_20261013.json').read_text())
    expected = next(row['sha256'] for row in audit['sources'] if row['path'] == rubric)
    if sha(raw) != expected:
        raise ValueError('Committee rubric differs from the preserved audit source')
    contents['Mid1_Rubric.pdf'] = raw
    source_files[rubric] = sha(raw)
    aliases[rubric] = 'Mid1_Rubric.pdf'
    aliases.update(GUIDES)
    for relative, name in GUIDES.items():
        raw = (ROOT / relative).read_bytes()
        source_files[relative] = sha(raw)

        def replace_link(match):
            label, target = match.groups()
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                return match.group(0)
            destination, separator, anchor = target.partition('#')
            resolved = posixpath.normpath(posixpath.dirname(relative) + '/' + destination)
            if resolved.startswith('../') or resolved.startswith('/'):
                raise ValueError('Guide link escapes the source repository')
            new_target = aliases.get(resolved)
            if new_target is None:
                new_target = REPOSITORY + '/blob/main/' + quote(resolved, safe='/')
            else:
                new_target = posixpath.relpath(new_target, posixpath.dirname(name) or '.')
            if separator:
                new_target += '#' + anchor
            return f'[{label}]({new_target})'

        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace_link, raw.decode('utf-8'))
        contents[name] = text.encode('utf-8')
    contents['READ_FIRST.txt'] = (f'''INVESTIFY MID-1 GROUPMATE PACK

Extract this ZIP. Start with TEAM_GUIDE.md for setup, demo, speaking schedule,
your member section, code reading, questions and the team todo.

Investify_Report.pdf: current {page_counts['report']}-page report.
Investify_Presentation.pdf: current {page_counts['presentation']}-slide deck.
Mid1_Rubric.pdf: official committee assessment criteria.
technical/: implementation, research and requirements references.

Source: https://github.com/Ahmed-Javaid/Investify-FYP-2027
Clone/run instructions are in TEAM_GUIDE.md. No GPU/API keys/model downloads
are needed for the recorded demo. Initial dependency installation needs internet.

Report date: 11 October 2026; actual revisions/tests retain their dates.
Predictions/studies are recorded; profile arithmetic and checking run live.
The full FYP continues beyond this checkpoint. Print/sign after real review.
manifest.json records hashes. Code, datasets, weights and old notes are excluded.
''').encode('utf-8')
    manifest = {'schema': 'investify-groupmate-document-pack-v1',
                'built_utc': datetime.now(timezone.utc).isoformat(),
                'source_repository': REPOSITORY,
                'source_repository_head_at_packaging': subprocess.check_output(
                    ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                'scope': 'Reviewed documents and practice guides; source code is obtained from GitHub.',
                'source_files_sha256': source_files,
                'files_sha256': {name: sha(raw) for name, raw in contents.items()}}
    contents['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode('utf-8')
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(contents.items()):
            archive.writestr('Investify_Mid1_Groupmates/' + name, raw)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != len(contents):
            raise ValueError('Archive integrity failed')
        for name, raw in contents.items():
            if archive.read('Investify_Mid1_Groupmates/' + name) != raw:
                raise ValueError('Packaged file differs from prepared bytes')
    receipt = {**manifest, 'output': output.relative_to(ROOT).as_posix(),
               'zip_sha256': sha(output.read_bytes()), 'zip_bytes': output.stat().st_size,
               'file_count': len(contents), 'archive_integrity': 'passed',
               'pdfs_and_rubric_preserved_byte_for_byte': True}
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(f'Groupmate pack: {output}; {len(contents)} files; {output.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
