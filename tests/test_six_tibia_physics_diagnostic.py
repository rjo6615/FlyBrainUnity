import json
import unittest
from types import SimpleNamespace

import numpy as np

from malecns_backend.embodiment.six_tibia import LEG_ORDER
from malecns_backend.embodiment.six_tibia_physics_diagnostic import (
    PhysicsRingRecorder, compare_runs, resolve_dof, run_physics_diagnostic)


class FakeModel:
    nv = 43
    nq = 50
    jnt_dofadr = np.array([0, 6, 7, 20, 39, 40])
    jnt_qposadr = np.array([0, 7, 8, 21, 45, 46])
    jnt_bodyid = np.array([1, 2, 3, 4, 9, 10])
    jnt_type = np.array([0, 3, 3, 3, 3, 3])
    jnt_limited = np.array([0, 1, 1, 1, 1, 1])
    jnt_range = np.array([[0, 0], [-1, 1], [-1, 1], [-1, 1], [-1.35, 1.3], [-1, 1]])
    actuator_trnid = np.array([[4, -1], [2, -1]])

    def id2name(self, object_id, kind):
        names = {("joint", 4): "joint_RHTibia", ("body", 9): "RHTibia",
                 ("actuator", 0): "joint_RHTibia"}
        return names.get((kind, object_id))


def interfaces():
    return {leg: SimpleNamespace(action_index=i, actuator_name=("joint_RHTibia" if leg == "RH"
                                                                 else f"joint_{leg}Tibia"))
            for i, leg in enumerate(LEG_ORDER)}


class DiagnosticTests(unittest.TestCase):
    def test_dof_lookup_uses_addresses_not_joint_index(self):
        result = resolve_dof(FakeModel(), 39, ("joint_RHTibia",))
        self.assertEqual(result["joint_id"], 4)
        self.assertEqual(result["joint_name"], "joint_RHTibia")
        self.assertEqual(result["body_name"], "RHTibia")
        self.assertEqual(result["dof_address_range"], [39, 40])
        self.assertEqual(result["qpos_address_range"], [45, 46])
        self.assertNotEqual(result["joint_id"], result["dof_index"])
        self.assertNotEqual(result["qpos_address_range"][0], result["dof_index"])
        self.assertTrue(result["is_six_tibia_actuator"])

    def test_unresolved_metadata_is_explicit(self):
        result = resolve_dof(FakeModel(), 99)
        self.assertFalse(result["resolved"])
        self.assertIn("outside", result["reason"])

    def test_ring_is_bounded_and_failure_is_separate(self):
        recorder = PhysicsRingRecorder(interfaces(), .001, duration_ms=2)
        recorder._snapshot = lambda body, action: {"n": action, "simulation_time_ms": action + .25}
        for value in range(4):
            token = recorder.before_physics_step(None, value)
            recorder.successful_physics_step = lambda body, action, state: setattr(recorder, "last_successful_state", state)
            recorder.successful_physics_step(None, value, token)
        failed = recorder.before_physics_step(None, 4); recorder.failed_physics_step(failed)
        self.assertEqual(recorder.capacity, 2)
        self.assertEqual([row["n"] for row in recorder.states], [3, 4])
        self.assertEqual(recorder.last_successful_state["n"], 3)
        self.assertEqual(recorder.failed_call_input["n"], 4)

    def test_snapshot_does_not_mutate_action_or_physics(self):
        model = FakeModel()
        data = SimpleNamespace(qpos=np.arange(50, dtype=float), qvel=np.arange(43, dtype=float),
            qacc=np.arange(43, dtype=float), ctrl=np.array([.2, .3]),
            actuator_force=np.array([1., 2.]), time=.49)
        physics = SimpleNamespace(model=model, data=data)
        obs = {"joints": np.vstack((np.arange(6.), np.arange(6.) + 10)),
               "fly": np.array([[1., 2., 3.]]), "fly_orientation": np.array([1., 0., 0., 0.])}
        body = SimpleNamespace(sim=SimpleNamespace(physics=physics), observation=obs)
        action = {"joints": np.arange(6.), "adhesion": np.zeros(6)}
        before_action = action["joints"].copy(); before_qpos = data.qpos.copy()
        recorder = PhysicsRingRecorder(interfaces(), .0001)
        recorder.set_control_context(491, {leg: {"decoded_offset_rad": i / 10}
                                           for i, leg in enumerate(LEG_ORDER)})
        state = recorder.before_physics_step(body, action)
        np.testing.assert_array_equal(action["joints"], before_action)
        np.testing.assert_array_equal(data.qpos, before_qpos)
        self.assertTrue(state["all_tracked_values_finite"])
        self.assertEqual(state["max_abs_qvel_dof"], 42)

    def test_comparison_and_json_serialization(self):
        def state(time, position, velocity):
            return {"simulation_time_ms": time, "joint_position": [position],
                "joint_velocity": velocity, "associated_actuators": [{"id": 0, "control": position}],
                "six_decoded_offsets_rad": {leg: position for leg in LEG_ORDER}}
        result = compare_runs([state(475, 1., 2.)], [state(475, 1.1, 3.)],
                              {"actuators": [{"id": 0}]})
        self.assertEqual(result["first_dof_trajectory_divergence_ms"], 475)
        self.assertAlmostEqual(result["checkpoints"]["475"]["joint_position_difference_rad"][0], .1)
        json.dumps(result, allow_nan=False)

    def test_matched_diagnostic_uses_existing_runner_and_has_no_retry_loop(self):
        names = run_physics_diagnostic.__code__.co_names
        self.assertIn("_run_condition", names)
        self.assertNotIn("retry", names)


if __name__ == "__main__":
    unittest.main()
