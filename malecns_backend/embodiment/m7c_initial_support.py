"""Preregistered, physics-only M7C-B initial-support calibration.

This module deliberately imports neither MaleCNS nor a neural runtime.  The
Windows runner may import FlyGym only after the immutable preregistration has
been written and checked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

TIMESTEP_S = 0.0001
DURATION_MS = 100.0
TRANSITIONS = 1000
CHECKPOINT_TRANSITION = 130
FALL_HEIGHT = 0.25
ROLLOVER_UP_Z = 0.0
CANONICAL_ROOT = (0.0, 0.0, 0.5)
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "interface_output" / "m7c_initial_stability"
PREREGISTRATION = OUTPUT / "m7c_b_preregistration.json"
RESULT = OUTPUT / "m7c_b_initial_support_result.json"
AUDIT = OUTPUT / "m7c_initial_state_audit.json"


def candidates(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the complete candidate set; no dynamic result is an input."""
    geoms = {g["name"].rsplit("/", 1)[-1]: g for g in audit["geometries"]}
    feet = []
    for leg in ("LF", "LM", "LH", "RF", "RM", "RH"):
        geom = geoms[f"{leg}Tarsus5"]
        feet.append({"leg": leg, "center": geom["world_position"],
                     "conservative_lower_z": geom["world_position"][2] - max(geom["size"])})
    lowest = min(x["conservative_lower_z"] for x in feet)
    # The second candidate changes one initialization parameter only.  It is
    # geometry-derived rather than searched or selected using outcome data.
    return [
        {"id": "canonical_control", "root_position": list(CANONICAL_ROOT),
         "joint_pose": "FlyGym default pose (no override)", "vertical_translation": 0.0,
         "derivation": "exact canonical M7 initialization"},
        {"id": "distal_tarsus_support_translation",
         "root_position": [0.0, 0.0, CANONICAL_ROOT[2] - lowest],
         "joint_pose": "FlyGym default pose (no override)", "vertical_translation": -lowest,
         "derivation": "single vertical translation placing the lowest conservative Tarsus5 bound at ground z=0"},
    ]


def build_preregistration(audit: Mapping[str, Any]) -> dict[str, Any]:
    cs = candidates(audit)
    return {"schema": "M7C-B-PREREGISTRATION.1", "status": "FROZEN_BEFORE_EXECUTION",
        "candidate_definition_sha256": hashlib.sha256(json.dumps(cs, sort_keys=True).encode()).hexdigest(),
        "candidates": cs, "candidate_count": 2, "arbitrary_height_sweep": False,
        "optimizer": False, "brain_constructed": False, "neural_transitions": 0,
        "physics": {"timestep_s": TIMESTEP_S, "duration_ms": DURATION_MS,
            "transitions": TRANSITIONS, "checkpoint_13ms_transition": CHECKPOINT_TRANSITION,
            "fall_height_lt": FALL_HEIGHT, "rollover_body_up_z_le": ROLLOVER_UP_Z},
        "controls": {"position_targets": "post-reset measured 42-joint positions",
            "gait_controller": False, "balance_controller": False,
            "reference_trajectory": False, "reward_rl_ai": False,
            "adhesion_enabled": False, "adhesion_command": [0.0] * 6,
            "calibration_surface": "canonical present and fixed"},
        "gate": {"fail_closed_nonfinite": True, "reject_body_penetration": True,
            "reject_severe_foot_penetration": True, "flag_self_collision": True,
            "reject_unsupported_feet": True, "reject_mixed_support_surfaces": True},
        "execution_environment": "validated Windows FlyGym/MuJoCo environment only"}


def finite_state(values: Mapping[str, Any]) -> bool:
    """Fail-closed numeric-state predicate used by the Windows adapter/tests."""
    try:
        return all(math.isfinite(float(x)) for value in values.values()
                   for x in (value if isinstance(value, (list, tuple)) else (value,)))
    except (TypeError, ValueError):
        return False


def reconstruct(height: float, up_z: float) -> dict[str, bool]:
    return {"fall": float(height) < FALL_HEIGHT,
            "rollover": float(up_z) <= ROLLOVER_UP_Z}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-preregistration", action="store_true")
    args = parser.parse_args(argv)
    if not args.write_preregistration:
        parser.error("only preregistration is available locally; use the documented Windows runner after preflight")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    report = build_preregistration(audit)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PREREGISTRATION.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(PREREGISTRATION)


if __name__ == "__main__":
    main()
