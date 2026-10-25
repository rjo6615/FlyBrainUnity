"""V2 endpoint consumption and inherited native mechanics, not fly behavior."""
import json

import numpy as np
import pytest

from malecns_backend.embodiment import lf_synthetic_coupling_v2 as assay


@pytest.fixture(scope='module')
def ready():
    return dict(reference=assay.v1.force.load_reference(),
                binding=json.loads((assay.ROOT/assay.v1.schedule.BINDING).read_text(encoding='utf-8')))


@pytest.fixture
def native_fixture(ready):
    import mujoco as native
    model = native.MjModel.from_xml_path(str(assay.ROOT/assay.v1.FIXTURE))
    data = native.MjData(model)
    data.qfrc_applied[:] = assay.v1.FOREIGN
    data.xfrc_applied[:] = assay.v1.foreign_body()
    adapter = assay.EndpointSplitAdapter(native, model, data, ready, np.full(4, .5))
    return native, model, data, adapter


def test_native_step_consumes_endpoint_contract_once_and_preserves_foreign_forces(native_fixture, monkeypatch):
    native, model, data, adapter = native_fixture
    calls = []
    original = assay.endpoint.integrate_interval
    def counted(*args): calls.append(args); return original(*args)
    monkeypatch.setattr(assay.endpoint, 'integrate_interval', counted)
    before = adapter.activation
    torque = assay.v1.projected_torque(adapter.ready, before)
    row = adapter.advance('RELAX_ZERO')
    assert len(calls) == 1 and calls[0][0] is native
    assert data.time == model.opt.timestep and adapter.transitions == 1
    assert row['torque'] == torque.tolist()
    assert row['endpoint_contract'] == assay.endpoint.SCHEMA
    assert row['solver']['sample_kinds'] == ['SOLVER_TERMINAL_STATE']
    assert row['solver']['samples'] == [row['activation_after']]
    assert row['activation_after'] == row['solver']['after'] == row['solver']['solver']['activations'][-1]
    assert row['interpolated_samples_sha256'] == assay.dense_hash(row['solver']['interpolated_samples'])
    assert np.array_equal(data.qfrc_applied, assay.v1.FOREIGN)
    assert np.array_equal(data.xfrc_applied, assay.v1.foreign_body())


@pytest.mark.parametrize('after_native', [False, True])
def test_inherited_failure_contract_retains_uncertain_body_state(native_fixture, monkeypatch, after_native):
    native, model, data, adapter = native_fixture
    original = native.mj_step
    def failed(*args):
        if after_native: original(*args)
        raise RuntimeError('injected native failure')
    monkeypatch.setattr(native, 'mj_step', failed)
    before = adapter.activation
    with pytest.raises(RuntimeError): adapter.advance('RELAX_ZERO')
    assert adapter.failed and adapter.transitions == 0 and np.array_equal(adapter.activation, before)
    assert data.time == (model.opt.timestep if after_native else 0.)
    assert np.array_equal(data.qfrc_applied, assay.v1.FOREIGN)
    assert np.array_equal(data.xfrc_applied, assay.v1.foreign_body())
    with pytest.raises(ValueError): adapter.advance('RELAX_ZERO')


def test_duplicate_owner_and_foreign_target_force_are_rejected(native_fixture):
    _, _, data, adapter = native_fixture
    adapter.apply(np.ones(3))
    with pytest.raises(ValueError): adapter.apply(np.ones(3))
    adapter.clear(); data.qfrc_applied[1] = .1
    with pytest.raises(ValueError): adapter.advance('PULSE')
    assert data.time == 0 and adapter.transitions == 0


