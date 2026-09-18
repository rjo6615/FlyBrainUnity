import json
import hashlib
from pathlib import Path

import pytest

from malecns_backend.embodiment import tactile_motor_equivalence_diagnostic as diagnostic


def _row(time, **updates):
    row = {"time_ms": time, "ctrl": [0.0, 0.0], "contact_set": [[1, 2]],
           "selected_contact_metadata": {"pair_present": True, "contacts": []},
           "qacc": [0.0], "qvel": [0.0], "qpos": [0.0],
           "contact_forces": [[0.0, 0.0, 1.0]], "resolution": {
               "ctrl": {"1": {"actuator_name": "joint_LMTibia", "leg": "LM"}},
               "qacc": {"0": {"joint_name": "joint_LMTibia", "body_name": "LMTibia", "dof": 0}},
               "qvel": {}, "qpos": {}}}
    row.update(updates)
    return row


def _initial(model=1, state=1, surface=1):
    return {"model": {"nq": model}, "state": {"qpos": [state]},
            "surface": {"geom_id": surface}}


def _contact(namespace="0", tarsus="LMTarsus5", **updates):
    contact = {
        "contact_index": 0, "geom1": 9, "geom2": 42,
        "geom1_name": "m5d2c_calibration_surface",
        "geom2_name": f"{namespace}/{tarsus}", "distance": -0.0001,
        "position": [1.0, 2.0, 3.0], "frame": list(range(9)),
        "friction": [1.0, 0.005, 0.0001, 0.0001, 0.0001],
        "mujoco_contact_wrench": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    }
    contact.update(updates)
    return {"pair_present": True, "contacts": [contact]}


def test_schema_forces_motor_application_off_and_preserves_original():
    report = diagnostic.base_report()
    assert report["protocol"]["neural_motor_application"] is False
    assert report["protocol"]["original_m5d4_result_preserved"] is True
    assert report["protocol"]["duration_ms"] >= 14.5
    assert report["protocol"]["physics_timestep_s"] == 0.0001
    assert report["safety"]["neural_output_applied"] is False


def test_first_divergences_are_independent_and_exact():
    enabled = [_row(0), _row(.1, qacc=[1.0]),
               _row(.2, qacc=[2.0], qvel=[.01]),
               _row(.3, qacc=[3.0], qvel=[.02], qpos=[.001]),
               _row(.4, ctrl=[0.0, .2], contact_set=[])]
    disabled = [_row(t) for t in (0, .1, .2, .3, .4)]
    result = diagnostic.compare_trajectories(enabled, disabled)
    assert result["qacc"]["first_differing_time_ms"] == .1
    assert result["qvel"]["first_differing_time_ms"] == .2
    assert result["qpos"]["first_differing_time_ms"] == .3
    assert result["ctrl"]["first_differing_time_ms"] == .4
    assert result["ctrl"]["first_differing_index"] == "[1]"
    assert result["ctrl"]["resolved_index"]["actuator_name"] == "joint_LMTibia"
    assert result["contact_set"]["first_differing_time_ms"] == .4


def test_initialization_classification_precedence():
    equal = diagnostic.compare_initialization(_initial(), _initial())
    empty = diagnostic.compare_trajectories([_row(0)], [_row(0)])
    assert diagnostic.classify(equal, empty, empty) == "EXACT_REPEATABILITY_CONFIRMED"
    model = diagnostic.compare_initialization(_initial(), _initial(model=2))
    assert diagnostic.classify(model, empty, empty) == "MODEL_CONFIGURATION_MISMATCH"
    state = diagnostic.compare_initialization(_initial(), _initial(state=2))
    assert diagnostic.classify(state, empty, empty) == "INITIAL_STATE_MISMATCH"


def test_repeatability_and_wrapper_classifications():
    initial = diagnostic.compare_initialization(_initial(), _initial())
    exact = diagnostic.compare_trajectories([_row(0)], [_row(0)])
    qpos_diff = diagnostic.compare_trajectories([_row(0, qpos=[1.0])], [_row(0)])
    ctrl_diff = diagnostic.compare_trajectories([_row(0, ctrl=[1.0, 0.0])], [_row(0)])
    assert diagnostic.classify(initial, qpos_diff, exact) == "PHYSICS_REPEATABILITY_FAILURE"
    assert diagnostic.classify(initial, exact, qpos_diff) == "CONDITION_WRAPPER_MISMATCH"
    assert diagnostic.classify(initial, exact, ctrl_diff) == "CONTROL_COMMAND_MISMATCH"
    assert diagnostic.classify(initial, exact, qpos_diff, "run_order") == "SHARED_STATE_LEAK"


