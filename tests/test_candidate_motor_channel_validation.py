import json
import pytest

from malecns_backend.embodiment import candidate_motor_channel_validation as audit
from malecns_backend.embodiment import _windows_candidate_motor_mechanical_validation as mechanical


def test_identity_decoder_and_fail_closed_preregistration():
    result = audit.build()
    assert result["identity_validation_passed"] is True
    assert result["decoder_validation_passed"] is True
    assert result["mechanical_validation_passed"] is False
    assert result["preregistration_created"] is False
    assert set(result["candidate_channels"]) == set(audit.CANDIDATES)
    assert result["run_status"] == "SKIPPED / DEPENDENCIES_UNAVAILABLE"


def test_dependency_unavailable_mechanical_mode_fails_closed(tmp_path, monkeypatch):
    output = tmp_path / "validation.json"
    preregistration = tmp_path / "future.json"
    monkeypatch.setattr(audit, "OUTPUT", output)
    monkeypatch.setattr(audit, "PREREGISTRATION", preregistration)
    monkeypatch.setattr(audit, "dependencies_available", lambda: False)
    assert audit.main(["--mechanical"]) == 0
    value = json.loads(output.read_text())
    assert value["run_status"] == "SKIPPED / DEPENDENCIES_UNAVAILABLE"
    assert value["mechanical_validation_passed"] is False
    assert value["preregistration_created"] is False
    assert not preregistration.exists()


def test_engineered_vectors_are_isolated_and_means_not_sums():
    for name, index in audit.CANDIDATES.items():
        check = audit.engineered_checks(name, index)
        assert check["passed"] is True
        assert check["population_mean_invariance_hz"] == [34.0, 34.0]
        for case in check["cases"].values():
            assert case["nonzero_action_indices"] in ([], [index])


def test_expected_compiled_identity():
    ordered = tuple(audit.CANDIDATES) + tuple(f"unused_{i}" for i in range(39))
    # Exercise each expected index using a realistic 42-entry ordering.
    ordered = list(ordered)
    for name, index in audit.CANDIDATES.items():
        ordered[index] = name
        mechanical.validate_identity(tuple(ordered), index, f"1/actuator_position_{name}",
                                     f"1/{name}", 17 + index, 17 + index, name)
        with pytest.raises(RuntimeError, match="identity differs"):
            mechanical.validate_identity(tuple(ordered), index, "1/actuator_position_wrong",
                                         f"1/{name}", 17 + index, 17 + index, name)


def test_perturbation_isolation():
    neutral = [0.0] * 8
    changed = neutral.copy(); changed[6] = .0001
    mechanical.assert_isolated(neutral, changed, 6, .0001)
    changed[2] = 1
    with pytest.raises(RuntimeError, match="exactly the expected joint"):
        mechanical.assert_isolated(neutral, changed, 6, .0001)


def test_sign_decision_requires_consistent_rotation_and_endpoint():
    evidence = {"world_joint_axis_neutral": [0, 1, 0],
        "positive_minus_negative_endpoint_displacement": [0.1, 0, -0.2],
        "positive": {"world_rotation_axis_direction": [0, 1, 0], "relative_segment_rotation_rad": .0001},
        "negative": {"world_rotation_axis_direction": [0, -1, 0], "relative_segment_rotation_rad": .0001}}
    assert mechanical.decide_sign(evidence) == -1
    evidence["negative"]["world_rotation_axis_direction"] = [0, 1, 0]
    assert mechanical.decide_sign(evidence) is None


def test_preregistration_only_after_all_three_pass(tmp_path):
    result = audit.build()
    path = tmp_path / "future.json"
    with pytest.raises(RuntimeError, match="all three"):
        audit.create_preregistration_after_mechanics(result, path)
    assert not path.exists()
    for channel in result["candidate_channels"].values():
        channel["mechanics"]["historical_sign_reproduced"] = True
    digest = audit.create_preregistration_after_mechanics(result, path)
    value = json.loads(path.read_text())
    assert value["status"] == "NOT_RUN" and value["duration_ms"] == 1000
    assert len(digest) == 64
