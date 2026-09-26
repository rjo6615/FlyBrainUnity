import json
from pathlib import Path

import numpy as np
import pytest

from malecns_backend.embodiment import motor_population_activity_survey as survey


def test_frozen_hash_gates_and_inventory_invariants(tmp_path):
    inventory = survey.load_inventory(); survey.verify_preregistration()
    assert survey.sha256(survey.INVENTORY_PATH) == survey.INVENTORY_SHA256
    assert survey.sha256(survey.PREREGISTRATION_PATH) == survey.PREREGISTRATION_SHA256
    populations = inventory["population_inventory"]
    assert len(populations) == 102
    assert sum(p["neuron_count"] for p in populations) == 328
    assert len({i for p in populations for i in p["neuron_ids"]}) == 328
    assert len(inventory["admitted_11_inventory"]) == 11
    assert all(all(isinstance(i, int) and i >= 0 for i in p["dense_neural_indices"])
               for p in populations)
    bad = tmp_path / "inventory.json"; bad.write_bytes(survey.INVENTORY_PATH.read_bytes() + b" ")
    with pytest.raises(RuntimeError, match="SHA-256"): survey.load_inventory(bad)
    bad = tmp_path / "prereg.json"; bad.write_bytes(survey.PREREGISTRATION_PATH.read_bytes() + b" ")
    with pytest.raises(RuntimeError, match="SHA-256"): survey.verify_preregistration(bad)


@pytest.mark.parametrize(
    ("source_path", "verifier"),
    ((survey.INVENTORY_PATH, survey.load_inventory),
     (survey.PREREGISTRATION_PATH, survey.verify_preregistration)),
)
def test_frozen_text_hash_accepts_lf_and_equivalent_crlf_but_rejects_mutation(
        tmp_path, source_path, verifier):
    canonical_lf = source_path.read_bytes()
    assert b"\r\n" not in canonical_lf

    lf_path = tmp_path / f"lf-{source_path.name}"
    lf_path.write_bytes(canonical_lf)
    verifier(lf_path)

    crlf_path = tmp_path / f"crlf-{source_path.name}"
    crlf_path.write_bytes(canonical_lf.replace(b"\n", b"\r\n"))
    verifier(crlf_path)
    assert survey.canonical_text_sha256(crlf_path) == survey.canonical_text_sha256(lf_path)

    mutated_path = tmp_path / f"mutated-{source_path.name}"
    mutated_path.write_bytes(canonical_lf.replace(b'"schema":', b'"mutated_schema":', 1))
    with pytest.raises(RuntimeError, match="SHA-256"):
        verifier(mutated_path)


def test_general_sha256_remains_raw_byte_identity(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"binary\x00payload\r\n")
    assert survey.sha256(artifact) == __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
    assert survey.sha256(artifact) != survey.canonical_text_sha256(artifact)


def test_attempt4_and_all_coxa_yaw_directions_are_included():
    inventory = survey.load_inventory(); populations = inventory["population_inventory"]
    assert len(inventory["attempt4_candidates"]) == 3
    assert all(any(joint in p["candidate_flygym_joints"] for p in populations)
               for joint in (x["joint"] for x in inventory["attempt4_candidates"]))
    coxa_names = {name for row in inventory["coxa_yaw_audit"] for name in row["annotation_names"]}
    found = [p for p in populations if p["canonical_name"] in coxa_names]
    assert len(found) == 12 and all(p["possible_coxa_yaw"] for p in found)
    assert all(p["coordinate_sign"] is None for p in found)


def _tiny_inventory():
    return {"population_inventory": [{"canonical_name": "p", "dense_neural_indices": [0, 2],
        "neuron_ids": [10, 12], "neuron_count": 2, "leg": "LF", "surveyability": "DIRECTLY_SURVEYABLE",
        "candidate_action_indices": [], "candidate_flygym_joints": [], "admitted_11": False,
        "attempt4_silent_candidate": False, "possible_coxa_yaw": False}]}


