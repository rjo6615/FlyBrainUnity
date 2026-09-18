import json
from pathlib import Path

import pytest

from malecns_backend.embodiment import tactile_motor_loop as loop
from malecns_backend.embodiment.tactile_contact import TactileContactConfig


def test_locked_tactile_and_contact_protocol():
    report = loop.base_report(verify_provenance=False)
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
    report = loop.base_report(verify_provenance=False)
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
    report = loop.base_report(verify_provenance=False)
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
    report = loop.base_report(verify_provenance=False); path = tmp_path / "result.json"
    loop.atomic_write_report(path, report); first = path.read_bytes()
    loop.atomic_write_report(path, report)
    assert path.read_bytes() == first
    assert json.loads(first) == report
    assert report["locked_provenance"]["m5d3_live_result_semantically_validated"] is False


def test_no_behavior_gait_reflex_or_parameter_tuning():
    report = loop.base_report(verify_provenance=False)
    limitations = " ".join(report["limitations"]).lower()
    assert all(word in limitations for word in ("gait", "behavior", "reflex"))
    assert report["physics_stability"]["retry_or_retuning_permitted"] is False
    assert TactileContactConfig().maximum_modeled_rate_hz == 120


def _authoritative_m5d3_result():
    result = {}
    for dotted, value in loop.M5D3_LIVE_RESULT.items():
        target = result
        parts = dotted.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    return result


def test_canonical_complete_p7_result_passes_semantic_validation():
    assert loop.validate_m5d3_live_result(_authoritative_m5d3_result()) == (
        loop.M5D3_LIVE_RESULT_SHA256)


def test_obsolete_checked_in_not_run_result_fails_semantic_validation():
    obsolete = json.loads(Path(
        "malecns_backend/embodiment/interface_output/tactile_propagation.json"
    ).read_text())
    assert obsolete["run_status"] == "NOT_RUN"
    with pytest.raises(RuntimeError, match="run_status"):
        loop.validate_m5d3_live_result(obsolete)


@pytest.mark.parametrize("field,bad_value", [
    ("protocol_configuration.seed", 2),
    ("enabled_neural_summary.delivered_tactile_spikes", 295),
    ("physical_match_verification.matched", False),
    ("mapped_motor_observational_summary.first_divergence_ms", 11.5),
])
def test_changed_scientific_field_fails_even_when_json_is_valid(field, bad_value):
    result = _authoritative_m5d3_result()
    target = result
    parts = field.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = bad_value
    json.dumps(result)  # It remains syntactically valid JSON.
    with pytest.raises(RuntimeError, match=field):
        loop.validate_m5d3_live_result(result)


def test_expected_hash_manifest_is_static_and_not_built_from_current_files():
    source = Path(loop.__file__).read_text()
    assert isinstance(loop.EXPECTED_LOCKED_HASHES, type(loop.M5D3_LIVE_RESULT))
    assert "M5D3_LIVE_RESULT_SHA256 = \"6f01c2" in source
    manifest_region = source[source.index("SOURCE_PROTOCOL_HASHES ="):source.index(
        "def _canonical_bytes")]
    assert "read_bytes" not in manifest_region
    assert "file_hashes(" not in manifest_region


def test_line_endings_are_not_mistaken_for_source_modification(tmp_path):
    name = next(iter(loop.SOURCE_PROTOCOL_HASHES))
    original = Path(name).read_bytes()
    target = tmp_path / name
    target.parent.mkdir(parents=True)
    target.write_bytes(original.replace(b"\n", b"\r\n"))
    assert loop.file_hashes((name,), tmp_path)[name] == loop.SOURCE_PROTOCOL_HASHES[name]


def test_unexplained_source_change_fails_closed(tmp_path):
    for name in loop.SOURCE_PROTOCOL_HASHES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Path(name).read_bytes())
    result_name = "malecns_backend/embodiment/interface_output/tactile_propagation.json"
    (tmp_path / result_name).write_text(json.dumps(_authoritative_m5d3_result()))
    changed = next(iter(loop.SOURCE_PROTOCOL_HASHES))
    with (tmp_path / changed).open("ab") as stream:
        stream.write(b"unexpected")
    with pytest.raises(RuntimeError, match="locked milestone artifacts changed"):
        loop.verify_locked_hashes(tmp_path)


def test_provenance_failure_precedes_protocol_or_scientific_setup(monkeypatch):
    def fail():
        raise RuntimeError("provenance rejected")
    monkeypatch.setattr(loop, "verify_locked_hashes", fail)
    monkeypatch.setattr(loop, "tactile_population",
                        lambda: pytest.fail("scientific setup started"))
    with pytest.raises(RuntimeError, match="provenance rejected"):
        loop.base_report()
