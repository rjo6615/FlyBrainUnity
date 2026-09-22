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
