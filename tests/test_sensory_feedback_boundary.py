import hashlib
import json
import sys
from types import SimpleNamespace

import pytest

from malecns_backend.embodiment import sensory_feedback_boundary as boundary
from malecns_backend.embodiment import sensory_feedback_boundary_audit as audit


def fake_locked_module(monkeypatch, analyze, run_live):
    locked = SimpleNamespace(analyze=analyze, run_live=run_live)
    monkeypatch.setitem(sys.modules,
        "malecns_backend.embodiment.tactile_motor_closed_loop_audit", locked)
    return locked


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


def test_first_recursion_failure_is_preserved_without_reclassification():
    path = audit.DEFAULT_OUTPUT.with_name(
        "sensory_feedback_boundary_100ms_first_attempt_recursion_failure.json")
    artifact = json.loads(path.read_text(encoding="utf-8"))
    assert artifact["run_status"] == "FAILED"
    assert artifact["classification"] == "PROVENANCE_FAILURE"
    assert artifact["reason"] == "RecursionError: maximum recursion depth exceeded"
    assert artifact["provenance"]["verified"]
    assert artifact["provenance"]["earlier_locks_verified"]
    assert "Traceback" in artifact["traceback"]
    assert "sensory_feedback_boundary.py" in artifact["traceback"]


def test_live_uses_original_m5d4d_analyzer_once_and_restores(monkeypatch):
    calls = []

    def original(enabled, disabled):
        calls.append((enabled, disabled))
        return "original report"

    def m5d4e(enabled, disabled, *, _m5d4d_analyze):
        assert _m5d4d_analyze is original
        return _m5d4d_analyze(enabled, disabled)

    monkeypatch.setattr(audit, "verify_provenance", lambda: {"verified": True})
    monkeypatch.setattr(audit, "analyze", m5d4e)
    locked = fake_locked_module(monkeypatch, original,
        lambda *_: locked.analyze([1], [2]))
    assert audit.run_live() == "original report"
    assert calls == [([1], [2])]
    assert locked.analyze is original


@pytest.mark.parametrize("failure_site", ["reducer", "runner"])
def test_live_restores_original_after_diagnostic_failure(monkeypatch, failure_site):
    def original(*_):
        return {}

    def reducer(*_, **__):
        raise RuntimeError("reducer failed")

    def runner(*_):
        if failure_site == "reducer":
            return locked.analyze([], [])
        raise RuntimeError("runner failed")

    monkeypatch.setattr(audit, "verify_provenance", lambda: {"verified": True})
    monkeypatch.setattr(audit, "analyze", reducer)
    locked = fake_locked_module(monkeypatch, original, runner)
    with pytest.raises(RuntimeError, match=f"{failure_site} failed"):
        audit.run_live()
    assert locked.analyze is original


def test_live_does_not_patch_on_provenance_failure(monkeypatch):
    original = lambda *_: {}
    locked = fake_locked_module(monkeypatch, original, lambda *_: {})
    monkeypatch.setattr(audit, "verify_provenance",
        lambda: (_ for _ in ()).throw(RuntimeError("bad provenance")))
    with pytest.raises(RuntimeError, match="bad provenance"):
        audit.run_live()
    assert locked.analyze is original


@pytest.mark.parametrize(("stage", "classification"), [
    ("provenance", "PROVENANCE_FAILURE"),
    ("diagnostic", "DIAGNOSTIC_IMPLEMENTATION_FAILURE"),
])
def test_main_classifies_only_provenance_stage_as_provenance_failure(
        tmp_path, monkeypatch, stage, classification):
    output = tmp_path / "report.json"
    if stage == "provenance":
        monkeypatch.setattr(audit, "verify_provenance",
            lambda: (_ for _ in ()).throw(RuntimeError("provenance failed")))
    else:
        monkeypatch.setattr(audit, "verify_provenance", lambda: {"verified": True})
        monkeypatch.setattr(audit, "run_live",
            lambda *_: (_ for _ in ()).throw(RuntimeError("reducer failed")))
    assert audit.main(["--live", "--json", str(output)]) == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["classification"] == classification
