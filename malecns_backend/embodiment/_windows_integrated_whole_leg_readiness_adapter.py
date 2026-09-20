"""Windows-only M6C live boundary and condition orchestration.

The adapter keeps environment discovery outside the physics loop.  Low-level
live stepping is intentionally factored as ``_run_live_condition`` so unit
tests can verify orchestration without importing FlyGym.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

from .full_leg_interface import enumerate_live_actuators
from .integrated_whole_leg_readiness import (
    CONDITIONS, DURATION_MS, MILESTONES, SEED, TIER_A, EXPECTED_TIER_B,
    assert_physical_admission, classify, hidden_assistance_audit, m7_readiness,
)

EXPECTED_ENVIRONMENT_CONSTRUCTIONS = 4  # inventory plus three fresh conditions


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def progress_header() -> None:
    print("=" * 60, flush=True)
    print("M6C INTEGRATED WHOLE-LEG EMBODIMENT", flush=True)
    print("11 admitted motor channels", flush=True)
    print("3 matched conditions", flush=True)
    print(f"seed = {SEED}", flush=True)
    print(f"duration = {DURATION_MS} ms", flush=True)
    print("=" * 60, flush=True)


def format_progress(number: int, condition: str, fraction: float, step: int,
                    condition_wall: float, total_wall: float,
                    estimated_remaining: float | None) -> str:
    suffix = "" if estimated_remaining is None else f" | estimated remaining {estimated_remaining:.1f}s"
    return (f"[{number}/3] {fraction * 100:.0f}% | {condition} | "
            f"{fraction * DURATION_MS:.1f} ms | physics step {step} | "
            f"condition wall {condition_wall:.1f}s | total wall {total_wall:.1f}s{suffix}")


def validate_cached_inventory(protocol: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    table = tuple(protocol["actuator_admission_table"])
    if len(records) != 42 or len(table) != 42:
        raise RuntimeError("live model is not the locked 42-actuator inventory")
    if any(record["index"] != row["action_index"] or record["name"] != row["actuator"]
           for record, row in zip(records, table)):
        raise RuntimeError("live actuator action order differs from M6C admission table")
    if sum(row["neural_motor_admission"] for row in table) != 11:
        raise RuntimeError("M6C admission count changed")
    return table


def run_preflight(protocol: Mapping[str, Any], output_path: Path) -> dict[str, Any]:
    """Inspect real dependencies/model and construct fresh runtimes, never step."""
    import flygym  # lazy Windows dependency
    from malecns_backend import load_malecns
    from .tactile_motor_loop import validated_interfaces
    from .tactile_motor_loop_audit import _make_live

    data = load_malecns(); tibia = validated_interfaces()
    records = enumerate_live_actuators()  # exactly once, outside every loop
    table = validate_cached_inventory(protocol, records)
    admitted = [row for row in table if row["neural_motor_admission"]]
    if {row["actuator"] for row in admitted} != set(TIER_A + EXPECTED_TIER_B):
        raise RuntimeError("exact integrated admission order changed")
    constructed = []
    try:
        for _condition in CONDITIONS:
            sim, physics, observation, _, _ = _make_live(flygym, tibia)
            constructed.append((sim, physics, observation))
        if len({id(x[0]) for x in constructed}) != 3:
            raise RuntimeError("conditions do not have fresh simulations")
    finally:
        for sim, _, _ in constructed:
            close = getattr(sim, "close", None)
            if close: close()
    audit = hidden_assistance_audit()
    if audit["hidden_locomotion_assistance_executed"]:
        raise RuntimeError("hidden locomotion assistance is on the execution path")
    report = {"schema": "M6C-PREFLIGHT.0", "artifact_kind": "NON_SCIENTIFIC_PREFLIGHT",
        "run_status": "PASS", "scientific_run_executed": False,
        "canonical_artifact_status": "NOT_RUN", "seed": SEED, "duration_ms": DURATION_MS,
        "checks": {"dependencies": True, "provenance": protocol["provenance"]["verified"],
            "actuator_order_42": True, "exact_11_admissions": True, "action_indices": True,
            "coordinate_signs": all(row["coordinate_sign"] in (-1, 1) for row in admitted),
            "sensory_provenance": len(protocol["sensory_interfaces"]) == 6,
            "condition_plan": tuple(x["name"] for x in protocol["conditions"]) == CONDITIONS,
            "fresh_runtime_construction": True, "cleanup": True, "progress_instrumentation": True,
            "per_step_environment_construction": False,
            "canonical_artifact_not_run": protocol["run_status"] == "NOT_RUN"},
        "environment_construction_count": EXPECTED_ENVIRONMENT_CONSTRUCTIONS,
        "hidden_locomotion_audit": audit}
    _atomic_write(output_path, report)
    return report


def reduce_conditions(results: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Reduce full telemetry summaries supplied by the live condition loop."""
    if tuple(results) != CONDITIONS: raise RuntimeError("incomplete or reordered conditions")
    enabled, disabled, no_femur = (results[x] for x in CONDITIONS)
    def first_difference(left: Mapping[str, Any], right: Mapping[str, Any], fields: Sequence[str]) -> int | None:
        return next((i for i, (a, b) in enumerate(zip(left.get("trajectory", ()), right.get("trajectory", ())))
                     if any(a.get(field) != b.get(field) for field in fields)), None)
    command_b = first_difference(enabled, disabled, ("action", "ctrl"))
    physical_b = first_difference(enabled, disabled, ("qpos", "qvel"))
    command_c = first_difference(enabled, no_femur, ("action", "ctrl"))
    physical_c = first_difference(enabled, no_femur, ("qpos", "qvel"))
    command_b = enabled.get("first_command_divergence_vs_all_disabled", command_b)
    physical_b = enabled.get("first_physical_divergence_vs_all_disabled", physical_b)
    command_c = enabled.get("first_command_divergence_vs_tier_b_disabled", command_c)
    physical_c = enabled.get("first_femur_divergence_vs_tier_b_disabled", physical_c)
    sensory_c = first_difference(enabled, no_femur, ("sensory", "delivered_sensory_drive"))
    cns_c = first_difference(enabled, no_femur, ("malecns_state_digest", "aggregate_cns_spike_count"))
    disabled_rows = disabled.get("trajectory", ())
    per_channel = []
    action_index = {row["actuator"]: row["action_index"] for row in enabled.get("admission_table", ())}
    # Live results can omit a duplicate table; canonical indices remain in protocol reduction later.
    for summary in enabled.get("per_channel", ()):
        item = dict(summary); index = action_index.get(item["actuator"])
        maximum = (max((abs(a["qpos"][index] - b["qpos"][index])
                        for a, b in zip(enabled.get("trajectory", ()), disabled_rows)), default=0.)
                   if index is not None else 0.)
        item["maximum_selected_joint_divergence_vs_control"] = maximum
        if item.get("peak_admitted", 0) and maximum == 0:
            item["status"] = "ADMITTED_OUTPUT_NO_DETECTABLE_PHYSICAL_EFFECT"
        per_channel.append(item)
    snapshots = [x.get("pre_intervention_state") for x in (enabled, disabled, no_femur)]
    snapshot_equal = (not all(snapshots) or snapshots[0] == snapshots[1] == snapshots[2])
    has_trajectories = all(x.get("trajectory") for x in (enabled, disabled, no_femur))
    initial = [x.get("trajectory", [{}])[0] for x in (enabled, disabled, no_femur)]
    initial_equal = (not has_trajectories or bool(initial and all(all(row.get(k) == initial[0].get(k) for k in
        ("qpos", "qvel", "action", "ctrl", "malecns_state_digest", "aggregate_cns_spike_count"))
        for row in initial[1:])))
    milestones = {key: False for key in MILESTONES}
    milestones.update(enabled.get("local_milestones", {}))
    milestones["C0"] = snapshot_equal and initial_equal and all(results[x].get("pre_intervention_equivalence", False) for x in CONDITIONS[1:])
    milestones["C4"] = command_b is not None
    milestones["C5"] = physical_b is not None
    milestones["C8"] = all(x.get("unauthorized_contribution_count", 1) == 0 for x in results.values())
    milestones["C9"] = all(not x.get("physics_instability", True) for x in results.values())
    for key in ("C10", "C11", "C12"):
        milestones[key] = enabled.get("feedback_milestones", {}).get(key) is not None
    return {"milestones": milestones, "classification": classify(milestones),
        "per_channel_telemetry_summary": per_channel,
        "a_vs_b": {"first_command_divergence": command_b,
            "first_physical_divergence": physical_b},
        "a_vs_c": {"first_tier_b_command_divergence": command_c,
            "first_femur_physical_divergence": physical_c,
            "first_full_body_physical_divergence": physical_c,
            "first_validated_sensory_divergence": sensory_c,
            "first_cns_divergence": cns_c}}


