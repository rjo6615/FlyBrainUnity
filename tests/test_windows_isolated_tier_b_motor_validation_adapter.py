"""M6B Windows adapter contract tests that need no live FlyGym install."""
import inspect
import json
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import isolated_tier_b_motor_validation as m6b
from malecns_backend.embodiment import _windows_isolated_tier_b_motor_validation_adapter as adapter


def test_adapter_contract_and_signatures():
    expected = {"run_canonical", "run_preflight", "resolve_joint_metadata",
        "calibrate_physical_sign", "compute_raw_contribution",
        "assert_isolated_admission", "TELEMETRY_FIELDS"}
    assert expected <= set(adapter.__all__)
    assert tuple(inspect.signature(adapter.run_canonical).parameters) == ("protocol", "output_path")
    assert tuple(inspect.signature(adapter.run_preflight).parameters) == ("protocol", "output_path")


def test_validated_live_path_is_reused():
    source = inspect.getsource(adapter)
    for symbol in ("_make_live", "MaleCNSBrain", "load_malecns",
                   "MatchedControlPipeline", "MotorActivityObserver",
                   "SensoryEncoder", "TactileContactEncoder"):
        assert symbol in source


def test_single_tier_b_admission_and_other_tiers_impossible():
    values = {name: 0.0 for name in m6b.TIER_B}; values[m6b.TIER_B[0]] = 0.1
    adapter.assert_isolated_admission(m6b.TIER_B[0], values)
    values[m6b.TIER_B[1]] = 0.1
    with pytest.raises(RuntimeError): adapter.assert_isolated_admission(m6b.TIER_B[0], values)
    with pytest.raises(RuntimeError):
        adapter.assert_isolated_admission(m6b.TIER_B[0], {**values, "joint_LFTibia": 0.0})
    assert not set(m6b.TIBIA_INDICES) & {
        item["action_index"] for item in m6b.build_not_run_artifact()["interfaces"]}


def test_matched_gate_is_the_only_pipeline_condition(monkeypatch):
    from malecns_backend.embodiment.motor import MotorSafety
    from malecns_backend.embodiment.tactile_motor_matched_control import MatchedControlPipeline
    enabled = MatchedControlPipeline(True, MotorSafety(-1, 1, .25, 4))
    disabled = MatchedControlPipeline(False, MotorSafety(-1, 1, .25, 4))
    left, right = enabled.update(.2, .1, .0005), disabled.update(.2, .1, .0005)
    assert left.raw_neural_contribution == right.raw_neural_contribution
    assert left.baseline_target == right.baseline_target
    assert left.admitted_neural_contribution == .1
    assert right.admitted_neural_contribution == 0


class FakePhysics:
    def __init__(self):
        self.model = SimpleNamespace(jnt_axis=np.array([[0., 0., 1.]]),
            jnt_range=np.array([[-.5, .5]]), actuator_ctrlrange=np.array([[-.4, .4]]),
            ngeom=1, id2name=lambda *args: "fly/LFTarsus5")
        self.data = SimpleNamespace(qpos=np.array([0.]), qvel=np.array([0.]),
                                    geom_xpos=np.zeros((1, 3)))
    def forward(self):
        self.data.geom_xpos[0] = [0., 0., self.data.qpos[0]]


def test_joint_metadata_safe_bounds_and_non_neural_sign_calibration():
    physics = FakePhysics()
    record = {"index": 6, "name": "joint_LFTarsus1", "mujoco_metadata": {
        "actuator_id": 0, "joint_id": 0, "qpos_range": [0, 1], "dof_range": [0, 1]}}
    metadata = adapter.resolve_joint_metadata(physics, record)
    assert metadata.joint_min == -.4 and metadata.joint_max == .4
    assert m6b.safe_contribution_bound(metadata.joint_min, metadata.joint_max, 0) == .25
    interface = {"leg": "LF", "joint_class": "Tarsus1"}
    result = adapter.calibrate_physical_sign(physics, metadata, interface)
    assert result.status == "RESOLVED" and result.coordinate_sign == 1
    assert result.evidence["uses_neural_behavior"] is False
    assert result.evidence["uses_walking_performance"] is False


def test_invalid_joint_metadata_and_unresolved_sign_fail_closed():
    physics = FakePhysics()
    with pytest.raises(RuntimeError):
        adapter.resolve_joint_metadata(physics, {"index": 1, "name": "bad", "mujoco_metadata": {}})
    metadata = adapter.JointMetadata(0, 0, 0, 0, 0, (0., 0., 1.), -.4, .4, -.4, .4)
    result = adapter.calibrate_physical_sign(physics, metadata, {"leg": "XX", "joint_class": "Femur"})
    assert result.status == "SIGN_UNRESOLVED" and result.coordinate_sign is None
    with pytest.raises(ValueError): adapter.compute_raw_contribution(1, 0, .25, 0)


def test_telemetry_completeness_and_same_update_milestones():
    assert set(m6b.EQUIVALENCE_FIELDS) <= set(adapter.TELEMETRY_FIELDS)
    assert {"positive_population_spikes", "negative_population_spikes",
        "raw_contribution", "admitted_contribution", "mechanical_limit_encounter",
        "physics_warnings"} <= set(adapter.TELEMETRY_FIELDS)
    assert m6b.milestones_ordered({f"B{i}": 4 for i in range(6)})


def test_preflight_never_calls_scientific_runner(monkeypatch, tmp_path):
    protocol = {"interfaces": [{"physical_joint": "joint_LFCoxa_yaw",
        "action_index": 2, "leg": "LF", "joint_class": "Coxa_yaw",
        "directional_motor_populations": [{"population": "p", "body_ids": [1], "annotation_direction": 1},
            {"population": "n", "body_ids": [2], "annotation_direction": -1}]}]}
    record = {"index": 2, "name": "joint_LFCoxa_yaw", "mujoco_metadata": {
        "actuator_id": 0, "joint_id": 0, "qpos_range": [0, 1], "dof_range": [0, 1]}}
    physics = FakePhysics(); obs = {"joints": np.zeros(42)}
    monkeypatch.setattr(adapter, "_live_setup", lambda p: (object(),
        SimpleNamespace(body_ids=np.array([1, 2])), {}, [record], {record["name"]: record}))
    monkeypatch.setattr(adapter, "_make_live", lambda *a: (SimpleNamespace(close=lambda: None), physics, obs, 0, 0))
    monkeypatch.setattr(adapter, "_run_condition", lambda *a, **k: pytest.fail("scientific run launched"))
    output = tmp_path / "preflight.json"
    report = adapter.run_preflight(protocol, output)
    assert report["scientific_run_executed"] is False
    assert report["scientific_run_number_consumed"] is None
    assert json.loads(output.read_text())["artifact_kind"] == "NON_SCIENTIFIC_PREFLIGHT"


def test_setup_failure_does_not_consume_run_one(monkeypatch, capsys):
    monkeypatch.setattr(adapter, "run_preflight", lambda *a: (_ for _ in ()).throw(RuntimeError("missing dependency")))
    assert m6b.main(["--preflight-windows"]) == 1
    assert "M6B WINDOWS PREFLIGHT FAIL" in capsys.readouterr().out
    report = m6b.build_not_run_artifact()
    assert report["provenance"]["scientific_run_number"] is None
    assert report["run_status"] == "NOT_RUN"
