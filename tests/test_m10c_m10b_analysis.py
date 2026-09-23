"""Focused deterministic tests for analysis-only M10C; no simulation is run."""
import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

from malecns_backend.embodiment import m10c_m10b_analysis as m10c


def test_import_is_inert():
    module = importlib.reload(m10c)
    assert module.PHYSICS_TRANSITIONS == module.NEURAL_TRANSITIONS == 0
    assert "mujoco" not in module.__dict__ and "flygym" not in module.__dict__


def test_euclidean_com_deviation():
    actual = m10c.euclidean_deviation(np.array([[0, 0, 0], [1, 2, 3]]),
                                      np.array([[0, 0, 0], [1, -2, 0]]))
    assert np.array_equal(actual, [0, 5])


def test_quaternion_sign_invariance_and_shortest_arc():
    identity = np.array([[1., 0, 0, 0]])
    assert m10c.quaternion_shortest_arc_deg(identity, -identity).item() == 0
    quarter_turn = np.array([[np.sqrt(.5), 0, 0, np.sqrt(.5)]])
    assert m10c.quaternion_shortest_arc_deg(identity * 7, quarter_turn * 3).item() == pytest.approx(90)


def test_exact_window_boundaries():
    times = np.array([0, 499.9, 500, 519.9, 520, 556.9, 557, 1500, 1500.1])
    selected = {name: times[m10c.window_mask(times, rule)].tolist()
                for name, rule in m10c.WINDOWS.items()}
    assert selected["pre_perturbation"] == [0, 499.9]
    assert selected["direct_force"] == [500, 519.9]
    assert selected["early_post_force"] == [520, 556.9]
    assert selected["later_post_force"] == [557, 1500]


def test_enabled_minus_disabled_and_maximum_reduction():
    row = m10c.reduce_window(np.array([1., 4., 2.]), np.array([1., 2., 3.]),
                             np.array([520., 521., 522.]),
                             {"start_ms_inclusive": 520., "stop_ms_exclusive": 523.}, .5)
    assert row["enabled_maximum_deviation"] == 4
    assert row["disabled_maximum_deviation"] == 3
    assert row["directional_effect"] == 1
    assert row["enabled_maximum_time_ms"] == 521


@pytest.mark.parametrize("effect,expected", [(-.25, "ATTENUATING"), (.25, "AMPLIFYING"),
                                               (0, "UNRESOLVED"), (.249, "UNRESOLVED")])
def test_inclusive_threshold_and_unresolved(effect, expected):
    assert m10c.classify_window(effect, .25) == expected


def test_mixed_and_no_resolved_overall_rules():
    assert m10c.classify_overall("ATTENUATING", "AMPLIFYING") == "DIRECTIONALLY_MIXED"
    assert m10c.classify_overall("UNRESOLVED", "UNRESOLVED") == "NO_RESOLVED_DIRECTIONAL_EFFECT"
    assert m10c.classify_overall("UNRESOLVED", "ATTENUATING") == "ATTENUATING"


def test_scaling_changes_and_monotonicity():
    rows = [{"directional_effect": x, "directional_classification": label} for x, label in
            [(-1, "ATTENUATING"), (-2, "ATTENUATING"), (1, "AMPLIFYING"), (3, "AMPLIFYING")]]
    result = m10c.scaling_summary(rows)
    assert result["adjacent_signed_changes"] == [-1, 3, 2]
    assert result["adjacent_absolute_effect_changes"] == [1, -1, 2]
    assert result["absolute_effect_monotonic_nondecreasing"] is False
    assert result["adjacent_resolved_sign_changes"] == [False, True, False]
    for row, value in zip(rows, [1, 2, 3, 4]):
        row["directional_effect"] = value
    assert m10c.scaling_summary(rows)["absolute_effect_monotonic_nondecreasing"] is True


