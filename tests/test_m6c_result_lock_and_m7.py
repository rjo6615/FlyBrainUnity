import json
import hashlib
from pathlib import Path

import pytest

from malecns_backend.embodiment import m6c_result_lock as lock
from malecns_backend.embodiment import m7_spontaneous_locomotion as m7


def canonical_payload(condition_names=None):
    condition_names = condition_names or lock.CONDITIONS
    conditions = {name: {"pre_intervention_equivalence": True,
                         "physics_instability": False} for name in condition_names}
    return {
        "schema": "M6C.0", "seed": 1, "duration_ms": 500,
        "classification": "INTEGRATED_MULTI_LEG_CAUSALITY_CONFIRMED",
        "run_status": "COMPLETE", "scientific_run_executed": True,
        "m7_readiness": "M7_SPONTANEOUS_LOCOMOTION_EXPERIMENT_READY",
        "condition_results": conditions,
        "admitted_motor_interfaces": list(lock.TIER_A + lock.EXPECTED_TIER_B),
        "sensory_interfaces": [{"actuator": name} for name in lock.TIER_A],
        "hidden_locomotion_audit": {"hidden_locomotion_assistance_executed": False},
        "provenance": {"verified": True, "hash_policy": "raw-bytes",
            "m6a_sha256": lock.M6A_SHA256, "m6b_sha256": lock.M6B_SHA256,
            "tier_a_sha256": lock.TIER_A_SHA256},
    }


def write_and_build(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return lock.build_lock(path, expected_sha256=digest)


def test_lock_records_raw_bytes_accepts_nonsemantic_order_and_refuses_replacement(tmp_path):
    canonical = tmp_path / "canonical.json"
    result = write_and_build(canonical, canonical_payload(reversed(lock.CONDITIONS)))
    assert result["raw_sha256"] == lock.raw_identity(canonical)[0]
    assert result["byte_size"] == canonical.stat().st_size
    destination = tmp_path / "lock.json"
    lock.write_lock_exclusive(result, destination)
    with pytest.raises(FileExistsError):
        lock.write_lock_exclusive(result, destination)


def test_lock_fails_closed_on_noncanonical_identity(tmp_path):
    path = tmp_path / "wrong.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="identity checks failed"):
        lock.build_lock(path, expected_sha256=lock.raw_identity(path)[0])


@pytest.mark.parametrize("names", [lock.CONDITIONS[:-1], lock.CONDITIONS + ("EXTRA",)])
def test_lock_rejects_missing_or_extra_condition(tmp_path, names):
    path = tmp_path / "conditions.json"
    with pytest.raises(ValueError, match="condition_membership"):
        write_and_build(path, canonical_payload(names))


def test_lock_rejects_duplicate_condition_key(tmp_path):
    path = tmp_path / "duplicate.json"
    payload = canonical_payload()
    text = json.dumps(payload).replace('"condition_results": {',
        '"condition_results": {"INTEGRATED_NEURAL_MOTOR_ENABLED": {},', 1)
    path.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(lock.DuplicateJSONKeyError):
        lock.build_lock(path, expected_sha256=digest)


def test_lock_rejects_wrong_provenance_and_incomplete_condition(tmp_path):
    wrong = canonical_payload(); wrong["provenance"]["m6b_sha256"] = "wrong"
    with pytest.raises(ValueError, match="provenance"):
        write_and_build(tmp_path / "provenance.json", wrong)
    incomplete = canonical_payload()
    incomplete["condition_results"][lock.CONDITIONS[1]]["physics_instability"] = True
    with pytest.raises(ValueError, match="condition_completion"):
        write_and_build(tmp_path / "incomplete.json", incomplete)


def test_modified_artifact_cannot_masquerade_as_canonical(tmp_path):
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps(canonical_payload()), encoding="utf-8")
    digest, _ = lock.raw_identity(path)
    path.write_bytes(path.read_bytes() + b"\n")
    assert lock.raw_identity(path)[0] != digest
    with pytest.raises(ValueError, match="raw SHA256 mismatch"):
        lock.build_lock(path, expected_sha256=digest)


def test_m7_not_run_frozen_interfaces_and_preflight():
    protocol = m7.build_not_run()
    assert protocol["run_status"] == "NOT_RUN"
    assert protocol["scientific_run_executed"] is False
    assert (protocol["expected_physics_transitions"], protocol["expected_neural_updates"]) == (50000, 10000)
    assert tuple(protocol["admitted_motor_interfaces"]) == m7.ADMITTED_MOTOR
    assert tuple(protocol["admitted_sensory_interfaces"]) == m7.ADMITTED_SENSORY
    assert protocol["baseline_only_actuator_count"] == 31
    assert m7.validate_preflight(protocol)["scientific_run_executed"] is False


def test_m7_categories_are_nonexclusive_descriptions():
    assert m7.movement_categories(joint_divergent_legs=0, posture_changed=False,
        net_displacement=False, oscillatory=False) == ["NO_MEASURABLE_NEURAL_PHYSICAL_EFFECT"]
    assert m7.movement_categories(joint_divergent_legs=3, posture_changed=True,
        net_displacement=True, oscillatory=True) == ["MULTI_LEG_MOVEMENT",
            "BODY_POSTURAL_CHANGE", "NET_BODY_DISPLACEMENT", "REPEATED_OR_OSCILLATORY_LIMB_ACTIVITY"]


def test_m7_artifacts_cannot_be_overwritten(tmp_path):
    destination = tmp_path / "result.json"
    m7.write_json(destination, m7.build_not_run())
    with pytest.raises(FileExistsError):
        m7.write_json(destination, m7.build_not_run())
