"""Exact-ID reference leads and disagreement retention, never motor admission."""
import copy
import json
from unittest.mock import Mock

import pytest

from malecns_backend.embodiment import distal_tarsus_reference as ref


@pytest.fixture
def data():
    banc = dict(banc_888_id='720575941481071802', cell_type='tarsus_levator_D',
                cell_class='leg_motor_neuron', cell_sub_class='middle_leg_motor_neuron',
                super_class='motor', flow='efferent', side='right', neuromere='T2',
                nerve='right_mesothoracic_leg_nerve', malecns_match='801477',
                malecns_nblast_match='902719', manc_match='14828')
    old = dict(malecns_09_id='801477', cell_type='MNml81', side='right',
               nerve='right_mesothoracic_leg_nerve', neuromere=None)
    current = dict(bodyId=801477, type='MNml81', superclass='vnc_motor',
                   somaSide='R', rootSide=None, somaNeuromere='T2', subclass='ml',
                   exitNerve='MesoLN', mancBodyid=14828.0)
    return [banc], [old], [current], [20, 801477], []


def test_exact_body_index_and_original_rows_retained_without_admission(data):
    row = ref.records(*data)[0]
    assert row['malecns_reference_body_id'] == 801477
    assert row['runtime_dense_index'] == 1
    assert row['banc_original']['banc_888_id'] == '720575941481071802'
    assert row['v09_original_rows'] == data[1] and row['v10_original_rows'] == data[2]
    assert 'NBLAST_REFERENCE_DIFFERS' in row['flags']
    assert 'CURRENT_TYPE_HAS_NO_TARSUS_ACTION_LABEL' in row['flags']
    assert row['proposed_population'] is None and row['actuator_assignment'] is None
    assert row['decoder_sign'] is None and row['gain'] is None and not row['admission_ready']


@pytest.mark.parametrize('bad', [801477.0, True, '801477.0', '0801477', '801477,902719', '', None])
def test_reference_ids_never_round_or_choose_a_candidate(data, bad):
    data[0][0]['malecns_match'] = bad
    row = ref.records(*data)[0]
    assert row['malecns_reference_body_id'] is None
    assert row['runtime_dense_index'] is None
    assert 'MISSING_OR_NONSCALAR_MALECNS_REFERENCE' in row['flags']


def test_many_to_one_missing_and_external_label_controls_are_all_retained(data):
    second = copy.deepcopy(data[0][0]); second['banc_888_id'] = '720575941436891103'
    missing = copy.deepcopy(second); missing['banc_888_id'] = '720575941436891104'
    missing['malecns_match'] = None
    control = copy.deepcopy(second); control['banc_888_id'] = '720575941436891105'
    control['cell_type'] = 'other_motor'; control['malecns_cell_type'] = 'Ta depressor MN'
    data[0].extend([second, missing, control])
    rows = ref.records(*data)
    assert len(rows) == 4
    assert sum('MANY_BANC_ROWS_SHARE_REFERENCE' in r['flags'] for r in rows) == 3
    assert sum('MISSING_OR_NONSCALAR_MALECNS_REFERENCE' in r['flags'] for r in rows) == 1
    assert sum('EXTERNAL_LABEL_CONTROL_NOT_BANC_TARSUS_CLASS' in r['flags'] for r in rows) == 1
    assert all(not r['admission_ready'] for r in rows)


@pytest.mark.parametrize('defect,flag', [
    ('side', 'SIDE_DISAGREEMENT_OR_MISSING'),
    ('segment', 'SEGMENT_CLASS_OR_NERVE_DISAGREEMENT'),
    ('type', 'V09_V10_TYPE_DISAGREEMENT'),
    ('manc', 'MANC_MATCH_CYCLE_DISAGREEMENT'),
    ('runtime', 'NOT_IN_RUNTIME'),
    ('duplicate_current', 'V10_IDENTITY_MISSING_OR_DUPLICATE'),
    ('duplicate_old', 'V09_IDENTITY_MISSING_OR_DUPLICATE'),
])
def test_conflicts_are_recorded_not_resolved_by_selection(data, defect, flag):
    if defect == 'side': data[2][0]['somaSide'] = 'L'
    elif defect == 'segment': data[2][0]['somaNeuromere'] = 'T3'
    elif defect == 'type': data[1][0]['cell_type'] = 'different'
    elif defect == 'manc': data[2][0]['mancBodyid'] = 200065.0
    elif defect == 'runtime': data[3].remove(801477)
    elif defect == 'duplicate_current': data[2].append(copy.deepcopy(data[2][0]))
    elif defect == 'duplicate_old': data[1].append(copy.deepcopy(data[1][0]))
    row = ref.records(*data)[0]
    assert flag in row['flags'] and not row['admission_ready']


