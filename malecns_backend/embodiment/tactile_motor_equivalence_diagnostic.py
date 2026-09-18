"""Pure analysis and report schema for the M5D-4A pre-motor diagnostic.

This module intentionally has no FlyGym dependency.  The live runner records
exact (zero-tolerance) samples and this module finds the first unequal sample.
M5D-4A never authorizes a neural-derived value to cross the actuator boundary.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

SCHEMA = "M5D-4A.0"
DURATION_MS = 15.0
TIMESTEP_S = 0.0001
SEED = 1
CLASSIFICATIONS = (
    "EXACT_REPEATABILITY_CONFIRMED", "PHYSICS_REPEATABILITY_FAILURE",
    "CONDITION_WRAPPER_MISMATCH", "CONTROL_COMMAND_MISMATCH",
    "INITIAL_STATE_MISMATCH", "MODEL_CONFIGURATION_MISMATCH",
    "CONTACT_SOLVER_DIVERGENCE", "SHARED_STATE_LEAK",
    "UNRESOLVED_PRE_MOTOR_DIVERGENCE",
)
QUANTITIES = ("ctrl", "contact_set", "selected_contact_metadata", "qacc",
              "qvel", "qpos", "contact_forces")


def base_report() -> dict[str, Any]:
    """Return a truthful, deterministic not-yet-run artifact."""
    return {
        "schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "reason": "Live M5D-4A diagnostic has not been run on validated Windows FlyGym/MuJoCo",
        "protocol": {
            "duration_ms": DURATION_MS, "physics_timestep_s": TIMESTEP_S,
            "seed": SEED, "neural_motor_application": False,
            "zero_tolerance_exact_comparison": True,
            "conditions": ["TACTILE_MOTOR_ENABLED_LIKE_MOTOR_OFF",
                           "TACTILE_MOTOR_DISABLED_LIKE_MOTOR_OFF"],
            "same_condition_repeats": ["CONTROL_A", "CONTROL_B"],
            "original_m5d4_result_preserved": True,
        },
        "safety": {"neural_output_observed": True, "neural_output_decoded": True,
                   "neural_output_applied": False,
                   "applied_neural_output_sample_count": 0},
        "initialization_audit": None, "comparisons": None,
        "order_reversal": {"performed": False, "outcome_follows": None},
        "earliest_physical_divergence": None,
        "limitations": ["Diagnostic only; no M5D-4 motor-causality claim.",
                        "The canonical M5D-4 result is not rerun or reinterpreted."],
    }


def _difference(a: Any, b: Any, path: str = "") -> list[dict[str, Any]]:
    """Recursively report exact differences, including first indices."""
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        out = []
        for key in sorted(set(a) | set(b), key=str):
            child = f"{path}.{key}" if path else str(key)
            if key not in a or key not in b:
                out.append({"index": child, "enabled": a.get(key),
                            "disabled": b.get(key), "absolute_difference": None})
            else:
                out.extend(_difference(a[key], b[key], child))
        return out
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        out = []
        for index in range(max(len(a), len(b))):
            child = f"{path}[{index}]"
            if index >= len(a) or index >= len(b):
                out.append({"index": child,
                            "enabled": a[index] if index < len(a) else None,
                            "disabled": b[index] if index < len(b) else None,
                            "absolute_difference": None})
            else:
                out.extend(_difference(a[index], b[index], child))
        return out
    equal = type(a) is type(b) and a == b
    if equal:
        return []
    absolute = (abs(float(a) - float(b))
                if type(a) in (int, float) and type(b) in (int, float) else None)
    return [{"index": path or None, "enabled": a, "disabled": b,
             "absolute_difference": absolute}]


def compare_value(a: Any, b: Any) -> dict[str, Any]:
    differences = _difference(a, b)
    numeric = [x["absolute_difference"] for x in differences
               if x["absolute_difference"] is not None]
    return {"exactly_equal": not differences,
            "first_differing_index": differences[0]["index"] if differences else None,
            "enabled_value": differences[0]["enabled"] if differences else None,
            "disabled_value": differences[0]["disabled"] if differences else None,
            "absolute_difference": differences[0]["absolute_difference"] if differences else None,
            "maximum_absolute_difference": max(numeric, default=0.0),
            "difference_count": len(differences)}


def compare_initialization(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    comparison = compare_value(a, b)
    comparison["model_exactly_equal"] = not _difference(a.get("model"), b.get("model"))
    comparison["state_exactly_equal"] = not _difference(a.get("state"), b.get("state"))
    comparison["surface_exactly_equal"] = not _difference(a.get("surface"), b.get("surface"))
    return comparison


def compare_trajectories(a: Sequence[Mapping[str, Any]],
                         b: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Find each quantity's earliest difference at native 0.1-ms resolution."""
    result: dict[str, Any] = {}
    for quantity in QUANTITIES:
        found = None
        for row_a, row_b in zip(a, b):
            difference = compare_value(row_a[quantity], row_b[quantity])
            if not difference["exactly_equal"]:
                found = {"first_differing_time_ms": row_a["time_ms"], **difference}
                resolution = row_a.get("resolution", {}).get(quantity)
                if resolution is not None:
                    key = str(difference["first_differing_index"])
                    if key.startswith("[") and key.endswith("]"):
                        key = key[1:-1]
                    found["resolved_index"] = resolution.get(key)
                break
        result[quantity] = found or {
            "first_differing_time_ms": None, "first_differing_index": None,
            "enabled_value": None, "disabled_value": None,
            "absolute_difference": None, "maximum_absolute_difference": 0.0,
            "difference_count": 0, "exactly_equal": True}
    return result


def classify(initial: Mapping[str, Any], repeat: Mapping[str, Any],
             wrappers: Mapping[str, Any], order_outcome: str | None = None) -> str:
    if not initial["model_exactly_equal"]:
        return "MODEL_CONFIGURATION_MISMATCH"
    if not initial["state_exactly_equal"] or not initial["surface_exactly_equal"]:
        return "INITIAL_STATE_MISMATCH"
    if any(repeat[q]["first_differing_time_ms"] is not None for q in QUANTITIES):
        return "PHYSICS_REPEATABILITY_FAILURE"
    if order_outcome == "run_order":
        return "SHARED_STATE_LEAK"
    if wrappers["ctrl"]["first_differing_time_ms"] is not None:
        return "CONTROL_COMMAND_MISMATCH"
    if wrappers["contact_set"]["first_differing_time_ms"] is not None or wrappers[
            "selected_contact_metadata"]["first_differing_time_ms"] is not None:
        return "CONTACT_SOLVER_DIVERGENCE"
    if any(wrappers[q]["first_differing_time_ms"] is not None for q in QUANTITIES):
        return "CONDITION_WRAPPER_MISMATCH"
    return "EXACT_REPEATABILITY_CONFIRMED"


def atomic_write_report(path: Path, report: Mapping[str, Any]) -> None:
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
