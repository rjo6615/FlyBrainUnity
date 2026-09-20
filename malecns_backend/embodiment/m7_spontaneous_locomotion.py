"""M7 preregistration data model and non-scientific preflight.

There is intentionally no scientific runner in this module.  The future live
runner must reuse the locked M6C embodiment and emit immutable NPZ telemetry;
this module only validates the frozen plan and reduces already-recorded data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .integrated_whole_leg_readiness import EQUIVALENCE_FIELDS, EXPECTED_TIER_B, TIER_A

SCHEMA = "M7.0"
SEED = 1
DURATION_MS = 5000
PHYSICS_DT_MS = 0.1
NEURAL_DT_MS = 0.5
CONDITIONS = ("SPONTANEOUS_NEURAL_EMBODIMENT", "ALL_NEURAL_MOTOR_DISABLED")
ADMITTED_MOTOR = TIER_A + EXPECTED_TIER_B
ADMITTED_SENSORY = TIER_A
OUTPUT = Path(__file__).resolve().parent / "interface_output" / "m7_spontaneous_locomotion.json"
PREFLIGHT = Path(__file__).resolve().parent / "interface_output" / "m7_windows_preflight.json"

MOVEMENT_CATEGORIES = (
    "NO_MEASURABLE_NEURAL_PHYSICAL_EFFECT", "LOCALIZED_LIMB_MOVEMENT",
    "MULTI_LEG_MOVEMENT", "BODY_POSTURAL_CHANGE", "NET_BODY_DISPLACEMENT",
    "REPEATED_OR_OSCILLATORY_LIMB_ACTIVITY",
)
FAIL_CLOSED = (
    "provenance failure", "interface mismatch", "pre-intervention equivalence failure",
    "physics instability before intervention", "unauthorized actuator contribution",
    "hidden locomotion controller detected", "telemetry corruption", "incomplete condition",
)
THRESHOLDS = {"joint_divergence_rad": 1e-6, "com_displacement_m": 1e-6,
              "orientation_divergence_rad": 1e-6, "height_divergence_m": 1e-6,
              "oscillation_prominence_rad": 1e-4, "oscillation_min_extrema": 3,
              "rollover_body_up_z_max": 0.0, "fall_height_fraction": 0.5}


def build_not_run() -> dict[str, Any]:
    return {
        "schema": SCHEMA, "artifact_kind": "PREREGISTERED_NOT_RUN_RESULT",
        "run_status": "NOT_RUN", "scientific_run_executed": False,
        "scientific_question": "What does the currently validated MaleCNS embodied system do when placed in the FlyGym physical environment without being instructed to produce a gait or target movement?",
        "seed": SEED, "duration_ms": DURATION_MS,
        "physics_dt_ms": PHYSICS_DT_MS, "neural_dt_ms": NEURAL_DT_MS,
        "expected_physics_transitions": 50000, "expected_neural_updates": 10000,
        "conditions": [{"name": name, "fresh_runtime": True} for name in CONDITIONS],
        "admitted_motor_interfaces": list(ADMITTED_MOTOR),
        "admitted_sensory_interfaces": list(ADMITTED_SENSORY),
        "baseline_only_actuator_count": 31,
        "spontaneous_definition": "Frozen M6C initialization, deterministic background dynamics, and the six admitted tibial sensory streams only; no added stimulation, noise, tonic drive, locomotor command, controller, target, reference, reward, or tuning.",
        "equivalence_fields": list(EQUIVALENCE_FIELDS),
        "outcomes": ["body_center_of_mass_displacement", "forward_displacement", "lateral_displacement",
            "yaw_change", "body_height", "body_velocity", "joint_trajectories", "admitted_motor_activity",
            "tibial_sensory_activity", "cns_activity_summary", "existing_ground_contact_state",
            "numerical_stability", "objective_fall_or_rollover"],
        "movement_categories": list(MOVEMENT_CATEGORIES),
        "frozen_thresholds": dict(THRESHOLDS),
        "fail_closed": list(FAIL_CLOSED),
        "gait_policy": "Descriptive only: contact-derived stance/swing intervals, inter-leg phase, autocorrelation/periodicity, stride-like repetition, displacement per cycle, and directionality; no gait label, template, score, or optimization.",
        "telemetry": {"raw_format": "immutable compressed NPZ", "summary_format": "JSON",
            "trajectory_replay": "render only from recorded state; rendering must not alter simulation state"},
        "classification": None,
    }


def validate_preflight(protocol: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "not_run": protocol.get("run_status") == "NOT_RUN" and not protocol.get("scientific_run_executed"),
        "seed_frozen": protocol.get("seed") == 1,
        "duration_frozen": protocol.get("duration_ms") == 5000,
        "two_conditions": tuple(x["name"] for x in protocol.get("conditions", ())) == CONDITIONS,
        "fresh_runtimes": all(x.get("fresh_runtime") for x in protocol.get("conditions", ())),
        "exact_motor_interfaces": tuple(protocol.get("admitted_motor_interfaces", ())) == ADMITTED_MOTOR,
        "exact_sensory_interfaces": tuple(protocol.get("admitted_sensory_interfaces", ())) == ADMITTED_SENSORY,
        "other_31_baseline_only": protocol.get("baseline_only_actuator_count") == 31,
        "strict_equivalence": tuple(protocol.get("equivalence_fields", ())) == EQUIVALENCE_FIELDS,
        "no_scientific_runner_in_preregistration_module": True,
    }
    if not all(checks.values()):
        raise ValueError("M7 preregistration preflight failed")
    return {"schema": "M7-PREFLIGHT.0", "artifact_kind": "NON_SCIENTIFIC_PREFLIGHT",
            "run_status": "PASS", "scientific_run_executed": False, "checks": checks}


def movement_categories(*, joint_divergent_legs: int, posture_changed: bool,
                        net_displacement: bool, oscillatory: bool) -> list[str]:
    result = []
    if joint_divergent_legs == 0 and not posture_changed and not net_displacement:
        result.append(MOVEMENT_CATEGORIES[0])
    if joint_divergent_legs == 1: result.append(MOVEMENT_CATEGORIES[1])
    if joint_divergent_legs >= 2: result.append(MOVEMENT_CATEGORIES[2])
    if posture_changed: result.append(MOVEMENT_CATEGORIES[3])
    if net_displacement: result.append(MOVEMENT_CATEGORIES[4])
    if oscillatory: result.append(MOVEMENT_CATEGORIES[5])
    return result


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists(): raise FileExistsError(f"refusing to overwrite immutable artifact: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-not-run", action="store_true")
    parser.add_argument("--preflight-windows", action="store_true")
    args = parser.parse_args(argv)
    protocol = build_not_run()
    if args.write_not_run: write_json(OUTPUT, protocol)
    if args.preflight_windows:
        write_json(PREFLIGHT, validate_preflight(protocol))
        print("M7 WINDOWS PREFLIGHT PASS — SCIENCE NOT RUN")
    if not args.write_not_run and not args.preflight_windows:
        print("M7 NOT_RUN preregistration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
