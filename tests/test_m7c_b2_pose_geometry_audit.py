"""Pure M7C-B2 protocol/gate tests; no FlyGym, MuJoCo, or brain is imported."""
import ast
import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import m7c_b2_pose_geometry_audit as m


def contact(other, distance=-0.01, surface="ground"):
    return {"geom1": surface, "geom2": f"0/{other}", "distance": distance,
            "penetration_depth": max(0, -distance), "position": [0, 0, distance / 2]}


def gate(rows=(), finite=True):
    return m.geometry_gate(rows, state_finite=finite, calibration_surface_unchanged=True)


def test_named_static_pose_set_and_no_spawn_sweep():
    assert [x["init_pose"] for x in m.POSES] == ["stretch", "tripod", "zero"]
    assert m.POSES[0]["spawn_pos"] == [0.0, 0.0, 0.5]
    assert m.POSES[1]["spawn_pos"] is None and m.POSES[2]["spawn_pos"] is None
    report = json.loads(m.OUTPUT.read_text(encoding="utf-8"))
    protocol = report["protocol"]
    assert not protocol["height_sweep"] and not protocol["optimizer"]
    assert not protocol["adaptive_candidate_generation"]


def test_step_is_structurally_forbidden():
    with pytest.raises(RuntimeError, match=r"sim\.step\(\) is forbidden"):
        m.StepForbidden(object()).step({})


def test_proximal_and_body_penetration_fail_closed():
    proximal = gate([contact("LFCoxa")])
    assert not proximal["valid"]
    assert proximal["classifications"]["PROXIMAL_LEG_GROUND_PENETRATION"]
    body = gate([contact("Thorax")])
    assert not body["valid"]
    assert body["classifications"]["BODY_GROUND_PENETRATION"]


def test_no_support_is_distinct_from_penetration():
    result = gate([])
    assert result["classifications"]["NO_SUPPORT_CONTACT"]
    assert not result["classifications"]["BODY_GROUND_PENETRATION"]
    assert not result["classifications"]["PROXIMAL_LEG_GROUND_PENETRATION"]


def test_distal_contact_is_separate_and_tolerance_is_explicit():
    acceptable = gate([contact("LFTarsus5", -m.DISTAL_PENETRATION_TOLERANCE)])
    assert acceptable["valid"] and acceptable["classifications"]["VALID_SUPPORT_CONTACT"]
    assert not acceptable["classifications"]["EXCESSIVE_DISTAL_PENETRATION"]
    excessive = gate([contact("LFTarsus5", -m.DISTAL_PENETRATION_TOLERANCE * 2)])
    assert not excessive["valid"]
    assert excessive["classifications"]["EXCESSIVE_DISTAL_PENETRATION"]


def test_self_calibration_and_mixed_surfaces_reported_separately():
    rows = [contact("LFTarsus5", 0), contact("RFTarsus5", 0, m.SURFACE_NAME),
            {"geom1": "0/LHCoxa", "geom2": "0/RHCoxa", "distance": -0.02}]
    result = gate(rows)
    labels = result["classifications"]
    assert labels["SELF_COLLISION_PRESENT"] and labels["CALIBRATION_SURFACE_CONTACT"]
    assert labels["MIXED_SUPPORT_SURFACES"] and not result["valid"]


def test_nonfinite_state_fails_closed():
    assert not m.finite({"qpos": [0, float("nan")]})
    result = gate([contact("LFTarsus5", 0)], finite=False)
    assert result["classifications"]["VALID_SUPPORT_CONTACT"]
    assert not result["valid"]


def test_single_analytic_translation_or_incompatibility():
    good = m.derive_vertical_translation([
        {"name": "0/LFTarsus5", "minimum_z": .2}, {"name": "0/Thorax", "minimum_z": .8}])
    assert good["status"] == "ANALYTIC_CANDIDATE"
    assert good["translation_z"] == -.2
    assert good["resulting_non_distal_minimum_z"] == pytest.approx(.6)
    assert good["derivation"] == "negative of the minimum actual Tarsus5 mesh-vertex height"
    bad = m.derive_vertical_translation([
        {"name": "0/LFTarsus5", "minimum_z": .4}, {"name": "0/LFCoxa", "minimum_z": .1}])
    assert bad["status"] == "GEOMETRICALLY_INCOMPATIBLE_WITH_SIMPLE_VERTICAL_TRANSLATION"


def test_no_brain_or_controller_import_and_zero_transition_contract():
    tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imported.extend(x.name for x in node.names)
        if isinstance(node, ast.ImportFrom): imported.append(node.module or "")
    assert not any("malecns" in x or "neural" in x for x in imported)
    report = json.loads(m.OUTPUT.read_text(encoding="utf-8"))
    p = report["protocol"]
    assert p["brain_constructed"] is False
    assert p["neural_transitions"] == p["physics_transitions"] == 0
    assert p["sim_step_prohibited"] is True and p["adhesion_enabled"] is False
    assert p["calibration_surface_changed"] is False
    assert not any(p[x] for x in ("gait_controller", "balance_controller",
                                  "walking_reference_trajectory", "reward_rl_ai"))
