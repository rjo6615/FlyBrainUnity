"""Focused M11A design tests; no scientific runtime is constructed."""
import ast
import hashlib
import inspect
import json

import pytest

from malecns_backend.embodiment import m11_motor_channel_dissection as m


def test_exact_frozen_upstream_identity_registry_and_fail_closed(tmp_path):
    assert m.UPSTREAM_ARTIFACTS["m10b_raw.npz"] == {"directory": "m10b", "sha256": "85e98715ac3d8b219c86ef338187828e787ee8f300bacad9d318809e23208cde", "byte_size": 57652701}
    assert m.UPSTREAM_ARTIFACTS["m10c_analysis.json"]["sha256"] == "31d7dd5445ecd6bc17542f455d5196a087934f3251d5c36915424b737e595740"
    assert set(m.UPSTREAM_ARTIFACTS) == {"m10b_raw.npz", "m10b_report.json", "m10b_manifest.json", "m10b_preregistration.json", "m10c_analysis.json", "m10c_manifest.json"}
    with pytest.raises(RuntimeError, match="before transitions.*m10b_raw"):
        m.verify_upstream(tmp_path, tmp_path)


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
