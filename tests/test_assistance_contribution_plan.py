"""Static authority/partition/boundary checks; no actuator mutation or experiment."""
import copy
import json
import subprocess
import sys
from unittest.mock import patch

import pytest

from malecns_backend.live import assistance_contribution_plan as p


def test_complete_eight_arm_factorial_and_fixed_budget():
    plan=p.build()
    assert [a['id'] for a in plan['arms']]==['A_NC','A_WC','A_NP','A_WP','R_NC','R_WC','R_NP','R_WP']
    assert len({(a['baseline22_policy'],a['neural20_policy'],a['pulse']) for a in plan['arms']})==8
    assert plan['planned_physics_transitions_total']==8*plan['planned_physics_transitions_per_arm']==160000
    assert plan['planned_states_total']==160008 and plan['planned_neural_updates_total']==32000
    assert plan['planned_physics_transitions_per_arm']*plan['physics_dt_s']==plan['duration_s_per_arm']==2
    assert not plan['runner_implemented'] and not plan['native_qualification_passed']


def test_retained_and_selected_partition_exactly_match_original_admissions():
    plan=p.build(); old=p.read_json(p.ROOT/p.AUTHORITY)
    retained,selected=plan['retained_neural20'],plan['selected_baseline22']
    assert {r['coordinate'] for r in retained}=={r['name'] for r in old['motors']}
    assert {r['coordinate'] for r in selected}=={r['name'] for r in old['unadmitted_baseline_only']}
    assert not {r['coordinate'] for r in retained}.intersection(r['coordinate'] for r in selected)
    assert sorted(r['action_index'] for r in retained+selected)==list(range(42))
    for row in retained+selected:
        assert all(row[k] is None for k in ('native_actuator_id','native_joint_id','native_body_id','qpos_range','dof_range'))


@pytest.mark.parametrize('fault',['promote','overlap','index','wrong_name','bool_index'])
def test_static_selector_refuses_wrong_coordinate_authority(fault):
    authority=p.read_json(p.ROOT/p.AUTHORITY)
    if fault=='promote':authority['motors'].append(authority['unadmitted_baseline_only'].pop())
    if fault=='overlap':authority['unadmitted_baseline_only'][0]=copy.deepcopy(authority['motors'][0])
    if fault=='index':authority['motors'][0]['action_index']=0
    if fault=='wrong_name':authority['motors'][0]['name']='joint_unknown'
    if fault=='bool_index':authority['motors'][0]['action_index']=True
    with pytest.raises(ValueError):p.coordinate_partition(authority)


@pytest.mark.parametrize('arm',p.ARM_IDS)
def test_expected_sampled_model_phase_preserves_5005_endpoint(arm):
    assert p.expected_model_phase(arm,0)=='M0'
    assert p.expected_model_phase(arm,5000)=='M0'
    assert p.expected_model_phase(arm,5005)=='M0'
    assert p.expected_model_phase(arm,5006)==('MR' if arm.startswith('R_') else 'M0')
    assert p.expected_model_phase(arm,20000)==('MR' if arm.startswith('R_') else 'M0')


@pytest.mark.parametrize('index',[-1,20001,5005.0,True])
def test_phase_refuses_non_scientific_index(index):
    with pytest.raises(ValueError):p.expected_model_phase('R_NP',index)


def test_qualification_is_explicit_and_does_not_claim_old_lf_scope_validates22():
    q=p.build()['qualification']
    assert len(q['control_signs'])*len(q['velocity_signs'])*len(q['phases'])==q['explicit_shadow_forwards']==12
    assert q['explicit_shadow_resets']==12 and q['shadow_mjdata_allocations']==1
    assert q['integration']==q['cns_updates']==q['additional_flygym_models']==q['additional_cns_initializations']==0
    assert q['force_zero_preservation_atol']==1e-10 and q['force_projection_atol']==1e-8
    assert q['baseline_exposure_floor']==1e-8
    assert q['evidence_reused']=='LF_ISOLATION_MECHANISM_NOT_22COORDINATE_VALIDATION'


def test_verify_rejects_changed_mechanics_science_and_unsupported_pass_claim(tmp_path):
    plan=p.build(); target=tmp_path/'plan.json'
    for key,value in [('native_binding_completed',True),('native_qualification_passed',True),
                      ('automatic_retries',1),('seed',2),('planned_physics_transitions_total',80000)]:
        altered=dict(plan,**{key:value});target.write_text(json.dumps(altered))
        with pytest.raises(ValueError):p.verify(target)
    altered=copy.deepcopy(plan);altered['mechanical_event']['mutate_retained20_parameters']=True
    target.write_text(json.dumps(altered))
    with pytest.raises(ValueError):p.verify(target)


def test_strict_json_refuses_duplicate_nonfinite_or_numeric_type_drift(tmp_path):
    target=tmp_path/'plan.json'
    for text in ('{"seed":1,"seed":2}','{"seed":NaN}'):
        target.write_text(text)
        with pytest.raises(ValueError):p.read_json(target)
    plan=p.build();plan['seed']=1.0;target.write_text(json.dumps(plan))
    with pytest.raises(ValueError):p.verify(target)


def test_exclusive_output_preserves_existing_user_file(tmp_path):
    target=tmp_path/'existing.json';target.write_text('preserved')
    with patch.object(p,'build',side_effect=AssertionError('should refuse before building')):
        with pytest.raises(SystemExit):p.main(['--output',str(target)])
    assert target.read_text()=='preserved'


def test_cli_verify_does_not_accept_live_execution_flag(tmp_path):
    with patch.object(p,'build',side_effect=AssertionError('not an execution CLI')):
        with pytest.raises(SystemExit):p.main(['--verify',str(tmp_path/'unused'),'--live'])


def test_current_authorities_and_code_hashes_are_read_only():
    paths=[p.AUTHORITY,p.REFERENCE,*p.SOURCE_PATHS]
    before={name:(p.ROOT/name).read_bytes() for name in paths}
    assert p.build()['reference']['known_behavior']=='MIXED_OR_UNRESOLVED'
    assert before=={name:(p.ROOT/name).read_bytes() for name in paths}


def test_fresh_process_plan_forbids_native_imports_and_cns_or_loader_calls():
    code='''import importlib.abc,sys
from unittest.mock import patch
class Forbid(importlib.abc.MetaPathFinder):
    def find_spec(self,name,*args):
        if name.split('.')[0] in ('flygym','mujoco','dm_control'):
            raise AssertionError('native import forbidden: '+name)
sys.meta_path.insert(0,Forbid())
from malecns_backend.live import assistance_contribution_plan as p
from malecns_backend.neural import MaleCNSBrain
from malecns_backend import loader
with patch.object(MaleCNSBrain,'__init__',side_effect=AssertionError('CNS construction forbidden')),patch.object(loader,'load_malecns',side_effect=AssertionError('loader forbidden')):
    plan=p.build()
    assert len(plan['selected_baseline22'])==22
    assert not plan['native_execution_in_this_update']
print('Static plan only; native imports, CNS and loader forbidden.')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=p.ROOT,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert 'Static plan only' in result.stdout
