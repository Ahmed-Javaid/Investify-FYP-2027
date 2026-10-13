"""Report the user's technical completion definition, preserving historical readiness estimates."""
import argparse
import hashlib
import json
import os
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
    parser.add_argument('--hosted-receipt', type=Path)
    args = parser.parse_args()
    report = read('evidence/handbook_report_delivery_20261013_run06.json')
    deck = read('evidence/handbook_presentation_delivery_20261013_run06.json')
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
               'excluded_team_todo': 'deliverables/MID1_TEAM_TODO.md',
               'report_output': report['output'], 'presentation_output': deck['output'],
               'hosted_run': hosted['html_url'] if hosted else None,
               'limits': ['Mid-1 technical completion, not full FYP completion or a university grade.',
                          'Negative prediction, all-Buy calibration and AI-reference sentiment limits remain disclosed.',
                          'No signatures, supervisor approval, participant benefit or completed student training inferred.']}
    (ROOT / 'evidence/mid1_technical_completion_current.json').write_text(json.dumps(current, indent=2) + '\n', encoding='utf-8')
    summary = '**100% technical Mid-1 completion**' if hosted else '**Technical scope implemented; hosted CI/CD verification pending**'
    docs = ['README.md', 'code/README.md', 'deliverables/README.md', 'planning/CURRENT_STATUS.md',
            'planning/HANDOFF_20261012.md', 'deliverables/HANDOVER_GUIDE.md']
    for name in docs:
        path = ROOT / name
        def link(label, relative):
            return f'[{label}]({os.path.relpath(ROOT / relative, path.parent).replace(chr(92), "/")})'
        delivery = 'A new source handover archive is being prepared. GitHub automatically delivers the reviewed PDFs/source only after all four test jobs pass.'
        if args.verified:
            archive = read('evidence/investify_mid1_technical_review_20261013_receipt.json')
            checked = read('evidence/technical_review_20261013_clean_host_verification.json')
            if archive['zip_sha256'] != checked['archive_sha256']:
                raise ValueError('Archive/extraction receipt mismatch')
            delivery = (f'{link("Verified source archive", "deliverables/investify_mid1_technical_review_20261013.zip")}: '
                        f'{archive["files"]} files, source snapshot **{archive["code_commit"][:7]}**, '
                        f'{checked["portable_tests_passed"]} portable tests, {checked["live_checks_passed"]} HTTP checks and '
                        f'{checked["records_validated"]} records validated. Later navigation receipts are a separate increment.')
        run = (f'[Hosted CI/CD run]({hosted["html_url"]}) passes all five jobs and produces the verified delivery artifact.'
               if hosted else 'Hosted CI/CD is pending the authorized push/run. The two test jobs and nine delivery guards are checked locally; hosted Windows/Ubuntu execution is not inferred.')
        block = (f'{START}\n## Current technical Mid-1 completion - 13 October 2026\n\n'
                 f'{summary}. Completion now means working code, a complete report, working CI/CD and required Mid-1 modules. '
                 'The earlier **84.25%** mixed preparation estimate is historical and no longer governs current completion. Its original weights/receipts remain preserved below.\n\n'
                 f'- {link("Current report", report["output"])}: **{report["pages"]} pages**, coordinator omitted, Fall 2026 and report date 11 October 2026 retained. Current source/PDF/render hashes and visual review match.\n'
                 f'- {link("Current presentation", deck["output"])}: **12 reviewed LaTeX/Beamer slides**, editable source and synchronized member notes.\n'
                 f'- {link("Required modules and technical scope", "deliverables/MID1_TECHNICAL_COMPLETION.md")}: ingestion/calendar/features, baseline/leakage, sentiment comparison, decision/calibration/SHAP, profile comparator and explanation/fallback interfaces have execution evidence.\n'
                 f'- {link("CI/CD status", "deliverables/CI_CD_STATUS.md")}: cross-platform validation followed by gated, extraction-verified source/PDF artifact delivery. {run}\n'
                 f'- {link("Equal member packets", "deliverables/MEMBER_PREPARATION_PACK.md")}: one-third responsibility, four primary slides and five planned speaking minutes each.\n'
                 f'- {link("Team todo", "deliverables/MID1_TEAM_TODO.md")}: printing/signatures, supervisor review, code walkthrough and rehearsal/projector check remain outside this percentage.\n\n'
                 f'{delivery}\n\n'
                 'Scientific limits remain explicit: weak prediction, all-Buy calibration, AI-reference sentiment, no measured user benefit and untrained student. QLoRA and production hosting are later milestones. No human review or signature is inferred.\n'
                 f'{END}')
        content = path.read_text(encoding='utf-8')
        if START in content:
            first, rest = content.split(START, 1)
            _, last = rest.split(END, 1)
            content = first + block + last
        else:
            first, rest = content.split('\n', 1)
            content = first + '\n\n' + block + '\n' + rest
        path.write_text(content, encoding='utf-8')
    outline = read('deliverables/presentation_outline.json')
    notes = re.findall(r'\\note\{(.*?)\}\s*\\end\{frame\}', (ROOT / 'presentation/main.tex').read_text(), re.S)
    assert len(notes) == len(outline['slides']) == 12
    for item, note in zip(outline['slides'], notes):
        item['speaker_notes'] = note
    outline.update(compiled_output=deck['output'], status='Compiled and layout reviewed technical Mid-1 deck; team tasks remain separate.',
                   delivery_receipt='evidence/handbook_presentation_delivery_20261013_run06.json')
    (ROOT / 'deliverables/presentation_outline.json').write_text(json.dumps(outline, indent=2) + '\n', encoding='utf-8')
    print(f'Updated technical completion navigation; completion percent={percent}, team todo separate.')


if __name__ == '__main__':
    main()
