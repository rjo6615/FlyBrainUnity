"""Regression contracts for M7-A; these tests never execute science."""
import ast
import io
from pathlib import Path

import pytest

from malecns_backend.embodiment import m7_spontaneous_locomotion as m7
from malecns_backend.embodiment import _windows_m7_spontaneous_locomotion_adapter as adapter
from malecns_backend.embodiment import m7_telemetry as telemetry
from malecns_backend.embodiment.integrated_whole_leg_readiness import EQUIVALENCE_FIELDS
from malecns_backend.embodiment.isolated_tier_b_motor_validation import (
    DECODER_MAX_RAD, HALF_ACTIVATION_HZ, OBSERVER_TAU_MS, SLEW_RAD_S,
)


def test_frozen_scientific_contract_and_parameters():
    assert (m7.SEED, m7.DURATION_MS) == (1, 5000)
    assert (m7.PHYSICS_DT_MS, m7.NEURAL_DT_MS) == (0.1, 0.5)
    assert (m7.EXPECTED_PHYSICS_TRANSITIONS, m7.EXPECTED_NEURAL_UPDATES) == (50000, 10000)
    assert m7.CONDITIONS == ("SPONTANEOUS_NEURAL_EMBODIMENT", "ALL_NEURAL_MOTOR_DISABLED")
    assert len(m7.ADMITTED_MOTOR) == 11 and len(m7.ADMITTED_SENSORY) == 6
    assert m7.ADMITTED_SENSORY == m7.ADMITTED_MOTOR[:6]
    assert m7.build_not_run()["baseline_only_actuator_count"] == 31
    assert (OBSERVER_TAU_MS, HALF_ACTIVATION_HZ, DECODER_MAX_RAD, SLEW_RAD_S) == (40.0, 17.0, 0.25, 4.0)
    assert tuple(m7.build_not_run()["equivalence_fields"]) == EQUIVALENCE_FIELDS


def test_motor_disabled_is_the_only_gate_difference():
    values = dict.fromkeys(m7.ADMITTED_MOTOR, 0.125)
    assert adapter.gate_contributions(values, m7.CONDITIONS[0], m7.ADMITTED_MOTOR) == values
    assert set(adapter.gate_contributions(values, m7.CONDITIONS[1], m7.ADMITTED_MOTOR).values()) == {0.0}
    with pytest.raises(RuntimeError): adapter.gate_contributions({}, m7.CONDITIONS[0], m7.ADMITTED_MOTOR)


def test_outputs_are_exclusive_and_abort_is_not_a_result(tmp_path):
    path = tmp_path / "value.json"
    m7.write_json_exclusive(path, {"ok": True})
    with pytest.raises(FileExistsError): m7.write_json_exclusive(path, {"ok": False})
    aborted = m7.write_aborted(tmp_path, RuntimeError("engineering"), 0, 1.0)
    assert aborted.name.startswith("ABORTED_IMPLEMENTATION_")
    assert '"classification": null' in aborted.read_text()


def test_telemetry_schema_abort_has_specific_status_and_details(tmp_path):
    error = telemetry.TelemetrySchemaError("neural_sensory_encoded", (6,), (6, "ragged"), 0, 0.5)
    aborted = m7.write_aborted(tmp_path, error, 0, 1.0)
    payload = __import__("json").loads(aborted.read_text())
    assert payload["run_status"] == "ABORTED_IMPLEMENTATION_TELEMETRY_SCHEMA_FAILURE"
    assert payload["classification"] is None
    assert payload["telemetry_schema_failure"] == {"field": "neural_sensory_encoded",
        "expected_shape": [6], "observed_shape": [6, "ragged"], "sample_index": 0,
        "simulation_time_ms": 0.5}


