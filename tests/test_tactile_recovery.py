"""Force/phase boundaries and descriptive recovery; synthetic cases are not physics."""
import copy
import gzip
import json
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import Mock

import numpy as np
import pytest

from malecns_backend.live import tactile_recovery as recovery
from malecns_backend.live import tactile_recovery_metrics as metrics
from malecns_backend.live.tactile_boundary import Trial
from malecns_backend.live import tactile_recovery_replay as recorded
from malecns_backend.live.protocol import pose,validate_pose


def force_arm(pushed=True):
    samples=[]
    for i in range(20001):
        vector=list(recovery.force_at_transition(pushed,i-1)) if i else [0.,0.,0.]
        applied=[] if not any(vector) else [dict(body_id=1,wrench=vector+[0.,0.,0.])]
        samples.append(dict(applied_body_wrenches=applied,external_applied_max=max(map(abs,vector)),generalized_applied_max=0.))
    return dict(context=dict(force_body=dict(id=1,name='fly/Thorax',frame='world',point='body COM',torque=[0.,0.,0.]),
        identity=dict(body_names=['world','fly/Thorax','fly/LFTarsus5'],tarsus5_body_ids={'LF':2})), samples=samples)


def test_force_pulse_reuses_exact_historical_schedule_and_sample_offset():
    arm=force_arm()
    active=[i for i,s in enumerate(arm['samples']) if s['applied_body_wrenches']]
    assert active==list(range(5001,5201))
    audit=recovery.force_audit(arm,'OFF_P')
    assert audit['passed'] and audit['active_applied_samples']==200
    np.testing.assert_allclose(audit['impulse_native_force_s'],[0.,.02048,0.],rtol=0,atol=1e-15)
    assert recovery.force_audit(force_arm(False),'OFF_C')['passed']


@pytest.mark.parametrize('defect',['early','late','wrong_body','wrong_axis','torque','hidden_force','generalized','frame','sensor_body'])
def test_wrong_or_unplanned_force_never_passes(defect):
    arm=force_arm()
    if defect=='early': arm['samples'][5000]=copy.deepcopy(arm['samples'][5001])
    elif defect=='late': arm['samples'][5201]=copy.deepcopy(arm['samples'][5200])
    elif defect=='wrong_body': arm['samples'][5001]['applied_body_wrenches'][0]['body_id']=2
    elif defect=='wrong_axis': arm['samples'][5001]['applied_body_wrenches'][0]['wrench'][:3]=[1.024,0.,0.]
    elif defect=='torque': arm['samples'][5001]['applied_body_wrenches'][0]['wrench'][4]=1e-10
    elif defect=='hidden_force': arm['samples'][1]['applied_body_wrenches']=[dict(body_id=2,wrench=[1.,0.,0.,0.,0.,0.])]
    elif defect=='generalized': arm['samples'][1]['generalized_applied_max']=1e-30
    elif defect=='frame': arm['context']['force_body']['frame']='body-local'
    elif defect=='sensor_body': arm['context']['identity']['tarsus5_body_ids']['LF']=1
    assert not recovery.force_audit(arm,'ON_P')['passed']


@pytest.mark.parametrize('identity,index,expected',[('OFF_C',999,'ENABLED'),('OFF_C',1000,'WITHHELD'),
    ('OFF_P',999,'ENABLED'),('OFF_P',1000,'WITHHELD'),('ON_P',1000,'ENABLED')])
def test_withdrawal_starts_only_after_last_pre_force_neural_boundary(identity,index,expected):
    trial=recovery.RecoveryTrial(identity)
    trial.neural=[{} for _ in range(index)]
    seen=[]
    def original(instance):
        seen.append(instance.condition)
        instance.neural.append({'from_original':True})
        return np.asarray([7])
    with patch.object(Trial,'step',original):
        assert trial.step().tolist()==[7]
    assert seen==[expected] and trial.neural[-1]['delivery_phase']==expected


def trajectories():
    count=20001
    base=dict(position=np.tile([0.,0.,.6],(count,1)),quaternion=np.tile([1.,0.,0.,0.],(count,1)),
        velocity=np.zeros((count,6)),up_z=np.ones(count),supports=np.full(count,6))
    pushed=copy.deepcopy(base)
    angle=np.deg2rad(10.)
    pushed['quaternion'][5001:7001]=[np.cos(angle/2),np.sin(angle/2),0.,0.]
    pushed['up_z']=metrics.up_z(pushed['quaternion'])
    return pushed,base


def test_sustained_return_needs_a_prior_exit_and_complete_hundred_ms_dwell():
    p,c=trajectories()
    r=metrics.response(p,c)
    assert r['resolved_perturbation'] and r['baseline_qualified']
    assert r['recovery_status']=='SUSTAINED_BAND_RETURN'
    assert r['recovery_entry_ms']==pytest.approx(700.1)
    assert r['recovery_confirmation_ms']==pytest.approx(800.1)


