"""Deterministic and non-intervention contracts for Milestone 5A."""
import ast
import json
from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
