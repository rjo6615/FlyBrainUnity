"""M6A whole-leg motor mapping audit contracts."""
import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import whole_leg_motor_mapping_audit as m6a


@pytest.fixture(scope="module")
def audit():
    return m6a.build_audit()


def test_exactly_42_actuators_seven_per_leg_in_authoritative_order(audit):
    physical = audit["physical_actuators"]
    assert len(physical) == 42
    assert [item["global_action_index"] for item in physical] == list(range(42))
    for leg in m6a.LEGS:
        records = [item for item in physical if item["leg"] == leg]
        assert len(records) == 7
        assert [item["canonical_joint_class"] for item in records] == list(m6a.JOINT_CLASSES)


def test_six_tibia_indices_and_tier_a_are_immutable(audit):
    assert audit["six_tibia_regression"]["passed"]
    assert {item["leg"]: item["action_index"]
            for item in audit["six_tibia_regression"]["interfaces"]} == m6a.TIBIA_INDICES
    tibiae = [item for item in audit["per_actuator"]
              if item["global_action_index"] in m6a.TIBIA_INDICES.values()]
    assert len(tibiae) == 6
    assert all(item["motor_embodiment_tier"] == "A" for item in tibiae)
    assert all(item["decoder_readiness"] == "VALIDATED_EXISTING" for item in tibiae)


def test_every_actuator_has_one_known_classification_and_tier(audit):
    records = audit["per_actuator"]
    assert len(records) == 42
    assert all(item["association_classification"] in m6a.ASSOCIATION_CLASSES for item in records)
    assert all(item["motor_mapping_status"] in m6a.MAPPING_STATUSES for item in records)
    assert all(item["decoder_readiness"] in m6a.DECODER_READINESS for item in records)
    assert all(item["directional_structure"] in m6a.DIRECTIONAL_CLASSES for item in records)
    assert all(item["motor_embodiment_tier"] in m6a.TIERS for item in records)


def test_tier_b_requires_unique_explicit_directional_evidence(audit):
    tier_b = [item for item in audit["per_actuator"] if item["motor_embodiment_tier"] == "B"]
    assert tier_b
    assert all(item["candidates"] for item in tier_b)
    assert all(item["unique_physical_mapping"] for item in tier_b)
    assert all(item["explicit_signed_pair"] for item in tier_b)
    assert all(item["explicit_directional_terminology"] for item in tier_b)
    assert all(item["decoder_readiness"] == "DIRECTIONALLY_RESOLVABLE" for item in tier_b)


def test_m6b_eligibility_excludes_ambiguity_conflicts_and_existing_tibiae(audit):
    records = {item["actuator"]: item for item in audit["per_actuator"]}
    assert audit["m6b_eligible"] == [name for name, item in records.items() if item["motor_embodiment_tier"] == "B"]
    for name in audit["m6b_eligible"]:
        item = records[name]
        assert item["unique_physical_mapping"]
        assert not item["unresolved_shared_population_conflict"]
        assert item["decoder_readiness"] == "DIRECTIONALLY_RESOLVABLE"
        assert item["global_action_index"] not in m6a.TIBIA_INDICES.values()


def test_reverse_mapping_exactly_agrees_with_forward_mapping(audit):
    expected = {}
    for actuator in audit["per_actuator"]:
        for candidate in actuator["candidates"]:
            expected.setdefault(candidate["population"], []).append({
                "actuator": actuator["actuator"], "classification": candidate["classification"]})
    actual = {record["population"]: record["candidate_actuators"]
              for record in audit["reverse_population_mapping"]}
    assert actual == {name: sorted(items, key=lambda x: x["actuator"])
                      for name, items in expected.items()}
    assert all(len({item["actuator"] for item in conflict["candidate_actuators"]}) > 1
               for conflict in audit["shared_population_conflicts"])


def test_summary_and_breakdowns_are_closed_and_consistent(audit):
    summary = audit["summary"]
    assert summary["total_physical_actuators"] == 42
    assert summary["tier_counts"] == {"A": 6, "B": 14, "C": 18, "D": 4}
    assert summary["actuators_with_any_annotation_backed_motor_candidate"] == 38
    for dimension in ("by_leg", "by_joint_class", "by_left_right", "by_thoracic_segment"):
        assert sum(row["total"] for row in summary[dimension].values()) == 42
        assert all(sum(row["tiers"].values()) == row["total"]
                   for row in summary[dimension].values())
    assert sum(not population["present_in_unmappedMotor"]
               for population in audit["motor_populations"]) == 102
    assert sum(population["present_in_unmappedMotor"]
               for population in audit["motor_populations"]) == 285


def test_output_is_deterministic_and_committed_artifact_is_current(audit):
    first = m6a.serialized_audit(audit)
    second = m6a.serialized_audit(m6a.build_audit())
    assert first == second
    assert json.loads(first)["schema"] == "M6A.0"
    assert m6a.OUTPUT.read_text(encoding="utf-8") == first


def test_provenance_failure_is_fail_closed(tmp_path):
    fake = tmp_path / "authoritative.json"
    fake.write_text("changed", encoding="utf-8")
    relative = str(fake.relative_to(m6a.ROOT)) if fake.is_relative_to(m6a.ROOT) else None
    if relative is None:
        # verify_provenance resolves relative to ROOT, so create the temporary
        # fixture below it when pytest's tmpdir is outside the repository.
        fake = m6a.ROOT / ".m6a-provenance-test"
        fake.write_text("changed", encoding="utf-8")
        relative = fake.name
    try:
        with pytest.raises(m6a.AuditFailure) as exc:
            m6a.build_audit(provenance_locks={relative: ("0" * 64, "raw-bytes")})
        assert exc.value.classification == "PROVENANCE_FAILURE"
    finally:
        if fake.parent == m6a.ROOT:
            fake.unlink(missing_ok=True)


def test_non_intervention_contract(audit):
    assert audit["non_intervention"] == {
        "simulation_initialized": False, "physics_steps": 0,
        "actuators_commanded": False, "decoders_added": False,
        "sensory_encoders_added": False, "neural_dynamics_changed": False,
    }
