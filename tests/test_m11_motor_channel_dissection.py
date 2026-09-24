"""Focused M11A design tests; no scientific runtime is constructed."""
import ast
import hashlib
import inspect
import json
import pytest

try:
    import numpy as np
except ModuleNotFoundError:  # Core zero-transition tests remain runnable in minimal environments.
    np = None

from malecns_backend.embodiment import m11_motor_channel_dissection as m
from malecns_backend.embodiment import _windows_m11_motor_channel_dissection_adapter as adapter


def test_exact_frozen_upstream_identity_registry_and_fail_closed(tmp_path):
    assert m.UPSTREAM_ARTIFACTS["m10b_raw.npz"] == {"directory": "m10b", "sha256": "85e98715ac3d8b219c86ef338187828e787ee8f300bacad9d318809e23208cde", "byte_size": 57652701}
    assert m.UPSTREAM_ARTIFACTS["m10c_analysis.json"]["sha256"] == "31d7dd5445ecd6bc17542f455d5196a087934f3251d5c36915424b737e595740"
    assert m.UPSTREAM_ARTIFACTS["m10c_manifest.json"] == {"directory": "m10c", "sha256": "d5cb32c04da9b285247b35ad44b252997bc0a38c3f5fd9657a49857635f10454", "byte_size": 2588}
    assert set(m.UPSTREAM_ARTIFACTS) == {"m10b_raw.npz", "m10b_report.json", "m10b_manifest.json", "m10b_preregistration.json", "m10c_analysis.json", "m10c_manifest.json"}
    with pytest.raises(RuntimeError, match="before transitions.*m10b_raw"):
        m.verify_upstream(tmp_path, tmp_path)


def test_pre_execution_provenance_amendment_is_frozen():
    assert m.protocol()["provenance_amendment"] == {
        "type": "PRE-EXECUTION provenance correction",
        "previous_preregistration_sha256": "758668128d0fbc89e95da787a9f3088a453cb751d7c25a174c90d04cc746e3bd",
        "reason": "m10c_manifest.json was recorded using the LF-normalized Git blob identity rather than the canonical generated M10C artifact raw-byte identity",
        "scientific_conditions_executed_before_correction": 0,
        "physics_transitions_before_correction": 0,
        "neural_transitions_before_correction": 0,
        "scientific_design_changed": False,
    }


def test_exact_motor_and_condition_inventories():
    assert m.MOTOR_CHANNELS == (("joint_LFTibia", 5, 1), ("joint_LMTibia", 12, 1), ("joint_LHTibia", 19, 1), ("joint_RFTibia", 26, 1), ("joint_RMTibia", 33, 1), ("joint_RHTibia", 40, 1), ("joint_LFFemur", 3, -1), ("joint_LMFemur", 10, -1), ("joint_LHFemur", 17, -1), ("joint_RMFemur", 31, -1), ("joint_RHFemur", 38, -1))
    assert len(m.CONDITIONS) == 13
    assert m.CONDITIONS[0] == ("full_11_enabled", ())
    assert m.CONDITIONS[1][0] == "all_11_disabled" and len(m.CONDITIONS[1][1]) == 11
    assert [row[1] for row in m.CONDITIONS[2:]] == [(name,) for name, _, _ in m.MOTOR_CHANNELS]


def test_intervention_is_only_final_selected_contribution_zeroing():
    original = {name: index + 0.25 for index, (name, _, _) in enumerate(m.MOTOR_CHANNELS)}
    target = m.MOTOR_CHANNELS[4][0]
    result = m.intervene(original, [target])
    assert result[target] == 0.0
    assert {key: value for key, value in result.items() if key != target} == {key: value for key, value in original.items() if key != target}
    assert set(m.intervene(original, [x[0] for x in m.MOTOR_CHANNELS]).values()) == {0.0}
    with pytest.raises(ValueError):
        m.intervene(dict(reversed(list(original.items()))), [target])
    intervention = m.protocol()["intervention"]
    assert all(intervention[key] for key in ("MaleCNS_active", "sensory_encoding_active", "neural_updates_active", "motor_observation_active", "decoder_active"))


