"""Real small-graph neural boundary tests and synthetic paired-evidence tests."""
import copy
import gzip
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest

from malecns_backend.neural import MaleCNSBrain, NT_NAMES
from malecns_backend.embodiment.tactile_contact import TactilePopulation
from malecns_backend.embodiment.motor import MotorActivityObserver
from malecns_backend.live import tactile_boundary as boundary
from malecns_backend.live import matched_tactile_delivery as experiment
from malecns_backend.live import tactile_replay
from malecns_backend.live.protocol import pose, validate_pose


def small_trial(condition):
    n = 2270
    ids = np.arange(n, dtype=np.int64) + 10000
    data = SimpleNamespace(neuron_count=n, row_ptr=np.zeros(n+1, np.uint32), target_indices=np.empty(0, np.uint32),
        synapse_counts=np.empty(0, np.uint16), neuron_sizes=np.ones(n, np.float32), nt_signs=np.ones(n, np.float32),
        neurotransmitter_ids=np.ones(n, np.uint8), superclass_ids=np.zeros(n, np.uint8), superclasses=['central'],
        class_ids=np.zeros(n, np.uint16), classes=['other'], types=['x']*n, body_ids=ids,
        body_id_to_index={int(body):i for i, body in enumerate(ids)}, neurotransmitters=list(NT_NAMES))
    brain = MaleCNSBrain(data)
    pops = {}
    start = 0
    for leg, count in zip(boundary.LEGS, (151, 378, 394, 115, 428, 411)):
        indices = tuple(range(start, start+count))
        pops[leg] = TactilePopulation(leg, leg, tuple(map(int, ids[list(indices)])), indices)
        start += count
    trial = boundary.Trial(condition, populations=pops)
    trial.context = {}  # unit fixture, not an accepted physical context
    observer = MotorActivityObserver({'test_motor':[2269]})
    observer.reset(brain.spike_counts)
    channels = {'motor':dict(observer=observer, populations={'test_motor':(2269,)}, index=0, sign=1,
        decoder_mode='fixture', pipeline=SimpleNamespace(previous_physical_target=None))}
    before = boundary.neural_state_digest(brain)
    original = brain.step
    trial.attach(brain, channels, sensory_sources={'fixture':range(1877, 2269)})
    assert boundary.neural_state_digest(brain) == before
    return trial, brain, original


def step(trial, brain, tactile=(0,), proprio=(1877,)):
    brain.clear_external_drive()
    brain.set_external_drive(proprio, 2000.)
    trial.pending['LF'].update(tactile)
    return brain.step()


def test_only_delivery_gate_differs_with_real_neural_runtime_and_common_uniforms():
    a, ba, _ = small_trial('WITHHELD')
    b, bb, _ = small_trial('ENABLED')
    assert a.initial == b.initial
    step(a, ba); step(b, bb)
    assert a.neural[0]['eligible'] == b.neural[0]['eligible'] == [0, 1877]
    assert a.neural[0]['delivered'] == [1877]
    assert b.neural[0]['delivered'] == [0, 1877]
    assert a.neural[0]['pre_state_sha256'] == b.neural[0]['pre_state_sha256']
    assert a.neural[0]['sampling'] == b.neural[0]['sampling']
    assert int(ba.spike_counts[0]) == 0 and int(bb.spike_counts[0]) == 1
    for _ in range(12):
        step(a, ba); step(b, bb)
        assert a.neural[-1]['sampling']['uniforms_sha256'] == b.neural[-1]['sampling']['uniforms_sha256']
    assert a.initial['neural_config'] == b.initial['neural_config']


def test_actual_refractory_eligibility_is_used_in_both_arms_not_shadow_clock():
    for condition in experiment.CONDITIONS:
        trial, brain, _ = small_trial(condition)
        brain.refractory[0] = .1  # unavailable at entry even though decrement becomes negative
        step(trial, brain, proprio=())
        assert trial.neural[-1]['eligible'] == []
        assert trial.neural[-1]['delivered'] == []


def test_hooks_are_instance_local_restore_and_call_original_step_once():
    trial, brain, original = small_trial('ENABLED')
    other, plain, _ = small_trial('WITHHELD')
    trial.original_step = Mock(wraps=original)
    step(trial, brain)
    trial.original_step.assert_called_once_with()
    assert plain.time_ms == 0.
    trial.original_step = original
    trial.detach()
    assert brain.step == original
    other.detach()


