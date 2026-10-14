"""Report the user's technical completion definition, preserving historical readiness estimates."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- MID1_BROWSER_CHECKPOINT_START -->'
END = '<!-- MID1_BROWSER_CHECKPOINT_END -->'


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verified', action='store_true')
    parser.add_argument('--package-receipt', type=Path)
    parser.add_argument('--extraction-receipt', type=Path)
    parser.add_argument('--hosted-receipt', type=Path)
    args = parser.parse_args()
    if args.verified:
        if not args.package_receipt or not args.extraction_receipt:
            parser.error('--verified requires --package-receipt and --extraction-receipt')
        archive = json.loads(args.package_receipt.read_text(encoding='utf-8'))
        checked = json.loads(args.extraction_receipt.read_text(encoding='utf-8'))
        if archive['zip_sha256'] != checked['archive_sha256']:
            raise ValueError('Archive/extraction receipt mismatch')
    config = read('deliverables/current_delivery.json')
    report = read(config['report_receipt'])
    deck = read(config['presentation_receipt'])
    for value in (report, deck):
        if not value['all_pages_visually_checked'] or hashlib.sha256((ROOT / value['output']).read_bytes()).hexdigest() != value['pdf_sha256']:
            raise ValueError('Require current visually reviewed PDFs')
    hosted = None
    if args.hosted_receipt:
        hosted = json.loads(args.hosted_receipt.read_text(encoding='utf-8'))
        if hosted['conclusion'] != 'success' or hosted['passed_jobs'] != 5 or not hosted['delivery_artifact']:
            raise ValueError('Require successful hosted matrix and delivery evidence')
    percent = 100 if hosted else None
    current = {'schema': 'investify-mid1-technical-completion-v1', 'definition': 'User-defined technical scope, replacing the earlier mixed readiness score.',
               'technical_completion_percent': percent, 'code': 'implemented and locally checked',
               'report': 'complete authored content, compiled and visually reviewed',
               'required_modules': 'implemented with separate execution evidence',
               'ci_cd': 'hosted tests and artifact delivery passed' if hosted else 'configured; hosted verification pending',
               'excluded_team_todo': 'docs/TEAM_GUIDE.md#team-tasks',
               'report_output': report['output'], 'presentation_output': deck['output'],
               'hosted_run': hosted['html_url'] if hosted else None,
               'limits': ['Mid-1 technical completion, not full FYP completion or a university grade.',
                          'Weak prediction, historical isotonic collapse, current uncertainty/abstention and reference-label limits remain disclosed.',
                          'No signatures, supervisor approval, participant benefit or completed student training inferred.']}
    (ROOT / 'evidence/mid1_technical_completion_current.json').write_text(json.dumps(current, indent=2) + '\n', encoding='utf-8')
    summary = '**100% technical Mid-1 completion**' if hosted else '**Technical scope implemented; hosted CI/CD verification pending**'
    path = ROOT / 'docs/AGENT_HANDOFF.md'
    run = (f'[Retained hosted run]({hosted["html_url"]}) passes all five jobs.'
           if hosted else 'Hosted execution remains pending; configuration is not execution evidence.')
    block = (f'{START}\n{summary} under the user-defined code/report/CI-CD/module scope. '
             'This is not whole-FYP completion, useful prediction or a grade. '
             f'{run} Later working-tree changes need their own checks.\n'
             '[Machine status](../evidence/mid1_technical_completion_current.json).\n'
             f'{END}')
    content = path.read_text(encoding='utf-8')
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError('The consolidated handoff must contain one status block')
    first, rest = content.split(START, 1)
    _, last = rest.split(END, 1)
    path.write_text(first + block + last, encoding='utf-8')
    outline = read('deliverables/presentation_outline.json')
    notes = re.findall(r'\\note\{(.*?)\}\s*\\end\{frame\}', (ROOT / 'presentation/main.tex').read_text(), re.S)
    assert len(notes) == len(outline['slides']) == 12
    for item, note in zip(outline['slides'], notes):
        item['speaker_notes'] = note
    outline.update(compiled_output=deck['output'], status='Compiled and layout reviewed technical Mid-1 deck; team tasks remain separate.',
                   delivery_receipt=config['presentation_receipt'])
    (ROOT / 'deliverables/presentation_outline.json').write_text(json.dumps(outline, indent=2) + '\n', encoding='utf-8')
    print(f'Updated technical completion navigation; completion percent={percent}, team todo separate.')


if __name__ == '__main__':
    main()
