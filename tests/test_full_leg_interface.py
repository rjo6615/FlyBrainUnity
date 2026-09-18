"""Deterministic and non-intervention contracts for Milestone 5A."""
import ast
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from malecns_backend.embodiment import full_leg_interface as interface


class FullLegInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = interface.build_audit()
        cls.records = cls.audit["actuator_records"]

    def test_exactly_42_unique_physical_actuators(self):
        self.assertEqual(len(self.records), 42)
        self.assertEqual([r["actuator_index"] for r in self.records], list(range(42)))
        self.assertEqual(len({r["actuator_name"] for r in self.records}), 42)

    def test_every_actuator_has_one_joint_centric_record(self):
        keys = {(r["actuator_index"], r["actuator_name"]) for r in self.records}
        self.assertEqual(len(keys), 42)
        required = {"mujoco_metadata", "sensory_candidates", "motor_candidates", "axis", "provenance"}
        self.assertTrue(all(required <= set(record) for record in self.records))

    def test_confidence_and_tier_definitions(self):
        valid = set(interface.CONFIDENCE)
        for record in self.records:
            sensor, motor = record["sensory_confidence"], record["motor_confidence"]
            self.assertIn(sensor, valid)
            self.assertIn(motor, valid)
            expected, eligible, blockers = interface._tier(sensor, motor)
            self.assertEqual((record["activation_tier"], record["activation_eligible"], record["activation_blockers"]),
                             (expected, eligible, blockers))
            if "AMBIGUOUS" in (sensor, motor):
                self.assertFalse(record["activation_eligible"])
            if {sensor, motor} & {"MISSING", "UNMAPPED"}:
                self.assertFalse(record["activation_eligible"])

    def test_body_ids_are_sorted_unique_and_serialization_is_deterministic(self):
        first = interface.serialized_audit(self.audit)
        self.assertEqual(first, interface.serialized_audit(interface.build_audit()))
        json.loads(first)
        for record in self.records:
            for candidate in record["sensory_candidates"] + record["motor_candidates"]:
                self.assertEqual(candidate["body_ids"], sorted(set(candidate["body_ids"])))

    def test_all_six_tibia_interfaces_crosscheck(self):
        regression = self.audit["six_tibia_regression"]
        self.assertTrue(regression["passed"])
        self.assertEqual([item["leg"] for item in regression["interfaces"]], list(interface.LEG_ORDER))
        self.assertTrue(all(item["passed"] for item in regression["interfaces"]))

    def test_read_only_and_no_controller_logic(self):
        self.assertEqual(self.audit["non_intervention"], {
            "simulation_initialized": False, "physics_steps": 0,
            "actuators_commanded": False, "neural_constants_changed": False,
        })
        paths = [Path(interface.__file__), Path(interface.__file__).with_name("full_leg_interface_audit.py")]
        forbidden_imports = {"neural", "controller", "cpg", "gait"}
        forbidden_calls = {"step", "reset", "decode", "command"}
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
            imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
            self.assertFalse(any(word in module.lower() for word in forbidden_imports for module in imports))
            calls = {getattr(node.func, "attr", getattr(node.func, "id", "")) for node in ast.walk(tree) if isinstance(node, ast.Call)}
            self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_live_uses_compiled_transmissions_and_never_native_name_lookup(self):
        names = tuple(f"joint_{i}" for i in range(42))

        class CompiledModel:
            # A free root joint followed by 42 one-DOF joints.  Actuators are
            # deliberately reversed and have unrelated names.
            njnt, nq, nv, nu = 43, 49, 48, 42
            jnt_qposadr = [0] + list(range(7, 49))
            jnt_dofadr = [0] + list(range(6, 48))
            jnt_type = [0] + [3] * 42
            actuator_trntype = [0] * 42
            actuator_trnid = [[42 - i, -1] for i in range(42)]
            actuator_ctrlrange = [[-i - .5, i + .5] for i in range(42)]

            def id2name(self, object_id, kind):
                if kind == "joint":
                    return "root" if object_id == 0 else names[object_id - 1]
                if kind == "actuator":
                    return f"motor-unrelated-{object_id}"
                return None

        model = CompiledModel()
        physics = SimpleNamespace(model=model)
        calls = {"reset": 0, "step": 0, "native_lookup": 0}

        class Fly:
            def __init__(self, **kwargs):
                self.actuated_joints = names
                # This is the regression-triggering MJCF source object.  It
                # must never be sent to a native MuJoCo lookup.
                self.model = SimpleNamespace(tag="mujoco")

        class Simulation:
            def __init__(self, **kwargs):
                self.env = SimpleNamespace(physics=physics)

            def reset(self):
                calls["reset"] += 1

            def step(self, action):
                calls["step"] += 1

        def forbidden_name_lookup(*args):
            calls["native_lookup"] += 1
            raise AssertionError("native name lookup must not receive an MJCF element")

        fake_flygym = SimpleNamespace(Fly=Fly, SingleFlySimulation=Simulation)
        fake_mujoco = SimpleNamespace(
            mjtTrn=SimpleNamespace(mjTRN_JOINT=0), mj_name2id=forbidden_name_lookup)
        with patch.dict(sys.modules, {"flygym": fake_flygym, "mujoco": fake_mujoco}):
            records = interface.enumerate_live_actuators()

        self.assertEqual(len(records), 42)
        self.assertEqual(calls, {"reset": 0, "step": 0, "native_lookup": 0})
        first = records[0]["mujoco_metadata"]
        self.assertEqual(first["joint_id"], 1)
        self.assertEqual(first["actuator_id"], 41)
        self.assertEqual(first["actuator_name"], "motor-unrelated-41")
        self.assertNotEqual(first["actuator_name"], first["joint_name"])
        self.assertEqual(first["qpos_range"], [7, 8])
        self.assertEqual(first["dof_range"], [6, 7])
        last = records[-1]["mujoco_metadata"]
        self.assertEqual(last["qpos_range"], [48, 49])
        self.assertEqual(last["dof_range"], [47, 48])

    def test_missing_compiled_actuator_association_fails_loudly(self):
        class Model:
            njnt, nq, nv, nu = 1, 1, 1, 0
            actuator_trntype = []
            actuator_trnid = []

            def id2name(self, object_id, kind):
                return "unused"

        class Fly:
            def __init__(self, **kwargs): self.actuated_joints = ("not-an-actuator-name",)

        fake_flygym = SimpleNamespace(
            Fly=Fly, SingleFlySimulation=lambda **kwargs: SimpleNamespace(
                physics=SimpleNamespace(model=Model())))
        fake_mujoco = SimpleNamespace(mjtTrn=SimpleNamespace(mjTRN_JOINT=0))
        with patch.dict(sys.modules, {"flygym": fake_flygym, "mujoco": fake_mujoco}):
            with self.assertRaisesRegex(RuntimeError, "logical_action_index.*logical_name"):
                interface.enumerate_live_actuators()

    def test_namespaced_coxa_axes_use_flygym_ordered_actuator_contract(self):
        logical = ("joint_LFCoxa", "joint_LFCoxa_yaw", "joint_LFCoxa_roll")
        compiled_joints = tuple(f"fly/{name}" for name in logical)
        compiled_actuators = tuple(f"fly/actuator_position_{name}" for name in logical)

        class Element:
            def __init__(self, name, full_identifier):
                self.name, self.full_identifier = name, full_identifier

        class Model:
            njnt, nq, nv, nu = 3, 3, 3, 3
            jnt_qposadr = jnt_dofadr = [0, 1, 2]
            jnt_type = [3, 3, 3]
            actuator_trntype = [0, 0, 0]
            actuator_trnid = [[2, -1], [0, -1], [1, -1]]
            actuator_ctrlrange = [[-1, 1]] * 3

            def id2name(self, object_id, kind):
                if kind == "joint": return compiled_joints[object_id]
                if kind == "actuator":
                    return (compiled_actuators[2], compiled_actuators[0], compiled_actuators[1])[object_id]

        class Fly:
            def __init__(self, **kwargs):
                self.actuated_joints = logical
                # In the real construction the source MJCF element remains
                # unqualified: both fields report actuator_position_joint_LFCoxa
                # for index zero.  dm_control adds/replaces the prefix only in
                # the compiled name table during attachment.
                self._actuators = [Element(f"actuator_position_{name}",
                                           f"actuator_position_{name}")
                                   for name in logical]

        fake_flygym = SimpleNamespace(Fly=Fly, SingleFlySimulation=lambda **kwargs:
            SimpleNamespace(physics=SimpleNamespace(model=Model())))
        fake_mujoco = SimpleNamespace(mjtTrn=SimpleNamespace(mjTRN_JOINT=0))
        with patch.dict(sys.modules, {"flygym": fake_flygym, "mujoco": fake_mujoco}):
            records = interface.enumerate_live_actuators()

        metadata = [record["mujoco_metadata"] for record in records]
        self.assertEqual([item["actuator_id"] for item in metadata], [1, 2, 0])
        self.assertEqual([item["joint_name"] for item in metadata], list(compiled_joints))
        self.assertEqual([item["actuator_transmission_ids"] for item in metadata],
                         [[0, -1], [1, -1], [2, -1]])

    def test_compiled_attachment_prefix_is_derived_and_coxa_is_exact(self):
        logical = ("joint_LFCoxa", "joint_LFCoxa_roll", "joint_LFCoxa_yaw")

        for namespace in ("0", "another_attachment"):
            with self.subTest(namespace=namespace):
                joints = tuple(f"{namespace}/{name}" for name in logical)
                actuators = tuple(
                    f"{namespace}/actuator_position_{name}" for name in logical)

                class Element:
                    def __init__(self, name):
                        self.name = self.full_identifier = name

                class Model:
                    njnt = nq = nv = nu = 3
                    jnt_qposadr = jnt_dofadr = [0, 1, 2]
                    jnt_type = actuator_trntype = [0, 0, 0]
                    actuator_trnid = [[0, -1], [1, -1], [2, -1]]
                    actuator_ctrlrange = [[-1, 1]] * 3

                    def id2name(self, object_id, kind):
                        return joints[object_id] if kind == "joint" else actuators[object_id]

                class Fly:
                    def __init__(self, **kwargs):
                        self.actuated_joints = logical
                        self._actuators = [
                            Element(f"actuator_position_{name}") for name in logical]

                fake_flygym = SimpleNamespace(
                    Fly=Fly, SingleFlySimulation=lambda **kwargs:
                    SimpleNamespace(physics=SimpleNamespace(model=Model())))
                fake_mujoco = SimpleNamespace(mjtTrn=SimpleNamespace(mjTRN_JOINT=0))
                with patch.dict(sys.modules, {"flygym": fake_flygym, "mujoco": fake_mujoco}):
                    records = interface.enumerate_live_actuators()

                metadata = [record["mujoco_metadata"] for record in records]
                self.assertEqual([item["actuator_id"] for item in metadata], [0, 1, 2])
                self.assertEqual(metadata[0]["actuator_name"], actuators[0])
                self.assertEqual(metadata[0]["joint_name"], joints[0])
                self.assertNotIn(metadata[0]["joint_name"], joints[1:])

    def test_attachment_qualified_contract_resolves_all_42_in_action_order(self):
        names = tuple(record["actuator_name"] for record in self.records)
        namespace = "installation_specific"

        class Element:
            def __init__(self, name):
                self.name = self.full_identifier = name

        class Model:
            njnt = nq = nv = nu = 42
            jnt_qposadr = jnt_dofadr = list(range(42))
            jnt_type = actuator_trntype = [0] * 42
            actuator_trnid = [[i, -1] for i in range(42)]
            actuator_ctrlrange = [[-1, 1]] * 42

            def id2name(self, object_id, kind):
                stem = names[object_id]
                if kind == "joint":
                    return f"{namespace}/{stem}"
                return f"{namespace}/actuator_position_{stem}"

        class Fly:
            def __init__(self, **kwargs):
                self.actuated_joints = names
                self._actuators = [Element(f"actuator_position_{name}") for name in names]

        fake_flygym = SimpleNamespace(Fly=Fly, SingleFlySimulation=lambda **kwargs:
            SimpleNamespace(physics=SimpleNamespace(model=Model())))
        fake_mujoco = SimpleNamespace(mjtTrn=SimpleNamespace(mjTRN_JOINT=0))
        with patch.dict(sys.modules, {"flygym": fake_flygym, "mujoco": fake_mujoco}):
            records = interface.enumerate_live_actuators()

        self.assertEqual([record["index"] for record in records], list(range(42)))
        self.assertEqual([record["name"] for record in records], list(names))
        self.assertEqual(
            [record["mujoco_metadata"]["actuator_id"] for record in records],
            list(range(42)))

    def test_unresolved_coxa_reports_related_compiled_inventory(self):
        class Model:
            njnt = nq = nv = nu = 1
            jnt_qposadr = jnt_dofadr = jnt_type = [0]
            actuator_trntype, actuator_trnid = [0], [[0, -1]]
            actuator_ctrlrange = [[-1, 1]]
            def id2name(self, object_id, kind):
                return "fly/joint_LFCoxa_roll" if kind == "joint" else "fly/LFCoxa_roll_motor"
        class Fly:
            def __init__(self, **kwargs): self.actuated_joints = ("joint_LFCoxa",)
        fake_flygym = SimpleNamespace(Fly=Fly, SingleFlySimulation=lambda **kwargs:
            SimpleNamespace(physics=SimpleNamespace(model=Model())))
        fake_mujoco = SimpleNamespace(mjtTrn=SimpleNamespace(mjTRN_JOINT=0))
        with patch.dict(sys.modules, {"flygym": fake_flygym, "mujoco": fake_mujoco}):
            with self.assertRaises(RuntimeError) as caught:
                interface.enumerate_live_actuators()
        message = str(caught.exception)
        self.assertIn('"logical_action_index": 0', message)
        self.assertIn('"actuator_id": 0', message)
        self.assertIn('"transmission_ids": [0, -1]', message)
        self.assertIn('fly/joint_LFCoxa_roll', message)

    def test_live_ordering_mismatch_still_fails_loudly(self):
        live = [{"index": record["actuator_index"], "name": record["actuator_name"],
                 "mujoco_metadata": record["mujoco_metadata"]} for record in self.records]
        live[0]["name"], live[1]["name"] = live[1]["name"], live[0]["name"]
        with self.assertRaisesRegex(ValueError, "order disagrees"):
            interface.build_audit(live)


if __name__ == "__main__":
    unittest.main()
