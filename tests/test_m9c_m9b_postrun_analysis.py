"""M9C unit tests use synthetic evidence and execute no scientific simulation."""
import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

from malecns_backend.embodiment import m9b_external_perturbation as m9b
from malecns_backend.embodiment import m9c_m9b_postrun_analysis as m9c


def test_import_is_inert_and_zero_transition(monkeypatch):
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("import loaded evidence"))
    module = importlib.reload(m9c)
    assert module.PHYSICS_TRANSITIONS == module.NEURAL_TRANSITIONS == 0
    assert "flygym" not in module.__dict__ and "mujoco" not in module.__dict__


def test_factorial_arithmetic_and_boolean_contacts():
    arrays = {}
    for c, value in zip(m9b.CONDITIONS, (9, 3, 5, 4)):
        arrays[f"{c}__x"] = np.array([[value, value + 1.]])
    result = m9c.factorial(arrays, "x")
    assert np.array_equal(result["delta_A"], [[6, 6]])
    assert np.array_equal(result["delta_B"], [[1, 1]])
    assert np.array_equal(result["interaction"], [[5, 5]])
    for c, value in zip(m9b.CONDITIONS, (True, False, True, True)):
        arrays[f"{c}__contact"] = np.array([[value]])
    assert m9c.factorial(arrays, "contact")["interaction"].item() == 1


def test_quaternion_shortest_arc_sign_invariance():
    identity = np.array([[1., 0, 0, 0]])
    assert m9c.quaternion_shortest_arc(identity, -identity).item() == 0
    quarter = np.array([[np.sqrt(.5), 0, 0, np.sqrt(.5)]])
    assert m9c.quaternion_shortest_arc(identity, quarter).item() == pytest.approx(np.pi / 2)


def test_first_divergence_respects_analysis_boundary():
    t = np.array([499.9, 500., 500.1, 500.2])
    x = np.array([[1, 0], [0, 0], [0, 0], [0, -1]])
    assert m9c.first_divergence(x, t) == 500.2
    assert m9c.first_divergence(np.zeros(4), t) is None


def _forces():
    arrays = {}
    expected = np.zeros((15000, 3)); expected[5000:5200, 1] = 1.024
    for c in m9b.CONDITIONS:
        arrays[f"{c}__physics_external_force"] = expected.copy() if c.endswith("P") else np.zeros_like(expected)
    return arrays


def test_exact_force_schedule_and_fail_closed_mutation():
    arrays = _forces()
    result = m9c.verify_force_integrity(arrays)
    assert result["active_transition_indices"] == [5000, 5199]
    assert result["nonzero_transitions_per_perturbed_condition"] == 200
    assert m9c.verify_force_integrity(arrays)["first_potentially_affected_state"] == 5001
    arrays["A_P__physics_external_force"][5199, 1] = 0
    with pytest.raises(RuntimeError, match="force schedule"): m9c.verify_force_integrity(arrays)


def test_disabled_post_zero_audit_and_processing_activity():
    arrays = {}
    required = ("neural_time_ms", "neural_sensory_encoded", "neural_delivered_drive_count",
                "neural_aggregate_spikes", "neural_observer_outputs", "neural_decoder_outputs")
    for c in ("B_P", "B_C"):
        arrays[f"{c}__neural_motor_pre_zero"] = np.ones((3000, 11))
        arrays[f"{c}__neural_motor_post_zero"] = np.zeros((3000, 11))
        for field in required: arrays[f"{c}__{field}"] = np.zeros((3000,))
    assert all(x["post_zero_exactly_zero"] for x in m9c.audit_disabled(arrays).values())
    arrays["B_P__neural_motor_post_zero"][2, 1] = 1
    with pytest.raises(RuntimeError, match="post-zero"): m9c.audit_disabled(arrays)


def test_contact_summary_reports_signed_per_leg_difference():
    arrays = {}
    for c in m9b.CONDITIONS:
        arrays[f"{c}__contact"] = np.zeros((4, 6), bool)
    arrays["A_P__contact"][2:, 0] = True
    out = m9c._contrast_summaries(arrays, "contact", np.array([500., 520., 750., 1500.]), m9c.LEGS)
    assert out["delta_A"]["channels"]["LF"]["first_detectable_divergence_ms"] == 750
    assert out["delta_A"]["channels"]["LF"]["at_1500_ms"]["value"] == 1


