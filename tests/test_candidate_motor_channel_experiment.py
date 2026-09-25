import json

import pytest

from malecns_backend.embodiment import candidate_motor_channel_experiment as exp
from malecns_backend.embodiment import _windows_m8_live_condition as kernel
from malecns_backend.embodiment.m7_telemetry import CompactTelemetry, build_schema

import numpy as np


def test_frozen_preregistration_gate_and_status(tmp_path):
    assert exp.verify_preregistration() == exp.PREREGISTRATION_SHA256
    altered = tmp_path / "prereg.json"
    altered.write_bytes(exp.PREREGISTRATION_PATH.read_bytes() + b" ")
    with pytest.raises(RuntimeError, match="SHA-256"):
        exp.verify_preregistration(altered)
    value = json.loads(exp.PREREGISTRATION_PATH.read_text())
    value["status"] = "COMPLETE"
    changed = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
    # Isolate the status gate from the immutable-file hash gate.
    with pytest.raises(RuntimeError, match="NOT_RUN"):
        exp.verify_preregistration_bytes(changed, exp.sha256_bytes(changed))


@pytest.mark.parametrize("condition,expected", [("ENABLED", 0.125), ("ZEROED", 0.0)])
def test_exactly_one_candidate_authorized_and_other_41_zero(condition, expected):
    vector, before, after = exp.authorize_contribution(24, 0.125, condition)
    assert before == 0.125 and after == expected
    assert vector[24] == expected
    assert sum(value != 0.0 for value in vector) == (1 if condition == "ENABLED" else 0)
    assert all(vector[index] == 0.0 for index in exp.CURRENT_11_INDICES)


def test_authorization_rejects_unknown_candidate_and_nonfinite():
    with pytest.raises(ValueError):
        exp.authorize_contribution(5, 1.0, "ENABLED")
    with pytest.raises(ValueError):
        exp.authorize_contribution(24, float("nan"), "ENABLED")


def test_matched_initialization_is_exact_and_complete():
    state = {key: [1, 2] for key in exp.INITIALIZATION_FIELDS}
    assert exp.require_matched_initialization(state, dict(state))
    different = dict(state); different["initial_ctrl"] = [1, 3]
    with pytest.raises(RuntimeError, match="initial_ctrl"):
        exp.require_matched_initialization(state, different)


class _FakeOption:
    def __init__(self):
        self.timestep = .0001
        self.gravity = np.asarray([0., 0., -9.81])


class _FakeModel:
    def __init__(self):
        self.nq, self.nv, self.nu, self.na = 2, 2, 1, 1
        self.nbody, self.njnt, self.ngeom = 1, 1, 1
        self.nsensor, self.nsite = 0, 0
        self.opt = _FakeOption()
        self.jnt_range = np.asarray([[-1., 1.]])
        self.body_mass = np.asarray([1.])
        self.names = np.frombuffer(f"instance-{id(self)}".encode(), dtype=np.uint8)
        self.jnt_nameadr = np.asarray([len(self.names)])

    def id2name(self, index, kind):
        return f"instance-{id(self)}/{kind}-{index}"


class _FakeData:
    def __init__(self):
        self.qpos = np.asarray([0., 1.])
        self.qvel = np.asarray([0., 0.])
        self.act = np.asarray([0.])
        self.ctrl = np.asarray([0.])


def test_physics_identity_ignores_instance_namespace_but_rejects_scientific_changes():
    first = exp.physics_model_identity(_FakeModel(), _FakeData())
    second = exp.physics_model_identity(_FakeModel(), _FakeData())
    assert first == second

    changed_qpos = _FakeData(); changed_qpos.qpos[0] = 1.
    assert exp.physics_model_identity(_FakeModel(), changed_qpos) != first
    changed_qvel = _FakeData(); changed_qvel.qvel[0] = 1.
    assert exp.physics_model_identity(_FakeModel(), changed_qvel) != first
    changed_model = _FakeModel(); changed_model.opt.gravity[2] = -1.62
    assert exp.physics_model_identity(changed_model, _FakeData()) != first
    changed_act = _FakeData(); changed_act.act[0] = .25
    assert exp.physics_model_identity(_FakeModel(), changed_act) != first


def test_component_diagnostic_reports_exact_array_values_and_inventory_indices():
    enabled = exp.physics_model_diagnostic_snapshot(_FakeModel(), _FakeData())
    model, data = _FakeModel(), _FakeData()
    model.body_mass[0] = np.nextafter(1.0, 2.0)
    data.act[0] = .25
    zeroed = exp.physics_model_diagnostic_snapshot(model, data)
    zeroed["inventories"]["body"][0] = "different-body"
    comparison = exp.compare_physics_model_snapshots(enabled, zeroed)
    assert not comparison["identical"]
    by_name = {row["component"]: row for row in comparison["differences"]}
    mass = by_name["model_arrays.body_mass"]
    assert mass["enabled_dtype"] == mass["zeroed_dtype"] == "<f8"
    assert mass["enabled_shape"] == mass["zeroed_shape"] == [1]
    assert mass["differing_element_count"] == 1
    assert mass["first_differences"] == [{"index": [0], "enabled": 1.0,
                                           "zeroed": np.nextafter(1.0, 2.0)}]
    assert mass["maximum_absolute_difference"] == np.nextafter(1.0, 2.0) - 1.0
    assert by_name["initial_state.act"]["first_differences"][0]["index"] == [0]
    assert by_name["inventories.body"]["differing_indices"] == [
        {"index": 0, "enabled": "body-0", "zeroed": "different-body"}]


