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
