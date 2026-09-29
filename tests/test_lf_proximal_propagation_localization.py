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

def test_execute_cli_requires_authorization_before_execute_assay(
    monkeypatch,
    capsys,
    tmp_path,
):
    calls = []

    fake_result = {
        "schema": "LF-PROXIMAL-PROPAGATION-LOCALIZATION-RESULT.1",
        "seeds": [1, 2, 3],
        "conditions": [
            "CONTROL_REPLAY",
            "LF_MIN_BOUND",
            "LF_MAX_BOUND",
        ],
    }

    def fake_execute_assay(replay, provenance):
        calls.append((replay, provenance))
        return fake_result

    monkeypatch.setattr(
        runner,
        "execute_assay",
        fake_execute_assay,
    )

    canonical = (
        runner.SPEC_DIR
        / "lf_proximal_propagation_localization_result.json"
    )
    canonical_before = canonical.read_bytes()

    output_path = tmp_path / "fake_result.json"

    exit_code = runner.main([
        "--execute",
        "--output",
        str(output_path),
    ])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert len(calls) == 1
    assert "SCIENTIFIC_EXECUTION_COMPLETE" in captured.out
    assert '"scientific_execution_authorized": true' in captured.out

    assert output_path.is_file()
    assert runner.json.loads(
        output_path.read_text(encoding="utf-8")
    ) == fake_result

    # Tests must never mutate the canonical scientific result.
    assert canonical.read_bytes() == canonical_before


def test_result_writer_refuses_to_replace_existing_file(tmp_path):
    output_path = tmp_path / "existing_result.json"
    sentinel = b"existing-scientific-result\n"
    output_path.write_bytes(sentinel)

    with pytest.raises(FileExistsError):
        runner._write_result_exclusive(
            output_path,
            {
                "schema": "TEST",
                "status": "FAKE",
            },
        )

    assert output_path.read_bytes() == sentinel


def test_result_writer_creates_new_strict_utf8_file(tmp_path):
    output_path = tmp_path / "new_result.json"
    payload = {
        "schema": "TEST",
        "status": "FAKE",
    }

    runner._write_result_exclusive(
        output_path,
        payload,
    )

    raw = output_path.read_bytes()

    assert not raw.startswith(b"\xef\xbb\xbf")
    assert raw.endswith(b"\n")
    assert runner.json.loads(raw.decode("utf-8")) == payload



