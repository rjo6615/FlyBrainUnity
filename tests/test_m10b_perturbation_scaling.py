"""M10B preregistration tests.  Nothing here constructs a scientific runtime."""
import ast
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import m10b_perturbation_scaling as m
from malecns_backend.embodiment import _windows_m10b_perturbation_scaling_adapter as adapter


def test_frozen_m10a_hashes_and_fail_closed_mutation(tmp_path):
    assert m.verify_m10a() == m.M10A_ARTIFACTS
    for name in m.M10A_ARTIFACTS:
        (tmp_path / name).write_bytes((m.M10A_DIR / name).read_bytes())
    target = tmp_path / "m10a_report.json"
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="before transitions.*mismatch"):
        m.preflight(tmp_path)


def test_force_series_condition_matrix_and_shared_controls_are_exact():
    assert m.FORCES == (0.256, 1.024, 2.896309375740099, 4.096)
    assert m.CONDITIONS == (
        ("A_C", True, 0.0), ("B_C", False, 0.0),
        ("A_F0256", True, .256), ("B_F0256", False, .256),
        ("A_F1024", True, 1.024), ("B_F1024", False, 1.024),
        ("A_F2896", True, 2.896309375740099), ("B_F2896", False, 2.896309375740099),
        ("A_F4096", True, 4.096), ("B_F4096", False, 4.096))
    assert len(m.CONDITIONS) == 10
    assert [row for row in m.CONDITIONS if row[2] == 0] == list(m.CONDITIONS[:2])
    assert m.protocol()["shared_controls"] == ["A_C", "B_C"]


def test_geometry_interval_and_only_magnitude_varies():
    p = m.protocol()["perturbation"]
    assert p == m.PERTURBATION
    assert p["direction_xyz"] == [0.0, 1.0, 0.0]
    assert p["application_body_source"] == "Thorax"
    assert p["application_point"] == "authoritative body center of mass"
    assert p["torque_xyz"] == [0.0, 0.0, 0.0]
    assert (p["start_ms_inclusive"], p["stop_ms_exclusive"]) == (500., 520.)
    for name, _, force in m.CONDITIONS:
        active = [i for i in range(15000) if any(m.force_at_transition(name, i))]
        assert active == ([] if force == 0 else list(range(5000, 5200)))
        if force:
            assert m.force_at_transition(name, 5000) == (0.0, force, 0.0)


def test_initialization_interfaces_contact_and_timing_are_inherited():
    p = m.protocol()
    assert p["physical_initialization"] == m.m7d.protocol()["physical_initialization"]
    assert p["physical_initialization"]["spawn_pos"] == [0.0, 0.0, 0.6045752232266313]
    assert p["interfaces"]["sensory"] == list(m.m9b.SENSORY_INTERFACES)
    assert len(p["interfaces"]["sensory"]) == 6
    assert [(x["name"], x["action_index"], x["coordinate_sign"]) for x in p["interfaces"]["motor"]] == list(m.m9b.MOTOR_INTERFACES)
    assert len(p["interfaces"]["motor"]) == 11
    assert p["interfaces"]["contact_is_neural_input"] is False
    assert p["timing"] == {"flygym": "1.2.1", "mujoco": "3.2.7", "physics_dt_ms": .1,
        "neural_dt_ms": .5, "duration_ms": 1500., "physics_transitions": 15000,
        "physics_states": 15001, "neural_updates": 3000}


def test_disabled_semantics_and_exact_zero_physical_contribution():
    values = {name: index + .5 for index, name in enumerate(m.m7d.ADMITTED_MOTOR)}
    assert m.gate_contributions(values, True) == values
    assert set(m.gate_contributions(values, False).values()) == {0.0}
    disabled = m.protocol()["disabled_intervention"]
    assert all(disabled[k] for k in ("male_cns_runs", "sensory_encoding_and_delivery_runs",
        "observer_runtime_runs", "decoder_runs", "exact_11_channel_physical_contribution_zero_required"))
    assert disabled["zero_boundary"] == "immediately before physical application"