def test_output_namespace_protection(tmp_path):
    output = tmp_path / "existing"; output.mkdir()
    with pytest.raises(RuntimeError, match="already exists"): m9c.analyze(tmp_path, output)


def test_conservative_classification_rules():
    assert m9c.classify(False, False)["supported"] == [m9b.CLASSIFICATIONS[0]]
    assert m9c.classify(True, False)["primary"] == m9b.CLASSIFICATIONS[2]
    nested = m9c.classify(True, True)
    assert nested["supported"] == [m9b.CLASSIFICATIONS[1], m9b.CLASSIFICATIONS[2]]
    assert not any(word in json.dumps(nested).lower() for word in ("balance", "righting", "gait", "cpg"))


def test_canonical_provenance_validation_without_loading_npz():
    if (m9c.SOURCE_DIR / "m9b_raw.npz").read_bytes().startswith(b"version https://git-lfs"):
        pytest.skip("canonical raw evidence is an unmaterialized Git LFS pointer")
    evidence = m9c.validate_provenance()
    assert evidence["report"]["status"] == "COMPLETE_UNCLASSIFIED"
    assert evidence["preregistration"]["design"]["conditions"] == list(m9b.CONDITIONS)


def test_provenance_rejects_report_mutation(tmp_path):
    source = m9c.SOURCE_DIR
    for name in ("m9b_raw.npz", "m9b_report.json", "m9b_manifest.json", "m9b_preregistration.json"):
        (tmp_path / name).write_bytes((source / name).read_bytes())
    report = json.loads((tmp_path / "m9b_report.json").read_text())
    report["status"] = "COMPLETE"
    (tmp_path / "m9b_report.json").write_text(json.dumps(report))
    with pytest.raises(RuntimeError, match="provenance"): m9c.validate_provenance(tmp_path)


def _schema_arrays():
    """Make a low-memory, shape-faithful view of every recorded M9B field."""
    arrays = {}
    for condition in m9b.CONDITIONS:
        for field, shape in m9c.M9B_RECORDED_SHAPES.items():
            if field == "physics_time_ms":
                value = np.arange(15001, dtype=float) * .1
            elif field == "neural_time_ms":
                value = np.arange(1, 3001, dtype=float) * .5
            else:
                value = np.broadcast_to(np.zeros((), dtype=float), shape)
            arrays[f"{condition}__{field}"] = value
    return arrays


def _recorder_physics_clock():
    """Synthetic MuJoCo-style clock: repeated seconds additions, then ms."""
    result = np.empty(15001, dtype=np.float64)
    now_s = np.float64(0.0)
    for index in range(result.size):
        result[index] = now_s * 1000.0
        now_s += np.float64(0.0001)
    return result


def test_recorder_and_alternate_float_timestamp_expressions_pass():
    recorder = _schema_arrays()
    physics = _recorder_physics_clock()
    for condition in m9b.CONDITIONS:
        recorder[f"{condition}__physics_time_ms"] = physics.copy()
        recorder[f"{condition}__neural_time_ms"] = physics[5::5].copy()
    m9c._validate_arrays(recorder)

    # Independent index multiplication is mathematically identical but not
    # byte-identical to MuJoCo's repeatedly advanced binary64 clock.
    alternate = _schema_arrays()
    assert not np.array_equal(physics, alternate["A_P__physics_time_ms"])
    assert not np.array_equal(physics[5::5], alternate["A_P__neural_time_ms"])
    m9c._validate_arrays(alternate)


@pytest.mark.parametrize(("field", "mutation", "message"), [
    ("physics_time_ms", lambda x: x.__setitem__(7000, x[7000] + 1e-6), "index cadence"),
    ("physics_time_ms", lambda x: x.__setitem__(slice(None), np.arange(x.size) * .11), "endpoint"),
    ("physics_time_ms", lambda x: x.__setitem__(0, .1), "origin"),
    ("physics_time_ms", lambda x: x.__setitem__(100, x[99]), "strictly monotonic"),
    ("physics_time_ms", lambda x: x.__setitem__(100, x[99] - .1), "strictly monotonic"),
    ("neural_time_ms", lambda x: x.__setitem__(0, 0.), "origin"),
])
def test_timestamp_cadence_mutations_fail_closed(field, mutation, message):
    arrays = _schema_arrays()
    value = arrays[f"A_P__{field}"].copy()
    mutation(value)
    arrays[f"A_P__{field}"] = value
    with pytest.raises(RuntimeError, match=message):
        m9c._validate_arrays(arrays)