def test_component_diagnostic_identical_fresh_fake_constructions():
    a1 = exp.physics_model_diagnostic_snapshot(_FakeModel(), _FakeData())
    a2 = exp.physics_model_diagnostic_snapshot(_FakeModel(), _FakeData())
    result = exp.compare_physics_model_snapshots(a1, a2)
    assert result["identical"] and result["differences"] == []


def test_diagnostic_json_value_recursively_normalizes_numpy_values():
    diagnostic = {
        "difference": {
            "index": (np.int64(7),),
            "values": [np.float64(1.25), np.bool_(True)],
            "sample": np.asarray([[2, 3]], dtype=np.int64),
        }
    }

    normalized = exp.diagnostic_json_value(diagnostic)

    assert normalized == {"difference": {
        "index": [7], "values": [1.25, True], "sample": [[2, 3]]}}
    assert type(normalized["difference"]["index"][0]) is int
    assert type(normalized["difference"]["values"][0]) is float
    assert type(normalized["difference"]["values"][1]) is bool
    assert json.loads(json.dumps(normalized)) == normalized


def test_fixed_duration_has_no_result_dependent_extension():
    assert exp.transition_counts(1000, 0.1, 0.5) == (10000, 2000)
    with pytest.raises(ValueError):
        exp.transition_counts(1000.1, 0.1, 0.5)


def test_output_cannot_overlap_preregistration(tmp_path):
    with pytest.raises(ValueError, match="preregistration"):
        exp.require_new_output_directory(exp.PREREGISTRATION_PATH)
    occupied = tmp_path / "output"; occupied.mkdir(); (occupied / "x").write_text("x")
    with pytest.raises(FileExistsError):
        exp.require_new_output_directory(occupied)


def test_aborted_legacy_attempt_is_immutable_and_next_attempt_is_namespaced(tmp_path):
    root = tmp_path / "candidate_motor_channel_experiment"
    root.mkdir()
    original = b'{"status":"STARTED"}\n'
    (root / "execution_manifest.json").write_bytes(original)
    destination, attempt, prior = exp.next_attempt_directory(root)
    assert destination == root / "attempt_002"
    assert attempt == 2
    assert prior[0]["status"] == "ABORTED_INFRASTRUCTURE_ERROR"
    assert (root / "execution_manifest.json").read_bytes() == original


def test_candidate_mode_preserves_legacy_shape_and_exposes_42_vectors():
    schema = build_schema(qpos_shape=(2,), qvel_shape=(2,), ctrl_shape=(2,),
                          contact_forces_shape=(1,))
    telemetry = CompactTelemetry(schema, physics_capacity=1, neural_capacity=1)
    observer, decoder, admitted = kernel._legacy_neural_telemetry(
        admitted_names=("joint_RFFemur",), channels={"joint_RFFemur": {"peak_observer": 2.0}},
        raw_values={"joint_RFFemur": .2}, contributions={"joint_RFFemur": .1},
        isolated_candidate_telemetry=True)
    telemetry.record("neural", {"neural_time_ms": .5,
        "neural_sensory_encoded": np.zeros(6), "neural_delivered_drive_count": 0,
        "neural_aggregate_spikes": 0, "neural_observer_outputs": observer,
        "neural_decoder_outputs": decoder, "neural_admitted_contributions": admitted}, .5)
    assert telemetry.export()["neural_admitted_contributions"].shape == (1, 11)
    assert not np.any(telemetry.export()["neural_admitted_contributions"])
    for condition in exp.CONDITIONS:
        post, before_value, after_value = exp.authorize_contribution(24, .125, condition)
        before = np.zeros(42); before[24] = before_value
        assert before.shape == np.asarray(post).shape == (42,)
        assert np.flatnonzero(before).tolist() == [24]
        assert np.flatnonzero(post).tolist() == ([24] if condition == "ENABLED" else [])
        assert after_value == post[24]


def test_default_legacy_telemetry_behavior_is_unchanged():
    names = tuple(f"channel_{index}" for index in range(11))
    channels = {name: {"peak_observer": float(index)} for index, name in enumerate(names)}
    raw = {name: float(index + 20) for index, name in enumerate(names)}
    admitted_input = {name: float(index + 40) for index, name in enumerate(names)}
    assert kernel._legacy_neural_telemetry(admitted_names=names, channels=channels,
        raw_values=raw, contributions=admitted_input, isolated_candidate_telemetry=False) == (
            [float(index) for index in range(11)],
            [float(index + 20) for index in range(11)],
            [float(index + 40) for index in range(11)])


@pytest.mark.parametrize("metrics,classification", [
    ({"total_spike_increments": 2, "peak_filtered_rate_hz": 10., "peak_absolute_contribution": .01,
      "peak_absolute_raw_antagonist_signal": .1, "positive_peak_hz": 10., "negative_peak_hz": 0.}, "SUPPORTED_AND_ACTIVE"),
    ({"total_spike_increments": 0, "peak_filtered_rate_hz": 0., "peak_absolute_contribution": 0.,
      "peak_absolute_raw_antagonist_signal": 0., "positive_peak_hz": 0., "negative_peak_hz": 0.}, "SUPPORTED_BUT_SILENT"),
    ({"total_spike_increments": 2, "peak_filtered_rate_hz": 10., "peak_absolute_contribution": 0.,
      "peak_absolute_raw_antagonist_signal": 0., "positive_peak_hz": 10., "negative_peak_hz": 10.}, "DECODER_CANCELLATION"),
    ({"total_spike_increments": 1, "peak_filtered_rate_hz": .2, "peak_absolute_contribution": 0.,
      "peak_absolute_raw_antagonist_signal": 0., "positive_peak_hz": .2, "negative_peak_hz": 0.}, "SUPPORTED_LOW_ACTIVITY"),
])
def test_synthetic_classification(metrics, classification):
    assert exp.classify(metrics) == classification
