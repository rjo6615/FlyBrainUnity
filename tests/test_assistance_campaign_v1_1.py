"""V1.1 guard correction and campaign gates. Toy MuJoCo/synthetic only; no fly or CNS."""
import copy
import importlib.util
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from malecns_backend.live import assistance_campaign_v1_1 as v
from malecns_backend.live import assistance_native_v1_1 as g
from malecns_backend.live import assistance_trial_v1_1 as t

base, mechanical = v.base, v.mechanical


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, v.ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


campaign_fixture = load('assistance_campaign_v1_fixture', 'tests/test_assistance_campaign.py')
native_fixture = campaign_fixture.native_fixture
checked, boundary = campaign_fixture.checked, campaign_fixture.boundary

TOY = '''<mujoco><option timestep="0.0001"/><worldbody><geom type="plane" size="1 1 .1"/>
<body pos="0 0 .06"><freejoint/><geom size=".05"/><body><joint name="h" type="hinge" damping=".1"/>
<geom size=".02" pos=".1 0 0"/><body pos=".1 0 0"><joint name="h2" type="hinge" axis="0 1 0"/>
<geom type="capsule" size=".01" fromto="0 0 0 0 0 -.08"/></body></body></body></worldbody>
<actuator><position joint="h" kp="2"/><position joint="h2" kp="2" kv=".1"/></actuator></mujoco>'''


def toy(islands=False):
    import mujoco
    model = mujoco.MjModel.from_xml_string(TOY)
    if islands:
        model.opt.enableflags |= mujoco.mjtEnableBit.mjENBL_ISLAND
    data = mujoco.MjData(model)
    for _ in range(200):
        mujoco.mj_step(model, data)  # contacts and constraints active
    return mujoco, model, data


# ---- real standalone MuJoCo regression of the failed capture path ---------

@pytest.mark.parametrize('islands', [False, True])
def test_guard_fields_are_exactly_mujoco_integration_state(islands):
    mujoco, model, data = toy(islands)
    assert data.ncon > 0 and data.nefc > 0 and (data.nisland > 0) == islands
    size = mujoco.mj_stateSize(model, mujoco.mjtState.mjSTATE_INTEGRATION)
    state = np.empty(size)
    mujoco.mj_getState(model, data, state, mujoco.mjtState.mjSTATE_INTEGRATION)
    fields = np.concatenate([np.asarray(getattr(data, n), dtype=float).ravel() for n in g.INTEGRATION_FIELDS])
    assert np.array_equal(fields, state)


@pytest.mark.parametrize('islands', [False, True])
def test_real_mjdata_guard_is_stable_across_reads_and_read_only_captures(islands):
    mujoco, model, data = toy(islands)
    for _ in range(20):
        fields = g.data_fields(data)
        assert len({g.data_digest(data) for _ in range(50)}) == 1
        mechanical.force_record(mujoco, model, data)
        g.require_unchanged(fields, data, 'read-only force record changed data')
        mujoco.mj_step(model, data)


def test_real_mutation_is_still_detected_and_named():
    _, _, data = toy()
    before = g.data_fields(data)
    data.qacc_warmstart[0] += 1e-12
    with pytest.raises(ValueError, match='qacc_warmstart'):
        g.require_unchanged(before, data, 'mutated')


def test_failed_v1_trial_capture_path_now_passes_on_real_mjdata():
    mujoco, model, data = toy()
    trial = t.Trial('A_NC')
    for _ in range(200):
        trial._capture_mechanical(SimpleNamespace(model=model, data=data))
    assert len(trial.mechanical_samples) == 200 and len(trial.mechanical_samples[0]['actuator_force']) == model.nu


# ---- synthetic force-law fixture under the V1.1 guard ---------------------

@pytest.fixture
def mech(monkeypatch):
    model, data, api, inv, record = native_fixture.fixture.__wrapped__(monkeypatch)
    extra = dict(eq_active=np.zeros(0, dtype=np.uint8), mocap_pos=np.zeros((0, 3)), mocap_quat=np.zeros((0, 4)),
                 userdata=np.zeros(0), plugin_state=np.zeros(0))
    data.__dict__.update(copy.deepcopy(extra))
    allocate = api.MjData
    def shadow(model):
        made = allocate(model); made.__dict__.update(copy.deepcopy(extra))
        return made
    api.MjData = shadow
    return model, data, api, inv, record


