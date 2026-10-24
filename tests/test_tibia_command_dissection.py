"""Synthetic dissection boundary tests; not evidence of biological balance."""
import copy
import json
from unittest.mock import Mock

import numpy as np
import pytest

from malecns_backend.live import tibia_command_dissection as study


@pytest.fixture
def baseline(monkeypatch):
    monkeypatch.setattr(study.recovery,'STEPS',2)
    return dict(samples=[dict(commanded_joints=None,adhesion=None),
        dict(commanded_joints=list(np.arange(42,dtype=float)),adhesion=[0.]*6),
        dict(commanded_joints=list(np.arange(42,dtype=float)+100),adhesion=[0.]*6)])


def test_selected_anatomical_inventory_and_only_selected_coordinates_change():
    assert tuple(i for _,i in study.SELECTED)==(5,12,19,26,33,40)
    proposed=np.arange(42,dtype=float)
    archived=proposed+100
    applied=study.selected_action(proposed,archived)
    other=np.setdiff1d(np.arange(42),study.INDICES)
    np.testing.assert_array_equal(applied[study.INDICES],archived[study.INDICES])
    np.testing.assert_array_equal(applied[other],proposed[other])
    np.testing.assert_array_equal(proposed,np.arange(42))
    np.testing.assert_array_equal(archived,np.arange(42)+100)
    applied[0]=999
    assert proposed[0]==0


@pytest.mark.parametrize('proposed,archived',[([0.], [0.]*42),([0.]*42,[0.]),([float('nan')]*42,[0.]*42),([0.]*42,[float('inf')]*42)])
def test_invalid_action_rejected(proposed,archived):
    with pytest.raises(ValueError): study.selected_action(proposed,archived)


def test_apply_records_actual_selected_action_and_preserves_other_motors(baseline):
    trial=study.TibiaTrial('T_P',baseline)
    trial.samples=[{}]
    trial.original_sim_step=Mock(return_value='native-result')
    action=dict(joints=[-1.]*42,adhesion=[0.]*6)
    assert trial.apply(action)=='native-result'
    expected=study.selected_action(action['joints'],baseline['samples'][1]['commanded_joints'])
    np.testing.assert_array_equal(trial.original_sim_step.call_args.args[0]['joints'],expected)
    assert action['joints']==[-1.]*42 and trial.proposed==[-1.]*42
    np.testing.assert_array_equal(trial.applied['joints'],expected)
    trial.samples.append({})
    trial.apply(action)
    assert trial.applied['joints'][5]==105.


@pytest.mark.parametrize('defect',['adhesion','extra','out_of_range'])
def test_invalid_transition_never_calls_physics(baseline,defect):
    trial=study.TibiaTrial('T_C',baseline)
    trial.samples=[{}]
    trial.original_sim_step=Mock()
    action=dict(joints=[0.]*42,adhesion=[0.]*6)
    if defect=='adhesion': action['adhesion'][0]=1.
    if defect=='extra': action['extra']=1
    if defect=='out_of_range': trial.samples=[{}]*3
    with pytest.raises(ValueError): trial.apply(action)
    trial.original_sim_step.assert_not_called()


def test_capture_passes_actual_action_and_retains_proposal(baseline,monkeypatch):
    trial=study.TibiaTrial('T_P',baseline)
    trial.samples=[{}]
    trial.original_sim_step=Mock()
    trial.apply(dict(joints=[-1.]*42,adhesion=[0.]*6))
    def capture(self,physics,obs,action):
        self.samples.append(dict(commanded_joints=list(action['joints'])))
    monkeypatch.setattr(study.recovery.RecoveryTrial,'capture',capture)
    trial.capture(None,None,dict(joints=[-1.]*42))
    assert trial.samples[-1]['commanded_joints'][5]==5.
    assert trial.samples[-1]['commanded_joints'][3]==-1.
    assert trial.samples[-1]['proposed_joints']==[-1.]*42


def test_audit_rejects_nonselected_mutation_and_reports_each_selected_exposure(baseline):
    arm=dict(samples=[dict(proposed_joints=None)])
    for row in baseline['samples'][1:]:
        applied=study.selected_action([-1.]*42,row['commanded_joints']).tolist()
        arm['samples'].append(dict(commanded_joints=applied,proposed_joints=[-1.]*42,adhesion=[0.]*6))
    good=study.command_audit(arm,baseline)
    assert good['passed'] and good['altered_transitions']==2 and good['first_altered_outgoing_transition']==0
    assert set(good['per_channel'].values())=={2}
    arm['samples'][1]['commanded_joints'][3]=99.
    assert not study.command_audit(arm,baseline)['passed']
    arm['samples'][1]['commanded_joints'][3]=-1.
    arm['samples'][1]['commanded_joints'][5]=99.
    assert not study.command_audit(arm,baseline)['passed']
    arm['samples'].pop()
    assert not study.command_audit(arm,baseline)['passed']


@pytest.mark.parametrize('peak,mean,label',[(-.25,-.25,'SELECTIVE_YOKING_REDUCES_RESPONSE'),
    (.25,.25,'SELECTIVE_YOKING_INCREASES_RESPONSE'),(-.25,.25,'MIXED_OR_UNRESOLVED'),
    (-.249,-.249,'MIXED_OR_UNRESOLVED')])
