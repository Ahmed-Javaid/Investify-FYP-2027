"""Plan/check restored historical science, or run it only when preflight passes.

No package installation, acquisition, synthetic market data or credential
configuration occurs. Existing scientific outputs and original caches are
read-only inputs; new results have a separate directory and source identity.
"""
import argparse
import ast
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investify.demo_readiness import harness_input_report


def requirement_status():
    import tomllib
    from packaging.requirements import Requirement
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']
    rows = []
    for specification in project['dependencies']:
        requirement = Requirement(specification)
        try:
            installed = importlib.metadata.version(requirement.name)
        except importlib.metadata.PackageNotFoundError:
            installed = None
        rows.append({'requirement': specification, 'installed': installed,
                     'declared_range_satisfied': installed is not None and installed in requirement.specifier})
    return rows


def plan(config, *, run_directory, cache_directory, interpreter=None):
    interpreter = interpreter or sys.executable
    cfg = copy.deepcopy(config)
    # Absolute input paths prevent changing the caller's cwd from changing data.
    for key in ('store', 'artifacts'):
        cfg['paths'][key] = str((ROOT / Path(cfg['paths'][key])).resolve())
    cfg['sentiment']['cache_dir'] = str((ROOT / Path(cfg['sentiment']['cache_dir'])).resolve())
    for specification in cfg['corpora'].values():
        for key in ('path', 'feature_matrix'):
            if key in specification:
                specification[key] = str((ROOT / Path(specification[key])).resolve())
    cfg['news']['extracted_path'] = str((ROOT / Path(cfg['news']['extracted_path'])).resolve())
    preflights = {name: harness_input_report(cfg, name, ROOT) for name in cfg['corpora']}
    requirements = requirement_status()
    blockers = [f"{name}: {item}" for name, report in preflights.items() for item in report['blockers']]
    blockers += [f"Scientific requirement not satisfied: {row['requirement']} (installed {row['installed']})"
                 for row in requirements if not row['declared_range_satisfied']]
    if sys.version_info[:2] != (3, 11):
        blockers.append('Scientific project requires Python 3.11')
    if run_directory.exists():
        blockers.append('Result directory already exists; choose a new run identity')
    split_source = ROOT / 'src/investify/harness/splits.py'
    definitions = ast.parse(split_source.read_text(encoding='utf-8')).body
    split_contract = next(ast.literal_eval(node.value) for node in definitions if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == 'SPLIT_CONTRACT_VERSION' for target in node.targets))
    config_path = run_directory / 'recovery_config.yaml'
    commands = []
    for corpus in cfg['corpora']:
        commands += [[interpreter, '-B', '-m', 'investify.harness.run_spike', '--corpus', corpus,
                      '--config', str(config_path), '--output-directory', str(run_directory / ('harness_' + corpus))],
                     [interpreter, '-B', str(ROOT / 'scripts/build_decision_records.py'), '--corpus', corpus,
                      '--config', str(config_path), '--calibration-mode', 'frozen_classifier',
                      '--output-directory', str(run_directory / ('engine_frozen_' + corpus))],
                     [interpreter, '-B', str(ROOT / 'scripts/build_decision_records.py'), '--corpus', corpus,
                      '--config', str(config_path), '--calibration-mode', 'refit_transfer',
                      '--output-directory', str(run_directory / ('engine_refit_' + corpus))]]
    sources = [Path(__file__), ROOT / 'config/spike.yaml', ROOT / 'pyproject.toml', ROOT / 'uv.lock',
               split_source, ROOT / 'src/investify/harness/arms.py', ROOT / 'src/investify/labels.py',
               ROOT / 'src/investify/engine.py', ROOT / 'src/investify/calibration_split.py',
               ROOT / 'src/investify/features/indicators.py', ROOT / 'src/investify/features/assembly.py',
               ROOT / 'src/investify/news_cache.py', ROOT / 'src/investify/scaling.py',
               ROOT / 'src/investify/ingest/news.py', ROOT / 'src/investify/store.py']
    return {'schema': 'investify-historical-science-recovery-v1',
            'checked_utc': datetime.now(timezone.utc).isoformat(), 'executable': interpreter,
            'status': 'blocked' if blockers else 'structural_preflight_passed',
            'blockers': blockers, 'harness_preflight': preflights, 'declared_requirement_ranges': requirements,
            'config': cfg, 'split_contract': split_contract, 'result_directory': str(run_directory),
            'process_cache_directory': str(cache_directory), 'commands': commands, 'executions': [],
            'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
            'exact_uv_lock_restored': False, 'historical_pipeline_executed': False, 'predictive_metrics': None,
            'scope': 'Read-only prerequisites and prepared separate-output commands. Satisfying declared ranges is not exact '
                     'uv.lock restoration. Only explicit execution with genuine inputs can produce model results; '
                     'data/schema/cache coverage, full arrays/calibration comparison and full acceptance still require review.'}


def save_receipt(report, receipt, *, new=False):
    """Retain a usable status before and after each attempted scientific step."""
    with receipt.open('x' if new else 'w', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False, default=str)
        stream.write('\n')


