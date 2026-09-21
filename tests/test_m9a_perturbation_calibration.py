"""Static and pure M9A contract tests; no physics or neural transition runs."""
from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d
from malecns_backend.embodiment import m8_extended_spontaneous as m8
from malecns_backend.embodiment import m9a_perturbation_calibration as m9a
from malecns_backend.embodiment import _windows_m9a_perturbation_calibration_adapter as live
from malecns_backend.embodiment import m8_contact_kinematics as contacts


ROOT = Path(__file__).resolve().parents[1]
FROZEN = {
    "malecns_backend/embodiment/interface_output/m7d_corrected_spontaneous/m7d_manifest.json": "6c788951eee438a5969588a768b6b227e48dc1f64dc2f686f56203a052a8d6f2",
    "malecns_backend/embodiment/interface_output/m7d_corrected_spontaneous/m7d_summary.json": "981d02fa12629bcd3639b8fcc07493800848f9b7a587ef195c4f04d1aa691661",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/M8_POSTRUN_REPORT.md": "41f5b0181e740c01eae7df3f52daf0400ef63b9d89a4ea4a5ff7a6f082ac7dc1",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_analysis.json": "5ed3e0c7003b95b987cc2b81c1d4d565a1cc9f274e881597988bfbd8a3836884",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_disabled_replay.bin": "29569c8b8612acda0cd5b12471a00ba80599b7e6c7b5e77ea4e200ea47dfd843",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_enabled_replay.bin": "56a19ef572338e454febe4249578a54787e697bba87a2a4a4f7a11976e69b558",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_manifest.json": "b57ffb147daed37c6cf447005f8b687d78d2018ee511146cca0941d43a79a2ff",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_replay_manifest.json": "c745d018e91b737b82bfd17a1acdd7e9706d3c8efb5f355fb8da0db02c5ce26e",
}


def test_frozen_m7d_m8_artifacts_are_byte_identical():
    assert {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in FROZEN} == FROZEN


def test_exact_corrected_initialization_and_inventory_are_inherited():
    value = m9a.protocol()
    assert value["physical_initialization"] == m7d.protocol()["physical_initialization"]
    assert value["physical_initialization"] == m8.protocol()["physical_initialization"]
    assert tuple(value["embodiment_inventory_retained_but_inactive"]["sensory_interfaces"]) == m7d.ADMITTED_SENSORY
    assert tuple(value["embodiment_inventory_retained_but_inactive"]["motor_interfaces"]) == m7d.ADMITTED_MOTOR
    assert value["embodiment_inventory_retained_but_inactive"]["baseline_only_actuator_count"] == 31
    m9a.validate_protocol(value)


def test_malecns_is_never_imported_constructed_or_advanced():
    source = inspect.getsource(live)
    assert "from malecns_backend import" not in source
    assert "MaleCNSBrain" not in source
    assert m9a.protocol()["male_cns"] == {"constructed": False, "advanced": False, "neural_transitions": 0}


def test_force_schedule_is_half_open_and_has_exactly_200_transitions():
    values = [m9a.force_at(i * m9a.DT_MS, 0.0004) for i in range(m9a.TRANSITIONS)]
    active = [i for i, force in enumerate(values) if force != (0.0, 0.0, 0.0)]
    assert active == list(range(5000, 5200))
    assert all(values[i] == (0.0, 0.0004, 0.0) for i in active)
    assert values[4999] == values[5200] == values[-1] == (0.0, 0.0, 0.0)


def test_force_target_fails_closed_and_xfrc_targets_one_body_only():
    source = inspect.getsource(live)
    assert 'name == m9a.APPLICATION_BODY_EXACT' in source
    assert 'len(matches) != 1 or matches[0] == 0' in source
    assert 'physics.data.xfrc_applied[:] = 0.0' in source
    assert 'physics.data.xfrc_applied[body["body_id"], :3] = force' in source
    assert 'nonzero.tolist() != [body["body_id"]]' in source


class _CompiledModel:
    nbody = 8
    ngeom = 8
    geom_bodyid = [0, 2, 3, 4, 5, 6, 7, 1]
    _bodies = ("world", "Thorax", "LFTarsus5", "LMTarsus5", "LHTarsus5",
               "RFTarsus5", "RMTarsus5", "RHTarsus5")
    _geoms = ("ground", "LFTarsus", "LMTarsus", "LHTarsus", "RFTarsus",
              "RMTarsus", "RHTarsus", "other")

    def id2name(self, object_id, kind):
        return {"body": self._bodies, "geom": self._geoms}[kind][object_id]


def test_m9a_identity_resolution_uses_dm_control_compiled_model_api(monkeypatch):
    """Regression: never pass a dm_control MjModel to native mj_id2name."""
    class NativeMuJoCo:
        class mjtObj:
            mjOBJ_BODY = object()
            mjOBJ_GEOM = object()

        @staticmethod
        def mj_id2name(*_args):
            raise AssertionError("native mj_id2name received the dm_control wrapper")

    monkeypatch.setitem(__import__("sys").modules, "mujoco", NativeMuJoCo)
    model = _CompiledModel()
    body = live._body_identity(model)
    identity = contacts.resolve(model)
    assert body["body_id"] == 1 and body["body_name"] == "Thorax"
    assert identity["available"]
    assert identity["ground_geom_ids"] == (0,)
    assert identity["tarsus5_body_ids"] == {
        "LF": 2, "LM": 3, "LH": 4, "RF": 5, "RM": 6, "RH": 7}


def test_m9a_thorax_identity_still_fails_closed():
    model = _CompiledModel()
    model._bodies = ("world", "Thorax", "Thorax", "LMTarsus5", "LHTarsus5",
                     "RFTarsus5", "RMTarsus5", "RHTarsus5")
    with pytest.raises(RuntimeError, match="Thorax body identity is not unique"):
        live._body_identity(model)


def test_authoritative_contact_identity_still_fails_closed():
    model = _CompiledModel()
    model._geoms = ("other",) * model.ngeom
    assert contacts.resolve(model)["available"] is False


def test_no_controller_assistance_is_introduced():
    value = m9a.protocol()
    assert not any(value["controls_absent"].values())
    assert not any(value["explicit_absences"].values())
    source = inspect.getsource(live)
    assert '"adhesion": np.zeros(6)' in source
    assert "baseline.copy()" in source


def _candidate(magnitude, **changes):
    row = {"magnitude_native": magnitude, "finite": True,
        "fall_or_rollover_by_600ms": False, "maximum_root_displacement_mm": 0.1,
        "maximum_tilt_deg": 6.0, "authoritative_contact_pattern_changed": True,
        "post_force_displacement_reduction_fraction": 0.3,
        "post_force_tilt_reduction_fraction": 0.1}
    row.update(changes); return row


def test_selection_is_ordered_and_uses_only_preregistered_physics_metrics():
    rows = [_candidate(x) for x in m9a.CANDIDATE_FORCE_NATIVE]
    rows[0]["authoritative_contact_pattern_changed"] = False
    assert m9a.choose_candidate(rows) == m9a.CANDIDATE_FORCE_NATIVE[1]
    assert set(m9a.protocol()["selection_rule_preregistered"]["inputs"]) == {
        "finite", "fall_or_rollover", "maximum_root_displacement_mm", "maximum_tilt_deg",
        "authoritative_contact_pattern_changed", "post_force_displacement_reduction_fraction",
        "post_force_tilt_reduction_fraction"}
    with pytest.raises(RuntimeError, match="no preregistered candidate"):
        m9a.choose_candidate([_candidate(x, finite=False) for x in m9a.CANDIDATE_FORCE_NATIVE])
