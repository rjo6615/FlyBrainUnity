import hashlib
import json

import pytest

from malecns_backend.embodiment import sensory_feedback_boundary as boundary
from malecns_backend.embodiment import sensory_feedback_boundary_audit as audit


def test_m5d4d_raw_artifact_and_sources_are_immutable_and_semantically_valid():
    result = boundary.verify_provenance()
    assert result["verified"] and result["earlier_locks_verified"]
    artifact = json.loads(boundary.M5D4D_ARTIFACT.read_text())
    assert artifact["classification"] == "MOTOR_CAUSALITY_CONFIRMED_NO_FEEDBACK_WITHIN_WINDOW"
    assert artifact["m5d4c_prefix_validation"]["passed"]


def test_provenance_fails_closed(tmp_path, monkeypatch):
    changed = tmp_path / "changed.json"; changed.write_text("{}")
    monkeypatch.setattr(boundary, "M5D4D_ARTIFACT", changed)
    with pytest.raises(RuntimeError, match="provenance mismatch"):
        boundary.verify_provenance()


def test_inventory_is_exactly_the_drive_used_by_m5d4d():
    inventory = boundary.active_channel_inventory()
    assert len(inventory) == 1
    assert inventory[0]["channel_name"] == "LM_Tarsus5_tactile"
    assert inventory[0]["physical_source_indices"] == [11, [0, 1, 2]]
    inactive = boundary.available_but_inactive_proprioception()
    assert [x["leg"] for x in inactive] == list(boundary.LEG_ORDER)
    assert all(not x["active_external_drive_in_m5d4d"] for x in inactive)
    assert [x["observation_action_index"] for x in inactive] == [5, 12, 19, 26, 33, 40]


def test_global_force_row_is_not_tactile_source():
    report = boundary.base_report()
    assert report["active_sensory_channels"][0]["physical_source_indices"][0] == 11
    artifact = json.loads(boundary.M5D4D_ARTIFACT.read_text())
    assert artifact["physical_sensory_divergence"]["contact_force"]["first_differing_index"] == "[24][0]"


@pytest.mark.parametrize(("evidence", "expected"), [
    ({}, "PROVENANCE_FAILURE"),
    ({"provenance": True}, "PREFIX_REPRODUCTION_FAILURE"),
    ({"provenance": True, "prefix": True}, "RNG_PARITY_FAILURE"),
    ({"provenance": True, "prefix": True, "rng_parity": True}, "NO_SENSOR_RELEVANT_PHYSICAL_DIVERGENCE"),
    ({"provenance": True, "prefix": True, "rng_parity": True, "sensor_source": True}, "SENSOR_SOURCE_DIVERGED_ENCODER_INSENSITIVE"),
    ({"provenance": True, "prefix": True, "rng_parity": True, "rate": True}, "ENCODING_DIVERGED_NO_SPIKE_DIVERGENCE"),
    ({"provenance": True, "prefix": True, "rng_parity": True, "delivered": True}, "SENSORY_SPIKES_DIVERGED_NO_CNS_EFFECT"),
    ({"provenance": True, "prefix": True, "rng_parity": True, "delivered": True, "cns": True}, "FEEDBACK_REACHED_CNS_NOT_MOTOR"),
    ({"provenance": True, "prefix": True, "rng_parity": True, "delivered": True, "cns": True, "motor": True}, "FEEDBACK_REACHED_MAPPED_MOTOR"),
    ({"provenance": True, "prefix": True, "rng_parity": True, "telemetry_blind_spot": True}, "M5D4D_TELEMETRY_BLIND_SPOT"),
])
def test_classification_is_evidence_ordered(evidence, expected):
    assert boundary.classify(evidence) == expected


def test_protocol_nulls_and_no_tuning_are_locked():
    report = boundary.base_report()
    assert report["protocol"] == {"seed": 1, "duration_ms": 100.0,
        "physics_timestep_ms": .1, "neural_timestep_ms": .5,
        "automatic_retries": 0, "parameter_mutations": []}
    stages = report["channels"]["LM_Tarsus5_tactile"]
    assert all(value is None for value in stages.values())


def test_live_rejects_scientific_protocol_mutation():
    with pytest.raises(ValueError): audit.run_live(100.1, 1)
    with pytest.raises(ValueError): audit.run_live(100.0, 2)


def test_not_run_artifact_is_truthful_compact_and_deterministic():
    artifact = json.loads(audit.DEFAULT_OUTPUT.read_text())
    assert artifact["run_status"] == "NOT_RUN" and artifact["classification"] is None
    assert artifact["runner"]["exact_m5d4d_runner_reused"]
    assert audit.DEFAULT_OUTPUT.stat().st_size < 30000
    serialize = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
    assert serialize(boundary.base_report()) == serialize(boundary.base_report())


def test_rng_desynchronization_always_fails_closed():
    evidence = {"provenance": True, "prefix": True, "rng_parity": False,
        "sensor_source": True, "rate": True, "delivered": True, "cns": True, "motor": True}
    assert boundary.classify(evidence) == "RNG_PARITY_FAILURE"
