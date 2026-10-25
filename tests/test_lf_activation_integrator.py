"""Implementation checks distinguish analytic mocks from native source calls."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import lf_activation_integrator as integration
from malecns_backend.embodiment import lf_activation_integrator_validation as assay


def test_radau_matches_analytic_linear_law_without_mutating_input():
    # Analytic mock only tests solver plumbing, not the native muscle model.
    native = SimpleNamespace(mju_muscleDynamics=lambda c, a, p: (c-a)/.001)
    a = np.array([0., .2, .5, 1.])
    original = a.copy()
    times = np.array([.000025, .00005, .0001])
    actual = integration.integrate_interval(native, a, np.ones(4), np.zeros((4, 10)), .0001, times)
    expected = 1+(original-1)*np.exp(-times[:, None]/.001)
    assert np.array_equal(a, original)
    assert np.max(np.abs(np.asarray(actual['samples'])-expected)) < 1e-9
    assert actual['solver']['success'] and actual['solver']['times'][-1] == .0001


@pytest.mark.parametrize('defect', ['duration', 'control', 'parameters', 'offsets', 'nan'])
def test_integrator_rejects_invalid_intervals(defect):
    inputs = dict(native=None, initial=np.zeros(4), effective_control=np.zeros(4),
                  dynprm=np.zeros((4, 10)), duration=.0001, sample_offsets=[.0001])
    if defect == 'duration': inputs['duration'] = 0.
    if defect == 'control': inputs['effective_control'] = np.zeros(3)
    if defect == 'parameters': inputs['dynprm'] = np.zeros((4, 2))
    if defect == 'offsets': inputs['sample_offsets'] = [.0001, .000025]
    if defect == 'nan': inputs['initial'][0] = np.nan
    with pytest.raises(ValueError): integration.integrate_interval(**inputs)


def test_native_state_ownership_and_force_timing_without_native_step(monkeypatch):
    import mujoco as native
    model = native.MjModel.from_xml_path(str(assay.ROOT/assay.prior.FIXTURE))
    data = native.MjData(model)
    binding = json.loads((assay.ROOT/assay.prior.BINDING).read_text())
    assert assay.valid_metadata(assay.metadata(native, model), binding)
    data.act[:] = .5
    snapshot = model.actuator_dynprm.copy()
    forward = native.mj_forward
    calls = []
    def observed(*args):
        calls.append(float(data.time))
        return forward(*args)
    def forbidden(*args): raise AssertionError('native activation must not advance twice')
    monkeypatch.setattr(native, 'mj_forward', observed)
    monkeypatch.setattr(native, 'mj_step', forbidden)
    result = integration.advance_fixed_fixture(native, model, data, 0., .0001, [.000025, .00005, .000075, .0001])
    gain, bias = np.asarray(binding['frozen_gain']), np.asarray(binding['frozen_bias'])
    assert calls == [0., .0001]
    assert data.time == .0001 and data.qpos.size == data.qvel.size == 0
    assert np.array_equal(snapshot, model.actuator_dynprm)
    assert result['effective_control'] == [.0001]*4 and result['before'] == [.5]*4
    assert np.max(np.abs(np.asarray(result['force_before'])-(.5*gain+bias))) <= 1e-8
    assert np.max(np.abs(np.asarray(result['force_after'])-(data.act*gain+bias))) <= 1e-8
    for k in ('derivative_before', 'derivative_after'):
        assert np.max(np.abs(np.asarray(result[k])-result['native_'+k])) <= 1e-8


@pytest.mark.parametrize('defect', ['address', 'clamp', 'moving'])
def test_adapter_refuses_unsupported_ownership(defect):
    import mujoco as native
    if defect == 'moving':
        model = native.MjModel.from_xml_string('<mujoco><worldbody><body><joint/><geom size=".1"/></body></worldbody></mujoco>')
    else:
        model = native.MjModel.from_xml_path(str(assay.ROOT/assay.prior.FIXTURE))
        if defect == 'address': model.actuator_actadr[0] = 1
        if defect == 'clamp': model.actuator_actlimited[0] = 1
    data = native.MjData(model)
    with pytest.raises(ValueError): integration.advance_fixed_fixture(native, model, data, 0., .0001, [.0001])
    assert data.time == 0


def test_solver_failure_does_not_commit_state_or_time(monkeypatch):
    import mujoco as native
    model = native.MjModel.from_xml_path(str(assay.ROOT/assay.prior.FIXTURE))
    data = native.MjData(model)
    data.act[:] = .5
    monkeypatch.setattr(integration, 'solve_ivp', lambda *a, **k: SimpleNamespace(success=False, message='injected failure'))
    with pytest.raises(ValueError, match='injected failure'):
        integration.advance_fixed_fixture(native, model, data, 1., .0001, [.0001])
    assert data.time == 0 and np.array_equal(data.act, [.5]*4)


def forbid_computation(monkeypatch):
    import mujoco as native
    from malecns_backend.embodiment import _windows_m7_spontaneous_locomotion_adapter as old
    def forbidden(*a, **k): raise AssertionError('static review cannot construct a model or integrate')
    for key in ('MjModel', 'mj_forward', 'mj_step', 'mju_muscleDynamics'):
        monkeypatch.setattr(native, key, forbidden)
    monkeypatch.setattr(integration, 'solve_ivp', forbidden)
    monkeypatch.setattr(assay.prior, 'solve_ivp', forbidden)
    monkeypatch.setattr(old, 'enumerate_live_actuators', forbidden)


def test_preflight_reuses_exact_reference_without_native_or_solver(monkeypatch):
    forbid_computation(monkeypatch)
    ready = assay.preflight()
    assert ready['sources'][assay.PREVIOUS] == assay.PREVIOUS_SHA
    assert len(ready['references']['PULSE']) == 401
    assert not ready['euler_evaluation']['all_numerically_accepted']


def test_failure_output_is_retained_exclusively(tmp_path, monkeypatch):
    monkeypatch.setattr(assay, 'preflight', lambda: {})
    def fail(*args): raise ValueError('injected source failure')
    monkeypatch.setattr(assay, 'execute', fail)
    output = tmp_path/'fresh'
    assert assay.main(['--execute', '--output-dir', str(output)]) == 1
    before = (output/'validation.json').read_bytes()
    assert 'injected source failure' in before.decode()
    with pytest.raises(FileExistsError): assay.main(['--execute', '--output-dir', str(output)])
    assert (output/'validation.json').read_bytes() == before


def saved():
    return json.loads((assay.ROOT/(assay.DIRECTORY+'run/validation.json')).read_text(encoding='utf-8'))


def test_saved_review_does_not_integrate(monkeypatch):
    forbid_computation(monkeypatch)
    assert assay.main(['--report', str(assay.ROOT/(assay.DIRECTORY+'run/validation.json'))]) == 0


def test_saved_acceptance_recomputes_all_dense_samples_and_preserves_euler():
    report = saved()
    result = assay.evaluate(report, report['ready'])
    assert result['integrity_passed']
    assert not report['ready']['euler_evaluation']['all_numerically_accepted']
    for case, row in zip(report['cases'], result['cases']):
        dense = np.vstack((case['initial']['activation'], *[r['samples'] for r in case['steps']]))
        ref = np.asarray(report['ready']['references'][case['condition']])
        assert len(dense) == 401
        assert row['maximum_activation_error'] == np.max(np.abs(dense-ref))
        assert row['numerical_acceptance'] == all(row['numerical_checks'].values())


@pytest.mark.parametrize('defect', ['drop', 'state', 'time', 'force', 'control', 'nodes', 'counter', 'identity', 'dense'])
def test_saved_corruption_rejected(defect):
    report = saved()
    first = report['cases'][0]['steps'][0]
    if defect == 'drop': report['cases'].pop()
    if defect == 'state': first['before'][0] += .1
    if defect == 'time': first['time'] += .001
    if defect == 'force': first['force_after'][0] += 1
    if defect == 'control': first['effective_control'][0] = 1
    if defect == 'nodes': first['solver']['times'][-1] += .001
    if defect == 'counter': report['api_calls']['mj_step'] += 1
    if defect == 'identity': report['compiled'][0]['actadr'][0] = 2
    if defect == 'dense': first['samples'][-1][0] += .1
    assert not assay.evaluate(report, report['ready'])['integrity_passed']