def test_existing_actuator_annotations_not_reassigned(data):
    data[4].append(dict(name='existing', actuator='femur_T2_right', idx=[1], dir=-1))
    row = ref.records(*data)[0]
    assert row['existing_actuator_annotations'] == data[4]
    assert 'EXISTING_ACTUATOR_ANNOTATIONS_RETAINED' in row['flags']
    assert row['actuator_assignment'] is None


def test_runtime_duplicates_and_nonexact_banc_ids_refused(data):
    data[3].append(801477)
    with pytest.raises(ValueError): ref.records(*data)
    data[3].pop()
    data[0][0]['banc_888_id'] = float(720575941481071802)
    with pytest.raises(ValueError): ref.records(*data)


def test_exclusive_failed_attempt_and_no_execution_flag(tmp_path, monkeypatch):
    target = tmp_path/'failed'
    monkeypatch.setattr(ref, 'build', Mock(side_effect=ValueError('changed source')))
    with pytest.raises(ValueError): ref.main(['--output-dir', str(target)])
    before = (target/'error.json').read_bytes()
    assert json.loads(before)['scientific_transitions'] == 0
    with pytest.raises(FileExistsError): ref.main(['--output-dir', str(target)])
    assert (target/'error.json').read_bytes() == before
    with pytest.raises(SystemExit): ref.main(['--output-dir', str(target), '--execute'])


def test_verify_rejects_omitted_or_changed_reference_record(tmp_path, monkeypatch, data):
    now = dict(records=ref.records(*data), current_three_original_raw_locks=True)
    monkeypatch.setattr(ref, 'build', lambda: now)
    path = tmp_path/'saved.json'
    saved = copy.deepcopy(now); saved['current_three_original_raw_locks'] = False
    path.write_text(json.dumps(saved))
    assert ref.verify(path)[1] == now
    saved['records'][0]['actuator_assignment'] = 'unauthorized'
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError): ref.verify(path)


def test_nonfinite_representation_never_conflates_nan_and_missing():
    raw = {'missing': None, 'nan': float('nan'), 'positive': float('inf'),
           'negative': -float('inf'), 'nested': [0.5, float('nan')]}
    safe = json.loads(json.dumps(ref.json_safe(raw), allow_nan=False))
    assert safe['missing'] is None
    assert safe['nan'] == {'__arrow_nonfinite_float__': 'NaN'}
    assert safe['positive'] == {'__arrow_nonfinite_float__': '+Infinity'}
    assert safe['negative'] == {'__arrow_nonfinite_float__': '-Infinity'}
    assert safe['nested'] == [0.5, {'__arrow_nonfinite_float__': 'NaN'}]


def test_encoding_failure_preserves_error_without_partial_report(tmp_path, monkeypatch):
    monkeypatch.setattr(ref, 'build', lambda: {'unencoded': float('nan')})
    target = tmp_path/'encoding-error'
    with pytest.raises(ValueError): ref.main(['--output-dir', str(target)])
    assert not (target/'reference.json').exists()
    assert json.loads((target/'error.json').read_text())['status'] == 'EXTRACTION_FAILED'


def test_real_saved_reference_reconstructs_without_physics_or_cns(monkeypatch):
    import sys
    from malecns_backend.embodiment import _windows_m7_spontaneous_locomotion_adapter as legacy
    from malecns_backend.embodiment import full_leg_interface as inventory
    from malecns_backend.embodiment import _windows_m8_live_condition as kernel
    forbidden = Mock(side_effect=AssertionError('forbidden native/CNS/live-audit boundary'))
    monkeypatch.setattr(legacy, '_inventory', forbidden)
    monkeypatch.setattr(legacy, 'enumerate_live_actuators', forbidden)
    monkeypatch.setattr(inventory, 'enumerate_live_actuators', forbidden)
    monkeypatch.setattr(ref.official.audit, 'build', forbidden)
    monkeypatch.setattr(kernel, '_scientific_transition_kernel', forbidden)
    for module in ['flygym', 'mujoco', 'malecns_backend.neural']:
        monkeypatch.setitem(sys.modules, module, None)
    saved, now = ref.verify(ref.ROOT/'docs/evidence/distal-tarsus-reference-v1_3/run/reference.json')
    assert saved['scoped_rows'] == now['scoped_rows'] == 43
    assert now['new_admissions'] == now['scientific_transitions'] == 0
    assert now['current_motor_count'] == 20
    assert all(not r['admission_ready'] and r['actuator_assignment'] is None for r in now['records'])
    forbidden.assert_not_called()


def test_all_observed_scalar_types_and_timestamp_roundtrip():
    from datetime import datetime, timezone
    original = datetime(2026, 5, 6, 17, 17, 8, 123456, tzinfo=timezone.utc)
    raw = [None, True, 'literal', 801477, 0.5, float('nan'), original]
    saved = json.loads(json.dumps(ref.json_safe(raw), allow_nan=False))
    assert saved[:5] == raw[:5]
    assert datetime.fromisoformat(saved[-1]['__arrow_datetime_iso8601__']) == original
    assert saved[-2] == {'__arrow_nonfinite_float__': 'NaN'}