def test_no_band_exit_is_not_a_successful_recovery():
    _,c=trajectories()
    r=metrics.response(c,c)
    assert r['recovery_status']=='NO_BAND_EXIT'
    assert r['recovery_entry_ms'] is None and not r['resolved_perturbation']


@pytest.mark.parametrize('defect',['support','height','angular_speed','linear_speed','upright'])
def test_returning_orientation_alone_is_insufficient(defect):
    p,c=trajectories()
    if defect=='support': p['supports'][7001:]=2
    elif defect=='height': p['position'][7001:,2]=.2
    elif defect=='angular_speed': p['velocity'][7001:,3]=2.
    elif defect=='linear_speed': p['velocity'][7001:,0]=2.
    elif defect=='upright': p['up_z'][7001:]=0.
    assert metrics.response(p,c)['recovery_status']=='NOT_RECOVERED_IN_WINDOW'


def test_dwell_counts_transitions_not_only_samples_and_rejects_gaps():
    assert metrics.sustained_entry([True]*10,0,10) is None
    assert metrics.sustained_entry([True]*11,0,10)==0
    assert metrics.sustained_entry([True]*10+[False]+[True]*11,0,10)==11


def test_counterfactual_control_and_quaternion_sign_are_respected():
    p,c=trajectories()
    p['quaternion']*=-1.
    r=metrics.response(p,c)
    assert r['post_peak_orientation_deg']==pytest.approx(10.)
    # Identical perturbed/control trajectories give no resolved response.
    assert not metrics.response(p,p)['resolved_perturbation']


def test_angular_velocity_uses_a_common_world_frame():
    half=np.sqrt(.5)
    q=np.array([[1.,0.,0.,0.],[half,0.,0.,half]])
    local=np.array([[0.,1.,0.],[1.,0.,0.]])
    world=metrics.angular_velocity_world(q,local)
    np.testing.assert_allclose(world,[[0.,1.,0.],[0.,1.,0.]],atol=1e-15)
    np.testing.assert_allclose(metrics.angular_velocity_world(-q,local),world,atol=1e-15)


def test_baseline_qualification_and_directional_metrics_do_not_claim_balance():
    p,c=trajectories()
    c['supports'][4000:5001]=2
    on=metrics.response(p,c)
    off=copy.deepcopy(on)
    off['post_peak_orientation_deg']+=1.
    off['post_mean_orientation_deg']+=1.
    r=metrics.contrast(on,off)
    assert r['orientation_label']=='ATTENUATED_ORIENTATION_RESPONSE_WITH_TACTILE'
    assert r['active_balance_proven'] is False
    assert 'ON_BASELINE_NOT_QUALIFIED' in r['interpretation_limits']


def test_prefix_compares_actual_neural_physics_and_encoder_state(monkeypatch):
    monkeypatch.setattr(recovery,'START',1)
    monkeypatch.setattr(recovery,'WITHDRAW_INDEX',1)
    ref=dict(initial={'same':True},context={'physics_model_identity':'same'},
        samples=[dict(qpos=[0.],qvel=[0.],ctrl=[0.],joint_positions=[0.],telemetry_forces=[],tactile={}) for _ in range(2)],
        neural=[{'same':'neural'}])
    arm=copy.deepcopy(ref)
    arm['neural'][0]['delivery_phase']='ENABLED'
    assert all(recovery.prefix_checks(arm,ref).values())
    arm['samples'][1]['qvel']=[1.]
    assert not recovery.prefix_checks(arm,ref)['physical_prefix']


def test_exclusive_directory_dry_cli_and_no_tuning_knobs(tmp_path):
    output=tmp_path/'dry'
    assert recovery.main(['--output-dir',str(output)])==1
    before=(output/'manifest.json').read_bytes()
    with pytest.raises(FileExistsError): recovery.main(['--live','--output-dir',str(output)])
    assert (output/'manifest.json').read_bytes()==before
    assert json.loads(before)['run_status']=='NOT_RUN'
    with pytest.raises(SystemExit): recovery.main(['--output-dir',str(output),'--force','2'])


def test_raw_arm_write_preserves_partial_and_nonfinite_locations(tmp_path):
    path=tmp_path/'partial.gz'
    result={'run_status':'ERROR','samples':[{'qpos':[float('nan')]}]}
    metadata=recovery.write_arm(path,result)
    report,actual=recovery.read_gzip(path)
    assert report['run_status']=='ERROR' and report['samples'][0]['qpos']==[None]
    assert report['nonfinite_measurement_paths']==['evidence.samples[0].qpos[0]']
    assert all(metadata[k]==v for k,v in actual.items())
    with pytest.raises(FileExistsError): recovery.write_arm(path,result)


