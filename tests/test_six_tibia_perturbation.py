import json
import unittest
from array import array
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from malecns_backend.neural import MaleCNSBrain, ModelConfig
from malecns_backend.embodiment.body import SixTibiaBodySnapshot
from malecns_backend.embodiment.six_tibia import LEG_ORDER, load_six_tibia_interfaces
from malecns_backend.embodiment.six_tibia_causal import CANONICAL_SEED, SixTibiaRuntime, rng_state_digest
from malecns_backend.embodiment.six_tibia_pathway_audit import CANONICAL
from malecns_backend.embodiment.six_tibia_perturbation import (
    classify_trace, first_spike_delta, motor_influence_matrix, split_own_cross,
    summarize_run, validate_canonical_baseline)
from malecns_backend.embodiment.six_tibia_perturbation import _run_condition


def tiny_data(n):
    return SimpleNamespace(neuron_count=n, row_ptr=array('I', [0] * (n + 1)),
        target_indices=array('I'), synapse_counts=array('H'), neuron_sizes=array('f', [1] * n),
        nt_signs=array('f', [1] * n), neurotransmitter_ids=array('B', [0] * n),
        superclass_ids=array('B', [0] * n), superclasses=['central'], class_ids=array('H', [0] * n),
        classes=['other'], types=['sensory'] * n, body_ids=array('q', range(100, 100 + n)),
        neurotransmitters=['unknown'])


def tiny_config():
    return ModelConfig(min_synapses=1, sensory_mask=False, neuromodulation=False,
                       adaptation_increment=0, kc_threshold_offset=0, lamina_bias=0)


class Body:
    timestep_s = .0001
    def __init__(self, interfaces): self.interfaces = interfaces; self.time = 0.; self.closed = False
    def observe(self):
        return SixTibiaBodySnapshot(self.time, {leg: 0. for leg in LEG_ORDER}, {leg: 0. for leg in LEG_ORDER})
    def step(self, commands, count): self.time += count * self.timestep_s; return self.observe()
    def close(self): self.closed = True


