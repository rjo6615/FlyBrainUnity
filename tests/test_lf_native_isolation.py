"""Forward-only native assay boundaries and saved evidence checks."""
import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import lf_native_isolation as audit


@pytest.fixture
def small_inventory():
    # Synthetic addresses exercise input scheduling only, not physical identity.
    names = list(audit.contract.force.audit.JOINT_NAMES)
    rows = [dict(coordinate=n, action_index=i, actuator_id=i, qpos_range=[i+7, i+8],
                 dof_range=[i+6, i+7]) for i, n in enumerate(names)]
    return dict(rows=rows, nv=48, joints=dict(dofadr=list(range(43))))


@pytest.mark.parametrize('probe', audit.PROBES)
def test_fixed_probe_inputs_and_comparison_controls(small_inventory, probe):
    center = np.arange(49)*.001
    q, v, ctrl = audit.probe_inputs(small_inventory, center, probe, 'BASELINE')
    nq, nv, neutral = audit.probe_inputs(small_inventory, center, probe, 'NEUTRALIZED')
    zq, zv, zero = audit.probe_inputs(small_inventory, center, probe, 'CTRL_ZERO_ONLY')
    assert np.array_equal(q, nq) and np.array_equal(q, zq)
    assert np.array_equal(v, nv) and np.array_equal(v, zv)
    assert np.array_equal(ctrl, neutral) and np.array_equal(ctrl[3:], zero[3:])
    assert not np.any(zero[:3]) and not np.any(ctrl[42:])
    assert np.array_equal(center, np.arange(49)*.001)
    if probe == 'CENTER': assert np.array_equal(q, center) and not np.any(v)
    if probe.startswith('VELOCITY'):
        sign = 1 if probe.endswith('PLUS') else -1
        assert np.array_equal(q, center)
        assert v[[8, 6, 7]].tolist() == [sign*.1, -sign*.1, sign*.1]
    if probe.startswith(('YAW', 'PITCH', 'ROLL')):
        index = {'YAW': 9, 'PITCH': 7, 'ROLL': 8}[probe.split('_')[0]]
        assert np.flatnonzero(q-center).tolist() == [index]
        assert abs(q[index]-center[index]-(.05 if probe.endswith('PLUS') else -.05)) < 1e-15


def test_native_api_accounting_blocks_integration_and_restores_functions():
    called = []
    def forwarded(*args): called.append('forward')
    native = SimpleNamespace(mj_forward=forwarded, mj_resetData=lambda *a: None,
                             **{k: lambda *a: None for k in audit.INTEGRATORS})
    originals = {k: getattr(native, k) for k in ('mj_forward', 'mj_resetData', *audit.INTEGRATORS)}
    with audit.native_accounting(native) as (counts, phase):
        native.mj_forward(None, None)
        native.mj_resetData(None, None)
        phase[0] = 'probes'
        with pytest.raises(ValueError, match='integration prohibited'): native.mj_step(None, None)
    assert called == ['forward']
    assert counts['initialization']['mj_forward'] == counts['initialization']['mj_resetData'] == 1
    assert counts['probes']['mj_step'] == 1
    assert all(getattr(native, k) is v for k, v in originals.items())


def forbid_execution(monkeypatch):
    import mujoco
    import flygym
    from malecns_backend import neural
    def forbidden(*a, **k): raise AssertionError('saved review/preflight cannot execute physics or CNS')
    for key in ('MjModel', 'MjData', 'mj_forward', 'mj_resetData', *audit.INTEGRATORS):
        monkeypatch.setattr(mujoco, key, forbidden)
    monkeypatch.setattr(flygym, 'Fly', forbidden)
    monkeypatch.setattr(flygym, 'SingleFlySimulation', forbidden)
    monkeypatch.setattr(neural, 'MaleCNSBrain', forbidden)
    monkeypatch.setattr(audit.contract.activation.integrator, 'solve_ivp', forbidden)
    monkeypatch.setattr(audit.contract.activation.prior, 'solve_ivp', forbidden)


def test_preflight_locks_inputs_without_native_work(monkeypatch):
    forbid_execution(monkeypatch)
    ready = audit.preflight()
    assert ready['installed_inputs']['versions']['mujoco'] == '3.2.7'
    assert len(ready['installed_inputs']['files']) == 196


def test_failure_output_is_exclusive_and_retained(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'preflight', lambda: {})
    def failed(*a): raise ValueError('injected initializer failure')
    monkeypatch.setattr(audit, 'execute', failed)
    output = tmp_path/'fresh'
    assert audit.main(['--execute', '--output-dir', str(output)]) == 1
    original = (output/'validation.json').read_bytes()
    assert 'injected initializer failure' in original.decode()
    with pytest.raises(FileExistsError): audit.main(['--execute', '--output-dir', str(output)])
    assert (output/'validation.json').read_bytes() == original


def saved():
    return audit.load_report(audit.ROOT/(audit.DIRECTORY+'run/validation.json'))


def test_lossless_nonfinite_metadata_does_not_change_values_or_array_identity():
    original = dict(limits=[-float('inf'), float('inf'), float('nan')], ordinary=[0., .125, -3.5])
    text = json.dumps(audit.encode_nonfinite(original), allow_nan=False)
    assert 'native_nonfinite' in text and 'Infinity' not in text
    restored = json.loads(text, object_hook=audit.decode_nonfinite)
    assert np.isneginf(restored['limits'][0]) and np.isposinf(restored['limits'][1]) and np.isnan(restored['limits'][2])
    assert restored['ordinary'] == original['ordinary']
    assert audit._canonical_array_identity(restored['limits']) == audit._canonical_array_identity(original['limits'])


def test_saved_review_has_no_native_work(monkeypatch):
    forbid_execution(monkeypatch)
    assert audit.main(['--report', str(audit.ROOT/(audit.DIRECTORY+'run/validation.json'))]) == 0


def test_saved_force_suppression_is_nonvacuous_and_current_addresses_are_resolved():
    r = saved()
    assert audit.evaluate(r, r['ready'])['passed']
    assert len(r['inventory']['rows']) == 42 and len(r['inventory']['adhesion']) == 6
    for row in audit.targets(r['inventory']):
        assert type(row['body_id']) is int and row['body_name']
        assert row['activation_address'] == -1 and row['activation_count'] == 0
    for result in r['evaluation']['comparisons']:
        assert result['maximum_selected_force'] <= 1e-10
        assert result['maximum_retained_force_difference'] <= 1e-10
    assert r['evaluation']['checks']['nonvacuous_baseline']
    assert r['evaluation']['checks']['control_zero_comparison_informative']


@pytest.mark.parametrize('defect', ['drop', 'time', 'force', 'retained_gain', 'sparse', 'body_id', 'sensor', 'counter'])
def test_saved_corruption_is_rejected(defect):
    r = saved()
    if defect == 'drop': r['cases'].pop()
    if defect == 'time': r['cases'][0]['after']['time'] = .001
    if defect == 'force': r['cases'][-1]['outputs']['actuator_force'][0] = 1.
    if defect == 'retained_gain': r['neutralized_parameters']['gainprm'][5][0] += 1.
    if defect == 'sparse': r['cases'][0]['sparse_moments']['values'][0] += 1.
    if defect == 'body_id': r['inventory']['rows'][0]['body_id'] += 1
    if defect == 'sensor': r['inventory']['sensors']['objid'][0] += 1
    if defect == 'counter': r['api_calls']['probes']['mj_step'] = 1
    assert not audit.evaluate(r, r['ready'])['passed']
