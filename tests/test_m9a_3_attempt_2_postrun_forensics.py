"""Synthetic, zero-transition tests for M9A-3 Attempt-2 forensics."""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

from malecns_backend.embodiment import m9a_3_attempt_2_postrun_forensics as forensic


def _arrays(magnitude: float, condition: str) -> dict[str, np.ndarray]:
    count = 15001
    root = np.zeros((count, 3)); root[:, 2] = 1.0
    velocity = np.zeros((count, 3)); velocity[1] = [0.0, 11.0, 0.0]
    orientation = np.zeros((count, 4)); orientation[:, 0] = 1.0
    force = np.zeros((count, 3))
    feet = np.zeros((count, 6, 3))
    if condition == "P":
        force[5000:5200, 1] = magnitude
        # Only the largest candidate crosses the registered 0.005-mm posture gate.
        root[5001:, 1] = magnitude * .003
        velocity[5001:, 1] = magnitude * .01
        feet[5001:, 0, 1] = magnitude * .002
    return {"time_ms": np.arange(count) * .1, "root_position": root,
        "orientation_wxyz": orientation, "body_up_z": np.ones(count),
        "linear_velocity": velocity, "angular_velocity": np.zeros((count, 3)),
        "ground_contact": np.zeros((count, 6), dtype=bool),
        "distal_tarsus_positions": feet, "applied_force": force,
        "fixed_actuator_commands": np.zeros((count, 42)),
        "finite": np.ones(count, dtype=bool)}


@pytest.fixture()
def synthetic_files(tmp_path: Path):
    files = []
    for magnitude in forensic.MAGNITUDES:
        for condition in forensic.CONDITIONS:
            path = tmp_path / f"candidate_{magnitude:.6f}_{condition}_raw.npz"
            np.savez_compressed(path, **_arrays(magnitude, condition))
            files.append((magnitude, condition, path))
    return tuple(files)


def test_namespace_has_no_scientific_transition_route():
    source = inspect.getsource(forensic)
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == "step" for node in ast.walk(tree))
    assert "flygym" not in source.lower() and "mujoco" not in source.lower()
    assert '"physics_transitions": 0' in source
    assert '"neural_transitions": 0' in source


def test_inventory_fails_closed_before_loading_and_records_exact_bytes(tmp_path):
    absent = ((.256, "P", tmp_path / "missing.npz"),)
    with pytest.raises(FileNotFoundError, match="missing canonical Attempt-2 raw evidence"):
        forensic.inventory(absent)
    path = tmp_path / "evidence.npz"; path.write_bytes(b"evidence")
    record = forensic.inventory(((.256, "P", path),))[0]
    assert record == {"filename": "evidence.npz", "byte_size": 8,
                      "sha256": "ee8250fb76e094b34b471f13a73dbbe51d1ae142e9df59d7c0d31ec20f0a0a8e"}


def test_loader_explicitly_disables_pickle(tmp_path, monkeypatch):
    seen = {}

    class Archive:
        files = list(forensic.REQUIRED)
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def __getitem__(self, key): return np.zeros(1)

    def fake_load(path, **kwargs):
        seen.update(kwargs); return Archive()

    monkeypatch.setattr(np, "load", fake_load)
    forensic._load(np, tmp_path / "dummy.npz")
    assert seen == {"allow_pickle": False}


def test_synthetic_complete_analysis_reproduces_failure_and_forensics(synthetic_files):
    report = forensic.analyze(synthetic_files)
    assert report["physics_transitions"] == report["neural_transitions"] == 0
    assert report["production_selection_result"] == "NO_PREREGISTERED_CANDIDATE_QUALIFIES"
    assert report["evidence_before_and_after_identical"] is True
    assert report["absolute_speed_forensics"] == {
        "same_preforce_maximum_shared_across_all_four_matched_pairs": True,
        "hypothesis": "SHARED_PREPERTURBATION_BASELINE_TRANSIENT_EXCEEDS_ABSOLUTE_SPEED_LIMIT",
        "hypothesis_supported": True,
    }
    assert report["magnitude_2_048_meaningfulness"]["satisfies_one_or_more"] is True
    assert report["magnitude_2_048_meaningfulness"]["not_a_selection"] is True
    assert all(report["perturbation_response_monotonic_non_decreasing"].values())
    for magnitude in forensic.MAGNITUDES:
        audit = report["condition_protocol_audits"][f"{magnitude:.6f}"]
        assert audit["P"]["force_nonzero_indices"] == list(range(5000, 5200))
        assert audit["P"]["force_schedule_exact"] and audit["C"]["force_schedule_exact"]
        peak = audit["P"]["maximum_absolute_root_linear_speed"]
        assert peak["p_c_linear_velocity_exactly_equal_at_state"]
        assert peak["p_c_physical_state_exactly_equal_at_state"]


def test_report_creation_is_exclusive_and_outside_evidence(tmp_path):
    target = tmp_path / "forensics" / "report.json"
    forensic.write_report({"physics_transitions": 0, "neural_transitions": 0}, target)
    with pytest.raises(FileExistsError):
        forensic.write_report({}, target)
    assert target.read_text().endswith("\n")
    assert forensic.REPORT_PATH.parent != forensic.EVIDENCE_DIR


def test_exact_canonical_filename_set_is_declared():
    assert [path.name for _, _, path in forensic.FILES] == [
        f"candidate_{magnitude:.6f}_{condition}_raw.npz"
        for magnitude in forensic.MAGNITUDES for condition in forensic.CONDITIONS]
