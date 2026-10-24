"""Read-only mapping, provenance and no-admission contracts."""
import copy
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from malecns_backend.embodiment import remaining_leg_admission_audit as audit


@pytest.fixture
def identity():
    source=dict(name='exact',actuator='coxa_T1_left',dir=1,idx=[1,3])
    population=dict(name='exact',body_ids=[20,40],dense_indices=[1,3],count=2,
                    bodymap_metadata={k:source[k] for k in ('name','actuator','dir')})
    return {'exact':population},{'exact':source},[10,20,30,40]


def test_body_id_dense_index_is_independently_verified(identity):
    populations,muscles,ids=identity
    result=audit.resolve_population('exact',[20,40],populations,muscles,ids)
    assert result['count']==2 and all(result['checks'].values())
    assert result['body_ids']==[20,40] and result['dense_indices']==[1,3]


def test_multi_target_aliases_retain_ambiguity_without_weakening_identity(identity):
    populations,muscles,ids=identity
    p=populations['exact']; s=muscles['exact']
    second=copy.deepcopy(p); second['bodymap_metadata']['actuator']='coxa_abduct_T1_left'
    other=copy.deepcopy(s); other['actuator']='coxa_abduct_T1_left'
    populations['exact']=[p,second];muscles['exact']=[s,other]
    result=audit.resolve_population('exact',[20,40],populations,muscles,ids)
    assert result['annotation_actuators']==['coxa_T1_left','coxa_abduct_T1_left']
    assert len(result['exact_annotation_aliases'])==2
    second['body_ids']=[20,30]
    with pytest.raises(ValueError): audit.resolve_population('exact',[20,40],populations,muscles,ids)
    second['body_ids']=[20,40]
    muscles['exact']=[s]
    with pytest.raises(ValueError): audit.resolve_population('exact',[20,40],populations,muscles,ids)


@pytest.mark.parametrize('defect',['body','dense','duplicate','count','metadata','float','bodymap'])
def test_identity_defects_fail_closed(identity,defect):
    populations,muscles,ids=identity
    p=populations['exact']
    if defect=='body': ids[1]=999
    if defect=='dense': p['dense_indices'][0]=2
    if defect=='duplicate': p['body_ids'][1]=20
    if defect=='count': p['count']=3
    if defect=='metadata': p['bodymap_metadata']['dir']=-1
    if defect=='float': p['dense_indices'][0]=1.0
    if defect=='bodymap': muscles['exact']['idx']=[3,1]
    with pytest.raises(ValueError): audit.resolve_population('exact',[20,40],populations,muscles,ids)


def test_crlf_correspondence_never_turns_failed_raw_lock_into_pass(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    raw=b'{\n  "unchanged": true\n}\n'
    (tmp_path/'frozen.json').write_bytes(raw.replace(b'\n',b'\r\n'))
    monkeypatch.setattr(audit.subprocess,'check_output',lambda *a,**k:raw)
    result=audit.frozen_record('frozen.json',audit.sha(raw))
    assert result['canonical_content_verified'] and not result['raw_lock_passed']
    assert 'NOT passed' in result['interpretation']
    (tmp_path/'frozen.json').write_bytes(raw)
    assert audit.frozen_record('frozen.json',audit.sha(raw))['raw_lock_passed']
    (tmp_path/'frozen.json').write_bytes(raw.replace(b'true',b'false'))
    with pytest.raises(ValueError): audit.frozen_record('frozen.json',audit.sha(raw))


def test_shared_axis_row_remains_blocked_with_exact_ids(identity):
    populations,muscles,ids=identity
    row=dict(actuator='joint_LFCoxa',global_action_index=0,joint_class='Coxa',leg='LF',
        candidates=[dict(population='exact',body_ids=[20,40])],unresolved_shared_population_conflict=True,
        motor_mapping_status='AMBIGUOUS',decoder_readiness='AMBIGUOUS_DIRECTION',
        unique_physical_mapping=False,candidate_physical_axes=['joint_LFCoxa','joint_LFCoxa_roll'])
    admission=dict(actuator='joint_LFCoxa',action_index=0,neural_motor_admission=False)
    result=audit.row_record(row,admission,populations,muscles,ids,{})
    assert result['status']=='SHARED_AXIS_BINDING_REQUIRED' and not result['admission_ready']
    assert result['coordinate_sign_assigned_by_audit'] is None
    admission['neural_motor_admission']=True
    with pytest.raises(ValueError): audit.row_record(row,admission,populations,muscles,ids,{})


def test_tarsus2_is_not_promoted_to_missing_tarsus1():
    row=dict(actuator='joint_LMTarsus1',global_action_index=13,joint_class='Tarsus1',leg='LM',segment='T2',side='left',
        candidates=[],unresolved_shared_population_conflict=False,motor_mapping_status='UNMAPPED',
        decoder_readiness='INSUFFICIENT_EVIDENCE',unique_physical_mapping=False,candidate_physical_axes=[])
    admission=dict(actuator=row['actuator'],action_index=13,neural_motor_admission=False)
    muscles={'different':dict(name='different',actuator='tarsus2_T2_left')}
    result=audit.row_record(row,admission,{},muscles,[],{})
    assert result['evidence']['related_tarsus2_not_candidates']==['different']
    assert not result['candidates'] and not result['admission_ready']
    muscles['new_exact']=dict(name='new_exact',actuator='tarsus_T2_left')
    with pytest.raises(ValueError): audit.row_record(row,admission,{},muscles,[],{})


def test_exclusive_failure_output_and_no_execution_flags(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'build',Mock(side_effect=ValueError('changed evidence')))
    output=tmp_path/'audit'
    assert audit.main(['--output-dir',str(output)])==1
    raw=(output/'audit.json').read_bytes()
    assert json.loads(raw)['scientific_transitions']==0
    with pytest.raises(FileExistsError): audit.main(['--output-dir',str(output)])
    assert (output/'audit.json').read_bytes()==raw
    with pytest.raises(SystemExit): audit.main(['--output-dir',str(output),'--execute'])