def test_force_timing_windows_and_thresholds_are_exact():
    assert m.TIMING == {"duration_ms": 1500.0, "physics_dt_ms": 0.1, "neural_dt_ms": 0.5, "physics_transitions_per_condition": 15000, "neural_transitions_per_condition": 3000}
    assert m.PERTURBATION["direction_xyz"] == [0.0, 1.0, 0.0]
    assert m.PERTURBATION["magnitude"] == 1.024 and m.PERTURBATION["torque_xyz"] == [0.0, 0.0, 0.0]
    assert m.force_at_transition(4999) == (0.0, 0.0, 0.0)
    assert m.force_at_transition(5000) == (0.0, 1.024, 0.0)
    assert m.force_at_transition(5199) == (0.0, 1.024, 0.0)
    assert m.force_at_transition(5200) == (0.0, 0.0, 0.0)
    assert m.WINDOWS == {"pre": {"start_ms_inclusive": 0.0, "stop_ms_exclusive": 500.0}, "direct_force": {"start_ms_inclusive": 500.0, "stop_ms_exclusive": 520.0}, "early_post_force": {"start_ms_inclusive": 520.0, "stop_ms_exclusive": 557.0}, "later_post_force": {"start_ms_inclusive": 557.0, "stop_ms_inclusive": 1500.0}}
    assert m.THRESHOLDS == {"thorax_com_deviation_mm": 0.005, "root_orientation_shortest_arc_deg": 0.25}


def test_signed_estimand_and_inclusive_classification_are_frozen():
    assert m.ablation_effect(1.5, 2.0) == -0.5
    assert m.classify(-0.005, 0.005) == "ABLATION_REDUCES_AMPLIFICATION"
    assert m.classify(0.005, 0.005) == "ABLATION_INCREASES_AMPLIFICATION"
    assert m.classify(0.0049, 0.005) == "UNRESOLVED_AT_INHERITED_THRESHOLD"
    signs = m.protocol()["analysis"]["sign_semantics"]
    assert "increased" in signs["positive"] and "decreased" in signs["negative"]
    assert m.protocol()["analysis"]["classification"]["ranking_or_composite"] is False


def test_preregistration_bytes_match_protocol_and_frozen_hash():
    assert json.loads(m.PREREGISTRATION_PATH.read_text()) == m.protocol()
    assert hashlib.sha256(m.PREREGISTRATION_PATH.read_bytes()).hexdigest() == m.PREREGISTRATION_SHA256
    assert m.verify_preregistration() == m.PREREGISTRATION_SHA256
    assert m.PREREGISTRATION_PATH.stat().st_size == 10003
    assert not any((m.OUTPUT_DIR / name).exists() for name in m.FUTURE_OUTPUTS.values())


def test_zero_transition_preflight_with_exact_identity_fixtures(tmp_path, monkeypatch):
    m10b, m10c, output = tmp_path / "b", tmp_path / "c", tmp_path / "out"
    m10b.mkdir(); m10c.mkdir(); output.mkdir()
    # Tiny fixtures exercise complete hash+size logic without canonical science data.
    identities = {}
    for index, name in enumerate(m.UPSTREAM_ARTIFACTS):
        path = (m10b if name.startswith("m10b") else m10c) / name
        path.write_bytes(bytes([index]) * (index + 1))
        identities[name] = {"directory": "m10b" if name.startswith("m10b") else "m10c", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "byte_size": index + 1}
    monkeypatch.setattr(m, "verify_upstream",
        lambda b, c: {name: {key: value for key, value in identity.items() if key != "directory"}
                      for name, identity in identities.items()})
    result = m.preflight(m10b, m10c, output)
    assert result["physics_transitions"] == result["neural_transitions"] == 0
    assert result["scientific_conditions_executed"] == 0
    assert result["physics_runtime_constructed"] is result["MaleCNS_constructed"] is False


def test_occupied_namespace_rejected_and_no_overwrite(tmp_path):
    assert m.outputs_available(tmp_path)
    sentinel = tmp_path / m.FUTURE_OUTPUTS["report"]
    sentinel.write_bytes(b"do not overwrite")
    assert not m.outputs_available(tmp_path)
    with pytest.raises(FileExistsError, match="occupied.*overwrite forbidden"):
        # Bypass upstream checks only to isolate namespace behavior.
        original = m.verify_upstream
        m.verify_upstream = lambda *_: {}
        try: m.preflight(output_dir=tmp_path)
        finally: m.verify_upstream = original
    assert sentinel.read_bytes() == b"do not overwrite"


