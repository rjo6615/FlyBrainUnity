"""M7D contract tests; no FlyGym or MaleCNS transition is executed."""
import io
import json

import pytest

from malecns_backend.embodiment import m7d_corrected_spontaneous as m
from malecns_backend.embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter


def test_exact_frozen_contract():
    p = m.protocol()
    m.validate_protocol(p)
    assert (m.SEED, m.DURATION_MS, m.PHYSICS_DT_MS) == (1, 500, .1)
    assert (m.EXPECTED_PHYSICS_TRANSITIONS, m.EXPECTED_PHYSICS_STATES, m.EXPECTED_NEURAL_UPDATES) == (5000, 5001, 1000)
    assert m.SPAWN_POS == (0., 0., 0.6045752232266313) and m.INIT_POSE == "tripod"
    assert len(m.CONDITIONS) == 2 and len(m.ADMITTED_MOTOR) == 11 and len(m.ADMITTED_SENSORY) == 6
    assert p["baseline_only_actuator_count"] == 31
    assert p["walking"] is None and p["tripod_gait_classification"] is None
    assert not any(p["hidden_assistance"].values())
    assert p["physical_initialization"]["adhesion_enabled"] is False
    assert p["physical_initialization"]["settling_transitions"] == 0


def test_b4_exact_hash_is_required(tmp_path):
    summary, manifest, raw = (tmp_path/x for x in ("summary.json", "manifest.json", "raw.npz"))
    raw.write_bytes(b"not canonical")
    summary.write_text(json.dumps({"status":"COMPLETE", "classification":"SUPPORTED_INITIALIZATION_STABLE_100MS", "physics_transitions":1000, "neural_transitions":0}))
    manifest.write_text(json.dumps({"status":"COMPLETE", "raw":{"sha256":m.B4_RAW_SHA256, "byte_size":len(raw.read_bytes())}}))
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        m.verify_b4(summary, manifest, raw)


def test_disabled_gate_zeros_only_admitted_contributions():
    values = {name: .125 for name in m.ADMITTED_MOTOR}
    assert adapter.gate_contributions(values, m.CONDITIONS[0], m.ADMITTED_MOTOR) == values
    assert set(adapter.gate_contributions(values, m.CONDITIONS[1], m.ADMITTED_MOTOR).values()) == {0.}
    with pytest.raises(RuntimeError): adapter.gate_contributions({}, m.CONDITIONS[0], m.ADMITTED_MOTOR)


def test_preflight_is_two_fresh_zero_transition_runtimes(monkeypatch):
    calls = []
    monkeypatch.setattr(adapter.m7d, "verify_b4", lambda: {"raw":{"sha256":m.B4_RAW_SHA256}})
    monkeypatch.setattr(adapter.m7d, "verify_m7", lambda: {"raw":{"sha256":"test"}})
    monkeypatch.setattr(adapter, "_environment", lambda: {"flygym":"1.2.1", "mujoco":"3.2.7"})
    monkeypatch.setattr(adapter, "_protocol", lambda: ({"admitted_motor_interfaces":list(m.ADMITTED_MOTOR)}, [], []))
    monkeypatch.setattr(adapter.m6c, "pre_intervention_equivalent", lambda *x: True)
    monkeypatch.setattr(adapter.m7d, "output_available", lambda: True)
    def runner(**kwargs):
        calls.append(kwargs)
        return {"physics_steps":0, "neural_steps":0, "pre_intervention_state":{"same":True},
            "initial_physical_state_audit":{"body_position":list(m.SPAWN_POS)},
            "telemetry_schema":{"x":{"dtype":"float64"}}, "telemetry_object_dtype":False,
            "telemetry_npz_roundtrip":True}
    report = adapter.windows_preflight(runner)
    assert len(calls) == 2 and all(x["initialize_only"] for x in calls)
    assert all(x["runtime_factory"] is adapter._runtime and x["proprioception_only"] for x in calls)
    assert all(x["fixed_initial_baseline"] for x in calls)
    assert report["physics_transitions"] == report["neural_transitions"] == 0


def test_numeric_npz_allow_pickle_false():
    np = pytest.importorskip("numpy"); stream = io.BytesIO()
    arrays = {"physics":np.zeros((5001, 3)), "neural":np.zeros((1000, 6))}
    np.savez_compressed(stream, **arrays); stream.seek(0)
    with np.load(stream, allow_pickle=False) as loaded:
        assert all(loaded[x].dtype != object for x in loaded.files)


def test_complete_result_and_raw_are_not_overwritable(tmp_path, monkeypatch):
    summary, manifest, raw = (tmp_path/x for x in ("s.json", "m.json", "r.npz"))
    summary.write_text('{"status":"COMPLETE"}')
    monkeypatch.setattr(m, "SUMMARY_PATH", summary); monkeypatch.setattr(m, "MANIFEST_PATH", manifest); monkeypatch.setattr(m, "RAW_PATH", raw)
    assert not m.output_available()
    summary.write_text('{"status":"NOT_RUN"}'); raw.write_bytes(b"exists")
    assert not m.output_available()


def test_fall_is_data_not_early_termination():
    assert m.protocol()["fall_after_intervention_terminates"] is False
