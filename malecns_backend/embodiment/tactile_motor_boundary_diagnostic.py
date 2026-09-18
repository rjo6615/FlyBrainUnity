"""Pure, exact analysis for the M5D-4B intervention-boundary diagnostic.

This module deliberately has no FlyGym dependency.  It distinguishes a
condition-label/program difference from a value that crosses ``sim.step``.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

from .tactile_motor_loop import ACTUATOR_INDICES, NEURAL_DT_MS
from .tactile_motor_equivalence_diagnostic import compare_value, mujoco_object_identity
from .tactile_targeted_contact_calibration import DEFAULT_TIMESTEP_S

SCHEMA = "M5D-4B.0"
DURATION_MS = 15.0
SEED = 1
PIPELINE_STAGES = (
    "measured_joint_position", "previous_target", "base_hold_target",
    "raw_mapped_motor_spike_counts", "motor_observer_state",
    "decoder_filtered_state", "decoded_extensor_activation",
    "decoded_flexor_activation", "decoded_antagonist_signal",
    "decoded_angular_offset", "condition_application_flag",
    "requested_neural_contribution", "gated_neural_contribution",
    "candidate_target_before_clamp", "target_after_range_clamp",
    "target_before_slew_limiter", "target_after_slew_limiter",
    "final_target", "actual_mujoco_ctrl",
)
CLASSIFICATIONS = (
    "INTERVENTION_BOUNDARY_CONFIRMED", "EARLY_CONTROL_INTERVENTION_FOUND",
    "BASE_HOLD_STATE_DIVERGENCE", "SLEW_CLAMP_STATE_DIVERGENCE",
    "ACTION_ARRAY_MUTATION", "SHARED_MUTABLE_STATE_LEAK",
    "TELEMETRY_BOUNDARY_BUG", "PHYSICAL_DIVERGENCE_WITHOUT_CONTROL_DIVERGENCE",
    "UNRESOLVED_RUNNER_DIVERGENCE",
)


def base_report() -> dict[str, Any]:
    """Return the truthful checked-in artifact; no live result is implied."""
    return {
        "schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "reason": "Live M5D-4B diagnostic has not been run on validated Windows FlyGym/MuJoCo",
        "protocol": {"seed": SEED, "duration_ms": DURATION_MS,
            "physics_timestep_s": DEFAULT_TIMESTEP_S, "neural_timestep_ms": NEURAL_DT_MS,
            "conditions": ["TACTILE_MOTOR_ENABLED", "TACTILE_MOTOR_DISABLED"],
            "exact_comparison": True, "canonical_100ms_run_permitted": False,
            "original_m5d4_branch_semantics": True},
        "provenance": {"verified": False, "m5d2c": None, "m5d3": None,
            "m5d4": None, "m5d4a": None},
        "static_runner_audit": static_runner_audit(),
        "mutable_state_audit": {"live_object_identity_checked": False,
            "construction_lifetime_inspected": False,
            "fresh_per_condition_required": ["simulation", "MuJoCo model/data", "MaleCNS",
                "decoder set", "motor observers", "tactile encoder/RNG", "command array"],
            "shared_mutable_state_found": None, "shared_mutable_state_status": "NOT_RUN"},
        "logical_condition_divergence": None,
        "effective_physical_intervention": None,
        "pipeline_comparisons": None,
        "first_ctrl_divergence": None, "first_qacc_divergence": None,
        "first_qvel_divergence": None, "first_qpos_divergence": None,
        "first_contact_divergence": None, "first_force_divergence": None,
        "intervention_telemetry_audit": telemetry_audit(),
        "causal_ordering": {"established": False, "sequence": None},
        "resolved_actuator_or_dof": None,
        "limitations": ["NOT_RUN: static findings are not live causal findings.",
            "The canonical M5D-4 artifact is preserved and is not interpreted as motor causality."],
    }


def static_runner_audit() -> dict[str, Any]:
    return {
        "first_logical_branch": {
            "location": "tactile_motor_loop_audit._run_condition(..., apply_motor)",
            "value": {"enabled": True, "disabled": False},
            "time_ms": 0.0, "physically_relevant_by_itself": False},
        "neural_update_order": ["sample measured joints", "update motor observer",
            "decode with apply_neural_offset=apply_motor", "update decoder previous_target",
            "enabled writes decoder target; disabled writes measured position",
            "copy full joints action", "sim.step"],
        "first_possible_command_branch": {
            "location": "tactile_motor_loop_audit._run_condition command assignment",
            "cadence": "neural updates only (0.5 ms)",
            "enabled": "command.target_position_rad",
            "disabled": "measured[action_index]"},
        "base_hold_risk": "Between neural updates both retain the prior command. At later updates the enabled path can be slew-limited from decoder.previous_target while the disabled path bypasses that result and writes the newly measured position, even with a zero decoded offset.",
        "actual_decoder_order": ["base measured position + gated offset", "joint-range clamp",
            "slew from previous_target", "final joint-range clamp", "store previous_target"],
        "scientific_parameters_changed": False,
    }


def telemetry_audit() -> dict[str, Any]:
    return {
        "first_mapped_tibia_motor_spike_ms": "first row with any nonzero mapped motor increment",
        "first_nonzero_decoded_output_ms": "first row with any decoded magnitude_clamped_output_rad != 0",
        "first_applied_neural_output_ms": "first row with any telemetry applied_output != 0; applied_output is decoded output when apply_motor else zero",
        "answers": "B",
        "is_any_condition_dependent_physical_value_boundary": False,
        "zero_decoded_offset_is_nonzero_applied_output": False,
        "warning": "The field does not inspect action arrays or MuJoCo ctrl and therefore cannot establish the effective physical intervention boundary.",
    }


def first_difference(enabled: Sequence[Mapping[str, Any]], disabled: Sequence[Mapping[str, Any]],
                     fields: Sequence[str], *, contact: bool = False) -> dict[str, Any] | None:
    """Select the first exact difference by step, then requested stage order."""
    if len(enabled) != len(disabled):
        raise ValueError("condition trace lengths differ")
    for step, (left, right) in enumerate(zip(enabled, disabled)):
        if left.get("time_ms") != right.get("time_ms"):
            raise ValueError("condition sample schedules differ")
        for field in fields:
            comparator = compare_contact_sets if contact else compare_value
            difference = comparator(left.get(field), right.get(field))
            if not difference["exactly_equal"]:
                return {"time_ms": left["time_ms"], "physical_step_index": step,
                    "variable": field, **difference}
    return None


def _semantic_contact_set(value: Any) -> Any:
    """Canonicalize only construction-local contact identity and ordering."""
    if isinstance(value, Mapping):
        names = value.get("geom1_name"), value.get("geom2_name")
        result = {_key: _semantic_contact_set(child) for _key, child in value.items()
                  if not (all(name is not None for name in names) and _key in (
                      "geom1", "geom2", "geom1_id", "geom2_id", "geom1_name", "geom2_name"))}
        if all(name is not None for name in names):
            result["semantic_geometry_pair"] = sorted(
                (mujoco_object_identity(names[0]), mujoco_object_identity(names[1])), key=str)
        for key in ("selected_contact_pairs", "all_contact_pairs"):
            if isinstance(result.get(key), list):
                result[key] = sorted(result[key],
                    key=lambda item: json.dumps(item, sort_keys=True, allow_nan=False))
        return result
    if isinstance(value, (list, tuple)):
        return [_semantic_contact_set(child) for child in value]
    return value


def compare_contact_sets(a: Any, b: Any) -> dict[str, Any]:
    """Compare unordered contact pairs using M5D-4A's exact name identity."""
    return compare_value(_semantic_contact_set(a), _semantic_contact_set(b))