def test_import_and_cli_have_no_automatic_scientific_execution():
    source = inspect.getsource(m)
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not any(name.startswith(("flygym", "mujoco")) for name in imports)
    assert ".step(" not in source and "--run-windows" not in source
    assert m.protocol()["integrity"]["no_automatic_retries"] is True


def test_cli_requires_explicit_mode_and_preflight_does_not_load_adapter(monkeypatch):
    with pytest.raises(SystemExit):
        m.main([])
    called = False
    monkeypatch.setattr(m, "preflight", lambda: {"status": "PREFLIGHT_PASS"})
    assert m.main(["--preflight"]) == 0
    assert called is False


def test_initialization_diagnostic_reports_only_exact_differences(monkeypatch):
    conditions = (("baseline", ()), ("comparison", ()))
    monkeypatch.setattr(adapter.m11, "CONDITIONS", conditions)
    monkeypatch.setattr(adapter.m7runner, "_protocol", lambda: (object(), object(), object()))
    calls = []
    states = {
        "baseline": {"physics_steps": 0, "neural_steps": 0,
            "pre_intervention_state": {"position": 1},
            "initial_physical_state_audit": {
                "position": [1.0, 2.0], "runtime_name": "first", "equal": 7}},
        "comparison": {"physics_steps": 0, "neural_steps": 0,
            "pre_intervention_state": {"position": 2},
            "initial_physical_state_audit": {
                "position": [1.0, 3.0], "runtime_name": "second", "equal": 7}},
    }
    def initialize_only(runner, live, records, table, name, number, flag):
        calls.append((name, flag))
        return states[name]
    monkeypatch.setattr(adapter, "invoke", initialize_only)
    monkeypatch.setattr(adapter.m6c, "pre_intervention_equivalent", lambda left, right: left == right)
    published = False
    def forbidden_publish(*args, **kwargs):
        nonlocal published
        published = True
        raise AssertionError("diagnostic published")
    monkeypatch.setattr(adapter, "publish_transaction", forbidden_publish)

    progress = []
    result = adapter.diagnose_initialization(object(), progress.append)

    assert calls == [("baseline", True), ("comparison", True)]
    assert result["scientific_conditions_executed"] == 0
    assert result["canonical_outputs_published"] is False and published is False
    assert result["initial_physical_state_audit_keys"] == ["equal", "position", "runtime_name"]
    comparison = result["conditions"][1]
    assert comparison["pre_intervention_equivalent_to_condition_1"] is False
    assert [row["field"] for row in comparison["differing_audit_fields"]] == ["position", "runtime_name"]
    assert comparison["differing_audit_fields"][0] == {
        "field": "position", "baseline_present": True, "comparison_present": True,
        "baseline_value": [1.0, 2.0], "comparison_value": [1.0, 3.0],
        "category": "numeric_physical_state_value"}
    assert comparison["differing_audit_fields"][1]["category"] == "condition_or_runtime_metadata"
    assert comparison["canonical_audit_equivalent_to_condition_1"] is False
    assert comparison["raw_differences_disappear_under_canonical_audit_identity"] is False
    assert progress == ["[1/2] constructing baseline", "[1/2] complete: physics=0 neural=0",
                        "[2/2] constructing comparison", "[2/2] complete: physics=0 neural=0"]


def _m11_initial_audit(namespace="1"):
    return {
        "initial_pose_source": "caller-supplied frozen physical runtime",
        "body_position": [0.0, 0.0, 0.5],
        "body_orientation_quaternion": [1.0, 0.0, 0.0, 0.0],
        "joint_configuration": [0.1, 0.2],
        "qpos": [0.0, 0.5], "qvel": [0.0, 0.0],
        "ground": "frozen surface", "ground_dynamic_after_reset": False,
        "gravity": [0.0, 0.0, -9.81], "control": "position",
        "adhesion_enabled": False, "adhesion_command": [0.0] * 6,
        "adhesion_policy": "constant zero baseline",
        "locomotion_or_reference_controller": False,
        "m8_contact_identity": {
            "available": True,
            "method": "exact terminal component of slash-namespaced compiled MuJoCo identities",
            "body_names": {0: "world", 1: f"{namespace}/Thorax",
                           2: f"{namespace}/LFTibia"},
            "ground_geom_ids": [0],
            "tarsal_geom_ids": {"LF": [7, 8]},
            "tarsus5_body_ids": {"LF": 9},
        },
    }


