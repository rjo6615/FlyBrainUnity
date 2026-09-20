"""M6B Windows adapter contract tests that need no live FlyGym install."""
import ast
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
        "assert_isolated_admission", "assert_physical_admission", "TELEMETRY_FIELDS"}
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
        item["action_index"] for item in m6b.build_not_run_artifact()["interfaces"]
        if item["physical_joint"] in m6b.TIER_B}
    all_names = list(m6b.ANNOTATION_TIER_B) + ["joint_LFTibia", "joint_LFCoxa", "joint_LFTarsus2"]
    full = {name: 0.0 for name in all_names}; full[m6b.TIER_B[0]] = .1
    adapter.assert_physical_admission(m6b.TIER_B[0], full, all_names)
    full["joint_LFTibia"] = .1
    with pytest.raises(RuntimeError, match="excluded actuator"):
        adapter.assert_physical_admission(m6b.TIER_B[0], full, all_names)


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
        def id2name(*args):
            kind = next((x for x in args if isinstance(x, str)), "")
            return {"actuator": "fly/actuator_position_joint_LFTarsus1",
                    "joint": "fly/joint_LFTarsus1",
                    "geom": "fly/LFTarsus5"}.get(kind)
        self.model = SimpleNamespace(jnt_axis=np.array([[0., 0., 1.]]),
            jnt_range=np.array([[-.5, .5]]), actuator_ctrlrange=np.array([[-.4, .4]]),
            jnt_limited=np.array([1]), actuator_ctrllimited=np.array([1]),
            actuator_forcelimited=np.array([0]), actuator_forcerange=np.array([[0., 0.]]),
            actuator_trntype=np.array([0]), actuator_trnid=np.array([[0, -1]]),
            actuator_gear=np.array([[1., 0., 0., 0., 0., 0.]]),
            actuator_gainprm=np.array([[10., 0., 0.]]),
            actuator_biasprm=np.array([[0., -10., 0.]]), jnt_type=np.array([3]),
            ngeom=1, id2name=id2name)
        self.data = SimpleNamespace(qpos=np.array([0.]), qvel=np.array([0.]),
                                    ctrl=np.array([0.]), geom_xpos=np.zeros((1, 3)))
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


def test_limit_domains_and_enable_flags_are_respected():
    record = {"index": 6, "name": "joint_LFTarsus1", "mujoco_metadata": {
        "actuator_id": 0, "joint_id": 0, "qpos_range": [0, 1], "dof_range": [0, 1]}}
    physics = FakePhysics()
    # Same-domain active ranges really are intersected.
    assert adapter.resolve_joint_metadata(physics, record).joint_min == -.4
    physics.model.actuator_ctrlrange[0] = [2., 3.]
    with pytest.raises(RuntimeError, match="same-domain limits.*joint_LFTarsus1"):
        adapter.resolve_joint_metadata(physics, record)

    # A non-position ctrl range is not an angle and must not be intersected.
    physics.model.id2name = lambda *args: "fly/actuator_torque_joint_LFTarsus1"
    diagnostic = adapter.inspect_limit_metadata(physics, record)
    assert diagnostic["classification"] == "VALID_BUT_DIFFERENT_DOMAINS"
    with pytest.raises(RuntimeError, match="not an absolute unit-gear"):
        adapter.resolve_joint_metadata(physics, record)

    # MuJoCo's [0, 0] for an unlimited joint is an inactive placeholder, not
    # an empty mechanical range.  The active position-control range remains.
    physics = FakePhysics()
    physics.model.jnt_limited[0] = 0
    physics.model.jnt_range[0] = [0., 0.]
    metadata = adapter.resolve_joint_metadata(physics, record)
    assert (metadata.joint_min, metadata.joint_max) == (-.4, .4)
    assert metadata.limit_classification == "JOINT_RANGE_UNAVAILABLE"


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
    protocol = {"interfaces": [{"physical_joint": "joint_LFFemur",
        "action_index": 3, "leg": "LF", "joint_class": "Femur", "coordinate_sign": -1,
        "mechanical_calibration": {"evidence": {}},
        "directional_motor_populations": [{"population": "p", "body_ids": [1], "annotation_direction": 1},
            {"population": "n", "body_ids": [2], "annotation_direction": -1}]}]}
    record = {"index": 3, "name": "joint_LFFemur", "mujoco_metadata": {
        "actuator_id": 0, "joint_id": 0, "qpos_range": [0, 1], "dof_range": [0, 1]}}
    physics = FakePhysics(); obs = {"joints": np.zeros(42)}
    monkeypatch.setattr(adapter, "_live_setup", lambda p: (object(),
        SimpleNamespace(body_ids=np.array([1, 2])), {}, [record], {record["name"]: record}))
    monkeypatch.setattr(adapter, "_make_live", lambda *a: (SimpleNamespace(close=lambda: None), physics, obs, 0, 0))
    monkeypatch.setattr(adapter, "_run_condition", lambda *a, **k: pytest.fail("scientific run launched"))
    counter = iter(range(2))
    monkeypatch.setattr(adapter, "_fresh_runtime", lambda *a, **k: {
        "sim": SimpleNamespace(close=lambda: None), "brain": object(), "serial": next(counter)})
    output = tmp_path / "preflight.json"
    report = adapter.run_preflight(protocol, output)
    assert report["scientific_run_executed"] is False
    assert report["scientific_run_number_consumed"] is None
    assert json.loads(output.read_text())["artifact_kind"] == "NON_SCIENTIFIC_PREFLIGHT"