def execute_plan(report, receipt, *, step_timeout=None, runner=None):
    """Execute only eligible plans; preserve partial outputs and every failure.

    A successful process exit still requires result review. A launch failure or
    timeout must never be described as an executed historical pipeline.
    """
    if receipt.exists():
        raise ValueError('Preserve prior recovery receipts; use a new receipt')
    if report['blockers']:
        save_receipt(report, receipt, new=True)
        return report
    if not report['commands']:
        raise ValueError('An eligible recovery plan must contain commands')
    if step_timeout is not None and (not isinstance(step_timeout, int) or step_timeout <= 0):
        raise ValueError('Step timeout must be a positive whole number of seconds')
    run_directory = Path(report['result_directory'])
    cache_directory = Path(report['process_cache_directory'])
    report['step_timeout_seconds'] = step_timeout
    report['status'] = 'execution_prepared'
    save_receipt(report, receipt, new=True)
    try:
        run_directory.mkdir(parents=True)  # Exclusive: never reuse prior outputs.
        import yaml
        (run_directory / 'recovery_config.yaml').write_text(yaml.safe_dump(report['config']), encoding='utf-8')
        cache_directory.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError, TypeError) as error:
        report.update(status='execution_failed', setup_error={'type': type(error).__name__, 'message': str(error)})
        save_receipt(report, receipt)
        return report
    env = dict(os.environ, TEMP=str(cache_directory), TMP=str(cache_directory),
               PYTHONDONTWRITEBYTECODE='1', HF_HOME=str(cache_directory / 'huggingface'),
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               MPLCONFIGDIR=str(cache_directory / 'matplotlib'),
               NUMBA_CACHE_DIR=str(cache_directory / 'numba'),
               TORCH_HOME=str(cache_directory / 'torch'),
               XDG_CACHE_HOME=str(cache_directory / 'xdg'), PYTHONPATH=str(ROOT / 'src'))
    runner = runner or subprocess.run
    for command in report['commands']:
        log_path = run_directory / f"step-{len(report['executions']) + 1:02d}.log"
        attempt = {'command': command, 'status': 'running',
                   'started_utc': datetime.now(timezone.utc).isoformat(), 'log': str(log_path),
                   'returncode': None, 'log_sha256': None}
        report['executions'].append(attempt)
        report['status'] = 'executing'
        save_receipt(report, receipt)
        try:
            with log_path.open('x', encoding='utf-8') as logfile:
                result = runner(command, cwd=ROOT, env=env, stdout=logfile,
                                stderr=subprocess.STDOUT, timeout=step_timeout)
            attempt.update(returncode=result.returncode,
                           status='failed' if result.returncode else 'completed')
        except (OSError, subprocess.TimeoutExpired) as error:
            attempt.update(status='timed_out' if isinstance(error, subprocess.TimeoutExpired) else 'launch_failed',
                           error={'type': type(error).__name__, 'message': str(error)})
        except KeyboardInterrupt:
            attempt['status'] = 'interrupted'
            report['status'] = 'execution_interrupted'
            attempt['completed_utc'] = datetime.now(timezone.utc).isoformat()
            save_receipt(report, receipt)
            raise
        attempt['completed_utc'] = datetime.now(timezone.utc).isoformat()
        if log_path.is_file():
            attempt['log_sha256'] = hashlib.sha256(log_path.read_bytes()).hexdigest()
        if attempt['status'] != 'completed':
            report['status'] = 'execution_failed'
            save_receipt(report, receipt)
            return report
        save_receipt(report, receipt)
    report['status'] = 'executed_pending_result_review'
    report['historical_pipeline_executed'] = True
    save_receipt(report, receipt)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'config/spike.yaml')
    parser.add_argument('--run-directory', type=Path, required=True)
    parser.add_argument('--cache-directory', type=Path, default=Path('E:/AI-Tools/Temp/investify-scientific-process-cache'))
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--store', type=Path)
    parser.add_argument('--sentiment-cache', type=Path, help='Existing scores-cache directory, not a new scoring/download destination')
    parser.add_argument('--alpaca-news', type=Path)
    parser.add_argument('--corpus', choices=['fnspid', 'alpaca'], help='Advance one corpus independently when the other is unavailable')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--step-timeout-seconds', type=int,
                        help='Optional positive process limit per step; not a measured performance target')
    args = parser.parse_args()
    run_directory, cache_directory, receipt = args.run_directory.resolve(), args.cache_directory.resolve(), args.receipt.resolve()
    if not run_directory.is_relative_to(ROOT / 'artifacts/scientific_runs'):
        raise ValueError('New scientific outputs must remain in code/artifacts/scientific_runs')
    if not cache_directory.is_relative_to(Path('E:/AI-Tools').resolve()):
        raise ValueError('Process cache/temp must remain on E:/AI-Tools')
    if not receipt.is_relative_to(ROOT.parent / 'evidence') or receipt.exists():
        raise ValueError('Use a new evidence receipt')
    import yaml
    cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))
    if args.store:
        cfg['paths']['store'] = str(args.store.resolve())
    if args.sentiment_cache:
        cfg['sentiment']['cache_dir'] = str(args.sentiment_cache.resolve())
    if args.alpaca_news:
        cfg['corpora']['alpaca']['path'] = str(args.alpaca_news.resolve())
    if args.corpus:
        cfg['corpora'] = {args.corpus: cfg['corpora'][args.corpus]}
    report = plan(cfg, run_directory=run_directory, cache_directory=cache_directory)
    if args.execute:
        execute_plan(report, receipt, step_timeout=args.step_timeout_seconds)
    else:
        save_receipt(report, receipt, new=True)
    print(f"Scientific recovery: {report['status']}; {len(report['blockers'])} blockers; "
          f"{len(report['executions'])} commands executed; receipt {receipt}")
    return 2 if report['blockers'] or report['status'] == 'execution_failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
