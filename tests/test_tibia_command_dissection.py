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
