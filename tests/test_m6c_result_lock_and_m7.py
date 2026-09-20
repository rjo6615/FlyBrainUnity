import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import m6c_result_lock as lock
from malecns_backend.embodiment import m7_spontaneous_locomotion as m7


def test_lock_records_raw_bytes_and_refuses_replacement(tmp_path):
    canonical = tmp_path / "canonical.json"
    conditions = {name: {"complete": True} for name in lock.CONDITIONS}
    canonical.write_text(json.dumps({
        "schema": "M6C.0", "seed": 1, "duration_ms": 500,
        "classification": "INTEGRATED_MULTI_LEG_CAUSALITY_CONFIRMED",
        "run_status": "COMPLETE", "scientific_run_executed": True,
        "m7_readiness": "M7_SPONTANEOUS_LOCOMOTION_EXPERIMENT_READY",
        "condition_results": conditions,
        "provenance": {"m6a_sha256": "a", "m6b_sha256": "b", "tier_a_sha256": "c"},
    }), encoding="utf-8")
    result = lock.build_lock(canonical)
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
        lock.build_lock(path)


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
