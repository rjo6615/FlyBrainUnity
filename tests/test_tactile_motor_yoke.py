"""Synthetic boundary defects are not evidence of physical stabilization."""
import copy
import json
from unittest.mock import Mock

import numpy as np
import pytest

from malecns_backend.live import tactile_motor_yoke as yoke


@pytest.fixture
def baseline(monkeypatch):
    monkeypatch.setattr(yoke.prior,'STEPS',2)
    return {'samples':[dict(commanded_joints=None,adhesion=None),
        dict(commanded_joints=[.1]*42,adhesion=[0.]*6),
        dict(commanded_joints=[.2]*42,adhesion=[0.]*6)]}


def test_exact_outgoing_command_and_input_immutability(baseline):
    trial=yoke.YokeTrial('Y_P',baseline)
    trial.samples=[{}]
    trial.original_sim_step=Mock(return_value='physics-result')
    action=dict(joints=np.full(42,9.),adhesion=np.zeros(6))
    assert trial.apply(action)=='physics-result'
    np.testing.assert_array_equal(trial.original_sim_step.call_args.args[0]['joints'],[.1]*42)
    np.testing.assert_array_equal(action['joints'],[9.]*42)
    assert trial.proposed==[9.]*42
    trial.samples.append({})
    trial.apply(action)
    np.testing.assert_array_equal(trial.original_sim_step.call_args.args[0]['joints'],[.2]*42)
    assert trial.withdraw is False


@pytest.mark.parametrize('defect',['size','nan','adhesion'])
def test_reject_corrupt_source_schedule(baseline,defect):
    if defect=='size': baseline['samples'][1]['commanded_joints']=[0.]
    if defect=='nan': baseline['samples'][1]['commanded_joints'][0]=float('nan')
    if defect=='adhesion': baseline['samples'][2]['adhesion'][0]=1.
    with pytest.raises(ValueError): yoke.commands(baseline)


@pytest.mark.parametrize('defect',['size','nan','adhesion','extra','past_end'])
def test_reject_invalid_proposed_action_without_physics(baseline,defect):
    trial=yoke.YokeTrial('Y_C',baseline)
    trial.samples=[{}]
    trial.original_sim_step=Mock()
    action=dict(joints=[0.]*42,adhesion=[0.]*6)
    if defect=='size': action['joints']=[0.]
    if defect=='nan': action['joints'][0]=float('nan')
    if defect=='adhesion': action['adhesion'][0]=1.
    if defect=='extra': action['unexpected']=1
    if defect=='past_end': trial.samples=[{}]*3
    with pytest.raises(ValueError): trial.apply(action)
    trial.original_sim_step.assert_not_called()


def test_complete_applied_schedule_and_exposure(baseline):
    arm=copy.deepcopy(baseline)
    arm['samples'][0]['proposed_joints']=None
    for s in arm['samples'][1:]: s['proposed_joints']=s['commanded_joints'].copy()
    assert yoke.command_audit(arm,baseline)==dict(passed=True,altered_transitions=0,first_altered_outgoing_transition=None)
    arm['samples'][2]['proposed_joints'][0]=9.
    assert yoke.command_audit(arm,baseline)==dict(passed=True,altered_transitions=1,first_altered_outgoing_transition=1)
    arm['samples'][1]['commanded_joints'][0]=9.
    assert not yoke.command_audit(arm,baseline)['passed']
    arm['samples'].pop()
    assert not yoke.command_audit(arm,baseline)['passed']


def test_matching_checks_full_contact_values_but_not_generated_namespace():
    row={k:[] for k in ('qpos','qvel','ctrl','joint_positions','telemetry_forces','tactile','commanded_joints','adhesion')}
    row['contacts']=[dict(geom1_name='1/LFTarsus5',geom2_name='ground',geom1_id=7,geom2_id=0,force=[1.])]
    ref={'samples':[row]}
    arm=copy.deepcopy(ref)
    arm['samples'][0]['contacts'][0]['geom1_name']='23/LFTarsus5'
    assert yoke.matching(arm,ref,1)
    assert not yoke.matching(arm,ref,2)
    arm['samples'][0]['contacts'][0]['geom1_id']=8
    assert not yoke.matching(arm,ref,1)


def test_dry_cli_exclusive_and_no_tuning(tmp_path):
    output=tmp_path/'dry'
    assert yoke.main(['--output-dir',str(output)])==1
    raw=(output/'manifest.json').read_bytes()
    assert json.loads(raw)['run_status']=='NOT_RUN'
    with pytest.raises(FileExistsError): yoke.main(['--live','--output-dir',str(output)])
    assert (output/'manifest.json').read_bytes()==raw
    with pytest.raises(SystemExit): yoke.main(['--output-dir',str(output),'--force','2'])


