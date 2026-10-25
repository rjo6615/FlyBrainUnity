"""Reference algebra and fail-closed binding checks; no physics/CNS experiments."""
import copy
import hashlib
import json

import numpy as np
import pytest

from malecns_backend.embodiment import lf_proximal_binding_review as review


@pytest.fixture
def reference():
    read = lambda p: json.loads((review.ROOT/p).read_text(encoding='utf-8'))
    registration = read(review.audit.PATHS['registration'])
    inventory = read(review.audit.PATHS['candidates'])['candidate_population_inventory']
    identities = read(review.UPSTREAM)['lf_reference']['candidate_identities']
    return registration, inventory, identities


def test_all_hypotheses_and_exact_aliases_remain_unassigned(reference):
    rows = review.reference_rows(*reference)
    assert [len(r['tendon_hypotheses']) for r in rows] == [3, 1, 1, 1, 1]
    assert len(rows[1]['identity']['exact_annotation_aliases']) == 2
    assert sum(len(r['per_neuron_tendon_assignments']) for r in rows) == 13
    for row in rows:
        assert not row['admission_ready']
        assert all(n['tendon'] is None for n in row['per_neuron_tendon_assignments'])
        assert all(row[k] is None for k in ('spike_to_activation', 'activation_to_force',
                                          'force_to_position_target', 'decoder_vector', 'gain'))


@pytest.mark.parametrize('defect', ['drop', 'duplicate', 'basis', 'convention', 'nan', 'identity', 'omit_alternative'])
def test_binding_defects_cannot_be_silently_selected_or_reinterpreted(reference, defect):
    reg, inventory, identities = copy.deepcopy(reference)
    if defect == 'drop': reg['muscle_mechanics'].pop()
    if defect == 'duplicate': reg['muscle_mechanics'][-1] = reg['muscle_mechanics'][0]
    if defect == 'basis': reg['muscle_mechanics'][0]['flygym_covector']['basis_order'].reverse()
    if defect == 'convention': reg['muscle_mechanics'][0]['moment_arm_convention'] = 'dL/dq'
    if defect == 'nan': reg['muscle_mechanics'][0]['flygym_covector']['values'][0] = float('nan')
    if defect == 'identity': identities[0]['body_ids'][0] = 999
    if defect == 'omit_alternative': inventory[0]['mechanical_hypothesis']['external_reference_covectors'].pop()
    with pytest.raises(ValueError): review.reference_rows(reg, inventory, identities)


def test_virtual_work_sign_and_covector_transfer(reference):
    # Synthetic displacements/tensions test an identity, not biological gain or motion.
    reg, _, _ = reference
    jacobian = np.asarray(reg['local_differential_registration']['J_GM'])
    dq_m = np.array([0.013, -0.027, 0.009])
    dq_g = jacobian @ dq_m
    for row in reg['muscle_mechanics']:
        rm = np.array(row['flymimic_covector']['values'])
        rg = np.array(row['flygym_covector']['values'])
        dl = -rm @ dq_m
        for tension in (0., 0.2, 3.):
            assert float((tension*rg) @ dq_g) == pytest.approx(-tension*dl, abs=1e-15)


@pytest.fixture
def xml(monkeypatch):
    raw = b'''<mujoco><default><default class="muscle"><general dyntype="muscle"
    gaintype="muscle" biastype="muscle"/></default></default><tendon><spatial name="t">
    <site site="a"/><site site="b"/></spatial></tendon><actuator><general name="a"
    class="muscle" tendon="t" ctrlrange="0.0001 1" gainprm="1 1 2 1 0 2 10 1 1 0"/>
    </actuator></mujoco>'''
    monkeypatch.setattr(review, 'MODEL_HASH', hashlib.sha256(raw).hexdigest())
    return raw


def test_source_raw_hash_is_not_refreshed_or_canonicalized(xml):
    result = review.inspect_model(xml, review.MODEL_HASH, ['t'])
    assert result['inspection'] == 'XML_ONLY_NOT_COMPILED_OR_SIMULATED'
    assert result['bindings'][0]['tendon_sites'] == [{'site': 'a'}, {'site': 'b'}]
    with pytest.raises(ValueError): review.inspect_model(xml+b' ', review.MODEL_HASH, ['t'])
    with pytest.raises(ValueError): review.inspect_model(xml, 'new_expected_hash', ['t'])
    with pytest.raises(ValueError): review.inspect_model(xml, review.MODEL_HASH, ['absent'])


@pytest.mark.parametrize('old,new', [(b'ctrlrange="0.0001 1"', b'ctrlrange="-1 1"'),
    (b'gainprm="1 1 2', b'gainprm="1 1 -2'),
    (b'gaintype="muscle"', b'gaintype="fixed"'),
    (b'name="a"\n    class=', b'name="a" gear="-1 0 0 0 0 0"\n    class=')])
def test_opposing_source_semantics_rejected(xml, monkeypatch, old, new):
    changed = xml.replace(old, new)
    assert changed != xml
    monkeypatch.setattr(review, 'MODEL_HASH', hashlib.sha256(changed).hexdigest())
    with pytest.raises(ValueError): review.inspect_model(changed, review.MODEL_HASH, ['t'])


def test_failed_output_preserved_and_no_execution_option(tmp_path, monkeypatch):
    def fail(model): raise ValueError('changed source')
    monkeypatch.setattr(review, 'build', fail)
    output = tmp_path/'new'
    args = ['--model', 'missing.xml', '--output-dir', str(output)]
    assert review.main(args) == 1
    record = (output/'review.json').read_bytes()
    assert json.loads(record)['status'] == 'INTEGRITY_ERROR'
    assert json.loads(record)['scientific_transitions'] == 0
    with pytest.raises(FileExistsError): review.main(args)
    assert (output/'review.json').read_bytes() == record
    with pytest.raises(SystemExit): review.main(args+['--execute'])


def test_saved_review_tampering_rejected(tmp_path, monkeypatch):
    record = dict(schema=review.SCHEMA, current_original_raw_freezes_satisfied=False,
                  status='REFERENCE_SEMANTICS_ONLY_ADMISSION_BLOCKED', new_admissions=0)
    monkeypatch.setattr(review, 'build', lambda model: copy.deepcopy(record))
    path = tmp_path/'review.json'
    path.write_text(json.dumps(record))
    assert review.verify(path, 'unused')[0] == record
    record_saved = dict(record, new_admissions=1)
    path.write_text(json.dumps(record_saved))
    with pytest.raises(ValueError): review.verify(path, 'unused')
