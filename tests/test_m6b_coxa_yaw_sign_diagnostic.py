"""M6B-P3 non-scientific, geometry-only contracts."""
import json
from pathlib import Path

import numpy as np

from malecns_backend.embodiment import m6b_coxa_yaw_sign_diagnostic as p3


def test_rotational_metric_and_antisymmetry():
    plus = p3.signed_rotational_metric([0, 0, 1], [1, 0, 0], [1, .0001, 0])
    minus = p3.signed_rotational_metric([0, 0, 1], [1, 0, 0], [1, -.0001, 0])
    assert plus > 0 > minus
    assert np.isclose(plus, -minus)


def test_local_axis_rotation_to_world():
    rotation = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    assert np.allclose(p3.transform_local_axis([1, 0, 0], rotation), [0, 1, 0])


def test_fail_closed_annotation_and_geometry_rules():
    assert p3.assess_coordinate_sign(0, 0, "positive_axis_rotation")[0] == "SIGN_UNRESOLVED"
    assert p3.assess_coordinate_sign(.1, -.1, None)[0] == "SIGN_UNRESOLVED"
    assert p3.assess_coordinate_sign(.1, -.1, "anterior rotator")[0] == "SIGN_UNRESOLVED"
    assert p3.assess_coordinate_sign(.1, -.1, "positive_axis_rotation", bilateral_only=True)[0] == "SIGN_UNRESOLVED"
    assert p3.assess_coordinate_sign(.1, -.1, "positive_axis_rotation")[:2] == ("RESOLVED", 1)


def test_committed_diagnostic_contract_and_history():
    root = Path(__file__).parents[1]
    report = json.loads((root / "malecns_backend/embodiment/interface_output/m6b_coxa_yaw_sign_diagnostic.json").read_text())
    canonical = json.loads((root / "malecns_backend/embodiment/interface_output/isolated_tier_b_motor_validation.json").read_text())
    assert p3.EPSILON_RAD == .0001
    assert report["schema"] == "M6B-P3.0" and len(report["interfaces"]) == 6
    assert report["scientific_runner_called"] is False
    assert all(not x["uses_neural_behavior"] and not x["uses_walking_performance"] for x in report["interfaces"])
    assert all(not x["uses_bilateral_assumption"] for x in report["interfaces"])
    assert len({x["actuator"] for x in report["interfaces"]}) == 6  # independent records
    assert report["summary"]["m6b_eligible_after_sign_calibration"] == [
        "joint_LFFemur", "joint_LFTarsus1", "joint_LMFemur", "joint_LHFemur",
        "joint_RFFemur", "joint_RFTarsus1", "joint_RMFemur", "joint_RHFemur"]
    assert canonical["run_status"] == "NOT_RUN"
    assert canonical["provenance"]["scientific_run_number"] is None
