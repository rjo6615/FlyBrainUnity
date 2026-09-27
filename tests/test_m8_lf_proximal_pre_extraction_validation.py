import numpy as np
import pytest

from malecns_backend.embodiment import m8_lf_proximal_pre_extraction_validation as validation


def _sequential_physics_clock():
    clock = np.empty(100_001, dtype=np.float64)
    clock[0] = 0.0
    for index in range(1, clock.size):
        clock[index] = clock[index - 1] + 0.1
    return clock


def _report(neural_time, physics_time=None, *, physics_valid=True):
    if physics_time is None:
        physics_time = np.arange(100_001, dtype=np.float64) * 0.1
    return validation._neural_time_report(
        neural_time, physics_time=physics_time,
        physics_valid=physics_valid, np=np)


def test_exact_sampled_physics_clock_is_accepted():
    physics_time = np.arange(100_001, dtype=np.float64) * 0.1
    report, valid = _report(physics_time[5::5].copy(), physics_time)

    assert valid
    assert report["exact_alignment_to_physics_rows"]
    assert report["parent_physics_time_valid"]


def test_one_ulp_difference_from_corresponding_physics_sample_is_rejected():
    physics_time = np.arange(100_001, dtype=np.float64) * 0.1
    neural_time = physics_time[5::5].copy()
    neural_time[10_000] = np.nextafter(neural_time[10_000], np.inf)

    report, valid = _report(neural_time, physics_time)

    assert not valid
    assert not report["exact_alignment_to_physics_rows"]


@pytest.mark.parametrize("delta", [-1, 1])
def test_wrong_count_is_rejected(delta):
    physics_time = np.arange(100_001, dtype=np.float64) * 0.1
    neural_time = physics_time[5::5].copy()
    neural_time = neural_time[:20_000 + delta] if delta < 0 else np.append(neural_time, 10_000.5)

    assert not _report(neural_time, physics_time)[1]


def test_nonfinite_neural_timestamp_is_rejected():
    physics_time = np.arange(100_001, dtype=np.float64) * 0.1
    neural_time = physics_time[5::5].copy()
    neural_time[42] = np.nan

    report, valid = _report(neural_time, physics_time)

    assert not valid
    assert not report["finite"]


def test_nonmonotonic_neural_timestamp_is_rejected():
    physics_time = np.arange(100_001, dtype=np.float64) * 0.1
    neural_time = physics_time[5::5].copy()
    neural_time[42] = neural_time[41]

    report, valid = _report(neural_time, physics_time)

    assert not valid
    assert not report["strictly_increasing"]


def test_invalid_parent_physics_clock_is_rejected():
    physics_time = np.arange(100_001, dtype=np.float64) * 0.1
    report, valid = _report(
        physics_time[5::5].copy(), physics_time, physics_valid=False)

    assert not valid
    assert not report["parent_physics_time_valid"]


def test_ideal_grid_diagnostic_failure_alone_does_not_reject_sampled_clock():
    physics_time = _sequential_physics_clock()
    physics_report, physics_valid, _ = validation._time_report(
        physics_time, count=100_001, dt_ms=0.1, first_index=0, np=np)
    report, valid = _report(
        physics_time[5::5].copy(), physics_time, physics_valid=physics_valid)

    assert physics_report["valid"]
    assert not report["integer_sample_index_correspondence"]
    assert not report["hypothetical_independent_0_5ms_accumulator_comparison"][
        "within_derived_accumulation_and_adjacent_cadence_bounds"]
    assert valid