def test_preflight_inspects_all_fourteen_before_sign_calibration(monkeypatch, tmp_path):
    interfaces = [{"physical_joint": name, "action_index": m6b.LOCKED_ACTION_INDICES[name], "leg": name[6:8],
        "joint_class": "Femur", "coordinate_sign": -1, "mechanical_calibration": {"evidence": {}}, "directional_motor_populations": [
            {"population": "p", "body_ids": [1], "annotation_direction": 1},
            {"population": "n", "body_ids": [2], "annotation_direction": -1}]}
        for name in m6b.TIER_B]
    records = [{"index": item["action_index"], "name": item["physical_joint"], "mujoco_metadata": {
        "actuator_id": 0, "joint_id": 0, "qpos_range": [0, 1], "dof_range": [0, 1]}}
        for i, item in enumerate(interfaces)]
    physics = FakePhysics(); obs = {"joints": np.zeros(42)}
    monkeypatch.setattr(adapter, "_live_setup", lambda p: (object(),
        SimpleNamespace(body_ids=np.array([1, 2])), {}, records,
        {record["name"]: record for record in records}))
    monkeypatch.setattr(adapter, "_make_live", lambda *a: (
        SimpleNamespace(close=lambda: None), physics, obs, 0, 0))
    monkeypatch.setattr(adapter, "_run_condition", lambda *a, **k:
                        pytest.fail("scientific run launched"))
    monkeypatch.setattr(adapter, "_fresh_runtime", lambda *a, **k: {
        "sim": SimpleNamespace(close=lambda: None), "brain": object()})
    report = adapter.run_preflight({"interfaces": interfaces}, tmp_path / "limits.json")
    assert report["schema"] == "M6B-P5.0"
    assert [x["physical_actuator_name"] for x in report["interfaces"]] == list(m6b.TIER_B)
    assert len(report["interfaces"]) == 8


def test_setup_failure_does_not_consume_run_one(monkeypatch, capsys):
    monkeypatch.setattr(adapter, "run_preflight", lambda *a: (_ for _ in ()).throw(RuntimeError("missing dependency")))
    assert m6b.main(["--preflight-windows"]) == 1
    assert "M6B WINDOWS PREFLIGHT FAIL" in capsys.readouterr().out
    report = m6b.build_not_run_artifact()
    assert report["provenance"]["scientific_run_number"] is None
    assert report["run_status"] == "NOT_RUN"


def test_provenance_failure_cannot_launch_preflight_or_science(monkeypatch, capsys):
    def provenance_failure():
        raise m6b.ValidationFailure("PROVENANCE_FAILURE", "M6A raw-byte provenance mismatch")
    monkeypatch.setattr(m6b, "load_locked_m6a", provenance_failure)
    monkeypatch.setattr(adapter, "run_preflight",
                        lambda *a: pytest.fail("preflight adapter launched after provenance failure"))
    monkeypatch.setattr(adapter, "run_canonical",
                        lambda *a: pytest.fail("scientific conditions launched"))
    assert m6b.main(["--preflight-windows"]) == 1
    assert "M6B WINDOWS PREFLIGHT FAIL: M6A raw-byte provenance mismatch" in capsys.readouterr().out

    committed = json.loads(m6b.OUTPUT.read_text(encoding="utf-8"))
    assert committed["run_status"] == "NOT_RUN"
    assert committed["provenance"]["scientific_run_number"] is None