def test_unexpected_rng_use_or_input_is_rejected():
    trial, brain, _ = small_trial('ENABLED')
    brain.rng.random()
    with pytest.raises(RuntimeError, match='RNG'): step(trial, brain)
    trial, brain, _ = small_trial('ENABLED')
    with pytest.raises(RuntimeError, match='proprioceptive'): step(trial, brain, proprio=(2269,))


def test_real_motor_observer_readout_is_checked():
    trial, brain, _ = small_trial('ENABLED')
    step(trial, brain)
    observer = trial.channels['motor']['observer']
    observer.update(brain.spike_counts, .5)
    trial.sample(brain)
    assert trial.neural[-1]['motor_readout_verified']
    observer.last_counts[0] += 1
    with pytest.raises(RuntimeError, match='readout'): trial.sample(brain)


@pytest.fixture
def synthetic_pair(monkeypatch):
    monkeypatch.setitem(experiment.PROTOCOL, 'physics_steps', 10)
    monkeypatch.setitem(experiment.PROTOCOL, 'neural_steps', 2)
    a, ba, _ = small_trial('WITHHELD')
    b, bb, _ = small_trial('ENABLED')
    report = dict(protocol=copy.deepcopy(experiment.PROTOCOL), prerequisite=dict(verified=True, configuration={}),
                  sources_before={'fixture':'same'}, sources_after={'fixture':'same'}, arms={})
    for trial, brain in ((a, ba), (b, bb)):
        for _ in range(2):
            step(trial, brain)
            row = trial.neural[-1]
            row['motor_readout_verified'] = True
            row['motor_telemetry'] = dict(delivered_external_sensory_events=row['delivered'],
                per_neuron_spike_increments={'motor':[0]}, raw_signed_contribution_rad={'motor':0.},
                commanded_joint_targets=[0.]*42)
        samples = [dict(time_s=i*.0001, qpos=[0.,0.,1.,1.,0.,0.,0.], qvel=[0.]*6, ctrl=[0.]*42,
                        joint_positions=[0.]*42, tactile={}, telemetry_forces=[[0.]*3]*6) for i in range(11)]
        report['arms'][trial.condition] = dict(run_status='COMPLETE', initial=trial.initial, neural=trial.neural,
            samples=samples, context=dict(configuration={}, physics_model_identity={'same':True}))
    # Physical attribution has its own tested evaluator; these are synthetic neural-boundary cases.
    monkeypatch.setattr(experiment.context, 'evaluate', lambda *_: dict(accepted=True, legs={l:dict(calibration_surface_positive_samples=0) for l in boundary.LEGS}))
    return report


def test_valid_delivery_with_null_motor_and_physics_is_valid_not_a_failure(synthetic_pair):
    r = experiment.evaluate(synthetic_pair)
    assert r['integrity_passed']
    assert r['outcome'] == 'DELIVERY_VERIFIED_NO_DOWNSTREAM_CHANGE'
    assert r['milestones']['first_eligible_tactile_ms'] == .5
    assert r['arms']['ENABLED']['tactile']['LF']['delivered'] == 1


@pytest.mark.parametrize('defect', ['leaked_delivery','lost_proprio','wrong_uniforms','initial','pre_state',
    'missing_step','mask','source','motor_readout','wrong_schedule','new_surface','noninput_mislabel'])
def test_invalid_pair_does_not_gain_integrity(synthetic_pair, defect, monkeypatch):
    r = synthetic_pair
    a, b = r['arms']['WITHHELD'], r['arms']['ENABLED']
    if defect == 'leaked_delivery': a['neural'][0]['delivered'].append(0)
    elif defect == 'lost_proprio': b['neural'][0]['delivered'].remove(1877)
    elif defect == 'wrong_uniforms': b['neural'][0]['sampling']['uniforms_sha256'] = 'wrong'
    elif defect == 'initial': b['initial']['neural_state_sha256'] = 'wrong'
    elif defect == 'pre_state': b['neural'][0]['pre_state_sha256'] = 'wrong'
    elif defect == 'missing_step': b['samples'].pop()
    elif defect == 'mask': b['neural'][0]['withheld_mask_sha256'] = 'wrong'
    elif defect == 'source': r['sources_after']['fixture'] = 'changed'
    elif defect == 'motor_readout': b['neural'][0]['motor_readout_verified'] = False
    elif defect == 'wrong_schedule': b['neural'][0]['sampling']['draws'] = 5
    elif defect == 'new_surface': monkeypatch.setattr(experiment.context, 'evaluate', lambda *_: dict(accepted=True, legs={'LF':dict(calibration_surface_positive_samples=1)}))
    elif defect == 'noninput_mislabel': b['neural'][0]['non_input_fired'] = [0]
    assert not experiment.evaluate(r)['integrity_passed']


