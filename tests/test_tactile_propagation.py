import ast
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np

from malecns_backend.embodiment import tactile_propagation as propagation
from malecns_backend.embodiment import tactile_propagation_audit as audit
from malecns_backend.embodiment.tactile_contact import TactileContactConfig, TactileContactEncoder

ROOT = Path(__file__).parents[1]
LOCKED = {
    "malecns_backend/embodiment/tactile_contact.py": "10fb5edb8c9d59036a703d4ebe1bfac9c67e986f0d42d1ea412666f7404011f9",
    "malecns_backend/embodiment/tactile_contact_calibration.py": "1cab509fa2bd8f24638711cb974bf9a122d1199152f5c9c666a0933c54593b1c",
    "malecns_backend/embodiment/interface_output/tactile_contact_calibration.json": "a088f2923d7b752377fd48cf2a348b546eb32ddc0c23d8d6525056b4bf26420d",
}


def forces(value=0):
    result = np.zeros((36, 3)); result[propagation.CONTACT_FORCE_ROW, 0] = value
    return result


def test_complete_annotation_backed_population_has_exactly_378_members_without_subsampling():
    pop = propagation.tactile_population()
    assert pop.name == "tactile T2 left"
    assert len(pop.body_ids) == len(pop.dense_indices) == 378
    assert len(set(pop.body_ids)) == 378
    assert propagation.base_report()["population"]["subsampled"] is False


def test_physical_source_and_exact_pair_protocol_are_locked():
    report = propagation.base_report()["physical_contact_verification"]
    assert (report["leg"], report["segment"], report["contact_forces_row"]) == ("LM", "Tarsus5", 11)
    assert report["surface"] == "m5d2c_calibration_surface"
    assert report["penetration_model_units"] == 0.0001
    assert report["exact_unordered_geom_pair_required"] is True


def test_modeled_threshold_rate_and_duration_are_unchanged():
    config = TactileContactConfig()
    assert config.engineering_threshold == 1e-12
    assert config.maximum_modeled_rate_hz == 120
    assert config.transient_duration_ms == 20


def test_sustained_contact_does_not_retrigger_and_release_rearms():
    encoder = TactileContactEncoder(config=TactileContactConfig(seed=7))
    assert encoder.encode(forces(1), 0, .1)["LM"].onset_time_ms == 0
    assert encoder.encode(forces(1), 25, .1)["LM"].modeled_rate_hz == 0
    encoder.encode(forces(), 26, .1)
    rearmed = encoder.encode(forces(1), 27, .1)["LM"]
    assert rearmed.onset_time_ms == 27 and rearmed.modeled_rate_hz == 120


def test_common_random_numbers_and_disabled_encoder_rng_consumption_match():
    result = propagation.matched_encoder_candidates([forces(1)] * 10, np.arange(10) * .1,
                                                     dt_ms=.1, seed=19)
    assert result["parity"]
    assert len(result["rng_checkpoints"]) == 10


def test_disabled_arm_withholds_delivery_only_and_uses_external_drive_api():
    source = inspect.getsource(audit._run_neural)
    assert "encoder.encode" in source
    assert "set_external_drive" in source
    assert "external_drive_withheld_indices" in source
    assert "brain.v[" not in source and "brain.spike_counts[" not in source


def test_downstream_metric_excludes_every_directly_driven_neuron():
    result = propagation.downstream_indices(7, [1, 3, 5])
    np.testing.assert_array_equal(result, [0, 2, 4, 6])


