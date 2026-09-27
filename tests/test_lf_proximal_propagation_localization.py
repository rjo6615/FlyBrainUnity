import numpy as np
import pytest

from malecns_backend.embodiment import lf_proximal_propagation_localization as runner


LF = np.asarray([101, 202, 303], dtype=np.intp)


def test_identical_event_stage_does_not_diverge():
    records = [
        {"time_ms": 250.5, "neurons": []},
        {"time_ms": 251.0, "neurons": [101, 303]},
        {"time_ms": 251.5, "neurons": [202]},
    ]

    result = runner._compare_recorded_stage(
        records,
        [dict(record) for record in records],
        "delivered_lf_external_events",
        LF,
    )

    assert result == {
        "diverged": False,
        "first_difference_time_ms": None,
        "first_differing_neurons": [],
    }


def test_event_stage_reports_first_exact_difference():
    control = [
        {"time_ms": 250.5, "neurons": []},
        {"time_ms": 251.0, "neurons": [101]},
        {"time_ms": 251.5, "neurons": [202]},
    ]
    perturbation = [
        {"time_ms": 250.5, "neurons": []},
        {"time_ms": 251.0, "neurons": [101, 303]},
        {"time_ms": 251.5, "neurons": []},
    ]

    result = runner._compare_recorded_stage(
        control,
        perturbation,
        "lf_sensory_neural_events",
        LF,
    )

    assert result == {
        "diverged": True,
        "first_difference_time_ms": 251.0,
        "first_differing_neurons": [303],
    }


def test_event_stage_reports_all_neurons_differing_on_first_step():
    control = [
        {"time_ms": 250.5, "neurons": [101, 202]},
    ]
    perturbation = [
        {"time_ms": 250.5, "neurons": [202, 303]},
    ]

    result = runner._compare_recorded_stage(
        control,
        perturbation,
        "anatomical_one_hop_neural_events",
        LF,
    )

    assert result["diverged"] is True
    assert result["first_difference_time_ms"] == 250.5
    assert result["first_differing_neurons"] == [101, 303]


def test_encoded_rates_report_first_difference_and_frozen_neuron_ids():
    control = [
        {
            "sample_time_ms": 250.0,
            "rates_hz": [10.0, 20.0, 30.0],
        },
        {
            "sample_time_ms": 251.0,
            "rates_hz": [11.0, 21.0, 31.0],
        },
    ]
    perturbation = [
        {
            "sample_time_ms": 250.0,
            "rates_hz": [10.0, 99.0, 88.0],
        },
        {
            "sample_time_ms": 251.0,
            "rates_hz": [0.0, 0.0, 0.0],
        },
    ]

    result = runner._compare_recorded_stage(
        control,
        perturbation,
        "encoded_lf_rates",
        LF,
    )

    assert result == {
        "diverged": True,
        "first_difference_time_ms": 250.0,
        "first_differing_neurons": [202, 303],
    }


@pytest.mark.parametrize(
    "control, perturbation, stage, message",
    [
        (
            [{"time_ms": 250.5, "neurons": []}],
            [],
            "candidate_motor_neural_events",
            "record-count mismatch",
        ),
        (
            [{"time_ms": 250.5, "neurons": []}],
            [{"time_ms": 251.0, "neurons": []}],
            "candidate_motor_neural_events",
            "neural-step time mismatch",
        ),
        (
            [{"sample_time_ms": 250.0, "rates_hz": [1.0, 2.0, 3.0]}],
            [{"sample_time_ms": 251.0, "rates_hz": [1.0, 2.0, 3.0]}],
            "encoded_lf_rates",
            "sample-time mismatch",
        ),
    ],
)
def test_comparison_contract_mismatches_fail_closed(
    control,
    perturbation,
    stage,
    message,
):
    with pytest.raises(runner.RecruitmentFailure, match=message):
        runner._compare_recorded_stage(
            control,
            perturbation,
            stage,
            LF,
        )

def test_events_in_population_filters_and_sorts():
    events = np.asarray([900, 303, 101, 700, 202], dtype=np.intp)

    result = runner._events_in_population(events, LF)

    assert np.array_equal(
        result,
        np.asarray([101, 202, 303], dtype=np.intp),
    )


def test_events_in_population_empty_input_is_empty():
    result = runner._events_in_population(
        np.asarray([], dtype=np.intp),
        LF,
    )

    assert result.dtype == np.intp
    assert result.size == 0


