import json
from pathlib import Path

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


def test_checked_in_artifact_is_not_a_reinterpretation():
    path = Path("malecns_backend/embodiment/interface_output/tactile_motor_equivalence_diagnostic.json")
    report = json.loads(path.read_text())
    assert report["run_status"] == "NOT_RUN"
    assert report["classification"] is None
    assert Path("malecns_backend/embodiment/interface_output/tactile_motor_loop.json").exists()


def test_runner_has_hard_motor_boundary_and_fresh_instances():
    source = Path("malecns_backend/embodiment/tactile_motor_equivalence_diagnostic_audit.py").read_text()
    assert "apply_neural_offset=True" in source
    assert 'commands[ACTUATOR_INDICES[leg]] = measured[ACTUATOR_INDICES[leg]]' in source
    assert '"neural_application_flag": False' in source
    # Definition + four mandatory fresh runs + two conditional reversed runs.
    assert source.count("_run(") >= 7
