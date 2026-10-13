"""Package tracked code and working report/evidence sources, with file hashes."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
SCRATCH = Path('E:/AI-Tools/Temp').resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'deliverables/investify_mideval_source.zip')
    parser.add_argument('--working-tree', action='store_true', help='Explicit uncommitted review bundle, never a HEAD snapshot')
    current = json.loads((ROOT / 'deliverables/current_delivery.json').read_text(encoding='utf-8'))
    parser.add_argument('--report-receipt', type=Path, default=ROOT / current['report_receipt'])
    parser.add_argument('--presentation-receipt', type=Path, default=ROOT / current['presentation_receipt'])
    parser.add_argument('--scratch-directory', type=Path, default=Path('E:/AI-Tools/Temp'))
    args = parser.parse_args()
    scratch = args.scratch_directory.resolve()
    if not scratch.is_dir():
        raise ValueError('Prepared scratch directory is unavailable')
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'deliverables') or output.suffix != '.zip':
        raise ValueError('Deliverable ZIP must remain in this workspace deliverables directory')
    receipt_path = ROOT / 'evidence' / (output.stem + '_receipt.json' if args.working_tree or output.name != 'investify_mideval_source.zip' else 'source_bundle_receipt.json')
    if output.exists() or receipt_path.exists():
        raise ValueError('Preserve prior archives/receipts; choose a new dated output filename')
    for path in (args.report_receipt, args.presentation_receipt):
        if not path.resolve().is_relative_to(ROOT / 'evidence'):
            raise ValueError('Use document review receipts within project evidence')
    dirty = subprocess.check_output(['git', '-C', str(CODE), 'status', '--porcelain'], text=True).strip()
    if dirty and not args.working_tree:
        raise ValueError('Commit/review current code before packaging; do not label a dirty tree as a commit snapshot')
    commit = subprocess.check_output(['git', '-C', str(CODE), 'rev-parse', 'HEAD'], text=True).strip()
    listing = ['git', '-C', str(CODE), 'ls-files', '-z']
    if args.working_tree:
        listing += ['--cached', '--others', '--exclude-standard']
    tracked = subprocess.check_output(listing).decode().split('\0')
    if args.working_tree:
        deleted = set(subprocess.check_output(['git', '-C', str(CODE), 'ls-files', '-z', '--deleted']).decode().split('\0'))
        tracked = [relative for relative in tracked if relative not in deleted]
    tracked = [relative for relative in tracked if relative and relative != 'source_revision.json']
    with tempfile.TemporaryDirectory(prefix='investify-package-', dir=scratch) as directory:
        stage = Path(directory).resolve()
        if not stage.is_relative_to(scratch) or not stage.name.startswith('investify-package-'):
            raise ValueError('Scratch path failed storage/cleanup validation')
        bundle = stage / 'InvestifyMidEval'
        code_inventory = {}
        for relative in tracked:
            source = (CODE / relative).resolve()
            target = (bundle / 'code' / relative).resolve()
            if not source.is_relative_to(CODE) or not target.is_relative_to(bundle):
                raise ValueError('Tracked code path escapes the intended source/staging roots')
            if source.name == '.env' or source.suffix in ('.pyc', '.gguf', '.safetensors'):
                raise ValueError('Unexpected credential/cache/model file in tracked delivery sources')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            code_inventory[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
        revision = {'schema': 'investify-source-revision-v1', 'commit': commit, 'files': code_inventory}
        if args.working_tree:
            revision.update(schema='investify-working-source-revision-v2', working_tree=True)
        (bundle / 'code/source_revision.json').write_text(json.dumps(revision, indent=2), encoding='utf-8')
        for folder in ('report', 'presentation', 'docs/team', 'docs/technical', 'docs/handoffs'):
            for source in (ROOT / folder).rglob('*'):
                if source.is_file() and source.suffix not in ('.aux', '.log', '.out', '.toc', '.synctex'):
                    relative = source.relative_to(ROOT)
                    target = bundle / relative
                    if not source.resolve().is_relative_to(ROOT / folder) or not target.resolve().is_relative_to(bundle):
                        raise ValueError('Report/planning path escapes its declared root')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
        for name in ('presentation_outline.json', 'social_annotation_protocol.json', 'current_delivery.json',
                     'stocknet_source_access.json', 'stocknet_source_access_v2.json'):
            target = bundle / 'deliverables' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / 'deliverables' / name, target)
        # Deliver current evidence and inputs; retired archives and obsolete
        # document exports are recovered from Git history, not repackaged.
        for folder in ('evidence', 'sources/stocknet', 'sources/historical_science_20261012', 'tools'):
            for source in (ROOT / folder).rglob('*'):
                if source.is_file() and source.suffix not in ('.pyc', '.zip'):
                    target = bundle / source.relative_to(ROOT)
                    if not source.resolve().is_relative_to(ROOT / folder) or not target.resolve().is_relative_to(bundle):
                        raise ValueError('Delivery input escaped its declared root')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
        for relative in ('sources/BS-FYP-Handbook-2026_DRAFT.pdf',
                         '.github/workflows/mideval-evidence.yml', 'AGENTS.md',
                         'sources/Investify_Proposal_Full.docx', 'sources/Investify_Concept.docx',
                         'sources/Investify Updated (1).pptx',
                         'sources/Mid_Eval/PROPOSAL_ACTION_REGISTER.md',
                         'sources/Mid_Eval/FYP-1-Mid-Assessment-Guidelines-and-Rubrics.pdf'):
            target = bundle / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        report_receipt = json.loads(args.report_receipt.read_text(encoding='utf-8'))
        current_report = (ROOT / report_receipt['output']).resolve()
        if (not current_report.is_relative_to(ROOT / 'deliverables')
                or not report_receipt['all_pages_visually_checked']
                or report_receipt['status'] not in ('compiled_and_layout_reviewed_unsigned_working_draft', 'compiled_and_layout_reviewed_submission_copy')
                or hashlib.sha256(current_report.read_bytes()).hexdigest() != report_receipt['pdf_sha256']):
            raise ValueError('Current report must match its reviewed source/PDF receipt')
        shutil.copyfile(current_report, bundle / 'deliverables' / current_report.name)
        deck_receipt = json.loads(args.presentation_receipt.read_text(encoding='utf-8'))
        current_deck = (ROOT / deck_receipt['output']).resolve()
        if (not current_deck.is_relative_to(ROOT / 'deliverables')
                or not deck_receipt['all_pages_visually_checked']
                or hashlib.sha256(current_deck.read_bytes()).hexdigest() != deck_receipt['pdf_sha256']):
            raise ValueError('Current presentation must match its reviewed Beamer receipt')
        shutil.copyfile(current_deck, bundle / 'deliverables' / current_deck.name)
        for kind, reviewed in (('report', report_receipt), ('presentation', deck_receipt)):
            for relative, expected in reviewed['compiled_source_files'].items():
                source = (ROOT / relative).resolve()
                if (not source.is_relative_to(ROOT / kind)
                        or hashlib.sha256(source.read_bytes()).hexdigest() != expected):
                    raise ValueError('Compiled artifact source changed since visual review: ' + relative)
        shutil.copyfile(ROOT / 'README.md', bundle / 'README.md')
        files = {str(path.relative_to(bundle)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(bundle.rglob('*')) if path.is_file()}
        manifest = {'built_utc': datetime.now(timezone.utc).isoformat(), 'code_commit': commit,
                    'code_snapshot_kind': 'uncommitted_working_tree' if args.working_tree else 'clean_commit_snapshot',
                    'files': files, 'scope': f'Current Mid-1 review with four-step Streamlit UI, calibration diagnostics, separately executed fresh Alpaca science, original CryptoBERT/Cardiff outputs and six teacher examples. Dated receipts distinguish overlapping scopes. The {report_receipt["pages"]}-page report and {deck_receipt["pages"]}-slide LaTeX/Beamer deck are compiled/layout-reviewed authored copies. Browser capture/review evidence has its own source-bound receipt; physical projector review, rehearsal, student training and human/institutional acceptance remain open. Publisher weights, E: caches and ignored raw acquisition inputs are external prerequisites for fresh inference/training replay. Private review archive; third-party corpus is not approved for public redistribution.',
                    'document_receipts': {'report': str(args.report_receipt.resolve().relative_to(ROOT)).replace('\\','/'), 'presentation': str(args.presentation_receipt.resolve().relative_to(ROOT)).replace('\\','/')},
                    'rendered_visual_qa': False, 'institutional_report_rendered_visual_qa': True, 'beamer_presentation_rendered_visual_qa': True}
        (bundle / 'bundle_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob('*')):
                if path.is_file():
                    archive.write(path, str(path.relative_to(stage)).replace('\\', '/'))
    receipt = {'built_utc': manifest['built_utc'], 'code_commit': commit, 'files': len(files) + 1,
               'code_snapshot_kind': manifest['code_snapshot_kind'],
               'zip_bytes': output.stat().st_size, 'zip_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
               'scope': manifest['scope'], 'source_inventory_files': len(code_inventory)}
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    label = 'uncommitted review, base HEAD' if args.working_tree else 'clean commit'
    print(f'Source bundle: {output}; {receipt["files"]} files; {label} {commit[:7]}')


if __name__ == '__main__':
    main()