def test_capture_records_applied_not_proposed_action_and_detach_restores(baseline,monkeypatch):
    trial=yoke.YokeTrial('Y_P',baseline)
    trial.samples=[{}]
    trial.proposed=[9.]*42
    def capture(self,physics,obs,action):
        self.samples.append(dict(commanded_joints=list(action['joints'])))
    monkeypatch.setattr(yoke.prior.RecoveryTrial,'capture',capture)
    trial.capture(None,None,dict(joints=[9.]*42))
    assert trial.samples[-1]['commanded_joints']==[.1]*42
    assert trial.samples[-1]['proposed_joints']==[9.]*42
    trial.original_sim_step=Mock()
    trial.sim=Mock()
    monkeypatch.setattr(yoke.prior.RecoveryTrial,'detach',lambda _:None)
    trial.detach()
    assert trial.sim.step is trial.original_sim_step


def test_recorded_replay_exact_poses_and_explicit_condition_labels(capsys):
    from malecns_backend.live import tactile_motor_yoke_replay as replay
    clips={k:[dict(time_s=0.,qpos=[0.,0.,.6,1.,0.,0.,0.],joint_positions=[.2]*42)] for k in ('Y_P','ON_P')}
    server=Mock()
    server.__enter__=Mock(return_value=server)
    server.__exit__=Mock(return_value=False)
    replay.replay(clips,loop=False,server_factory=lambda:server,clock=lambda:0.,sleep=lambda _:None)
    assert server.publish.call_count==2
    assert server.publish.call_args.args[0].joint_positions==tuple([.2]*42)
    text=capsys.readouterr().out
    assert 'Y_P' in text and 'ON_P' in text and 'NOT a physical jump' in text
    with pytest.raises(ValueError): replay.replay(clips,speed=float('nan'))
    with pytest.raises(ValueError): replay.replay(clips,condition='unknown')


def test_archived_yoke_analysis_and_actual_tcp():
    import socket
    from malecns_backend.live import tactile_motor_yoke_replay as replay
    from malecns_backend.live.protocol import validate_pose
    manifest,clips=replay.load_verified(yoke.ROOT/'docs/evidence/tactile-motor-yoke-v1/manifest.json')
    assert manifest['sources_before']==manifest['sources_after']==yoke.sources()
    assert manifest['run_status']=='COMPLETE' and manifest['evaluation']['active_balance_proven'] is False
    with replay.PoseServer(port=0) as server:
        with socket.create_connection(('127.0.0.1',server.bound_port),timeout=2.) as client:
            client.settimeout(2.)
            with client.makefile('rb') as stream:
                assert json.loads(stream.readline())['type']=='hello'
                for number,identity in enumerate(('Y_P','ON_P')):
                    sample=clips[identity][-1]
                    snapshot=replay.replay_snapshot(sample,20000)
                    assert server.publish(snapshot,now=number+1.)
                    packet=json.loads(stream.readline())
                    validate_pose(packet)
                    assert packet['joint_positions']==sample['joint_positions']


@pytest.mark.parametrize('defect',[None,'inherited','new_sources','protocol'])
def test_versioned_source_audit_retains_every_other_requirement(monkeypatch,defect):
    own={'new':'locked'}
    arm=dict(samples=[],neural=[],sources_before=own,sources_after=own,yoke_protocol=yoke.PROTOCOL)
    if defect=='new_sources': arm['sources_after']={}
    if defect=='protocol': arm['yoke_protocol']={}
    manifest=dict(protocol=yoke.PROTOCOL,sources_before=own,sources_after=own,
        prerequisite=dict(verified=True,recovery_prerequisite={}),
        artifacts={i:dict(path=i,h=1) for i in yoke.CONDITIONS})
    monkeypatch.setattr(yoke,'sources',lambda:own)
    monkeypatch.setattr(yoke.prior,'read_gzip',lambda _: (arm,{'h':1}))
    monkeypatch.setattr(yoke.prior,'arm_audit',lambda *_:dict(checks={
        'source_integrity':False,'every_other_strict_check':defect!='inherited'}))
    monkeypatch.setattr(yoke,'command_audit',lambda *_:dict(passed=True,altered_transitions=0))
    monkeypatch.setattr(yoke.prior,'prefix_checks',lambda *_:dict(prefix=True))
    monkeypatch.setattr(yoke,'matching',lambda *_:True)
    monkeypatch.setattr(yoke.prior,'support_counts',lambda _:[])
    monkeypatch.setattr(yoke.prior.metrics,'trace',lambda *_:{})
    response=dict(post_peak_orientation_deg=1.,post_mean_orientation_deg=1.,post_peak_height_error_mm=0.,
                  baseline_qualified=True,resolved_perturbation=True,relative_band_exited=True)
    monkeypatch.setattr(yoke.prior.metrics,'response',lambda *_:response)
    result=yoke.analyze('.',manifest,dict(neural=[]),response)
    assert result['integrity_passed'] is (defect is None)
    assert result['audits']['Y_P']['inherited_recovery_audit']['checks']['source_integrity'] is False
    assert 'NO_MOTOR_COMMAND_INTERVENTION_EXPOSURE' in result['contrast']['interpretation_limits']
