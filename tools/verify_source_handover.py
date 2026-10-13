"""Exercise the delivered source ZIP in an isolated standard-library-only host."""
import hashlib
import argparse
import json
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path('E:/AI-Tools/Temp').resolve()
ARCHIVE = ROOT / 'deliverables/investify_mideval_source.zip'
ENVIRONMENT = SCRATCH / 'investify-portable-clean-py311'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ARCHIVE)
    parser.add_argument('--receipt-prefix', default='source_bundle')
    parser.add_argument('--scratch-directory', type=Path, default=Path('E:/AI-Tools/Temp'))
    parser.add_argument('--receipt-directory', type=Path, default=ROOT / 'evidence')
    args = parser.parse_args()
    global SCRATCH, ENVIRONMENT
    SCRATCH = args.scratch_directory.resolve()
    ENVIRONMENT = SCRATCH / 'investify-portable-clean-py311'
    receipts = args.receipt_directory.resolve()
    if not SCRATCH.is_dir() or not (receipts == ROOT / 'evidence' or receipts.is_relative_to(ROOT / 'code/artifacts/ci_evidence')):
        raise ValueError('Use prepared scratch and this project\'s evidence directory')
    receipts.mkdir(parents=True, exist_ok=True)
    archive_path = args.archive.resolve()
    if not archive_path.is_relative_to(ROOT / 'deliverables') or not re.fullmatch('[a-zA-Z0-9_-]+', args.receipt_prefix):
        raise ValueError('Use a local deliverable archive and plain receipt prefix')
    if any((receipts / (args.receipt_prefix + suffix)).exists()
           for suffix in ('_clean_host_tests.txt', '_clean_host_verification.json')):
        raise ValueError('Preserve prior clean-host receipts; choose a new dated prefix')
    interpreter = ENVIRONMENT / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not interpreter.exists():
        subprocess.run([sys.executable, '-B', '-m', 'venv', '--without-pip', str(ENVIRONMENT)], check=True)
    env = dict(os.environ, TEMP=str(SCRATCH), TMP=str(SCRATCH), PYTHONDONTWRITEBYTECODE='1')
    for name in ('INVESTIFY_LLM_MODEL', 'INVESTIFY_LLM_BASE_URL', 'INVESTIFY_LLM_API_KEY', 'PYTHONPATH'):
        env.pop(name, None)
    with tempfile.TemporaryDirectory(prefix='investify-clean-handover-', dir=SCRATCH) as directory:
        stage = Path(directory).resolve()
        if not stage.is_relative_to(SCRATCH) or not stage.name.startswith('investify-clean-handover-'):
            raise ValueError('Extraction/cleanup path escaped the declared scratch root')
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                target = (stage / info.filename).resolve()
                if (not target.is_relative_to(stage) or Path(info.filename).is_absolute()
                        or stat.S_ISLNK(info.external_attr >> 16)):
                    raise ValueError('Unsafe path or symlink in the source archive')
            archive.extractall(stage)
        bundle = stage / 'InvestifyMidEval'
        code = bundle / 'code'
        manifest = json.loads((bundle / 'bundle_manifest.json').read_text())
        for relative, expected in manifest['files'].items():
            path = (bundle / relative).resolve()
            if not path.is_relative_to(bundle) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f'Bundled content failed its inventory: {relative}')

        def run(*arguments):
            result = subprocess.run([str(interpreter), '-I', '-B', *arguments], cwd=code, env=env,
                                    capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError(f'Clean-host command failed: {arguments[0]}\n{result.stderr[-3000:]}')
            return result

        modules = run('-c', 'import importlib.util,json; print(json.dumps({name:importlib.util.find_spec(name) is not None for name in ("numpy","streamlit","torch","pytest")}))')
        availability = json.loads(modules.stdout)
        if any(availability.values()):
            raise ValueError('Clean host unexpectedly contains scientific/UI/test packages')
        tests = run('-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_mideval*.py', '-v')
        log = tests.stdout + tests.stderr
        match = re.search(r'Ran (\d+) tests in', log)
        if not match or not log.rstrip().endswith('OK'):
            raise ValueError('Clean-host unit-test result was not a complete pass')
        run('scripts/verify_demo_artifacts.py', '--output', str(stage / 'artifact_check.json'))
        run('scripts/evaluate_mideval_llm.py', '--plan-only', '--output', str(stage / 'plan_only.json'))
        artifacts = json.loads((stage / 'artifact_check.json').read_text())
        plan = json.loads((stage / 'plan_only.json').read_text())
        expected_source = 'checked_working_tree_inventory' if manifest.get('code_snapshot_kind') == 'uncommitted_working_tree' else 'checked_bundle_inventory'
        if artifacts['revision_source'] != expected_source or artifacts['git_commit'] != manifest['code_commit']:
            raise ValueError('Delivered revision metadata does not match the package')
        if expected_source == 'checked_working_tree_inventory' and artifacts['git_dirty'] is not True:
            raise ValueError('Uncommitted review sources must remain explicitly labelled')
        if plan['status'] != 'plan_only' or plan['raw_completions'] != 0:
            raise ValueError('Clean-host plan-only command must not call a model')
        original_source_replayed = False
        if (bundle / 'tools/verify_ai_pilot_evidence.py').exists():
            original_source_replayed = (bundle / 'sources/stocknet/acquisition_manifest.json').exists()
            extra = [] if original_source_replayed else ['--saved-only']
            run('../tools/verify_ai_pilot_evidence.py', *extra)
        teacher_replayed = 0
        if (bundle / 'evidence/teacher_pilot/assistant_20261012/verified/verification.json').exists():
            run('../tools/verify_teacher_pilot_evidence.py')
            teacher = json.loads((bundle / 'evidence/teacher_pilot/assistant_20261012/verified/verification.json').read_text(encoding='utf-8'))
            teacher_replayed = teacher['accepted']
        requirement_anchors = 0
        if (code / 'docs/requirements_traceability.json').exists():
            run('../tools/verify_requirements_traceability.py', '--tests', '../evidence/current_tests.xml',
                '--output', '../evidence/clean_host_requirement_anchors.json')
            trace = json.loads((bundle / 'evidence/clean_host_requirement_anchors.json').read_text(encoding='utf-8'))
            requirement_anchors = trace['requirements_checked']
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        server = subprocess.Popen([str(interpreter), '-I', '-B', 'scripts/serve_mideval_demo.py', '--port', str(port)],
                                  cwd=code, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            base = f'http://127.0.0.1:{port}'
            opener = build_opener(ProxyHandler({}))
            ready = False
            for _ in range(30):
                if server.poll() is not None:
                    raise RuntimeError('Delivered portable server exited during startup')
                try:
                    with opener.open(base + '/health', timeout=1) as response:
                        ready = response.status == 200
                except OSError:
                    time.sleep(.1)
                if ready:
                    break
            if not ready:
                raise RuntimeError('Delivered portable server did not become ready')
            run('scripts/verify_mideval_demo.py', '--base-url', base, '--output', str(stage / 'live_check.json'))
        finally:
            server.terminate()
            server.wait(timeout=5)
            if server.stderr:
                server.stderr.close()
        live = json.loads((stage / 'live_check.json').read_text())
        receipt = {'checked_utc': datetime.now(timezone.utc).isoformat(),
                   'archive_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                   'code_commit': manifest['code_commit'], 'inventory_files_verified': len(manifest['files']),
                   'clean_environment': str(ENVIRONMENT), 'unavailable_external_packages': availability,
                   'portable_tests_passed': int(match.group(1)), 'live_checks_passed': live['checks_passed'],
                   'records_validated': sum(item['records'] for item in artifacts['results']),
                   'revision_source': artifacts['revision_source'], 'git_dirty': artifacts['git_dirty'],
                   'plan_only_status': plan['status'], 'real_completions': 0, 'browser_visual_qa': False,
                   'recorded_teacher_examples_replayed': teacher_replayed, 'student_training_executed': False,
                   'original_social_acquisition_inputs_replayed': original_source_replayed,
                   'requirement_anchors_checked_against_bundled_selected_receipt': requirement_anchors,
                   'streamlit_tests_executed_on_clean_host': False,
                   'scope': 'Actual ZIP extraction, hash inventory, stdlib-only execution, live portable server and no-inference planning; not scientific reproduction or rendered report/deck'}
        (receipts / (args.receipt_prefix + '_clean_host_tests.txt')).write_text(log, encoding='utf-8')
        (receipts / (args.receipt_prefix + '_clean_host_verification.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print(f"Clean source handover: {receipt['portable_tests_passed']} tests, {receipt['live_checks_passed']} live checks, {receipt['records_validated']} records; no external packages/model calls")


if __name__ == '__main__':
    main()
