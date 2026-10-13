"""Point current navigation to the proposal-division and executed-CI review."""
import argparse
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
    parser.add_argument('--delivery-run-id', default='20261013_run03')
    parser.add_argument('--archive-id', default='ci_work_division_review_20261013')
    parser.add_argument('--member-allocation', action='store_true')
    parser.add_argument('--fall-metadata', action='store_true')
    args = parser.parse_args()
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in (args.delivery_run_id, args.archive_id)):
        raise ValueError('Use plain dated receipt identities')
    report = read(f'evidence/handbook_report_delivery_{args.delivery_run_id}.json')
    deck = read(f'evidence/handbook_presentation_delivery_{args.delivery_run_id}.json')
    portable = read('evidence/ci_replay_20261013_run02/evidence/job_receipt.json')
    ui = read('evidence/ci_replay_20261013_run02/streamlit-ui/job_receipt.json')
    if any(r['status'] != 'passed' or r['execution_location'] != 'local_replay'
           or not r['temporary_component_metadata_restored'] for r in (portable, ui)):
        raise ValueError('Require completed local CI jobs with restored temporary declarations')
    docs = ['README.md', 'code/README.md', 'deliverables/README.md', 'planning/CURRENT_STATUS.md',
            'planning/HANDOFF_20261012.md', 'deliverables/HANDOVER_GUIDE.md']
    for name in docs:
        path = ROOT / name
        def link(label, relative):
            return f'[{label}]({os.path.relpath(ROOT / relative, path.parent).replace(chr(92), "/")})'
        archive_line = 'The new source ZIP is being prepared; extraction verification is pending.'
        if args.verified:
            archive_name = f'investify_mid1_{args.archive_id}'
            archive = read(f'evidence/{archive_name}_receipt.json')
            verification = read(f'evidence/{args.archive_id}_clean_host_verification.json')
            if archive['zip_sha256'] != verification['archive_sha256']:
                raise ValueError('Archive and extraction evidence disagree')
            archive_line = (f'{link("Current source ZIP", f"deliverables/{archive_name}.zip")}: '
                            f'{archive["files"]} files, clean snapshot **{archive["code_commit"][:7]}**. '
                            f'{link("Actual extraction review", f"evidence/{args.archive_id}_clean_host_verification.json")} '
                            f'passes {verification["portable_tests_passed"]} portable tests, {verification["live_checks_passed"]} HTTP checks '
                            f'and {verification["records_validated"]} historical records. Later receipt/navigation notes are a separate increment.')
        allocation_line = ''
        heading = 'Current proposal division and local CI'
        remaining = 'cover/session/coordinator/co-supervisor facts, actual member contributions/defence'
        if args.member_allocation:
            allocation = read('evidence/equal_member_allocation_20261013.json')
            if len(allocation['members']) != 3 or any(m['planned_speaking_seconds'] != 300 for m in allocation['members']):
                raise ValueError('Require the equal team allocation receipt')
            heading = 'Current equal member allocation and confirmed team'
            remaining = 'session/cohort, coordinator and assessment date; actual individual review/code defence'
            allocation_line = (f'- {link("Member preparation packets", "deliverables/MEMBER_PREPARATION_PACK.md")}: equal **one-third** assigned responsibility, four primary slides and five minutes of speaking each, including shared demo segments. Three individual handouts specify files, tests and likely questions. The team confirms names/roll numbers and supervisor; **no co-supervisor** applies.\n'
                               f'- {link("Functional status", "deliverables/MID1_FUNCTIONAL_STATUS.md")}: the current recorded Mid-1 prototype is ready for practice. Predictive usefulness, student training and deployment remain unresolved or later work.\n')
        if args.fall_metadata:
            metadata = read('evidence/fall_report_metadata_20261013.json')
            if metadata['report_date'] != '2026-10-11' or not metadata['execution_dates_preserved']:
                raise ValueError('Require team-supplied report metadata with preserved execution dates')
            heading = 'Current Fall 2026 Mid-1 report and equal member allocation'
            remaining = 'current coordinator/submission details and actual individual review/code defence'
            allocation_line += (f'- {link("Report metadata", "deliverables/REPORT_METADATA.md")}: **FYP-1 Mid-Evaluation, Fall 2026**. Team-selected report date: **11 October 2026 (Sunday)**. Actual revision/test dates are retained; the formal committee appointment is separate.\n')
        block = (f'{START}\n## {heading} - 13 October 2026\n\n'
                 'Mid-1 planning readiness remains **84.25%**, using the original weights. Work assignments are filled; actual member preparation and defence will be recorded during practice. Earlier dated sections below retain their historical scope.\n\n'
                 f'- {link("Current report", report["output"])}: **{report["pages"]} pages**, with the original planned work-division table, actual UI captures and local CI evidence. All pages rendered/reviewed, with no overfull boxes or fully blank pages.\n'
                 f'- {link("Current presentation", deck["output"])}: **{deck["pages"]} LaTeX/Beamer slides**, including the proposal assignments on the final slide. Source and speaker notes remain editable.\n'
                 f'- {link("Work division", "deliverables/WORK_DIVISION.md")}: three members and fifteen exact responsibilities recovered from proposal slide 13 using SmartArt parent/child connections. Planned harness ownership and historical authorship remain distinct.\n'
                 f'- {link("CI/CD status", "deliverables/CI_CD_STATUS.md")}: both shared CI jobs execute successfully on the local Windows runtime. Portable scope: **165 tests + 7 CI guards**, 62 live HTTP checks, 372 saved records and 228 comparator probes. UI scope: **42 tests**. These scopes overlap other receipts. GitHub/Ubuntu execution and continuous deployment remain unexecuted.\n'
                 f'- {link("Route to 90% and 95%", "deliverables/MID1_90_95_ROADMAP.md")}: unchanged-weight conditional scenarios of **90.25%** and **95.00%**, with the genuine review/acceptance requirements listed explicitly.\n\n'
                 f'{allocation_line}\n'
                 f'{archive_line}\n\n'
                 f'Remaining inputs: {remaining}, physical projector/timed rehearsal and supervisor baseline/criteria/proposal-action review. Scientific findings, frozen inputs and labels remain unchanged; weak prediction, all-Buy calibration, AI-reference sentiment limits and untrained Phi-3-mini are still disclosed. Original PDFs/ZIPs and dated receipts remain preserved.\n'
                 f'{END}')
        text = path.read_text(encoding='utf-8')
        if START in text:
            first, rest = text.split(START, 1)
            _, last = rest.split(END, 1)
            text = first + block + last
        else:
            first, rest = text.split('\n', 1)
            text = first + '\n\n' + block + '\n' + rest
        path.write_text(text, encoding='utf-8')
    if args.member_allocation:
        outline = read('deliverables/presentation_outline.json')
        for item in outline['slides']:
            item['primary_presenter'] = 'Rafay Ul Haq' if item['number'] == 8 else item['assigned_presenter']
        outline.update(status='Twelve-slide equal-allocation PDF compiled and layout reviewed; individual practice and rehearsal remain pending.',
                       compiled_output=deck['output'], delivery_receipt=f'evidence/handbook_presentation_delivery_{args.delivery_run_id}.json')
        (ROOT / 'deliverables/presentation_outline.json').write_text(json.dumps(outline, indent=2) + '\n', encoding='utf-8')
    print('Updated current report/deck, proposal assignments, local CI evidence and conditional readiness routes.')


if __name__ == '__main__':
    main()