def test_inherited_m11_inclusive_rule_and_no_biological_claim(peak,mean,label):
    ref=dict(post_peak_orientation_deg=1.,post_mean_orientation_deg=1.,baseline_qualified=True,
             resolved_perturbation=True,relative_band_exited=True)
    selected=dict(ref,post_peak_orientation_deg=1.+peak,post_mean_orientation_deg=1.+mean)
    result=study.comparison(selected,ref)
    assert result['label']==label and result['active_balance_proven'] is False
    selected['baseline_qualified']=False
    assert 'SELECTED_BASELINE_NOT_QUALIFIED' in study.comparison(selected,ref)['interpretation_limits']


def test_dry_exclusive_output_and_no_tuning_knobs(tmp_path):
    path=tmp_path/'dry'
    assert study.main(['--output-dir',str(path)])==1
    raw=(path/'manifest.json').read_bytes()
    assert json.loads(raw)['run_status']=='NOT_RUN'
    with pytest.raises(FileExistsError): study.main(['--live','--output-dir',str(path)])
    assert (path/'manifest.json').read_bytes()==raw
    with pytest.raises(SystemExit): study.main(['--output-dir',str(path),'--channel','best'])


def test_shared_recorded_replay_explicitly_labels_selected_and_original(capsys):
    from malecns_backend.live import tibia_command_replay as replay
    clips={i:[dict(time_s=0.,qpos=[0.,0.,.6,1.,0.,0.,0.],joint_positions=[.1]*42)] for i in ('T_P','ON_P')}
    server=Mock()
    server.__enter__=Mock(return_value=server)
    server.__exit__=Mock(return_value=False)
    replay.replay_clips(clips,('T_P','ON_P'),replay.DESCRIPTIONS,loop=False,
        server_factory=lambda:server,clock=lambda:0.,sleep=lambda _:None)
    assert server.publish.call_count==2
    assert server.publish.call_args.args[0].joint_positions==tuple([.1]*42)
    output=capsys.readouterr().out
    assert 'Only six tibia' in output and 'other 14 motors' in output and 'NOT a physical jump' in output
    with pytest.raises(ValueError): replay.replay_clips(clips,('missing',),{})


def test_archived_tibia_evidence_analysis_and_actual_tcp():
    import socket
    from malecns_backend.live import tibia_command_replay as replay
    from malecns_backend.live.tactile_motor_yoke_replay import PoseServer,replay_snapshot
    from malecns_backend.live.protocol import validate_pose
    manifest,clips=replay.load_verified(study.ROOT/'docs/evidence/tibia-command-dissection-v1/manifest.json')
    assert manifest['run_status']=='COMPLETE'
    assert manifest['sources_before']==manifest['sources_after']==study.sources()
    assert manifest['evaluation']['active_balance_proven'] is False
    with PoseServer(port=0) as server:
        with socket.create_connection(('127.0.0.1',server.bound_port),timeout=2.) as client:
            client.settimeout(2.)
            with client.makefile('rb') as stream:
                assert json.loads(stream.readline())['type']=='hello'
                for number,identity in enumerate(('T_P','ON_P','Y_P')):
                    sample=clips[identity][-1]
                    assert server.publish(replay_snapshot(sample,20000),now=number+1.)
                    packet=json.loads(stream.readline())
                    validate_pose(packet)
                    assert packet['joint_positions']==sample['joint_positions']


@pytest.mark.parametrize('defect',[None,'inherited','sources','protocol','inventory'])
def test_versioned_audit_does_not_bypass_strict_inherited_or_identity_checks(monkeypatch,defect):
    own={'version':'locked'}
    inventory={n:dict(action_index=study.v3.V3_MOTOR.index(n)) for n in study.v3.V3_MOTOR}
    for n,i in study.SELECTED: inventory[n]['action_index']=i
    if defect=='inventory': inventory[study.SELECTED[0][0]]['action_index']=0
    arm=dict(samples=[],neural=[],sources_before=own,sources_after={} if defect=='sources' else own,
        initial=dict(motor_inventory=inventory),dissection_protocol={} if defect=='protocol' else study.PROTOCOL)
    response=dict(post_peak_orientation_deg=1.,post_mean_orientation_deg=1.,baseline_qualified=True,
                  resolved_perturbation=True,relative_band_exited=True)
    manifest=dict(protocol=study.PROTOCOL,sources_before=own,sources_after=own,
        prerequisite=dict(verified=True,recovery_prerequisite={},closed_loop_response=response,all_yoke_response=response),
        artifacts={i:dict(path=i,h=1) for i in study.CONDITIONS})
    monkeypatch.setattr(study,'sources',lambda:own)
    monkeypatch.setattr(study.recovery,'read_gzip',lambda _: (arm,{'h':1}))
    monkeypatch.setattr(study.recovery,'arm_audit',lambda *_:dict(checks={
        'source_integrity':False,'strict_existing_requirement':defect!='inherited'}))
    monkeypatch.setattr(study,'command_audit',lambda *_:dict(passed=True,altered_transitions=0))
    monkeypatch.setattr(study.recovery,'prefix_checks',lambda *_:dict(prefix=True))
    monkeypatch.setattr(study.yoke,'matching',lambda *_:True)
    monkeypatch.setattr(study.recovery,'support_counts',lambda _:[])
    monkeypatch.setattr(study.recovery.metrics,'trace',lambda *_:{})
    monkeypatch.setattr(study.recovery.metrics,'response',lambda *_:response)
    result=study.analyze('.',manifest,dict(neural=[]))
    assert result['integrity_passed'] is (defect is None)
    assert result['audits']['T_P']['inherited_recovery_audit']['checks']['source_integrity'] is False
    assert 'NO_SELECTED_COMMAND_INTERVENTION_EXPOSURE' in result['primary']['interpretation_limits']
