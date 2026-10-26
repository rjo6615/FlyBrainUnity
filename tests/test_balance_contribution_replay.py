"""Saved-pose projection and existing transport glue; no native/CNS model."""
import copy
import json
from unittest.mock import patch

import pytest

from malecns_backend.live import balance_contribution_replay as r
from malecns_backend.live.protocol import JOINT_NAMES, pose, validate_pose


def arm():
    qpos = [0., 1., 2., 1., 0., 0., 0.] + [i/100 for i in range(42)]
    rows = [dict(coordinate=n, action_index=i, qpos_range=[7+41-i, 8+41-i]) for i,n in enumerate(JOINT_NAMES)]
    return dict(run_status='COMPLETE', context=dict(free_root=dict(qpos_address=0, dof_address=0),
        native_inventory=dict(rows=rows, nq=49)),
        samples=[dict(time_s=i*.0001, qpos=qpos) for i in range(20001)])


def report():
    return dict(evaluation=dict(accepted=True, unity_replay_eligible=True,
        behavior=dict(primary_label='MIXED_OR_UNRESOLVED', independent_balance_proven=False)))


def test_projection_uses_actual_permuted_addresses_in_canonical_order():
    result = r.pose_only(arm())
    assert len(result) == 20001
    assert list(result[0]['joint_positions']) == [i/100 for i in range(41,-1,-1)]
    assert result[-1]['time_s'] == 2. and list(result[0]['qpos']) == [0.,1.,2.,1.,0.,0.,0.]
    snap = r.replay_snapshot(result[-1], 20000)
    packet = pose('saved-test', 20000, snap.time_ms/1000, snap.root_position_xyz,
                  snap.root_quaternion_wxyz, snap.joint_positions)
    validate_pose(packet)
    assert packet['root_quaternion_wxyz'] == [1.,0.,0.,0.]


@pytest.mark.parametrize('corruption', ['order','duplicate','address','clock','nonfinite','incomplete','root'])
def test_corrupt_pose_inputs_rejected(corruption):
    a = arm()
    if corruption == 'order': a['context']['native_inventory']['rows'][0]['coordinate'] = 'wrong'
    if corruption == 'duplicate': a['context']['native_inventory']['rows'][0]['qpos_range'] = [47,48]
    if corruption == 'address': a['context']['native_inventory']['rows'][0]['qpos_range'] = [0,1]
    if corruption == 'clock': a['samples'][-1]['time_s'] = 1.9
    if corruption == 'nonfinite': a['samples'][0]['qpos'] = [float('nan')]*49
    if corruption == 'incomplete': a['samples'].pop()
    if corruption == 'root': a['context']['free_root']['qpos_address'] = 1
    with pytest.raises(ValueError): r.pose_only(a)


def test_rejected_saved_evaluation_never_loads_pose_clips(tmp_path):
    (tmp_path/'report.json').write_text(json.dumps(report()))
    with patch.object(r.experiment, 'evaluate', return_value=dict(accepted=False, unity_replay_eligible=False)), patch.object(
            r.experiment, 'read_arm', side_effect=AssertionError('must not display failed evidence')):
        with pytest.raises(ValueError, match='four-arm integrity'): r.load_verified(tmp_path)


def test_valid_null_saved_result_is_replayable_without_behavior_success(tmp_path):
    saved = report()
    saved['arm_artifacts'] = {c:dict(path=c+'.json.gz') for c in r.experiment.base.CONDITIONS}
    (tmp_path/'report.json').write_text(json.dumps(saved))
    with patch.object(r.experiment, 'evaluate', return_value=saved['evaluation']), patch.object(
            r.experiment, 'read_arm', side_effect=lambda *args: arm()):
        result, clips = r.load_verified(tmp_path)
    assert result == saved and list(clips) == list(r.experiment.base.CONDITIONS)


def test_existing_snapshot_and_transport_are_used_for_all_saved_states(capsys):
    clips = {'WP':r.pose_only(arm())}
    sent, sleeps = [], []
    current = [0.]
    class Server:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def publish(self, snapshot, **kwargs): sent.append(snapshot)
    def sleep(delay): sleeps.append(delay); current[0] += delay
    r.replay(report(), clips, 'WP', speed=.1, loop=False, server_factory=Server,
             clock=lambda:current[0], sleep=sleep)
    assert len(sent) == 20001 and sent[-1].time_ms == 2000.
    assert sent[-1].diagnostics['neural_transition_count'] == 4000
    assert sum(sleeps) == pytest.approx(20.)
    output = capsys.readouterr().out
    assert 'tactile OFF' in output and 'decoder input withdrawn' in output
    assert 'recorded thorax pulse starts' in output and 'recorded thorax pulse ends' in output


@pytest.mark.parametrize('speed',[0.,-1.,2.,float('nan')])
def test_invalid_speed_is_rejected_before_opening_transport(speed):
    with pytest.raises(ValueError, match='display speed'):
        r.replay(report(), {}, speed=speed, server_factory=lambda:pytest.fail('opened transport'))


def test_inconclusive_report_never_opens_server():
    saved = report(); saved['evaluation']['accepted'] = False
    with pytest.raises(ValueError, match='integrity-gated'):
        r.replay(saved, {}, server_factory=lambda:pytest.fail('opened transport'))