def test_initialization_audit_canonicalizes_only_body_name_runtime_namespaces():
    first = _m11_initial_audit("1")
    later = _m11_initial_audit("13")
    canonical_first = adapter._canonical_initialization_audit(first)
    canonical_later = adapter._canonical_initialization_audit(later)
    assert canonical_first == canonical_later
    assert canonical_first["m8_contact_identity"]["body_names"] == {
        0: "world", 1: "Thorax", 2: "LFTibia"}
    # Canonicalization is comparison-only and never mutates runtime evidence.
    assert first["m8_contact_identity"]["body_names"][1] == "1/Thorax"
    assert later["m8_contact_identity"]["body_names"][2] == "13/LFTibia"


@pytest.mark.parametrize(("path", "replacement"), [
    (("m8_contact_identity", "body_names", 2), "13/RFTibia"),
    (("m8_contact_identity", "body_names"), {0: "world", 7: "13/Thorax", 2: "13/LFTibia"}),
    (("m8_contact_identity", "tarsal_geom_ids"), {"LF": [7, 99]}),
    (("m8_contact_identity", "tarsus5_body_ids"), {"LF": 10}),
    (("m8_contact_identity", "ground_geom_ids"), [4]),
    (("m8_contact_identity", "method"), "different method"),
    (("m8_contact_identity", "available"), False),
    (("qpos",), [1.0, 0.5]), (("qvel",), [1.0, 0.0]),
    (("body_position",), [0.0, 0.1, 0.5]),
    (("body_orientation_quaternion",), [0.0, 1.0, 0.0, 0.0]),
    (("control",), "torque"), (("gravity",), [0.0, 0.0, -1.0]),
    (("ground",), "other"), (("ground_dynamic_after_reset",), True),
    (("initial_pose_source",), "other"), (("joint_configuration",), [0.1, 0.3]),
    (("adhesion_enabled",), True), (("adhesion_command",), [1.0] * 6),
    (("adhesion_policy",), "other"), (("locomotion_or_reference_controller",), True),
])
def test_initialization_audit_canonicalization_preserves_strict_differences(path, replacement):
    baseline = _m11_initial_audit("1")
    changed = _m11_initial_audit("13")
    target = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    assert (adapter._canonical_initialization_audit(baseline)
            != adapter._canonical_initialization_audit(changed))


def test_readiness_uses_13_zero_transition_canonical_audits_and_deterministic_hash(monkeypatch):
    monkeypatch.setattr(adapter.m7runner, "_protocol", lambda: (None, None, None))
    calls = []
    def initialize_only(runner, live, records, table, name, number, flag):
        calls.append((name, number, flag))
        return {"physics_steps": 0, "neural_steps": 0,
                "pre_intervention_state": {"same": True},
                "initial_physical_state_audit": _m11_initial_audit(str(number))}
    monkeypatch.setattr(adapter, "invoke", initialize_only)
    monkeypatch.setattr(adapter.m6c, "pre_intervention_equivalent", lambda left, right: left == right)
    first = adapter.readiness(object())
    second = adapter.readiness(object())
    expected = hashlib.sha256(adapter._serialized_audit(
        adapter._canonical_initialization_audit(_m11_initial_audit("99"))).encode()).hexdigest()
    assert len(calls) == 26 and all(flag is True for _, _, flag in calls)
    assert first["fresh_runtime_count"] == 13
    assert first["physics_transitions"] == first["neural_transitions"] == 0
    assert first["initialization_identity_sha256"] == expected
    assert second["initialization_identity_sha256"] == expected


