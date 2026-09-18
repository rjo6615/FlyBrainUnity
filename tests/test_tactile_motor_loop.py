import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import tactile_motor_loop as loop
from malecns_backend.embodiment.tactile_contact import TactileContactConfig


def test_locked_tactile_and_contact_protocol():
    report = loop.base_report()
    population = report["biological_tactile_population"]
    physical = report["physical_contact_verification"]
    encoder = report["tactile_encoder_parameters"]
    assert (population["name"], population["size"], population["subsampled"]) == (
        "tactile T2 left", 378, False)
    assert physical == {"leg": "LM", "segment": "Tarsus5", "contact_forces_row": 11,
        "surface": "m5d2c_calibration_surface", "penetration_model_units": .0001,
        "threshold": 1e-12, "exact_unordered_geom_pair_required": True, "verified": None}
    assert encoder == {"maximum_modeled_rate_hz": 120.0, "transient_duration_ms": 20.0,
        "envelope": "linear decay", "sustained_contact_retrigger": False, "release_rearms": True}


def test_six_and_only_six_locked_tibia_targets_and_existing_decoder():
    report = loop.base_report()
    assert report["actuator_indices"] == {"LF": 5, "LM": 12, "LH": 19,
                                           "RF": 26, "RM": 33, "RH": 40}
    targets = report["physical_neural_actuation_targets"]
    assert len(targets) == 6
    assert {x["joint"] for x in targets} == {"Tibia"}
    assert report["excluded_actuation_joints"] == [
        "coxa", "coxa_roll", "coxa_yaw", "femur", "femur_roll", "tarsus1"]
    assert report["motor_mapping_provenance"]["new_assignments_inferred"] is False
    assert report["decoder_parameters"]["implementation"].startswith("six_tibia.IsolatedMotorDecoder")


def test_matched_design_computes_both_and_withholds_application_only():
    report = loop.base_report()
    assert report["protocol_configuration"]["conditions"] == list(loop.CONDITIONS)
    assert report["protocol_configuration"]["only_intended_difference"] == (
        "decoded tibia contribution applied to physical actuators")
    source = Path("malecns_backend/embodiment/tactile_motor_loop_audit.py").read_text()
    assert "brain.set_external_drive(candidates" in source
    assert "apply_neural_offset=apply_motor" in source
    assert "if apply_motor else measured" in source
    assert "external_drive_withheld_indices = np.empty" in source


def _row(time, *, applied=0.0, q=0.0, force=1.0, contact=True,
         rate=120.0, candidate=(), delivered=(), state="same", spike=(), motor=0):
    tibia = {leg: (q if leg == "LM" else 0.0) for leg in loop.LEG_ORDER}
    values = {leg: 0 for leg in loop.LEG_ORDER}; values["LM"] = motor
    outputs = {leg: 0.0 for leg in loop.LEG_ORDER}
    outputs["LM"] = applied
    return {"time_ms": time, "tibia_qpos": tibia, "full_qpos": (q, 0.0),
      "force_magnitude": force, "contact_metadata": {"selected_pair_present": contact},
      "modeled_rate_hz": rate, "candidate_events": candidate, "delivered_events": delivered,
      "cns_spikes": spike, "neural_state": state, "motor_spikes": values,
      "decoder_state": {leg: 0.0 for leg in loop.LEG_ORDER},
      "decoded_output": outputs, "applied_output": outputs}


def test_pre_motor_equivalence_and_feedback_order():
    enabled = [_row(0), _row(1, applied=.01, motor=1),
      _row(2, applied=.01, q=.001, motor=1),
      _row(3, applied=.01, q=.002, force=2.0, rate=60.0, candidate=(4,),
           delivered=(4,), state="feedback", spike=(9,), motor=2)]
    disabled = [_row(0), _row(1, motor=1), _row(2, motor=1),
                _row(3, candidate=(), delivered=(), motor=1)]
    result = loop.analyze(enabled, disabled)
    assert result["pre_motor_equivalence"]["passed"] is True
    times = result["timing_milestones_ms"]
    assert times["first_applied_neural_output"] == 1
    assert times["first_physical_qpos_divergence"] == 2
    assert times["first_lm_tarsus5_force_divergence"] == 3
    assert times["first_sensory_feedback_divergence"] == 3
    assert times["first_subsequent_cns_divergence"] == 3
    assert times["first_subsequent_mapped_motor_divergence"] == 3


@pytest.mark.parametrize("stage,flags", [
    ("C4", dict(contact=True,tactile_delivered=True,downstream=True,motor_spike=True,decoded=True,physical=False,contact_feedback=False,tactile_and_cns_feedback=False,motor_feedback=False)),
    ("C5", dict(contact=True,tactile_delivered=True,downstream=True,motor_spike=True,decoded=True,physical=True,contact_feedback=False,tactile_and_cns_feedback=False,motor_feedback=False)),
    ("C6", dict(contact=True,tactile_delivered=True,downstream=True,motor_spike=True,decoded=True,physical=True,contact_feedback=True,tactile_and_cns_feedback=False,motor_feedback=False)),
    ("C7", dict(contact=True,tactile_delivered=True,downstream=True,motor_spike=True,decoded=True,physical=True,contact_feedback=True,tactile_and_cns_feedback=True,motor_feedback=False)),
    ("C8", dict(contact=True,tactile_delivered=True,downstream=True,motor_spike=True,decoded=True,physical=True,contact_feedback=True,tactile_and_cns_feedback=True,motor_feedback=True)),
])
def test_causal_boundaries(stage, flags):
    assert loop.classify(**flags) == stage


def test_pre_motor_failure_and_physics_failure_override_claims():
    flags = dict(contact=True,tactile_delivered=True,downstream=True,motor_spike=True,
      decoded=True,physical=True,contact_feedback=True,tactile_and_cns_feedback=True,motor_feedback=True)
    assert loop.classify(**flags, pre_motor_equivalent=False) == "PRE_MOTOR_EQUIVALENCE_FAILED"
    assert loop.classify(**flags, physics_stable=False) == "PHYSICS_UNSTABLE"


def test_deterministic_atomic_report_and_locked_hashes(tmp_path):
    report = loop.base_report(); path = tmp_path / "result.json"
    loop.atomic_write_report(path, report); first = path.read_bytes()
    loop.atomic_write_report(path, report)
    assert path.read_bytes() == first
    assert json.loads(first) == report
    assert loop.verify_locked_hashes() == loop.EXPECTED_LOCKED_HASHES


def test_no_behavior_gait_reflex_or_parameter_tuning():
    report = loop.base_report()
    limitations = " ".join(report["limitations"]).lower()
    assert all(word in limitations for word in ("gait", "behavior", "reflex"))
    assert report["physics_stability"]["retry_or_retuning_permitted"] is False
    assert TactileContactConfig().maximum_modeled_rate_hz == 120