def test_fail_closed_rules_and_thresholds_are_frozen():
    required = ("canonical M6C lock mismatch", "protocol mismatch", "interface mismatch",
        "pre-intervention equivalence failure", "unauthorized actuator contribution",
        "hidden locomotion controller detected", "unexpected dynamic adhesion assistance",
        "telemetry corruption", "incomplete condition", "wrong physics transition count",
        "wrong neural update count")
    assert all(item in m7.FAIL_CLOSED for item in required)
    assert m7.THRESHOLDS == {"joint_divergence_rad": 1e-6, "com_displacement_m": 1e-6,
        "orientation_divergence_rad": 1e-6, "height_divergence_m": 1e-6,
        "oscillation_prominence_rad": 1e-4, "oscillation_min_extrema": 3,
        "rollover_body_up_z_max": 0.0, "fall_height_fraction": 0.5}


def test_no_environment_construction_inside_physics_loop():
    source = Path(adapter.__file__).with_name("_windows_m6c_live_condition.py").read_text()
    tree = ast.parse(source)
    loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While))]
    forbidden = {"_make_live", "enumerate_live_actuators", "load_malecns"}
    assert not any(isinstance(call.func, ast.Name) and call.func.id in forbidden
                   for loop in loops for call in ast.walk(loop) if isinstance(call, ast.Call))


def test_reducer_is_control_relative_and_never_claims_walking():
    np = pytest.importorskip("numpy")
    nphysics, nneural = 4, 2
    base = {"physics_qpos": np.zeros((nphysics, 49)), "physics_qvel": np.zeros((nphysics, 48)),
        "physics_joint_position": np.zeros((nphysics, 42)), "physics_body_position": np.zeros((nphysics, 3)),
        "physics_body_orientation": np.zeros((nphysics, 4)), "physics_contact_forces": np.zeros((nphysics, 36, 3)),
        "neural_aggregate_spikes": np.zeros(nneural, dtype=int),
        "neural_admitted_contributions": np.zeros((nneural, 11)),
        "neural_sensory_encoded": np.zeros((nneural, 6))}
    base["physics_body_orientation"][:, 0] = 1
    table = [{"action_index": i, "leg": ("LF", "LM", "LH", "RF", "RM", "RH")[i % 6],
              "neural_motor_admission": i < 11} for i in range(42)]
    results = {name: {"raw_arrays": {key: value.copy() for key, value in base.items()}} for name in m7.CONDITIONS}
    summary = m7.reduce_results(results, table)
    assert summary["movement_categories"] == ["NO_MEASURABLE_NEURAL_PHYSICAL_EFFECT"]
    assert summary["walking"] is None


def _schema():
    return telemetry.build_schema(qpos_shape=(97,), qvel_shape=(93,), ctrl_shape=(42,),
        contact_forces_shape=(30, 3))


def test_exact_old_heterogeneous_sensory_value_reproduces_numpy_failure():
    np = pytest.importorskip("numpy")
    sizes = (23, 80, 93, 13, 83, 100)
    sample = [tuple(float(i) for i in range(size)) for size in sizes]
    old_samples = [sample] * telemetry.NEURAL_SAMPLES
    with pytest.raises(ValueError, match=r"detected shape was \(10000, 6\)"):
        np.asarray(old_samples)


def test_repaired_sensory_representation_preserves_six_interface_peaks():
    np = pytest.importorskip("numpy")
    sizes = (23, 80, 93, 13, 83, 100)
    old_value = [np.arange(size, dtype=np.float64) for size in sizes]
    repaired = telemetry.sensory_channel_peaks(old_value)
    assert repaired.shape == (6,) and repaired.dtype == np.float64
    np.testing.assert_array_equal(repaired, np.asarray(sizes, dtype=np.float64) - 1)
    # Invalid channel structure is rejected, not flattened, padded, or truncated.
    with pytest.raises(ValueError, match="exactly six"):
        telemetry.sensory_channel_peaks(old_value[:-1])
    with pytest.raises(ValueError, match="nonempty finite rate vector"):
        telemetry.sensory_channel_peaks(old_value[:-1] + [np.ones((2, 2))])


