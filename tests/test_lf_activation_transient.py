"""Activation-only reference plumbing; numerical failures are not hidden."""
import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import lf_activation_transient as transient


@pytest.mark.parametrize('dt', transient.DTS)
def test_fixed_control_boundaries_are_outgoing_interval_indices(dt):
    on, off = round(.002/dt), round(.005/dt)
    assert transient.raw_control('PULSE', on-1, dt) == 0
    assert transient.raw_control('PULSE', on, dt) == 1
    assert transient.raw_control('PULSE', off-1, dt) == 1
    assert transient.raw_control('PULSE', off, dt) == 0
    assert transient.raw_control('RELAX_ZERO', on, dt) == 0
    assert transient.raw_control('FLOOR_BASELINE', on, dt) == 0
    with pytest.raises(ValueError): transient.raw_control('unregistered', 0, dt)


def test_native_fixture_has_no_body_dofs_and_preserves_source_force_parameters():
    import mujoco
    binding = json.loads((transient.ROOT/transient.BINDING).read_text(encoding='utf-8'))
    model = mujoco.MjModel.from_xml_path(str(transient.ROOT/transient.FIXTURE))
    assert model.nq == model.nv == model.ngeom == 0
    assert model.nu == model.na == model.ntendon == 4
    assert not np.any(model.actuator_actearly)
    for key in ('dynprm', 'gainprm', 'biasprm', 'ctrlrange'):
        assert np.array_equal(getattr(model, 'actuator_'+key), binding[key])
    for level, expected in zip((0., .5, 1.), binding['frozen_forces']):
        data = mujoco.MjData(model)
        data.act[:] = level
        data.ctrl[:] = level
        mujoco.mj_forward(model, data)
        assert np.max(np.abs(data.actuator_force-expected)) <= 1e-8


def test_piecewise_independent_solver_boundaries_with_analytic_linear_test_law():
    # Mocked linear ODE tests solver plumbing only, not native muscle physiology.
    native = SimpleNamespace(mju_muscleDynamics=lambda c, a, p: (c-a)/.001)
    floor = np.full(4, .0001)
    times = np.array([0., .002, .003, .005, .01])
    actual = transient.continuous_reference(native, np.zeros((4, 10)), floor, 'PULSE', times)
    a5 = 1+(.0001-1)*np.exp(-3)
    expected = np.array([.0001, .0001, 1+(.0001-1)*np.exp(-1), a5,
                         .0001+(a5-.0001)*np.exp(-5)])
    assert np.max(np.abs(actual-expected[:, None])) <= 1e-10


def test_native_single_step_and_force_refresh_use_different_activation_times():
    import mujoco
    binding = json.loads((transient.ROOT/transient.BINDING).read_text(encoding='utf-8'))
    model = mujoco.MjModel.from_xml_path(str(transient.ROOT/transient.FIXTURE))
    data = mujoco.MjData(model)
    data.act[:] = .5
    data.ctrl[:] = 0.
    floor = np.clip(np.zeros(4), model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
    derivative = np.array([mujoco.mju_muscleDynamics(c, .5, p[:3]) for c, p in zip(floor, model.actuator_dynprm)])
    expected = np.full(4, .5)+model.opt.timestep*derivative
    for i, limited in enumerate(model.actuator_actlimited):
        if limited: expected[i] = np.clip(expected[i], *model.actuator_actrange[i])
    gain, bias = np.asarray(binding['frozen_gain']), np.asarray(binding['frozen_bias'])
    mujoco.mj_step(model, data)
    assert np.max(np.abs(data.act-expected)) <= 1e-10
    assert np.max(np.abs(data.actuator_force-(gain*.5+bias))) <= 1e-8
    mujoco.mj_forward(model, data)
    assert np.max(np.abs(data.actuator_force-(gain*expected+bias))) <= 1e-8
    assert data.qpos.size == data.qvel.size == 0 and data.time == model.opt.timestep


def test_preflight_is_model_and_integration_free(monkeypatch):
    import mujoco
    from malecns_backend.embodiment import _windows_m7_spontaneous_locomotion_adapter as old
    def forbidden(*a, **k): raise AssertionError('no model/native/reference integration allowed')
    for key in ('MjModel', 'mj_forward', 'mj_step'): monkeypatch.setattr(mujoco, key, forbidden)
    monkeypatch.setattr(transient, 'solve_ivp', forbidden)
    monkeypatch.setattr(old, 'enumerate_live_actuators', forbidden)
    ready = transient.preflight()
    assert ready['binding']['source_xml_sha256'] == transient.pose.binding.MODEL_HASH


def test_failure_output_is_exclusive_and_not_replaced(tmp_path, monkeypatch):
    monkeypatch.setattr(transient, 'preflight', lambda: {})
    def fail(ready): raise ValueError('source mismatch')
    monkeypatch.setattr(transient, 'execute', fail)
    output = tmp_path/'attempt'
    args = ['--execute', '--output-dir', str(output)]
    assert transient.main(args) == 1
    raw = (output/'validation.json').read_bytes()
    assert json.loads(raw)['status'] == 'INTEGRITY_ERROR'
    with pytest.raises(FileExistsError): transient.main(args)
    assert (output/'validation.json').read_bytes() == raw


def test_saved_review_does_not_integrate_native_or_reference(monkeypatch):
    import mujoco
    def forbidden(*a, **k): raise AssertionError('saved review cannot reconstruct dynamics')
    for key in ('MjModel', 'mj_forward', 'mj_step'): monkeypatch.setattr(mujoco, key, forbidden)
    monkeypatch.setattr(transient, 'solve_ivp', forbidden)
    assert transient.main(['--report', str(transient.ROOT/(transient.DIRECTORY+'run/validation.json'))]) == 0


def test_saved_numerical_acceptance_is_full_window_and_separate_from_integrity():
    raw = json.loads((transient.ROOT/(transient.DIRECTORY+'run/validation.json')).read_text(encoding='utf-8'))
    actual = transient.evaluate(raw, raw['ready'])
    assert actual['integrity_passed']
    assert len(actual['cases']) == 9
    for case, result in zip(raw['cases'], actual['cases']):
        a = np.vstack((case['initial']['activation'], [r['after'] for r in case['steps']]))
        ref = np.asarray(case['reference_activations'])
        error = float(np.max(np.abs(a-ref)))
        bounded = np.min(a) >= -1e-12 and np.max(a) <= 1+1e-12
        assert result['maximum_activation_error'] == error
        assert result['numerical_acceptance'] == bool(bounded and error <= .01)
    assert actual['all_numerically_accepted'] == all(c['numerical_acceptance'] for c in actual['cases'])


@pytest.mark.parametrize('defect', ['drop', 'time', 'force', 'control', 'length', 'counter'])
def test_saved_integrity_defects_rejected(defect):
    raw = json.loads((transient.ROOT/(transient.DIRECTORY+'run/validation.json')).read_text(encoding='utf-8'))
    if defect == 'drop': raw['cases'].pop()
    if defect == 'time': raw['cases'][0]['steps'][0]['time'] += .001
    if defect == 'force': raw['cases'][0]['steps'][0]['refreshed_force'][0] += 1
    if defect == 'control': raw['cases'][2]['steps'][0]['raw_control'] = 1
    if defect == 'length': raw['cases'][0]['steps'][0]['length'][0] += .1
    if defect == 'counter': raw['api_calls']['mj_step'] += 1
    assert not transient.evaluate(raw, raw['ready'])['integrity_passed']