def _protocol_files(directory: Path):
    conditions = [{"force_magnitude": f, "fresh_identical_deterministic_initialization": True,
                   "motor_enabled": enabled, "name": name} for f, name, enabled in m10c.CONDITIONS]
    report = {"status": "COMPLETE_UNANALYZED", "canonical_experiment_executed": True,
              "disabled_motor_integrity": {"passed": True}, "force_integrity": {"passed": True},
              "condition_order": [x[1] for x in m10c.CONDITIONS]}
    manifest = {"conditions": conditions, "disabled_motor_integrity": {"passed": True},
                "force_integrity": {"passed": True}}
    prereg = {"conditions": conditions, "scientific_question": m10c.SCIENTIFIC_QUESTION,
              "analysis_windows": m10c.WINDOWS, "directional_resolution": {"thresholds": m10c.THRESHOLDS},
              "supporting_metrics": []}
    values = {"m10b_raw.npz": b"synthetic-not-loaded",
              "m10b_report.json": json.dumps(report).encode(),
              "m10b_manifest.json": json.dumps(manifest).encode(),
              "m10b_preregistration.json": json.dumps(prereg).encode()}
    for name, value in values.items():
        (directory / name).write_bytes(value)
    return {name: {"byte_size": len(value), "sha256": hashlib.sha256(value).hexdigest()}
            for name, value in values.items()}


def test_fail_closed_artifact_hash_mismatch(tmp_path):
    expected = _protocol_files(tmp_path)
    expected["m10b_report.json"]["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="identity mismatch"):
        m10c.validate_provenance(tmp_path, expected)


@pytest.mark.parametrize("section", ["disabled_motor_integrity", "force_integrity"])
def test_integrity_failure_is_rejected(tmp_path, section):
    expected = _protocol_files(tmp_path)
    report_path = tmp_path / "m10b_report.json"
    report = json.loads(report_path.read_text())
    report[section]["passed"] = False
    report_path.write_text(json.dumps(report))
    content = report_path.read_bytes()
    expected["m10b_report.json"] = {"byte_size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    with pytest.raises(RuntimeError, match="integrity failure"):
        m10c.validate_provenance(tmp_path, expected)


def _primary_arrays():
    arrays = {}
    times = np.linspace(0, 1500, 15001)
    quaternion = np.zeros((15001, 4)); quaternion[:, 0] = 1
    for _, condition, _ in m10c.CONDITIONS:
        arrays[f"{condition}__physics_time_ms"] = times.copy()
        arrays[f"{condition}__root_thorax_position"] = np.zeros((15001, 3))
        arrays[f"{condition}__root_orientation_wxyz"] = quaternion.copy()
    return arrays


def test_analysis_does_not_modify_input_arrays_or_canonical_files(tmp_path):
    expected = _protocol_files(tmp_path)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    arrays = _primary_arrays()
    arrays_before = {name: value.copy() for name, value in arrays.items()}
    m10c.validate_provenance(tmp_path, expected)
    per_force, scaling = m10c.analyze_arrays(arrays)
    assert per_force and scaling
    assert all(np.array_equal(value, arrays_before[name]) for name, value in arrays.items())
    assert before == {path.name: path.read_bytes() for path in tmp_path.iterdir()}


def test_array_validation_rejects_time_misalignment_and_nonfinite_primary_data():
    arrays = _primary_arrays()
    arrays["A_F0256__physics_time_ms"][3] += .01
    with pytest.raises(RuntimeError, match="time vectors"):
        m10c.analyze_arrays(arrays)
    arrays = _primary_arrays()
    arrays["B_F4096__root_thorax_position"][4, 0] = np.nan
    with pytest.raises(RuntimeError, match="nonfinite"):
        m10c.analyze_arrays(arrays)


def test_output_manifest_does_not_self_hash(tmp_path):
    output = tmp_path / "m10c"
    m10c._write_outputs(output, {"source_git_commit": "synthetic"},
                         {"m10b_preregistration.json": {"sha256": "x", "byte_size": 1}})
    manifest = json.loads((output / "m10c_manifest.json").read_text())
    assert set(manifest["outputs"]) == {"m10c_analysis.json"}
    assert "m10c_manifest.json" not in manifest["outputs"]


def test_cli_requires_explicit_analyze():
    with pytest.raises(SystemExit):
        m10c.main([])
