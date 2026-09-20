"""M7C-B4 contract tests.  No Windows physics experiment is run here."""
import ast
import copy
import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

from malecns_backend.embodiment import m7c_b4_stability as m


def _artifact(tmp_path):
    value = json.loads(m.B3_PATH.read_text(encoding="utf-8"))
    path = tmp_path / "b3.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path, value


@pytest.mark.parametrize("field,value", [("analytic_dz", 0.1), ("corrected_spawn_z", 0.6)])
def test_exact_b3_height_is_required(tmp_path, field, value):
    path, artifact = _artifact(tmp_path)
    artifact["analytic_solution"][field] = value
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(RuntimeError, match=field): m.validate_b3(path)


def test_exact_tripod_and_complete_provenance_are_required(tmp_path):
    path, artifact = _artifact(tmp_path)
    artifact["tripod_pose"]["relative_path"] = "data/pose/pose_zero.yaml"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(RuntimeError, match="tripod"): m.validate_b3(path)
    artifact["tripod_pose"]["relative_path"] = "data/pose/pose_tripod.yaml"
    artifact["status"] = "INCOMPLETE"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(RuntimeError, match="status"): m.validate_b3(path)


def test_every_b3_gate_and_zero_transition_protocol_value_is_required(tmp_path):
    _, original = _artifact(tmp_path)
    mutations = [
        ("zero_step_reconstruction", "future_physics_eligible"),
        ("protocol", "physics_transitions"), ("protocol", "neural_transitions"),
        ("protocol", "adhesion_enabled"), ("protocol", "calibration_surface_changed"),
        ("protocol", "height_sweep"), ("protocol", "optimizer"),
    ]
    for parent, key in mutations:
        artifact = copy.deepcopy(original); artifact[parent][key] = not artifact[parent][key]
        path = tmp_path / f"{parent}-{key}.json"; path.write_text(json.dumps(artifact))
        with pytest.raises(RuntimeError): m.validate_b3(path)


def _state(target, *, finite=True, adhesion=0):
    return {"finite": finite, "commanded_targets": target.copy(),
            "action": np.r_[target, np.full(6, adhesion)]}


def test_trace_is_exactly_1001_states_with_constant_baseline_and_zero_adhesion():
    target = np.arange(42.0); records = [_state(target) for _ in range(m.STATES)]
    m.validate_trace(records, target, np)
    with pytest.raises(RuntimeError, match="state count"): m.validate_trace(records[:-1], target, np)
    records[500]["commanded_targets"][0] += 1
    with pytest.raises(RuntimeError, match="target changed"): m.validate_trace(records, target, np)
    records[500] = _state(target, adhesion=1)
    with pytest.raises(RuntimeError, match="adhesion"): m.validate_trace(records, target, np)


def test_nonfinite_physics_fails_closed():
    target = np.zeros(42); records = [_state(target) for _ in range(m.STATES)]
    records[-1]["finite"] = False
    with pytest.raises(RuntimeError, match="nonfinite"): m.validate_trace(records, target, np)


def test_frozen_constants_schema_and_checkpoints():
    assert (m.INIT_POSE, m.SPAWN_POS, m.SPAWN_ORIENTATION) == ("tripod", (0, 0, 0.6045752232266313), (0, 0, 0))
    assert (m.DT, m.TRANSITIONS, m.STATES) == (0.0001, 1000, 1001)
    assert m.CHECKPOINTS == (0, 72, 130, 1000)
    schema = m.telemetry_schema()
    assert schema["states"] == 1001
    assert {"self_contacts", "calibration_surface_contacts"} <= set(schema["json_utf8"])


def test_no_neural_controller_learning_tuning_or_pose_mutation_code():
    source = Path(m.__file__).read_text(encoding="utf-8"); tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports += [x.name for x in node.names]
        elif isinstance(node, ast.ImportFrom): imports.append(node.module or "")
    assert not any("neural" in x.lower() or x == "malecns_backend.neural" for x in imports)
    forbidden = ("gait_controller", "balance_controller", "reference_trajectory", "reward(", "optimizer(", "height_sweep(", "collision_mask")
    assert not any(token in source.lower() for token in forbidden)
    assert source.count("sim.step(action)") == 1
    assert "spawn_pos=SPAWN_POS" in source and "init_pose=INIT_POSE" in source


def test_completed_output_and_raw_are_never_overwritten(tmp_path, monkeypatch):
    summary, manifest, raw = (tmp_path / name for name in ("summary.json", "manifest.json", "raw.npz"))
    monkeypatch.setattr(m, "SUMMARY_PATH", summary); monkeypatch.setattr(m, "MANIFEST_PATH", manifest); monkeypatch.setattr(m, "RAW_PATH", raw)
    summary.write_text('{"status":"COMPLETE"}')
    assert not m._output_available()
    with pytest.raises(FileExistsError): m._write_exclusive(summary, {})
    summary.unlink(); raw.write_bytes(b"canonical")
    assert not m._output_available()


def test_fall_is_recorded_not_an_early_break_or_retry():
    source = Path(m.__file__).read_text(encoding="utf-8")
    loop = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.For) and
                any(isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr == "step" for x in ast.walk(n)))
    assert not any(isinstance(x, (ast.Break, ast.Continue)) for x in ast.walk(loop))
    assert "range(TRANSITIONS)" in ast.get_source_segment(source, loop)