def test_frozen_canonical_execution_counts_and_order():
    assert adapter.CONDITIONS == ("ENABLED", "MOTOR_OUTPUT_DISABLED")
    assert tuple(m6b.TIER_B) == ("joint_LFFemur", "joint_LFTarsus1", "joint_LMFemur",
        "joint_LHFemur", "joint_RFFemur", "joint_RFTarsus1", "joint_RMFemur",
        "joint_RHFemur")
    assert adapter.PHYSICS_DT_MS == .1 and adapter.NEURAL_DT_MS == .5
    assert m6b.DURATION_MS == 500
    assert adapter.EXPECTED_PHYSICS_STEPS_PER_CONDITION == 5000
    assert adapter.EXPECTED_NEURAL_STEPS_PER_CONDITION == 1000
    assert adapter.EXPECTED_CONDITIONS == 16
    assert adapter.EXPECTED_CONDITIONS * adapter.EXPECTED_PHYSICS_STEPS_PER_CONDITION == 80_000
    assert adapter.EXPECTED_CONDITIONS * adapter.EXPECTED_NEURAL_STEPS_PER_CONDITION == 16_000
    assert adapter.EXPECTED_CANONICAL_ENVIRONMENT_CONSTRUCTIONS == 17
    plan = [(name, condition) for name in m6b.TIER_B for condition in adapter.CONDITIONS]
    assert len(plan) == len(set(plan)) == 16


def test_no_live_inventory_construction_in_condition_loop():
    tree = ast.parse(inspect.getsource(adapter._run_condition))
    calls = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "enumerate_live_actuators" not in calls
    assert "_make_live" not in calls  # construction is isolated in the fresh-runtime boundary
    source = inspect.getsource(adapter._run_condition)
    assert "for name in actuator_names" in source
    assert "assert_physical_admission" in source


def test_cached_digest_sequence_is_identical_between_neural_updates(monkeypatch):
    brain = SimpleNamespace(v=np.array([1.]), g_exc=np.array([2.]),
        g_inh=np.array([3.]), spike_counts=np.array([4]))
    calls = 0
    original = adapter._state_tuple
    def counted(value):
        nonlocal calls
        calls += 1
        return original(value)
    monkeypatch.setattr(adapter, "_state_tuple", counted)
    cached = adapter._cached_state_digest(brain, None, True)
    expected = [original(brain)] * 5
    actual = [adapter._cached_state_digest(brain, cached, False) for _ in range(5)]
    assert actual == expected and calls == 1
    brain.v[0] = 9
    cached = adapter._cached_state_digest(brain, cached, True)
    assert cached == original(brain) and calls == 2


def test_progress_is_flushed_and_rng_neutral(monkeypatch):
    emitted = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: emitted.append((a, k)))
    state = np.random.default_rng(1).bit_generator.state
    adapter._progress("hello")
    assert emitted == [(("hello",), {"flush": True})]
    assert np.random.default_rng(1).bit_generator.state == state


def test_attempt_one_is_machine_readable_aborted_not_complete():
    path = m6b.OUTPUT.with_name("m6b_attempt_1_abort.json")
    attempt = json.loads(path.read_text(encoding="utf-8"))
    assert attempt["attempt_number"] == 1
    assert attempt["status"] == "ABORTED_IMPLEMENTATION_PERFORMANCE_DEFECT"
    assert attempt["scientific_result_available"] is False
    assert attempt["scientific_result_inspected"] is False
    assert attempt["canonical_scientific_result_complete"] is False


def test_fresh_runtime_closes_environment_when_initialization_is_interrupted(monkeypatch):
    closed = []
    sim = SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr(adapter, "_make_live", lambda *a: (sim, object(), {}, 0, 0))
    class InterruptedBrain:
        def __init__(self, data):
            raise KeyboardInterrupt
    monkeypatch.setattr(adapter, "MaleCNSBrain", InterruptedBrain)
    with pytest.raises(KeyboardInterrupt):
        adapter._fresh_runtime(object(), object(), {}, {}, {}, "ENABLED")
    assert closed == [True]
