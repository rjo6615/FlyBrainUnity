"""Static identity/unsafe-plan checks; no simulated intervention in this file."""
import copy
import json

import pytest

from malecns_backend.embodiment import lf_actuation_contract as audit


@pytest.fixture(scope='module')
def inputs():
    read = lambda p: json.loads((audit.ROOT/p).read_text(encoding='utf-8'))
    return (read(audit.M5A)['actuator_records'],
            read(audit.SIGNATURE)['candidates']['joint_LFTarsus1']['initialization']['ENABLED']['physics_model_identity']['components'],
            audit.force.static.load()['static_admission_table'])


def test_exact_partition_keeps_all_admissions_and_separates_address_spaces(inputs):
    result = audit.project_inventory(*inputs)
    assert result['target_basis'] == ['joint_LFCoxa_yaw', 'joint_LFCoxa', 'joint_LFCoxa_roll']
    assert [r['action_index'] for r in result['targets']] == [2, 0, 1]
    assert [r['compiled']['actuator_id'] for r in result['targets']] == [2, 0, 1]
    assert [r['compiled']['joint_id'] for r in result['targets']] == [1, 2, 3]
    assert [r['compiled']['dof_range'] for r in result['targets']] == [[6, 7], [7, 8], [8, 9]]
    assert [r['compiled']['qpos_range'] for r in result['targets']] == [[7, 8], [8, 9], [9, 10]]
    assert len(result['retained_joint_controls']) == 39
    assert result['retained_admitted_count'] == 20 and result['retained_baseline_count'] == 19
    assert all(r['body_id'] is None and r['activation_address'] is None for r in result['targets'])
    other = result['separate_signature']
    assert len(other['adhesion']) == 6 and other['adhesion'][0]['recorded_name_id'] == 42
    assert not other['equivalent_to_m5a_model'] and not other['current_native_capture']
    assert not other['values_available'] and other['dimensions']['na'] == 0
    assert all(r['transmission_values'] is None for r in other['adhesion'])


@pytest.mark.parametrize('defect', ['order', 'alias', 'transmission', 'joint_type', 'dof', 'duplicate_id', 'admitted_target', 'adhesion'])
def test_recorded_identity_conflicts_rejected(inputs, defect):
    rows, signature, admissions = copy.deepcopy(inputs)
    if defect == 'order': rows[0], rows[1] = rows[1], rows[0]
    if defect == 'alias': rows[0]['mujoco_metadata']['joint_name'] += '_similar'
    if defect == 'transmission': rows[0]['mujoco_metadata']['actuator_transmission_type'] = 3
    if defect == 'joint_type': rows[0]['mujoco_metadata']['joint_type'] = 0
    if defect == 'dof': rows[0]['mujoco_metadata']['dof_range'][1] += 1
    if defect == 'duplicate_id': rows[0]['mujoco_metadata']['actuator_id'] = rows[1]['mujoco_metadata']['actuator_id']
    if defect == 'admitted_target':
        admissions[0]['neural_motor_admission'] = True
        other = next(r for r in admissions if r['neural_motor_admission'] and r['action_index'] != 0)
        other['neural_motor_admission'] = False
    if defect == 'adhesion': signature['inventories']['actuator'].pop()
    with pytest.raises(ValueError): audit.project_inventory(rows, signature, admissions)


@pytest.mark.parametrize('field,value', [
    ('target_m5a_actuator_ids', [2, 0, 1, 5]),
    ('patch_fields', ['actuator_gainprm']),
    ('preserved_action_indices', []),
    ('remove_actuators', True),
    ('global_actuation_disable', True),
    ('control_zero_only', True),
    ('activation_owner', 'NATIVE_AND_EXTERNAL'),
    ('native_muscle_states_added', 4),
    ('external_body_time_writes', 1),
    ('native_body_intervals_per_transition', 2),
    ('force_buffer_policy', 'CLEAR_ALL_QFRC_AND_XFRC'),
    ('production_enabled', True),
    ('coupling_ready', True),
])
def test_unsafe_replacement_or_duplicate_ownership_rejected(inputs, field, value):
    inventory = audit.project_inventory(*inputs)
    plan = audit.proposed_plan(inventory)
    plan[field] = value
    with pytest.raises(ValueError): audit.validate_plan(plan, inventory)


def forbid_execution(monkeypatch):
    import mujoco
    import flygym
    from malecns_backend import neural
    from malecns_backend.embodiment import full_leg_interface as full
    from malecns_backend.embodiment import _windows_m7_spontaneous_locomotion_adapter as old
    from malecns_backend.embodiment import _windows_m8_live_condition as runtime
    def forbidden(*a, **k): raise AssertionError('static audit cannot execute physics, CNS or integration')
    for key in ('MjModel', 'mj_forward', 'mj_step', 'mju_muscleDynamics'):
        monkeypatch.setattr(mujoco, key, forbidden)
    monkeypatch.setattr(flygym, 'Fly', forbidden)
    monkeypatch.setattr(flygym, 'SingleFlySimulation', forbidden)
    monkeypatch.setattr(full, 'enumerate_live_actuators', forbidden)
    monkeypatch.setattr(old, 'enumerate_live_actuators', forbidden)
    monkeypatch.setattr(neural, 'MaleCNSBrain', forbidden)
    monkeypatch.setattr(runtime, '_scientific_transition_kernel', forbidden)
    monkeypatch.setattr(audit.activation.integrator, 'solve_ivp', forbidden)
    monkeypatch.setattr(audit.activation.prior, 'solve_ivp', forbidden)


def test_build_has_no_native_solver_or_cns_execution(monkeypatch):
    forbid_execution(monkeypatch)
    result = audit.build()
    assert result['classification'] == 'STATIC_CONTRACT_VERIFIED_COUPLING_BLOCKED'
    assert not result['coupling_ready'] and len(result['blockers']) == 6
    assert all(v == 0 for v in result['execution'].values())
    assert result['current_motor_count'] == 20 and result['new_admissions'] == 0
    states = result['source_activation_states']
    assert [r['source_fixture_activation_address'] for r in states] == [0, 1, 2, 3]
    assert all(r['flygym_activation_address'] is None and r['individual_neuron_assignment'] is None for r in states)
    assert result['source_hashes_before'] == result['source_hashes_after']


def test_failed_static_output_is_preserved_exclusively(tmp_path, monkeypatch):
    def fail(): raise ValueError('injected source conflict')
    monkeypatch.setattr(audit, 'build', fail)
    output = tmp_path/'fresh'
    assert audit.main(['--build', '--output-dir', str(output)]) == 1
    before = (output/'audit.json').read_bytes()
    assert json.loads(before)['classification'] == 'STATIC_AUDIT_FAILED'
    with pytest.raises(FileExistsError): audit.main(['--build', '--output-dir', str(output)])
    assert (output/'audit.json').read_bytes() == before


def test_saved_review_stays_static_and_preserves_blockers(monkeypatch):
    forbid_execution(monkeypatch)
    assert audit.main(['--report', str(audit.ROOT/(audit.DIRECTORY+'audit.json'))]) == 0


def test_saved_readiness_or_foreign_force_policy_tampering_rejected(tmp_path):
    saved = json.loads((audit.ROOT/(audit.DIRECTORY+'audit.json')).read_text(encoding='utf-8'))
    saved['coupling_ready'] = True
    path = tmp_path/'tampered.json'
    path.write_text(json.dumps(saved), encoding='utf-8')
    with pytest.raises(ValueError, match='saved static contract'): audit.main(['--report', str(path)])
