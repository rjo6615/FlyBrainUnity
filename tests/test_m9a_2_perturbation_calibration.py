"""Static and pure M9A-2 contract tests; no physics or neural transition runs."""
from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d
from malecns_backend.embodiment import m8_extended_spontaneous as m8
from malecns_backend.embodiment import m9a_2_perturbation_calibration as m9a
from malecns_backend.embodiment import _windows_m9a_2_perturbation_calibration_adapter as live
from malecns_backend.embodiment import m8_contact_kinematics as contacts


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT1_FROZEN = {
    "malecns_backend/embodiment/interface_output/m9a_perturbation_calibration/candidate_0.0001_raw.npz": "71b4c0150cb1296ffcffdab1bc600d725995f302cc1da25dd53fee88a701de41",
    "malecns_backend/embodiment/interface_output/m9a_perturbation_calibration/candidate_0.0002_raw.npz": "1bebe255c785ea6468a5e6bad2f4a86dca3575247ca0aecc9108942ad9b0a241",
    "malecns_backend/embodiment/interface_output/m9a_perturbation_calibration/candidate_0.0004_raw.npz": "f97e3d3f67dd70835592ab27458e237bc4b2ac331c61cee5ac12b8c602077075",
    "malecns_backend/embodiment/interface_output/m9a_perturbation_calibration/candidate_0.0008_raw.npz": "12bd71526456f844f66ac64fc58e84c7799a776432c1eec31b3aab763e4d45b7",
    "malecns_backend/embodiment/interface_output/m9a_perturbation_calibration/m9a_preregistration.json": "c597593129b6de859888023463f696dd5cc4c7cebba3ba07c25a0561252089fb",
}


FROZEN = {
    "malecns_backend/embodiment/interface_output/m7d_corrected_spontaneous/m7d_manifest.json": "6c788951eee438a5969588a768b6b227e48dc1f64dc2f686f56203a052a8d6f2",
    "malecns_backend/embodiment/interface_output/m7d_corrected_spontaneous/m7d_summary.json": "981d02fa12629bcd3639b8fcc07493800848f9b7a587ef195c4f04d1aa691661",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/M8_POSTRUN_REPORT.md": "41f5b0181e740c01eae7df3f52daf0400ef63b9d89a4ea4a5ff7a6f082ac7dc1",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_analysis.json": "5ed3e0c7003b95b987cc2b81c1d4d565a1cc9f274e881597988bfbd8a3836884",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_disabled_replay.bin": "04e1b878454583bfbd5146db3f6c9e62546ceeb7bbc360e41f99733626adbd16",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_enabled_replay.bin": "b9febf230f23cc6d9943819904876a729c283ccb050b6d16d2760a7a08ff38f8",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_manifest.json": "b57ffb147daed37c6cf447005f8b687d78d2018ee511146cca0941d43a79a2ff",
    "malecns_backend/embodiment/interface_output/m8_extended_spontaneous/m8_replay_manifest.json": "c745d018e91b737b82bfd17a1acdd7e9706d3c8efb5f355fb8da0db02c5ce26e",
}



def test_m9a_attempt_1_artifacts_are_byte_identical():
    attempt1_dir = "malecns_backend/embodiment/interface_output/m9a_perturbation_calibration/"
    assert {name: m9a.attempt1_sha256(name.removeprefix(attempt1_dir))
            for name in ATTEMPT1_FROZEN} == ATTEMPT1_FROZEN
    assert m9a.ATTEMPT1_FROZEN_SHA256 == {
        name.removeprefix(attempt1_dir): digest
        for name, digest in ATTEMPT1_FROZEN.items()}


def test_new_namespace_and_logarithmic_candidates_are_frozen_before_execution():
    value = m9a.protocol()
    assert value["experiment_namespace"] == "M9A-2"
    assert m9a.OUTPUT_DIR.name == "m9a_2_perturbation_calibration"
    assert m9a.CANDIDATE_FORCE_NATIVE == (0.002, 0.008, 0.032, 0.128)
    assert all(b / a == 4 for a, b in zip(m9a.CANDIDATE_FORCE_NATIVE, m9a.CANDIDATE_FORCE_NATIVE[1:]))
    assert value["status"] == "NOT_RUN"
    frozen = __import__("json").loads((m9a.OUTPUT_DIR / "m9a_2_preregistration.json").read_text())
    assert frozen["perturbation"] == value["perturbation"]
    assert frozen["selection_rule_preregistered"] == value["selection_rule_preregistered"]