def test_v1_1_qualification_same_budget_records_guard_and_evaluates(mech):
    model, data, api, inv, record = mech
    report = {}
    g.qualify(api, model, data, inv, record, lambda: 'protected', report)
    assert report['live_guard'] == g.GUARD and report['live_fields_changed'] == []
    assert report['explicit_calls'] == dict(shadow_allocations=1, shadow_resets=12, shadow_forwards=12)
    assert mechanical.evaluate_qualification(report)['passed'] and report['restored'] == record


def test_v1_1_qualification_names_live_mutation_and_retains_partial(mech):
    model, data, api, inv, record = mech
    api.on_forward = lambda m, shadow: data.qvel.__setitem__(0, data.qvel[0]+1.)
    report = {}
    with pytest.raises(ValueError, match='live'):
        g.qualify(api, model, data, inv, record, lambda: 'protected', report)
    assert report['status'] == 'FAILED_QUALIFICATION' and report['live_fields_changed'] == ['qvel']
    assert len(report['cases']) == 12 and report['restored'] == record
    with pytest.raises(ValueError):
        g.qualify(api, model, data, inv, record, lambda: 'protected', report)


@pytest.mark.parametrize('arm_id', ['A_WP', 'R_NC'])
def test_v1_1_boundary_event_matches_v1_trace_contract(mech, arm_id):
    model, data, api, inv, record = mech
    report = {}
    g.qualify(api, model, data, inv, record, lambda: 'protected', report)
    gate = g.Intervention(arm_id, model, data, inv, record)
    gate.accept_qualification(report)
    for index in range(5007):
        data.time = index*.0001
        gate.boundary(index, lambda: 'protected')
    assert gate.event['live_guard'] == g.GUARD
    assert gate.event['after'] == (mechanical.neutral_record(record, inv) if arm_id.startswith('R_') else record)
    mechanical.write_rows(model, record, inv, False)


# ---- V1.1 Trial lifecycle ---------------------------------------------------

@pytest.mark.parametrize('arm', ['A_NC', 'R_WP'])
def test_v1_1_boundary_hook_uses_v1_1_qualify_after_original_gate(arm):
    trial = t.Trial(arm, None if arm == 'A_NC' else {'proof': 'provided'})
    events = []
    trial.session = SimpleNamespace(_state={'physics_transition': 0})
    trial.physics = SimpleNamespace(model=object(), data=object())
    trial.inventory = {}
    trial.intervention = SimpleNamespace(original={},
        accept_qualification=lambda proof: events.append('accept'),
        boundary=lambda index, guard: events.append(('boundary', index)))
    trial.mechanical_samples = [{}]
    def qualify(*args):
        events.append('qualify'); args[-1].update(passed=True)
    with (patch.object(t.base.Trial, 'state_boundary', lambda self: events.append('original gate')),
          patch.object(t.guard, 'qualify', qualify),
          patch.object(t.v1.mechanical, 'qualify', side_effect=AssertionError('V1 guard used'))):
        trial.state_boundary()
    assert events == (['original gate', 'qualify', 'accept', ('boundary', 0)] if arm == 'A_NC'
                      else ['original gate', 'accept', ('boundary', 0)])


def test_v1_1_run_arm_keeps_partials_and_new_schema(tmp_path):
    def run(condition, protocol, table, stop, *, trial_factory, **kwargs):
        trial = trial_factory(condition)
        assert type(trial) is t.Trial
        trial.mechanical_samples.append({'partial': 'evidence'})
        return {'run_status': 'ERROR', 'condition': condition}, {'display': 'partial'}
    with patch('malecns_backend.live.controlled_live_balance.run_arm', run):
        result, display = t.run_arm('R_WP', {}, [], tmp_path/'STOP.json', qualification={'prior': 'proof'})
    assert result['schema'] == t.SCHEMA and result['live_guard'] == g.GUARD
    assert result['assistance']['samples'] == [{'partial': 'evidence'}] and not result['full_scientific_audit_completed']
    with pytest.raises(ValueError):
        t.run_arm('A_NC', {}, [], tmp_path/'STOP.json', trial_factory=lambda c: None)


