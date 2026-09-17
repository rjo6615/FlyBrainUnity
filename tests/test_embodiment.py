import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from malecns_backend.embodiment.body import BodySnapshot
from malecns_backend.embodiment.diagnostics import OUTCOME_CRITERIA, classify_weak_link
from malecns_backend.embodiment.temporal import (classify_temporal, directed_distances,
                                                 neuron_metadata)
from malecns_backend.embodiment.experiment import (calculate_physical_metrics,
                                                   summarize_experiment)
from malecns_backend.embodiment.causal import analyze_matched, row_record
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

    def diagnostics(self):
        """Match the numerical-health portion of the real brain interface."""
        return {
            "time_ms": self.time_ms,
            "spikes": int(self.spike_counts.sum()),
            "mean_voltage": float(np.mean(self.v)),
            "min_voltage": float(np.min(self.v)),
            "max_voltage": float(np.max(self.v)),
            "nonfinite": int((~np.isfinite(self.v)).sum()),
            "active_fraction": float(np.count_nonzero(self.spike_counts) / len(self.spike_counts)),
        }


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

    def test_duration_changes_only_number_of_steps_and_replays_reset(self):
        short=self.components(seed=19)[2]; long=self.components(seed=19)[2]
        short.run(10); long.run(25)
        self.assertEqual((short.control_steps,long.control_steps),(10,25))
        replay=self.components(seed=19)[2]; replay.run(10)
        np.testing.assert_array_equal(short.brain.spike_counts,replay.brain.spike_counts)

    def test_deterministic_duration_prefix(self):
        short=self.components(seed=23)[2]; long=self.components(seed=23)[2]
        a=short.run(10); b=long.run(25)
        self.assertEqual([x['cns_spike_increment'] for x in a],
                         [x['cns_spike_increment'] for x in b[:10]])

    def test_directed_graph_distance_respects_orientation(self):
        graph=SimpleNamespace(neuron_count=4,row_ptr=np.array([0,1,2,3,3]),
                              target_indices=np.array([1,2,3]))
        np.testing.assert_array_equal(directed_distances(graph,(0,)),(0,1,2,3))
        np.testing.assert_array_equal(directed_distances(graph,(3,)),(-1,-1,-1,0))

    def test_temporal_classification_uses_measured_stages(self):
        motor=lambda events,spike: [{'excitatory_events':events,'inhibitory_events':0,
                                     'threshold_crossed':spike}]
        self.assertEqual(classify_temporal(motor(0,False),0,0,0),'T1')
        self.assertEqual(classify_temporal(motor(1,False),0,0,0),'T2')
        self.assertEqual(classify_temporal(motor(1,True),0,0,0),'T3')
        self.assertEqual(classify_temporal(motor(1,True),.1,.01,.01),'T4')
        self.assertEqual(classify_temporal(motor(1,True),.1,.02,.01),'T5')

    def test_summary_passes_authoritative_selected_motors_to_activity_bins(self):
        p = self.pathway
        motor_indices = p.extensor.dense_indices + p.flexor.dense_indices
        self.assertEqual(p.extensor.body_ids, (800911, 801234))
        self.assertEqual(p.flexor.body_ids, (802295, 818295, 823739, 824041, 927808))
        self.assertTrue(set(motor_indices).isdisjoint(p.sensor.dense_indices))
        brain = FakeBrain()
        loop = SimpleNamespace(first_times_s={}, performance=lambda: {})
        snapshot = BodySnapshot(LegSensoryFrame(0, 0), (0, 0, 0), (), 0, 0, 0)
        command = SimpleNamespace(target_position_rad=0, antagonist_signal=0,
                                  raw_decoder_output_rad=0)
        rows = [{"before": snapshot, "after": snapshot, "command": command,
                 "motor": {"filtered_hz": {p.extensor.name: 0, p.flexor.name: 0}}}]
        recorder = SimpleNamespace(motor_results=lambda: [], downstream_events=[])
        with tempfile.TemporaryDirectory() as tmp:
            telemetry = Path(tmp) / "telemetry.jsonl"
            telemetry.write_text("{}\n", encoding="utf-8")
            with patch("malecns_backend.embodiment.experiment.activity_bins",
                       return_value=[]) as bins:
                result = summarize_experiment(
                    brain, p, loop, rows, snapshot, snapshot, telemetry,
                    recorder=recorder, duration_ms=10,
                    motor_indices=motor_indices)
        bins.assert_called_once_with(recorder, 10, motor_indices)
        self.assertEqual(result["activity_bins"], [])

    def test_actuator_latency_is_labeled_as_target_update(self):
        loop=self.components()[2]; loop.run(2)
        self.assertIn('actuator_target_update',loop.first_times_s)
        self.assertNotIn('changed_actuator_command',loop.first_times_s)

    def test_motor_disabled_computes_but_does_not_apply_neural_output(self):
        brain, body, loop = self.components()
        brain.spike_counts[list(self.pathway.extensor.dense_indices)] = 1
        row = loop.step(apply_neural_motor=False)
        self.assertGreater(row['decoded_neural_offset_rad'], 0)
        self.assertEqual(row['applied_neural_offset_rad'], 0)
        self.assertEqual(row['command'].target_position_rad, row['base_actuator_target_rad'])
        self.assertEqual(body.physics_steps, 10)
        self.assertGreater(brain.time_ms, 0)

    def test_closed_loop_applies_neural_contribution(self):
        brain, _, loop = self.components()
        brain.spike_counts[list(self.pathway.extensor.dense_indices)] = 1
        row = loop.step()
        self.assertEqual(row['applied_neural_offset_rad'], row['decoded_neural_offset_rad'])
        self.assertGreater(row['command'].target_position_rad, row['base_actuator_target_rad'])

    def test_causal_metrics_order_and_classification(self):
        def sample(t, angle=0, sensory=0, cns=0, motor=0, offset=0, applied=0):
            return dict(time_ms=t, tibia_angle_rad=angle, tibia_velocity_rad_s=angle,
                        decoded_neural_offset_rad=offset, applied_neural_offset_rad=applied,
                        extensor_mn_spikes=motor, flexor_mn_spikes=0,
                        sensory_rates_hz=[float(sensory)], sensory_spikes=sensory,
                        whole_cns_spikes=cns)
        control = [sample(i) for i in range(1, 6)]
        closed = [sample(1), sample(2, motor=1), sample(3, offset=.1, applied=.1),
                  sample(4, angle=.01, offset=.1, applied=.1),
                  sample(5, angle=.02, sensory=1, cns=1, offset=.1, applied=.1)]
        result = analyze_matched(closed, control)
        self.assertEqual(result['causal_order'], [2, 3, 3, 4, 5])
        self.assertTrue(result['classification'].startswith('D3'))
        self.assertEqual(result['pre_motor_max_angle_difference_rad'], 0)

    def test_causal_feedback_is_sensory_encoding_not_an_earlier_spike_event(self):
        def sample(t, angle=0, rate=0, sensory_spikes=0, cns=0, motor=0,
                   offset=0, applied=0):
            return dict(time_ms=t, tibia_angle_rad=angle, tibia_velocity_rad_s=angle,
                        decoded_neural_offset_rad=offset, applied_neural_offset_rad=applied,
                        extensor_mn_spikes=motor, flexor_mn_spikes=0,
                        sensory_rates_hz=[float(rate)], sensory_spikes=sensory_spikes,
                        whole_cns_spikes=cns)
        control = [sample(i) for i in range(1, 7)]
        closed = [sample(1), sample(2, sensory_spikes=1, cns=1, motor=1),
                  sample(3, offset=.1, applied=.1),
                  sample(4, angle=.01, offset=.1, applied=.1),
                  sample(5, angle=.02, offset=.1, applied=.1),
                  sample(6, angle=.03, rate=1, offset=.1, applied=.1)]
        result = analyze_matched(closed, control)
        self.assertEqual(result['first_sensory_spike_divergence_ms'], 2)
        self.assertEqual(result['first_cns_spike_divergence_ms'], 2)
        self.assertEqual(result['first_sensory_encoding_divergence_ms'], 6)
        self.assertEqual(result['causal_order'], [2, 3, 3, 4, 6])
        self.assertTrue(result['classification'].startswith('D3'))

    def test_causal_contradiction_is_invalid_not_d2_or_d3(self):
        def sample(t, angle=0, rate=0, motor=0, offset=0, applied=0):
            return dict(time_ms=t, tibia_angle_rad=angle, tibia_velocity_rad_s=angle,
                        decoded_neural_offset_rad=offset, applied_neural_offset_rad=applied,
                        extensor_mn_spikes=motor, flexor_mn_spikes=0,
                        sensory_rates_hz=[float(rate)], sensory_spikes=0,
                        whole_cns_spikes=0)
        control = [sample(i) for i in range(1, 6)]
        closed = [sample(1), sample(2, rate=1, motor=1),
                  sample(3, rate=1, offset=.1, applied=.1),
                  sample(4, angle=.01, rate=1, offset=.1, applied=.1),
                  sample(5, angle=.02, rate=1, offset=.1, applied=.1)]
        result = analyze_matched(closed, control)
        self.assertEqual(result['causal_order'], [2, 3, 3, 4, 2])
        self.assertFalse(result['causal_order_valid'])
        self.assertTrue(result['classification'].startswith('D0'))

    def test_causal_invalid_when_premotor_trajectory_differs(self):
        base = dict(tibia_velocity_rad_s=0, decoded_neural_offset_rad=0,
                    applied_neural_offset_rad=0, extensor_mn_spikes=0,
                    flexor_mn_spikes=0, sensory_rates_hz=[0.], sensory_spikes=0,
                    whole_cns_spikes=0)
        control = [dict(base, time_ms=1, tibia_angle_rad=0),
                   dict(base, time_ms=2, tibia_angle_rad=0)]
        closed = [dict(base, time_ms=1, tibia_angle_rad=.01),
                  dict(base, time_ms=2, tibia_angle_rad=0, decoded_neural_offset_rad=.1,
                       applied_neural_offset_rad=.1)]
        self.assertTrue(analyze_matched(closed, control)['classification'].startswith('D0'))

    def test_matched_timestamp_validation(self):
        with self.assertRaises(ValueError):
            analyze_matched([{'time_ms': 1}], [{'time_ms': 2}])


if __name__ == '__main__': unittest.main()
