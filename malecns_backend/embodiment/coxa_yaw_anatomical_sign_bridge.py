"""Preregistered geometry-only Coxa-yaw anatomical sign bridge.

Import and ``--preflight`` are construction-free and transition-free.  Only
``--execute`` imports FlyGym/MuJoCo, and execution uses qpos assignment plus
kinematic forward propagation--never a dynamics step or a neural runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT_DIR = HERE / "interface_output/coxa_yaw_anatomical_sign_bridge"
PREREGISTRATION_PATH = OUTPUT_DIR / "coxa_yaw_anatomical_sign_bridge_preregistration.json"
ATTEMPT_PATH = OUTPUT_DIR / "coxa_yaw_anatomical_sign_bridge_attempt.json"
RESULT_PATH = OUTPUT_DIR / "coxa_yaw_anatomical_sign_bridge_result.json"
MECHANICAL_PREREGISTRATION_PATH = (
    HERE / "interface_output/coxa_yaw_sign_validation/coxa_yaw_sign_validation_preregistration.json"
)

TARGETS = (
    ("LF", "joint_LFCoxa_yaw", 2, "LFFemur"),
    ("LM", "joint_LMCoxa_yaw", 9, "LMFemur"),
    ("LH", "joint_LHCoxa_yaw", 16, "LHFemur"),
    ("RF", "joint_RFCoxa_yaw", 23, "RFFemur"),
    ("RM", "joint_RMCoxa_yaw", 30, "RMFemur"),
    ("RH", "joint_RHCoxa_yaw", 37, "RHFemur"),
)
ACTION_VECTOR_LENGTH = 42
ACTIVE_INTERFACE_COUNT = 11
EPSILON_RAD = 0.0001
METRIC_TOLERANCE = 1e-10
BASELINE_TOLERANCE = 1e-12
OPPOSITION_TOLERANCE = 1e-10
MECHANICAL_PREREGISTRATION_SHA256 = "dcf1b4419f8d0bd7cd65979ad2da3084db5482cf906b3e40217836335c563254"
PREREGISTRATION_SHA256 = "90fff49d72547ae65c4f7af380a3c0eed2ef3a8bc102b81098ae594f033f13f3"


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def validate_targets(rows: Sequence[Sequence[Any]]) -> None:
    normalized = tuple((str(x[0]), str(x[1]), int(x[2]), str(x[3])) for x in rows)
    if normalized != TARGETS or len(set(normalized)) != 6:
        raise RuntimeError("target inventory differs from the ordered six-target freeze")


def isolated_action(index: int, value: float) -> list[float]:
    if index not in {row[2] for row in TARGETS} or not math.isfinite(value):
        raise ValueError("a finite displacement for one frozen Coxa-yaw target is required")
    result = [0.0] * ACTION_VECTOR_LENGTH
    result[index] = float(value)
    return result


def classify_leg(evidence: Mapping[str, Any]) -> str:
    """Apply the frozen rule without selecting or changing the metric."""
    if evidence.get("geometry_identity_valid") is not True or evidence.get("fresh_baseline_identical") is not True:
        return "GEOMETRY_IDENTITY_FAILURE"
    if evidence.get("mechanical_valid") is not True:
        return "MECHANICAL_FAILURE"
    try:
        plus = float(evidence["positive"]["projected_anterior_displacement"])
        minus = float(evidence["negative"]["projected_anterior_displacement"])
    except (KeyError, TypeError, ValueError):
        return "SOFTWARE_FAILURE"
    if not math.isfinite(plus) or not math.isfinite(minus):
        return "SOFTWARE_FAILURE"
    # Both motions must be nontrivial and lie on strictly opposite sides of zero.
    if min(abs(plus), abs(minus)) <= METRIC_TOLERANCE or plus * minus >= -OPPOSITION_TOLERANCE**2:
        return "ANATOMICAL_SIGN_GEOMETRICALLY_UNRESOLVED"
    if plus > METRIC_TOLERANCE and minus < -METRIC_TOLERANCE:
        return "ANTERIOR_SIGN_POSITIVE"
    if minus > METRIC_TOLERANCE and plus < -METRIC_TOLERANCE:
        return "ANTERIOR_SIGN_NEGATIVE"
    return "ANATOMICAL_SIGN_GEOMETRICALLY_UNRESOLVED"


def coordinate_signs(classification: str) -> tuple[int | None, int | None]:
    if classification == "ANTERIOR_SIGN_POSITIVE":
        return 1, -1
    if classification == "ANTERIOR_SIGN_NEGATIVE":
        return -1, 1
    return None, None


def verify_preregistration(path: Path = PREREGISTRATION_PATH) -> dict[str, Any]:
    if canonical_sha256(path) != PREREGISTRATION_SHA256:
        raise RuntimeError("frozen preregistration SHA-256 mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_targets([(x["leg"], x["joint"], x["action_index"], x["landmark_body"])
                      for x in value["targets"]])
    metric = value.get("anatomical_metric", {})
    expected = {
        "frame": "compiled Thorax body frame at the fresh neutral baseline",
        "anterior_axis": "Thorax local +X transformed to world by baseline Thorax xmat",
        "landmark": "origin of the named Femur body (the coxa distal child landmark)",
        "formula": "dot(landmark_perturbed_world - landmark_baseline_world, anterior_axis_world)",
    }
    if (value.get("status") != "NOT_RUN" or value.get("epsilon_rad") != EPSILON_RAD or
            value.get("action_vector_length") != ACTION_VECTOR_LENGTH or
            value.get("metric_tolerance") != METRIC_TOLERANCE or
            any(metric.get(key) != val for key, val in expected.items())):
        raise RuntimeError("frozen anatomical metric is incomplete or changed")
    return value


def _verify_previous_freeze() -> dict[str, Any]:
    if canonical_sha256(MECHANICAL_PREREGISTRATION_PATH) != MECHANICAL_PREREGISTRATION_SHA256:
        raise RuntimeError("previous mechanical preregistration identity mismatch")
    prior = json.loads(MECHANICAL_PREREGISTRATION_PATH.read_text(encoding="utf-8"))
    previous = tuple((x["leg"], x["joint"], x["action_index"]) for x in prior["targets"])
    if previous != tuple(row[:3] for row in TARGETS):
        raise RuntimeError("previous mechanical target freeze mismatch")
    result_path = MECHANICAL_PREREGISTRATION_PATH.with_name("coxa_yaw_sign_validation_result.json")
    return {"preregistration_sha256": MECHANICAL_PREREGISTRATION_SHA256,
            "targets_verified": True, "result_available": result_path.exists(),
            "result_sha256": canonical_sha256(result_path) if result_path.exists() else None}


def output_available() -> bool:
    return not ATTEMPT_PATH.exists() and not RESULT_PATH.exists()


def preflight() -> dict[str, Any]:
    prereg = verify_preregistration()
    previous = _verify_previous_freeze()
    if not output_available():
        raise FileExistsError("attempt/result namespace is occupied; overwrite refused")
    from .motor_population_inventory import ADMITTED
    if len(ADMITTED) != ACTIVE_INTERFACE_COUNT:
        raise RuntimeError("active physical interface is no longer exactly 11")
    if any(name.endswith("Coxa_yaw") for name, _, _ in ADMITTED):
        raise RuntimeError("a Coxa-yaw channel has entered the active interface")
    return {
        "status": "PREFLIGHT_PASSED", "scientific_execution_occurred": False,
        "neural_transitions": 0, "physics_transitions": 0, "kinematic_forwards": 0,
        "stimulation": False, "extra_forces": False, "active_interface_count": 11,
        "active_interface_modified": False, "action_vector_length": 42,
        "output_paths_unoccupied": True, "preregistration_sha256": PREREGISTRATION_SHA256,
        "metric_fully_specified": True, "targets": prereg["targets"],
        "previous_mechanical_freeze": previous,
        "sign_dependent_outcomes_evaluated": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    ready = preflight()
    if args.preflight:
        print(json.dumps(ready, indent=2, sort_keys=True))
        return 0
    from . import _windows_coxa_yaw_anatomical_sign_bridge as adapter
    print(json.dumps(adapter.execute(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
