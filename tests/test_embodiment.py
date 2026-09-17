import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from malecns_backend.embodiment.body import BodySnapshot
from malecns_backend.embodiment.diagnostics import OUTCOME_CRITERIA, classify_weak_link
from malecns_backend.embodiment.experiment import calculate_physical_metrics
from malecns_backend.embodiment.loop import EmbodimentLoop, TimingConfig
from malecns_backend.embodiment.mappings import INTERFACE_MAP, load_selected_pathway
from malecns_backend.embodiment.motor import MotorActivityObserver, MotorDecoder, MotorSafety
from malecns_backend.embodiment.sensory import LegSensoryFrame, SensoryEncoder
from malecns_backend.embodiment.telemetry import JSONLTelemetry


class FakeBrain:
    """Unit fixture only; never represented as a NeuroMechFly experiment."""
    def __init__(self, n=165200, seed=1):
        self.config = SimpleNamespace(dt=0.5)
        self.spike_counts = np.zeros(n, np.uint32)
        self.external_drive = np.zeros(n)
        self.time_ms = 0.0
        self.rng = np.random.default_rng(seed)
        self.v = np.full(n, -52.0)

    def clear_external_drive(self): self.external_drive.fill(0)
    def set_external_drive(self, indices, rates): self.external_drive[indices] = rates
    def step(self):
        fired = self.rng.random(len(self.external_drive)) < self.external_drive * 0.0005
        self.spike_counts[fired] += 1
        self.time_ms += 0.5
        return np.flatnonzero(fired)


class FakeBody:
    """Encoder/decoder/scheduler fixture, not a closed-loop body result."""
    behavior_controller_invoked = False
    timestep_s = 0.0001

    def __init__(self, angle=0.0):
        self.angle, self.physics_steps = angle, 0

    def observe(self):
        return BodySnapshot(LegSensoryFrame(self.physics_steps*self.timestep_s, self.angle),
                            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0), 0.0)

    def step(self, command, count=1):
        self.angle = command.target_position_rad
        self.physics_steps += count
        return self.observe()


class EmbodimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pathway = load_selected_pathway()

    def components(self, seed=1, telemetry=None):
        p = self.pathway
        brain, body = FakeBrain(seed=seed), FakeBody()
        encoder = SensoryEncoder(p)
        observer = MotorActivityObserver({p.extensor.name:p.extensor.dense_indices,
                                          p.flexor.name:p.flexor.dense_indices})
        decoder = MotorDecoder(p)
        return brain, body, EmbodimentLoop(brain, body, encoder, observer, decoder, p,
                                           telemetry=telemetry)

    def test_mapping_ids_resolve_exactly_against_interface_map(self):
        raw=json.loads(INTERFACE_MAP.read_text())
        ids={i for r in raw['populations'] for i in r.get('body_ids',())}
        p=self.pathway
        self.assertTrue(set(p.sensor.body_ids+p.extensor.body_ids+p.flexor.body_ids)<=ids)
        self.assertEqual((len(p.sensor.body_ids),len(p.extensor.body_ids),len(p.flexor.body_ids)),(80,2,5))

    def test_mapping_side_joint_and_directions(self):
        p=self.pathway
        self.assertEqual((p.leg,p.side,p.joint,p.flygym_leg,p.flygym_joint_index),("T2","left","tibia","LM",12))
        self.assertEqual((p.sensor.body_target,p.extensor.body_target,p.flexor.body_target),("tibia_T2_left",)*3)
        self.assertEqual((p.extensor.direction,p.flexor.direction),(1,-1))

    def test_sensory_encoder_targets_only_expected_population(self):
        drive=SensoryEncoder(self.pathway).encode(LegSensoryFrame(0,0))
        np.testing.assert_array_equal(drive.indices,self.pathway.sensor.dense_indices)
        self.assertEqual(drive.population_name,"chordotonal T2 left")

    def test_sensory_rates_finite_bounded_and_zero_angle_documented(self):
        encoder=SensoryEncoder(self.pathway)
        for angle in (-100,-1.35,0,1.3,100):
            rates=encoder.encode(LegSensoryFrame(0,angle)).rates_hz
            self.assertTrue(np.isfinite(rates).all()); self.assertTrue((rates>=0).all()); self.assertTrue((rates<=120).all())
        # Zero angle is a physical position, not absence of proprioception.
        self.assertGreater(encoder.encode(LegSensoryFrame(0,0)).rates_hz.max(),119)

    def test_encoder_uses_normal_external_rate_path(self):
        brain=FakeBrain(); drive=SensoryEncoder(self.pathway).encode(LegSensoryFrame(0,0)); drive.apply(brain)
        self.assertEqual(np.count_nonzero(brain.external_drive),np.count_nonzero(drive.rates_hz))
        outside=np.ones(len(brain.external_drive),bool); outside[drive.indices]=False
        self.assertFalse(np.any(brain.external_drive[outside]))

    def test_spike_increment_hz_and_40ms_filter(self):
        o=MotorActivityObserver({'p':(1,2)},tau_ms=40); counts=np.zeros(4,np.uint32); o.reset(counts)
        counts[1:3]=1; result=o.update(counts,10)
        # instantaneous is 100 Hz/neuron; alpha=.25 => 25 Hz.
        self.assertEqual(result['increments']['p'],2); self.assertAlmostEqual(result['filtered_hz']['p'],25)
        result=o.update(counts,10); self.assertAlmostEqual(result['filtered_hz']['p'],18.75)
        self.assertEqual(result['neurons']['p']['increments'],[0,0])
        self.assertEqual(result['neurons']['p']['instantaneous_hz'],[0.0,0.0])
        self.assertEqual(result['neurons']['p']['filtered_hz'],[18.75,18.75])

    def test_motor_decoder_sign_and_isolation(self):
        p=self.pathway; d=MotorDecoder(p,MotorSafety(max_velocity_rad_s=1000))
        ext={p.extensor.name:50,p.flexor.name:0}; flex={p.extensor.name:0,p.flexor.name:50}
        self.assertGreater(d.decode(ext,0,.001).target_position_rad,0)
        d.reset(); self.assertLess(d.decode(flex,0,.001).target_position_rad,0)
        self.assertEqual(d.decode(flex,0,.001).actuator,"joint_LMTibia")

    def test_actuator_safety_range_velocity_and_magnitude(self):
        p=self.pathway; safety=MotorSafety(-.1,.1,.02,.5); d=MotorDecoder(p,safety)
        rates={p.extensor.name:1e9,p.flexor.name:0}
        command=d.decode(rates,.09,.01)
        self.assertLessEqual(command.target_position_rad,.0950000001)
        self.assertLessEqual(command.target_position_rad,.1)
        self.assertLessEqual(command.unclamped_position_rad-.09,.020000001)
        self.assertAlmostEqual(command.raw_decoder_output_rad,.02)
        self.assertAlmostEqual(command.magnitude_clamped_output_rad,.02)
        self.assertAlmostEqual(command.range_clamped_position_rad,.1)
        self.assertAlmostEqual(command.slew_clamped_position_rad,.095)

    def test_multirate_scheduler_counts_and_causal_order(self):
        brain,body,loop=self.components(); before=body.observe().frame.time_s
        loop.step()
        self.assertEqual(brain.time_ms,1); self.assertEqual(body.physics_steps,10)
        self.assertEqual(body.observe().frame.time_s-before,.001)

    def test_deterministic_mode_reproduces_results(self):
        a=self.components(seed=7)[2]; b=self.components(seed=7)[2]
        for _ in range(30):
            ra,rb=a.step(),b.step()
            np.testing.assert_array_equal(a.brain.spike_counts,b.brain.spike_counts)
            self.assertEqual(ra['command'],rb['command'])

    def test_instrumentation_does_not_change_deterministic_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            with JSONLTelemetry(Path(tmp)/'trace.jsonl') as out:
                instrumented=self.components(seed=11,telemetry=out)[2]
                observed=instrumented.run(20)
            plain=self.components(seed=11)[2]
            expected=plain.run(20)
        np.testing.assert_array_equal(instrumented.brain.spike_counts,plain.brain.spike_counts)
        self.assertEqual([r['command'] for r in observed],[r['command'] for r in expected])
        self.assertEqual([r['after'].frame for r in observed],[r['after'].frame for r in expected])

    def test_telemetry_required_fields_and_finite_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run.jsonl'
            with JSONLTelemetry(path) as out:
                brain,body,loop=self.components(telemetry=out); loop.run(2)
            rows=[json.loads(x) for x in path.read_text().splitlines()]
        required={'simulation_time_s','physics_time_s','neural_time_ms','tibia_angle_rad','encoded_rate_mean_hz',
                  'sensory_spike_count','total_cns_spike_count','extensor_spike_increment','extensor_filtered_hz',
                  'actuator_target_rad','contact_force_n','body_position_m','body_orientation'}
        self.assertEqual(len(rows),2); self.assertTrue(required<=rows[0].keys())
        self.assertEqual([r['control_step'] for r in rows],[1,2])
        self.assertLess(path.stat().st_size,100_000)
        self.assertTrue(np.isfinite(brain.v).all()); self.assertTrue(math.isfinite(body.angle))

    def test_displacement_and_latency_metrics_are_measured(self):
        def snapshot(time, angle, velocity=0):
            return BodySnapshot(LegSensoryFrame(time,angle),(0,0,0),(),0,velocity,angle)
        initial, middle, final=snapshot(0,.1),snapshot(.001,.15,2),snapshot(.002,.08,-1)
        rows=[{'after':middle,'command':SimpleNamespace(target_position_rad=.16)},
              {'after':final,'command':SimpleNamespace(target_position_rad=.09)}]
        metrics=calculate_physical_metrics(initial,final,rows)
        self.assertAlmostEqual(metrics['maximum_displacement_rad'],.05)
        self.assertAlmostEqual(metrics['minimum_angle_rad'],.08)
        self.assertAlmostEqual(metrics['maximum_angle_rad'],.15)
        self.assertAlmostEqual(metrics['maximum_command_measured_error_rad'],.01)
        self.assertEqual(metrics['peak_abs_velocity_rad_s'],2)

    def test_weak_link_uses_measured_values_and_shared_outcome_criteria(self):
        base={'sensory_spikes':0,'nonsensory_spikes':0,'motor_spikes':0,
              'peak_antagonist_signal':0,'peak_raw_motor_command_rad':0,
              'peak_final_motor_command_rad':0,'max_displacement_rad':0}
        self.assertEqual(classify_weak_link(base)[0],'S0')
        base.update(sensory_spikes=1); self.assertEqual(classify_weak_link(base)[0],'S1')
        base.update(nonsensory_spikes=1); self.assertEqual(classify_weak_link(base)[0],'S2')
        base.update(motor_spikes=1); self.assertEqual(classify_weak_link(base)[0],'S3')
        base.update(peak_antagonist_signal=.2,peak_raw_motor_command_rad=.01,
                    peak_final_motor_command_rad=.004)
        self.assertEqual(classify_weak_link(base)[0],'S5')
        self.assertEqual(OUTCOME_CRITERIA.classify(0,1,0),
                         'B. NEURAL PROPAGATION WITHOUT MEANINGFUL BODY RESPONSE')

    def test_old_behavior_controller_is_not_invoked(self):
        _,body,loop=self.components(); loop.step()
        self.assertFalse(body.behavior_controller_invoked)
        source=(Path(__file__).parents[1]/'malecns_backend/embodiment/body.py').read_text()
        self.assertNotIn('flygym.examples',source)
        self.assertNotIn('PreprogrammedSteps',source)
        self.assertNotIn('HybridTurningController',source)

    def test_bad_timing_rejected(self):
        with self.assertRaises(ValueError): TimingConfig(control_dt_ms=.75)


if __name__ == '__main__': unittest.main()
