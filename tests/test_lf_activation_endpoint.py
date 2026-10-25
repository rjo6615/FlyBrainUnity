"""Endpoint semantics from constructed cases and analytic mocks, not fly motion."""
import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import lf_activation_endpoint as endpoint


def test_exact_boundaries_select_authoritative_state_and_near_time_stays_dense():
    case = endpoint.constructed_case(); adapted = case['adapted']
    assert adapted['samples'][0] == [2., -3., .5, 1.]
    assert adapted['samples'][-1] == [7., -11., 13., -17.]
    assert adapted['samples'][1:3] == [[20., 30., 40., 50.], [60., 70., 80., 90.]]
    assert adapted['interpolated_samples'] == case['original']['samples']
    assert adapted['sample_kinds'] == ['INITIAL_STATE', 'DENSE_INTERPOLANT', 'DENSE_INTERPOLANT', 'SOLVER_TERMINAL_STATE']
    assert case['offsets'][-2] < case['duration'] and np.nextafter(case['offsets'][-2], np.inf) == case['duration']
    assert adapted['after'] == case['original']['after'] and adapted['solver'] == case['original']['solver']
    assert case['input_unchanged']


def test_selection_deep_copies_without_mutating_raw_result():
    case = endpoint.constructed_case()
    raw = copy.deepcopy(case['original']); original = copy.deepcopy(raw)
    out = endpoint.select_samples(raw, case['initial'], case['duration'], case['offsets'])
    out['after'][0] = 999.; out['solver']['activations'][0][0] = 888.
    out['samples'][1][0] = 777.; out['interpolated_samples'][0][0] = 666.
    assert raw == original


@pytest.mark.parametrize('defect', ['after', 'initial', 'status', 'success', 'terminal_time', 'dense_nan', 'shape', 'offsets'])
def test_malformed_authority_or_dense_data_is_rejected(defect):
    case = endpoint.constructed_case(); raw = copy.deepcopy(case['original'])
    if defect == 'after': raw['after'][0] += 1
    if defect == 'initial': raw['solver']['activations'][0][0] += 1
    if defect == 'status': raw['solver']['status'] = 1
    if defect == 'success': raw['solver']['success'] = False
    if defect == 'terminal_time': raw['solver']['times'][-1] = .2
    if defect == 'dense_nan': raw['samples'][0][0] = float('nan')
    if defect == 'shape': raw['samples'][0].pop()
    if defect == 'offsets': raw['sample_offsets'][1] = .1
    with pytest.raises(ValueError): endpoint.select_samples(raw, case['initial'], case['duration'], case['offsets'])


def test_wrapper_delegates_once_with_unchanged_inputs_and_retains_raw_samples(monkeypatch):
    case = endpoint.constructed_case(); calls = []
    native = object(); control = np.arange(4.); params = np.zeros((4, 10))
    def solver(*args): calls.append(args); return case['original']
    monkeypatch.setattr(endpoint.prior, 'integrate_interval', solver)
    actual = endpoint.integrate_interval(native, case['initial'], control, params, case['duration'], case['offsets'])
    assert len(calls) == 1 and calls[0][0] is native and calls[0][2] is control and calls[0][3] is params
    assert calls[0][1] is case['initial'] and calls[0][4:] == (case['duration'], case['offsets'])
    assert actual['interpolated_samples'] == case['original']['samples']


@pytest.mark.parametrize('duration', endpoint.DURATIONS)
def test_actual_radau_linear_mock_matches_analytic_solution_with_exact_endpoint_role(duration):
    # Actual SciPy solving, but a mock linear derivative, not native muscle/CNS.
    native = SimpleNamespace(mju_muscleDynamics=lambda c, a, p: (c-a)/p[0])
    params = np.zeros((4, 10)); params[:, 0] = endpoint.TAU
    offsets = [0., duration/2, float(np.nextafter(duration, 0.)), duration]
    raw = endpoint.prior.integrate_interval(native, endpoint.INITIAL, endpoint.CONTROL, params, duration, offsets)
    original = copy.deepcopy(raw)
    result = endpoint.select_samples(raw, endpoint.INITIAL, duration, offsets)
    exact = endpoint.CONTROL+(endpoint.INITIAL-endpoint.CONTROL)*np.exp(-np.asarray(offsets)[:, None]/endpoint.TAU)
    assert np.max(np.abs(np.asarray(result['samples'])-exact)) <= 1e-8
    assert result['samples'][-1] == raw['after'] == result['solver']['activations'][-1]
    assert result['samples'][2] == raw['samples'][2] and raw == original


def test_preflight_does_not_read_old_trajectories_as_check_inputs_or_solve(monkeypatch):
    def forbidden(*a, **k): raise AssertionError('preflight cannot integrate')
    monkeypatch.setattr(endpoint.prior, 'solve_ivp', forbidden)
    ready = endpoint.preflight()
    assert ready['historical_classification'] == 'INTEGRITY_FAILURE'
    assert ready['historical_record_sha256'] == endpoint.OLD_SHA


def test_failure_output_is_exclusive(tmp_path, monkeypatch):
    def failed(): raise ValueError('injected lock failure')
    monkeypatch.setattr(endpoint, 'preflight', failed)
    output = tmp_path/'fresh'
    assert endpoint.main(['--execute', '--output-dir', str(output)]) == 1
    original = (output/'contract.json').read_bytes()
    with pytest.raises(FileExistsError): endpoint.main(['--execute', '--output-dir', str(output)])
    assert (output/'contract.json').read_bytes() == original


def saved(): return json.loads((endpoint.ROOT/(endpoint.DIRECTORY+'run/contract.json')).read_text(encoding='utf-8'))


def test_saved_review_runs_no_solver_native_or_cns(monkeypatch):
    import mujoco
    import flygym
    from malecns_backend import neural
    def forbidden(*a, **k): raise AssertionError('saved API review must be static')
    monkeypatch.setattr(endpoint.prior, 'solve_ivp', forbidden)
    monkeypatch.setattr(flygym, 'Fly', forbidden); monkeypatch.setattr(neural, 'MaleCNSBrain', forbidden)
    for name in ('MjModel', 'MjData', 'mj_forward', 'mj_step', 'mju_muscleDynamics'):
        monkeypatch.setattr(mujoco, name, forbidden)
    assert endpoint.main(['--report', str(endpoint.ROOT/(endpoint.DIRECTORY+'run/contract.json'))]) == 0


@pytest.mark.parametrize('defect', ['endpoint', 'role', 'dense', 'calls', 'historical', 'native'])
def test_saved_contract_corruption_rejected(defect):
    report = saved()
    row = report['analytic'][0]
    if defect == 'endpoint': row['result']['samples'][-1][0] += .1
    if defect == 'role': row['result']['sample_kinds'][-2] = 'SOLVER_TERMINAL_STATE'
    if defect == 'dense': report['constructed']['adapted']['interpolated_samples'][-1][0] += 1.
    if defect == 'calls': row['solver_calls'] = 2
    if defect == 'historical': report['ready']['historical_classification'] = 'PASS'
    if defect == 'native': report['native_body_steps'] = 1
    assert not endpoint.evaluate(report, endpoint.preflight())['passed']