def compare_traces(enabled: Sequence[Mapping[str, Any]], disabled: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups = {
        "logical": ("condition_application_flag",),
        "pipeline": PIPELINE_STAGES,
        "all_42_position_actuator_commands": ("action_joints",),
        "six_tibia_actuator_commands": ("six_tibia_action",),
        "six_adhesion_commands": ("adhesion",), "ctrl": ("ctrl",),
        "qacc": ("qacc",), "qvel": ("qvel",), "qpos": ("qpos",),
        "contact": ("contact_set",), "force": ("contact_forces",),
    }
    return {name: first_difference(enabled, disabled, fields, contact=name == "contact")
            for name, fields in groups.items()}


def shared_mutable_aliases(enabled: Mapping[str, Any],
                           disabled: Mapping[str, Any]) -> list[dict[str, str]]:
    """Return direct cross-condition aliases while both object sets are alive.

    Numeric ``id`` values are deliberately not accepted: CPython may recycle
    an address after a sequential condition has been destroyed.
    """
    return [{"enabled": left_name, "disabled": right_name}
            for left_name, left in enabled.items()
            for right_name, right in disabled.items() if left is right]


def classify(comparison: Mapping[str, Any], reported_applied_ms: float | None = None) -> str:
    ctrl = comparison.get("ctrl"); qpos = comparison.get("qpos")
    if ctrl is None and qpos is not None:
        return "PHYSICAL_DIVERGENCE_WITHOUT_CONTROL_DIVERGENCE"
    if ctrl is None:
        return "UNRESOLVED_RUNNER_DIVERGENCE"
    pipeline = comparison.get("pipeline") or {}
    variable = pipeline.get("variable", "")
    if variable in ("base_hold_target", "previous_target"):
        return "BASE_HOLD_STATE_DIVERGENCE"
    if variable in ("target_after_range_clamp", "target_before_slew_limiter", "target_after_slew_limiter"):
        return "SLEW_CLAMP_STATE_DIVERGENCE"
    if reported_applied_ms is not None and ctrl["time_ms"] < reported_applied_ms:
        return "EARLY_CONTROL_INTERVENTION_FOUND"
    return "INTERVENTION_BOUNDARY_CONFIRMED" if reported_applied_ms == ctrl["time_ms"] else "UNRESOLVED_RUNNER_DIVERGENCE"


def semantic_digest(report: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
    """Fail closed on locked semantic fields; ignore serialization and EOLs."""
    observed = {}
    for dotted, expected in manifest.items():
        value: Any = report
        try:
            for component in dotted.split("."):
                value = value[component]
        except (KeyError, TypeError) as error:
            raise RuntimeError(f"locked semantic field missing: {dotted}") from error
        if type(value) is not type(expected) or value != expected:
            raise RuntimeError(f"locked semantic field changed: {dotted}")
        observed[dotted] = value
    return hashlib.sha256(json.dumps(observed, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode()).hexdigest()


def serialize(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def atomic_write(path: Path, report: Mapping[str, Any]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialize(report)); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def actuator_identity(name: str | None, index: int) -> dict[str, Any]:
    basename = mujoco_object_identity(name)
    leg = next((leg for leg, value in ACTUATOR_INDICES.items() if value == index), None)
    return {"actuator_index": index, "exact_name": name, "basename": basename,
            "leg": leg, "joint": "Tibia" if leg else None,
            "validated_tibia": leg is not None, "adhesion": "adhesion" in (basename or "").lower()}