def test_no_assistance_system_and_primary_difference_in_differences():
    assert m.protocol()["execution_absences"] == {"controllers": False, "reward": False,
        "rl": False, "reference_trajectory": False, "gait_logic": False,
        "contact_sensory_input": False}
    assert m.difference_in_differences(10, 3, 8, 4) == 3
    assert m.protocol()["primary_estimator"].startswith("delta_delta_F(t) = (A_F(t) - A_C(t))")


def test_directional_rule_is_fixed_thresholded_and_handles_sign_changes():
    assert m.PRIMARY_THRESHOLDS == {"thorax_com_deviation_mm": .005,
                                    "root_orientation_shortest_arc_deg": .25}
    assert m.classify_direction(-.005, -.010, .005) == "ATTENUATING"
    assert m.classify_direction(.25, .5, .25) == "AMPLIFYING"
    assert m.classify_direction(-.25, .25, .25) == "DIRECTIONALLY_MIXED"
    assert m.classify_direction(-.0049, .0049, .005) == "NO_RESOLVED_DIRECTIONAL_EFFECT"
    # A lone resolved direction is not enough to characterize both windows.
    assert m.classify_direction(-.005, 0, .005) == "ATTENUATING"
    with pytest.raises(ValueError): m.classify_direction(0, 0, 0)


def test_windows_and_scaling_analysis_are_deterministic():
    assert m.WINDOWS["early_post_force"] == {"start_ms_inclusive": 520., "stop_ms_exclusive": 557.}
    assert m.WINDOWS["later_post_force"] == {"start_ms_inclusive": 557., "stop_ms_inclusive": 1500.}
    result = m.scaling_summary(m.FORCES, [-1., -2., 1., 3.])
    assert result["signed_effects"] == [-1., -2., 1., 3.]
    assert result["adjacent_signed_changes"] == [-1., 3., 2.]
    assert result["sign_changes"] == [False, True, False]
    assert result["absolute_effect_monotonic_nondecreasing"] is False
    with pytest.raises(ValueError): m.scaling_summary(tuple(reversed(m.FORCES)), [1] * 4)


def test_raw_schema_supports_read_only_causal_timing():
    schema = m.protocol()["raw_schema_per_condition"]
    required = {"physics_time_ms", "root_thorax_position", "root_orientation_wxyz",
        "root_linear_velocity", "root_angular_velocity", "height", "joint_positions",
        "distal_tarsus_positions", "physical_contact_observations", "applied_external_force",
        "tibial_proprioceptive_physical_inputs", "modeled_sensory_encoding",
        "delivered_sensory_cns_state", "mapped_motor_population_state", "decoder_state_output",
        "admitted_neural_motor_pre_intervention", "admitted_neural_motor_physical_contribution",
        "physical_command_after_intervention", "condition_identity", "force_magnitude", "motor_enabled"}
    assert required <= set(schema)
    assert schema["joint_positions"] == [15001, 42]
    assert schema["admitted_neural_motor_physical_contribution"] == [15000, 11]


def test_output_namespaces_are_m10b_exclusive_and_frozen_artifacts_untouched(tmp_path, monkeypatch):
    protected = tuple(m.M10A_DIR / name for name in m.M10A_ARTIFACTS)
    before = [(p.stat().st_mtime_ns, m._sha256(p)) for p in protected]
    monkeypatch.setattr(m, "RAW_PATH", tmp_path / "m10b_raw.npz")
    monkeypatch.setattr(m, "REPORT_PATH", tmp_path / "m10b_report.json")
    monkeypatch.setattr(m, "MANIFEST_PATH", tmp_path / "m10b_manifest.json")
    assert m.outputs_available()
    m.RAW_PATH.touch()
    assert not m.outputs_available()
    assert before == [(p.stat().st_mtime_ns, m._sha256(p)) for p in protected]
    future = m.protocol()["future_outputs"]
    assert future["m9_and_m10a_namespaces_read_only"] and future["exclusive_creation_required"]
    assert all("m10b_perturbation_scaling" in str(path) for path in
               (m.OUTPUT_DIR, m.PREREGISTRATION_PATH, m.PREFLIGHT_PATH))


