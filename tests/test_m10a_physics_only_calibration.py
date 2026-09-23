"""M10A preregistration tests; no test constructs or advances physics."""
import ast
import inspect
import json

import pytest

from malecns_backend.embodiment import m10a_physics_only_calibration as m
from malecns_backend.embodiment import _windows_m10a_physics_only_adapter as live
from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d


def physical_row(magnitude, score, **changes):
    row = {"magnitude_native": magnitude, "finite": True,
        "catastrophic_through_750ms": False, "max_absolute_root_displacement_mm": 1.0,
        "max_absolute_tilt_deg": 40.0, "post_force_observation_ms": 980.0,
        "max_continuous_divergence": max(score * 0.005, 1e-9),
        "max_root_position_divergence_mm": score * 0.005,
        "max_orientation_divergence_deg": 0.0,
        "max_distal_tarsus_divergence_mm": 0.0,
        "contact_pattern_diverged": False, "peak_linear_velocity": 1.0,
        "peak_angular_velocity": 1.0,
        "post_perturbation_trajectory_deviation_mm": score * 0.004}
    row.update(changes)
    return row


def rows():
    return [physical_row(magnitude, 2.0 ** index)
        for index, magnitude in enumerate(m.CANDIDATE_FORCE_NATIVE)]


def test_preregistration_is_frozen_not_run_and_uses_m9_initialization():
    protocol = m.protocol()
    assert protocol == json.loads(m.PREREGISTRATION_PATH.read_text(encoding="utf-8"))
    assert protocol["status"] == "NOT_RUN" and not protocol["scientific_run_executed"]
    assert protocol["physical_initialization"] == m7d.protocol()["physical_initialization"]
    assert protocol["physical_initialization"]["spawn_pos"] == list(m7d.SPAWN_POS)
    assert protocol["initialization_identity"].endswith("used by canonical M9")


def test_geometry_interval_anchor_and_generated_candidate_order():
    perturbation = m.protocol()["perturbation"]
    assert tuple(perturbation["direction_xyz"]) == (0.0, 1.0, 0.0)
    assert perturbation["frame"] == "world"
    assert perturbation["application_body_source"] == "Thorax"
    assert perturbation["application_point"] == "authoritative body center of mass"
    assert (m.START_MS, m.STOP_MS, m.START_TRANSITION, m.STOP_TRANSITION) == (500.0, 520.0, 5000, 5200)
    assert m.ANCHOR_FORCE_NATIVE == 1.024 and m.CANDIDATE_FORCE_NATIVE[4] == 1.024
    assert all(left < right for left, right in zip(m.CANDIDATE_FORCE_NATIVE, m.CANDIDATE_FORCE_NATIVE[1:]))
    assert m.CANDIDATE_FORCE_NATIVE == tuple(1.024 * 2.0 ** (index / 2.0) for index in range(-4, 5))


def test_only_magnitude_varies_and_zero_control_is_matched():
    for magnitude in (m.CONTROL_FORCE_NATIVE, *m.CANDIDATE_FORCE_NATIVE):
        active = [index for index in range(m.TRANSITIONS)
            if m.force_at_transition(magnitude, index) != (0.0, 0.0, 0.0)]
        assert active == ([] if magnitude == 0.0 else list(range(5000, 5200)))
    conditions = m.protocol()["conditions"]
    assert conditions["zero_force_control"] == 0.0
    assert conditions["same_initialization_duration_geometry_and_fixed_actuation"]
    assert m.protocol()["perturbation"]["only_force_magnitude_varies"]


def test_absent_systems_are_fail_closed_and_contact_is_observation_only():
    absence = m.protocol()["execution_absence"]
    assert absence == {"male_cns_constructed": False, "neural_transitions": 0,
        "sensory_encoding_or_delivery_count": 0, "neural_motor_decode_or_application_count": 0,
        "controllers": False, "reward_or_rl": False, "gait_or_reference_controller": False,
        "contact_used_as_sensory_input": False}
    assert m.protocol()["contact_semantics"].startswith("physical observation only")
    tree = ast.parse(inspect.getsource(live))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names}
    assert not any(any(term in name.lower() for term in ("malecns", "sensory", "decoder", "controller", "reward"))
        for name in imported)
    assert "sim.step(" not in inspect.getsource(m.preflight)


def test_selection_accepts_only_registered_physical_metrics():
    # Index 2 and 6 have equal response-space separation; lower magnitude wins.
    expected = (m.CANDIDATE_FORCE_NATIVE[0], m.CANDIDATE_FORCE_NATIVE[2],
                m.CANDIDATE_FORCE_NATIVE[4], m.CANDIDATE_FORCE_NATIVE[-1])
    assert m.select_force_series(rows()) == expected
    assert m.select_force_series(rows()) == expected
    contaminated = rows()
    contaminated[0]["neural_activity"] = 1.0
    with pytest.raises(RuntimeError, match="nonphysical"):
        m.select_force_series(contaminated)


def test_integrity_gates_anchor_and_order_fail_closed():
    for key, value in (("finite", False), ("catastrophic_through_750ms", True),
                       ("max_absolute_root_displacement_mm", 1.500001),
                       ("max_absolute_tilt_deg", 60.000001),
                       ("post_force_observation_ms", 979.999)):
        values = rows()
        values[4][key] = value
        assert m.select_force_series(values) == m.ANCHOR_FAILURE
    with pytest.raises(RuntimeError, match="ordered preregistered ladder"):
        m.select_force_series(list(reversed(rows())))


def test_completed_namespace_is_frozen_and_preflight_implementation_is_zero_transition():
    before = set(m.OUTPUT_DIR.iterdir())
    after = set(m.OUTPUT_DIR.iterdir())
    completed = {m.PREREGISTRATION_PATH, live.RAW_PATH, m.MANIFEST_PATH, m.REPORT_PATH}
    assert before == after == completed
    source = inspect.getsource(m.preflight)
    assert "sim.step(" not in source and "brain.step(" not in source
    assert '"physics_transitions": 0' in source and '"neural_transitions": 0' in source


def test_m10_namespace_and_exclusive_future_artifacts_do_not_target_m9():
    assert m.OUTPUT_DIR.name == "m10a_physics_only_calibration"
    paths = (m.PREREGISTRATION_PATH, m.REPORT_PATH, m.MANIFEST_PATH, live.RAW_PATH)
    assert all("m10a" in str(path).lower() and "m9" not in path.name.lower() for path in paths)
    source = inspect.getsource(live)
    assert "os.O_EXCL" in source
    assert "m9a_" not in source and "m9b_" not in source and "m9c_" not in source and "m9d_" not in source