@pytest.mark.parametrize("field", ("physics_time_ms", "neural_time_ms"))
def test_timestamp_wrong_sample_count_fails(field):
    arrays = _schema_arrays()
    arrays[f"A_P__{field}"] = arrays[f"A_P__{field}"][:-1]
    with pytest.raises(RuntimeError, match=field):
        m9c._validate_arrays(arrays)


def test_timestamp_dtype_must_remain_binary64():
    arrays = _schema_arrays()
    arrays["A_P__physics_time_ms"] = arrays["A_P__physics_time_ms"].astype(np.float32)
    with pytest.raises(RuntimeError, match="dtype"):
        m9c._validate_arrays(arrays)


def test_authoritative_model_nq_and_nv_are_independent_and_accepted():
    manifest = json.loads((m9c.SOURCE_DIR / "m9b_manifest.json").read_text(encoding="utf-8"))
    runtimes = manifest["preflight"]["corrected_initialization_diagnostics"]["runtimes"]
    assert {(len(x["state_zero"]["qpos"]), len(x["state_zero"]["qvel"]))
            for x in runtimes} == {(94, 93)}
    arrays = _schema_arrays()
    m9c._validate_arrays(arrays)
    assert m9c.M9B_RECORDED_SHAPES["physics_qpos"] == (15001, 94)
    assert m9c.M9B_RECORDED_SHAPES["physics_qvel"] == (15001, 93)


@pytest.mark.parametrize(("field", "wrong_width"),
                         (("physics_qpos", 93), ("physics_qvel", 94)))
def test_qpos_and_qvel_wrong_dimensions_fail_independently(field, wrong_width):
    arrays = _schema_arrays()
    arrays[f"A_P__{field}"] = np.broadcast_to(0., (15001, wrong_width))
    with pytest.raises(RuntimeError, match=field):
        m9c._validate_arrays(arrays)


def test_complete_recorder_contract_and_each_malformed_dimension_fail_closed():
    expected = {
        # CompactTelemetry physics fields.
        "physics_time_ms", "physics_qpos", "physics_qvel", "physics_joint_position",
        "physics_action", "physics_ctrl", "physics_body_position", "physics_body_orientation",
        "physics_contact_forces", "physics_finite",
        # M8/M9B extended physics and all neural fields.
        "physics_tarsal_contact", "physics_tarsus5_world_position", "physics_body_up_vector",
        "physics_fall_rollover", "physics_external_force", "neural_time_ms",
        "neural_sensory_encoded", "neural_delivered_drive_count", "neural_aggregate_spikes",
        "neural_observer_outputs", "neural_decoder_outputs", "neural_admitted_contributions",
        "neural_motor_pre_zero", "neural_motor_post_zero",
    }
    assert set(m9c.M9B_RECORDED_SHAPES) == expected
    baseline = _schema_arrays()
    m9c._validate_arrays(baseline)
    for field, shape in m9c.M9B_RECORDED_SHAPES.items():
        malformed = dict(baseline)
        malformed[f"A_P__{field}"] = np.zeros((*shape[:-1], shape[-1] + 1))
        with pytest.raises(RuntimeError, match=field):
            m9c._validate_arrays(malformed)


def test_validation_failure_precedes_output_publication(tmp_path, monkeypatch):
    arrays = _schema_arrays()
    arrays["A_P__physics_qvel"] = np.zeros((15001, 48))
    output = tmp_path / "m9c"
    monkeypatch.setattr(m9c, "validate_provenance", lambda source: {})
    monkeypatch.setattr(m9c, "_load_raw", lambda path: arrays)
    with pytest.raises(RuntimeError, match="physics_qvel"):
        m9c.analyze(tmp_path, output)
    assert not output.exists()
    assert m9c.PHYSICS_TRANSITIONS == m9c.NEURAL_TRANSITIONS == 0


def test_cadence_failure_precedes_output_publication(tmp_path, monkeypatch):
    arrays = _schema_arrays()
    arrays["A_P__physics_time_ms"] = arrays["A_P__physics_time_ms"].copy()
    arrays["A_P__physics_time_ms"][42] += 1e-6
    output = tmp_path / "m9c"
    monkeypatch.setattr(m9c, "validate_provenance", lambda source: {})
    monkeypatch.setattr(m9c, "_load_raw", lambda path: arrays)
    with pytest.raises(RuntimeError, match="physics cadence"):
        m9c.analyze(tmp_path, output)
    assert not output.exists()
