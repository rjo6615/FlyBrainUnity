"""Mandatory full-source gates and original scientific equivalence, no native assay."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from malecns_backend.live import controlled_live_balance_v1_1 as v


def checked():
    expected=v.specification()['source_graph_authority']
    return dict(verified=True,checks={k:True for k in ('design','original_authorities','original_neural_data')},
        errors={},scientific_transitions=0,native_constructions=0,cns_initializations=0,
        environment=dict(verified=True,observed={k:value for k,value in v.base.design()['expected_environment'].items()
                                               if k!='dependency_changes_allowed'},mismatches={}),
        complete_source_schema='balance-loader-source-prerequisites-v1',
        orientation_source=dict(verified=True,path=v.source_guard.GRAPH,expected=expected,
            observed={k:expected[k] for k in ('sha256','bytes')}))


def test_spec_locks_prior_failure_executed_sources_and_original_source_checker():
    p=v.specification()
    assert p['executed_v1_sources']==v.prior.sources()
    assert not p['scientific_parameters_changed'] and not p['assistance_changed']
    assert v.run_arm is v.prior.run_arm and v.audit_display is v.prior.audit_display
    assert v.original is v.prior.original
    assert v.verified_preflight(checked())


def test_actual_construction_free_receipt_satisfies_complete_semantic_gate():
    path=v.ROOT/'docs/evidence/controlled-live-balance-v1_1/engineering-preflight-01/preflight.json'
    if not path.exists():pytest.skip('actual construction-free engineering receipt unavailable')
    record=json.loads(path.read_text())
    assert record['verified'] and v.verified_preflight(record)


@pytest.mark.parametrize('fault',['missing_graph','bad_hash','bad_size','old_only','false_old_check','clock_work','environment'])
def test_full_preflight_guard_rejects_partial_or_forged_success(fault):
    value=checked()
    if fault=='missing_graph': value.pop('orientation_source')
    if fault=='bad_hash': value['orientation_source']['observed']['sha256']='changed'
    if fault=='bad_size': value['orientation_source']['observed']['bytes']+=1
    if fault=='old_only': value={'verified':True}
    if fault=='false_old_check': value['checks']['original_neural_data']=False
    if fault=='clock_work': value['scientific_transitions']=1
    if fault=='environment': value['environment']['observed']=dict(value['environment']['observed'],numpy='changed')
    assert not v.verified_preflight(value)


def test_controller_will_not_launch_when_complete_guard_fails(tmp_path):
    with patch.object(v,'preflight',return_value=dict(checked(),verified=False)),patch.object(v,'committed',side_effect=AssertionError('must refuse before commit/native')):
        report=v.execute(tmp_path/'refused',live=True,review_note='user confirmed review',child_runner=lambda *a:pytest.fail('worker launched'))
    assert not report['scientific_experiment_started'] and report['run_status']=='ERROR'
    assert not report['evaluation']['scientific']['accepted']


def control(folder):
    p=folder/'controller.json'
    result=v.base.save(p,dict(schema=v.SCHEMA,specification=v.specification(),sources=v.sources(),commit='fixture',
        prior_full_body_review_note='synthetic fixture only',complete_preflight=checked()))
    request=folder/'NC.request.json'
    v.base.save(request,dict(condition='NC',controller_sha256=result['sha256']))
    return request


def test_worker_checks_missing_source_before_scientific_factory(tmp_path):
    request=control(tmp_path)
    with patch.object(v,'committed',return_value='fixture'),patch.object(v.original,'process_boundary',return_value={}), \
            patch.object(v,'preflight',return_value=dict(checked(),verified=False)), \
            patch.object(v.base,'static_authority',side_effect=AssertionError('native authority reached')), \
            patch.object(v,'run_arm',side_effect=AssertionError('scientific arm started')):
        assert v.worker(request)==1
    receipt=json.loads((tmp_path/'NC.done.json').read_text())
    arm=v.original.read_arm(tmp_path,'NC',receipt['artifact'])
    assert arm['samples']==[] and not arm['complete_preflight_before']['verified']
    assert 'before initialization' in arm['worker_error']


def test_worker_rejects_controller_without_complete_prerequisite_record(tmp_path):
    request=control(tmp_path)
    path=tmp_path/'controller.json'; value=json.loads(path.read_text());value['complete_preflight']={'verified':True}
    path.write_text(json.dumps(value))
    with patch.object(v,'committed',return_value='fixture'),patch.object(v,'preflight',side_effect=AssertionError('must reject first')):
        with pytest.raises(ValueError,match='controller/prerequisite'):v.worker(request)
    assert not (tmp_path/'NC.claim.json').exists()


def test_worker_post_check_error_keeps_acquired_raw_and_stops(tmp_path):
    request=control(tmp_path); before=checked(); after=dict(before,verified=False)
    body=dict(condition='NC',run_status='COMPLETE',samples=[{'synthetic':True}],neural=[])
    fake=SimpleNamespace(Fly=SimpleNamespace(_existing_fly_names=set(),_default_fly_name=0))
    with patch.object(v,'committed',return_value='fixture'),patch.object(v.original,'process_boundary',return_value={}), \
            patch.object(v,'preflight',side_effect=[before,after]),patch.object(v.base,'static_authority',return_value=({},[])), \
            patch.dict(sys.modules,{'flygym':fake}),patch.object(v,'run_arm',return_value=(body,None)):
        assert v.worker(request)==1
    receipt=json.loads((tmp_path/'NC.done.json').read_text()); arm=v.original.read_arm(tmp_path,'NC',receipt['artifact'])
    assert arm['samples']==[{'synthetic':True}] and arm['run_status']=='ERROR'
    assert arm['complete_preflight_before']==before and arm['complete_preflight_after']==after


@pytest.fixture(scope='module')
def synthetic():
    spec=importlib.util.spec_from_file_location('prior_live_fixture_v11',v.ROOT/'tests/test_controlled_live_balance.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    old,report,arms=module.synthetic_evaluation.__wrapped__()
    report=dict(report,schema=v.SCHEMA,specification=v.specification(),preflight=checked(),sources_before=v.sources(),sources_after=v.sources())
    arms={c:dict(a,worker_sources_before=v.sources(),worker_sources_after=v.sources(),
                 complete_preflight_before=checked(),complete_preflight_after=checked()) for c,a in arms.items()}
    return old,report,arms


def test_full_original_auditor_and_behavior_equivalence_with_new_schema(synthetic):
    old,report,arms=synthetic
    expected=v.base.evaluate(old)
    actual=v.evaluate(report,'.',loader=lambda f,c,a:arms[c],display_loader=lambda *a:None,
                      reference_comparator=lambda *a:{'status':'SYNTHETIC_NO_REFERENCE'})
    scientific=actual['scientific']
    assert scientific['accepted'],scientific.get('reason')
    for field in ('arms','behavior','pair_exposure','unity_replay_eligible'):assert scientific[field]==expected[field]
    assert all(d['status']=='FAILED' for d in actual['display'].values())


def test_incomplete_preflight_worker_evidence_rejects_before_original_audit(synthetic):
    _,report,arms=synthetic
    arm=dict(arms['NC'],complete_preflight_after={'verified':True})
    with patch.object(v.base,'audit_arm',side_effect=AssertionError('must reject first')):
        actual=v.evaluate(report,'.',loader=lambda *a:arm)
    assert not actual['scientific']['accepted']


def test_source_corruption_and_incomplete_campaign_reject_without_loading(synthetic):
    report=synthetic[1]
    for changed in (dict(report,sources_after={'changed':'code'}),dict(report,run_status='INCOMPLETE')):
        actual=v.evaluate(changed,'.',loader=lambda *a:pytest.fail('loaded incomplete/changed'))
        assert not actual['scientific']['accepted']


def test_no_retry_controller_stops_on_first_worker_failure(tmp_path):
    calls=[]
    def child(folder,condition,*args):
        calls.append(condition)
        return dict(run_status='ERROR',artifact=dict(path='NC.json.gz',sha256='fixture'),
                    display_artifact=dict(path='NC.display.json.gz',sha256='fixture')),False
    with patch.object(v,'preflight',return_value=checked()),patch.object(v,'committed',return_value='fixture'):
        report=v.execute(tmp_path/'partial',live=True,review_note='confirmed user review',child_runner=child)
    assert calls==['NC'] and report['run_status']=='INCOMPLETE'
    assert not report['evaluation']['scientific']['accepted']


def test_actual_os_workers_bind_complete_precheck_and_postcheck(tmp_path):
    """Two actual OS processes; fixture registry/science only, no native fly/CNS."""
    script=tmp_path/'worker_fixture.py'
    script.write_text('''import sys
from types import SimpleNamespace
sys.path.insert(0,ROOT_VALUE)
from malecns_backend.live import controlled_live_balance_v1_1 as v
class FixtureFly:
    _existing_fly_names=set()
    _default_fly_name=0
sys.modules['flygym']=SimpleNamespace(Fly=FixtureFly)
v.committed=lambda:'fixture'
v.preflight=lambda:FULL_CHECK_VALUE
v.base.static_authority=lambda:({},[])
def arm(condition,*args):
    assert FixtureFly._existing_fly_names==set()
    FixtureFly._existing_fly_names.add('fixture-used')
    return dict(condition=condition,run_status='COMPLETE',samples=[{'synthetic':True}],neural=[]),None
v.run_arm=arm
raise SystemExit(v.worker(sys.argv[1]))
'''.replace('ROOT_VALUE',repr(str(v.ROOT))).replace('FULL_CHECK_VALUE',repr(checked())),encoding='utf-8')
    artifact=v.base.save(tmp_path/'controller.json',dict(schema=v.SCHEMA,specification=v.specification(),sources=v.sources(),
        commit='fixture',prior_full_body_review_note='synthetic only',complete_preflight=checked()))
    real_popen=v.subprocess.Popen
    def launch(command,**kwargs):
        assert command[3]=='malecns_backend.live.controlled_live_balance_v1_1'
        return real_popen([sys.executable,'-u',str(script),command[-1]],**kwargs)
    pids=[]
    with patch.object(v.subprocess,'Popen',side_effect=launch):
        for condition in ('NC','WC'):
            receipt,interrupted=v.run_child(tmp_path,condition,artifact['sha256'])
            assert receipt['run_status']=='COMPLETE' and not interrupted
            arm=v.original.read_arm(tmp_path,condition,receipt['artifact'])
            assert arm['complete_preflight_before']==arm['complete_preflight_after']==checked()
            pids.append(receipt['pid'])
    assert len(set(pids))==2


def test_new_default_cli_cannot_execute_or_accept_uncommitted_source(tmp_path):
    with patch.object(v,'preflight',return_value=checked()):
        report=v.execute(tmp_path/'check',child_runner=lambda *a:pytest.fail('worker'))
    assert report['run_status']=='NOT_RUN' and not report['scientific_experiment_started']
    with pytest.raises(FileExistsError):v.execute(tmp_path/'check')
    with pytest.raises(SystemExit):v.main(['--evaluate','.','--live'])
    with patch.object(v,'preflight',return_value=checked()),patch.object(v,'committed',side_effect=ValueError('uncommitted')):
        report=v.execute(tmp_path/'uncommitted',live=True,review_note='confirmed',child_runner=lambda *a:pytest.fail('worker'))
    assert not report['scientific_experiment_started'] and 'uncommitted' in report['error']
