"""Complement-boundary implementation checks; synthetic tests are not physics."""
import json
from unittest.mock import Mock

import numpy as np
import pytest

from malecns_backend.live import complement_command_dissection as study


@pytest.fixture
def baseline(monkeypatch):
    monkeypatch.setattr(study.recovery,'STEPS',2)
    return dict(samples=[dict(commanded_joints=None,adhesion=None),
        dict(commanded_joints=list(np.arange(42,dtype=float)),adhesion=[0.]*6),
        dict(commanded_joints=list(np.arange(42,dtype=float)+100),adhesion=[0.]*6)])


def test_exact_complement_partition_and_only_selected_actions_change():
    assert tuple(i for _,i in study.SELECTED)==(3,10,17,31,38,4,11,18,25,32,39,24,6,27)
    selected={n for n,_ in study.SELECTED}
    tibia={n for n,_ in study.tibia.SELECTED}
    assert len(selected)==14 and not selected&tibia and selected|tibia==set(study.v3.V3_MOTOR)
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


@pytest.mark.parametrize('proposed,archived',[([0.],[0.]*42),([0.]*42,[0.]),([float('nan')]*42,[0.]*42),([0.]*42,[float('inf')]*42)])
def test_invalid_vectors_rejected(proposed,archived):
    with pytest.raises(ValueError): study.selected_action(proposed,archived)


def test_apply_time_index_and_original_tibia_proposals_preserved(baseline):
    trial=study.ComplementTrial('C_P',baseline)
    trial.samples=[{}]
    trial.original_sim_step=Mock(return_value='native-result')
    action=dict(joints=[-1.]*42,adhesion=[0.]*6)
    assert trial.apply(action)=='native-result'
    expected=study.selected_action(action['joints'],baseline['samples'][1]['commanded_joints'])
    np.testing.assert_array_equal(trial.original_sim_step.call_args.args[0]['joints'],expected)
    assert action['joints']==[-1.]*42 and trial.proposed==[-1.]*42
    for _,i in study.tibia.SELECTED: assert trial.applied['joints'][i]==-1.
    trial.samples.append({})
    trial.apply(action)
    assert trial.applied['joints'][3]==103.


@pytest.mark.parametrize('defect',['adhesion','extra','past_end'])
def test_invalid_boundary_never_calls_physics(baseline,defect):
    trial=study.ComplementTrial('C_C',baseline)
    trial.samples=[{}]
    trial.original_sim_step=Mock()
    action=dict(joints=[0.]*42,adhesion=[0.]*6)
    if defect=='adhesion': action['adhesion'][0]=1.
    if defect=='extra': action['extra']=1
    if defect=='past_end': trial.samples=[{}]*3
    with pytest.raises(ValueError): trial.apply(action)
    trial.original_sim_step.assert_not_called()


def test_capture_preserves_proposal_and_records_applied_selected_action(baseline,monkeypatch):
    trial=study.ComplementTrial('C_P',baseline)
    trial.samples=[{}]
    trial.original_sim_step=Mock()
    trial.apply(dict(joints=[-1.]*42,adhesion=[0.]*6))
    def capture(self,physics,obs,action):
        self.samples.append(dict(commanded_joints=list(action['joints'])))
    monkeypatch.setattr(study.recovery.RecoveryTrial,'capture',capture)
    trial.capture(None,None,dict(joints=[-1.]*42))
    assert trial.samples[-1]['commanded_joints'][3]==3.
    assert trial.samples[-1]['commanded_joints'][5]==-1.
    assert trial.samples[-1]['proposed_joints']==[-1.]*42


def test_audit_rejects_tibia_or_selected_mutation_and_reports_per_channel(baseline):
    arm=dict(samples=[dict(proposed_joints=None)])
    for row in baseline['samples'][1:]:
        arm['samples'].append(dict(commanded_joints=study.selected_action([-1.]*42,row['commanded_joints']).tolist(),
            proposed_joints=[-1.]*42,adhesion=[0.]*6))
    good=study.command_audit(arm,baseline)
    assert good['passed'] and good['altered_transitions']==2 and good['first_altered_outgoing_transition']==0
    assert len(good['per_channel'])==14 and set(good['per_channel'].values())=={2}
    arm['samples'][1]['commanded_joints'][5]=99.
    assert not study.command_audit(arm,baseline)['passed']
    arm['samples'][1]['commanded_joints'][5]=-1.
    arm['samples'][1]['commanded_joints'][3]=99.
    assert not study.command_audit(arm,baseline)['passed']
    arm['samples'].pop()
    assert not study.command_audit(arm,baseline)['passed']


@pytest.mark.parametrize('peak,mean,label',[(-.25,-.25,'SELECTIVE_YOKING_REDUCES_RESPONSE'),
    (.25,.25,'SELECTIVE_YOKING_INCREASES_RESPONSE'),(-.25,.25,'MIXED_OR_UNRESOLVED'),(-.249,-.249,'MIXED_OR_UNRESOLVED')])
def test_inclusive_m11_rule_and_limits(peak,mean,label):
    ref=dict(post_peak_orientation_deg=1.,post_mean_orientation_deg=1.,baseline_qualified=True,
             resolved_perturbation=True,relative_band_exited=True)
    selected=dict(ref,post_peak_orientation_deg=1.+peak,post_mean_orientation_deg=1.+mean)
    result=study.comparison(selected,ref)
    assert result['label']==label and result['active_balance_proven'] is False
    selected['baseline_qualified']=False
    assert 'SELECTED_BASELINE_NOT_QUALIFIED' in study.comparison(selected,ref)['interpretation_limits']


def test_exclusive_dry_cli_and_no_selection_tuning(tmp_path):
    path=tmp_path/'dry'
    assert study.main(['--output-dir',str(path)])==1
    raw=(path/'manifest.json').read_bytes()
    assert json.loads(raw)['run_status']=='NOT_RUN'
    with pytest.raises(FileExistsError): study.main(['--live','--output-dir',str(path)])
    assert (path/'manifest.json').read_bytes()==raw
    with pytest.raises(SystemExit): study.main(['--output-dir',str(path),'--channel','winner'])
