"""Static/pure tests: these never construct FlyGym, MuJoCo, or MaleCNS."""
import ast
import json
from pathlib import Path

from malecns_backend.embodiment import m7c_initial_support as m


def _audit():
    return json.loads(m.AUDIT.read_text(encoding="utf-8"))


def test_preregistration_freezes_small_nonoptimized_candidate_set():
    report = m.build_preregistration(_audit())
    assert report["status"] == "FROZEN_BEFORE_EXECUTION"
    assert report["candidate_count"] == len(report["candidates"]) == 2
    assert report["schema"] == "M7C-B-PREREGISTRATION.2"
    assert report["correction_notice"]["schema"] == "M7C-B-PREREGISTRATION.1"
    assert report["candidate_c"] is None
    assert not report["arbitrary_height_sweep"] and not report["optimizer"]
    assert len(json.dumps(report)) < 20_000


def test_canonical_control_and_single_geometry_derivation():
    control, translated = m.candidates(_audit())
    assert control["root_position"] == [0.0, 0.0, 0.5]
    assert control["vertical_translation"] == 0.0
    assert translated["vertical_translation"] < 0
    assert "enclosing-radius support bound" in translated["derivation"]
    assert translated["differences_from_canonical"] == ["spawn_pos.z only"]


def test_geometry_derivation_uses_rotation_invariant_enclosing_radius():
    feet = m._foot_geometry(_audit())
    for foot in feet:
        expected = sum(x * x for x in foot["aabb_half_extents"]) ** .5
        assert foot["enclosing_radius"] == expected
        assert foot["conservative_lower_z"] == foot["center_world_xyz"][2] - expected
    # The obsolete max(size) method produced -1.4259575251353929.
    assert m.candidates(_audit())[1]["vertical_translation"] != -1.4259575251353929


def test_physics_only_contract_and_exact_cadence():
    report = m.build_preregistration(_audit())
    assert report["brain_constructed"] is False and report["neural_transitions"] == 0
    assert report["physics"] == {"timestep_s": .0001, "duration_ms": 100.0,
        "transitions": 1000, "checkpoint_13ms_transition": 130,
        "fall_height_lt": .25, "rollover_body_up_z_le": 0.0}
    controls = report["controls"]
    assert not any(controls[x] for x in ("gait_controller", "balance_controller",
                                         "reference_trajectory", "reward_rl_ai"))
    assert controls["adhesion_enabled"] is False
    assert controls["calibration_surface"] == "canonical world pose and dimensions, present and fixed"


def test_predicates_and_nonfinite_fail_closed():
    assert m.reconstruct(.249, 1) == {"fall": True, "rollover": False}
    assert m.reconstruct(.25, 0) == {"fall": False, "rollover": True}
    assert m.finite_state({"qpos": [0, 1], "qvel": [0]})
    assert not m.finite_state({"qpos": [float("nan")]})


def test_no_neural_or_assistance_imports():
    source = Path(m.__file__).read_text(encoding="utf-8")
    imports = {node.module for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)}
    assert not any(name and ("neural" in name or "malecns" in name) for name in imports)


def test_windows_modes_and_fail_closed_provenance_are_explicit():
    source = Path(m.__file__).read_text(encoding="utf-8")
    assert '"--windows-preflight"' in source and '"--run-windows"' in source
    assert "preregistration content/provenance mismatch" in source
    assert "range(1, TRANSITIONS + 1)" in source
