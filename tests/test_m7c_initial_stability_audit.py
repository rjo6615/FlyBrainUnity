"""Synthetic/static tests only: no M7, neural, or physics transition is run."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from malecns_backend.embodiment import m7c_canonical_first10ms as first10
from malecns_backend.embodiment import m7c_initial_stability_audit as initial


def _archive(path: Path, *, mismatch=False, malformed=False) -> None:
    t = np.arange(101, dtype=np.float64) / 10
    pos = np.zeros((101, 3)); pos[:, 2] = np.linspace(.5, .2, 101)
    quat = np.tile([1., 0., 0., 0.], (101, 1))
    values = {"physics_time_ms": t, "physics_qpos": np.zeros((101, 49)),
        "physics_qvel": np.zeros((101, 48)), "physics_joint_position": np.zeros((101, 42)),
        "physics_action": np.zeros((101, 42)), "physics_ctrl": np.zeros((101, 42)),
        "physics_body_position": pos, "physics_body_orientation": quat,
        "physics_contact_forces": np.zeros((101, 36, 3))}
    arrays = {}
    for condition in first10.CONDITIONS:
        for name, value in values.items(): arrays[f"{condition}__{name}"] = value.copy()
    if mismatch: arrays[f"{first10.CONDITIONS[1]}__physics_body_position"][1, 0] = 1
    if malformed: arrays[f"{first10.CONDITIONS[0]}__physics_qvel"] = np.zeros((100, 48))
    np.savez(path, **arrays)


def _trust_synthetic(monkeypatch, path):
    monkeypatch.setattr(first10, "CANONICAL_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())


def test_canonical_sha_rejection_and_no_mutation(tmp_path):
    raw = tmp_path / "raw.npz"; _archive(raw); before = raw.read_bytes()
    with pytest.raises(first10.EvidenceError, match="SHA-256 mismatch"): first10.analyze(raw)
    assert raw.read_bytes() == before


def test_first10_reconstructs_predicates_equality_and_small_json(tmp_path, monkeypatch):
    raw = tmp_path / "raw.npz"; _archive(raw); _trust_synthetic(monkeypatch, raw)
    before = raw.read_bytes(); report = first10.analyze(raw)
    assert report["np_load_allow_pickle"] is False
    assert report["physics_transitions_executed"] == report["neural_transitions_executed"] == 0
    assert all(v["array_equal"] for v in report["condition_equality"].values())
    trajectory = report["trajectories"][first10.CONDITIONS[0]]
    assert trajectory["first_fall_sample_index"] == 84
    assert trajectory["samples"][84]["fall"]["height_below_threshold"] is True
    assert raw.read_bytes() == before
    assert len(json.dumps(report)) < 2_000_000


def test_fail_closed_malformed_or_different_telemetry(tmp_path, monkeypatch):
    for kind in ("malformed", "mismatch"):
        raw = tmp_path / f"{kind}.npz"; _archive(raw, **{kind: True}); _trust_synthetic(monkeypatch, raw)
        with pytest.raises(first10.EvidenceError): first10.analyze(raw)


def test_analyzer_disables_pickle_and_has_no_scientific_runner_import():
    source = Path(first10.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert "allow_pickle=False" in source
    assert not any("m7_spontaneous_locomotion" in name or "_windows_m6c_live_condition" in name for name in imports)


def test_exact_baseline_comparison_and_zero_step_contract():
    source = Path(initial.__file__).read_text(encoding="utf-8")
    assert "baseline = joints.copy(); mismatch = baseline - joints" in source
    assert ".step(" not in source
    assert '"physics_transitions": 0' in source and '"neural_transitions": 0' in source
    assert "data.contact" in source and "SURFACE_HALF_SIZE" in source


def test_unavailable_preflight_is_explicit_and_zero_transition(monkeypatch):
    real = initial.importlib.import_module
    def unavailable(name):
        if name == "flygym": raise ImportError("synthetic absence")
        return real(name)
    monkeypatch.setattr(initial.importlib, "import_module", unavailable)
    report = initial.build_report()
    assert report["run_status"] == "UNAVAILABLE"
    assert report["physics_transitions"] == report["neural_transitions"] == 0
