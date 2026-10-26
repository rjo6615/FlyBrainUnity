"""Synthetic engineering checks only; no native model or full CNS experiment."""
from array import array
import copy
from dataclasses import asdict
import importlib.abc
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from malecns_backend.live import balance_contribution as b
from malecns_backend.neural import MaleCNSBrain, ModelConfig


def names():
    return tuple(r['name'] for r in b.design()['motors'])


def command_arm(condition='WP', raw_value=.25):
    """Synthetic commands drive max offsets, independent of neural biology."""
    motor = {r['name']: dict(action_index=r['action_index'], safety=asdict(b.MotorSafety()))
             for r in b.design()['motors']}
    pipes = {n: b.MatchedControlPipeline(True, b.MotorSafety()) for n in motor}
    neural, proposals = [], {0: [0.] * 42}
    for t in range(1, 4001):
        raw = dict.fromkeys(motor, raw_value)
        gated = b.gated(raw, condition, t, tuple(motor))
        row = dict(tick=t, applied=b.command_is_applied(t), raw=raw, gated=gated, previous={}, pipeline={})
        commands = [0.] * 42
        for n, p in pipes.items():
            row['previous'][n] = p.previous_physical_target
            cf = b.MatchedControlPipeline(True, p.safety)
            cf.previous_physical_target = p.previous_physical_target
            enabled = cf.update(0., raw[n], .0005)
            result = p.update(0., gated[n], .0005)
            row['pipeline'][n] = dict(asdict(result), enabled_counterfactual_target=enabled.actuator_command)
            commands[motor[n]['action_index']] = result.actuator_command
        row['telemetry'] = dict(commanded_joint_targets=commands, raw_signed_contribution_rad=raw,
                                final_contribution_rad=gated)
        proposals[t * 5] = commands
        neural.append(row)
    samples = []
    for i in range(20001):
        applied = proposals[((i - 1) // 5) * 5] if i else None
        samples.append(dict(proposed_commands=proposals[(i // 5) * 5], commanded_joints=applied,
                            adhesion=[0.] * 6 if i else None, ctrl=applied + [0.] * 6 if i else [0.] * 48))
    return dict(condition=condition, initial=dict(motors=motor, baseline=[0.] * 42), neural=neural,
                samples=samples, context=dict(native_inventory=dict(rows=[dict(actuator_id=i, action_index=i) for i in range(42)])))


def small_brain():
    n = 400
    data = SimpleNamespace(neuron_count=n, row_ptr=array('I', [0] * (n + 1)),
        target_indices=array('I'), synapse_counts=array('H'), neuron_sizes=array('f', [1.] * n),
        nt_signs=array('f', [1.] * n), neurotransmitter_ids=array('B', [1] * n),
        superclass_ids=array('B', [0] * n), superclasses=['central'], class_ids=array('H', [0] * n),
        classes=['other'], types=['fixture'] * n, body_ids=array('q', range(1000, 1000 + n)),
        body_id_to_index={1000 + i: i for i in range(n)})
    return MaleCNSBrain(data, ModelConfig())


def null_report():
    """Full 80,004-state synthetic null; never claimed as simulated physics."""
    arm = command_arm('NC', raw_value=0.)
    sensors = [f'fly/{l}{s}' for l in b.context.LEGS for s in
               ('Tibia', 'Tarsus1', 'Tarsus2', 'Tarsus3', 'Tarsus4', 'Tarsus5')]
    table = dict(body_names=['world'] + sensors + ['fly/Thorax'],
        geom_names=['ground', b.context.batch.single.SURFACE_NAME] + [f'fly/{l}Tarsus5' for l in b.context.LEGS],
        geom_bodyid=[0, 0] + [i * 6 + 6 for i in range(6)], sensor_placement_names=sensors,
        sensor_body_ids=list(range(1, 37)), tarsus5_body_ids={l: i * 6 + 6 for i, l in enumerate(b.context.LEGS)},
        ground_geom_ids=[0, 1])
    config = dict(timestep=.0001)
    arm['context'].update(identity=table, configuration=config, configuration_sha256=b.context.digest(config),
                          adhesion_enabled=False, inherited_surface_unchanged=True, thorax_body_id=37)
    arm['context']['native_inventory'].update(nq=49, nv=48)
    arm.update(run_status='COMPLETE', initialization_operations={'synthetic_fixture': 1})
    for i, sample in enumerate(arm['samples']):
        sample.update(time_s=i * .0001, qpos=[0., 0., 1., 1., 0., 0., 0.] + [0.] * 42, qvel=[0.] * 48,
            contacts=[], body_forces=[[0.] * 3] * 6, telemetry_forces=[[0.] * 3] * 6,
            xfrc_applied=[[0.] * 6] * 38, qfrc_applied=[0.] * 48,
            external_applied_max=0., generalized_applied_max=0.,
            configuration_sha256=b.context.digest(config), observer_state_before_sha256='unchanged',
            observer_state_after_sha256='unchanged')
    brain = small_brain(); brain.reset(1)
    arm['initial']['rng_state'] = copy.deepcopy(brain.rng.bit_generator.state)
    brain.configure_external_rng_schedule(np.arange(392))
    from malecns_backend.embodiment.proprioceptive_activation import proprio_rngs
    local = proprio_rngs(1)
    arm['initial']['proprio_rng_state'] = {l: copy.deepcopy(r.bit_generator.state) for l, r in local.items()}
    partitions = dict(zip(b.context.LEGS, np.array_split(np.arange(392), 6)))
    arm['initial']['encoder_state'] = {l: dict(dense_indices=indices.tolist()) for l, indices in partitions.items()}
    arm['initial']['external_schedule'] = list(range(392))
    for tick, row in enumerate(arm['neural'], 1):
        brain.step()
        for l, r in local.items(): r.random(len(partitions[l]))
        row.update(time_ms=tick * .5, rng_indices=list(range(392)), draws=392, offered=[], eligible=[], delivered=[],
            fired=[], pre_state_sha256='synthetic', post_state_sha256='synthetic', encoder_state={},
            rng_state=copy.deepcopy(brain.rng.bit_generator.state),
            uniforms_sha256=b.array_digest(brain._last_external_rng_uniforms), readout_verified=True,
            proprio_rng_state={l: copy.deepcopy(r.bit_generator.state) for l, r in local.items()})
        row['telemetry'].update(scheduled_sensory_candidate_events=[], delivered_external_sensory_events=[],
                                encoded_sensory_rates={l: [0.] * len(v) for l, v in partitions.items()})
    arms = {}
    for c in b.CONDITIONS:
        arms[c] = dict(arm, condition=c, samples=[dict(s) for s in arm['samples']])
        if c.endswith('P'):
            for i in range(5001, 5201):
                s = arms[c]['samples'][i]
                s['xfrc_applied'] = [[0.] * 6 for _ in range(38)]
                s['xfrc_applied'][37][1] = 1.024
                s['external_applied_max'] = 1.024
    sources = b.source_hashes()
    return dict(design=b.design(), preflight=dict(verified=True), sources_before=sources,
                sources_after=sources, arms=arms)


class BoundaryTests(unittest.TestCase):
    def test_session_factory_reuses_frozen_kernel_and_has_no_final_gate(self):
        trial = b.Trial('WP')
        from malecns_backend.embodiment import _windows_m8_live_condition as kernel
        from malecns_backend.embodiment import live_v3_motor_interface as v3
        with patch.object(kernel, 'create_scientific_session', return_value=object()) as factory:
            result = b.create_session(trial, {'synthetic': True}, [])
        kw = factory.call_args.kwargs
        self.assertTrue(kw['proprioception_only']); self.assertTrue(kw['fixed_initial_baseline'])
        self.assertEqual(kw['motor_channel_names'], v3.V3_MOTOR)
        self.assertNotIn('final_contribution_gate', kw)
        self.assertIs(kw['contribution_gate'].__self__, trial)
        self.assertIs(kw['external_force_by_transition'], b.force)
        self.assertIs(trial.session, result)

    def test_interrupted_arm_retains_partial_samples_and_closes(self):
        closed = []
        class FakeTrial:
            def __init__(self, condition):
                self.samples, self.neural = [], []
                self.context, self.initial, self.brain = {}, {}, None
            def state_boundary(self): self.samples.append({'synthetic': len(self.samples)})
            def detach(self): closed.append('detach')
        class FakeSession:
            def initialize(self): return SimpleNamespace(time_ms=0.)
            def step(self, **kwargs):
                if hasattr(self, 'stepped'): raise KeyboardInterrupt('synthetic interruption')
                self.stepped = True
                return SimpleNamespace(physics_transitions=1, neural_transitions=0)
            def close(self): closed.append('close')
        with patch.object(b, 'Trial', FakeTrial), patch.object(b, 'create_session', return_value=FakeSession()):
            result = b.run_arm('NC', {}, [], progress=lambda *a, **k: None)
        self.assertEqual(result['run_status'], 'ERROR')
        self.assertIn('KeyboardInterrupt', result['error'])
        self.assertEqual(len(result['samples']), 2)
        self.assertEqual(closed, ['close', 'detach'])

    def test_preflight_forbids_native_imports_and_model_construction(self):
        class Forbid(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, *args):
                if fullname.split('.')[0] in ('flygym', 'mujoco', 'dm_control'):
                    raise AssertionError('forbidden native import: ' + fullname)
        guard = Forbid()
        sys.meta_path.insert(0, guard)
        from malecns_backend.embodiment import remaining_leg_admission_audit as audit
        from malecns_backend.embodiment import _windows_m7_spontaneous_locomotion_adapter as old
        from malecns_backend.embodiment import full_leg_interface as full
        try:
            with patch.object(audit, 'build', side_effect=AssertionError('live audit forbidden')), patch.object(
                    old, '_inventory', side_effect=AssertionError('extra inventory forbidden')), patch.object(
                    full, 'enumerate_live_actuators', side_effect=AssertionError('extra model forbidden')), patch.object(
                    MaleCNSBrain, '__init__', side_effect=AssertionError('CNS constructor forbidden')):
                result = b.preflight()
            self.assertEqual(result['native_constructions'], 0)
            self.assertTrue(result['checks']['design'])
            self.assertTrue(result['checks']['original_neural_data'], result['errors'])
        finally:
            sys.meta_path.remove(guard)

    def test_complete_synthetic_null_passes_integrity_with_behavior_limits(self):
        report = null_report()
        result = b.evaluate(report)
        self.assertTrue(result['accepted'], result.get('reason'))
        self.assertEqual(result['behavior']['primary_label'], 'MIXED_OR_UNRESOLVED')
        self.assertEqual(result['behavior']['responses']['NP']['recovery_status'], 'NO_BAND_EXIT')
        self.assertIn('WP_NO_SAFE_COMMAND_WITHDRAWAL_EXPOSURE', result['behavior']['interpretation_limits'])
        self.assertFalse(result['behavior']['independent_balance_proven'])
        # The cleared boundary and full tail cannot be trimmed to hide bad data.
        report['arms']['WP']['samples'][-1]['time_s'] = 1.9
        with self.assertRaisesRegex(ValueError, 'clock'): b.audit_arm(report['arms']['WP'])
        report['arms']['WP']['samples'][-1]['time_s'] = 2.
        report['arms']['WP']['neural'][-1]['uniforms_sha256'] = 'same-corruption-in-all-arms'
        with self.assertRaisesRegex(ValueError, 'common-slot replay'): b.audit_arm(report['arms']['WP'])

    def test_original_design_fingerprints(self):
        self.assertEqual(b.validate_design()['status'], 'SPECIFIED_NOT_IMPLEMENTED_NOT_RUN')

    def test_force_integer_boundaries_and_impulse(self):
        for c in b.CONDITIONS:
            forces = np.array([b.force(c, i) for i in range(20000)])
            active = np.flatnonzero(np.any(forces != 0, axis=1))
            np.testing.assert_array_equal(active, np.arange(5000, 5200) if c.endswith('P') else [])
            self.assertAlmostEqual(float(forces[:, 1].sum() * .0001), .02048 if c.endswith('P') else 0)
        for i in (-1, 20000, 5000., True):
            with self.assertRaises(ValueError): b.force('NP', i)

    def test_gate_boundary_keeps_decoder_running(self):
        values = dict.fromkeys(names(), .123)
        for c in b.CONDITIONS:
            self.assertEqual(b.gated(values, c, 1000, names()), values)
            expected = dict.fromkeys(names(), 0.) if c.startswith('W') else values
            self.assertEqual(b.gated(values, c, 1001, names()), expected)
        self.assertEqual(values, dict.fromkeys(names(), .123))

    def test_gate_rejects_nonfinite_inventory_and_tick(self):
        values = dict.fromkeys(names(), 0.)
        for tick in (0, 4001, 1001., True):
            with self.assertRaises(ValueError): b.gated(values, 'WP', tick, names())
        with self.assertRaises(ValueError): b.gated(dict(reversed(list(values.items()))), 'WP', 1001, names())
        values[names()[0]] = float('nan')
        with self.assertRaises(ValueError): b.gated(values, 'WP', 1001, names())

    def test_terminal_proposal_ownership(self):
        self.assertTrue(b.command_is_applied(3999))
        self.assertFalse(b.command_is_applied(4000))

    def test_raw_zero_preserves_slew_history(self):
        for offset in (-.25, .25):
            p = b.MatchedControlPipeline(True, b.MotorSafety())
            p.previous_physical_target = offset
            result = p.update(0., 0., .0005)
            self.assertEqual(result.admitted_neural_contribution, 0.)
            self.assertAlmostEqual(result.actuator_command, offset - np.sign(offset) * .002)
            for _ in range(125): result = p.update(0., 0., .0005)
            self.assertEqual(result.actuator_command, 0.)

    def test_full_fixed_command_replay_and_exposure(self):
        arm = command_arm()
        result = b.audit_commands(arm)
        self.assertEqual(result['first_raw_gate_difference_tick'], 1001)
        self.assertEqual(result['first_safe_counterfactual_difference_tick'], 1001)
        self.assertEqual(result['first_exposed_counterfactual_outgoing_transition'], 5005)
        self.assertFalse(result['terminal_proposal_applied'])
        self.assertEqual(arm['samples'][5005]['commanded_joints'], arm['samples'][5004]['commanded_joints'])
        self.assertNotEqual(arm['samples'][5006]['commanded_joints'], arm['samples'][5005]['commanded_joints'])

    def test_replay_rejects_final_target_hard_zero(self):
        arm = command_arm()
        arm['neural'][1000]['pipeline'][names()[0]]['actuator_command'] = 0.
        with self.assertRaisesRegex(ValueError, 'pipeline replay'): b.audit_commands(arm)

    def test_replay_rejects_unadmitted_command(self):
        arm = command_arm()
        arm['samples'][6000]['commanded_joints'] = list(arm['samples'][6000]['commanded_joints'])
        arm['samples'][6000]['commanded_joints'][0] = .1
        with self.assertRaisesRegex(ValueError, 'actual outgoing'): b.audit_commands(arm)

    def test_replay_rejects_native_ctrl_mismatch(self):
        arm = command_arm()
        arm['samples'][6000]['ctrl'][47] = .1
        with self.assertRaisesRegex(ValueError, 'native ctrl'): b.audit_commands(arm)

    def test_replay_rejects_terminal_counted_as_applied(self):
        arm = command_arm()
        arm['neural'][-1]['applied'] = True
        with self.assertRaisesRegex(ValueError, 'ownership'): b.audit_commands(arm)

    def test_prefix_retains_5005_applied_but_separates_proposal(self):
        a = dict(samples=[dict(qpos=[0.], proposed_commands=[0.]) for _ in range(5006)])
        c = copy.deepcopy(a)
        c['samples'][5005]['proposed_commands'] = [.1]
        b.equal_prefix(a, c, 5005, proposed=False)
        with self.assertRaises(ValueError): b.equal_prefix(a, c, 5005)
        c['samples'][5005]['qpos'] = [.1]
        with self.assertRaises(ValueError): b.equal_prefix(a, c, 5005, proposed=False)

    def test_real_392_slot_kernel_sampler_keeps_stream_with_different_inputs(self):
        a, c = small_brain(), small_brain()
        for brain in (a, c): brain.reset(1); brain.configure_external_rng_schedule(np.arange(392))
        for tick in range(40):
            a.clear_external_drive(); c.clear_external_drive()
            a.set_external_drive(np.arange(20), 2000.)
            c.set_external_drive(np.arange(200, 240), 2000.)
            a.step(); c.step()
            self.assertEqual(a._external_rng_step_draws, 392)
            np.testing.assert_array_equal(a._last_external_rng_uniforms, c._last_external_rng_uniforms)
            self.assertEqual(a.rng.bit_generator.state, c.rng.bit_generator.state)
        self.assertNotEqual(a.spike_counts.tolist(), c.spike_counts.tolist())

    def test_rng_schedule_rejects_missing_duplicate_unsorted_slots(self):
        brain = small_brain()
        for schedule in (range(391), [0] * 392, range(391, -1, -1)):
            with self.assertRaises(ValueError): brain.configure_external_rng_schedule(schedule)

    def test_world_frame_rotation_and_rms_math(self):
        q = np.array([[np.sqrt(.5), 0., 0., np.sqrt(.5)]])
        np.testing.assert_allclose(b.metrics.angular_velocity_world(q, [[1., 0., 0.]]), [[0., 1., 0.]], atol=1e-14)
        arms, audits = {}, {}
        for c, angle in zip(b.CONDITIONS, (0., 0., 10., 20.)):
            half = np.radians(angle) / 2
            pose = [0., 0., 1., float(np.cos(half)), float(np.sin(half)), 0., 0.]
            arms[c] = dict(samples=[dict(qpos=pose, qvel=[0.] * 6)] * 20001)
            audits[c] = dict(ground_support_counts=[6] * 20001, calibration_support_counts=[0] * 20001,
                            unexpected_distal_contact_counts=[0] * 20001, contact_correspondence_mismatch_counts=[0] * 20001,
                            commands=dict(first_exposed_counterfactual_outgoing_transition=5005))
        result = b.behavior(arms, audits)
        self.assertEqual(result['primary_label'], 'LOWER_PUSHED_WORLD_TILT_WITH_NEURAL_INPUT')
        self.assertAlmostEqual(result['posture']['NP']['world_tilt_rms_deg'], 10.)
        self.assertAlmostEqual(result['posture']['WP']['world_tilt_mean_deg'], 20.)
        expected_y = -np.sin(np.radians(10.)) + np.sin(np.radians(20.))
        self.assertAlmostEqual(result['factorial_world_up_vector'][0][1], expected_y)

    def test_incomplete_evidence_never_eligible_for_unity(self):
        report = dict(design=b.design(), preflight=dict(verified=True), sources_before={'x':'a'},
                      sources_after={'x':'a'}, arms={})
        result = b.evaluate(report)
        self.assertFalse(result['accepted']); self.assertFalse(result['unity_replay_eligible'])
        self.assertEqual(result['status'], 'INCONCLUSIVE_INTEGRITY')

    def test_failed_preflight_prevents_native_or_cns_construction(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(b, 'preflight', return_value=dict(verified=False)), patch.object(
                b, 'create_session', side_effect=AssertionError('native boundary crossed')):
            result = b.execute(Path(tmp) / 'blocked', live=True)
            self.assertEqual(result['run_status'], 'BLOCKED_PREREQUISITES')
            self.assertFalse(result['scientific_experiment_started'])
            self.assertFalse(b.load_run(Path(tmp) / 'blocked')['arms'])

    def test_nonfinite_partial_raw_preserved_and_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'partial.json'
            b.save(p, dict(qpos=[float('nan'), float('inf')], run_status='ERROR'))
            raw = json.loads(p.read_text())
            self.assertEqual(raw['qpos'], [{'__arrow_nonfinite_float__':'NaN'}, {'__arrow_nonfinite_float__':'+Infinity'}])
            with self.assertRaises(FileExistsError): b.save(p, {})

    def test_saved_arm_hash_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            b.save(d / 'NC.json.gz', dict(run_status='ERROR'))
            b.save(d / 'report.json', dict(arm_artifacts=dict(NC=dict(path='NC.json.gz', sha256='wrong'))))
            with self.assertRaisesRegex(ValueError, 'hash mismatch'): b.load_run(d)


if __name__ == '__main__':
    unittest.main()
