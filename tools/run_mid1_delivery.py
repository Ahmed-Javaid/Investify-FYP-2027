"""Deliver a source/PDF bundle only after source-bound CI and extraction checks pass."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_ci(receipts, root, commit, hosted=False):
    observed = set()
    result = []
    for path in receipts:
        value = json.loads(path.read_text(encoding='utf-8'))
        if (value.get('status') != 'passed' or not value.get('temporary_component_metadata_restored')
                or value['source']['repository_commit'] != commit or value['source']['repository_dirty']):
            raise ValueError('Delivery requires passing, clean, same-commit CI jobs')
        if hosted and value.get('execution_location') != 'github_actions':
            raise ValueError('Hosted delivery cannot use local replay as hosted evidence')
        family = value['platform'].split('-')[0]
        key = (family, value['job'])
        if key in observed:
            raise ValueError('Duplicate CI prerequisite')
        observed.add(key)
        declaration = path.parent / 'source_revision.json'
        if sha(declaration) != value['source']['declared_code_inventory_sha256']:
            raise ValueError('Changed CI source declaration')
        metadata = json.loads(declaration.read_text(encoding='utf-8'))
        for name, expected in metadata['files'].items():
            source = (root / 'code' / name).resolve()
            if (not source.is_relative_to(root / 'code') or source.name.startswith('.env')
                    or sha(source) != expected):
                raise ValueError('CI source no longer matches the delivery checkout')
        for name, expected in value['artifacts_sha256'].items():
            artifact = (path.parent / name).resolve()
            if artifact.parent != path.parent.resolve() or sha(artifact) != expected:
                raise ValueError('Changed or unsafe CI artifact')
        result.append({'job': value['job'], 'platform': value['platform'], 'receipt_sha256': sha(path),
                       'execution_location': value['execution_location']})
    families = {family for family, _ in observed}
    required = {'Windows', 'Linux'} if hosted else families
    if not required or observed != {(family, job) for family in required for job in ('evidence', 'streamlit-ui')}:
        raise ValueError('Both CI jobs must pass on every required platform')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ci-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--documents', type=Path, default=ROOT / 'deliverables/current_delivery.json')
    args = parser.parse_args()
    output = args.output.resolve()
    allowed = (ROOT / 'code/artifacts/ci_evidence').resolve()
    if not output.is_relative_to(allowed) or output == allowed or output.exists():
        raise ValueError('Use a new ignored CI delivery directory')
    commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    receipts = sorted(args.ci_root.resolve().rglob('job_receipt.json'))
    hosted = os.environ.get('GITHUB_ACTIONS') == 'true'
    prerequisites = check_ci(receipts, ROOT, commit, hosted)
    documents = json.loads(args.documents.read_text(encoding='utf-8'))
    output.mkdir(parents=True)
    scratch = Path(os.environ.get('RUNNER_TEMP', 'E:/AI-Tools/Temp')).resolve()
    if not scratch.is_dir():
        raise ValueError('Prepared scratch directory is unavailable')
    archive = ROOT / 'deliverables' / f'investify_mid1_ci_delivery_{commit[:12]}.zip'
    package_receipt = ROOT / 'evidence' / (archive.stem + '_receipt.json')
    command = [sys.executable, '-B', str(ROOT / 'tools/package_source_handover.py'), '--output', str(archive),
               '--scratch-directory', str(scratch), '--report-receipt', documents['report_receipt'],
               '--presentation-receipt', documents['presentation_receipt']]
    subprocess.run(command, cwd=ROOT, check=True, timeout=180)
    subprocess.run([sys.executable, '-B', str(ROOT / 'tools/verify_source_handover.py'), '--archive', str(archive),
                    '--receipt-prefix', 'delivery_extraction', '--scratch-directory', str(scratch),
                    '--receipt-directory', str(output)], cwd=ROOT, check=True, timeout=180)
    archive.replace(output / archive.name)
    package_receipt.replace(output / 'package_receipt.json')
    for index, path in enumerate(receipts):
        (output / f'prerequisite_{index + 1}.json').write_bytes(path.read_bytes())
    result = {'schema': 'investify-verified-continuous-delivery-v1', 'checked_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'passed', 'repository_commit': commit,
              'execution_location': 'github_actions' if hosted else 'local_replay',
              'ci_prerequisites': prerequisites, 'document_configuration_sha256': sha(args.documents),
              'delivery_kind': 'Verified source, reviewed PDF and handover artifact; production hosting is later scope.',
              'artifacts_sha256': {path.name: sha(path) for path in sorted(output.iterdir()) if path.is_file()}}
    (output / 'delivery_receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Continuous delivery: passed, {output}')


if __name__ == '__main__':
    main()