class PerturbationTests(unittest.TestCase):
    def setUp(self): self.interfaces = load_six_tibia_interfaces()

    def test_withholding_runs_every_encoder_and_only_zeros_delivery(self):
        n = max(i for interface in self.interfaces.values() for population in (interface.sensor,) + interface.motor_populations for i in population.dense_indices) + 1
        brain = MaleCNSBrain(tiny_data(n), tiny_config())
        runtime = SixTibiaRuntime(brain, Body(self.interfaces), self.interfaces, CANONICAL_SEED, True,
                                  withheld_sensory="LH")
        calls = []
        for leg, encoder in runtime.encoders.items():
            original = encoder.encode
            encoder.encode = lambda frame, leg=leg, original=original: (calls.append(leg), original(frame))[1]
        row = runtime.step(1)
        self.assertEqual(tuple(calls), LEG_ORDER)
        self.assertIn("LH", row["counterfactual_sensory_increments"])
        self.assertEqual(row["delivered_sensory_increments"]["LH"], 0)
        self.assertEqual(row["sensory_provenance"]["LH"]["counterfactual_provenance"],
                         "MODELED_TRANSDUCTION")
        self.assertEqual(row["sensory_provenance"]["LH"]["delivered_provenance"],
                         "ENGINEERED_SENSORY_WITHHOLDING")
        for leg in LEG_ORDER:
            if leg != "LH":
                self.assertEqual(row["counterfactual_sensory_increments"][leg],
                                 row["delivered_sensory_increments"][leg])
                self.assertEqual(row["sensory_provenance"][leg]["delivered_provenance"],
                                 "MODELED_TRANSDUCTION")

    def test_common_random_numbers_and_later_population_draws(self):
        n = 12; plain = MaleCNSBrain(tiny_data(n), tiny_config()); withheld = MaleCNSBrain(tiny_data(n), tiny_config())
        plain.reset(1); withheld.reset(1)
        rates = np.full(n, 120., dtype=float)
        plain.set_external_drive(np.arange(n), rates); withheld.set_external_drive(np.arange(n), rates)
        withheld.external_drive_withheld_indices = np.array([3, 4], dtype=np.intp)
        for _ in range(20):
            plain.step(); withheld.step()
            self.assertEqual(rng_state_digest(plain.rng), rng_state_digest(withheld.rng))
            np.testing.assert_array_equal(plain._last_external_candidates,
                                          withheld._last_external_candidates)
            self.assertFalse(set(withheld._last_external_delivered) & {3, 4})

    def test_intervention_does_not_mutate_mapping_motor_or_body(self):
        before = {leg: (self.interfaces[leg].actuator_name,
                        tuple((p.body_ids, p.dense_indices) for p in self.interfaces[leg].motor_populations))
                  for leg in LEG_ORDER}
        n = max(i for interface in self.interfaces.values() for population in (interface.sensor,) + interface.motor_populations for i in population.dense_indices) + 1
        body = Body(self.interfaces)
        SixTibiaRuntime(MaleCNSBrain(tiny_data(n), tiny_config()), body, self.interfaces, 1, True,
                        withheld_sensory="LH")
        after = {leg: (self.interfaces[leg].actuator_name,
                       tuple((p.body_ids, p.dense_indices) for p in self.interfaces[leg].motor_populations))
                 for leg in LEG_ORDER}
        self.assertEqual(before, after); self.assertIn("LH", body.interfaces)

    def test_signed_matrix_none_timing_and_own_cross(self):
        baseline = {leg: 10 for leg in LEG_ORDER}
        interventions = {source: {target: 10 for target in LEG_ORDER} for source in LEG_ORDER}
        interventions["LH"]["LM"] = 13; interventions["LH"]["LH"] = 6
        matrix = motor_influence_matrix(baseline, interventions)
        self.assertEqual(matrix["LH"]["LM"], 3); self.assertEqual(matrix["LH"]["LH"], -4)
        self.assertEqual(matrix["LF"]["RM"], 0)
        effects = split_own_cross("LH", matrix["LH"])
        self.assertEqual(effects["own_leg_motor_delta"], -4); self.assertNotIn("LH", effects["cross_leg_motor_deltas"])
        self.assertIsNone(first_spike_delta(None, 2)); self.assertEqual(first_spike_delta(5, 2), 3.)

    def test_classifier_feedback_prerequisites(self):
        self.assertEqual(classify_trace(True, 1, 2, 3, 4, None, 6, 7), "P4")
        self.assertEqual(classify_trace(True, 1, 2, 3, 4, 5, None, 7), "P5")
        self.assertEqual(classify_trace(True, 1, 2, 3, 4, 5, 6, 7), "P7")
        self.assertEqual(classify_trace(False, 1, 2, 3, 4, 5, 6, 7), "P0")

    def test_canonical_contract_seed_and_json(self):
        self.assertEqual(CANONICAL_SEED, 1)
        summary = {"sensory": {}, "motor": {}}
        for leg, values in CANONICAL.items():
            summary["sensory"][leg] = {"intervention_delivered_spikes": values[0]}
            summary["motor"][leg] = {"selected_mapped_motor_spikes": values[1],
                "first_mapped_motor_spike_ms": values[2], "peak_decoded_offset_rad": values[3]}
        self.assertTrue(validate_canonical_baseline(summary)[1]); json.dumps(summary)

    def test_no_dense_graph_or_controller_logic(self):
        source = Path("malecns_backend/embodiment/six_tibia_perturbation.py").read_text(
            encoding="utf-8").lower()
        self.assertNotIn("np.zeros((brain.n, brain.n", source)
        for forbidden in ("descending_drive =", "class gait", "class cpg", "engineered_cross_leg"):
            self.assertNotIn(forbidden, source)

    def test_physics_error_is_partial_preserves_rows_and_closes_without_retry(self):
        class FakePhysicsError(Exception): pass
        bodies = []
        class FakeRuntime:
            calls = 0
            def __init__(self, brain, body, interfaces, seed, apply, withheld_sensory=None):
                self.interfaces = interfaces; self.withheld_sensory = withheld_sensory
                self.events = SimpleNamespace(first_motor={leg: None for leg in LEG_ORDER})
                self.last_step_attempt = None
            def step(self, t):
                FakeRuntime.calls += 1
                snap = SixTibiaBodySnapshot(t / 1000, {leg: 0. for leg in LEG_ORDER},
                                            {leg: 0. for leg in LEG_ORDER})
                act = {leg: {"decoded_offset_rad": 0., "final_target_rad": 0.} for leg in LEG_ORDER}
                self.last_step_attempt = {"time_ms": t, "before": snap, "actuation": act}
                if t == 101: raise FakePhysicsError("Physics state is invalid: mjWARN_BADQACC")
                return {"time_ms": t, "after": snap, "actuation": act,
                    "counterfactual_sensory_increments": {leg: 1 for leg in LEG_ORDER},
                    "delivered_sensory_increments": {leg: 0 if leg == "RH" else 1 for leg in LEG_ORDER},
                    "motor": {leg: {"increments": {}, "filtered_hz": {}} for leg in LEG_ORDER},
                    "cns_spike_increment": 1, "spiking_neuron_indices": ()}
        def body_factory(interfaces):
            body = Body(interfaces); bodies.append(body); return body
        with patch("malecns_backend.embodiment.six_tibia_perturbation.SixTibiaRuntime", FakeRuntime):
            rows, _, summary = _run_condition("-RH", "RH", 500, 1, self.interfaces,
                object(), lambda data: object(), body_factory, (FakePhysicsError,))
        self.assertEqual(len(rows), 100); self.assertEqual(FakeRuntime.calls, 101)
        self.assertFalse(summary["completed"]); self.assertEqual(summary["completed_duration_ms"], 100)
        self.assertTrue(summary["metrics_scope"]["partial"])
        self.assertIsNotNone(summary["checkpoints"]["50"])
        self.assertIsNotNone(summary["checkpoints"]["100"])
        self.assertIsNone(summary["checkpoints"]["250"])
        self.assertEqual(summary["termination_reason"], "PHYSICS_INVALID_STATE")
        self.assertEqual(summary["mujoco_warning"], "mjWARN_BADQACC")
        self.assertTrue(bodies[0].closed)

    def test_programming_exception_propagates_and_body_closes(self):
        bodies = []
        class BrokenRuntime:
            def __init__(self, *args, **kwargs): pass
            def step(self, t): raise ValueError("programmer bug")
        def body_factory(interfaces):
            body = Body(interfaces); bodies.append(body); return body
        with patch("malecns_backend.embodiment.six_tibia_perturbation.SixTibiaRuntime", BrokenRuntime):
            with self.assertRaisesRegex(ValueError, "programmer bug"):
                _run_condition("-RH", "RH", 500, 1, self.interfaces, object(),
                               lambda data: object(), body_factory, (RuntimeError,))
        self.assertTrue(bodies[0].closed)

    def test_partial_influence_cells_have_duration_and_completion_semantics(self):
        baseline = {source: {target: 10 for target in LEG_ORDER} for source in LEG_ORDER}
        interventions = {source: {target: 12 for target in LEG_ORDER} for source in LEG_ORDER}
        metadata = {source: {"completed": source != "RH",
                             "completed_duration_ms": 496 if source == "RH" else 500}
                    for source in LEG_ORDER}
        matrix = motor_influence_matrix(baseline, interventions, metadata)
        self.assertEqual(matrix["RH"]["LF"],
                         {"value": 2, "complete": False, "observation_duration_ms": 496})
        self.assertTrue(matrix["LF"]["LF"]["complete"])


if __name__ == "__main__": unittest.main()
