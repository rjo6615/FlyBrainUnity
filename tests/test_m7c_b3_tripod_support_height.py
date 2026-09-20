"""Pure analytic M7C-B3 tests: no FlyGym, MuJoCo, or simulation transitions."""
import ast
from pathlib import Path

import pytest

from malecns_backend.embodiment import m7c_b3_tripod_support_height as m


def geom(name, z):
    return {"name": f"1/{name}", "minimum_z": z}


def test_all_five_tarsal_segments_are_floor_support_geometry():
    assert len(m.ALLOWED_FLOOR_PARTS) == 30
    assert all(m.is_allowed_floor_geom(f"1/LFTarsus{i}") for i in range(1, 6))
    assert not m.is_allowed_floor_geom("1/LFTibia")


def test_exactly_one_minimum_boundary_dz_is_derived():
    result = m.solve_vertical_translation([
        geom("Thorax", .2), geom("LFTibia", -.02),
        geom("LFTarsus4", -.03), geom("RFTarsus5", -.10),
    ])
    assert result["classification"] == "TRIPOD_ANALYTIC_SUPPORT_HEIGHT_FOUND"
    assert result["forbidden_required_dz"] == pytest.approx(.019999)
    assert result["distal_penetration_required_dz"] == pytest.approx(.099)
    assert result["analytic_dz"] == pytest.approx(.099999)
    assert result["corrected_spawn_z"] == pytest.approx(.599999)


def test_infeasible_interval_fails_closed():
    result = m.solve_vertical_translation([geom("LFTibia", -.2), geom("LFTarsus5", -.1)])
    assert result["classification"] == "TRIPOD_SIMPLE_VERTICAL_TRANSLATION_INFEASIBLE"
    assert result["analytic_dz"] is None and result["feasible_dz_intervals"] == []


def test_no_step_brain_controller_sweep_or_optimizer():
    source = Path(m.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert not any(isinstance(n.func, ast.Attribute) and n.func.attr == "step" for n in calls)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.extend(item.name for item in node.names)
        if isinstance(node, ast.ImportFrom): imports.append(node.module or "")
    assert not any("malecns" in name.lower() or "neural" in name.lower() for name in imports)
    assert "height_sweep\": False" in source and "optimizer\": False" in source
    assert "adhesion_enabled\": False" in source and "controller\": False" in source
