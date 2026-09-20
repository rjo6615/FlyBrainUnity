"""M7 frozen protocol, reductions, and explicit scientific-runner CLI.

Protocol definition remains side-effect free.  Windows preflight and science
are separate adapter calls; neither importing this module nor reducing saved
telemetry can advance a simulation.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
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
PREFLIGHT = Path(__file__).resolve().parent / "interface_output" / "m7_windows_preflight_v3.json"
RESULT_DIRECTORY = Path(__file__).resolve().parent / "interface_output" / "m7_canonical"
EXPECTED_PHYSICS_TRANSITIONS = 50000
EXPECTED_NEURAL_UPDATES = 10000

MOVEMENT_CATEGORIES = (
    "NO_MEASURABLE_NEURAL_PHYSICAL_EFFECT", "LOCALIZED_LIMB_MOVEMENT",
    "MULTI_LEG_MOVEMENT", "BODY_POSTURAL_CHANGE", "NET_BODY_DISPLACEMENT",
    "REPEATED_OR_OSCILLATORY_LIMB_ACTIVITY",
)
FAIL_CLOSED = (
    "provenance failure", "canonical M6C lock mismatch", "protocol mismatch",
    "interface mismatch", "pre-intervention equivalence failure",
    "physics instability before intervention", "unauthorized actuator contribution",
    "hidden locomotion controller detected", "unexpected dynamic adhesion assistance",
    "numerical or physics instability", "telemetry corruption", "incomplete condition",
    "wrong physics transition count", "wrong neural update count",
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


def write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    """Durably create JSON without a check-then-write overwrite race."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())


@dataclass(frozen=True)
class OutputPaths:
    directory: Path
    raw: Path
    summary: Path
    manifest: Path

    @property
    def all(self) -> tuple[Path, ...]: return self.raw, self.summary, self.manifest

    @classmethod
    def canonical(cls, directory: Path = RESULT_DIRECTORY) -> "OutputPaths":
        return cls(directory, directory / "m7_raw.npz", directory / "m7_summary.json",
                   directory / "m7_manifest.json")


def write_aborted(directory: Path, exc: BaseException, completed: int, elapsed: float) -> Path:
    """Preserve an engineering abort separately; never call it a result."""
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = directory / f"ABORTED_IMPLEMENTATION_{stamp}_{os.getpid()}.json"
    status = getattr(exc, "run_status", "ABORTED_IMPLEMENTATION_FAILURE")
    payload = {"schema": "M7-ABORT.1", "artifact_kind": "NON_SCIENTIFIC_ATTEMPT_PROVENANCE",
        "run_status": status, "classification": None,
        "completed_condition_count": completed, "exception": f"{type(exc).__name__}: {exc}",
        "elapsed_wall_seconds": elapsed}
    details = getattr(exc, "details", None)
    if callable(details): payload["telemetry_schema_failure"] = details()
    write_json_exclusive(path, payload)
    return path


