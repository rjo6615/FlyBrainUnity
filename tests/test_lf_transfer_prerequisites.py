"""Static source/identity and tamper checks, not new physics or biological tests."""
import copy
import json
from unittest.mock import patch

import pytest

from malecns_backend.embodiment import lf_transfer_prerequisites as review


@pytest.fixture
def inputs():
    return review.read(review.CONTEXT), review.read(review.coupling.v1.schedule.BINDING)


@pytest.mark.parametrize('defect', ['source', 'default', 'tendon_order', 'drop', 'extra', 'force', 'dynamics', 'length'])
def test_source_identity_or_parameter_change_cannot_be_interpreted_as_transfer(inputs, defect):
    context, binding = copy.deepcopy(inputs)
    if defect == 'source': binding['source_xml_sha256'] = '0'*64
    if defect == 'default': context['source_model']['muscle_default']['gear'] = '2'
    if defect == 'tendon_order': context['source_model']['bindings'].reverse()
    if defect == 'drop': binding['selected'].pop()
    if defect == 'extra': binding['selected'].append(binding['selected'][0])
    if defect == 'force': binding['selected'][0]['source_attributes']['gainprm'] = '0 1 -1 200 0 2 10 1 1 0'
    if defect == 'dynamics': binding['selected'][0]['source_attributes']['dynprm'] = '0.01 0.04'
    if defect == 'length': binding['selected'][0]['source_attributes']['lengthrange'] = '0 1'
    with pytest.raises(ValueError): review.selected_parameters(context, binding)


def test_automatic_default_and_observation_scale_do_not_override_explicit_muscles(inputs):
    context, binding = inputs
    assert float(context['source_model']['muscle_default']['gainprm'].split()[2]) == -1
    rows = review.selected_parameters(context, binding)
    assert [r['explicit_peak_force'] for r in rows] == [28.7481, 12.9, 10.5807, 157.429]
    assert all(r['source_force_SI_unit'] is None and r['target_force_conversion'] is None for r in rows)


def test_optional_external_xml_rejects_a_different_model_before_parsing(tmp_path, inputs):
    other = tmp_path/'other.xml'
    other.write_text('<mujoco/>')
    with pytest.raises(ValueError, match='raw hash mismatch'):
        review.inspect_external_model(other, inputs[0])


@pytest.fixture(scope='module')
def rebuilt():
    import mujoco
    import scipy.integrate
    from malecns_backend.embodiment import lf_anatomical_crosswalk as crosswalk
    from malecns_backend.embodiment import remaining_leg_admission_audit as audit
    # Real saved-evidence reconstruction, with live execution entry points made
    # fatal. It must not fall back to model enumeration or solver recomputation.
    def forbidden(*args, **kwargs):
        raise AssertionError('review attempted physics/solver/live enumeration')
    with patch.object(mujoco, 'MjModel', forbidden), patch.object(mujoco, 'MjData', forbidden), \
         patch.object(mujoco, 'mj_forward', forbidden), patch.object(mujoco, 'mj_step', forbidden), \
         patch.object(mujoco, 'mju_muscleDynamics', forbidden), \
         patch.object(scipy.integrate, 'solve_ivp', forbidden), \
         patch.object(review.coupling.v1, 'solve_ivp', forbidden), \
         patch.object(review.coupling, 'execute', forbidden), \
         patch.object(audit, 'build', forbidden), patch.object(crosswalk, 'verify', forbidden):
        return review.build()


def test_real_saved_evidence_keeps_all_hypotheses_and_no_admissions(rebuilt):
    assert rebuilt['synthetic_prerequisite']['cases'] == 9
    populations = rebuilt['population_hypotheses']
    assert [len(p['tendon_hypotheses']) for p in populations] == [3, 1, 1, 1, 1]
    assert sum(len(p['per_neuron_tendon_assignments']) for p in populations) == 13
    assert all(n['tendon'] is None for p in populations for n in p['per_neuron_tendon_assignments'])
    assert all(p['spike_to_activation'] is None and not p['admission_ready'] for p in populations)
    assert not rebuilt['production_transfer_enabled']
    assert not rebuilt['dimensional_ledger']['observation_division_by_1000_is_force_calibration']
    assert rebuilt['dimensional_ledger']['force_conversion'] is None


@pytest.mark.parametrize('defect', ['admit', 'convert', 'gate', 'identity', 'evidence', 'historical_failure', 'raw_type'])
def test_saved_review_tampering_is_rejected(rebuilt, tmp_path, defect):
    saved = copy.deepcopy(rebuilt)
    if defect == 'admit': saved['production_transfer_enabled'] = True
    if defect == 'convert': saved['dimensional_ledger']['force_conversion'] = 0.001
    if defect == 'gate': saved['gates'][1]['status'] = 'VERIFIED'
    if defect == 'identity': saved['population_hypotheses'][0]['identity']['body_ids'][0] = 123
    if defect == 'evidence': saved['source_hashes'][review.RECORD] = '0'*64
    if defect == 'historical_failure': saved['synthetic_prerequisite']['historical_v1_classification'] = 'PASS'
    if defect == 'raw_type': saved['current_original_raw_freezes_satisfied'] = 'false'
    path = tmp_path/'review.json'
    path.write_text(json.dumps(saved))
    with patch.object(review, 'build', return_value=rebuilt), pytest.raises(ValueError):
        review.verify(path)


def test_checkout_raw_representation_is_reported_without_rewriting_history(rebuilt, tmp_path):
    saved = copy.deepcopy(rebuilt)
    saved['current_original_raw_freezes_satisfied'] = not rebuilt['current_original_raw_freezes_satisfied']
    path = tmp_path/'review.json'
    path.write_text(json.dumps(saved))
    before = path.read_bytes()
    with patch.object(review, 'build', return_value=rebuilt):
        historical, now = review.verify(path)
    assert historical['current_original_raw_freezes_satisfied'] != now['current_original_raw_freezes_satisfied']
    assert not now['production_transfer_enabled']
    assert path.read_bytes() == before


def test_changed_context_snapshot_is_rejected_before_saved_reconstruction(monkeypatch):
    monkeypatch.setattr(review, 'CONTEXT_SHA', '0'*64)
    with pytest.raises(ValueError, match='context snapshot changed'):
        review.source_hashes()
