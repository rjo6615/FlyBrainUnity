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
    with pytest.raises(PermissionError, match="not authorized"):
        exp.main(["--execute"])


def test_result_schema_has_only_permitted_classes_and_all_outputs():
    schema = exp.result_schema()
    assert schema["status"] == "NOT_RUN"
    assert len(schema["channels"]) == 11 and schema["baseline_only_joint_count"] == 31
    assert set(sum(schema["classifications"].values(), ())) == {
        "OBSERVED_ACTIVE", "OBSERVED_INACTIVE", "DECODER_OUTPUT",
        "NO_DECODER_OUTPUT", "PHYSICALLY_DIVERGENT", "NOT_PHYSICALLY_DIVERGENT"}
    assert len(schema["channel_metrics"]) == 13


def test_tests_cannot_reach_scientific_execution():
    from malecns_backend.embodiment import _windows_live_v1_motor_output_experiment_adapter as adapter
    with pytest.raises(PermissionError):
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