def test_m9b_has_no_execution_route():
    source = inspect.getsource(m9a.main)
    assert source.count("modes.add_argument") == 2
    assert "--windows-preflight" in source and "--run-windows" in source
    with pytest.raises(SystemExit):
        m9a.main(["--run-m9b"])

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
    values = [m9a.force_at(i * m9a.DT_MS, 0.032) for i in range(m9a.TRANSITIONS)]
    active = [i for i, force in enumerate(values) if force != (0.0, 0.0, 0.0)]
    assert active == list(range(5000, 5200))
    assert all(values[i] == (0.0, 0.032, 0.0) for i in active)
    assert values[4999] == values[5200] == values[-1] == (0.0, 0.0, 0.0)


def test_force_target_fails_closed_and_xfrc_targets_one_body_only():
    source = inspect.getsource(live)
    assert 'if name == m9a.APPLICATION_BODY_EXACT' in source
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


def test_m9a_2_identity_resolution_uses_dm_control_compiled_model_api(monkeypatch):
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
    model._bodies = ("world", "0/Thorax", *model._bodies[2:])
    body = live._body_identity(model)
    identity = contacts.resolve(model)
    assert body["body_id"] == 1 and body["body_name"] == "0/Thorax"
    assert identity["available"]
    assert identity["ground_geom_ids"] == (0,)
    assert identity["tarsus5_body_ids"] == {
        "LF": 2, "LM": 3, "LH": 4, "RF": 5, "RM": 6, "RH": 7}


def test_m9a_2_thorax_identity_requires_exact_authoritative_compiled_name():
    model = _CompiledModel()
    model._bodies = ("world", "0/Thorax", *model._bodies[2:])
    assert live._body_identity(model) == {
        "body_id": 1, "body_name": "0/Thorax",
        "resolution": "exact compiled MuJoCo body name",
        "all_body_names": {i: name for i, name in enumerate(model._bodies)}}
    model._bodies = ("world", "Thorax", *model._bodies[2:])
    with pytest.raises(RuntimeError, match="zero authoritative Thorax matches"):
        live._body_identity(model)


@pytest.mark.parametrize("deceptive", ["FakeThorax", "ThoraxExtra", "0/FakeThorax", "0/ThoraxExtra"])
def test_m9a_2_thorax_identity_rejects_deceptive_substrings(deceptive):
    model = _CompiledModel()
    model._bodies = ("world", deceptive, *model._bodies[2:])
    with pytest.raises(RuntimeError, match="zero authoritative Thorax matches"):
        live._body_identity(model)


def test_m9a_2_thorax_identity_ignores_other_namespaces_but_rejects_duplicate_exact_names():
    model = _CompiledModel()
    model._bodies = ("world", "0/Thorax", "1/Thorax", "LMTarsus5", "LHTarsus5",
                     "RFTarsus5", "RMTarsus5", "RHTarsus5")
    assert live._body_identity(model)["body_id"] == 1
    model._bodies = ("world", "0/Thorax", "0/Thorax", *model._bodies[3:])
    with pytest.raises(RuntimeError, match="multiple/ambiguous authoritative Thorax matches"):
        live._body_identity(model)


def test_m9a_2_thorax_identity_rejects_no_match_and_world_body():
    model = _CompiledModel()
    model._bodies = ("world", "Head", *model._bodies[2:])
    with pytest.raises(RuntimeError, match="zero authoritative Thorax matches"):
        live._body_identity(model)
    model._bodies = ("0/Thorax", "Head", *model._bodies[2:])
    with pytest.raises(RuntimeError, match="Thorax match resolves to the MuJoCo world body"):
        live._body_identity(model)


def test_authoritative_contact_identity_still_fails_closed():
    model = _CompiledModel()
    model._geoms = ("other",) * model.ngeom
    assert contacts.resolve(model)["available"] is False


def test_authoritative_contact_identity_is_namespace_exact_and_ambiguous_safe():
    model = _CompiledModel()
    model._bodies = tuple("0/" + name if name != "world" else name for name in model._bodies)
    model._geoms = ("arena/ground", *model._geoms[1:])
    assert contacts.resolve(model)["available"] is True
    model._bodies = tuple(name.replace("LFTarsus5", "LFFakeTarsus5") for name in model._bodies)
    assert contacts.resolve(model)["available"] is False
    model._bodies = (*model._bodies, "1/LFTarsus5")
    model.nbody = 9
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
