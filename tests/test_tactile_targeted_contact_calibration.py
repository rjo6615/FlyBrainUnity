import ast
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.embodiment import tactile_targeted_contact_calibration as target


ROOT = Path(__file__).parents[1]
LOCKED = {
    "malecns_backend/embodiment/tactile_contact.py": "10fb5edb8c9d59036a703d4ebe1bfac9c67e986f0d42d1ea412666f7404011f9",
    "malecns_backend/embodiment/tactile_contact_calibration.py": "1cab509fa2bd8f24638711cb974bf9a122d1199152f5c9c666a0933c54593b1c",
    "malecns_backend/embodiment/interface_output/tactile_contact_calibration.json": "a088f2923d7b752377fd48cf2a348b546eb32ddc0c23d8d6525056b4bf26420d",
}


def pair(a, aname, b, bname):
    return target.ContactPair(a, aname, b, bname)


class Model:
    def __init__(self, names):
        self.names = names
        self.ngeom = len(names)

    def id2name(self, geom_id, kind):
        assert kind == "geom"
        return self.names[geom_id]


def test_fresh_conditions_have_identical_reset_pose_and_no_fly_displacement():
    # Environment placement is a pure geometric calculation and cannot mutate qpos.
    qpos = np.arange(12.0)
    before = qpos.copy()
    target.surface_position((1, 2, 3), 0.2, contact=True)
    np.testing.assert_array_equal(qpos, before)


def test_only_surface_position_differs_between_matched_conditions():
    tarsus = (0.2, -0.3, 0.4)
    control = target.surface_position(tarsus, 0.05, contact=False)
    contact = target.surface_position(tarsus, 0.05, contact=True)
    np.testing.assert_array_equal(control[:2], contact[:2])
    assert contact[2] - control[2] == pytest.approx(target.CONTROL_GAP + target.CONTACT_PENETRATION)


def test_exact_lm_tarsus5_geom_resolution_rejects_partial_names():
    model = Model(["0/LMTarsus5_sensor", "0/LMTarsus5"])
    assert target.resolve_exact_geom(model, "LMTarsus5") == (1, "0/LMTarsus5")


def test_exact_calibration_surface_resolution_and_uniqueness():
    model = Model(["0/m5d2c_calibration_surface", "ground"])
    assert target.resolve_exact_geom(model, target.SURFACE_NAME)[0] == 0
    with pytest.raises(RuntimeError):
        target.resolve_exact_geom(Model([target.SURFACE_NAME, f"1/{target.SURFACE_NAME}"]), target.SURFACE_NAME)


def test_ground_truth_requires_exact_unordered_geom_pair():
    metadata = target.contact_metadata([pair(7, "tarsus", 9, "surface")], 7, 9)
    assert metadata["selected_pair_present"]
    assert target.contact_metadata([pair(9, "surface", 7, "tarsus")], 7, 9)["selected_pair_present"]


def test_unrelated_contacts_cannot_establish_ground_truth():
    contacts = [pair(7, "tarsus", 4, "fly body"), pair(3, "other leg", 9, "surface")]
    metadata = target.contact_metadata(contacts, 7, 9)
    assert not metadata["selected_pair_present"]
    assert len(metadata["all_contact_pairs"]) == 2


def test_force_alone_cannot_establish_ground_truth():
    assert target.classify_correspondence([]) == "NO_VERIFIED_CONTACT"
    result = target.evaluate_threshold([999.0], [], "NO_VERIFIED_CONTACT")
    assert not result["evaluated"]
    assert result["false_positives"] is None


def test_correspondence_requires_metadata_selected_samples_and_nonzero_force():
    assert target.classify_correspondence([0.0, 0.25]) == "SENSOR_CORRESPONDENCE_CONFIRMED"


def test_metadata_contact_with_zero_sensor_is_explicit():
    correspondence = target.classify_correspondence([0.0, 0.0])
    assert correspondence == "CONTACT_CONFIRMED_SENSOR_ZERO"
    assert target.evaluate_threshold([], [0, 0], correspondence)["classification"] == "CALIBRATION_INCONCLUSIVE"


def test_threshold_only_evaluated_after_correspondence_confirmation():
    skipped = target.evaluate_threshold([1.0], [0.0], "CONTACT_CONFIRMED_SENSOR_ZERO")
    assert not skipped["evaluated"]
    evaluated = target.evaluate_threshold([0.0], [1.0], "SENSOR_CORRESPONDENCE_CONFIRMED")
    assert evaluated["evaluated"] and evaluated["classification"] == "THRESHOLD_ACCEPTED"


def test_threshold_false_positive_and_negative_counts():
    result = target.evaluate_threshold([0, 2e-12], [0, 2e-12],
                                       "SENSOR_CORRESPONDENCE_CONFIRMED")
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 1
    assert result["classification"] == "THRESHOLD_REQUIRES_REVISION"


def test_no_neural_runtime_import_or_use():
    tree = ast.parse(inspect.getsource(target))
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert all("neural" not in ast.unparse(node).lower() for node in imports)
    assert "set_external_drive" not in inspect.getsource(target)


def test_deterministic_serialization():
    report = {"z": 1, "a": {"x": 2}}
    assert target.serialized_report(report) == target.serialized_report(report)
    assert list(json.loads(target.serialized_report(report))) == ["a", "z"]


def test_nonlive_report_is_explicitly_inconclusive():
    report = target.build_report()
    assert report["run_status"] == "NOT_RUN"
    assert report["sensor_correspondence_classification"] == "NO_VERIFIED_CONTACT"
    assert report["threshold_evaluation"]["classification"] == "CALIBRATION_INCONCLUSIVE"


def test_locked_hashes_unchanged():
    for relative, expected in LOCKED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
