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
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'deliverables') or output.suffix != '.zip':
        raise ValueError('Deliverable ZIP must remain in this workspace deliverables directory')
    receipt_path = ROOT / 'evidence' / (output.stem + '_receipt.json' if args.working_tree else 'source_bundle_receipt.json')
    if output.exists() or receipt_path.exists():
        raise ValueError('Preserve prior archives/receipts; choose a new dated output filename')
    dirty = subprocess.check_output(['git', '-C', str(CODE), 'status', '--porcelain'], text=True).strip()
    if dirty and not args.working_tree:
        raise ValueError('Commit/review current code before packaging; do not label a dirty tree as a commit snapshot')
    commit = subprocess.check_output(['git', '-C', str(CODE), 'rev-parse', 'HEAD'], text=True).strip()
    listing = ['git', '-C', str(CODE), 'ls-files', '-z']
    if args.working_tree:
        listing += ['--cached', '--others', '--exclude-standard']
    tracked = subprocess.check_output(listing).decode().split('\0')
    tracked = [relative for relative in tracked if relative]
    with tempfile.TemporaryDirectory(prefix='investify-package-', dir=SCRATCH) as directory:
        stage = Path(directory).resolve()
        if not stage.is_relative_to(SCRATCH) or not stage.name.startswith('investify-package-'):
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
        for folder in ('report', 'planning'):
            for source in (ROOT / folder).rglob('*'):
                if source.is_file() and source.suffix not in ('.aux', '.log', '.out', '.toc', '.synctex'):
                    relative = source.relative_to(ROOT)
                    target = bundle / relative
                    if not source.resolve().is_relative_to(ROOT / folder) or not target.resolve().is_relative_to(bundle):
                        raise ValueError('Report/planning path escapes its declared root')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
        for name in ('presentation_outline.json', 'social_annotation_protocol.json', 'PROBLEM_AND_CONTRIBUTION.md',
                     'LLM_DESIGN.md', 'MODELS_AND_EVALUATION.md', 'DOMAIN_NOTES.md', 'SOCIAL_CORPUS_ACCESS.md', 'REPORT_METADATA.md',
                     'AI_SENTIMENT_PILOT.md', 'CALIBRATION_INVESTIGATION.md', 'OFFICIAL_MODEL_POLICY.md', 'ASSISTANT_TEACHER_PILOT.md',
                     'DEMO_AND_DEFENCE_GUIDE.md', 'REQUIREMENTS_TRACEABILITY.md',
                     'ORIGINAL_MID_TRACEABILITY.md', 'SCIENCE_CORRECTIONS_20261012.md', 'SOCIAL_V4_RUNBOOK.md',
                     'stocknet_source_access.json', 'stocknet_source_access_v2.json'):
            target = bundle / 'deliverables' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / 'deliverables' / name, target)
        evidence = ('current_tests.xml', 'streamlit_runtime_verification.json', 'source_syntax_verification.json',
                    'javascript_syntax_verification.json', 'demo_artifact_verification.json', 'live_demo_verification.json',
                    'risk_comparator_verification.json', 'social_study_readiness.json', 'social_inference_readiness.json', 'local_llm_probe.json',
                    'ollama_local_probe.json', 'explainer_evaluation_plan.json', 'llm_evaluation_blocked.json',
                    'originals_preservation_check.json', 'ui_dependency_source_receipt.json')
        for name in evidence:
            source = ROOT / 'evidence' / name
            target = bundle / 'evidence' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        for folder in ('evidence/social_pilot', 'evidence/teacher_pilot', 'sources/stocknet',
                       'sources/historical_science_20261012', 'tools'):
            for source in (ROOT / folder).rglob('*'):
                if source.is_file():
                    target = bundle / source.relative_to(ROOT)
                    if not source.resolve().is_relative_to(ROOT / folder) or not target.resolve().is_relative_to(bundle):
                        raise ValueError('Research artifact path escaped its declared root')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
        for relative in ('sources/Investify_Proposal_Full.docx',
                         'sources/Mid_Eval/PROPOSAL_ACTION_REGISTER.md',
                         'sources/Mid_Eval/FYP-1-Mid-Assessment-Guidelines-and-Rubrics.pdf'):
            target = bundle / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        for name in ('calibration_audit_20261012.json', 'current_tests_20261012.xml', 'local_llm_probe_20261012.json',
                     'current_tests_official_policy_20261012.xml', 'profile_blend_semantics_20261012.json',
                     'official_qwen25_acquisition_20261012.json', 'explainer_evaluation_plan_official_20261012.json',
                     'reference_evaluability_20261012.json', 'mid_eval_evidence_brief_verification_20261012.json',
                     'reportlab_source_runtime_20261012.json', 'pypdf_cached_runtime_20261012.json',
                     'current_tests_teacher_20261012.xml', 'teacher_streamlit_tests_20261012.xml', 'teacher_dataset_readiness_20261012.json',
                     'model_policy_cleanup_20261012.json'):
            shutil.copyfile(ROOT / 'evidence' / name, bundle / 'evidence' / name)
        for source in sorted((ROOT / 'evidence').glob('background_*')):
            if source.is_file() and source.suffix in ('.json', '.xml', '.txt'):
                shutil.copyfile(source, bundle / 'evidence' / source.name)
            elif source.is_dir():
                for child in source.rglob('*'):
                    if child.is_file() and child.suffix in ('.json', '.xml', '.txt'):
                        target = bundle / child.relative_to(ROOT)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(child, target)
        # Recovery orchestration receipts are separate from the earlier native
        # background receipts; include their exact dated scopes in the handover.
        for pattern in ('recovery_*', 'parallel_*', 'sentiment_v4_*'):
            for source in sorted((ROOT / 'evidence').glob(pattern)):
                if source.is_file() and source.suffix in ('.json', '.xml', '.txt'):
                    shutil.copyfile(source, bundle / 'evidence' / source.name)
        continuation = ROOT / 'deliverables/mid_eval_continuation_evidence_20261012.pdf'
        continuation_qa = json.loads((ROOT / 'evidence/background_continuation_pdf_verification_20261012.json').read_text(encoding='utf-8'))
        if not continuation_qa['all_pages_visually_checked'] or hashlib.sha256(continuation.read_bytes()).hexdigest() != continuation_qa['pdf_sha256']:
            raise ValueError('Continuation brief must match its completed render/visual receipt')
        shutil.copyfile(continuation, bundle / 'deliverables' / continuation.name)
        shutil.copyfile(ROOT / 'deliverables/HANDOVER_GUIDE.md', bundle / 'HANDOVER.md')
        brief = ROOT / 'deliverables/mid_eval_evidence_brief_20261012.pdf'
        qa = json.loads((ROOT / 'evidence/mid_eval_evidence_brief_verification_20261012.json').read_text(encoding='utf-8'))
        if not qa['all_pages_visually_checked'] or hashlib.sha256(brief.read_bytes()).hexdigest() != qa['pdf_sha256']:
            raise ValueError('Working brief must match its completed render/visual receipt')
        shutil.copyfile(brief, bundle / 'deliverables' / brief.name)
        files = {str(path.relative_to(bundle)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in sorted(bundle.rglob('*')) if path.is_file()}
        manifest = {'built_utc': datetime.now(timezone.utc).isoformat(), 'code_commit': commit,
                    'code_snapshot_kind': 'uncommitted_working_tree' if args.working_tree else 'clean_commit_snapshot',
                    'files': files, 'scope': 'Uncommitted continuation source handover with temporal/ingestion repairs, receipt-bound original-publisher gates, actual unchanged AI references and six teacher examples. CPU classifier imports and labelled tensor serialization are verified; real scientific/candidate/student inference, institutional report/deck and human review remain pending. Current-role continuation brief is rendered/checked; the earlier brief is historical. Third-party corpus is not approved for public redistribution.',
                    'rendered_visual_qa': False, 'working_evidence_brief_rendered_visual_qa': True}
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