# ---- campaign identity and evaluator ------------------------------------

def test_amendment_locks_failed_attempt_unchanged_science_and_executed_sources():
    spec = v.specification()
    a = spec['amendment']
    assert a['failed_attempt']['executed_commit'] == '953b607877ee9b790bda73429f4ab2d64e677362'
    assert not a['scientific_parameters_changed'] and not a['acceptance_changed'] and a['automatic_retries'] == 0
    assert spec['scientific'] == v.v1.specification()
    assert {k: x for k, x in v.CAMPAIGN.items() if k not in ('schema', 'amendment', 'live_guard')} == {
        k: x for k, x in v.v1.CAMPAIGN.items() if k != 'schema'}
    s = v.sources()
    assert set(v.v1.sources()) <= set(s) and v.AMENDMENT in s and v.MODULE in s
    v.v1.source_check()


def test_retained_failed_attempt_stays_inconclusive_without_loading_raw():
    folder = v.ROOT/'docs/evidence/assistance-campaign-v1/run-desktop-01'
    report = json.loads((folder/'report.json').read_text())
    assert report['run_status'] == 'INCOMPLETE' and list(report['arm_artifacts']) == ['A_NC']
    result = v.v1.evaluate(report, folder, loader=lambda *a: pytest.fail('raw loaded'))['scientific']
    assert not result['accepted']
    done = json.loads((folder/'A_NC.done.json').read_text())
    assert (done['run_status'], done['states'], done['neural_updates'], done['mechanical_states']) == ('ERROR', 1, 0, 0)


@pytest.fixture(scope='module')
def world():
    w = campaign_fixture.world.__wrapped__()
    qualification = dict(w['qualification'], live_guard=g.GUARD)
    arms = {}
    for arm_id, arm in w['arms'].items():
        ev = arm['assistance']
        arms[arm_id] = dict(arm, schema=t.SCHEMA, live_guard=g.GUARD, assistance=dict(ev, qualification=qualification,
            context=dict(ev['context'], live_guard=g.GUARD), event=dict(ev['event'], live_guard=g.GUARD)))
    report = dict(w['report'], schema=v.SCHEMA, campaign=v.CAMPAIGN, specification=v.specification(),
                  sources_before=v.sources(), sources_after=v.sources())
    for arm in arms.values():
        arm.update(worker_sources_before=report['sources_before'], worker_sources_after=report['sources_after'])
    return dict(w, arms=arms, report=report, qualification=qualification)


def evaluate(world, arms=None):
    arms = arms or world['arms']
    def missing(*args):
        raise OSError('synthetic fixture has no display journal')
    return v.evaluate(world['report'], '.', loader=lambda folder, a, artifact: arms[a], display_loader=missing,
        qualification_loader=lambda folder, artifact: world['qualification'],
        reference_comparator=lambda *a: dict(status='SYNTHETIC_NOT_COMPARED'))['scientific']


def test_v1_1_synthetic_eight_arms_accepted_with_unchanged_science(world):
    result = evaluate(world)
    assert result['accepted'], result.get('reason')
    assert all(result['checks'].values()) and len(result['behavior']['comparisons']) == 8
    assert {a: r['model_context'] for a, r in result['arms'].items()} == {
        a: 'M0_CONSTANT_FROZEN_AUDITOR_ACCEPTED' if a.startswith('A_') else 'PIECEWISE_M0_0_5005_MR_5006_20000'
        for a in v.ARM_IDS}
    assert not result['behavior']['independent_balance_proven']


@pytest.mark.parametrize('where', ['arm', 'context', 'event'])
def test_arm_without_v1_1_guard_identity_is_rejected(world, where):
    arm = dict(world['arms']['R_NP'])
    ev = dict(arm['assistance'])
    if where == 'arm':
        arm['live_guard'] = 'v1'
    elif where == 'context':
        ev['context'] = dict(ev['context'], live_guard='v1')
    else:
        ev['event'] = dict(ev['event'], live_guard='v1')
    arm['assistance'] = ev
    with pytest.raises(ValueError, match='identity'):
        v.audit_mechanical(arm, 'R_NP', world['qualification'])


