"""Deterministic Live Fly v3 interface tests; no scientific run is executed."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from malecns_backend.embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
from malecns_backend.embodiment import _windows_m8_live_condition as kernel
from malecns_backend.embodiment import live_v2_motor_interface as v2
from malecns_backend.embodiment import live_v3_motor_interface as v3
from malecns_backend.embodiment.integrated_whole_leg_readiness import TIER_A
from malecns_backend.embodiment._windows_isolated_tier_b_motor_validation_adapter import compute_raw_contribution
from malecns_backend.live import headless


ARTIFACT = Path(
    "malecns_backend/embodiment/interface_output/candidate_motor_channel_validation.json"
)


def _real_v3_metadata():
    protocol, records, table = adapter._protocol()
    v2_protocol, records, v2_table = v2.derive_v2(protocol, records, table)
    return protocol, records, table, v2_protocol, v2_table, v3.derive_v3(
        v2_protocol, records, v2_table
    )


def test_v3_derives_exact_20_motor_six_sensory_without_mutating_v1_or_v2():
    v1_protocol, records, v1_table = adapter._protocol()
    v1_protocol_before = copy.deepcopy(v1_protocol)
    v1_table_before = copy.deepcopy(v1_table)

    v2_protocol, v2_records, v2_table = v2.derive_v2(v1_protocol, records, v1_table)
    v2_protocol_before = copy.deepcopy(v2_protocol)
    v2_table_before = copy.deepcopy(v2_table)

    derived, derived_records, rows = v3.derive_v3(v2_protocol, v2_records, v2_table)

    assert v1_protocol == v1_protocol_before
    assert v1_table == v1_table_before
    assert v2_protocol == v2_protocol_before
    assert v2_table == v2_table_before
    assert len(derived_records) == 42
    assert sum(row["neural_motor_admission"] for row in rows) == 20
    assert sum(row["neural_sensory_admission"] for row in rows) == 6
    assert derived["motor_output_count"] == 20
    assert derived["sensory_proprioceptive_input_count"] == 6
    assert tuple(row["actuator"] for row in derived["sensory_interfaces"]) == TIER_A

    admitted = {row["action_index"] for row in rows if row["neural_motor_admission"]}
    v2_admitted = {row["action_index"] for row in v2_table if row["neural_motor_admission"]}
    assert admitted - v2_admitted == {6, 24, 27}
    assert tuple(derived["admitted_motor_interfaces"]) == v3.V3_MOTOR
    assert tuple(v2_protocol["admitted_motor_interfaces"]) == v2.V2_MOTOR


def test_v3_candidate_definitions_match_frozen_validation_artifact():
    artifact = json.loads(ARTIFACT.read_text())
    expected = artifact["candidate_channels"]
    assert set(v3.CANDIDATE_MOTOR_CHANNELS) == {
        "joint_RFFemur", "joint_LFTarsus1", "joint_RFTarsus1"
    }

    for name, definition in v3.CANDIDATE_MOTOR_CHANNELS.items():
        row = expected[name]
        assert definition["action_index"] == row["action_index"]
        assert definition["coordinate_sign"] == row["coordinate_sign"] == -1
        assert definition["decoder_mode"] == kernel.ANTAGONIST_PAIR

        positive = {
            item["exact_annotation"]: tuple(item["body_root_ids"])
            for item in row["directional_pools"]["positive"]
        }
        negative = {
            item["exact_annotation"]: tuple(item["body_root_ids"])
            for item in row["directional_pools"]["negative"]
        }
        assert dict(definition["positive_populations"]) == positive
        assert dict(definition["negative_populations"]) == negative


def test_v3_supplemental_populations_resolve_exactly_once_in_real_malecns():
    from malecns_backend import load_malecns

    data = load_malecns()
    _, _, _, _, v2_table, (_, _, rows) = _real_v3_metadata()
    by_name = {row["actuator"]: row for row in rows}

    resolved = kernel._resolve_supplemental_channels(
        v3.SUPPLEMENTAL_MOTOR_CHANNELS, data, by_name, v2.HISTORICAL_MOTOR
    )
    assert set(resolved) == set(v3.SUPPLEMENTAL_MOTOR_CHANNELS)

    for name, channel in resolved.items():
        all_dense = [
            dense
            for population in channel["populations"].values()
            for dense in population
        ]
        assert len(all_dense) == len(set(all_dense))
        if name in v3.CANDIDATE_MOTOR_CHANNELS:
            assert channel["decoder_mode"] == kernel.ANTAGONIST_PAIR
            assert channel["positive"]
            assert channel["negative"]
            positive = {
                dense
                for population in channel["positive"]
                for dense in channel["populations"][population]
            }
            negative = {
                dense
                for population in channel["negative"]
                for dense in channel["populations"][population]
            }
            assert positive.isdisjoint(negative)
        else:
            assert channel["decoder_mode"] == kernel.UNIDIRECTIONAL_POSITIVE
            assert channel["negative"] == ()


def test_antagonist_pair_uses_existing_decoder_arithmetic_with_negative_coordinate_sign():
    bound = 0.25
    zero = compute_raw_contribution(0.0, 0.0, bound, -1)
    equal = compute_raw_contribution(34.0, 34.0, bound, -1)
    positive_only = compute_raw_contribution(34.0, 0.0, bound, -1)
    negative_only = compute_raw_contribution(0.0, 34.0, bound, -1)

    assert zero == 0.0
    assert equal == pytest.approx(0.0)
    assert positive_only < 0.0
    assert negative_only > 0.0
    assert positive_only == pytest.approx(-negative_only)

    # v2's one-sided Femur_roll path is unchanged.
    assert kernel.compute_unidirectional_positive_contribution(0.0, bound, 1) == 0.0
    assert kernel.compute_unidirectional_positive_contribution(17.0, bound, 1) == pytest.approx(0.125)


def test_v3_rejects_unauthorized_output_and_unauthorized_joint_admission():
    _, _, _, _, _, (protocol, _, rows) = _real_v3_metadata()
    vector = [0.0] * 42
    v3.assert_v3_physical_admission(vector, rows)

    vector[0] = 0.1
    with pytest.raises(RuntimeError, match="unauthorized"):
        v3.assert_v3_physical_admission(vector, rows)

    bad = copy.deepcopy(rows)
    bad[0]["neural_motor_admission"] = True
    with pytest.raises(RuntimeError, match="contract mismatch"):
        v3.validate_v3(protocol, bad)


def test_factories_keep_v1_11_v2_17_and_v3_20(monkeypatch):
    v1_protocol, records, v1_table = adapter._protocol()
    captured = []
    sentinel = SimpleNamespace(initialize=lambda: None)

    monkeypatch.setattr(
        "malecns_backend.embodiment._windows_m7d_corrected_spontaneous_adapter._protocol",
        lambda: (copy.deepcopy(v1_protocol), copy.deepcopy(records), copy.deepcopy(v1_table)),
    )
    monkeypatch.setattr(
        "malecns_backend.embodiment._windows_m8_live_condition.create_scientific_session",
        lambda **kwargs: captured.append(kwargs) or sentinel,
    )

    assert headless.create_live_session() is sentinel
    v1_args = captured.pop()
    assert "motor_channel_names" not in v1_args
    assert "supplemental_motor_channels" not in v1_args

    assert headless.create_live_v2_session(runtime_factory=lambda *_: None) is sentinel
    v2_args = captured.pop()
    assert len(v2_args["motor_channel_names"]) == 17
    assert len(v2_args["supplemental_motor_channels"]) == 6

    observer = lambda record: None
    assert headless.create_live_v3_session(
        telemetry_observer=observer, runtime_factory=lambda *_: None
    ) is sentinel
    v3_args = captured.pop()
    assert v3_args["continuous"] is True
    assert v3_args["proprioception_only"] is True
    assert v3_args["fixed_initial_baseline"] is True
    assert len(v3_args["motor_channel_names"]) == 20
    assert len(v3_args["supplemental_motor_channels"]) == 9
    assert v3_args["telemetry_observer"] is observer
