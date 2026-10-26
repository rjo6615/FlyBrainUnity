"""Process lifecycle, full original audit equivalence, and failure preservation."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from malecns_backend.live import balance_contribution_process as p


def fixture_module():
    spec = importlib.util.spec_from_file_location('balance_v1_reference_fixture',
                                                p.ROOT / 'tests/test_balance_contribution.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def synthetic():
    original = fixture_module().null_report()
    source = p.sources()
    report = dict(schema=p.SCHEMA, protocol=p.protocol(), design=p.base.design(), run_status='COMPLETE',
        preflight=dict(verified=True), sources_before=source, sources_after=source,
        controller_pid=100, implementation_commit='synthetic',
        arm_artifacts={c: dict(path=c + '.json.gz', sha256='synthetic') for c in p.base.CONDITIONS})
    arms = {}
    for i, c in enumerate(p.base.CONDITIONS):
        arms[c] = dict(original['arms'][c], worker_sources_before=source, worker_sources_after=source,
            process_boundary=dict(pid=200+i, parent_pid=100, launch_pid=200+i, controller_pid=100,
                                  launcher_parent_pid=100, mode='direct', commit='synthetic',
                                  fresh_registry=dict(existing_names=[], default_name=0)))
    return original, report, arms


def test_original_design_and_prospective_protocol_are_locked():
    assert p.validate_protocol()['conditions'] == ['NC', 'WC', 'NP', 'WP']
    p.base.validate_design()


@pytest.mark.parametrize('field', ['scientific_parameters_changed', 'native_execution_in_this_specification'])
def test_spec_cannot_silently_declare_scientific_change_or_execution(field):
    changed = dict(p.protocol(), **{field: True})
    with patch.object(p, 'protocol', return_value=changed):
        with pytest.raises(ValueError): p.validate_protocol()


def test_empty_flygym_registry_is_observed_not_modified():
    fly = SimpleNamespace(_existing_fly_names=set(), _default_fly_name=0)
    assert p.fresh_registry(SimpleNamespace(Fly=fly)) == dict(existing_names=[], default_name=0)
    assert fly._existing_fly_names == set() and fly._default_fly_name == 0


@pytest.mark.parametrize('names,counter', [({'0'}, 0), (set(), 1), ({'0','1'}, 2)])
def test_contaminated_registry_fails_without_reset(names, counter):
    fly = SimpleNamespace(_existing_fly_names=names.copy(), _default_fly_name=counter)
    with pytest.raises(ValueError, match='fresh FlyGym'):
        p.fresh_registry(SimpleNamespace(Fly=fly))
    assert fly._existing_fly_names == names and fly._default_fly_name == counter


def test_stop_boundary_delegates_original_session_and_prevents_next_step(tmp_path):
    calls = []
    class Session:
        def initialize(self): calls.append('initialize'); return 'initial'
        def step(self, **kwargs): calls.append(kwargs); return 'next'
        def close(self): calls.append('close')
    stop = tmp_path / 'STOP.json'
    s = p.StopAwareSession(Session(), stop)
    assert s.initialize() == 'initial'
    assert s.step(lightweight=True) == 'next'
    stop.write_text('{}')
    with pytest.raises(KeyboardInterrupt): s.step(lightweight=True)
    s.close()
    assert calls == ['initialize', {'lightweight': True}, 'close']


def test_stop_before_initialization_does_not_construct(tmp_path):
    stop = tmp_path / 'STOP.json'; stop.write_text('{}')
    s = p.StopAwareSession(SimpleNamespace(initialize=lambda: pytest.fail('constructed')), stop)
    with pytest.raises(KeyboardInterrupt): s.initialize()


def test_stop_during_launch_handshake_checks_controller_marker(tmp_path):
    launch_dir = tmp_path/'NC'; launch_dir.mkdir()
    (tmp_path/'STOP.json').write_text('{}')
    with pytest.raises(KeyboardInterrupt): p.process_boundary(launch_dir)


def test_full_synthetic_null_matches_original_auditors_and_analysis(synthetic):
    old, report, arms = synthetic
    original = p.base.evaluate(old)
    actual = p.evaluate(report, '.', loader=lambda folder, c, artifact: arms[c])
    assert original['accepted'] and actual['accepted'], actual.get('reason')
    for field in ('arms', 'behavior', 'pair_exposure', 'unity_replay_eligible'):
        assert actual[field] == original[field]
    assert actual['behavior']['primary_label'] == 'MIXED_OR_UNRESOLVED'
    assert not actual['behavior']['independent_balance_proven']


@pytest.fixture(scope='module')
def proofs(synthetic):
    return {c: p.proof(a) for c, a in synthetic[2].items()}


def test_namespace_fields_are_not_stripped_from_original_context(proofs):
    changed = dict(proofs)
    changed['WC'] = dict(proofs['WC'], context=copy.deepcopy(proofs['WC']['context']))
    changed['WC']['context']['identity']['body_names'][1] = '1/LFTibia'
    with pytest.raises(ValueError, match='context'): p.compare_proofs(changed)


@pytest.mark.parametrize('field,index', [('physical_prefix',5000), ('neural_prefix',999), ('rng',3999)])
def test_exact_prefix_and_full_rng_corruption_rejected(proofs, field, index):
    changed = dict(proofs)
    changed['WP'] = dict(proofs['WP'])
    changed['WP'][field] = list(proofs['WP'][field]); changed['WP'][field][index] = 'corrupt'
    with pytest.raises(ValueError): p.compare_proofs(changed)


def test_pair_gate_and_actual_outgoing_exposure_boundaries(proofs):
    changed = {c: dict(v) for c, v in proofs.items()}
    changed['WC']['actions'] = list(changed['WC']['actions'])
    changed['WC']['physics'] = list(changed['WC']['physics'])
    changed['WC']['actions'][5006] = 'different-command'
    changed['WC']['physics'][5006] = 'different-physical-state'
    exposure = p.compare_proofs(changed)['NC_vs_WC']
    assert exposure == dict(first_actual_outgoing_command_difference=5005,
        first_physical_difference_state=5006, first_actual_command_effect_state=5006)
    changed['WC']['pre_gate'] = 'changed prior safety state'
    with pytest.raises(ValueError, match='pre-gate'): p.compare_proofs(changed)


def test_incomplete_manifest_never_loads_or_accepts(synthetic):
    report = dict(synthetic[1], arm_artifacts={})
    result = p.evaluate(report, '.', loader=lambda *args: pytest.fail('loaded incomplete assay'))
    assert not result['accepted'] and not result['unity_replay_eligible']


@pytest.mark.parametrize('status', ['INCOMPLETE', 'ERROR'])
def test_incomplete_controller_cannot_be_promoted_with_four_artifacts(synthetic, status):
    report = dict(synthetic[1], run_status=status)
    result = p.evaluate(report, '.', loader=lambda *args: pytest.fail('loaded incomplete controller'))
    assert not result['accepted'] and not result['unity_replay_eligible']


def test_unknown_arm_cannot_create_a_request(tmp_path):
    with pytest.raises(ValueError, match='unknown fixed arm'): p.run_child(tmp_path, '../other', 'lock')
    assert not list(tmp_path.iterdir())


def test_worker_metadata_checked_before_original_audit(synthetic):
    report = synthetic[1]
    arm = dict(synthetic[2]['NC'], process_boundary=dict(synthetic[2]['NC']['process_boundary'], pid=100))
    with patch.object(p.base, 'audit_arm', side_effect=AssertionError('must reject first')):
        result = p.evaluate(report, '.', loader=lambda *args: arm)
    assert not result['accepted'] and 'fresh worker' in result['reason']


def test_source_change_rejects_before_raw_load(synthetic):
    report = dict(synthetic[1], sources_after={'changed': 'source'})
    assert not p.evaluate(report, '.', loader=lambda *args: pytest.fail('loaded changed source'))['accepted']


def test_raw_hash_and_condition_path_guard(tmp_path):
    p.base.save(tmp_path / 'NC.json.gz', {'synthetic': True})
    with pytest.raises(ValueError, match='SHA256'):
        p.read_arm(tmp_path, 'NC', dict(path='NC.json.gz', sha256='wrong'))
    with pytest.raises(ValueError, match='identity'):
        p.read_arm(tmp_path, 'WC', dict(path='../NC.json.gz', sha256='wrong'))


def test_child_uses_same_interpreter_once_and_preserves_error_receipt(tmp_path):
    calls = []
    class Process:
        pid = 1234
        def __init__(self, command, **kwargs):
            calls.append((command, kwargs))
            p.base.save(tmp_path / 'NC.done.json', dict(pid=self.pid, condition='NC', run_status='ERROR',
                artifact=dict(path='NC.json.gz', sha256='synthetic'), states=1, neural_updates=0))
        def poll(self): return 1
    with patch.object(p.subprocess, 'Popen', Process):
        receipt, interrupted = p.run_child(tmp_path, 'NC', 'controller-lock')
    assert len(calls) == 1 and calls[0][0][0] == sys.executable
    assert calls[0][0][2:4] == ['-m', 'malecns_backend.live.balance_contribution_process']
    assert receipt['run_status'] == 'ERROR' and receipt['states'] == 1 and not interrupted
    assert json.loads((tmp_path/'NC.request.json').read_text())['controller_sha256'] == 'controller-lock'
    if os.name == 'nt': assert calls[0][1]['creationflags'] & p.subprocess.CREATE_NO_WINDOW


def test_missing_worker_receipt_is_not_fabricated_or_retried(tmp_path):
    process = SimpleNamespace(pid=1234, poll=lambda: 37)
    with patch.object(p.subprocess, 'Popen', return_value=process) as create:
        with pytest.raises(RuntimeError, match='without a complete raw-file receipt'):
            p.run_child(tmp_path, 'NC', 'lock')
    assert create.call_count == 1 and not (tmp_path/'NC.done.json').exists()


def test_real_child_processes_have_fresh_fixture_registry_and_verified_os_ancestry(tmp_path):
    """Real OS launches; fake registry/data only, zero native/CNS construction."""
    driver = tmp_path / 'synthetic_worker.py'
    driver.write_text('''import sys
from types import SimpleNamespace
sys.path.insert(0, ROOT_VALUE)
from malecns_backend.live import balance_contribution_process as p
class FixtureFly:
    _existing_fly_names = set()
    _default_fly_name = 0
sys.modules['flygym'] = SimpleNamespace(Fly=FixtureFly)
p.committed = lambda: 'synthetic-commit'
p.base.environment = lambda: {'verified': True}
p.base.static_authority = lambda: ({}, [])
p.base.data_identities = lambda: {}
def synthetic_arm(condition, *args):
    assert FixtureFly._existing_fly_names == set()
    FixtureFly._existing_fly_names.add('0')
    return dict(condition=condition, run_status='COMPLETE', samples=[], neural=[], synthetic_process_fixture=True)
p.base.run_arm = synthetic_arm
raise SystemExit(p.worker(sys.argv[1]))
'''.replace('ROOT_VALUE', repr(str(p.ROOT))), encoding='utf-8')
    controller = p.base.save(tmp_path/'controller.json', dict(schema=p.SCHEMA, protocol=p.protocol(),
        commit='synthetic-commit', sources=p.sources()))
    actual_popen = p.subprocess.Popen
    def fixture_popen(command, **kwargs):
        assert command[0] == sys.executable
        return actual_popen([sys.executable, str(driver), command[-1]], **kwargs)
    pids = []
    with patch.object(p.subprocess, 'Popen', side_effect=fixture_popen):
        for condition in p.base.CONDITIONS:
            receipt, interrupted = p.run_child(tmp_path, condition, controller['sha256'])
            assert receipt['run_status'] == 'COMPLETE' and not interrupted
            assert receipt['process_boundary']['fresh_registry'] == dict(existing_names=[], default_name=0)
            assert p.valid_boundary(receipt['process_boundary'], os.getpid())
            arm = p.read_arm(tmp_path, condition, receipt['artifact'])
            assert arm['synthetic_process_fixture'] and arm['samples'] == [] and arm['neural'] == []
            pids.append(receipt['pid'])
    assert len(set(pids)) == 4


def test_process_protocol_source_must_be_committed_before_live():
    with patch.object(p.base, 'implementation_committed', return_value='commit'), patch.object(
            p.base, 'git', return_value=b'changed source'):
        with pytest.raises(ValueError, match='commit process'): p.committed()


def test_wp_failure_cannot_be_mislabeled_complete(tmp_path):
    counter = []
    def child(folder, condition, lock):
        counter.append(condition)
        return dict(run_status='ERROR' if condition=='WP' else 'COMPLETE',
                    artifact=dict(path=condition+'.json.gz', sha256='synthetic')), False
    with patch.object(p.base, 'preflight', return_value=dict(verified=True)), patch.object(
            p, 'committed', return_value='commit'), patch.object(p, 'run_child', side_effect=child), patch.object(
            p, 'evaluate', return_value=dict(accepted=False, status='INCONCLUSIVE_INTEGRITY')):
        result = p.execute(tmp_path/'exclusive', live=True)
    assert result['run_status'] == 'INCOMPLETE' and counter == list(p.base.CONDITIONS)


def test_first_error_stops_without_reusing_nc_or_starting_push(tmp_path):
    counter = []
    def child(folder, condition, lock):
        counter.append(condition)
        return dict(run_status='ERROR', artifact=dict(path=condition+'.json.gz', sha256='synthetic')), False
    with patch.object(p.base, 'preflight', return_value=dict(verified=True)), patch.object(
            p, 'committed', return_value='commit'), patch.object(p, 'run_child', side_effect=child), patch.object(
            p, 'evaluate', return_value=dict(accepted=False, status='INCONCLUSIVE_INTEGRITY')):
        result = p.execute(tmp_path/'exclusive', live=True)
    assert counter == ['NC'] and result['run_status'] == 'INCOMPLETE'