@pytest.mark.parametrize(("physics", "neural"), [(1, 0), (0, 1)])
def test_readiness_rejects_physics_or_neural_transition(monkeypatch, physics, neural):
    monkeypatch.setattr(adapter.m7runner, "_protocol", lambda: (None, None, None))
    monkeypatch.setattr(adapter, "invoke", lambda *args: {
        "physics_steps": physics, "neural_steps": neural,
        "pre_intervention_state": {}, "initial_physical_state_audit": _m11_initial_audit()})
    with pytest.raises(RuntimeError, match="crossed a transition boundary"):
        adapter.readiness(object())


def test_readiness_still_requires_pre_intervention_equivalence(monkeypatch):
    monkeypatch.setattr(adapter.m7runner, "_protocol", lambda: (None, None, None))
    monkeypatch.setattr(adapter, "invoke", lambda *args: {
        "physics_steps": 0, "neural_steps": 0,
        "pre_intervention_state": {"condition": args[4]},
        "initial_physical_state_audit": _m11_initial_audit(str(args[5]))})
    monkeypatch.setattr(adapter.m6c, "pre_intervention_equivalent", lambda left, right: False)
    with pytest.raises(RuntimeError, match="fresh initial states differ"):
        adapter.readiness(object())


def test_diagnostic_exposes_raw_namespace_difference_and_canonical_match(monkeypatch):
    monkeypatch.setattr(adapter.m11, "CONDITIONS", (("baseline", ()), ("comparison", ())))
    monkeypatch.setattr(adapter.m7runner, "_protocol", lambda: (None, None, None))
    monkeypatch.setattr(adapter, "invoke", lambda runner, live, records, table, name, number, flag: {
        "physics_steps": 0, "neural_steps": 0, "pre_intervention_state": {},
        "initial_physical_state_audit": _m11_initial_audit(str(number))})
    monkeypatch.setattr(adapter.m6c, "pre_intervention_equivalent", lambda left, right: True)
    result = adapter.diagnose_initialization(object(), lambda message: None)
    comparison = result["conditions"][1]
    assert [row["field"] for row in comparison["differing_audit_fields"]] == ["m8_contact_identity"]
    assert comparison["canonical_audit_equivalent_to_condition_1"] is True
    assert comparison["raw_differences_disappear_under_canonical_audit_identity"] is True


def test_initialization_diagnostic_rejects_any_transition(monkeypatch):
    monkeypatch.setattr(adapter.m11, "CONDITIONS", (("baseline", ()),))
    monkeypatch.setattr(adapter.m7runner, "_protocol", lambda: (None, None, None))
    monkeypatch.setattr(adapter, "invoke", lambda *args: {
        "physics_steps": 1, "neural_steps": 0,
        "pre_intervention_state": {}, "initial_physical_state_audit": {}})
    with pytest.raises(RuntimeError, match="crossed a transition boundary.*physics=1 neural=0"):
        adapter.diagnose_initialization(object(), lambda message: None)


def test_cli_modes_remain_mutually_exclusive_and_dispatch_unchanged(monkeypatch):
    with pytest.raises(SystemExit):
        m.main(["--diagnose-initialization", "--execute-canonical"])
    monkeypatch.setattr(adapter, "diagnose_initialization",
                        lambda: {"mode": "INITIALIZATION_DIAGNOSTIC"})
    monkeypatch.setattr(adapter, "execute_canonical", lambda: {"mode": "CANONICAL"})
    assert m.main(["--diagnose-initialization"]) == 0
    assert m.main(["--execute-canonical"]) == 0


@pytest.mark.skipif(np is None, reason="NumPy unavailable")
def _synthetic_raw(condition):
    names = [x[0] for x in m.MOTOR_CHANNELS]
    pre = np.arange(33_000, dtype=float).reshape(3000, 11) + 1
    post = np.repeat(pre, 5, axis=0)
    mask = np.asarray([name in dict(m.CONDITIONS)[condition] for name in names])
    post[:, mask] = 0
    times = np.linspace(0, 1500, 15001)
    position = np.column_stack((times / 1000, np.zeros((15001, 2))))
    orientation = np.zeros((15001, 4)); orientation[:, 0] = 1
    return {
        "physics_time_ms": times, "physics_body_position": position,
        "physics_body_orientation": orientation,
        "physics_qvel": np.zeros((15001, 6)),
        "physics_joint_position": np.zeros((15001, 42)),
        "physics_tarsus5_world_position": np.zeros((15001, 6, 3)),
        "physics_tarsal_contact": np.zeros((15001, 6)),
        "physics_external_force": np.asarray([m.force_at_transition(i) for i in range(15000)]),
        "neural_sensory_physical_inputs": np.zeros((3000, 6)),
        "neural_sensory_encoded": np.zeros((3000, 6)),
        "neural_delivered_sensory_state": np.zeros((3000, 6)),
        "neural_mapped_motor_population_state": np.zeros((3000, 11)),
        "neural_decoder_outputs": pre.copy(), "neural_motor_pre_zero": pre,
        "physics_neural_motor_contribution": post,
        "physics_action": np.zeros((15001, 42)), "neural_time_ms": np.arange(3000) * .5,
    }