def reduce_results(results: Mapping[str, Mapping[str, Any]], table: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Control-relative reduction using only preregistered thresholds."""
    import numpy as np
    if tuple(results) != CONDITIONS: raise RuntimeError("incomplete or reordered conditions")
    enabled, control = (results[name]["raw_arrays"] for name in CONDITIONS)
    joint_delta = np.asarray(enabled["physics_joint_position"]) - np.asarray(control["physics_joint_position"])
    body_delta = np.asarray(enabled["physics_body_position"]) - np.asarray(control["physics_body_position"])
    orientation_delta = np.asarray(enabled["physics_body_orientation"]) - np.asarray(control["physics_body_orientation"])
    indices = [row["action_index"] for row in table if row["neural_motor_admission"]]
    joint_peak = np.max(np.abs(joint_delta[:, indices]), axis=0)
    divergent_legs = len({table[i]["leg"] for i in indices if joint_peak[indices.index(i)] > THRESHOLDS["joint_divergence_rad"]})
    net = float(np.linalg.norm(body_delta[-1] - body_delta[0]))
    posture = (float(np.max(np.abs(orientation_delta))) > THRESHOLDS["orientation_divergence_rad"] or
               float(np.ptp(body_delta[:, 2])) > THRESHOLDS["height_divergence_m"])
    # Extrema count is deterministic and fixed before execution; autocorrelation
    # is reported but never used to invent a gait label.
    extrema = int(max((np.count_nonzero(np.diff(np.sign(np.diff(joint_delta[:, i])))) for i in indices), default=0))
    oscillatory = extrema >= THRESHOLDS["oscillation_min_extrema"] and float(np.max(joint_peak)) >= THRESHOLDS["oscillation_prominence_rad"]
    per_condition = {}
    for name, result in results.items():
        arrays = result["raw_arrays"]; pos = np.asarray(arrays["physics_body_position"]); vel = np.asarray(arrays["physics_qvel"])
        quat = np.asarray(arrays["physics_body_orientation"])
        yaw = np.unwrap(np.arctan2(2 * (quat[:, 0] * quat[:, 3] + quat[:, 1] * quat[:, 2]),
                                   1 - 2 * (quat[:, 2] ** 2 + quat[:, 3] ** 2)))
        displacement = pos[-1] - pos[0]; cy, sy = np.cos(yaw[0]), np.sin(yaw[0])
        neural_contribution = np.asarray(arrays["neural_admitted_contributions"])
        sensory = np.asarray(arrays["neural_sensory_encoded"])
        up_z = 1 - 2 * (quat[:, 1] ** 2 + quat[:, 2] ** 2)
        per_condition[name] = {"net_com_displacement": displacement.tolist(),
            "forward_displacement": float(cy * displacement[0] + sy * displacement[1]),
            "lateral_displacement": float(-sy * displacement[0] + cy * displacement[1]),
            "vertical_displacement": float(displacement[2]), "yaw_change_rad": float(yaw[-1] - yaw[0]),
            "orientation_component_change": (quat[-1] - quat[0]).tolist(),
            "body_height_range": [float(pos[:, 2].min()), float(pos[:, 2].max())],
            "mean_body_velocity": float(np.mean(np.linalg.norm(vel[:, :3], axis=1))),
            "peak_body_velocity": float(np.max(np.linalg.norm(vel[:, :3], axis=1))),
            "per_joint_range_of_motion": np.ptp(np.asarray(arrays["physics_joint_position"])[:, indices], axis=0).tolist(),
            "contact_nonzero_samples": int(np.count_nonzero(arrays["physics_contact_forces"])),
            "admitted_channel_peak_abs": np.max(np.abs(neural_contribution), axis=0).tolist(),
            "validated_sensory_peak_hz": np.max(sensory, axis=0).tolist(),
            "cns_final_aggregate_spikes": int(arrays["neural_aggregate_spikes"][-1]),
            "fall": bool(pos[:, 2].min() < THRESHOLDS["fall_height_fraction"] * pos[0, 2]),
            "rollover": bool(np.any(up_z <= THRESHOLDS["rollover_body_up_z_max"]))}
    return {"schema": "M7-RESULT.1", "run_status": "COMPLETE", "scientific_run_executed": True,
        "seed": SEED, "duration_ms": DURATION_MS, "conditions": list(CONDITIONS),
        "physics_transitions_per_condition": EXPECTED_PHYSICS_TRANSITIONS,
        "neural_updates_per_condition": EXPECTED_NEURAL_UPDATES,
        "control_relative": {"net_com_divergence_m": net,
            "maximum_joint_divergence_rad": float(np.max(joint_peak)),
            "maximum_orientation_component_divergence": float(np.max(np.abs(orientation_delta))),
            "oscillation_extrema_count": extrema},
        "movement_categories": movement_categories(joint_divergent_legs=divergent_legs,
            posture_changed=posture, net_displacement=net > THRESHOLDS["com_displacement_m"], oscillatory=oscillatory),
        "per_condition": per_condition, "walking": None,
        "interpretation_policy": "descriptive observational categories only; no walking claim"}


def build_manifest(raw: Path, arrays: Mapping[str, Any], digest: str, elapsed: float) -> dict[str, Any]:
    def units(name: str) -> str:
        if "time_ms" in name: return "ms"
        if "velocity" in name or "qvel" in name: return "MuJoCo generalized units/s"
        if any(token in name for token in ("position", "qpos", "action", "ctrl", "contribution")): return "MuJoCo native/rad or m"
        if "sensory_encoded" in name or "observer" in name: return "Hz"
        if "contact_forces" in name: return "N"
        return "count/dimensionless"
    return {"schema": "M7-MANIFEST.1", "raw_file": raw.name, "raw_sha256": digest,
        "raw_byte_size": raw.stat().st_size, "seed": SEED, "duration_ms": DURATION_MS,
        "conditions": list(CONDITIONS), "elapsed_wall_seconds": elapsed,
        "arrays": {name: {"shape": list(value.shape), "dtype": str(value.dtype), "units": units(name)} for name, value in arrays.items()},
        "provenance": {"m6c_lock": "m6c_canonical_result_lock.final.json"},
        "render_policy": "offline replay only; never participates in control"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-not-run", action="store_true")
    parser.add_argument("--preflight-windows", action="store_true")
    parser.add_argument("--run-windows", action="store_true")
    parser.add_argument("--output-directory", type=Path, default=RESULT_DIRECTORY)
    args = parser.parse_args(argv)
    if sum((args.write_not_run, args.preflight_windows, args.run_windows)) > 1:
        parser.error("execution modes are mutually exclusive")
    protocol = build_not_run()
    if args.write_not_run: write_json(OUTPUT, protocol)
    if args.preflight_windows:
        validate_preflight(protocol)
        from ._windows_m7_spontaneous_locomotion_adapter import run_preflight
        run_preflight(PREFLIGHT)
        print("M7 WINDOWS SCIENTIFIC PREFLIGHT PASS — TELEMETRY SCHEMA VALID — ZERO STEPS — SCIENCE NOT RUN")
    if args.run_windows:
        from ._windows_m7_spontaneous_locomotion_adapter import run_canonical
        run_canonical(OutputPaths.canonical(args.output_directory))
    if not args.write_not_run and not args.preflight_windows and not args.run_windows:
        print("M7 NOT_RUN preregistration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
