"""Preregistered, physics-only Coxa-yaw coordinate-direction validation.

Import and ``--preflight`` are zero-transition operations.  ``--execute`` is
the only entry point that imports the mechanical adapter; it never constructs
or advances MaleCNS and does not assign a neural coordinate sign.
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
OUTPUT_DIR = HERE / "interface_output/coxa_yaw_sign_validation"
PREREGISTRATION_PATH = OUTPUT_DIR / "coxa_yaw_sign_validation_preregistration.json"
RESULT_PATH = OUTPUT_DIR / "coxa_yaw_sign_validation_result.json"
ATTEMPT_PATH = OUTPUT_DIR / "coxa_yaw_sign_validation_attempt.json"
SURVEY_INVENTORY = HERE / "interface_output/motor_population_activity_survey/motor_population_inventory.json"
SIX_LEG_MAP = HERE / "six_leg_map.json"
TARGETS = (
    ("LF", "joint_LFCoxa_yaw", 2), ("LM", "joint_LMCoxa_yaw", 9),
    ("LH", "joint_LHCoxa_yaw", 16), ("RF", "joint_RFCoxa_yaw", 23),
    ("RM", "joint_RMCoxa_yaw", 30), ("RH", "joint_RHCoxa_yaw", 37),
)
EPSILON_RAD = 0.0001
ACTION_VECTOR_LENGTH = 42
ACTIVE_INTERFACE_COUNT = 11
PREREGISTRATION_SHA256 = "dcf1b4419f8d0bd7cd65979ad2da3084db5482cf906b3e40217836335c563254"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preregistration_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def isolated_action(index: int, value: float) -> list[float]:
    if index not in {row[2] for row in TARGETS} or not math.isfinite(value):
        raise ValueError("exactly one frozen Coxa-yaw target is required")
    vector = [0.0] * ACTION_VECTOR_LENGTH
    vector[index] = float(value)
    return vector


def validate_targets(rows: Sequence[Sequence[Any]]) -> None:
    normalized = tuple((str(x[0]), str(x[1]), int(x[2])) for x in rows)
    if normalized != TARGETS or len(set(normalized)) != len(TARGETS):
        raise RuntimeError("target inventory must equal the ordered six-target freeze")


def classify(evidence: Mapping[str, Any], tolerance: float = 1e-10) -> str:
    """Classify measured mechanics without mapping anatomy to coordinate sign."""
    required = tuple(row[1] for row in TARGETS)
    if tuple(evidence) != required:
        return "MECHANICAL_VALIDATION_FAILED"
    for name in required:
        row = evidence[name]
        plus, minus = row.get("positive", {}), row.get("negative", {})
        pd = plus.get("endpoint_displacement_from_baseline", ())
        md = minus.get("endpoint_displacement_from_baseline", ())
        dot = sum(float(a) * float(b) for a, b in zip(pd, md)) if len(pd) == len(md) == 3 else 0.0
        pnorm = math.sqrt(sum(float(x) ** 2 for x in pd)) if len(pd) == 3 else 0.0
        mnorm = math.sqrt(sum(float(x) ** 2 for x in md)) if len(md) == 3 else 0.0
        checks = (
            row.get("action_isolation") is True,
            row.get("fresh_baseline_identical") is True,
            row.get("neural_transitions") == 0,
            row.get("stimulation") is False,
            row.get("extra_force") is False,
            math.isclose(float(plus.get("joint_delta_rad", 0)), EPSILON_RAD, abs_tol=1e-12),
            math.isclose(float(minus.get("joint_delta_rad", 0)), -EPSILON_RAD, abs_tol=1e-12),
            float(plus.get("axis_projection_rad", 0)) > tolerance,
            float(minus.get("axis_projection_rad", 0)) < -tolerance,
            pnorm > tolerance, mnorm > tolerance, dot < 0.0,
        )
        if not all(checks):
            return "MECHANICAL_VALIDATION_FAILED"
    return "MECHANICAL_DIRECTION_RESOLVED_ANATOMICAL_SIGN_UNRESOLVED"


def _validate_population_identity() -> list[dict[str, Any]]:
    survey = json.loads(SURVEY_INVENTORY.read_text(encoding="utf-8"))
    audits = {x["leg"]: x for x in survey["coxa_yaw_audit"]}
    result = []
    for leg, joint, index in TARGETS:
        row = audits.get(leg, {})
        names = row.get("annotation_names", [])
        segment, side = {"F": 1, "M": 2, "H": 3}[leg[1]], "left" if leg[0] == "L" else "right"
        expected = {f"Sternal anterior rotator MN T{segment} {side}",
                    f"Sternal posterior rotator MN T{segment} {side}"}
        # Labels identify populations only; body-map dir is deliberately ignored.
        if (set(names) != expected or row.get("candidate_joints") != [joint] or
                row.get("action_indices") != [index] or row.get("anatomical_mapping_unique") is not True):
            raise RuntimeError(f"authoritative population identity mismatch for {leg}")
        result.append({"leg": leg, "joint": joint, "action_index": index,
                       "anterior_population": sorted(expected)[0],
                       "posterior_population": sorted(expected)[1]})
    return result


def verify_preregistration(path: Path = PREREGISTRATION_PATH) -> dict[str, Any]:
    if preregistration_sha256(path) != PREREGISTRATION_SHA256:
        raise RuntimeError("frozen preregistration SHA-256 mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_targets([(x["leg"], x["joint"], x["action_index"]) for x in value["targets"]])
    if (value.get("status") != "NOT_RUN" or value.get("epsilon_rad") != EPSILON_RAD or
            value.get("action_vector_length") != ACTION_VECTOR_LENGTH):
        raise RuntimeError("frozen preregistration content mismatch")
    return value


def output_available() -> bool:
    return not RESULT_PATH.exists() and not ATTEMPT_PATH.exists()


def preflight() -> dict[str, Any]:
    prereg = verify_preregistration()
    populations = _validate_population_identity()
    if not output_available():
        raise FileExistsError("result/attempt namespace is occupied; overwrite refused")
    from .motor_population_inventory import ADMITTED
    if len(ADMITTED) != ACTIVE_INTERFACE_COUNT:
        raise RuntimeError("active physical interface is no longer exactly 11")
    return {"status": "PREFLIGHT_PASSED", "scientific_run_executed": False,
            "physics_transitions": 0, "neural_transitions": 0,
            "construction_policy": "static construction-free preflight; --execute owns all FlyGym construction",
            "preregistration_sha256": PREREGISTRATION_SHA256,
            "targets": prereg["targets"], "population_identity": populations,
            "action_vector_length": ACTION_VECTOR_LENGTH, "stimulation": False,
            "extra_force": False, "active_interface_modified": False,
            "active_interface_count": ACTIVE_INTERFACE_COUNT, "output_paths_unoccupied": True}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    ready = preflight()
    if args.preflight:
        print(json.dumps(ready, indent=2, sort_keys=True)); return 0
    from . import _windows_coxa_yaw_sign_validation as adapter
    print(json.dumps(adapter.execute(), indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
