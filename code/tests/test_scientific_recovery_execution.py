"""Failure/restart fixtures for the recovery runner; no scientific execution."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/prepare_scientific_recovery.py'
SPEC = importlib.util.spec_from_file_location('recovery_execution_fixture', SCRIPT)
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


def fixture_plan(root):
    return {'blockers': [], 'commands': [['fixture', 'one'], ['fixture', 'two']],
            'config': {'fixture_only': True}, 'result_directory': str(root / 'outputs'),
            'process_cache_directory': str(root / 'cache'), 'executions': [],
            'status': 'structural_preflight_passed', 'historical_pipeline_executed': False}


@pytest.mark.parametrize('failure', ['launch', 'timeout', 'nonzero'])
def test_failure_has_a_receipt_and_log_and_stops_later_steps(failure):
    with tempfile.TemporaryDirectory(prefix='investify-recovery-test-') as directory:
        root = Path(directory)
        receipt = root / 'receipt.json'
        report = fixture_plan(root)
        calls = []
        def runner(command, **options):
            calls.append(command)
            saved = json.loads(receipt.read_text())
            assert saved['executions'][0]['status'] == 'running'
            assert saved['historical_pipeline_executed'] is False
            assert options['env']['TEMP'].startswith(str(root))
            options['stdout'].write('labelled subprocess fixture\n')
            if failure == 'launch':
                raise FileNotFoundError('fixture interpreter absent')
            if failure == 'timeout':
                raise subprocess.TimeoutExpired(command, 1)
            return SimpleNamespace(returncode=7)
        recovery.execute_plan(report, receipt, step_timeout=1, runner=runner)
        saved = json.loads(receipt.read_text())
        assert len(calls) == 1
        assert saved['status'] == 'execution_failed'
        assert saved['historical_pipeline_executed'] is False
        assert saved['executions'][0]['log_sha256']
        assert saved['executions'][0]['status'] in ('launch_failed', 'timed_out', 'failed')
        original = receipt.read_bytes()
        with pytest.raises(ValueError, match='Preserve prior'):
            recovery.execute_plan(fixture_plan(root), receipt, runner=runner)
        assert receipt.read_bytes() == original


def test_blocked_plan_never_creates_outputs_or_calls_a_subprocess():
    with tempfile.TemporaryDirectory(prefix='investify-recovery-test-') as directory:
        root = Path(directory)
        report = fixture_plan(root)
        report.update(blockers=['genuine prices absent'], status='blocked')
        def forbidden(*args, **kwargs):
            raise AssertionError('blocked plan launched')
        recovery.execute_plan(report, root / 'receipt.json', runner=forbidden)
        assert not (root / 'outputs').exists()
        assert not (root / 'cache').exists()
        assert report['executions'] == []


def test_existing_output_refusal_is_retained_and_bytes_are_preserved():
    with tempfile.TemporaryDirectory(prefix='investify-recovery-test-') as directory:
        root = Path(directory)
        report = fixture_plan(root)
        output = root / 'outputs'
        output.mkdir()
        (output / 'original.txt').write_text('prior result')
        recovery.execute_plan(report, root / 'receipt.json')
        assert report['status'] == 'execution_failed'
        assert report['setup_error']['type'] == 'FileExistsError'
        assert (output / 'original.txt').read_text() == 'prior result'
        assert report['executions'] == []


def test_successful_fixture_steps_remain_pending_result_review():
    with tempfile.TemporaryDirectory(prefix='investify-recovery-test-') as directory:
        root = Path(directory)
        report = fixture_plan(root)
        def runner(command, **options):
            options['stdout'].write('fixture exit zero; no market/model data\n')
            return SimpleNamespace(returncode=0)
        recovery.execute_plan(report, root / 'receipt.json', runner=runner)
        assert report['status'] == 'executed_pending_result_review'
        assert len(report['executions']) == 2
        assert all(step['status'] == 'completed' for step in report['executions'])
        # The plan marker means only that its processes exited successfully.
        assert report['historical_pipeline_executed'] is True


def test_empty_command_plan_cannot_claim_execution():
    with tempfile.TemporaryDirectory(prefix='investify-recovery-test-') as directory:
        root = Path(directory)
        report = fixture_plan(root)
        report['commands'] = []
        with pytest.raises(ValueError, match='must contain commands'):
            recovery.execute_plan(report, root / 'receipt.json')
        assert not (root / 'receipt.json').exists()
