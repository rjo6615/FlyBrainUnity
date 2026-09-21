"""M9A preregistered physics-only external-perturbation calibration.

M9A is a new experiment namespace.  Importing this module is inert and this
module deliberately does not import the MaleCNS runtime.  The live command is
the only route which may advance MuJoCo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import m7d_corrected_spontaneous as m7d

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "interface_output" / "m9a_perturbation_calibration"
REPORT_PATH = OUTPUT_DIR / "m9a_calibration_report.json"
MANIFEST_PATH = OUTPUT_DIR / "m9a_calibration_manifest.json"
SCHEMA = "M9A-PHYSICS-ONLY-PERTURBATION-CALIBRATION.1"

# MuJoCo/FlyGym uses the model's native mm, ms, mg unit convention.  These
# candidates and their ordering are preregistered, not generated adaptively.
CANDIDATE_FORCE_NATIVE = (0.0001, 0.0002, 0.0004, 0.0008)
DIRECTION = (0.0, 1.0, 0.0)
APPLICATION_BODY_EXACT = "Thorax"
START_MS, STOP_MS, OBSERVE_MS = 500.0, 520.0, 1500.0
DT_MS = m7d.PHYSICS_DT_MS
TRANSITIONS = 15_000
STATES = 15_001


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def force_at(time_ms: float, magnitude: float) -> tuple[float, float, float]:
    """Exact half-open perturbation schedule for the outgoing transition."""
    return tuple(magnitude * x if START_MS <= time_ms < STOP_MS else 0.0 for x in DIRECTION)


def protocol() -> dict[str, Any]:
    inherited = m7d.protocol()
    return {"schema": SCHEMA, "status": "NOT_RUN", "experiment_namespace": "M9A",
        "scientific_claim_boundary": "calibrated external physical perturbation only",
        "male_cns": {"constructed": False, "advanced": False, "neural_transitions": 0},
        "physics": {"flygym": "1.2.1", "mujoco": "3.2.7", "dt_ms": DT_MS,
            "transitions_per_candidate": TRANSITIONS, "states_per_candidate": STATES,
            "observation_duration_ms": OBSERVE_MS},
        "physical_initialization": inherited["physical_initialization"],
        "embodiment_inventory_retained_but_inactive": {
            "sensory_interfaces": list(m7d.ADMITTED_SENSORY),
            "motor_interfaces": list(m7d.ADMITTED_MOTOR),
            "baseline_only_actuator_count": inherited["baseline_only_actuator_count"]},
        "perturbation": {"mechanism": "MuJoCo data.xfrc_applied direct Cartesian force",
            "application_body_exact": APPLICATION_BODY_EXACT,
            "application_point": "compiled body center of mass (xfrc_applied force; zero torque)",
            "direction_xyz": list(DIRECTION), "start_ms_inclusive": START_MS,
            "stop_ms_exclusive": STOP_MS, "duration_ms": STOP_MS - START_MS,
            "candidate_force_magnitudes_native": list(CANDIDATE_FORCE_NATIVE),
            "force_units": "MuJoCo model-native force (mm-ms-mg derived unit)",
            "impulse_semantics": "magnitude * 20 ms in model-native force-time units"},
        "selection_rule_preregistered": {
            "inputs": ["finite", "fall_or_rollover", "maximum_root_displacement_mm",
                "maximum_tilt_deg", "authoritative_contact_pattern_changed",
                "post_force_displacement_reduction_fraction", "post_force_tilt_reduction_fraction"],
            "hard_exclusions": {"nonfinite": True, "fall_or_rollover_by_600ms": True,
                "maximum_root_displacement_mm_greater_than": 1.5,
                "maximum_tilt_deg_greater_than": 60.0},
            "meaningful_disturbance": {"minimum_root_displacement_mm": 0.05,
                "minimum_tilt_deg": 5.0, "contact_pattern_change_required": True},
            "return_toward_pre_state": {"either_displacement_or_tilt_reduction_fraction_at_least": 0.25,
                "late_window_ms": [1250.0, 1500.0]},
            "choice": "lowest preregistered magnitude satisfying every criterion; fail closed if none"},
        "controls_absent": inherited["hidden_assistance"],
        "explicit_absences": {"gait_controller": False, "cpg": False,
            "stabilization_controller": False, "adhesion_scheduling": False,
            "reward_or_rl": False, "ai_controller": False, "reference_trajectory": False,
            "target_pose_controller_beyond_inherited_fixed_actuator_semantics": False,
            "hidden_assistance": False}}


def validate_protocol(value: Mapping[str, Any]) -> None:
    p, inherited = value.get("perturbation", {}), m7d.protocol()
    checks = (value.get("physical_initialization") == inherited["physical_initialization"],
        value.get("male_cns") == {"constructed": False, "advanced": False, "neural_transitions": 0},
        tuple(p.get("candidate_force_magnitudes_native", ())) == CANDIDATE_FORCE_NATIVE,
        p.get("application_body_exact") == APPLICATION_BODY_EXACT,
        p.get("direction_xyz") == list(DIRECTION), p.get("start_ms_inclusive") == START_MS,
        p.get("stop_ms_exclusive") == STOP_MS,
        not any(value.get("controls_absent", {}).values()),
        not any(value.get("explicit_absences", {}).values()))
    if not all(checks):
        raise RuntimeError("M9A preregistration or frozen M7D/M8 inheritance mismatch")


def choose_candidate(rows: Sequence[Mapping[str, Any]]) -> float:
    """Apply only the declared physics metrics, preserving magnitude order."""
    if tuple(float(x["magnitude_native"]) for x in rows) != CANDIDATE_FORCE_NATIVE:
        raise RuntimeError("candidate results do not match preregistered sweep")
    for row in rows:
        if (row["finite"] and not row["fall_or_rollover_by_600ms"] and
                row["maximum_root_displacement_mm"] <= 1.5 and row["maximum_tilt_deg"] <= 60.0 and
                (row["maximum_root_displacement_mm"] >= 0.05 or row["maximum_tilt_deg"] >= 5.0) and
                row["authoritative_contact_pattern_changed"] and
                max(row["post_force_displacement_reduction_fraction"],
                    row["post_force_tilt_reduction_fraction"]) >= 0.25):
            return float(row["magnitude_native"])
    raise RuntimeError("no preregistered candidate satisfies the physics-only selection rule")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--windows-preflight", action="store_true")
    modes.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv); validate_protocol(protocol())
    from . import _windows_m9a_perturbation_calibration_adapter as adapter
    result = adapter.windows_preflight() if args.windows_preflight else adapter.run_windows()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
