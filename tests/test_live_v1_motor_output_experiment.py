import importlib
import json
import subprocess
import sys
from collections import OrderedDict

import pytest

from malecns_backend.embodiment import live_v1_motor_output_experiment as exp


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


def test_no_decoder_equation_or_runtime_file_changes_are_required():
    design = exp.design()
    assert "decoder change" in design["prohibitions"]
    assert exp.readiness()["existing_runtime_hook_added"] is False


def _neural(index=1):
    values = [index, index * .5, [[0]], [[0.0]], [0.0] * 11, [0.0] * 11,
              [0.0] * 11, [0.0] * 11, [0.0] * 11, [0.0] * 11,
              [0.0] * 11, [False] * 11, [False] * 11, [0.0] * 42,
              [0.0] * 6, None, []]
    return OrderedDict(zip(exp.NEURAL_FIELDS, values))


def _physics(index=1):
    values = [index, index * .1, [0.0] * 42, [0.0] * 42, [0.0] * 49,
              [0.0] * 48, [0.0] * 3, [1.0, 0.0, 0.0, 0.0], []]
    return OrderedDict(zip(exp.PHYSICS_FIELDS, values))


def test_telemetry_validation_is_passive_and_cadence_exact():
    neural = _neural(); physics = _physics()
    before = json.dumps([neural, physics])
    exp.validate_neural_record(neural)
    exp.validate_physics_record(physics)
    assert json.dumps([neural, physics]) == before
    exp.validate_neural_record(_neural(2), previous_index=1)
    exp.validate_physics_record(_physics(2), previous_index=1)
    bad = _neural(2); bad["neural_time_ms"] = 1.1
    with pytest.raises(ValueError, match="cadence"):
        exp.validate_neural_record(bad, previous_index=1)


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
