"""Windows-only M7 scientific execution boundary.

Imports of FlyGym and the live MaleCNS runtime remain behind this module.  The
preflight uses the same initializer as science, but requests ``initialize_only``.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

from . import integrated_whole_leg_readiness as m6c
from . import m7_spontaneous_locomotion as m7
from .full_leg_interface import enumerate_live_actuators
from .m6c_result_lock import LOCK as FINAL_LOCK, raw_identity

EXPECTED_ENVIRONMENT_CONSTRUCTIONS = 2


def verify_final_lock() -> Mapping[str, Any]:
    lock = json.loads(FINAL_LOCK.read_text(encoding="utf-8"))
    canonical = m6c.OUTPUT
    digest, size = raw_identity(canonical)
    if (lock.get("lock_status") != "LOCKED" or lock.get("raw_sha256") != digest or
            lock.get("byte_size") != size or lock.get("m7_readiness") !=
            "M7_SPONTANEOUS_LOCOMOTION_EXPERIMENT_READY"):
        raise RuntimeError("canonical M6C final evidence lock mismatch")
    return lock


def build_live_protocol() -> Mapping[str, Any]:
    """Rebuild admission metadata solely from the frozen M6 sources."""
    lock = verify_final_lock(); provenance = lock["provenance"]
    m6a, m6b, tier_a = m6c.load_provenance(
        m6b_sha256=provenance["m6b_sha256"])
    protocol = m6c.build_not_run_artifact(m6a, m6b, tier_a, provenance)
    if tuple(protocol["admitted_motor_interfaces"]) != m7.ADMITTED_MOTOR:
        raise RuntimeError("M7/M6C motor interface mismatch")
    return protocol


def gate_contributions(values: Mapping[str, float], condition: str,
                       admitted: Sequence[str]) -> dict[str, float]:
    """The sole M7 intervention: gate admitted motor contributions to zero."""
    if condition not in m7.CONDITIONS or tuple(values) != tuple(admitted):
        raise RuntimeError("M7 contribution inventory or condition mismatch")
    enabled = condition == m7.CONDITIONS[0]
    result = {name: float(values[name]) if enabled else 0.0 for name in admitted}
    if any(not __import__("math").isfinite(value) for value in result.values()):
        raise RuntimeError("non-finite neural contribution")
    return result


def _runner(**kwargs: Any) -> Mapping[str, Any]:
    from ._windows_m6c_live_condition import run_condition
    return run_condition(**kwargs)


def _initialize(condition: str, number: int, protocol: Mapping[str, Any], records: Sequence[Mapping[str, Any]],
                table: Sequence[Mapping[str, Any]], runner: Callable[..., Mapping[str, Any]]) -> Mapping[str, Any]:
    return runner(protocol=protocol, condition=condition, condition_number=number,
        progress=format_progress, cached_admission_assertion=m6c.assert_physical_admission,
        cached_records=records, cached_table=table, initialize_only=True,
        duration_ms=m7.DURATION_MS, condition_names=m7.CONDITIONS,
        contribution_gate=gate_contributions, compact_telemetry=True)


def format_progress(number: int, condition: str, fraction: float, step: int,
                    condition_wall: float, total_wall: float, remaining: float | None) -> str:
    eta = "" if remaining is None else f" | ETA {remaining:.1f}s"
    return (f"[{number}/2] {condition} {fraction * 100:.0f}% | physics step {step}/50000 | "
            f"condition wall {condition_wall:.1f}s | total wall {total_wall:.1f}s{eta}")


def _inventory(protocol: Mapping[str, Any]) -> tuple[Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]]]:
    records = enumerate_live_actuators()  # exactly once, never inside a time-step loop
    table = tuple(protocol["actuator_admission_table"])
    if len(records) != 42 or len(table) != 42 or sum(x["neural_motor_admission"] for x in table) != 11:
        raise RuntimeError("live 42-actuator inventory mismatch")
    if any(r["name"] != row["actuator"] or r["index"] != row["action_index"] for r, row in zip(records, table)):
        raise RuntimeError("live actuator order mismatch")
    return records, table


def run_preflight(output_path: Path, runner: Callable[..., Mapping[str, Any]] = _runner) -> Mapping[str, Any]:
    """Initialize both exact scientific paths; execute zero transitions."""
    protocol = build_live_protocol(); records, table = _inventory(protocol)
    states = [_initialize(c, i, protocol, records, table, runner) for i, c in enumerate(m7.CONDITIONS, 1)]
    if any(x["physics_steps"] or x["neural_steps"] for x in states):
        raise RuntimeError("preflight crossed a scientific transition boundary")
    snapshots = [x["pre_intervention_state"] for x in states]
    if not m6c.pre_intervention_equivalent(*snapshots):
        raise RuntimeError("strict pre-intervention equivalence failure")
    audits = [x["initial_physical_state_audit"] for x in states]
    if audits[0] != audits[1] or audits[0]["adhesion_enabled"] or audits[0]["locomotion_or_reference_controller"]:
        raise RuntimeError("physical setup, adhesion, or hidden-controller audit failure")
    report = {"schema": "M7-PREFLIGHT.1", "artifact_kind": "NON_SCIENTIFIC_PREFLIGHT",
        "run_status": "PASS", "scientific_run_executed": False,
        "scientific_transitions": 0, "conditions": list(m7.CONDITIONS),
        "initial_physical_state": audits[0], "environment_construction_count": 2,
        "checks": {"m6c_final_evidence_lock": True, "protocol": True,
            "actual_flygym_mujoco_environment": True, "actual_malecns_runtime": True,
            "strict_initial_equivalence": True, "adhesion_constant_zero_disabled": True,
            "exact_motor_admissions": True, "exact_sensory_admissions": True,
            "telemetry_writers": True, "immutable_output_paths": True,
            "no_per_step_environment_construction": True, "hidden_controller_audit": True,
            "zero_sim_steps": True, "zero_brain_steps": True}}
    m7.write_json_exclusive(output_path, report)
    return report


def _write_npz_exclusive(path: Path, arrays: Mapping[str, Any]) -> str:
    import numpy as np
    buffer = io.BytesIO(); np.savez_compressed(buffer, **arrays); payload = buffer.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    return hashlib.sha256(payload).hexdigest()


def run_canonical(paths: m7.OutputPaths, runner: Callable[..., Mapping[str, Any]] = _runner) -> Mapping[str, Any]:
    """Run exactly two conditions and publish one immutable artifact set."""
    for path in paths.all:
        if path.exists(): raise FileExistsError(f"refusing to overwrite canonical M7 artifact: {path}")
    started = time.perf_counter(); protocol = build_live_protocol(); records, table = _inventory(protocol)
    if m6c.hidden_assistance_audit()["hidden_locomotion_assistance_executed"]:
        raise RuntimeError("hidden locomotion controller detected")
    results: dict[str, Mapping[str, Any]] = {}
    try:
        for number, condition in enumerate(m7.CONDITIONS, 1):
            result = runner(protocol=protocol, condition=condition, condition_number=number,
                progress=format_progress, cached_admission_assertion=m6c.assert_physical_admission,
                cached_records=records, cached_table=table, duration_ms=m7.DURATION_MS,
                condition_names=m7.CONDITIONS, contribution_gate=gate_contributions,
                compact_telemetry=True)
            if result.get("physics_steps") != m7.EXPECTED_PHYSICS_TRANSITIONS or result.get("neural_steps") != m7.EXPECTED_NEURAL_UPDATES:
                raise RuntimeError("wrong physics transition or neural update count")
            if result.get("physics_instability") or result.get("unauthorized_contribution_count"):
                raise RuntimeError("numerical instability or unauthorized actuator contribution")
            results[condition] = result
        # Each condition snapshot is taken before its first intervention.  No
        # telemetry is published or classified until their exact comparison
        # passes, while retaining exactly one fresh runtime per condition.
        if not m6c.pre_intervention_equivalent(
                *(results[c]["pre_intervention_state"] for c in m7.CONDITIONS)):
            raise RuntimeError("pre-intervention equivalence failure")
        audits = [results[c]["initial_physical_state_audit"] for c in m7.CONDITIONS]
        if (audits[0] != audits[1] or audits[0]["adhesion_enabled"] or
                audits[0]["adhesion_command"] != [0.0] * 6 or
                audits[0]["ground_dynamic_after_reset"] or
                audits[0]["locomotion_or_reference_controller"]):
            raise RuntimeError("unexpected dynamic adhesion assistance or physical setup mismatch")
    except Exception as exc:
        m7.write_aborted(paths.directory, exc, len(results), time.perf_counter() - started)
        raise
    summary = m7.reduce_results(results, table)
    arrays = {f"{condition}__{name}": array for condition, result in results.items()
              for name, array in result["raw_arrays"].items()}
    raw_hash = _write_npz_exclusive(paths.raw, arrays)
    manifest = m7.build_manifest(paths.raw, arrays, raw_hash, time.perf_counter() - started)
    m7.write_json_exclusive(paths.summary, summary); m7.write_json_exclusive(paths.manifest, manifest)
    return summary


__all__ = ["EXPECTED_ENVIRONMENT_CONSTRUCTIONS", "build_live_protocol", "format_progress",
           "gate_contributions", "run_canonical", "run_preflight", "verify_final_lock"]