def test_import_preflight_has_only_explicit_canonical_execution_path():
    tree = ast.parse(inspect.getsource(m))
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
               for alias in node.names}
    assert not any(name.startswith(("flygym", "mujoco")) for name in imports)
    source = inspect.getsource(m)
    assert '"--run-windows"' in source and ".step(" not in source
    assert "_windows_m10b_perturbation_scaling_adapter" in source
    assert not any(name.startswith("run") for name in vars(m))


def test_preregistration_matches_code_and_zero_transition_preflight():
    recorded = json.loads(m.PREREGISTRATION_PATH.read_text(encoding="utf-8"))
    # Validation maps the frozen legacy checkout-root strings to the portable
    # identifiers returned by protocol(), without rewriting the frozen file.
    m.validate_protocol(recorded)
    result = m.preflight()
    assert result["status"] == "PREFLIGHT_PASS"
    assert result["canonical_experiment_executed"] is False
    assert result["physics_runtime_constructed"] is False
    assert result["male_cns_constructed"] is False
    assert result["physics_transitions"] == result["neural_transitions"] == 0
    assert result["sensory_encoding_or_delivery_count"] == 0
    assert result["neural_motor_decode_or_application_count"] == 0
    assert result["verified_m10a_artifact_hashes"] == m.M10A_ARTIFACTS
    assert result["frozen_preregistration_sha256"] == m.PREREGISTRATION_SHA256


def test_preregistration_exact_byte_identity_fails_closed(tmp_path):
    assert m.verify_preregistration() == "a267647093d616f394374761da58ae495f12a6df6fe12e004abbcb1cb1b2d5a9"
    changed = tmp_path / "m10b_preregistration.json"
    original = m.PREREGISTRATION_PATH.read_bytes()
    changed.write_bytes(original.replace(b"0.256", b"0.257", 1))
    with pytest.raises(RuntimeError, match="frozen preregistration mismatch"):
        m.verify_preregistration(changed)


