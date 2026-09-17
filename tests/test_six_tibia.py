import json
import unittest
from types import SimpleNamespace

import numpy as np

from malecns_backend.embodiment.mappings import load_selected_pathway
from malecns_backend.embodiment.motor import MotorActivityObserver, MotorDecoder
from malecns_backend.embodiment.sensory import LegSensoryFrame, SensoryEncoder
from malecns_backend.embodiment.six_tibia import (LEG_ORDER, SIX_LEG_MAP,
                                                  IsolatedTibiaDecoder,
                                                  load_six_tibia_interfaces)
from malecns_backend.embodiment.six_tibia_audit import (
    lm_execution_configuration_preserved, run_isolated_experiments,
    run_isolated_leg)
from malecns_backend.embodiment.body import BodySnapshot


class _AuditBrain:
    def __init__(self, n=165200):
        self.config = SimpleNamespace(dt=.5)
        self.spike_counts = np.zeros(n, np.uint32)
        self.external_drive = np.zeros(n)
        self.diagnostic_observer = None

    def reset(self, seed):
        self.spike_counts.fill(0); self.external_drive.fill(0); self.time_ms = 0

    def clear_external_drive(self): self.external_drive.fill(0)
    def set_external_drive(self, indices, rates): self.external_drive[indices] = rates
    def step(self):
        fired = np.empty(0, np.int32)
        self.time_ms += .5
        if self.diagnostic_observer: self.diagnostic_observer.after_step(self, fired)
        return fired


class _AuditBody:
    timestep_s = .0001
    instances = []

    def __init__(self, pathway):
        self.pathway, self.physics_steps, self.angle, self.closed = pathway, 0, 0., False
        self.commands = []
        self.instances.append(self)

    def observe(self):
        return BodySnapshot(LegSensoryFrame(self.physics_steps * self.timestep_s, self.angle),
                            (0., 0., 0.), (), 0.)

    def step(self, command, count):
        self.commands.append(command); self.angle = command.target_position_rad
        self.physics_steps += count
        return self.observe()

    def close(self): self.closed = True


class SixTibiaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.interfaces = load_six_tibia_interfaces()

    def test_exactly_six_order_side_segment_actuators(self):
        self.assertEqual(tuple(self.interfaces), LEG_ORDER)
        expected = [("LF", "left", "T1", 5), ("LM", "left", "T2", 12),
                    ("LH", "left", "T3", 19), ("RF", "right", "T1", 26),
                    ("RM", "right", "T2", 33), ("RH", "right", "T3", 40)]
        self.assertEqual([(x.leg, x.side, x.segment, x.action_index)
                          for x in self.interfaces.values()], expected)
        self.assertEqual(len({x.actuator_name for x in self.interfaces.values()}), 6)
        self.assertEqual(len({x.action_index for x in self.interfaces.values()}), 6)

    def test_4a_records_ids_confidence_and_sizes_preserved(self):
        raw = json.loads(SIX_LEG_MAP.read_text())
        joints = {l["leg"]: next(j for j in l["joints"]
                                 if j["actuator"]["anatomical_joint"] == "tibia")
                  for l in raw["legs"]}
        self.assertEqual([len(x.sensor.body_ids) for x in self.interfaces.values()],
                         [23, 80, 93, 13, 83, 100])
        for leg, item in self.interfaces.items():
            joint = joints[leg]
            self.assertEqual(item.sensory_confidence, joint["sensory"]["status"])
            self.assertEqual(item.motor_confidence, joint["motor"]["status"])
            self.assertEqual(item.sensor.body_ids,
                             tuple(joint["sensory"]["populations"][0]["body_ids"]))
            self.assertEqual([(p.name, list(p.body_ids), p.direction) for p in item.motor_populations],
                             [(p["name"], p["body_ids"], p["direction"])
                              for p in joint["motor"]["populations"]])
            self.assertTrue(all(-(2**63) <= i < 2**63 for i in item.sensor.body_ids))
            self.assertTrue(all(-(2**63) <= i < 2**63
                                for p in item.motor_populations for i in p.body_ids))
        self.assertEqual(self.interfaces["LM"].motor_confidence, "EXACT")
        self.assertTrue(all(self.interfaces[x].motor_confidence == "SUPPORTED"
                            for x in LEG_ORDER if x != "LM"))

    def test_encoder_heterogeneous_and_selected_only(self):
        all_indices = {leg: set(x.sensor.dense_indices) for leg, x in self.interfaces.items()}
        for leg, item in self.interfaces.items():
            drive = SensoryEncoder(item).encode(LegSensoryFrame(0, 0))
            self.assertEqual(len(drive.rates_hz), len(item.sensor.body_ids))
            self.assertTrue(np.isfinite(drive.rates_hz).all())
            self.assertTrue(((drive.rates_hz >= 0) & (drive.rates_hz <= 120)).all())
            self.assertEqual(set(drive.indices), all_indices[leg])

    def test_engineered_debug_sign_and_cross_leg_isolation(self):
        # ENGINEERED DEBUG INPUT; not biological activity.
        for item in self.interfaces.values():
            d = MotorDecoder(item)
            ext = {item.extensor.name: 50, item.flexor.name: 0}
            flex = {item.extensor.name: 0, item.flexor.name: 50}
            self.assertGreater(d.decode(ext, 0, .001).antagonist_signal, 0)
            d.reset()
            self.assertLess(d.decode(flex, 0, .001).antagonist_signal, 0)
        a = IsolatedTibiaDecoder(self.interfaces["LF"])
        b = IsolatedTibiaDecoder(self.interfaces["RF"])
        a.decoder.previous_target = .4
        self.assertIsNone(b.decoder.previous_target)
        a.reset()
        self.assertIsNone(a.decoder.previous_target)

    def test_lm_m3d_numerical_equivalence(self):
        new, old = self.interfaces["LM"], load_selected_pathway()
        for angle in (-1.35, 0, .42, 1.3):
            a = SensoryEncoder(new).encode(LegSensoryFrame(0, angle))
            b = SensoryEncoder(old).encode(LegSensoryFrame(0, angle))
            np.testing.assert_array_equal(a.indices, b.indices)
            np.testing.assert_array_equal(a.rates_hz, b.rates_hz)
        self.assertEqual(new.extensor.dense_indices, old.extensor.dense_indices)
        self.assertEqual(new.flexor.dense_indices, old.flexor.dense_indices)
        counts = np.zeros(max(new.extensor.dense_indices + new.flexor.dense_indices)+1, np.uint32)
        baseline = counts.copy(); counts[np.asarray(new.extensor.dense_indices)] = 1
        populations = {new.extensor.name:new.extensor.dense_indices,
                       new.flexor.name:new.flexor.dense_indices}
        no, oo = MotorActivityObserver(populations), MotorActivityObserver(populations)
        no.reset(baseline); oo.reset(baseline)
        nr, or_ = no.update(counts, 1), oo.update(counts, 1)
        self.assertEqual(nr, or_)
        nc = MotorDecoder(new).decode(nr["filtered_hz"], .2, .001)
        oc = MotorDecoder(old).decode(or_["filtered_hz"], .2, .001)
        self.assertEqual(nc, oc)

    def test_constants_and_no_behavior_or_simultaneous_api(self):
        self.assertEqual((SensoryEncoder.maximum_rate_hz, SensoryEncoder.width_normalized,
                          SensoryEncoder.cutoff_hz), (120., .25, 5.))
        self.assertEqual((MotorDecoder.half_activation_hz,), (17.,))
        source = __import__("pathlib").Path(
            "malecns_backend/embodiment/six_tibia.py").read_text()
        for forbidden in ("PreprogrammedSteps", "HybridTurningController", "CPG", "gait"):
            self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(IsolatedTibiaDecoder, "decode_all"))

    def test_real_runner_fresh_reset_order_and_single_selection(self):
        _AuditBody.instances.clear()
        results = run_isolated_experiments(
            1, interfaces=self.interfaces, data=object(),
            brain_factory=lambda data: _AuditBrain(), body_factory=_AuditBody)
        self.assertEqual([r["leg"] for r in results], list(LEG_ORDER))
        self.assertEqual(len(_AuditBody.instances), 6)
        self.assertTrue(all(x.closed for x in _AuditBody.instances))
        for result, body in zip(results, _AuditBody.instances):
            self.assertEqual(result["isolation"]["engineered_sensory_populations"],
                             [self.interfaces[result["leg"]].sensor.name])
            self.assertEqual(result["isolation"]["eligible_neural_actuators"],
                             [self.interfaces[result["leg"]].actuator_name])
            self.assertTrue(all(c.actuator == self.interfaces[result["leg"]].actuator_name
                                for c in body.commands))
            self.assertTrue(result["biological_silence_is_valid"])

    def test_other_motor_activity_is_observed_not_decoded(self):
        other_index = self.interfaces["RH"].motor_populations[0].dense_indices[0]

        class NaturallyActive(_AuditBrain):
            def reset(self, seed):
                super().reset(seed); self.spike_counts[other_index] = 2

        result = run_isolated_leg(
            "LF", 1, interfaces=self.interfaces, data=object(),
            brain_factory=lambda data: NaturallyActive(), body_factory=_AuditBody)
        self.assertTrue(result["other_tibia_motor"]["naturally_spiked"])
        self.assertFalse(result["other_tibia_motor"]["decoded_or_applied"])
        self.assertTrue(any(key.startswith("RH:")
                            for key in result["other_tibia_motor"]["populations"]))

    def test_lm_execution_configuration_preserved(self):
        self.assertTrue(lm_execution_configuration_preserved(self.interfaces["LM"]))


if __name__ == "__main__":
    unittest.main()