@pytest.mark.parametrize("left,right", [
    ("0/LMTarsus5", "1/LMTarsus5"),
    ("2/LMTarsus5", "3/LMTarsus5"),
])
def test_instance_namespaces_have_the_same_semantic_identity(left, right):
    assert diagnostic.mujoco_object_identity(left) == diagnostic.mujoco_object_identity(right)


@pytest.mark.parametrize("right", ["1/LMTarsus4", "1/RMTarsus5"])
def test_genuinely_different_geometries_remain_different(right):
    assert diagnostic.mujoco_object_identity("0/LMTarsus5") != diagnostic.mujoco_object_identity(right)


def test_unqualified_calibration_surface_identity_remains_exact():
    surface = "m5d2c_calibration_surface"
    assert diagnostic.mujoco_object_identity(surface) == surface
    assert diagnostic.mujoco_object_identity(surface + "_other") != surface


def test_namespace_only_contact_metadata_is_exact_without_changing_numbers():
    enabled, disabled = _contact("0"), _contact("1")
    disabled["contacts"][0].update(geom1=109, geom2=142)
    result = diagnostic.compare_contact_metadata(enabled, disabled)
    assert result["exactly_equal"] is True
    assert enabled["contacts"][0]["distance"] == disabled["contacts"][0]["distance"]
    assert enabled["contacts"][0]["position"] == disabled["contacts"][0]["position"]


@pytest.mark.parametrize(("field", "different"), [
    ("distance", -0.0002),
    ("position", [1.0, 2.0, 4.0]),
    ("frame", list(range(8)) + [10]),
    ("friction", [0.9, 0.005, 0.0001, 0.0001, 0.0001]),
    ("mujoco_contact_wrench", [0.0, 0.0, 2.0, 0.0, 0.0, 0.0]),
])
def test_physical_contact_metadata_differences_fail(field, different):
    assert not diagnostic.compare_contact_metadata(
        _contact("0"), _contact("1", **{field: different}))["exactly_equal"]


@pytest.mark.parametrize(("quantity", "different"), [
    ("qacc", [1.0]), ("qvel", [1.0]), ("qpos", [1.0]),
    ("ctrl", [1.0, 0.0]), ("contact_forces", [[0.0, 0.0, 2.0]]),
    ("contact_set", [["LMTarsus4", "m5d2c_calibration_surface"]]),
])
def test_trajectory_physics_differences_fail(quantity, different):
    result = diagnostic.compare_trajectories([_row(0, **{quantity: different})], [_row(0)])
    assert result[quantity]["first_differing_time_ms"] == 0


def test_namespace_only_metadata_has_no_divergence_and_can_confirm_repeatability():
    a = [_row(0, selected_contact_metadata=_contact("0"))]
    b = [_row(0, selected_contact_metadata=_contact("1"))]
    comparison = diagnostic.compare_trajectories(a, b)
    assert all(item["first_differing_time_ms"] is None for item in comparison.values())
    assert diagnostic.earliest_physical_divergence(comparison) is None
    initial = diagnostic.compare_initialization(_initial(), _initial())
    assert diagnostic.classify(initial, comparison, comparison) == "EXACT_REPEATABILITY_CONFIRMED"


def test_checked_in_artifact_is_not_a_reinterpretation():
    path = Path("malecns_backend/embodiment/interface_output/tactile_motor_equivalence_diagnostic.json")
    report = json.loads(path.read_text())
    assert report["run_status"] == "COMPLETE"
    assert report["classification"] == "PHYSICS_REPEATABILITY_FAILURE"
    canonical = Path("malecns_backend/embodiment/interface_output/tactile_motor_loop.json")
    assert json.loads(canonical.read_text())["causal_classification"] == "PRE_MOTOR_EQUIVALENCE_FAILED"
    assert hashlib.sha256(canonical.read_bytes()).hexdigest() == (
        "4ddc41d4ec43c898a21eb0e2c64705a2bea3f08442b61b6e9ebfba24e85a201e")


def test_runner_has_hard_motor_boundary_and_fresh_instances():
    source = Path("malecns_backend/embodiment/tactile_motor_equivalence_diagnostic_audit.py").read_text()
    assert "apply_neural_offset=True" in source
    assert 'commands[ACTUATOR_INDICES[leg]] = measured[ACTUATOR_INDICES[leg]]' in source
    assert '"neural_application_flag": False' in source
    # Definition + four mandatory fresh runs + two conditional reversed runs.
    assert source.count("_run(") >= 7
