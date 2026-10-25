"""Real isolated MuJoCo implementation tests; no neural or whole-fly experiments."""
import copy
import json

import numpy as np
import pytest

from malecns_backend.embodiment import lf_force_reference as force
from malecns_backend.embodiment import lf_force_reference_validation as validation


@pytest.fixture(scope='module')
def reference():
    return force.load_reference()


@pytest.fixture
def native(reference):
    import mujoco
    model = mujoco.MjModel.from_xml_path(str(force.ROOT/force.FIXTURE))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    adapter = force.ReferenceForceAdapter(model, data, reference)
    return mujoco, model, data, adapter


def test_four_class_hypotheses_keep_exact_neurons_and_no_promotor(reference):
    assert reference['tendons'] == list(force.TENDONS)
    assert [p['identity']['count'] for p in reference['hypotheses']] == [2, 1, 2, 4]
    assert len(reference['hypotheses'][0]['identity']['exact_annotation_aliases']) == 2
    assert all(not p['admission_ready'] and p['decoder_vector'] is None and p['gain'] is None
               and all(n['tendon'] is None for n in p['per_neuron_tendon_assignments']) for p in reference['hypotheses'])


def test_native_addresses_force_equation_and_clear(native, reference):
    mujoco, model, data, adapter = native
    assert adapter.dofs == [7, 8, 9]
    assert adapter.jids == [2, 3, 4]
    assert [r['qpos_address_range'][0] for r in adapter.metadata] == [8, 9, 10]
    tensions = np.array([.25, .5, .75, 1.])
    expected = np.linalg.inv(np.asarray(reference['J'])).T @ (np.asarray(reference['R_M']) @ tensions)
    q0 = data.qpos.copy()
    assert np.allclose(adapter.apply(tensions), expected, rtol=0, atol=1e-12)
    mujoco.mj_forward(model, data)
    assert np.array_equal(data.qfrc_applied[:7], np.zeros(7))
    mass = np.empty((10, 10))
    mujoco.mj_fullM(model, mass, data.qM)
    assert np.max(np.abs(mass @ data.qacc-data.qfrc_applied)) < 1e-10
    assert np.array_equal(data.qpos, q0) and data.time == 0
    adapter.clear()
    mujoco.mj_forward(model, data)
    assert np.count_nonzero(data.qfrc_applied) == 0 and np.max(np.abs(data.qacc)) < 1e-10


@pytest.mark.parametrize('tensions', [[], [1, 0, 0], [[0, 0, 0, 0]], [-1, 0, 0, 0],
                                      [float('nan'), 0, 0, 0], [0, float('inf'), 0, 0]])
def test_invalid_tensions_do_not_mutate_force(native, tensions):
    _, _, data, adapter = native
    before = data.qfrc_applied.copy()
    with pytest.raises(ValueError): adapter.apply(tensions)
    assert np.array_equal(data.qfrc_applied, before)


@pytest.mark.parametrize('defect', ['pose', 'velocity', 'time', 'generalized_force', 'body_force', 'axis', 'gravity', 'damping'])
def test_out_of_scope_state_or_foreign_force_fails_before_mutation(native, defect):
    _, model, data, adapter = native
    if defect == 'pose': data.qpos[8] = .0001
    if defect == 'velocity': data.qvel[7] = .0001
    if defect == 'time': data.time = .0001
    if defect == 'generalized_force': data.qfrc_applied[6] = 1.
    if defect == 'body_force': data.xfrc_applied[1, 0] = 1.
    if defect == 'axis': model.jnt_axis[adapter.jids[0]] = [0, 1, 0]
    if defect == 'gravity': model.opt.gravity[2] = -1.
    if defect == 'damping': model.dof_damping[7] = .1
    before = data.qfrc_applied.copy()
    with pytest.raises(ValueError): adapter.apply([1, 0, 0, 0])
    assert np.array_equal(data.qfrc_applied, before)


def test_force_ownership_prevents_accumulation_and_unsafe_clear(native):
    _, _, data, adapter = native
    adapter.apply([1, 0, 0, 0])
    before = data.qfrc_applied.copy()
    with pytest.raises(ValueError): adapter.apply([1, 0, 0, 0])
    assert np.array_equal(data.qfrc_applied, before)
    data.qfrc_applied[6] = 1.
    before = data.qfrc_applied.copy()
    with pytest.raises(ValueError): adapter.clear()
    assert np.array_equal(data.qfrc_applied, before)
    data.qfrc_applied[6] = 0.
    adapter.clear()
    with pytest.raises(ValueError): adapter.clear()


def test_position_or_other_actuator_cannot_be_combined(reference):
    import mujoco
    xml = (force.ROOT/force.FIXTURE).read_text()
    xml = xml.replace('</mujoco>', '<actuator><position joint="unselected_hinge" kp="1"/></actuator></mujoco>')
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    with pytest.raises(ValueError): force.ReferenceForceAdapter(model, data, reference)
    assert np.count_nonzero(data.qfrc_applied) == 0


def test_reference_order_is_not_a_decoder_mapping(native, reference):
    _, model, data, _ = native
    altered = copy.deepcopy(reference)
    altered['tendons'].reverse()
    with pytest.raises(ValueError): force.ReferenceForceAdapter(model, data, altered)


def test_failed_output_and_existing_namespace_are_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(validation, 'preflight', lambda: {})
    def fail(ready): raise RuntimeError('missing immutable reference')
    monkeypatch.setattr(validation, 'execute', fail)
    output = tmp_path/'attempt'
    args = ['--execute', '--output-dir', str(output)]
    assert validation.main(args) == 1
    raw = (output/'validation.json').read_bytes()
    assert json.loads(raw)['status'] == 'INTEGRITY_ERROR'
    with pytest.raises(FileExistsError): validation.main(args)
    assert (output/'validation.json').read_bytes() == raw


def test_saved_native_campaign_rechecks_without_forward_dynamics(monkeypatch):
    import mujoco
    def forbidden(*a, **k): raise AssertionError('saved review must not rerun native dynamics')
    monkeypatch.setattr(mujoco, 'mj_forward', forbidden)
    saved, _ = validation.verify(force.ROOT/'docs/evidence/lf-force-reference-v1/validation.json')
    assert saved['evaluation']['passed']
    assert saved['native_forward_calls'] == 18 and saved['integration_steps'] == saved['neural_transitions'] == 0


@pytest.mark.parametrize('defect', ['force', 'axis_order', 'state', 'clear', 'mass', 'missing_case'])
def test_saved_record_tampering_fails(defect, reference):
    raw = json.loads((force.ROOT/'docs/evidence/lf-force-reference-v1/validation.json').read_text(encoding='utf-8'))
    applied = raw['cases'][1]['snapshots']['applied']
    if defect == 'force': applied['qfrc_applied'][6] = .01
    if defect == 'axis_order': raw['cases'][1]['metadata'].reverse()
    if defect == 'state': applied['qpos'][8] = .001
    if defect == 'clear': raw['cases'][1]['snapshots']['cleared']['qfrc_applied'][7] = .01
    if defect == 'mass': applied['mass_matrix'][0][0] = float('nan')
    if defect == 'missing_case': raw['cases'].pop()
    assert not validation.evaluate(raw, reference)['passed']