def forbid_computation(monkeypatch):
    import mujoco
    import flygym
    from malecns_backend import neural
    def forbidden(*a, **k): raise AssertionError('saved V2 review/preflight must be static')
    for key in ('MjModel', 'MjData', 'mj_forward', 'mj_step', 'mju_muscleDynamics'):
        monkeypatch.setattr(mujoco, key, forbidden)
    monkeypatch.setattr(flygym, 'Fly', forbidden); monkeypatch.setattr(neural, 'MaleCNSBrain', forbidden)
    monkeypatch.setattr(assay.v1, 'solve_ivp', forbidden)
    monkeypatch.setattr(assay.endpoint.prior, 'solve_ivp', forbidden)
    monkeypatch.setattr(assay.v1.schedule, 'solve_ivp', forbidden)


def test_preflight_verifies_endpoint_and_preserves_failed_v1_without_native_work(monkeypatch):
    forbid_computation(monkeypatch)
    ready = assay.preflight()
    assert ready['endpoint_prerequisite']['historical_v1_classification'] == 'INTEGRITY_FAILURE'
    assert ready['endpoint_prerequisite']['canonical_sha256'] == assay.CONTRACT_SHA


def test_failed_output_remains_exclusive(tmp_path, monkeypatch):
    monkeypatch.setattr(assay, 'preflight', lambda: {})
    def failed(*a): raise ValueError('injected source failure')
    monkeypatch.setattr(assay, 'execute', failed)
    out = tmp_path/'fresh'
    assert assay.main(['--execute', '--output-dir', str(out)]) == 1
    raw = (out/'validation.json').read_bytes()
    with pytest.raises(FileExistsError): assay.main(['--execute', '--output-dir', str(out)])
    assert (out/'validation.json').read_bytes() == raw


def saved(): return assay.v1.upstream.load_report(assay.ROOT/(assay.DIRECTORY+'run/validation.json'))


def test_saved_review_executes_no_solver_native_or_cns(monkeypatch):
    forbid_computation(monkeypatch)
    assert assay.main(['--report', str(assay.ROOT/(assay.DIRECTORY+'run/validation.json'))]) == 0


def test_saved_mechanical_checks_are_reused_without_changing_v1_acceptance():
    report = saved()
    actual = assay.evaluate(report, report['ready'])
    old_checks = assay.v1.evaluate(report, report['ready'])
    assert not old_checks['checks']['schema']  # V2 must never claim to be V1.
    for key, value in old_checks['checks'].items():
        if key != 'schema': assert actual['checks'][key] == value
    assert actual['cases'] == old_checks['cases'] and actual['refinement'] == old_checks['refinement']
    assert actual['integrity_passed'] and len(actual['dense_diagnostics']) == 9
    assert report['ready']['endpoint_prerequisite']['historical_v1_classification'] == 'INTEGRITY_FAILURE'
    for case in report['cases']:
        for row in case['steps']:
            assert row['solver']['samples'] == [row['solver']['after']]
            assert np.asarray(row['solver']['interpolated_samples']).shape == (1, 4)


@pytest.mark.parametrize('defect', ['schema', 'role', 'raw_dense', 'raw_hash', 'source', 'state', 'foreign', 'counter'])
def test_saved_corruption_changes_evaluation(defect):
    report = saved(); row = report['cases'][0]['steps'][0]
    if defect == 'schema': report['schema'] = assay.v1.SCHEMA
    if defect == 'role': row['solver']['sample_kinds'] = ['DENSE_INTERPOLANT']
    if defect == 'raw_dense': row['solver']['interpolated_samples'][0][0] += 1.
    if defect == 'raw_hash': row['interpolated_samples_sha256'] = '0'*64
    if defect == 'source': row['solver']['endpoint_state_source'] = 'DENSE_INTERPOLANT'
    if defect == 'state': row['after_clear']['qpos'][0] += .1
    if defect == 'foreign': row['after_clear']['body'][1][5] = 0.
    if defect == 'counter': report['api_calls']['mj_step'] += 1
    actual = assay.evaluate(report, report['ready'])
    assert not actual['integrity_passed'] and actual != report['evaluation']
