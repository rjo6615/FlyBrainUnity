import ast
import importlib
from pathlib import Path

import pytest

from malecns_backend.embodiment import coxa_yaw_anatomical_sign_bridge as bridge


EXPECTED = (
    ("LF", "joint_LFCoxa_yaw", 2, "LFFemur"),
    ("LM", "joint_LMCoxa_yaw", 9, "LMFemur"),
    ("LH", "joint_LHCoxa_yaw", 16, "LHFemur"),
    ("RF", "joint_RFCoxa_yaw", 23, "RFFemur"),
    ("RM", "joint_RMCoxa_yaw", 30, "RMFemur"),
    ("RH", "joint_RHCoxa_yaw", 37, "RHFemur"),
)


def test_exact_targets_action_vector_and_active_interface():
    assert bridge.TARGETS == EXPECTED
    for _, _, index, _ in EXPECTED:
        action = bridge.isolated_action(index, .1)
        assert len(action) == 42
        assert [i for i, value in enumerate(action) if value] == [index]
    ready = bridge.preflight()
    assert ready["active_interface_count"] == 11
    assert ready["active_interface_modified"] is False
    assert ready["neural_transitions"] == ready["physics_transitions"] == 0


def test_import_and_preflight_have_no_scientific_runtime(monkeypatch):
    forbidden = ("flygym", "mujoco", "malecns_backend.neural", "bodymap", "motor_population_activity_survey")
    original = importlib.import_module

    def guarded(name, *args, **kwargs):
        assert not any(token in name for token in forbidden)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", guarded)
    assert bridge.preflight()["sign_dependent_outcomes_evaluated"] is False


def test_preregistration_hash_fails_closed(tmp_path):
    changed = tmp_path / "changed.json"
    changed.write_bytes(bridge.PREREGISTRATION_PATH.read_bytes() + b" ")
    with pytest.raises(RuntimeError, match="SHA-256"):
        bridge.verify_preregistration(changed)


def test_output_paths_refuse_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "ATTEMPT_PATH", tmp_path / "attempt.json")
    monkeypatch.setattr(bridge, "RESULT_PATH", tmp_path / "result.json")
    assert bridge.output_available()
    bridge.ATTEMPT_PATH.write_text("occupied")
    assert not bridge.output_available()
    with pytest.raises(FileExistsError):
        bridge.preflight()


def evidence(plus, minus, *, mechanical=True, identity=True):
    return {"geometry_identity_valid": identity, "fresh_baseline_identical": identity,
            "mechanical_valid": mechanical,
            "positive": {"projected_anterior_displacement": plus},
            "negative": {"projected_anterior_displacement": minus}}


@pytest.mark.parametrize("value", [
    evidence(1e-12, -1e-12), evidence(1.0, .5), evidence(1.0, 0.0), evidence(1.0, -1.0, mechanical=False)
])
def test_classification_rejects_near_zero_nonopposing_and_mechanical_failure(value):
    assert bridge.classify_leg(value) not in {"ANTERIOR_SIGN_POSITIVE", "ANTERIOR_SIGN_NEGATIVE"}


def test_classification_resolves_both_directions_and_identity_fails_closed():
    assert bridge.classify_leg(evidence(1, -1)) == "ANTERIOR_SIGN_POSITIVE"
    assert bridge.classify_leg(evidence(-1, 1)) == "ANTERIOR_SIGN_NEGATIVE"
    assert bridge.classify_leg(evidence(1, -1, identity=False)) == "GEOMETRY_IDENTITY_FAILURE"
    assert bridge.coordinate_signs("ANTERIOR_SIGN_POSITIVE") == (1, -1)
    assert bridge.coordinate_signs("ANTERIOR_SIGN_NEGATIVE") == (-1, 1)


def test_legs_are_independent_not_mirrored():
    outcomes = {leg: bridge.classify_leg(evidence(1 if i % 2 else -1, -1 if i % 2 else 1))
                for i, (leg, *_rest) in enumerate(EXPECTED)}
    assert outcomes["LF"] != outcomes["RF"]
    assert len(outcomes) == 6


def test_metric_is_frozen_and_has_no_result_dependent_inputs():
    prereg = bridge.verify_preregistration()
    metric = prereg["anatomical_metric"]
    assert metric["landmark"].startswith("origin of the named Femur")
    assert "Thorax local +X" in metric["anterior_axis"]
    assert "no alternative landmark" in metric["selection_policy"]
    forbidden = {"dir", "bodymap", "survey", "activity", "neural", "expected_sign", "symmetry"}
    # The classifier consumes only fixed geometric evidence, not forbidden biological inputs.
    classifier = ast.get_source_segment(Path(bridge.__file__).read_text(),
        next(node for node in ast.parse(Path(bridge.__file__).read_text()).body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "classify_leg"))
    assert not any(word in classifier.lower() for word in forbidden)


def test_adapter_contains_no_step_force_or_stimulation_path():
    source = (bridge.HERE / "_windows_coxa_yaw_anatomical_sign_bridge.py").read_text()
    tree = ast.parse(source)
    called_attributes = {node.func.attr for node in ast.walk(tree)
                         if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert "step" not in called_attributes
    assert "mj_step" not in source
    assert "xfrc_applied" not in source
    assert "stimulate" not in called_attributes
    assert "bodymap" not in source.lower()
    assert "motor_population_activity_survey" not in source