def test_v1_qualification_without_new_guard_is_not_transferred(tmp_path, world):
    old = v.save(tmp_path/v.QUALIFICATION, dict(world['qualification'], live_guard=None))
    with pytest.raises(ValueError, match='V1.1 live-data guard'):
        v.read_qualification(tmp_path, old)
    good = v.save(tmp_path/('ok-'+v.QUALIFICATION), world['qualification'])
    with pytest.raises(ValueError, match='path'):
        v.read_qualification(tmp_path, good)


# ---- controller and worker ----------------------------------------------

def run_controller(tmp_path, child, *, note='user reviewed V1.1 saved replay', verified=True):
    with patch.object(v, 'preflight', return_value=dict(checked(), verified=verified)), \
            patch.object(v, 'committed', return_value='commit'), \
            patch.object(v, 'evaluate', return_value=dict(scientific=dict(accepted=False, status='INCONCLUSIVE_INTEGRITY'))):
        return v.execute(tmp_path/'campaign', live=True, review_note=note, child_runner=child)


receipt = campaign_fixture.receipt


def test_controller_refuses_unverified_prerequisites_before_workers(tmp_path):
    report = run_controller(tmp_path, lambda *a: pytest.fail('worker launched'), verified=False)
    assert report['run_status'] == 'ERROR' and not report['scientific_experiment_started']


def test_controller_transfers_v1_1_qualification_to_every_later_arm(tmp_path, world):
    calls = []
    def child(folder, arm_id, lock, transfer):
        calls.append(transfer)
        made = v.save(folder/v.QUALIFICATION, world['qualification']) if arm_id == v.FIRST else None
        return receipt(arm_id, qualification=made), False
    report = run_controller(tmp_path, child)
    assert report['run_status'] == 'COMPLETE' and calls[0] is None
    assert all(c == report['qualification_artifact'] for c in calls[1:]) and len(calls) == 8


def test_failed_first_arm_stops_and_keeps_partial(tmp_path):
    calls = []
    def child(folder, arm_id, lock, transfer):
        calls.append(arm_id)
        made = v.save(folder/v.QUALIFICATION, None)
        return receipt(arm_id, 'ERROR', made), False
    report = run_controller(tmp_path, child)
    assert calls == ['A_NC'] and report['run_status'] == 'INCOMPLETE' and report['qualification_artifact'] is None


def controller(folder, arm_id, transfer=None):
    folder.mkdir(exist_ok=True)
    made = v.save(folder/'controller.json', dict(schema=v.SCHEMA, campaign=v.CAMPAIGN, specification=v.specification(),
        sources=v.sources(), commit='fixture', prior_full_body_review_note='synthetic fixture only',
        complete_preflight=checked()))
    request = folder/f'{arm_id}.request.json'
    v.save(request, dict(arm_id=arm_id, controller_sha256=made['sha256'], qualification=transfer))
    return request


def run_worker(request, run):
    with patch.object(v, 'committed', return_value='fixture'), \
            patch.object(v.original, 'process_boundary', return_value=boundary(300)), \
            patch.object(v, 'preflight', return_value=checked()), \
            patch.object(base, 'static_authority', return_value=({}, [])), \
            patch.dict(sys.modules, {'flygym': SimpleNamespace(Fly=campaign_fixture.FixtureFly)}), \
            patch.object(v.adapter, 'run_arm', side_effect=run):
        return v.worker(request)


def test_worker_uses_v1_1_adapter_and_reevaluated_transfer(tmp_path, world):
    made = v.save(tmp_path/v.QUALIFICATION, world['qualification'])
    request = controller(tmp_path, 'R_WP', made)
    seen = []
    def run(arm_id, protocol, table, stop, *, qualification):
        seen.append(qualification)
        return dict(arm_id=arm_id, condition='WP', run_status='COMPLETE', samples=[], neural=[], assistance=None), None
    assert run_worker(request, run) == 0
    assert seen == [world['qualification']]
    done = json.loads((tmp_path/'R_WP.done.json').read_text())
    assert done['run_status'] == 'COMPLETE' and done['mechanical_states'] == 0


