"""Synthetic attribution/integrity cases; full live physics is a separate record."""
import copy
import gzip
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest

from malecns_backend.live import contact_context as context


def identity():
    sensor_names = [f'fly/{l}{s}' for l in context.LEGS for s in
                    ('Tibia', 'Tarsus1', 'Tarsus2', 'Tarsus3', 'Tarsus4', 'Tarsus5')]
    bodies = ['world'] + sensor_names
    names = ['ground', context.batch.single.SURFACE_NAME] + [f'fly/{l}Tarsus5' for l in context.LEGS]
    return dict(body_names=bodies, geom_names=names,
                geom_bodyid=[0, 0] + [i*6+6 for i in range(6)],
                sensor_placement_names=sensor_names, sensor_body_ids=list(range(1, 37)),
                tarsus5_body_ids={l: i*6+6 for i, l in enumerate(context.LEGS)},
                ground_geom_ids=[0, 1])


def pair(gid, *, other=0, reverse=False, frame=None, force=(0., 0., 2.)):
    table = identity()
    a, b = (gid, other) if reverse else (other, gid)
    return dict(geom1_id=a, geom1_name=table['geom_names'][a], geom2_id=b, geom2_name=table['geom_names'][b],
                frame=np.eye(3).tolist() if frame is None else frame, efc_address=0,
                local_force_torque=list(force) + [0., 0., 0.])


def sample(index=0, *, positive=False):
    forces = [[0., 0., 2.] if positive else [0., 0., 0.] for _ in context.LEGS]
    return dict(time_s=index*context.DT, contacts=[pair(i+2) for i in range(6)] if positive else [],
                body_forces=forces, telemetry_forces=copy.deepcopy(forces),
                qpos=[0., 0., 1., 1., 0., 0., 0.], qvel=[0.]*6,
                commanded_joints=[0.]*42 if index else None, adhesion=[0.]*6 if index else None,
                external_applied_max=0., generalized_applied_max=0.,
                configuration_sha256=context.digest(configuration()),
                observer_state_before_sha256='unchanged', observer_state_after_sha256='unchanged')


def configuration():
    return dict(timestep=context.DT, arrays=dict(pair_geom1=[0], eq_type=[]))


def report():
    return dict(protocol=copy.deepcopy(context.PROTOCOL), run_status='COMPLETE', prerequisite=dict(verified=True),
                sources_before={'synthetic': 'unchanged'}, sources_after={'synthetic': 'unchanged'},
                context=dict(identity=identity(), configuration=configuration(),
                             configuration_sha256=context.digest(configuration()),
                             inherited_surface_unchanged=True, adhesion_enabled=False),
                samples=[sample(), sample(1, positive=True), sample(2)])


def test_reconstruction_uses_frame_sign_ownership_and_separates_support_sources():
    s = sample()
    # Contact frame maps local +x to world +y; reversed geom ordering subtracts.
    s['contacts'] = [pair(2, frame=[[0., 1., 0.], [-1., 0., 0.], [0., 0., 1.]], force=(2., 0., 0.)),
                     pair(2, other=1, reverse=True, force=(0., 0., 3.))]
    s['body_forces'][0] = [0., 2., -3.]
    s['telemetry_forces'][0] = [0., 2., -3.]
    r = context.summarize_sample(s, identity())['LF']
    assert r['reconstruction_matches'] and r['telemetry_matches'] and r['correspondence']
    assert r['support_pairs'] == 2 and r['unselected_pairs'] == 0
    assert r['reconstructed_by_surface'] == {'0': [0., 2., 0.], '1': [0., 0., -3.]}


def test_other_body_contact_retained_without_misattributing_it_to_selected_foot():
    s = sample()
    s['contacts'] = [pair(3)]  # LM only
    s['body_forces'][1] = s['telemetry_forces'][1] = [0., 0., 2.]
    r = context.summarize_sample(s, identity())
    assert r['LF']['support_pairs'] == 0 and r['LF']['unselected_pairs'] == 0
    assert r['LM']['support_pairs'] == 1