def test_preregistration_lf_and_windows_crlf_share_canonical_identity(tmp_path):
    lf = m.PREREGISTRATION_PATH.read_bytes()
    assert b"\r" not in lf
    crlf_path = tmp_path / "m10b_preregistration.json"
    crlf_path.write_bytes(lf.replace(b"\n", b"\r\n"))
    assert m.verify_preregistration(crlf_path) == m.PREREGISTRATION_SHA256
    assert hashlib.sha256(crlf_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == m.PREREGISTRATION_SHA256


def test_protocol_paths_are_checkout_independent_and_runtime_paths_resolve(monkeypatch):
    expected = m.FUTURE_OUTPUT_IDENTIFIERS
    linux_protocol = m.protocol()
    linux = Path("/workspace/FlyBrainUnity/malecns_backend/embodiment")
    windows = Path("C:/Users/legen/Documents/FlyBrainUnity/malecns_backend/embodiment")
    monkeypatch.setattr(m, "HERE", windows)
    assert m.protocol() == linux_protocol
    assert {key: linux_protocol["future_outputs"][key] for key in expected} == expected
    for key, identifier in expected.items():
        assert m.resolve_future_output(identifier, linux) == linux / Path(identifier)
        assert m.resolve_future_output(identifier, windows) == windows / Path(identifier)
        assert getattr(m, key.upper() + "_PATH") == m.resolve_future_output(identifier)
    with pytest.raises(ValueError, match="unknown M10B output identifier"):
        m.resolve_future_output("../m10a_report.json")


def _synthetic_condition(name):
    import numpy as np
    force = np.asarray([m.force_at_transition(name, i) for i in range(15000)])
    enabled = dict((n, e) for n, e, _ in m.CONDITIONS)[name]
    return {"applied_external_force": force,
        "admitted_neural_motor_pre_intervention": np.ones((3000, 11)),
        "admitted_neural_motor_physical_contribution":
            np.ones((15000, 11)) if enabled else np.zeros((15000, 11))}


def test_force_and_disabled_motor_integrity_detect_corruption():
    np = pytest.importorskip("numpy")
    conditions = {name: _synthetic_condition(name) for name, _, _ in m.CONDITIONS}
    assert adapter.check_force_integrity(conditions)["passed"]
    assert adapter.check_disabled_motor_integrity(conditions)["passed"]
    conditions["A_F0256"]["applied_external_force"][4999, 1] = .256
    with pytest.raises(RuntimeError, match="applied-force corruption"):
        adapter.check_force_integrity(conditions)
    conditions = {name: _synthetic_condition(name) for name, _, _ in m.CONDITIONS}
    conditions["B_F1024"]["admitted_neural_motor_physical_contribution"][0, 0] = np.nextafter(0., 1.)
    with pytest.raises(RuntimeError, match="disabled motor physically admitted"):
        adapter.check_disabled_motor_integrity(conditions)


def test_complete_raw_contract_is_shape_checked_without_runtime():
    np = pytest.importorskip("numpy")
    arrays = {name: np.zeros(shape, dtype=("<U4" if name == "condition_identity" else float))
              for name, shape in m.RAW_SCHEMA.items()}
    arrays["condition_identity"] = np.asarray("A_C")
    arrays["motor_enabled"] = np.asarray(True)
    adapter.validate_raw_condition(arrays)
    arrays["joint_positions"] = np.zeros((15000, 42))
    with pytest.raises(RuntimeError, match="raw schema mismatch"):
        adapter.validate_raw_condition(arrays)


def test_runner_maps_order_fresh_runtime_and_m9_semantics_without_execution():
    calls = []
    def runner(**kwargs):
        calls.append(kwargs)
        return {"physics_steps": 0, "neural_steps": 0}
    for number, (condition, enabled, _) in enumerate(m.CONDITIONS, 1):
        adapter._invoke(runner, {}, (), (), condition, number, True)
        values = {name: index + .5 for index, name in enumerate(m.m7d.ADMITTED_MOTOR)}
        gated = calls[-1]["contribution_gate"](values, condition, tuple(values))
        assert gated == (values if enabled else dict.fromkeys(values, 0.0))
    assert [call["condition"] for call in calls] == [row[0] for row in m.CONDITIONS]
    assert len(calls) == 10 and all(call["initialize_only"] for call in calls)
    assert all(call["runtime_factory"] is adapter.m7da._runtime for call in calls)
    assert all(call["m10b_extended_telemetry"] for call in calls)
    assert "run_windows" not in inspect.getsource(adapter._invoke)


def test_transition_accounting_and_execution_absences_are_exact():
    assert (m.PHYSICS_TRANSITIONS_PER_CONDITION, m.NEURAL_UPDATES_PER_CONDITION) == (15000, 3000)
    assert (m.TOTAL_PHYSICS_TRANSITIONS, m.TOTAL_NEURAL_UPDATES) == (150000, 30000)
    assert m.protocol()["execution_absences"] == {"controllers": False, "reward": False,
        "rl": False, "reference_trajectory": False, "gait_logic": False,
        "contact_sensory_input": False}


def test_exclusive_json_publish_and_protected_namespaces(tmp_path):
    target = tmp_path / "m10b_manifest.json"
    adapter._publish_json(target, {"ok": True})
    with pytest.raises(FileExistsError):
        adapter._publish_json(target, {"ok": False})
    source = inspect.getsource(adapter.run_windows)
    assert "m9b.RAW_PATH.open" not in source and "m10b.RAW_PATH.open(\"xb\")" in source
    assert "m10b.verify_m10a()" in inspect.getsource(adapter._assert_protected_unchanged)
