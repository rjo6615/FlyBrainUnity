import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import tactile_motor_boundary_diagnostic as d
from malecns_backend.embodiment import tactile_motor_boundary_diagnostic_audit as runner
from malecns_backend.embodiment.tactile_motor_loop import ACTUATOR_INDICES


def row(time, **updates):
    value = {name: 0.0 for name in d.PIPELINE_STAGES}
    value.update({"time_ms": time, "action_joints": [0.0] * 42,
        "six_tibia_action": [0.0] * 6, "adhesion": [0.0] * 6,
        "ctrl": [0.0] * 42, "qacc": [0.0], "qvel": [0.0], "qpos": [0.0],
        "contact_set": [], "contact_forces": [[0.0]], **updates})
    return value


def test_locked_artifacts_are_read_only_inputs():
    source = Path(runner.M5D4).read_bytes(), Path(runner.M5D4A).read_bytes()
    d.base_report()
    assert source == (Path(runner.M5D4).read_bytes(), Path(runner.M5D4A).read_bytes())


def test_six_tibia_indices_locked():
    assert ACTUATOR_INDICES == {"LF": 5, "LM": 12, "LH": 19,
        "RF": 26, "RM": 33, "RH": 40}


def test_gate_and_zero_telemetry_semantics_are_explicit():
    audit = d.telemetry_audit()
    assert audit["answers"] == "B"
    assert audit["zero_decoded_offset_is_nonzero_applied_output"] is False
    assert "apply_neural_offset=apply_motor" in json.dumps(d.static_runner_audit()) or \
        "apply_motor" in json.dumps(d.static_runner_audit())


def test_logical_and_physical_boundaries_are_distinct():
    left, right = row(0, condition_application_flag=True), row(0, condition_application_flag=False)
    comparison = d.compare_traces([left], [right])
    assert comparison["logical"] is not None
    assert comparison["ctrl"] is None


def test_all_actuators_and_exact_physics_are_compared():
    left, right = row(0), row(0)
    right["action_joints"][41] = 1.0
    result = d.compare_traces([left], [right])
    assert result["all_42_position_actuator_commands"]["first_differing_index"] == "[41]"
    for field in ("qacc", "qvel", "qpos"):
        assert result[field] is None


def test_namespace_only_names_have_same_identity():
    assert d.actuator_identity("0/LMTibia", 12)["basename"] == \
        d.actuator_identity("fly/LMTibia", 12)["basename"]


def contact(namespace="0", geom="LHCoxa", force=1.0):
    return {"contact_count": 1, "selected_pair_present": True,
        "selected_contact_pairs": [], "all_contact_pairs": [{
            "geom1_id": 1, "geom1_name": "m5d2c_calibration_surface",
            "geom2_id": 2, "geom2_name": f"{namespace}/{geom}", "force": force}]}


def test_general_contact_comparison_reuses_m5d4a_semantic_identity():
    left, right = row(0, contact_set=contact("0")), row(0, contact_set=contact("1"))
    assert d.compare_traces([left], [right])["contact"] is None
    assert d.mujoco_object_identity("0/LHCoxa") == d.mujoco_object_identity("1/LHCoxa")


def test_general_contact_geometry_pair_is_unordered():
    left, right = contact("0"), contact("1")
    pair = right["all_contact_pairs"][0]
    pair["geom1_id"], pair["geom2_id"] = pair["geom2_id"], pair["geom1_id"]
    pair["geom1_name"], pair["geom2_name"] = pair["geom2_name"], pair["geom1_name"]
    assert d.compare_contact_sets(left, right)["exactly_equal"]


def test_genuine_geometry_and_numeric_contact_differences_remain_exact():
    left = row(0, contact_set=contact("0"))
    geometry = row(0, contact_set=contact("1", "RHCoxa"))
    numeric = row(0, contact_set=contact("1", force=1.0000000000000002))
    assert d.compare_traces([left], [geometry])["contact"] is not None
    assert d.compare_traces([left], [numeric])["contact"] is not None


def test_numeric_id_reuse_is_not_aliasing_but_simultaneous_aliasing_is_detected():
    recycled_enabled_ids = {"decoder": 12345}
    recycled_disabled_ids = {"brain": 12345}
    assert set(recycled_enabled_ids.values()) & set(recycled_disabled_ids.values())
    assert d.shared_mutable_aliases({"decoder": object()}, {"brain": object()}) == []
    shared = []
    assert d.shared_mutable_aliases({"decoder": shared}, {"brain": shared}) == [
        {"enabled": "decoder", "disabled": "brain"}]


def test_earliest_pipeline_stage_uses_declared_order():
    left, right = row(0), row(0)
    right["previous_target"] = 2.0
    right["final_target"] = 3.0
    found = d.first_difference([left], [right], d.PIPELINE_STAGES)
    assert found["variable"] == "previous_target"


def test_evidence_based_classification():
    assert d.classify({"ctrl": None, "qpos": {"time_ms": 1}}) == \
        "PHYSICAL_DIVERGENCE_WITHOUT_CONTROL_DIVERGENCE"
    comparison = {"ctrl": {"time_ms": 1}, "qpos": {"time_ms": 2},
                  "pipeline": {"variable": "previous_target"}}
    assert d.classify(comparison, 14.5) == "BASE_HOLD_STATE_DIVERGENCE"
    assert set(d.CLASSIFICATIONS)


def test_index_12_zero_neural_offset_physical_target_is_early_intervention():
    left, right = row(4.0), row(4.0)
    left["action_joints"][12] = -0.004521378919482231
    right["action_joints"][12] = -0.004795606713742018
    left["ctrl"][12] = left["action_joints"][12]
    right["ctrl"][12] = right["action_joints"][12]
    # All neural contribution fields retain the row helper's exact zero.
    comparison = d.compare_traces([left], [right])
    assert comparison["all_42_position_actuator_commands"]["first_differing_index"] == "[12]"
    assert d.classify(comparison, reported_applied_ms=14.5) == \
        "EARLY_CONTROL_INTERVENTION_FOUND"


def test_protocol_is_fixed_and_serialization_deterministic():
    report = d.base_report(); protocol = report["protocol"]
    assert (protocol["seed"], protocol["duration_ms"], protocol["physics_timestep_s"],
            protocol["neural_timestep_ms"]) == (1, 15.0, 0.0001, 0.5)
    assert protocol["canonical_100ms_run_permitted"] is False
    assert d.serialize(report) == d.serialize(report)


def test_provenance_fails_closed():
    with pytest.raises(RuntimeError):
        d.semantic_digest({"run_status": "COMPLETE"}, {"classification": "LOCKED"})
    with pytest.raises(RuntimeError):
        d.semantic_digest({"classification": "wrong"}, {"classification": "LOCKED"})


def test_checked_in_artifact_is_truthful_not_run():
    artifact = json.loads((Path(__file__).parents[1] /
        "malecns_backend/embodiment/interface_output/tactile_motor_boundary_diagnostic.json").read_text())
    assert artifact["run_status"] == "NOT_RUN"
    assert artifact["classification"] is None
    assert artifact["effective_physical_intervention"] is None