def test_execute_cli_refuses_existing_output_before_execute_assay(
    monkeypatch,
    capsys,
    tmp_path,
):
    calls = []

    def forbidden_execute_assay(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError(
            "execute_assay reached despite pre-existing output"
        )

    def forbidden_provenance(*args, **kwargs):
        calls.append(("provenance", args, kwargs))
        raise AssertionError(
            "provenance gate reached despite pre-existing output"
        )

    def forbidden_authorization(*args, **kwargs):
        calls.append(("authorization", args, kwargs))
        raise AssertionError(
            "authorization gate reached despite pre-existing output"
        )

    monkeypatch.setattr(
        runner,
        "execute_assay",
        forbidden_execute_assay,
    )
    monkeypatch.setattr(
        runner,
        "provenance_gate",
        forbidden_provenance,
    )
    monkeypatch.setattr(
        runner,
        "execution_authorization_gate",
        forbidden_authorization,
    )

    output_path = tmp_path / "existing_result.json"
    sentinel = b"already-preserved-scientific-result\n"
    output_path.write_bytes(sentinel)

    exit_code = runner.main([
        "--execute",
        "--output",
        str(output_path),
    ])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert calls == []
    assert output_path.read_bytes() == sentinel
    assert "FAIL_CLOSED" in captured.out
    assert "refusing to overwrite existing scientific result" in captured.out
    assert '"neural_runtime_steps": 0' in captured.out



def test_execute_cli_fails_closed_when_authorization_is_rejected(
    monkeypatch,
    capsys,
    tmp_path,
):
    def forbidden_execute_assay(*args, **kwargs):
        raise AssertionError(
            "execute_assay must not be reached after authorization failure"
        )

    def rejected_authorization(*args, **kwargs):
        raise runner.RecruitmentFailure(
            "execution authorization SHA-256 mismatch"
        )

    monkeypatch.setattr(
        runner,
        "execute_assay",
        forbidden_execute_assay,
    )
    monkeypatch.setattr(
        runner,
        "execution_authorization_gate",
        rejected_authorization,
    )

    output_path = tmp_path / "authorization_rejected_result.json"

    exit_code = runner.main([
        "--execute",
        "--output",
        str(output_path),
    ])

    captured = capsys.readouterr()

    assert exit_code != 0
    assert "FAIL_CLOSED" in captured.out
    assert '"scientific_execution_authorized": false' in captured.out
    assert '"neural_runtime_steps": 0' in captured.out
    assert "SHA-256 mismatch" in captured.out
    assert not output_path.exists()


def test_recovery_attempt_writer_refuses_existing_claim(tmp_path):
    attempt = tmp_path / "recovery_attempt.json"
    sentinel = b"existing-recovery-claim\n"
    attempt.write_bytes(sentinel)

    try:
        runner._write_recovery_attempt_exclusive(
            attempt,
            runner.EXPECTED["recovery_authorization"],
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError(
            "existing recovery-attempt claim was overwritten"
        )

    assert attempt.read_bytes() == sentinel


def test_recovery_cli_rejects_custom_output_before_any_gate(
    monkeypatch,
    capsys,
    tmp_path,
):
    calls = []

    def forbidden_gate(*args, **kwargs):
        calls.append(("gate", args, kwargs))
        raise AssertionError("recovery gate must not be reached")

    def forbidden_execute(*args, **kwargs):
        calls.append(("execute", args, kwargs))
        raise AssertionError("execute_assay must not be reached")

    monkeypatch.setattr(
        runner,
        "RECOVERY_RESULT",
        tmp_path / "recovery_result.json",
    )
    monkeypatch.setattr(
        runner,
        "RECOVERY_ATTEMPT",
        tmp_path / "recovery_attempt.json",
    )
    monkeypatch.setattr(
        runner,
        "recovery_authorization_gate",
        forbidden_gate,
    )
    monkeypatch.setattr(
        runner,
        "execute_assay",
        forbidden_execute,
    )

    custom_output = tmp_path / "forbidden_custom_result.json"

    exit_code = runner.main([
        "--recover-result",
        "--output",
        str(custom_output),
    ])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert calls == []
    assert not custom_output.exists()
    assert "FAIL_CLOSED" in captured.out
    assert '"scientific_execution_started": false' in captured.out
    assert '"neural_runtime_steps": 0' in captured.out


def test_recovery_cli_refuses_existing_result_before_any_gate(
    monkeypatch,
    capsys,
    tmp_path,
):
    calls = []

    output = tmp_path / "recovery_result.json"
    sentinel = b"already-preserved-recovery-result\n"
    output.write_bytes(sentinel)

    def forbidden_gate(*args, **kwargs):
        calls.append(("gate", args, kwargs))
        raise AssertionError("recovery gate must not be reached")

    def forbidden_execute(*args, **kwargs):
        calls.append(("execute", args, kwargs))
        raise AssertionError("execute_assay must not be reached")

    monkeypatch.setattr(runner, "RECOVERY_RESULT", output)
    monkeypatch.setattr(
        runner,
        "RECOVERY_ATTEMPT",
        tmp_path / "recovery_attempt.json",
    )
    monkeypatch.setattr(
        runner,
        "recovery_authorization_gate",
        forbidden_gate,
    )
    monkeypatch.setattr(
        runner,
        "execute_assay",
        forbidden_execute,
    )

    exit_code = runner.main(["--recover-result"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert calls == []
    assert output.read_bytes() == sentinel
    assert "FAIL_CLOSED" in captured.out
    assert "refusing to overwrite existing recovery result" in captured.out
    assert '"scientific_execution_started": false' in captured.out
    assert '"neural_runtime_steps": 0' in captured.out


def test_recovery_cli_claims_attempt_before_mocked_assay(
    monkeypatch,
    capsys,
    tmp_path,
):
    output = tmp_path / "recovery_result.json"
    attempt = tmp_path / "recovery_attempt.json"

    canonical_before = runner.CANONICAL_RESULT.read_bytes()
    calls = []

    def fake_authorization_gate():
        calls.append("authorization")
        return {
            "identity": runner.EXPECTED["recovery_authorization"],
            "authorization": {},
        }

    def fake_provenance_gate(**kwargs):
        calls.append("provenance")
        return "mock-replay", {"mock": "provenance"}

    def fake_execute_assay(replay, provenance):
        calls.append("execute")
        assert attempt.exists()
        assert replay == "mock-replay"
        assert provenance == {"mock": "provenance"}

        return {
            "schema": "LF-PROXIMAL-PROPAGATION-LOCALIZATION-RESULT.1",
            "seeds": list(runner.SEEDS),
            "conditions": list(runner.CONDITIONS),
        }

    monkeypatch.setattr(runner, "RECOVERY_RESULT", output)
    monkeypatch.setattr(runner, "RECOVERY_ATTEMPT", attempt)
    monkeypatch.setattr(
        runner,
        "recovery_authorization_gate",
        fake_authorization_gate,
    )
    monkeypatch.setattr(
        runner,
        "provenance_gate",
        fake_provenance_gate,
    )
    monkeypatch.setattr(
        runner,
        "execute_assay",
        fake_execute_assay,
    )

    exit_code = runner.main(["--recover-result"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert calls == ["authorization", "provenance", "execute"]
    assert attempt.exists()
    assert output.exists()
    assert runner.CANONICAL_RESULT.read_bytes() == canonical_before
    assert "RESULT_RECONSTRUCTION_COMPLETE" in captured.out
    assert '"independent_replicate": false' in captured.out


def test_failed_recovery_consumes_claim_before_mocked_assay_failure(
    monkeypatch,
    capsys,
    tmp_path,
):
    output = tmp_path / "recovery_result.json"
    attempt = tmp_path / "recovery_attempt.json"

    canonical_before = runner.CANONICAL_RESULT.read_bytes()
    execute_calls = []

    def fake_authorization_gate():
        return {
            "identity": runner.EXPECTED["recovery_authorization"],
            "authorization": {},
        }

    def fake_provenance_gate(**kwargs):
        return "mock-replay", {"mock": "provenance"}

    def failing_execute_assay(replay, provenance):
        execute_calls.append((replay, provenance))
        assert attempt.exists()
        raise runner.RecruitmentFailure(
            "mocked failure after recovery claim"
        )

    monkeypatch.setattr(runner, "RECOVERY_RESULT", output)
    monkeypatch.setattr(runner, "RECOVERY_ATTEMPT", attempt)
    monkeypatch.setattr(
        runner,
        "recovery_authorization_gate",
        fake_authorization_gate,
    )
    monkeypatch.setattr(
        runner,
        "provenance_gate",
        fake_provenance_gate,
    )
    monkeypatch.setattr(
        runner,
        "execute_assay",
        failing_execute_assay,
    )

    first_exit = runner.main(["--recover-result"])
    first = capsys.readouterr()

    assert first_exit == 1
    assert len(execute_calls) == 1
    assert attempt.exists()
    assert not output.exists()
    assert runner.CANONICAL_RESULT.read_bytes() == canonical_before
    assert '"scientific_execution_started": true' in first.out
    assert '"scientific_execution_completed": false' in first.out
    assert '"neural_runtime_steps": null' in first.out

    second_exit = runner.main(["--recover-result"])
    second = capsys.readouterr()

    assert second_exit == 1
    assert len(execute_calls) == 1
    assert attempt.exists()
    assert not output.exists()
    assert runner.CANONICAL_RESULT.read_bytes() == canonical_before
    assert "FAIL_CLOSED" in second.out
    assert '"scientific_execution_started": false' in second.out
    assert '"neural_runtime_steps": 0' in second.out
