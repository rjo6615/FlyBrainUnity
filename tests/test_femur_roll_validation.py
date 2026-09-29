import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from malecns_backend.embodiment import femur_roll_validation as audit
from malecns_backend.embodiment import _femur_roll_mechanical_validation as mechanical


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_import_and_help_perform_zero_scientific_operations(tmp_path):
    marker = tmp_path / "must_not_exist.json"
    code = ("from malecns_backend.embodiment import femur_roll_validation as a; "
            f"a.OUTPUT=__import__('pathlib').Path({str(marker)!r}); a.main(['--help'])")
    run = subprocess.run([sys.executable, "-c", code], cwd=audit.ROOT,
                         capture_output=True, text=True)
    assert run.returncode == 0
    assert "--mechanical" in run.stdout
    assert not marker.exists()
    imported = subprocess.run(
        [sys.executable, "-c",
         "import malecns_backend.embodiment.femur_roll_validation; "
         "import malecns_backend.embodiment._femur_roll_mechanical_validation"],
        cwd=audit.ROOT, capture_output=True, text=True)
    assert imported.returncode == 0


def test_static_validation_cannot_modify_active_interface(tmp_path, monkeypatch):
    before = _digest(audit.INTERFACE_MAP)
    monkeypatch.setattr(audit, "OUTPUT", tmp_path / "result.json")
    assert audit.main([]) == 0
    assert _digest(audit.INTERFACE_MAP) == before
    result = json.loads(audit.OUTPUT.read_text())
    assert result["scope"]["active_11_channel_interface_modified"] is False
    assert result["scope"]["channels_admitted"] == 0


@pytest.mark.parametrize("qidx", range(6))
def test_only_selected_qpos_coordinate_changes(qidx):
    neutral = [0.0] * 6
    perturbed = neutral.copy(); perturbed[qidx] = mechanical.EPSILON
    mechanical.assert_isolated(neutral, perturbed, qidx, mechanical.EPSILON)
    perturbed[(qidx + 1) % 6] = 1.0
    with pytest.raises(RuntimeError, match="exactly the expected qpos"):
        mechanical.assert_isolated(neutral, perturbed, qidx, mechanical.EPSILON)


def test_exact_action_and_compiled_identity_contracts():
    ordered = [f"unused_{i}" for i in range(42)]
    for name, (index, _, _, _) in audit.CANDIDATES.items():
        ordered[index] = name
    for name, (index, _, _, _) in audit.CANDIDATES.items():
        mechanical.validate_identity(tuple(ordered), index, f"0/actuator_position_{name}",
                                     f"0/{name}", 100 + index, 100 + index, name)
        with pytest.raises(RuntimeError, match="identity differs"):
            mechanical.validate_identity(tuple(ordered), index, "0/actuator_position_wrong",
                                         f"0/{name}", 100 + index, 100 + index, name)


def test_no_neural_runtime_physics_step_or_controller_logic_is_introduced():
    paths = [Path(audit.__file__), Path(mechanical.__file__)]
    sources = "\n".join(path.read_text() for path in paths)
    trees = [ast.parse(path.read_text()) for path in paths]
    called_attributes = {node.func.attr for tree in trees for node in ast.walk(tree)
                         if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert "step" not in called_attributes
    imported_modules = {node.module for tree in trees for node in ast.walk(tree)
                        if isinstance(node, ast.ImportFrom)} | {
                            alias.name for tree in trees for node in ast.walk(tree)
                            if isinstance(node, ast.Import) for alias in node.names}
    assert not any(module and ("neural" in module.lower() or "malecns" in module.lower())
                   for module in imported_modules)
    forbidden = ("gait", "stabilization", "controller")
    assert all(term not in sources for term in forbidden)
    result = audit.build()
    assert result["scientific_operations"] == {
        "malecns_transitions": 0, "physics_steps": 0,
        "forward_kinematics_calls": 0, "neural_runtime_constructed": False}
    assert result["scope"]["neural_experiment_run"] is False
    assert result["scope"]["execution_authorization_created"] is False


def test_unresolved_biological_sign_fails_closed_and_antagonists_stay_missing():
    result = audit.build()
    assert set(result["candidate_channels"]) == set(audit.CANDIDATES)
    for name, record in result["candidate_channels"].items():
        assert record["action_index"] == audit.CANDIDATES[name][0]
        assert record["identity_valid"] is True
        assert record["biological_coordinate_sign"] is None
        assert record["biological_direction_resolved"] is False
        assert record["classification"] == "MECHANICAL_DIRECTION_UNRESOLVED"
        opposite = record["opposite_direction_population"]
        assert opposite == {"present_in_source": False, "exact_names": [],
                            "synthesized": False,
                            "status": "SOURCE_HAS_NO_ANTAGONIST_POPULATION"}
        assert "SOURCE_HAS_NO_ANTAGONIST_POPULATION" in record["statuses"]


def test_mechanics_can_resolve_coordinate_but_not_biological_sign():
    evidence = {
        "world_joint_axis_neutral": [0, 1, 0],
        "positive_minus_negative_endpoint_displacement": [0.1, 0.0, 0.0],
        "positive": {"relative_segment_rotation_rad": .0001,
                     "world_rotation_axis_direction": [0, 1, 0]},
        "negative": {"relative_segment_rotation_rad": .0001,
                     "world_rotation_axis_direction": [0, -1, 0]},
    }
    assert mechanical.mechanical_direction_resolved(evidence) is True
    result = audit.build()
    assert all(record["biological_coordinate_sign"] is None
               for record in result["candidate_channels"].values())