def test_inactive_contact_is_retained_and_cannot_establish_force_correspondence():
    s = sample()
    c = pair(2)
    c.update(efc_address=-1, local_force_torque=[0.]*6)
    s['contacts'] = [c]
    r = context.summarize_sample(s, identity())['LF']
    assert r['support_pairs'] == 1 and r['reconstruction_matches']
    assert not r['correspondence']


def test_whole_synthetic_window_requires_clean_positive_and_negative(monkeypatch):
    monkeypatch.setattr(context, 'STEPS', 2)
    r = report()
    old = copy.deepcopy(r)
    evaluation = context.evaluate(r)
    assert evaluation['accepted'] and evaluation['accepted_legs'] == list(context.LEGS)
    assert evaluation['legs']['LF']['negative_samples'] == 2
    assert r == old
    json.dumps(evaluation, allow_nan=False)


@pytest.mark.parametrize('defect', [
    'ambiguous', 'other_geom_same_body', 'negative_force', 'positive_zero', 'reconstruction', 'telemetry',
    'no_negative', 'no_positive', 'truncated', 'shifted_schedule', 'different_dt', 'changed_context',
    'mutated_state', 'applied_force', 'applied_generalized', 'adhesion', 'nan', 'source',
    'identity', 'moving_ground', 'missing_ground', 'duplicate_geom', 'wrong_pair_name', 'wrong_pair_id',
    'invalid_frame', 'invalid_wrench', 'missing_prerequisite', 'partial', 'surface', 'equality',
])
def test_no_admission_on_entire_window_defects(monkeypatch, defect):
    monkeypatch.setattr(context, 'STEPS', 2)
    r = report()
    s = r['samples'][1]
    table = r['context']['identity']
    if defect == 'ambiguous': s['contacts'].append(pair(2, other=3))
    elif defect == 'other_geom_same_body':
        table['geom_names'].append('other_geom')
        table['geom_bodyid'].append(table['tarsus5_body_ids']['LF'])
        c = pair(2); c.update(geom2_id=8, geom2_name='other_geom'); s['contacts'].append(c)
    elif defect == 'negative_force': r['samples'][0]['telemetry_forces'][0] = [1., 0., 0.]
    elif defect == 'positive_zero': s['telemetry_forces'][0] = [0., 0., 0.]
    elif defect == 'reconstruction': s['body_forces'][0][0] = .1
    elif defect == 'telemetry': s['telemetry_forces'][0][0] = .1
    elif defect == 'no_negative':
        r['samples'] = [sample(i, positive=True) for i in range(3)]
    elif defect == 'no_positive': r['samples'] = [sample(i) for i in range(3)]
    elif defect == 'truncated': r['samples'].pop()
    elif defect == 'shifted_schedule':
        for value in r['samples']: value['time_s'] += 1.
    elif defect == 'different_dt': r['protocol']['physics_dt_s'] = .001
    elif defect == 'changed_context': s['configuration_sha256'] = 'modified'
    elif defect == 'mutated_state': s['observer_state_after_sha256'] = 'modified'
    elif defect == 'applied_force': s['external_applied_max'] = 1e-20
    elif defect == 'applied_generalized': s['generalized_applied_max'] = 1e-20
    elif defect == 'adhesion': s['adhesion'][0] = 1.
    elif defect == 'nan': s['qpos'][0] = float('nan')
    elif defect == 'source': r['sources_after']['synthetic'] = 'changed'
    elif defect == 'identity': table['sensor_body_ids'][5] = 5
    elif defect == 'moving_ground': table['geom_bodyid'][0] = 1
    elif defect == 'missing_ground': table['ground_geom_ids'].pop()
    elif defect == 'duplicate_geom': table['geom_names'][3] = 'other/LFTarsus5'
    elif defect == 'wrong_pair_name': s['contacts'][0]['geom1_name'] = 'not_ground'
    elif defect == 'wrong_pair_id': s['contacts'][0]['geom1_id'] = -1
    elif defect == 'invalid_frame': s['contacts'][0]['frame'][0][0] = 2.
    elif defect == 'invalid_wrench': s['contacts'][0]['local_force_torque'][0] = float('nan')
    elif defect == 'missing_prerequisite': r['prerequisite']['verified'] = False
    elif defect == 'partial': r['run_status'] = 'ERROR'
    elif defect == 'surface': r['context']['inherited_surface_unchanged'] = False
    elif defect == 'equality': r['context']['configuration']['arrays']['eq_type'] = [0]
    assert not context.evaluate(r)['accepted']