def test_later_physical_divergence_is_an_outcome_not_automatic_failure(synthetic_pair):
    arm = synthetic_pair['arms']['ENABLED']
    arm['samples'][-1]['qpos'][0] = .01
    arm['samples'][-1]['tactile'] = {'changed':'after feedback'}
    r = experiment.evaluate(synthetic_pair)
    assert r['integrity_passed'] and r['outcome'] == 'PHYSICAL_DIVERGENCE_OBSERVED'


def test_dry_and_exclusive_output_do_not_construct_sessions(tmp_path):
    output = tmp_path/'dry.gz'
    with patch.object(experiment, 'prerequisites', return_value=dict(verified=True)), \
            patch.object(experiment, 'run_arm') as run:
        assert experiment.main(['--output', str(output)]) == 1
        before = output.read_bytes()
        with pytest.raises(FileExistsError): experiment.main(['--live', '--output', str(output)])
        run.assert_not_called()
    assert output.read_bytes() == before
    assert json.loads(gzip.decompress(before))['run_status'] == 'NOT_RUN'
    with pytest.raises(SystemExit): experiment.main(['--output', str(output), '--seed','2'])


def test_replay_uses_recorded_measured_pose_and_existing_protocol(synthetic_pair):
    synthetic_pair['evaluation'] = experiment.evaluate(synthetic_pair)
    sample = synthetic_pair['arms']['ENABLED']['samples'][0]
    snapshot = tactile_replay.replay_snapshot(sample, 0)
    validate_pose(pose('recorded',0,snapshot.time_ms/1000,snapshot.root_position_xyz,
                       snapshot.root_quaternion_wxyz,snapshot.joint_positions))
    server = Mock()
    server.__enter__ = Mock(return_value=server)
    server.__exit__ = Mock(return_value=False)
    tactile_replay.replay(synthetic_pair,'ENABLED',loop=False,server_factory=lambda:server,clock=lambda:1.,sleep=lambda _:None)
    assert server.publish.call_count == 11
    server.publish.reset_mock()
    tactile_replay.replay(synthetic_pair,'BOTH',loop=False,server_factory=lambda:server,clock=lambda:1.,sleep=lambda _:None)
    assert server.publish.call_count == 22


def test_arm_interruption_preserves_partial_trace_and_closes():
    trial = Mock(samples=[{'time_s':0.}], neural=[], context={'partial':True}, initial=None)
    session = Mock()
    session.initialize.return_value = SimpleNamespace(time_ms=0.)
    session.step.side_effect = KeyboardInterrupt()
    with patch.object(experiment, 'Trial', return_value=trial), \
            patch.object(experiment, 'create_session', return_value=session):
        result = experiment.run_arm('WITHHELD', lambda *_:None)
    assert result['run_status'] == 'ERROR' and 'KeyboardInterrupt' in result['error']
    assert result['samples'] == [{'time_s':0.}]
    session.close.assert_called_once()
    trial.detach.assert_called_once()


def test_both_arms_attempted_once_without_retry_on_failure():
    with patch.object(experiment, 'prerequisites', return_value={'verified':True}), \
            patch('malecns_backend.embodiment._windows_m7d_corrected_spontaneous_adapter._environment'), \
            patch.object(experiment.importlib.metadata, 'version', return_value='synthetic'), \
            patch.object(experiment, 'run_arm', side_effect=[{'run_status':'ERROR'}, {'run_status':'COMPLETE'}]) as run:
        result = experiment.build_report(live=True, progress=lambda *_:None)
    assert [call.args[0] for call in run.call_args_list] == list(experiment.CONDITIONS)
    assert run.call_count == 2 and result['run_status'] == 'INCOMPLETE'
    assert not result['evaluation']['integrity_passed']


def test_archived_pair_full_replay_and_source_hashes():
    folder = experiment.ROOT/'docs/evidence'
    manifest = json.loads((folder/'matched-tactile-checkpoint.json').read_text())
    packed = (folder/manifest['raw_artifact']).read_bytes()
    raw = gzip.decompress(packed)
    assert hashlib.sha256(packed).hexdigest() == manifest['gzip_sha256']
    assert hashlib.sha256(raw).hexdigest() == manifest['raw_json_sha256']
    report = json.loads(raw)
    assert report['sources_before'] == report['sources_after'] == experiment.source_hashes()
    assert report['evaluation'] == experiment.evaluate(report) == manifest['evaluation']