def test_no_neural_motor_actuation_path_exists():
    tree = ast.parse(inspect.getsource(audit))
    calls = [ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert not any("decode" in call.lower() or "actuator" in call.lower() for call in calls)
    report = propagation.base_report()["mapped_motor_observational_summary"]
    assert report["motor_output_decoded"] is report["motor_output_applied"] is False


def test_physical_match_checks_qpos_force_pair_state_and_time():
    row = {"simulation_time_s": 0.0, "force_magnitude": .2,
           "selected_pair_present": True, "qpos": [1, 2]}
    assert propagation.physical_match([row], [dict(row)])["matched"]
    changed = dict(row, force_magnitude=.3)
    assert propagation.physical_match([row], [changed])["classification"] == "PHYSICAL_MATCH_FAILED"


def classify(**changes):
    values = dict(physical_contact=True, sensor_correspondence=True, candidate_count=1,
                  delivered_count=1, non_tactile_state_diverged=False,
                  non_tactile_spikes_diverged=False, mapped_motor_diverged=False)
    values.update(changes)
    return propagation.classify_causal(**values)


def test_p4_p5_p6_p7_classification_boundaries():
    assert classify() == "P4"
    assert classify(non_tactile_state_diverged=True) == "P5"
    assert classify(non_tactile_state_diverged=True, non_tactile_spikes_diverged=True) == "P6"
    assert classify(non_tactile_state_diverged=True, non_tactile_spikes_diverged=True,
                    mapped_motor_diverged=True) == "P7"
    assert classify(non_tactile_state_diverged=True, non_tactile_spikes_diverged=True,
                    mapped_motor_diverged=True,
                    mapped_motor_observation_valid=False) == "P6"


def _empty_analysis_inputs():
    condition = {"snapshots": [], "brain": type("Brain", (), {
        "spike_counts": np.zeros(200000, dtype=np.int64)})()}
    data = type("Data", (), {"row_ptr": np.zeros(200001, dtype=np.int64),
                              "target_indices": np.array([], dtype=np.int64),
                              "body_ids": np.arange(200000),
                              "types": np.array([""] * 200000)})()
    return condition, data


def test_authoritative_m4a_motor_inventory_excludes_ambiguous_broad_records():
    """Regression: the exact Windows-crashing duplicate is not role-inferred."""
    source = json.loads((ROOT / "malecns_backend/interface_map.json").read_text())
    antenna = [record for record in source["populations"]
               if record["name"] == "GNG133 antenna"]
    assert len(antenna) == 2 and antenna[0]["dense_indices"] != antenna[1]["dense_indices"]

    motors = propagation.motor_populations()
    assert "GNG133 antenna" not in motors
    authoritative = json.loads((ROOT / "malecns_backend/embodiment/six_leg_map.json").read_text())
    expected = {record["name"] for record in
                authoritative["population_inventory"]["leg_motor"]}
    assert set(motors) == expected
    assert len(motors) == 102
    condition, data = _empty_analysis_inputs()
    assert audit._analyze(condition, condition, data)["motor_observation"]["result"] == "AVAILABLE"

    source_text = inspect.getsource(propagation.motor_populations)
    assert "startswith" not in source_text and "endswith" not in source_text
    assert "population_inventory\"][\"leg_motor" in source_text


def test_motor_observer_failure_is_fail_closed_but_p6_remains_evaluable(monkeypatch):
    monkeypatch.setattr(audit, "motor_populations",
                        lambda: (_ for _ in ()).throw(OSError("missing authoritative map")))
    condition, data = _empty_analysis_inputs()
    result = audit._analyze(condition, condition, data)
    assert result["motor_observation"]["result"] == "ERROR"
    assert result["motor_diverged"] is False
    assert propagation.classify_causal(
        physical_contact=True, sensor_correspondence=True, candidate_count=1,
        delivered_count=1, non_tactile_state_diverged=True,
        non_tactile_spikes_diverged=True, mapped_motor_diverged=True,
        mapped_motor_observation_valid=False) == "P6"


def test_report_write_is_atomic(tmp_path, monkeypatch):
    output = tmp_path / "report.json"
    output.write_text("old complete report", encoding="utf-8")
    monkeypatch.setattr(audit.os, "replace",
                        lambda source, destination: (_ for _ in ()).throw(OSError("stop")))
    try:
        audit._write_report_atomic(output, propagation.base_report())
    except OSError:
        pass
    else:
        raise AssertionError("simulated replacement failure did not propagate")
    assert output.read_text(encoding="utf-8") == "old complete report"
    assert not list(tmp_path.glob("*.tmp"))


def test_deterministic_serialization_and_not_run_schema():
    a = propagation.serialized_report(propagation.base_report())
    b = propagation.serialized_report(propagation.base_report())
    assert a == b
    report = json.loads(a)
    assert report["run_status"] == report["causal_classification"] == "NOT_RUN"
    for key in ("protocol_configuration", "locked_provenance", "physical_contact_verification",
                "physical_match_verification", "rng_parity_checkpoints", "tactile_candidate_events",
                "tactile_delivered_events", "timing_milestones_ms", "enabled_neural_summary",
                "disabled_neural_summary", "non_tactile_cns_divergence_summary",
                "first_differing_neurons", "mapped_motor_observational_summary",
                "anatomical_context", "limitations"):
        assert key in report


def test_locked_artifact_hashes_unchanged():
    assert propagation.locked_hashes(ROOT) == LOCKED
    for name, digest in LOCKED.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
