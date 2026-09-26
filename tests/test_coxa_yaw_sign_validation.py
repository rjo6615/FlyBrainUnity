import copy
import json

import pytest

from malecns_backend.embodiment import coxa_yaw_sign_validation as validation
from malecns_backend.embodiment.motor_population_inventory import ADMITTED


EXPECTED = (
    ("LF", "joint_LFCoxa_yaw", 2), ("LM", "joint_LMCoxa_yaw", 9),
    ("LH", "joint_LHCoxa_yaw", 16), ("RF", "joint_RFCoxa_yaw", 23),
    ("RM", "joint_RMCoxa_yaw", 30), ("RH", "joint_RHCoxa_yaw", 37),
)


def test_exact_six_targets_and_authoritative_population_identity():
    assert validation.TARGETS == EXPECTED
    rows = validation._validate_population_identity()
    assert len(rows) == 6
    assert all("anterior" in row["anterior_population"] for row in rows)
    assert all("posterior" in row["posterior_population"] for row in rows)


@pytest.mark.parametrize("rows", [EXPECTED[:-1], EXPECTED + (("XX", "extra", 41),),
    EXPECTED[:-1] + (EXPECTED[0],), tuple(reversed(EXPECTED))])
def test_missing_extra_duplicate_or_reordered_targets_rejected(rows):
    with pytest.raises(RuntimeError, match="six-target freeze"):
        validation.validate_targets(rows)


def test_action_vector_has_42_entries_and_only_target_nonzero():
    for _, _, index in EXPECTED:
        vector = validation.isolated_action(index, validation.EPSILON_RAD)
        assert len(vector) == 42
        assert [i for i, value in enumerate(vector) if value] == [index]
    with pytest.raises(ValueError):
        validation.isolated_action(5, 0.1)


def test_positive_and_negative_action_prescriptions_are_symmetric():
    for _, _, index in EXPECTED:
        plus = validation.isolated_action(index, validation.EPSILON_RAD)
        minus = validation.isolated_action(index, -validation.EPSILON_RAD)
        assert all(a == -b for a, b in zip(plus, minus))


def _passing_evidence():
    return {joint: {"action_isolation": True, "fresh_baseline_identical": True,
        "neural_transitions": 0, "stimulation": False, "extra_force": False,
        "positive": {"joint_delta_rad": validation.EPSILON_RAD,
                     "axis_projection_rad": validation.EPSILON_RAD,
                     "endpoint_displacement_from_baseline": [0.01, 0.02, 0.0]},
        "negative": {"joint_delta_rad": -validation.EPSILON_RAD,
                     "axis_projection_rad": -validation.EPSILON_RAD,
                     "endpoint_displacement_from_baseline": [-0.01, -0.02, 0.0]}}
        for _, joint, _ in EXPECTED}


def test_symmetry_opposition_and_deterministic_anatomical_boundary():
    evidence = _passing_evidence()
    expected = "MECHANICAL_DIRECTION_RESOLVED_ANATOMICAL_SIGN_UNRESOLVED"
    assert validation.classify(evidence) == expected
    assert validation.classify(copy.deepcopy(evidence)) == expected
    evidence[EXPECTED[0][1]]["negative"]["axis_projection_rad"] *= -1
    assert validation.classify(evidence) == "MECHANICAL_VALIDATION_FAILED"


@pytest.mark.parametrize("field,value", [("fresh_baseline_identical", False),
    ("neural_transitions", 1), ("stimulation", True), ("extra_force", True),
    ("action_isolation", False)])
def test_identity_neural_stimulation_force_and_isolation_fail_closed(field, value):
    evidence = _passing_evidence(); evidence[EXPECTED[2][1]][field] = value
    assert validation.classify(evidence) == "MECHANICAL_VALIDATION_FAILED"


def test_frozen_preregistration_lf_and_crlf_hash_and_not_run_status(tmp_path):
    value = validation.verify_preregistration()
    assert value["status"] == "NOT_RUN"
    assert validation.PREREGISTRATION_SHA256 == "dcf1b4419f8d0bd7cd65979ad2da3084db5482cf906b3e40217836335c563254"
    original = validation.PREREGISTRATION_PATH.read_bytes()
    assert validation.preregistration_sha256(validation.PREREGISTRATION_PATH) == validation.PREREGISTRATION_SHA256
    crlf = tmp_path / "crlf.json"
    crlf.write_bytes(original.replace(b"\n", b"\r\n"))
    assert validation.verify_preregistration(crlf) == value
    changed = tmp_path / "changed.json"
    changed.write_bytes(original + b" ")
    with pytest.raises(RuntimeError, match="SHA-256"):
        validation.verify_preregistration(changed)


def test_preregistration_hash_normalization_is_limited_to_crlf(tmp_path):
    original = validation.PREREGISTRATION_PATH.read_bytes()
    lone_cr = tmp_path / "lone-cr.json"
    lone_cr.write_bytes(original.replace(b"\n", b"\r", 1))
    assert validation.preregistration_sha256(lone_cr) != validation.PREREGISTRATION_SHA256
    with pytest.raises(RuntimeError, match="SHA-256"):
        validation.verify_preregistration(lone_cr)


def test_preflight_is_zero_transition_and_interface_remains_11():
    result = validation.preflight()
    assert result["scientific_run_executed"] is False
    assert result["physics_transitions"] == result["neural_transitions"] == 0
    assert result["stimulation"] is result["extra_force"] is False
    assert result["active_interface_modified"] is False
    assert len(ADMITTED) == result["active_interface_count"] == 11


def test_output_overwrite_refusal(tmp_path, monkeypatch):
    monkeypatch.setattr(validation, "RESULT_PATH", tmp_path / "result.json")
    monkeypatch.setattr(validation, "ATTEMPT_PATH", tmp_path / "attempt.json")
    assert validation.output_available()
    validation.RESULT_PATH.write_text("occupied")
    assert not validation.output_available()
    with pytest.raises(FileExistsError, match="overwrite refused"):
        validation.preflight()
