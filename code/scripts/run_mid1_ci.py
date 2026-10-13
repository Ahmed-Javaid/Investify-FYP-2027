"""Run the same bounded Mid-1 validation jobs locally and in GitHub Actions."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener

CODE = Path(__file__).resolve().parents[1]
PROJECT = CODE.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declare_revision():
    """Explicitly bind this code component to its owning repository, without ancestor inference."""
    if not (PROJECT / '.git').exists():
        raise ValueError('Run CI from this project checkout, with its own root Git metadata')
    actual = Path(subprocess.check_output(['git', '-C', str(PROJECT), 'rev-parse', '--show-toplevel'],
                                         text=True).strip()).resolve()
    if actual != PROJECT.resolve():
        raise ValueError('A parent repository cannot supply this CI identity')
    commit = subprocess.check_output(['git', '-C', str(PROJECT), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', '-C', str(PROJECT), 'status', '--porcelain'], text=True).strip())
    names = subprocess.check_output(['git', '-C', str(CODE), 'ls-files', '-z', '--cached', '--others',
                                     '--exclude-standard'], text=True).split('\0')
    files = {}
    for name in names:
        if not name or name == 'source_revision.json':
            continue
        path = (CODE / name).resolve()
        if not path.is_relative_to(CODE) or path.name.startswith('.env') or path.suffix in ('.gguf', '.safetensors', '.pyc'):
            raise ValueError('Unexpected path, credential or model file in the CI source inventory')
        if not path.is_file():
            if dirty and not path.exists():
                continue  # An explicitly dirty checkout may include an unstaged deletion.
            raise ValueError('A declared source path is not a file')
        files[name.replace('\\', '/')] = sha(path)
    metadata = {'schema': 'investify-working-source-revision-v2' if dirty else 'investify-source-revision-v1',
                'commit': commit, 'files': files}
    if dirty:
        metadata['working_tree'] = True
    generated = CODE / 'source_revision.json'
    if generated.exists():
        previous = json.loads(generated.read_text(encoding='utf-8'))
        if previous.get('schema') not in ('investify-source-revision-v1', 'investify-working-source-revision-v2'):
            raise ValueError('Do not replace unrecognized revision metadata')
    generated.write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    return {'repository_commit': commit, 'repository_dirty': dirty, 'code_files': len(files),
            'declared_code_inventory_sha256': sha(generated)}


def restore_revision(previous, expected):
    """Remove only this job's temporary declaration, or restore its prior bytes."""
    generated = CODE / 'source_revision.json'
    if sha(generated) != expected:
        raise ValueError('Revision metadata changed during CI; leave it as found')
    current = generated.read_bytes()
    metadata = json.loads(current)
    for name, digest in metadata['files'].items():
        path = (CODE / name).resolve()
        if not path.is_relative_to(CODE) or sha(path) != digest:
            raise ValueError('A CI source changed during execution')
    if previous is None:
        generated.unlink()
    else:
        generated.write_bytes(previous)
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', choices=['evidence', 'streamlit-ui'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ruff-executable', type=Path, help='Use an already prepared checker for local replay')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not any(output.is_relative_to(root) and output != root for root in
                                  (PROJECT / 'evidence', CODE / 'artifacts/ci_evidence')):
        raise ValueError('Use a new evidence run directory in this project')
    output.mkdir(parents=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PIP_DISABLE_PIP_VERSION_CHECK='1', PYTHONIOENCODING='utf-8')
    # Local caches/scratch stay on E:. Hosted runners use their own isolated temporary directory.
    if not env.get('GITHUB_ACTIONS') and Path('E:/AI-Tools/Temp').is_dir():
        env.update(TEMP='E:/AI-Tools/Temp', TMP='E:/AI-Tools/Temp',
                   MPLCONFIGDIR='E:/AI-Tools/Cache/matplotlib', NUMBA_CACHE_DIR='E:/AI-Tools/Cache/numba')
    elif env.get('RUNNER_TEMP'):
        env.update(TEMP=env['RUNNER_TEMP'], TMP=env['RUNNER_TEMP'])
    generated = CODE / 'source_revision.json'
    previous = generated.read_bytes() if generated.exists() else None
    result = {'schema': 'investify-executed-ci-job-v1', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'job': args.job, 'platform': platform.platform(), 'python': platform.python_version(),
              'execution_location': 'github_actions' if env.get('GITHUB_ACTIONS') else 'local_replay',
              'runner_version': env.get('RUNNER_VERSION'), 'dependency_installation_verified_by_this_runner': False,
              'status': 'running', 'steps': [], 'scientific_training_or_llm_inference': False,
              'deployment_executed': False, 'source': declare_revision()}

    def run(name, command):
        started = time.monotonic()
        done = subprocess.run(command, cwd=CODE, env=env, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=180)
        log = output / (name + '.txt')
        log.write_text(done.stdout + done.stderr, encoding='utf-8')
        count = re.search(r'Ran (\d+) tests in', done.stdout + done.stderr)
        result['steps'].append({'name': name, 'exit_code': done.returncode,
                                'elapsed_seconds': round(time.monotonic() - started, 3),
                                'tests_passed': int(count.group(1)) if count and done.returncode == 0 else None,
                                'log_sha256': sha(log)})
        if done.returncode:
            raise RuntimeError(f'{name} failed; see {log.name}')

    python = [sys.executable, '-B']
    try:
        if args.job == 'evidence':
            run('ci-runner-guards', python + ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_ci_runner.py', '-v'])
            run('portable-tests', python + ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_mideval*.py', '-v'])
            for name, script, extra in (
                    ('record-validation', 'verify_demo_artifacts.py', []),
                    ('standalone-preview', 'export_mideval_preview.py', []),
                    ('plan-only', 'evaluate_mideval_llm.py', ['--plan-only']),
                    ('risk-comparator', 'verify_risk_comparator.py', [])):
                suffix = '.html' if name == 'standalone-preview' else '.json'
                run(name, python + ['scripts/' + script, *extra, '--output', str(output / (name + suffix))])
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            server = subprocess.Popen(python + ['scripts/serve_mideval_demo.py', '--port', str(port)], cwd=CODE,
                                      env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                opener = build_opener(ProxyHandler({}))
                ready = False
                for _ in range(60):
                    if server.poll() is not None:
                        raise RuntimeError('Portable CI server exited before its health check')
                    try:
                        with opener.open(f'http://127.0.0.1:{port}/health', timeout=1) as response:
                            ready = response.status == 200
                    except OSError:
                        time.sleep(.1)
                    if ready:
                        break
                if not ready:
                    raise RuntimeError('Portable CI server did not become ready')
                run('portable-http', python + ['scripts/verify_mideval_demo.py', '--base-url',
                                               f'http://127.0.0.1:{port}', '--output', str(output / 'portable-http.json')])
            finally:
                server.terminate()
                server.wait(timeout=10)
        else:
            checker = ([str(args.ruff_executable.resolve())] if args.ruff_executable else python + ['-m', 'ruff'])
            run('ui-source-check', checker + ['check', '--no-cache', '--select', 'E4,E9,F',
                'app/streamlit_app.py', 'app/presenter.py', 'app/presenter_data.py', 'app/presenter_style.py',
                'tests/test_presenter_ui.py', 'scripts/run_mid1_ci.py'])
            for name, pattern in (('legacy-ui', 'test_streamlit_mideval.py'),
                                  ('primary-ui', 'test_presenter_ui.py'),
                                  ('recorded-study-selectors', 'test_recorded_social_study.py')):
                run(name, python + ['-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v'])
        # Every captured artifact is independently bound to its exact bytes.
        result['status'] = 'passed'
    except Exception as error:
        result.update(status='failed', error=str(error))
    try:
        declaration = restore_revision(previous, result['source']['declared_code_inventory_sha256'])
        (output / 'source_revision.json').write_bytes(declaration)
        result['temporary_component_metadata_restored'] = True
    except (OSError, ValueError) as error:
        result.update(status='failed', error=str(error), temporary_component_metadata_restored=False)
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    result['artifacts_sha256'] = {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output / 'job_receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'{args.job}: {result["status"]}, {len(result["steps"])} recorded steps, {output}')
    if result['status'] != 'passed':
        raise RuntimeError(result['error'])


if __name__ == '__main__':
    main()