def test_versioned_force_requirement_replaces_only_the_old_no_force_flag(monkeypatch):
    arm=force_arm()
    arm.update(run_status='COMPLETE',protocol=copy.deepcopy(recovery.PROTOCOL),
               sources_before={'fixture':'same'},sources_after={'fixture':'same'},nonfinite_measurement_paths=[])
    arm['context']['configuration']={}
    inventory={}
    start=0
    for leg,count in zip(recovery.context.LEGS,(151,378,394,115,428,411)):
        inventory[leg]=dict(dense_indices=list(range(start,start+count)),body_ids=list(range(start,start+count)))
        start+=count
    arm['initial']=dict(external_schedule=list(range(2269)),tactile_inventory=inventory)
    mask=recovery.context.digest(list(range(1877)))
    empty=recovery.context.digest([])
    arm['neural']=[]
    for i in range(4000):
        off=i>=1000
        delivered=[1877] if off else [0,1877]
        arm['neural'].append(dict(time_ms=(i+1)*.5,offered_tactile={l:[0] if l=='LF' else [] for l in inventory},
            offered_proprio=[1877],eligible=[0,1877],delivered=delivered,withheld_mask_sha256=mask if off else empty,
            delivery_phase='WITHHELD' if off else 'ENABLED',sampling=dict(draws=2269,eligible_indices=[0,1877]),
            motor_readout_verified=True,non_input_fired=[],fired=delivered,
            motor_telemetry=dict(delivered_external_sensory_events=delivered,commanded_joint_targets=[0.]*42)))
    leg=dict(positive_samples=1,negative_samples=1,ambiguous_samples=0,force_disagreements=0,
             reconstruction_disagreements=0,telemetry_disagreements=0,calibration_surface_positive_samples=0)
    legacy=dict(accepted=False,checks=dict(no_external_forcing=False,unchanged_strict_requirement=True),
                legs={l:leg.copy() for l in inventory})
    monkeypatch.setattr(recovery.context,'evaluate',lambda *_:copy.deepcopy(legacy))
    monkeypatch.setattr(recovery,'sources',lambda:{'fixture':'same'})
    info={'earlier':{'configuration':{}},'verified':True}
    good=recovery.arm_audit(arm,'OFF_P',info)
    assert good['passed'] and not good['legacy_no_force_audit']['accepted']
    assert good['legacy_no_force_audit']['checks']['no_external_forcing'] is False
    legacy['checks']['unchanged_strict_requirement']=False
    assert not recovery.arm_audit(arm,'OFF_P',info)['passed']
    legacy['checks']['unchanged_strict_requirement']=True
    arm['neural'][999]['delivered']=[1877]  # withdrawal one tick too early
    assert not recovery.arm_audit(arm,'OFF_P',info)['checks']['phase_gate']


def test_recorded_replay_labels_resets_and_streams_exact_measured_poses(capsys):
    samples=[dict(time_s=i*.0001,qpos=[i*.01,0.,.6,1.,0.,0.,0.],joint_positions=[i*.001]*42) for i in range(3)]
    manifest=dict(artifacts={i:dict(path=f'{i}.json.gz') for i in recovery.FRESH},
                  evaluation=dict(integrity_passed=True,contrast={'active_balance_proven':False}))
    server=Mock()
    server.__enter__=Mock(return_value=server)
    server.__exit__=Mock(return_value=False)
    with patch.object(recorded.recovery,'read_gzip',return_value=({'samples':samples},{})):
        recorded.replay('manifest.json',manifest,{'samples':samples},'PUSHED',loop=False,
                        server_factory=lambda:server,clock=lambda:0.,sleep=lambda _:None)
    assert server.publish.call_count==6
    last=server.publish.call_args.args[0]
    assert last.joint_positions==tuple(samples[-1]['joint_positions'])
    assert last.root_position_xyz==tuple(samples[-1]['qpos'][:3])
    validate_pose(pose('recorded',0,last.time_ms/1000,last.root_position_xyz,last.root_quaternion_wxyz,last.joint_positions))
    output=capsys.readouterr().out
    assert 'OFF_P' in output and 'ON_P' in output and 'NOT a simulated jump' in output


def test_replay_refuses_unverified_manifest_and_invalid_speed():
    with pytest.raises(ValueError): recorded.replay('manifest.json',{'evaluation':{}},{},'ALL')
    with pytest.raises(ValueError): recorded.replay('manifest.json',{}, {},'PUSHED',speed=float('nan'))


def test_archived_recovery_full_analysis_and_actual_pose_tcp():
    import socket
    path=recovery.ROOT/'docs/evidence/tactile-recovery-v1/manifest.json'
    manifest,baseline=recorded.load_verified(path)
    assert manifest['run_status']=='COMPLETE'
    assert manifest['sources_before']==manifest['sources_after']==recovery.sources()
    assert manifest['evaluation']['active_balance_proven'] is False
    with recorded.PoseServer(port=0) as server:
        with socket.create_connection(('127.0.0.1',server.bound_port),timeout=2.) as client:
            client.settimeout(2.)
            with client.makefile('rb') as stream:
                assert json.loads(stream.readline())['type']=='hello'
                for index in (0,len(baseline['samples'])-1):
                    snapshot=recorded.replay_snapshot(baseline['samples'][index],index)
                    assert server.publish(snapshot,now=float(index))
                    packet=json.loads(stream.readline())
                    validate_pose(packet)
                    assert packet['joint_positions']==list(snapshot.joint_positions)
