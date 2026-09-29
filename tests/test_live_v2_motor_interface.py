"""Deterministic Live Fly v2 interface tests; no scientific run is executed."""
import copy
from types import SimpleNamespace

import pytest

from malecns_backend.embodiment import live_v2_motor_interface as v2
from malecns_backend.embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
from malecns_backend.embodiment import _windows_m8_live_condition as kernel
from malecns_backend.embodiment.integrated_whole_leg_readiness import TIER_A
from malecns_backend.embodiment.tactile_motor_matched_control import MatchedControlPipeline
from malecns_backend.embodiment.motor import MotorSafety
from malecns_backend.live import headless


HISTORICAL_INDICES = (5, 12, 19, 26, 33, 40, 3, 10, 17, 31, 38)


def _v1_metadata():
    names = [f"joint_unused_{index}" for index in range(42)]
    for name, index in zip(v2.HISTORICAL_MOTOR, HISTORICAL_INDICES):
        names[index] = name
    for name, definition in v2.SUPPLEMENTAL_MOTOR_CHANNELS.items():
        names[definition["action_index"]] = name
    table = [{"actuator": name, "action_index": index,
              "neural_motor_admission": index in HISTORICAL_INDICES,
              "neural_sensory_admission": index in HISTORICAL_INDICES[:6],
              "coordinate_sign": 1 if index in HISTORICAL_INDICES[:6] else -1}
             for index, name in enumerate(names)]
    protocol = {"admitted_motor_interfaces": list(v2.HISTORICAL_MOTOR),
                "sensory_interfaces": [{"actuator": name} for name in TIER_A]}
    records = [{"name": name} for name in names]
    return protocol, records, table


def test_v2_derivation_preserves_v1_and_admits_only_six_femur_roll_channels():
    protocol, records, table = _v1_metadata()
    original_rows = [dict(row) for row in table]
    derived, derived_records, rows = v2.derive_v2(protocol, records, table)
    assert table == original_rows
    assert len(rows) == 42 and len(derived_records) == 42
    assert sum(row["neural_motor_admission"] for row in rows) == 17
    assert sum(row["neural_sensory_admission"] for row in rows) == 6
    old = {row["action_index"] for row in rows if row["actuator"] in v2.HISTORICAL_MOTOR}
    admitted = {row["action_index"] for row in rows if row["neural_motor_admission"]}
    assert admitted - old == v2.NEW_ACTION_INDICES
    assert tuple(row["actuator"] for row in derived["sensory_interfaces"]) == TIER_A


def test_v2_derivation_accepts_real_canonical_protocol_without_mutation():
    protocol, records, table = adapter._protocol()
    original = copy.deepcopy(protocol)

    derived, _, rows = v2.derive_v2(protocol, records, table)

    assert protocol == original
    assert sum(row["neural_motor_admission"] for row in rows) == 17
    assert sum(row["neural_sensory_admission"] for row in rows) == 6
    assert derived["sensory_interfaces"] == original["sensory_interfaces"]
    assert tuple(row["actuator"] for row in derived["sensory_interfaces"]) == TIER_A


def test_supplemental_population_contract_and_real_malecns_resolution():
    from malecns_backend import load_malecns

    data = load_malecns()
    _, _, table = _v1_metadata()
    rows = {row["actuator"]: row for row in table}
    resolved = kernel._resolve_supplemental_channels(
        v2.SUPPLEMENTAL_MOTOR_CHANNELS, data, rows, v2.HISTORICAL_MOTOR)
    assert set(resolved) == set(v2.SUPPLEMENTAL_MOTOR_CHANNELS)
    for name, channel in resolved.items():
        assert channel["coordinate_sign"] == 1
        assert channel["negative"] == ()
        assert len(next(iter(channel["populations"].values()))) == len(channel["body_ids"])

    missing = {name: dict(definition) for name, definition in v2.SUPPLEMENTAL_MOTOR_CHANNELS.items()}
    missing["joint_LFFemur_roll"]["body_ids"] = (999999999999999,)
    with pytest.raises(ValueError, match="missing from MaleCNS"):
        kernel._resolve_supplemental_channels(missing, data, rows, v2.HISTORICAL_MOTOR)


def test_unidirectional_decoder_silence_half_activation_and_existing_safety_path():
    assert kernel.compute_unidirectional_positive_contribution(0.0, 0.25, 1) == 0.0
    assert kernel.compute_unidirectional_positive_contribution(17.0, 0.25, 1) == pytest.approx(0.125)
    pipeline = MatchedControlPipeline(True, MotorSafety(-1.0, 1.0, 0.25, 4.0))
    result = pipeline.update(0.99, 0.25, 0.0005)
    assert result.range_clamped_target == 1.0
    assert result.slew_limited_target == pytest.approx(0.992)


def test_v2_assertion_rejects_unauthorized_output():
    protocol, records, table = _v1_metadata()
    _, _, rows = v2.derive_v2(protocol, records, table)
    vector = [0.0] * 42
    v2.assert_v2_physical_admission(vector, rows)
    vector[0] = 0.1
    with pytest.raises(RuntimeError, match="unauthorized"):
        v2.assert_v2_physical_admission(vector, rows)


def test_v1_factory_stays_11_channel_and_v2_factory_wires_continuous_session(monkeypatch):
    protocol, records, table = _v1_metadata()
    captured = []
    sentinel = SimpleNamespace(initialize=lambda: None)
    monkeypatch.setattr(
        "malecns_backend.embodiment._windows_m7d_corrected_spontaneous_adapter._protocol",
        lambda: (protocol, records, table))
    monkeypatch.setattr(
        "malecns_backend.embodiment._windows_m8_live_condition.create_scientific_session",
        lambda **kwargs: captured.append(kwargs) or sentinel)

    assert headless.create_live_session() is sentinel
    v1 = captured.pop()
    assert "supplemental_motor_channels" not in v1
    assert "motor_channel_names" not in v1

    observer = lambda record: None
    assert headless.create_live_v2_session(telemetry_observer=observer,
                                           runtime_factory=lambda *_: None) is sentinel
    configured = captured.pop()
    assert configured["continuous"] is True
    assert configured["proprioception_only"] is True
    assert configured["fixed_initial_baseline"] is True
    assert configured["motor_channel_names"] == v2.V2_MOTOR
    assert len(configured["supplemental_motor_channels"]) == 6
    assert configured["telemetry_observer"] is observer
