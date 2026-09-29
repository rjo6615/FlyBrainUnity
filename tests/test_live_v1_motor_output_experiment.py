import importlib
import json
import math
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

import pytest

from malecns_backend.embodiment import live_v1_motor_output_experiment as exp
from malecns_backend.embodiment import _windows_m8_live_condition as live


def test_import_default_help_and_validation_are_zero_transition(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(exp, "assert_execution_authorized", lambda: calls.append("execute"))
    assert importlib.reload(exp) is exp
    assert exp.main([]) == 0
    with pytest.raises(SystemExit) as stopped:
        exp.main(["--help"])
    assert stopped.value.code == 0
    capsys.readouterr()
    assert exp.main(["--validate"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["neural_transitions"] == report["physics_transitions"] == 0
    assert calls == []


def test_frozen_11_channel_inventory_identity_and_order():
    assert exp.MOTOR_CHANNELS == (
        ("joint_LFTibia", 5, 1), ("joint_LMTibia", 12, 1),
        ("joint_LHTibia", 19, 1), ("joint_RFTibia", 26, 1),
        ("joint_RMTibia", 33, 1), ("joint_RHTibia", 40, 1),
        ("joint_LFFemur", 3, -1), ("joint_LMFemur", 10, -1),
        ("joint_LHFemur", 17, -1), ("joint_RMFemur", 31, -1),
        ("joint_RHFemur", 38, -1))
    assert len(exp.MOTOR_CHANNELS) == len({x[0] for x in exp.MOTOR_CHANNELS}) == 11


def test_existing_gates_only_zero_final_contributions():
    from malecns_backend.embodiment import _windows_live_v1_motor_output_experiment_adapter as adapter
    names = tuple(x[0] for x in exp.MOTOR_CHANNELS)
    decoded = {name: index + .25 for index, name in enumerate(names)}
    assert adapter.enabled_gate(decoded, names) == decoded
    assert adapter.matched_control_gate(decoded, names) == dict.fromkeys(names, 0.0)
    with pytest.raises(RuntimeError):
        adapter.enabled_gate(decoded, tuple(reversed(names)))


def test_observational_hook_added_without_decoder_change():
    design = exp.design()
    assert "decoder change" in design["prohibitions"]
    assert exp.readiness()["existing_runtime_hook_added"] is True


def _neural(index=1, timestamp=None):
    values = [index, index * .5 if timestamp is None else timestamp,
              [[0]], [[0.0]], [0.0] * 11, [0.0] * 11,
              [0.0] * 11, [0.0] * 11, [0.0] * 11, [0.0] * 11,
              [0.0] * 11, [False] * 11, [False] * 11, [0.0] * 42,
              [0.0] * 6, None, []]
    return OrderedDict(zip(exp.NEURAL_FIELDS, values))


def _physics(index=1, timestamp=None):
    values = [index, index * .1 if timestamp is None else timestamp,
              [0.0] * 42, [0.0] * 42, [0.0] * 49,
              [0.0] * 48, [0.0] * 3, [1.0, 0.0, 0.0, 0.0], []]
    return OrderedDict(zip(exp.PHYSICS_FIELDS, values))


def test_individual_telemetry_validation_is_passive_and_checks_shape_and_order():
    neural = _neural(); physics = _physics()
    before = json.dumps([neural, physics])
    exp.validate_neural_record(neural)
    exp.validate_physics_record(physics)
    assert json.dumps([neural, physics]) == before
    exp.validate_neural_record(_neural(2), previous_index=1)
    exp.validate_physics_record(_physics(2), previous_index=1)
    bad_shape = _neural(); bad_shape["commanded_joint_targets"] = [0.0] * 41
    with pytest.raises(ValueError, match="42"):
        exp.validate_neural_record(bad_shape)
    bad_order = OrderedDict(reversed(tuple(_physics().items())))
    with pytest.raises(ValueError, match="inventory/order"):
        exp.validate_physics_record(bad_order)


def _accumulated_records(count=20):
    now_seconds = 0.0
    physics = []
    neural = []
    for physics_index in range(1, count + 1):
        now_seconds += 0.0001
        now_ms = now_seconds * 1000.0
        physics.append(_physics(physics_index, now_ms))
        if physics_index % 5 == 0:
            neural.append(_neural(physics_index // 5, now_ms))
    return neural, physics


def test_authentic_accumulated_clock_and_exact_sampling_are_accepted():
    neural, physics = _accumulated_records()
    assert physics[9]["physics_time_ms"] != 10 * .1
    assert neural[1]["neural_time_ms"] == physics[9]["physics_time_ms"]
    exp.validate_telemetry_clocks(neural, physics)


def test_one_ulp_neural_clock_mutation_is_rejected():
    neural, physics = _accumulated_records()
    neural[1]["neural_time_ms"] = math.nextafter(
        neural[1]["neural_time_ms"], math.inf)
    with pytest.raises(ValueError, match="exactly"):
        exp.validate_telemetry_clocks(neural, physics)


def test_wrong_physics_transition_sample_is_rejected():
    neural, physics = _accumulated_records()
    neural[1]["neural_time_ms"] = physics[10]["physics_time_ms"]
    with pytest.raises(ValueError, match="sampled physics"):
        exp.validate_telemetry_clocks(neural, physics)


@pytest.mark.parametrize("stream", ["neural", "physics"])
def test_non_contiguous_indices_are_rejected(stream):
    neural, physics = _accumulated_records()
    records = neural if stream == "neural" else physics
    records[1][f"{stream}_transition_index"] += 1
    with pytest.raises(ValueError, match="non-contiguous"):
        exp.validate_telemetry_clocks(neural, physics)


@pytest.mark.parametrize("stream", ["neural", "physics"])
def test_non_finite_timestamps_are_rejected(stream):
    neural, physics = _accumulated_records()
    records = neural if stream == "neural" else physics
    records[1][f"{stream}_time_ms"] = math.inf
    with pytest.raises(ValueError, match="non-finite"):
        exp.validate_telemetry_clocks(neural, physics)


@pytest.mark.parametrize("stream", ["neural", "physics"])
def test_non_monotonic_timestamps_are_rejected(stream):
    neural, physics = _accumulated_records()
    records = neural if stream == "neural" else physics
    records[1][f"{stream}_time_ms"] = records[0][f"{stream}_time_ms"]
    with pytest.raises(ValueError, match="strictly increasing"):
        exp.validate_telemetry_clocks(neural, physics)


def test_neural_count_must_match_available_complete_physics_groups():
    neural, physics = _accumulated_records()
    with pytest.raises(ValueError, match="count"):
        exp.validate_telemetry_clocks(neural[:-1], physics)


def test_fail_closed_provenance_and_authorization(tmp_path):
    assert len(exp.verify_design()) == 64
    bad = tmp_path / "design.json"
    bad.write_text(json.dumps({**exp.design(), "status": "RUN"}))
    with pytest.raises(RuntimeError, match="mismatch"):
        exp.verify_design(bad)
    fake = tmp_path / "prospective_execution_authorization.json"
    fake.write_text("{}")
    with pytest.raises(PermissionError, match="not authorized"):
        exp.assert_execution_authorized(fake)

    # The real prospective authorization is now valid, but authorization
    # verification alone performs zero scientific transitions.
    assert exp.assert_execution_authorized() is None


def test_result_schema_has_only_permitted_classes_and_all_outputs():
    schema = exp.result_schema()
    assert schema["status"] == "NOT_RUN"
    assert len(schema["channels"]) == 11 and schema["baseline_only_joint_count"] == 31
    assert set(sum(schema["classifications"].values(), ())) == {
        "OBSERVED_ACTIVE", "OBSERVED_INACTIVE", "DECODER_OUTPUT",
        "NO_DECODER_OUTPUT", "PHYSICALLY_DIVERGENT", "NOT_PHYSICALLY_DIVERGENT"}
    assert len(schema["channel_metrics"]) == 13


def test_tests_cannot_reach_scientific_execution(monkeypatch):
    from malecns_backend.embodiment import _windows_live_v1_motor_output_experiment_adapter as adapter

    def deny():
        raise PermissionError("synthetic test authorization denial")

    monkeypatch.setattr(exp, "assert_execution_authorized", deny)

    with pytest.raises(PermissionError, match="synthetic test"):
        adapter.execute()


def test_module_help_in_fresh_process_is_successful_and_inert():
    result = subprocess.run([sys.executable, "-m",
        "malecns_backend.embodiment.live_v1_motor_output_experiment", "--help"],
        check=False, capture_output=True, text=True)
    assert result.returncode == 0
    assert "performs zero transitions" in result.stdout


def test_runtime_observer_receives_deterministic_detached_read_only_records():
    np = pytest.importorskip("numpy")
    source = np.arange(3, dtype=np.float64)
    nested = {"first": source, "second": {"values": [1, 2]}}
    records = []
    live._observe(records.append, nested)
    source[0] = 99

    record = records[0]
    assert tuple(record) == ("first", "second")
    assert record["first"].tolist() == [0.0, 1.0, 2.0]
    assert record["second"]["values"] == (1, 2)
    with pytest.raises(ValueError):
        record["first"][0] = -1
    with pytest.raises(TypeError):
        record["second"]["values"] = ()


def test_none_observer_is_noop_and_hook_is_optional():
    class ExplosiveMapping(dict):
        def items(self):
            raise AssertionError("telemetry copied with observer disabled")

    assert live._observe(None, ExplosiveMapping()) is None
    source = Path(live.__file__).read_text()
    signature = source[source.index("def _scientific_transition_kernel("):
                       source.index(") -> Mapping[str, Any]:")]
    assert "telemetry_observer: Any | None = None" in signature


def _fake_experiment3_run(*, control=False):
    from malecns_backend.embodiment import (
        _windows_live_v1_motor_output_experiment_adapter as adapter,
    )

    names = adapter.CHANNEL_NAMES

    neural = []
    for index in range(1, 1001):
        time_ms = index * 0.5

        spikes = {name: [0, 0] for name in names}
        rates = {name: [0.0, 0.0] for name in names}
        population = {name: 0.0 for name in names}
        positive_rate = {name: 0.0 for name in names}
        negative_rate = {name: 0.0 for name in names}
        positive_activation = {name: 0.0 for name in names}
        negative_activation = {name: 0.0 for name in names}
        raw = {name: 0.0 for name in names}
        final = {name: 0.0 for name in names}
        clamped = {name: False for name in names}
        slew = {name: False for name in names}

        # Give only the first frozen channel a known synthetic signal.
        channel = names[0]

        if index == 2:
            spikes[channel] = [1, 0]
            rates[channel] = [10.0, 0.0]
            population[channel] = 5.0
            positive_rate[channel] = 10.0
            positive_activation[channel] = 0.25

        if index >= 2:
            raw[channel] = 0.1

        if index in (2, 3):
            clamped[channel] = True

        if index in (2, 3, 4):
            slew[channel] = True

        commands = [0.0] * 42

        if index >= 2 and not control:
            final[channel] = 0.05
            commands[adapter.CHANNEL_INDEX[channel]] = 0.05

        neural.append({
            "neural_transition_index": index,
            "neural_time_ms": time_ms,
            "per_neuron_spike_increments": spikes,
            "per_neuron_filtered_rate_hz": rates,
            "population_mean_filtered_rate_hz": population,
            "pooled_positive_rate_hz": positive_rate,
            "pooled_negative_rate_hz": negative_rate,
            "positive_activation": positive_activation,
            "negative_activation": negative_activation,
            "raw_signed_contribution_rad": raw,
            "final_contribution_rad": final,
            "range_clamped": clamped,
            "slew_limited": slew,
            "commanded_joint_targets": commands,
            "encoded_sensory_rates": [0.0] * 6,
            "scheduled_sensory_candidate_events": None,
            "delivered_external_sensory_events": [],
        })

    physics = []
    controlled_index = adapter.CHANNEL_INDEX[names[0]]

    for index in range(1, 5001):
        time_ms = index * 0.1
        measured = [0.0] * 42
        commands = [0.0] * 42

        # Command divergence begins at neural t=1.0 ms.
        if index >= 10 and not control:
            commands[controlled_index] = 0.05

        # Physical response divergence begins at 1.2 ms.
        if index >= 12 and not control:
            measured[controlled_index] = 0.001

        # A baseline-only joint moves identically in both conditions.
        baseline_index = adapter.BASELINE_ONLY_INDICES[0]
        if index >= 20:
            measured[baseline_index] = 0.002

        physics.append({
            "physics_transition_index": index,
            "physics_time_ms": time_ms,
            "commanded_joint_targets": commands,
            "measured_joint_positions": measured,
            "qpos": [0.0] * 49,
            "qvel": [0.0] * 48,
            "root_position": [0.0] * 3,
            "root_quaternion": [1.0, 0.0, 0.0, 0.0],
            "contact_information": [],
        })

    initial = [0.0] * 42

    return {
        "condition": (
            "matched_control_final_11_zeroed"
            if control
            else "live_v1_enabled"
        ),
        "neural": neural,
        "physics": physics,
        "runtime_result": {
            "physics_steps": 5000,
            "neural_steps": 1000,
            "physics_instability": False,
            "unauthorized_contribution_count": 0,
            "initial_physical_state_audit": {
                "joint_configuration": initial,
            },
        },
    }


def test_fake_analysis_obeys_frozen_activity_decoder_and_occupancy_rules():
    from malecns_backend.embodiment import (
        _windows_live_v1_motor_output_experiment_adapter as adapter,
    )

    run = _fake_experiment3_run(control=False)
    channel = adapter.CHANNEL_NAMES[0]

    metrics = adapter._condition_channel_metrics(
        run["neural"],
        channel,
    )

    assert metrics["first_motor_population_activity_time_ms"] == 1.0
    assert metrics["first_nonzero_decoder_output_time_ms"] == 1.0
    assert metrics["activity_classification"] == "OBSERVED_ACTIVE"
    assert metrics["decoder_classification"] == "DECODER_OUTPUT"

    assert metrics["nonzero_output_duty_fraction"] == 999 / 1000
    assert metrics["range_clamp_occupancy"] == 2 / 1000
    assert metrics["slew_limit_occupancy"] == 3 / 1000

    assert metrics["spike_increment_distribution"] == [
        {"increment": 0, "count": 1999},
        {"increment": 1, "count": 1},
    ]

    assert len(metrics["raw_contribution_distribution"]) == 1000
    assert len(metrics["final_contribution_distribution"]) == 1000
    assert len(metrics["filtered_rate_distribution"]) == 2000
    assert len(metrics["positive_negative_directional_balance"]) == 1000

    balance = metrics["positive_negative_directional_balance"][1]
    assert balance["neural_time_ms"] == 1.0
    assert balance["activation_difference"] == 0.25


def test_fake_control_preserves_decoder_activity_but_zeros_final_output():
    from malecns_backend.embodiment import (
        _windows_live_v1_motor_output_experiment_adapter as adapter,
    )

    run = _fake_experiment3_run(control=True)
    channel = adapter.CHANNEL_NAMES[0]

    metrics = adapter._condition_channel_metrics(
        run["neural"],
        channel,
    )

    # The matched control is downstream of neural activity and decoder output.
    assert metrics["first_motor_population_activity_time_ms"] == 1.0
    assert metrics["first_nonzero_decoder_output_time_ms"] == 1.0
    assert metrics["decoder_classification"] == "DECODER_OUTPUT"

    assert metrics["nonzero_output_duty_fraction"] == 0.0
    assert set(metrics["final_contribution_distribution"]) == {0.0}


def test_fake_exact_physical_divergence_and_command_response_lag():
    from malecns_backend.embodiment import (
        _windows_live_v1_motor_output_experiment_adapter as adapter,
    )

    enabled = _fake_experiment3_run(control=False)
    control = _fake_experiment3_run(control=True)

    channel = adapter.CHANNEL_NAMES[0]
    action_index = adapter.CHANNEL_INDEX[channel]

    first = adapter._first_physical_divergence(
        enabled["physics"],
        control["physics"],
        action_index,
    )
    assert first == pytest.approx(1.2)

    lag = adapter._command_response_lag(
        enabled["neural"],
        control["neural"],
        enabled["physics"],
        control["physics"],
        action_index,
    )

    assert lag["first_command_divergence_time_ms"] == 1.0
    assert lag["first_measured_response_divergence_time_ms"] == pytest.approx(1.2)
    assert lag["command_to_measured_response_lag_ms"] == pytest.approx(0.2)


def test_fake_channel_result_classifies_exact_physical_divergence():
    from malecns_backend.embodiment import (
        _windows_live_v1_motor_output_experiment_adapter as adapter,
    )

    enabled = _fake_experiment3_run(control=False)
    control = _fake_experiment3_run(control=True)

    results = adapter._channel_results(enabled, control)
    first = adapter.CHANNEL_NAMES[0]
    second = adapter.CHANNEL_NAMES[1]

    assert results[first]["enabled_control_physical_divergence"] is True
    assert results[first]["physics_classification"] == "PHYSICALLY_DIVERGENT"
    assert results[first]["first_physical_divergence_time_ms"] == pytest.approx(1.2)

    assert results[second]["enabled_control_physical_divergence"] is False
    assert results[second]["physics_classification"] == "NOT_PHYSICALLY_DIVERGENT"
    assert results[second]["first_physical_divergence_time_ms"] is None


def test_fake_baseline_only_joint_report_is_descriptive_and_complete():
    from malecns_backend.embodiment import (
        _windows_live_v1_motor_output_experiment_adapter as adapter,
    )

    enabled = _fake_experiment3_run(control=False)
    control = _fake_experiment3_run(control=True)

    report = adapter._passive_motion_report(enabled, control)

    assert report["joint_count"] == 31
    assert len(report["joints"]) == 31

    first = report["joints"][0]
    assert first["action_index"] == adapter.BASELINE_ONLY_INDICES[0]

    for condition in (
        "live_v1_enabled",
        "matched_control_final_11_zeroed",
    ):
        values = first["conditions"][condition]
        assert values["initial_position"] == 0.0
        assert values["maximum_measured_position"] == 0.002
        assert values["final_measured_position"] == 0.002
        assert values["net_change_from_initial"] == 0.002
        assert values["ever_changed_from_initial_exactly"] is True

    # It moved, but identically, so it is not an enabled/control divergence.
    assert first["first_enabled_control_exact_divergence_time_ms"] is None


def test_fake_pairing_rejects_transition_index_mismatch():
    from malecns_backend.embodiment import (
        _windows_live_v1_motor_output_experiment_adapter as adapter,
    )

    enabled = _fake_experiment3_run(control=False)
    control = _fake_experiment3_run(control=True)

    control["physics"][100]["physics_transition_index"] += 1

    with pytest.raises(RuntimeError, match="paired physics index mismatch"):
        adapter._verify_pairing(enabled, control)


def test_result_writer_is_deterministic_and_exclusive(tmp_path):
    path = tmp_path / "result.json"
    result = {
        "schema": "LIVE-V1-MOTOR-OUTPUT-RESULT.1",
        "status": "SYNTHETIC_TEST_ONLY",
        "value": 1.25,
    }

    receipt = exp.write_result_exclusive(result, path)

    expected = exp.canonical_json(result).encode("utf-8")

    import hashlib

    assert path.read_bytes() == expected
    assert receipt["path"] == path.as_posix()
    assert receipt["size_bytes"] == len(expected)
    assert receipt["sha256"] == hashlib.sha256(expected).hexdigest()

    before = path.read_bytes()

    with pytest.raises(FileExistsError, match="canonical result already exists"):
        exp.write_result_exclusive(
            {"status": "SHOULD_NOT_OVERWRITE"},
            path,
        )

    assert path.read_bytes() == before


def test_preexisting_result_fails_closed(tmp_path):
    path = tmp_path / "existing_result.json"
    path.write_text('{"preserved": true}\n', encoding="utf-8")

    before = path.read_bytes()

    with pytest.raises(FileExistsError, match="canonical result already exists"):
        exp.assert_result_available(path)

    assert path.read_bytes() == before


def test_missing_result_path_is_available(tmp_path):
    path = tmp_path / "not_created.json"

    assert exp.assert_result_available(path) is None
    assert not path.exists()


def test_execution_attempt_marker_is_deterministic_and_exclusive(tmp_path):
    path = tmp_path / "attempt.json"
    provenance = {
        "design_sha256": "a" * 64,
        "execution_contract_sha256": "b" * 64,
    }

    receipt = exp.claim_execution_attempt(provenance, path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "LIVE-V1-MOTOR-OUTPUT-EXECUTION-ATTEMPT.1"
    assert payload["status"] == "EXECUTION_ATTEMPT_CLAIMED"
    assert payload["provenance"] == provenance
    assert payload["result_path"] == exp.RESULT_PATH.name

    expected = exp.canonical_json(payload).encode("utf-8")

    import hashlib

    assert path.read_bytes() == expected
    assert receipt["path"] == path.as_posix()
    assert receipt["size_bytes"] == len(expected)
    assert receipt["sha256"] == hashlib.sha256(expected).hexdigest()

    before = path.read_bytes()

    with pytest.raises(FileExistsError, match="execution attempt already claimed"):
        exp.claim_execution_attempt(
            {"design_sha256": "SHOULD_NOT_REPLACE"},
            path,
        )

    assert path.read_bytes() == before


def test_unauthorized_execute_cannot_claim_attempt(monkeypatch, tmp_path):
    from malecns_backend.embodiment import (
        _windows_live_v1_motor_output_experiment_adapter as adapter,
    )

    attempt = tmp_path / "attempt.json"

    monkeypatch.setattr(exp, "ATTEMPT_PATH", attempt)

    def deny():
        raise PermissionError("synthetic test authorization denial")

    monkeypatch.setattr(exp, "assert_execution_authorized", deny)

    with pytest.raises(PermissionError, match="synthetic test"):
        adapter.execute()

    assert not attempt.exists()