@pytest.mark.skipif(np is None, reason="NumPy unavailable")
def test_raw_contract_retains_intervention_force_time_and_initialization_evidence():
    result = {"raw_arrays": _synthetic_raw("leave_one_out__joint_LFTibia")}
    arrays = adapter.condition_arrays(result, "leave_one_out__joint_LFTibia", "abc123")
    assert tuple(arrays) == adapter.RAW_FIELDS
    assert arrays["ablated_channel_mask"].sum() == 1
    assert arrays["initialization_identity_sha256"].item() == "abc123"
    assert np.count_nonzero(arrays["applied_external_force"][:, 1]) == 200
    assert np.all(arrays["admitted_neural_motor_physical_contribution"][:, 0] == 0)
    assert np.all(arrays["admitted_neural_motor_physical_contribution"][:, 1:] != 0)


@pytest.mark.skipif(np is None, reason="NumPy unavailable")
def test_report_builder_is_deterministic_and_has_required_estimands():
    conditions = {name: adapter.condition_arrays({"raw_arrays": _synthetic_raw(name)}, name, "same")
                  for name, _ in m.CONDITIONS}
    counts = {"aggregate": {"physics_transitions": 195000, "neural_transitions": 39000}}
    init = {"fresh_runtime_count": 13, "fresh_initialization_equivalent": True}
    first = adapter.build_report(conditions, counts, init)
    second = adapter.build_report(conditions, counts, init)
    assert adapter._json_bytes(first) == adapter._json_bytes(second)
    assert set(first["later_post_force_estimands"]) == {x[0] for x in m.MOTOR_CHANNELS}
    assert "not biological latency" in first["interpretation_boundaries"]["boundary_557_ms"]
    assert "not neural sensory input" in first["interpretation_boundaries"]["contact"]


def test_transactional_publish_and_failure_rollback(tmp_path, monkeypatch):
    report = {"schema": m.SCHEMA, "status": "COMPLETE"}
    base = {"schema": m.SCHEMA, "status": "COMPLETE"}
    manifest = adapter.publish_transaction(tmp_path, b"synthetic npz bytes", report, base)
    assert manifest["outputs"]["m11_raw.npz"]["byte_size"] == 19
    assert all((tmp_path / name).is_file() for name in m.FUTURE_OUTPUTS.values())

    failed = tmp_path / "failed"; failed.mkdir()
    real_replace = adapter.os.replace
    calls = 0
    def fail_second(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic publication failure")
        return real_replace(source, destination)
    monkeypatch.setattr(adapter.os, "replace", fail_second)
    with pytest.raises(OSError, match="synthetic"):
        adapter.publish_transaction(failed, b"raw", report, base)
    assert not any((failed / name).exists() for name in m.FUTURE_OUTPUTS.values())
    assert not any(path.name.startswith(".m11b-tmp") for path in failed.iterdir())


def test_execution_checks_namespace_before_runtime_construction(tmp_path, monkeypatch):
    (tmp_path / "m11_report.json").write_text("sentinel")
    monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(m, "verify_preregistration", lambda: m.PREREGISTRATION_SHA256)
    monkeypatch.setattr(m, "verify_upstream", lambda *args: {})
    constructed = False
    def forbidden(*args, **kwargs):
        nonlocal constructed
        constructed = True
        raise AssertionError("runtime constructed")
    with pytest.raises(FileExistsError):
        adapter.execute_canonical(forbidden)
    assert constructed is False