def test_worker_initialization_failure_publishes_null_first_qualification(tmp_path):
    request = controller(tmp_path, 'A_NC')
    assert run_worker(request, ValueError('binding refused')) == 1
    done = json.loads((tmp_path/'A_NC.done.json').read_text())
    assert v.read_artifact(tmp_path, done['qualification_artifact'], v.QUALIFICATION) is None
    assert 'binding refused' in v.read_arm(tmp_path, 'A_NC', done['artifact'])['worker_error']


def test_real_child_processes_launch_v1_1_worker_with_verified_ancestry(tmp_path, world):
    script = tmp_path/'synthetic_worker.py'
    script.write_text('''import sys
from types import SimpleNamespace
sys.path.insert(0, ROOT_VALUE)
from malecns_backend.live import assistance_campaign_v1_1 as v
class FixtureFly:
    _existing_fly_names = set()
    _default_fly_name = 0
sys.modules['flygym'] = SimpleNamespace(Fly=FixtureFly)
v.committed = lambda: 'synthetic-commit'
v.preflight = lambda: CHECKED
v.base.static_authority = lambda: ({}, [])
v.read_qualification = lambda folder, artifact: v.read_artifact(folder, artifact, v.QUALIFICATION)
def run(arm_id, protocol, table, stop, *, qualification):
    q = qualification if qualification is not None else {'synthetic': 'first'}
    return dict(arm_id=arm_id, condition=arm_id[2:], run_status='COMPLETE', samples=[], neural=[],
                assistance=dict(qualification=q, samples=[])), None
v.adapter.run_arm = run
raise SystemExit(v.worker(sys.argv[1]))
'''.replace('ROOT_VALUE', repr(str(v.ROOT))).replace('CHECKED', repr(checked())), encoding='utf-8')
    made = v.save(tmp_path/'controller.json', dict(schema=v.SCHEMA, campaign=v.CAMPAIGN, specification=v.specification(),
        sources=v.sources(), commit='synthetic-commit', prior_full_body_review_note='synthetic fixture only',
        complete_preflight=checked()))
    actual = v.subprocess.Popen
    def popen(command, **kwargs):
        assert command[3] == 'malecns_backend.live.assistance_campaign_v1_1'
        return actual([sys.executable, str(script), command[-1]], **kwargs)
    with patch.object(v.subprocess, 'Popen', side_effect=popen):
        first, _ = v.run_child(tmp_path, 'A_NC', made['sha256'], None)
        second, _ = v.run_child(tmp_path, 'A_WC', made['sha256'], first['qualification_artifact'])
    for r in (first, second):
        assert r['run_status'] == 'COMPLETE' and v.original.valid_boundary(r['process_boundary'], os.getpid())
    assert first['pid'] != second['pid']
    assert v.read_arm(tmp_path, 'A_WC', second['artifact'])['assistance']['qualification'] == {'synthetic': 'first'}


# ---- static entry points --------------------------------------------------

def test_cli_and_source_checkpoint(tmp_path, capsys):
    for args in (['--live'], ['--check', '--review-note', 'x'], ['--output', 'x', '--live']):
        with pytest.raises(SystemExit):
            v.main(args)
    value = v.implementation_record()
    path = tmp_path/'implementation.json'; path.write_text(json.dumps(value))
    assert v.source_check(path) == value
    value['campaign'] = dict(value['campaign'], automatic_retries=1); path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='checkpoint'):
        v.source_check(path)
    with patch.object(v, 'source_check'):
        assert v.main(['--check']) == 0
    assert 'not run by this check' in capsys.readouterr().out


def test_uncommitted_v1_1_source_blocks_execution():
    with patch.object(v.v1.guard, 'committed', return_value='head'), patch.object(base, 'git', return_value=b'changed'):
        with pytest.raises(ValueError, match='commit V1.1'):
            v.committed()
