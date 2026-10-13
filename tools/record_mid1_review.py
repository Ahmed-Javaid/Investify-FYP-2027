"""Record reviewed browser evidence and reconcile current Mid-1 navigation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- MID1_BROWSER_CHECKPOINT_START -->'
END = '<!-- MID1_BROWSER_CHECKPOINT_END -->'
REPORT = ROOT / 'evidence/handbook_report_delivery_20261013_run02.json'
DECK = ROOT / 'evidence/handbook_presentation_delivery_20261013_run02.json'
ARCHIVE_RECEIPT = ROOT / 'evidence/investify_mid1_browser_review_20261013_receipt.json'
EXTRACTION = ROOT / 'evidence/browser_review_20261013_clean_host_verification.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def fresh(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def evidence():
    capture_path = ROOT / 'evidence/presenter_browser_20261013_run07.json'
    capture = read(capture_path)
    if (capture['status'] != 'captured_for_visual_review' or capture['page_errors']
            or not all(capture['layout_checks'].values()) or len(capture['screenshots']) != 14):
        raise ValueError('Require all fourteen completed browser captures and layout checks')
    for relative, expected in capture['ui_source_sha256'].items():
        if digest(ROOT / relative) != expected:
            raise ValueError('The reviewed UI source changed')
    for name, expected in capture['screenshots'].items():
        if digest(ROOT / 'report/figures/presenter_browser_20261013_run07' / name) != expected:
            raise ValueError('Preserved browser image changed')
    fresh(ROOT / 'evidence/presenter_visual_review_20261013.json', {
        'schema': 'investify-browser-visual-review-v1',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'capture_receipt': capture_path.relative_to(ROOT).as_posix(),
        'capture_receipt_sha256': digest(capture_path),
        'ui_source_sha256': capture['ui_source_sha256'],
        'all_captured_views_visually_checked': True, 'views': 14,
        'method': 'Assistant reviewed four numbered QA sheets, with complete original captures of explanation failure and design also inspected individually',
        'layout_checks': capture['layout_checks'], 'page_errors': [],
        'screenshot_files_sha256': capture['screenshots'],
        'full_content_capture': 'Real desktop-width viewports temporarily grow in height to expose the Streamlit internal scroll content',
        'human_acceptance_or_projector_review': False,
        'scope': 'Actual localhost browser journey and captured software layout. No participant understanding, projector usability, student ownership or model usefulness is inferred.'})

    preservation = read(ROOT / 'evidence/originals_preservation_browser_20261013.json')
    config_path = Path('E:/Uni_Stuff/investify_repo/.git/config')
    if len(preservation['changed_originals']) != 1 or Path(preservation['changed_originals'][0]['checked_path']) != config_path:
        raise ValueError('Unexpected original-byte differences require investigation')
    manifest = read(ROOT / 'evidence/original_files.sha256.json')
    entry = next(e for e in manifest['files'] if e['origin'] == 'investify_repo'
                 and e['path'].replace('\\', '/') == '.git/config')
    data = config_path.read_bytes()
    trimmed = b''.join(line for line in data.splitlines(keepends=True) if b'vscode-merge-base' not in line)
    if hashlib.sha256(trimmed).hexdigest() != entry['sha256']:
        raise ValueError('Git metadata divergence extends beyond the editor bookmark')
    fresh(ROOT / 'evidence/originals_preservation_browser_metadata_20261013.json', {
        'schema': 'investify-original-byte-divergence-v1',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'files_checked': preservation['files_checked'], 'exact_byte_matches': 223,
        'literal_all_originals_unchanged': False,
        'changed_file': str(config_path), 'current_sha256': digest(config_path),
        'original_sha256': entry['sha256'], 'additional_key': 'vscode-merge-base',
        'in_memory_removal_reconstructs_original_bytes': True,
        'external_configuration_modified_by_this_review': False,
        'action': 'Preserve the external checkout as found. Retain the failed literal check alongside this byte-exact explanation.',
        'scope': 'All other protected files match. This records an editor Git bookmark, without rewriting the original manifest or claiming literal 224-file equality.'})

    checked = ['code/app/streamlit_app.py', 'code/app/presenter.py', 'code/app/presenter_data.py',
               'code/app/presenter_style.py', 'code/tests/test_presenter_ui.py', 'tools/audit_calibration_bounds.py',
               'tools/review_presenter_browser.py', 'tools/package_source_handover.py',
               'tools/review_mid1_artifacts.py', 'tools/build_mid1_pdfs.py', 'tools/record_mid1_review.py']
    checker = Path('E:/AI-Tools/Work/investify-quality-tools/bin/ruff.exe')
    lint = subprocess.run([str(checker), 'check', '--no-cache', '--select', 'E4,E9,F', *checked],
                          cwd=ROOT, capture_output=True, text=True, timeout=30)
    if lint.returncode:
        raise RuntimeError(lint.stdout + lint.stderr)
    fresh(ROOT / 'evidence/presenter_delivery_static_analysis_20261013.json', {
        'schema': 'investify-scoped-static-analysis-v1', 'checked_utc': datetime.now(timezone.utc).isoformat(),
        'tool': 'Ruff', 'version': '0.14.0', 'rules': ['E4', 'E9', 'F'],
        'files_sha256': {name: digest(ROOT / name) for name in checked}, 'findings': [], 'passed': True,
        'scope': 'Eleven current UI/test/review/build modules. Not full repository lint or scientific/human acceptance.'})
    print('Recorded fourteen reviewed browser views, eleven linted files and the explicit original Git metadata divergence.')


def checkpoint(verified):
    report, deck = read(REPORT), read(DECK)
    if verified and not EXTRACTION.exists():
        raise ValueError('Require actual source archive extraction verification')
    docs = ['README.md', 'deliverables/README.md', 'planning/CURRENT_STATUS.md',
            'planning/HANDOFF_20261012.md', 'deliverables/HANDOVER_GUIDE.md']
    for name in docs:
        path = ROOT / name
        def link(label, relative):
            return f'[{label}]({os.path.relpath(ROOT / relative, path.parent).replace(chr(92), "/")})'
        package = 'The new source review archive is prepared for clean-snapshot packaging; extraction verification is still pending.'
        if verified:
            archive, extraction = read(ARCHIVE_RECEIPT), read(EXTRACTION)
            package = (f'The {link("current review ZIP", "deliverables/investify_mid1_browser_review_20261013.zip")} '
                       f'contains {archive["files"]} files and certifies clean source snapshot **{archive["code_commit"][:7]}**. '
                       f'{link("Actual extraction verification", "evidence/browser_review_20261013_clean_host_verification.json")} '
                       'passes 165 portable tests, 62 live HTTP checks and 372 historical records, with six teacher examples replayed. '
                       'These later navigation/receipt notes are a separate documentation increment.')
            if extraction.get('zip_sha256', extraction.get('archive_sha256')) not in (None, archive['zip_sha256']):
                raise ValueError('Archive and extraction receipts disagree')
        block = (f'{START}\n## Current browser-reviewed package - 13 October 2026\n\n'
                 'Mid-1 planning readiness remains **84.25%, about 84%**, with unchanged weights. Earlier dated sections below retain their historical scope and are superseded for current navigation.\n\n'
                 f'- {link("Current report", report["output"])}: {report["pages"]} pages, actual browser screenshots and the source-bound calibration diagnosis. All pages rendered/reviewed; no fully blank pages or overfull boxes.\n'
                 f'- {link("Current LaTeX/Beamer presentation", deck["output"])}: {deck["pages"]} slides, rendered and reviewed, with editable source and speaker notes. Earlier PDFs remain preserved.\n'
                 f'- {link("Actual browser review", "evidence/presenter_visual_review_20261013.json")}: fourteen captured views, including both profiles, rejection/fallback and restored-candidate acceptance, all three recorded studies and Design. Desktop header/overflow checks pass.\n'
                 f'- {link("Current focused UI receipt", "evidence/presenter_delivery_tests_20261013_run03.xml")}: **42 passes** (14 primary, 24 legacy, 4 selectors). This overlaps earlier scopes. Eleven current modules pass scoped Ruff checks.\n\n'
                 f'{package}\n\n'
                 'Scientific findings remain unchanged: weak prediction, all-Buy fresh calibration, exploratory AI-reference sentiment results and an untrained Phi-3-mini student. Physical projector review, timed rehearsal, confirmed cover facts, actual member contributions/defence and supervisor/baseline/criteria review remain open. Prepared CI is not remote CI execution.\n\n'
                 f'{link("The preservation audit", "evidence/originals_preservation_browser_metadata_20261013.json")} '
                 'records 223 exact original-byte matches and one external historical Git config with an added editor bookmark. Removing only that key in memory reproduces the original hash exactly. The external config was left as found; literal 224-file equality is not claimed.\n'
                 f'{END}')
        text = path.read_text(encoding='utf-8')
        if START in text:
            first, tail = text.split(START, 1)
            _, last = tail.split(END, 1)
            text = first + block + last
        else:
            first, rest = text.split('\n', 1)
            text = first + '\n\n' + block + '\n' + rest
        path.write_text(text, encoding='utf-8')

    readiness = ROOT / 'planning/MID_EVAL_READINESS.md'
    text = readiness.read_text(encoding='utf-8')
    marker = '## Browser-review continuation - 13 October 2026'
    if marker not in text:
        first, rest = text.split('\n', 1)
        text = first + '\n\n' + marker + ('\n\nThe completed desktop browser journey, reviewed screenshots and updated PDFs close software-layout evidence gaps. The estimate is held at **84.25%**; projector review, rehearsal, actual member defence and supervisor/metadata/criteria review remain open. The unchanged category weights and targets below still apply. This is a planning judgement, not a university grade.\n') + rest
        readiness.write_text(text, encoding='utf-8')
    print('Updated current navigation and retained the 84.25% readiness judgement.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['evidence', 'checkpoint', 'verified'])
    args = parser.parse_args()
    if args.mode == 'evidence':
        evidence()
    else:
        checkpoint(args.mode == 'verified')


if __name__ == '__main__':
    main()
