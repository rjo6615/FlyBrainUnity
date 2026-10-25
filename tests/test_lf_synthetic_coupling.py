"""Synthetic native mechanics/ownership checks, separate from fly experiments."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import lf_synthetic_coupling as audit


@pytest.fixture(scope='module')
def ready():
    return dict(reference=audit.force.load_reference(),
                binding=json.loads((audit.ROOT/audit.schedule.BINDING).read_text(encoding='utf-8')))


@pytest.fixture
def fixture(ready):
    import mujoco as native
    model = native.MjModel.from_xml_path(str(audit.ROOT/audit.FIXTURE))
    data = native.MjData(model)
    data.qfrc_applied[:] = audit.FOREIGN
    data.xfrc_applied[:] = audit.foreign_body()
    adapter = audit.SyntheticSplitAdapter(native, model, data, ready, np.full(4, .5))
    return native, model, data, adapter


def test_native_left_endpoint_force_once_only_body_and_external_commit(fixture, ready):
    native, model, data, adapter = fixture
    old = adapter.activation
    alias = adapter.activation; alias[:] = 0
    assert np.array_equal(adapter.activation, old)
    torque = audit.projected_torque(ready, old)
    row = adapter.advance('RELAX_ZERO')
    expected_force = audit.FOREIGN_TOTAL.copy(); expected_force[1:] += torque
    assert data.time == model.opt.timestep and adapter.transitions == 1
    assert np.max(np.abs(data.qvel-model.opt.timestep*expected_force/audit.INERTIA)) <= 1e-12
    assert np.max(np.abs(data.qpos-model.opt.timestep*data.qvel)) <= 1e-12
    assert row['torque'] == torque.tolist() and not np.array_equal(adapter.activation, old)
    assert row['activation_after'] == row['solver']['after']
    assert np.array_equal(data.qfrc_applied, audit.FOREIGN)
    assert np.array_equal(data.xfrc_applied, audit.foreign_body())


def test_owned_clear_preserves_both_foreign_buffers_and_rejects_duplicate(fixture):
    _, _, data, adapter = fixture
    adapter.apply(np.array([.1, .2, .3]))
    assert data.qfrc_applied.tolist() == [.125, .1, .2, .3]
    with pytest.raises(ValueError): adapter.apply(np.ones(3))
    adapter.clear()
    assert np.array_equal(data.qfrc_applied, audit.FOREIGN)
    assert np.array_equal(data.xfrc_applied, audit.foreign_body())
    with pytest.raises(ValueError): adapter.clear()


@pytest.mark.parametrize('defect', ['target_force', 'sentinel_force', 'body_wrench', 'time', 'gravity', 'inertia', 'timestep'])
def test_foreign_force_or_context_corruption_fails_before_step(fixture, defect):
    _, model, data, adapter = fixture
    if defect == 'target_force': data.qfrc_applied[1] = 1.
    if defect == 'sentinel_force': data.qfrc_applied[0] += .1
    if defect == 'body_wrench': data.xfrc_applied[2, 0] = 1.
    if defect == 'time': data.time = .001
    if defect == 'gravity': model.opt.gravity[2] = -1.
    if defect == 'inertia': model.body_inertia[2, 0] += .1
    if defect == 'timestep': model.opt.timestep *= 2
    before = data.qpos.copy()
    with pytest.raises(ValueError): adapter.advance('PULSE')
    assert adapter.transitions == 0 and np.array_equal(data.qpos, before)


@pytest.mark.parametrize('after_native', [False, True])
def test_body_failure_latches_and_preserves_uncertain_advance(fixture, monkeypatch, after_native):
    native, model, data, adapter = fixture
    original = native.mj_step
    def failed(*args):
        if after_native: original(*args)
        raise RuntimeError('injected body failure')
    monkeypatch.setattr(native, 'mj_step', failed)
    before = adapter.activation
    with pytest.raises(RuntimeError): adapter.advance('RELAX_ZERO')
    assert adapter.failed and adapter.transitions == 0
    assert np.array_equal(before, adapter.activation)
    assert data.time == (model.opt.timestep if after_native else 0.)
    assert np.array_equal(data.qfrc_applied, audit.FOREIGN) and np.array_equal(data.xfrc_applied, audit.foreign_body())
    assert adapter.last_attempt['failure_state']['time'] == data.time
    with pytest.raises(ValueError): adapter.advance('RELAX_ZERO')


def test_continuous_reference_constant_torque_matches_analytic_rotor_solution(ready):
    import mujoco as native
    ref = audit.continuous_reference(native, ready, 'FLOOR_BASELINE')
    t, states = np.asarray(ref['times']), np.asarray(ref['states'])
    a = np.asarray(ready['binding']['ctrlrange'])[:, 0]
    total = audit.FOREIGN_TOTAL.copy(); total[1:] += audit.projected_torque(ready, a)
    acc = total/audit.INERTIA
    assert np.max(np.abs(states[:, :4]-a)) == 0
    assert np.max(np.abs(states[:, 4:8]-.5*t[:, None]**2*acc)) <= 1e-12
    assert np.max(np.abs(states[:, 8:]-t[:, None]*acc)) <= 1e-12


def forbid_computation(monkeypatch):
    import mujoco
    import flygym
    from malecns_backend import neural
    def forbidden(*a, **k): raise AssertionError('static review must not execute native/solver/CNS')
    for key in ('MjModel', 'MjData', 'mj_forward', 'mj_step', 'mju_muscleDynamics'):
        monkeypatch.setattr(mujoco, key, forbidden)
    monkeypatch.setattr(flygym, 'Fly', forbidden)
    monkeypatch.setattr(neural, 'MaleCNSBrain', forbidden)
    monkeypatch.setattr(audit, 'solve_ivp', forbidden)
    monkeypatch.setattr(audit.activation, 'solve_ivp', forbidden)
    monkeypatch.setattr(audit.schedule, 'solve_ivp', forbidden)


def test_preflight_is_native_and_solver_free(monkeypatch):
    forbid_computation(monkeypatch)
    ready = audit.preflight()
    assert ready['reference']['basis'] == list(audit.force.BASIS)


def test_exclusive_failure_output_is_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'preflight', lambda: {})
    def failed(*a): raise ValueError('injected source failure')
    monkeypatch.setattr(audit, 'execute', failed)
    output = tmp_path/'fresh'
    assert audit.main(['--execute', '--output-dir', str(output)]) == 1
    raw = (output/'validation.json').read_bytes()
    assert 'injected source failure' in raw.decode()
    with pytest.raises(FileExistsError): audit.main(['--execute', '--output-dir', str(output)])
    assert (output/'validation.json').read_bytes() == raw


def saved(): return audit.upstream.load_report(audit.ROOT/(audit.DIRECTORY+'run/validation.json'))


def test_saved_review_executes_no_native_reference_or_cns(monkeypatch):
    forbid_computation(monkeypatch)
    assert audit.main(['--report', str(audit.ROOT/(audit.DIRECTORY+'run/validation.json'))]) == 0


def test_saved_full_window_errors_and_all_grids_are_retained():
    report = saved()
    actual = audit.evaluate(report, report['ready'])
    assert actual['integrity_passed'] and len(actual['cases']) == 9
    for case, result in zip(report['cases'], actual['cases']):
        stride = round(case['dt']/audit.schedule.DTS[-1])
        ref = np.asarray(report['references'][case['condition']]['states'])[::stride]
        q = np.vstack((case['initial']['qpos'], [r['after_clear']['qpos'] for r in case['steps']]))
        v = np.vstack((case['initial']['qvel'], [r['after_clear']['qvel'] for r in case['steps']]))
        assert result['maximum_position_error'] == np.max(np.abs(q-ref[:, 4:8]))
        assert result['maximum_velocity_error'] == np.max(np.abs(v-ref[:, 8:]))
        assert result['numerical_acceptance'] == all(result['numerical_checks'].values())


@pytest.mark.parametrize('defect', ['drop', 'time', 'foreign', 'owned', 'activation', 'step_counter', 'mass', 'solver', 'metadata'])
def test_saved_corruption_is_rejected(defect):
    report = saved(); row = report['cases'][0]['steps'][0]
    if defect == 'drop': report['cases'].pop()
    if defect == 'time': row['after_clear']['time'] += .001
    if defect == 'foreign': row['after_clear']['body'][1][5] = 0.
    if defect == 'owned': row['applied']['generalized'][0] = 1.
    if defect == 'activation': row['activation_after'][0] += .1
    if defect == 'step_counter': report['api_calls']['mj_step'] += 1
    if defect == 'mass': report['calibrations'][0]['mass'][0][0] = 2.
    if defect == 'solver': row['solver']['solver']['success'] = False
    if defect == 'metadata': report['cases'][0]['metadata'][0]['body_id'] = 1
    assert not audit.evaluate(report, report['ready'])['integrity_passed']
