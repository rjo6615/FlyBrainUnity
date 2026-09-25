import json

import pytest

from malecns_backend.embodiment import candidate_motor_channel_experiment as exp


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
