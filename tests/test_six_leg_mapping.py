"""Focused, lightweight contract tests for the read-only Milestone 4A map."""
import ast
import json
from pathlib import Path
import unittest

from malecns_backend.embodiment import six_leg_audit as audit
from malecns_backend.embodiment.mappings import load_selected_pathway


class SixLegMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = audit.generate_map()
        cls.text = audit.serialized_map(cls.data)
        cls.populations = (
            cls.data["population_inventory"]["leg_sensory"]
            + cls.data["population_inventory"]["leg_motor"]
        )

    def test_generation_is_deterministic_and_committed_map_is_current(self):
        self.assertEqual(self.text, audit.serialized_map(audit.generate_map()))
        self.assertEqual(self.text, audit.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(audit.main(["--check"]), 0)

    def test_every_stored_id_resolves_exactly_and_has_no_duplicates(self):
        source = json.loads(audit.INTERFACE_MAP.read_text(encoding="utf-8"))
        exact_source_lists = {tuple(record["body_ids"]) for record in source["populations"]}
        for pop in self.populations:
            ids = pop["body_ids"]
            self.assertIn(tuple(ids), exact_source_lists, pop["name"])
            self.assertEqual(len(ids), len(set(ids)), pop["name"])
            self.assertEqual(pop["resolved_neuron_count"], len(ids))

    def test_signed_64_bit_ids_survive_json_round_trip(self):
        again = json.loads(self.text)
        before = [i for pop in self.populations for i in pop["body_ids"]]
        after = [i for key in ("leg_sensory", "leg_motor")
                 for pop in again["population_inventory"][key] for i in pop["body_ids"]]
        self.assertEqual(before, after)
        self.assertTrue(all(-(2**63) <= value < 2**63 for value in after))

    def test_legs_actuators_indices_and_separate_interfaces(self):
        inventory = self.data["actuator_inventory"]
        self.assertEqual(len(inventory), 42)
        self.assertEqual([a["action_index"] for a in inventory], list(range(42)))
        names = {a["name"] for a in inventory}
        self.assertEqual(len(names), 42)
        for leg in self.data["legs"]:
            for joint in leg["joints"]:
                actuator = joint["actuator"]
                self.assertIn(actuator["name"], names)
                self.assertEqual(actuator["side"], leg["side"])
                self.assertEqual(actuator["segment"], leg["segment"])
                self.assertIsNot(joint["sensory"], joint["motor"])
                for interface in (joint["sensory"], joint["motor"]):
                    self.assertIn(interface["status"], audit.ALLOWED_STATUS)
                    for pop in interface["populations"]:
                        self.assertEqual(pop["side"], leg["side"])
                        self.assertEqual(pop["segment"], leg["segment"])

    def test_authoritative_flygym_order_and_preserved_tibias(self):
        expected_dofs = ("Coxa", "Coxa_roll", "Coxa_yaw", "Femur",
                         "Femur_roll", "Tibia", "Tarsus1")
        expected_tibias = {"LF": 5, "LM": 12, "LH": 19,
                           "RF": 26, "RM": 33, "RH": 40}
        for leg in self.data["legs"]:
            self.assertEqual(
                tuple(joint["actuator"]["name"].removeprefix(f"joint_{leg['leg']}")
                      for joint in leg["joints"]), expected_dofs)
            tibia = next(j for j in leg["joints"]
                         if j["actuator"]["anatomical_joint"] == "tibia")
            self.assertEqual(tibia["actuator"]["action_index"], expected_tibias[leg["leg"]])

    def test_ambiguity_and_asymmetry_are_preserved(self):
        coxa = self.data["legs"][0]["joints"][0]
        self.assertEqual(coxa["sensory"]["status"], "AMBIGUOUS")
        hair = next(x for x in self.data["symmetry_audit"] if x["family"] == "hair plate T# SIDE")
        self.assertIn("T1 right", hair["missing"])
        self.assertFalse(hair["size_symmetric"])

    def test_m3d_reference_is_value_equivalent(self):
        selected = load_selected_pathway()
        reference = self.data["validated_m3d_reference"]
        self.assertEqual(reference["sensor"], selected.sensor.name)
        self.assertEqual(reference["sensor_count"], len(selected.sensor.body_ids))
        self.assertEqual(reference["extensor_body_ids"], list(selected.extensor.body_ids))
        self.assertEqual(reference["flexor_body_ids"], list(selected.flexor.body_ids))
        self.assertEqual(reference["actuator"], selected.flygym_joint_name)
        self.assertEqual(reference["action_index"], selected.flygym_joint_index)

    def test_audit_is_structurally_non_intervening(self):
        tree = ast.parse(Path(audit.__file__).read_text(encoding="utf-8"))
        imported = {alias.name for node in ast.walk(tree)
                    if isinstance(node, ast.Import) for alias in node.names}
        imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        forbidden = ("flygym", "body", "loop", "motor", "causal", "controller", "cpg", "gait")
        self.assertFalse(any(any(word in module.lower() for word in forbidden) for module in imported))
        calls = {getattr(node.func, "attr", getattr(node.func, "id", ""))
                 for node in ast.walk(tree) if isinstance(node, ast.Call)}
        self.assertTrue({"step", "reset", "command", "decode"}.isdisjoint(calls))
        self.assertEqual(self.data["non_intervention"], {
            "actuators_commanded": False, "simulation_initialized": False,
            "scientific_parameters_changed": False,
        })


if __name__ == "__main__":
    unittest.main()
