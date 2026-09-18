import hashlib
import inspect
import json
from pathlib import Path

from malecns_backend.embodiment import tactile_contact_calibration as calibration
from malecns_backend.embodiment.tactile_contact_calibration import (
    ContactPair, contact_metadata, evaluate_threshold, magnitude_statistics,
    serialized_report,
)

ROOT = Path(__file__).parents[1]
LOCKED = {
    "malecns_backend/embodiment/six_leg_map.json": "575186602ac1e5a6e3b2c6d680309880266f5d80e18fff44f989440f6cd0a4bc",
    "malecns_backend/embodiment/interface_output/m5d_tarsal_contact_load_audit.json": "a8f8c0451f615cd3632ffc2730893ab7aedc3448a9745416bcaf6d4543454090",
}


def test_selected_calibration_leg_is_lm_by_default():
    assert calibration.DEFAULT_LEG == "LM"
    assert calibration.build_report()["selected_leg"] == "LM"


def test_mujoco_metadata_is_required_and_force_cannot_establish_truth():
    unrelated = ContactPair(1, "ground", 2, "LFTarsus5")
    selected = ContactPair(1, "ground", 7, "LMTarsus5_collision")
    assert not contact_metadata([unrelated], [7])["selected_tarsus5_involved"]
    assert contact_metadata([selected], [7])["selected_tarsus5_involved"]
    # Even an arbitrarily large force cannot replace verified metadata.
    result = evaluate_threshold([], [999.0], verified_contact_occurred=False)
    assert result["classification"] == "CALIBRATION_INCONCLUSIVE"


def test_no_contact_and_contact_samples_remain_separate():
    assert magnitude_statistics([0.0, 0.0])["max"] == 0.0
    assert magnitude_statistics([0.25, 1.0])["min"] == 0.25
    assert evaluate_threshold([0.0, 0.0], [0.25, 1.0])["classification"] == "THRESHOLD_ACCEPTED"


def test_strict_threshold_semantics_and_error_counts():
    threshold = 1e-12
    result = evaluate_threshold([0, threshold, threshold * 2],
                                [threshold, threshold * 2], threshold)
    assert result["comparison"] == "magnitude > threshold"
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 1
    assert result["classification"] == "THRESHOLD_REQUIRES_REVISION"


def test_inconclusive_without_verified_contact():
    result = evaluate_threshold([0.0], [], verified_contact_occurred=False)
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 0
    assert result["classification"] == "CALIBRATION_INCONCLUSIVE"


def test_no_neural_runtime_import_or_use():
    source = inspect.getsource(calibration)
    for forbidden in ("MaleCNS", "MaleCNSBrain", "malecns_backend.neural",
                      "set_external_drive", "TactileContactEncoder"):
        assert forbidden not in source


def test_deterministic_json_serialization():
    left = {"z": 1, "a": {"value": 2}}
    assert serialized_report(left) == serialized_report(left)
    assert list(json.loads(serialized_report(left))) == ["a", "z"]


def test_locked_artifact_hashes_unchanged():
    for relative, expected in LOCKED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