def test_observer_accounting_timing_binning_and_read_only(monkeypatch):
    monkeypatch.setattr(survey, "NEURAL_TRANSITIONS", 3)
    monkeypatch.setattr(survey, "DURATION_MS", 75)
    observer = survey.PopulationActivityObserver(_tiny_inventory())
    counts = np.array([5, 0, 8], dtype=np.uint32); observer.initialize(counts)
    action = np.arange(42, dtype=float); original = action.copy()
    observer.observe(time_ms=.5, spike_counts=np.array([6, 0, 8]), physical_action=action,
                     neural_transition_count=1, physics_transition_count=5)
    observer.observe(time_ms=25., spike_counts=np.array([6, 0, 10]), physical_action=action,
                     neural_transition_count=2, physics_transition_count=10)
    observer.observe(time_ms=50., spike_counts=np.array([6, 0, 10]), physical_action=action,
                     neural_transition_count=3, physics_transition_count=15)
    row = observer.finalize()["populations"][0]
    assert np.array_equal(action, original)
    assert row["total_spike_increments"] == 3
    assert row["active_member_neurons"] == 2 and row["active_member_neuron_fraction"] == 1
    assert row["mean_spike_increments_per_neuron"] == 1.5
    assert row["peak_spike_increments_member_neuron"] == 2
    assert row["first_activity_time_ms"] == .5 and row["last_activity_time_ms"] == 25.
    assert row["active_neural_transition_count"] == 2
    assert row["mean_per_neuron_filtered_rate_hz"] > 0 and row["peak_filtered_rate_hz"] > 0
    assert [b["total_spike_increments"] for b in row["bins"]] == [1, 2, 0]
    assert [b["active_member_neurons"] for b in row["bins"]] == [1, 1, 0]


def test_classification_rules():
    assert survey.classify(0, 1) == "OBSERVED_SILENT"
    assert survey.classify(1, .0099) == "OBSERVED_LOW_ACTIVITY"
    assert survey.classify(1, .01) == "OBSERVED_ACTIVE"


def test_frozen_design_and_deterministic_serialization():
    p = survey.verify_preregistration()
    assert (p["seed"], p["duration_ms"], p["neural_dt_ms"], p["physics_dt_ms"]) == (1, 1000, .5, .1)
    assert (p["expected_neural_transitions"], p["expected_physics_transitions"], p["bin_width_ms"]) == (2000, 10000, 25)
    assert survey.canonical_json(p) == survey.canonical_json(json.loads(survey.canonical_json(p)))


def test_output_overwrite_refusal(tmp_path, monkeypatch):
    paths = tuple(tmp_path / name for name in ("a", "b", "c", "d"))
    monkeypatch.setattr(survey, "RESULT_PATHS", paths); survey.assert_outputs_available()
    paths[2].write_text("exists")
    with pytest.raises(FileExistsError): survey.assert_outputs_available()


def test_no_candidate_action_leakage_gate():
    from malecns_backend.embodiment import _windows_motor_population_activity_survey_adapter as adapter
    admitted = tuple(f"joint{i}" for i in range(11)); values = {name: i for i, name in enumerate(admitted)}
    assert adapter._gate(values, adapter.CONDITION, admitted) == {k: float(v) for k, v in values.items()}
    with pytest.raises(RuntimeError): adapter._gate({**values, "candidate": 1}, adapter.CONDITION, admitted + ("candidate",))


def test_preflight_contract_has_zero_transitions(monkeypatch):
    from malecns_backend.embodiment import _windows_motor_population_activity_survey_adapter as adapter
    monkeypatch.setattr(survey, "assert_outputs_available", lambda: None)
    monkeypatch.setattr(adapter, "_invoke", lambda *a, **k: {"physics_steps": 0, "neural_steps": 0,
        "motor_interventions": 0, "admission_vector_length": 42})
    report = adapter.preflight()
    assert report["scientific_run_executed"] is False
    assert report["admitted_motor_channels"] == 11 and report["physical_action_entries"] == 42