def test_all_fields_have_explicit_numeric_schema_and_frozen_capacities():
    np = pytest.importorskip("numpy")
    schema = _schema()
    assert len(schema) == 17
    assert all(field.sample_shape is not None and field.dtype != object for field in schema.values())
    assert schema["neural_sensory_encoded"].sample_shape == (6,)
    for name in ("neural_observer_outputs", "neural_decoder_outputs", "neural_admitted_contributions"):
        assert schema[name].sample_shape == (11,)
    assert telemetry.PHYSICS_TRANSITIONS == 50_000
    assert telemetry.PHYSICS_STATE_SAMPLES == 50_001  # initial state + 50,000 transitions
    assert telemetry.NEURAL_SAMPLES == 10_000
    compact = telemetry.CompactTelemetry(schema, physics_capacity=2, neural_capacity=2)
    assert all(array.dtype != np.dtype(object) for array in compact.arrays.values())


def test_shape_mismatch_fails_on_assignment_with_index_and_time():
    compact = telemetry.CompactTelemetry(_schema(), physics_capacity=1, neural_capacity=1)
    neural = {name: __import__("numpy").zeros(field.sample_shape, dtype=field.dtype)
              for name, field in _schema().items() if field.cadence == "neural"}
    neural["neural_sensory_encoded"] = [1.0] * 5
    with pytest.raises(telemetry.TelemetrySchemaError) as caught:
        compact.record("neural", neural, 12.5)
    assert caught.value.field == "neural_sensory_encoded"
    assert caught.value.expected_shape == (6,)
    assert caught.value.observed_shape == (5,)
    assert caught.value.sample_index == 0 and caught.value.simulation_time_ms == 12.5
    assert compact.counts["neural"] == 0


def test_full_schema_npz_roundtrip_needs_no_pickle_and_preserves_contract():
    np = pytest.importorskip("numpy")
    schema = _schema(); arrays = telemetry.roundtrip_minimal(schema)
    assert set(arrays) == set(schema)
    assert all(value.dtype == schema[name].dtype and value.dtype != object and
               value.shape == (1, *schema[name].sample_shape) for name, value in arrays.items())
    stream = io.BytesIO(); np.savez_compressed(stream, **arrays); stream.seek(0)
    with np.load(stream, allow_pickle=False) as loaded:
        assert set(loaded.files) == set(schema)


def test_v3_preflight_validates_actual_schema_and_zero_transitions(tmp_path, monkeypatch):
    schema_report = {name: {"sample_shape": list(field.sample_shape), "dtype": str(field.dtype),
        "cadence": field.cadence, "meaning": field.meaning} for name, field in _schema().items()}
    protocol = {"actuator_admission_table": []}
    monkeypatch.setattr(adapter, "build_live_protocol", lambda: protocol)
    monkeypatch.setattr(adapter, "_inventory", lambda value: ((), ()))
    calls = []
    def runner(**kwargs):
        calls.append(kwargs)
        return {"physics_steps": 0, "neural_steps": 0,
            "pre_intervention_state": {"same": True},
            "initial_physical_state_audit": {"adhesion_enabled": False,
                "locomotion_or_reference_controller": False},
            "telemetry_schema": schema_report, "telemetry_npz_roundtrip": True,
            "telemetry_object_dtype": False}
    monkeypatch.setattr(adapter.m6c, "pre_intervention_equivalent", lambda *states: True)
    report = adapter.run_preflight(tmp_path / "v3.json", runner=runner)
    assert len(calls) == 2 and all(call["initialize_only"] for call in calls)
    assert report["schema"] == "M7-PREFLIGHT.3" and report["scientific_transitions"] == 0
    assert report["checks"]["zero_sim_steps"] and report["checks"]["zero_brain_steps"]
    assert report["checks"]["telemetry_npz_roundtrip_allow_pickle_false"]


def test_m6c_default_path_signature_remains_noncompact():
    source = Path(adapter.__file__).with_name("_windows_m6c_live_condition.py").read_text()
    tree = ast.parse(source)
    run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_condition")
    defaults = dict(zip((arg.arg for arg in run.args.kwonlyargs[-4:]), run.args.kw_defaults[-4:]))
    assert isinstance(defaults["compact_telemetry"], ast.Constant)
    assert defaults["compact_telemetry"].value is False