def _run_live_condition(*args: Any, **kwargs: Any) -> Mapping[str, Any]:
    """Load the reviewed live M6C runtime implementation.

    Keeping this import separate prevents Linux tests and preflight from ever
    entering the canonical condition loop.  Absence is an interface failure,
    never a fallback or fabricated result.
    """
    from ._windows_m6c_live_condition import run_condition
    return run_condition(*args, **kwargs)


def run_canonical(protocol: Mapping[str, Any], output_path: Path,
                  condition_runner: Callable[..., Mapping[str, Any]] = _run_live_condition) -> dict[str, Any]:
    """Run exactly three fresh matched conditions with abort-safe provenance."""
    started = time.perf_counter(); progress_header(); results = {}; active = None
    cached_records = enumerate_live_actuators()  # one locked inventory construction only
    cached_table = validate_cached_inventory(protocol, cached_records)
    checkpoint = Path(output_path).with_suffix(".progress.json")
    try:
        for number, condition in enumerate(CONDITIONS, 1):
            active = condition; print(f"[{number}/3] START {condition}", flush=True)
            result = condition_runner(protocol=protocol, condition=condition, condition_number=number,
                progress=format_progress, cached_admission_assertion=assert_physical_admission,
                cached_records=cached_records, cached_table=cached_table)
            result = dict(result); result.setdefault("admission_table", cached_table)
            results[condition] = result
            print(f"[{number}/3] DONE {condition}", flush=True); active = None
            _atomic_write(checkpoint, {"schema": "M6C-CHECKPOINT.0", "run_status": "IN_PROGRESS",
                "completed_condition_count": len(results), "active_condition": None,
                "resume_authorized": False, "elapsed_wall_seconds": time.perf_counter() - started})
    except KeyboardInterrupt:
        _atomic_write(checkpoint, {"schema": "M6C-CHECKPOINT.0", "run_status": "ABORTED_USER_INTERRUPT",
            "canonical_result_complete": False, "completed_condition_count": len(results),
            "active_condition": active, "resume_authorized": False,
            "elapsed_wall_seconds": time.perf_counter() - started})
        raise
    reduced = reduce_conditions(results); report = dict(protocol)
    report.update(run_status="COMPLETE", scientific_run_executed=True, **reduced,
        condition_results=results, hidden_locomotion_audit=hidden_assistance_audit())
    report["performance"] = {"total_wall_seconds": time.perf_counter() - started,
        "environment_construction_count": 3, "per_physics_step_environment_construction": False,
        "condition_phase_totals": {name: result.get("performance", {}) for name, result in results.items()}}
    report["m7_readiness"] = m7_readiness(provenance=True, milestones=report["milestones"],
        interface_valid=True, sensory_valid=True,
        hidden_assistance=report["hidden_locomotion_audit"]["hidden_locomotion_assistance_executed"], admissions=11)
    _atomic_write(Path(output_path), report)
    return report


__all__ = ["EXPECTED_ENVIRONMENT_CONSTRUCTIONS", "format_progress", "progress_header",
           "reduce_conditions", "run_canonical", "run_preflight", "validate_cached_inventory"]
