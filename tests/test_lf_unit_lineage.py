"""Static extraction/lineage tests; not new physics or biological validation."""
import copy
import json
from unittest.mock import patch

import pytest

from malecns_backend.embodiment import lf_unit_lineage as audit


@pytest.fixture
def snapshot():
    return audit.transfer.read(audit.SNAPSHOT)


def test_different_peak_changes_and_matching_activation_constants_stay_distinct(snapshot):
    result = audit.analyse(snapshot)
    assert [r['numeric_peak_ratio_not_unit_conversion'] for r in result['comparisons']] == pytest.approx(
        [1.7885541159854257, 1.4207090400820321, .21081114447510585, 1.603709663686259])
    assert all(r['activation_constants_numerically_equal'] for r in result['comparisons'])
    assert all(r['full_model_parameters_equal'] for r in result['comparisons'])
    assert not result['numeric_peak_ratios_all_identical']
    assert not result['original_OpenSim_input_to_locked_XML_proven']


def test_even_equal_force_ratios_and_unit_labels_cannot_calibrate_transfer(snapshot):
    for row, source in zip(snapshot['files']['opensim']['extract']['selected'],
                           snapshot['files']['source_mjcf']['extract']['binding']['bindings']):
        row['parameters']['max_isometric_force'] = float(source['actuator_attributes']['gainprm'].split()[2])
    result = audit.analyse(snapshot)
    assert result['numeric_peak_ratios_all_identical']
    assert result['unit_ledger']['opensim_declared_length'] == 'm'
    assert result['unit_ledger']['physical_force_conversion'] is None
    assert result['unit_ledger']['physical_torque_conversion'] is None
    assert not result['production_transfer_enabled']


def test_pdf_name_and_added_log_are_not_hash_linked_validation(snapshot):
    snapshot['repository']['tracked_paths'].append('best_combined_conversion.log')
    result = audit.analyse(snapshot)
    assert result['tracked_conversion_records']['conversion_log'] == ['best_combined_conversion.log']
    assert not result['conversion_pdf']['exact_locked_xml_hash_link']
    assert not result['conversion_pdf']['establishes_locked_xml_validation']
    assert result['converter_revision'] is None


@pytest.mark.parametrize('kind', ['drop', 'duplicate', 'wrong_class'])
def test_ambiguous_or_wrong_opensim_identity_rejected(kind):
    nodes = ['<Millard2012EquilibriumMuscle name="'+name+'">'+''.join(
        '<'+f+'>1</'+f+'>' for f in audit.MUSCLE_FIELDS)+'</Millard2012EquilibriumMuscle>' for name in audit.NAMES]
    if kind == 'drop': nodes.pop()
    if kind == 'duplicate': nodes.append(nodes[0])
    if kind == 'wrong_class': nodes[0] = nodes[0].replace('Millard2012EquilibriumMuscle', 'OtherMuscle')
    raw = ('<OpenSimDocument><Model><ForceSet><objects>'+''.join(nodes)+
           '</objects></ForceSet></Model></OpenSimDocument>').encode()
    with pytest.raises(ValueError, match='unique exact Millard'):
        audit.extract_osim(raw)


def test_external_raw_change_rejected_before_xml_interpretation(snapshot, tmp_path):
    first = snapshot['files']['opensim']
    path = tmp_path/first['path']; path.parent.mkdir(parents=True); path.write_text('<different/>')
    with pytest.raises(ValueError, match='raw identity mismatch'):
        audit.inspect_external(tmp_path, snapshot)


@pytest.fixture(scope='module')
def rebuilt():
    import mujoco
    import scipy.integrate
    from malecns_backend.embodiment import remaining_leg_admission_audit as legacy
    def forbidden(*args, **kwargs): raise AssertionError('native/solver/live audit attempted')
    with patch.object(mujoco, 'MjModel', forbidden), patch.object(mujoco, 'MjData', forbidden), \
         patch.object(mujoco, 'mj_forward', forbidden), patch.object(mujoco, 'mj_step', forbidden), \
         patch.object(mujoco, 'mju_muscleDynamics', forbidden), \
         patch.object(scipy.integrate, 'solve_ivp', forbidden), \
         patch.object(audit.transfer.coupling.v1, 'solve_ivp', forbidden), \
         patch.object(legacy, 'build', forbidden):
        return audit.build()


def test_actual_reconstruction_preserves_prior_failure_and_all_transfer_blocks(rebuilt):
    assert rebuilt['current_motor_count'] == 20
    assert rebuilt['physics_transitions'] == rebuilt['cns_transitions'] == rebuilt['new_admissions'] == 0
    assert not rebuilt['production_transfer_enabled']
    assert all(not paths for paths in rebuilt['tracked_conversion_records'].values())
    assert rebuilt['converter_configuration'] is None
    assert rebuilt['unit_ledger']['physical_force_conversion'] is None


@pytest.mark.parametrize('defect', ['conversion', 'pdf', 'converter', 'parameter', 'raw_type'])
def test_audit_tampering_rejected(rebuilt, tmp_path, defect):
    saved = copy.deepcopy(rebuilt)
    if defect == 'conversion': saved['unit_ledger']['physical_force_conversion'] = 1
    if defect == 'pdf': saved['conversion_pdf']['establishes_locked_xml_validation'] = True
    if defect == 'converter': saved['converter_revision'] = 'inferred_from_filename'
    if defect == 'parameter': saved['comparisons'][0]['mjcf_peak_force'] = 1
    if defect == 'raw_type': saved['current_original_raw_freezes_satisfied'] = 'false'
    path = tmp_path/'audit.json';path.write_text(json.dumps(saved))
    with patch.object(audit, 'build', return_value=rebuilt), pytest.raises(ValueError):
        audit.verify(path)


def test_changed_extract_snapshot_fails_closed(monkeypatch):
    monkeypatch.setattr(audit, 'SNAPSHOT_SHA', '0'*64)
    with pytest.raises(ValueError, match='snapshot changed'): audit.source_hashes()