def test_events_in_population_duplicate_neuron_fails_closed():
    events = np.asarray([101, 303, 101], dtype=np.intp)

    with pytest.raises(
        runner.RecruitmentFailure,
        match="duplicate neuron IDs",
    ):
        runner._events_in_population(events, LF)

def _empty_propagation_telemetry():
    return {
        "delivered_lf_external_events": [],
        "lf_sensory_neural_events": [],
        "anatomical_one_hop_neural_events": [],
        "runtime_admitted_one_hop_neural_events": [],
        "candidate_motor_neural_events": [],
    }


def test_record_propagation_step_records_frozen_populations_passively():
    class DummyBranch:
        pass

    branch = DummyBranch()
    branch.time_ms = 250.5
    branch._last_external_candidates = np.asarray(
        [101, 900],
        dtype=np.intp,
    )
    branch._last_external_delivered = np.asarray(
        [101, 900],
        dtype=np.intp,
    )
    branch.untouched_state = np.asarray(
        [7.0, 8.0, 9.0],
        dtype=np.float64,
    )

    fired = np.asarray(
        [101, 202, 303, 404, 505, 900],
        dtype=np.intp,
    )
    anatomical = np.asarray(
        [202, 303, 404],
        dtype=np.intp,
    )
    admitted = np.asarray(
        [303, 404],
        dtype=np.intp,
    )
    candidates = np.asarray(
        [404, 505],
        dtype=np.intp,
    )

    before_state = branch.untouched_state.copy()
    before_candidates = branch._last_external_candidates.copy()
    before_delivered = branch._last_external_delivered.copy()

    telemetry = _empty_propagation_telemetry()

    fired_candidates = runner._record_propagation_step(
        branch,
        fired,
        telemetry,
        LF,
        anatomical,
        admitted,
        candidates,
    )

    assert telemetry == {
        "delivered_lf_external_events": [
            {"time_ms": 250.5, "neurons": [101]}
        ],
        "lf_sensory_neural_events": [
            {"time_ms": 250.5, "neurons": [101, 202, 303]}
        ],
        "anatomical_one_hop_neural_events": [
            {"time_ms": 250.5, "neurons": [202, 303, 404]}
        ],
        "runtime_admitted_one_hop_neural_events": [
            {"time_ms": 250.5, "neurons": [303, 404]}
        ],
        "candidate_motor_neural_events": [
            {"time_ms": 250.5, "neurons": [404, 505]}
        ],
    }

    assert np.array_equal(
        fired_candidates,
        np.asarray([404, 505], dtype=np.intp),
    )
    assert branch.time_ms == 250.5
    assert np.array_equal(branch.untouched_state, before_state)
    assert np.array_equal(
        branch._last_external_candidates,
        before_candidates,
    )
    assert np.array_equal(
        branch._last_external_delivered,
        before_delivered,
    )


def test_record_propagation_step_rejects_external_withholding():
    class DummyBranch:
        pass

    branch = DummyBranch()
    branch.time_ms = 250.5
    branch._last_external_candidates = np.asarray(
        [101, 202],
        dtype=np.intp,
    )
    branch._last_external_delivered = np.asarray(
        [101],
        dtype=np.intp,
    )

    with pytest.raises(
        runner.RecruitmentFailure,
        match="withholding unexpectedly active",
    ):
        runner._record_propagation_step(
            branch,
            np.asarray([101], dtype=np.intp),
            _empty_propagation_telemetry(),
            LF,
            np.asarray([], dtype=np.intp),
            np.asarray([], dtype=np.intp),
            np.asarray([], dtype=np.intp),
        )

def test_execute_cli_fails_closed_before_execute_assay(monkeypatch, capsys):
    def forbidden_execute_assay(*args, **kwargs):
        raise AssertionError(
            "execute_assay must not be reached while scientific execution is locked"
        )

    monkeypatch.setattr(
        runner,
        "execute_assay",
        forbidden_execute_assay,
    )

    exit_code = runner.main(["--execute"])

    captured = capsys.readouterr()

    assert exit_code != 0
    assert "FAIL_CLOSED" in captured.out
    assert '"scientific_execution_authorized": false' in captured.out
    assert '"neural_runtime_steps": 0' in captured.out
    assert "scientific execution is not authorized" in captured.out