def test_actual_archived_prerequisite_rechecked_without_changing_locks():
    assert context.prerequisite()['accepted_legs'] == list(context.LEGS)
    with patch.object(context.gzip, 'decompress', return_value=b'corrupt'):
        with pytest.raises(RuntimeError, match='hash mismatch'): context.prerequisite()


def test_proxy_passes_action_and_result_unchanged_and_never_resets():
    action = {'joints': np.arange(42.), 'adhesion': np.zeros(6)}
    result = ({'contact_forces': np.zeros((36, 3))}, 0., False, False, {})
    sim, recorder = Mock(), Mock()
    sim.step.return_value = result
    proxy = context.ObservedSimulation(sim, 'physics', recorder)
    assert proxy.step(action) is result
    assert sim.step.call_args.args[0] is action
    recorder.capture.assert_called_once_with('physics', result[0], action)
    sim.reset.assert_not_called()
    proxy.close()
    sim.close.assert_called_once()


def test_capture_does_not_mutate_physics_observation_action_or_rng():
    model = SimpleNamespace()
    data = SimpleNamespace(qpos=np.arange(7.), qvel=np.arange(6.), qacc=np.zeros(6), ctrl=np.zeros(42),
                           cfrc_ext=np.zeros((37, 6)), xfrc_applied=np.zeros((37, 6)),
                           qfrc_applied=np.zeros(6), efc_force=np.zeros(0), time=0.)
    physics = SimpleNamespace(model=model, data=data)
    obs = {'contact_forces': np.zeros((36, 3), dtype=np.float32)}
    action = {'joints': np.arange(42.), 'adhesion': np.zeros(6)}
    recorder = context.PassiveRecorder()
    recorder.context = dict(identity=identity())
    before = copy.deepcopy((data, obs, action, np.random.get_state()))
    with patch.object(context.batch.single, '_pairs', return_value=()), \
            patch.object(context, 'configuration', return_value=configuration()):
        recorder.capture(physics, obs, action)
    assert recorder.samples[0]['observer_state_before_sha256'] == recorder.samples[0]['observer_state_after_sha256']
    for name in vars(data): np.testing.assert_array_equal(getattr(data, name), getattr(before[0], name))
    np.testing.assert_array_equal(obs['contact_forces'], before[1]['contact_forces'])
    np.testing.assert_array_equal(action['joints'], before[2]['joints'])
    np.testing.assert_array_equal(np.random.get_state()[1], before[3][1])


def test_dry_run_overwrite_protection_and_fixed_cli(tmp_path):
    output = tmp_path / 'dry.json.gz'
    assert context.main(['--output', str(output)]) == 1
    raw = output.read_bytes()
    r = json.loads(gzip.decompress(raw))
    assert r['run_status'] == 'NOT_RUN' and not r['evaluation']['accepted']
    assert r['protocol']['physics_steps'] == 20000 and r['protocol']['duration_s'] == 2.
    with patch.object(context, 'build_report') as build:
        with pytest.raises(FileExistsError): context.main(['--live', '--output', str(output)])
        build.assert_not_called()
    assert raw == output.read_bytes()
    with pytest.raises(SystemExit): context.main(['--output', str(output), '--duration-s', '1'])


def test_bounded_live_driver_retains_partial_error_and_closes(monkeypatch):
    monkeypatch.setattr(context, 'STEPS', 2)
    session = Mock()
    session.initialize.return_value = SimpleNamespace(time_ms=0.)
    session.step.side_effect = [SimpleNamespace(physics_transitions=1, neural_transitions=0), KeyboardInterrupt()]
    with patch('malecns_backend.live.headless.create_live_v3_session', return_value=session), \
            patch('malecns_backend.embodiment._windows_m7d_corrected_spontaneous_adapter._environment'):
        r = context.build_report(live=True, progress=lambda *_: None)
    assert r['run_status'] == 'ERROR' and 'KeyboardInterrupt' in r['error']
    assert not r['evaluation']['accepted']
    assert session.step.call_count == 2
    session.close.assert_called_once()
