"""Regression contracts for M7-A; these tests never execute science."""
import ast
from pathlib import Path

import pytest

from malecns_backend.embodiment import m7_spontaneous_locomotion as m7
from malecns_backend.embodiment import _windows_m7_spontaneous_locomotion_adapter as adapter
from malecns_backend.embodiment.integrated_whole_leg_readiness import EQUIVALENCE_FIELDS
from malecns_backend.embodiment.isolated_tier_b_motor_validation import (
    DECODER_MAX_RAD, HALF_ACTIVATION_HZ, OBSERVER_TAU_MS, SLEW_RAD_S,
)


def test_frozen_scientific_contract_and_parameters():
    assert (m7.SEED, m7.DURATION_MS) == (1, 5000)
    assert (m7.PHYSICS_DT_MS, m7.NEURAL_DT_MS) == (0.1, 0.5)
    assert (m7.EXPECTED_PHYSICS_TRANSITIONS, m7.EXPECTED_NEURAL_UPDATES) == (50000, 10000)
    assert m7.CONDITIONS == ("SPONTANEOUS_NEURAL_EMBODIMENT", "ALL_NEURAL_MOTOR_DISABLED")
    assert len(m7.ADMITTED_MOTOR) == 11 and len(m7.ADMITTED_SENSORY) == 6
    assert m7.ADMITTED_SENSORY == m7.ADMITTED_MOTOR[:6]
    assert m7.build_not_run()["baseline_only_actuator_count"] == 31
    assert (OBSERVER_TAU_MS, HALF_ACTIVATION_HZ, DECODER_MAX_RAD, SLEW_RAD_S) == (40.0, 17.0, 0.25, 4.0)
    assert tuple(m7.build_not_run()["equivalence_fields"]) == EQUIVALENCE_FIELDS


def test_motor_disabled_is_the_only_gate_difference():
    values = dict.fromkeys(m7.ADMITTED_MOTOR, 0.125)
    assert adapter.gate_contributions(values, m7.CONDITIONS[0], m7.ADMITTED_MOTOR) == values
    assert set(adapter.gate_contributions(values, m7.CONDITIONS[1], m7.ADMITTED_MOTOR).values()) == {0.0}
    with pytest.raises(RuntimeError): adapter.gate_contributions({}, m7.CONDITIONS[0], m7.ADMITTED_MOTOR)


def test_outputs_are_exclusive_and_abort_is_not_a_result(tmp_path):
    path = tmp_path / "value.json"
    m7.write_json_exclusive(path, {"ok": True})
    with pytest.raises(FileExistsError): m7.write_json_exclusive(path, {"ok": False})
    aborted = m7.write_aborted(tmp_path, RuntimeError("engineering"), 0, 1.0)
    assert aborted.name.startswith("ABORTED_IMPLEMENTATION_")
    assert '"classification": null' in aborted.read_text()


def test_fail_closed_rules_and_thresholds_are_frozen():
    required = ("canonical M6C lock mismatch", "protocol mismatch", "interface mismatch",
        "pre-intervention equivalence failure", "unauthorized actuator contribution",
        "hidden locomotion controller detected", "unexpected dynamic adhesion assistance",
        "telemetry corruption", "incomplete condition", "wrong physics transition count",
        "wrong neural update count")
    assert all(item in m7.FAIL_CLOSED for item in required)
    assert m7.THRESHOLDS == {"joint_divergence_rad": 1e-6, "com_displacement_m": 1e-6,
        "orientation_divergence_rad": 1e-6, "height_divergence_m": 1e-6,
        "oscillation_prominence_rad": 1e-4, "oscillation_min_extrema": 3,
        "rollover_body_up_z_max": 0.0, "fall_height_fraction": 0.5}


def test_no_environment_construction_inside_physics_loop():
    source = Path(adapter.__file__).with_name("_windows_m6c_live_condition.py").read_text()
    tree = ast.parse(source)
    loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While))]
    forbidden = {"_make_live", "enumerate_live_actuators", "load_malecns"}
    assert not any(isinstance(call.func, ast.Name) and call.func.id in forbidden
                   for loop in loops for call in ast.walk(loop) if isinstance(call, ast.Call))


def test_reducer_is_control_relative_and_never_claims_walking():
    np = pytest.importorskip("numpy")
    nphysics, nneural = 4, 2
    base = {"physics_qpos": np.zeros((nphysics, 49)), "physics_qvel": np.zeros((nphysics, 48)),
        "physics_joint_position": np.zeros((nphysics, 42)), "physics_body_position": np.zeros((nphysics, 3)),
        "physics_body_orientation": np.zeros((nphysics, 4)), "physics_contact_forces": np.zeros((nphysics, 36, 3)),
        "neural_aggregate_spikes": np.zeros(nneural, dtype=int),
        "neural_admitted_contributions": np.zeros((nneural, 11)),
        "neural_sensory_encoded": np.zeros((nneural, 6, 2))}
    base["physics_body_orientation"][:, 0] = 1
    table = [{"action_index": i, "leg": ("LF", "LM", "LH", "RF", "RM", "RH")[i % 6],
              "neural_motor_admission": i < 11} for i in range(42)]
    results = {name: {"raw_arrays": {key: value.copy() for key, value in base.items()}} for name in m7.CONDITIONS}
    summary = m7.reduce_results(results, table)
    assert summary["movement_categories"] == ["NO_MEASURABLE_NEURAL_PHYSICAL_EFFECT"]
    assert summary["walking"] is None
