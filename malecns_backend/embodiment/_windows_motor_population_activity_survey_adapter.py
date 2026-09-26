"""LegendaryPC execution boundary for the frozen read-only population survey."""
from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Mapping

from . import motor_population_activity_survey as survey
from . import _windows_m7d_corrected_spontaneous_adapter as m7d_adapter
from . import integrated_whole_leg_readiness as m6c

CONDITION = "CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT"
ADMITTED_INTERFACE_SIZE = 11


def _runner(**kwargs: Any) -> Mapping[str, Any]:
    from ._windows_m6c_live_condition import run_condition
    return run_condition(**kwargs)


def _gate(values: Mapping[str, float], condition: str, admitted: tuple[str, ...]) -> dict[str, float]:
    if condition != CONDITION or tuple(values) != tuple(admitted) or len(admitted) != 11:
        raise RuntimeError("survey admission gate is not exactly the existing 11 channels")
    return {name: float(values[name]) for name in admitted}


def _assert_admitted_interface_identity(
        live: list[tuple[str, int, int]], frozen: list[tuple[str, int, int]]) -> None:
    """Require the same complete admitted interface, independent of serialization order."""
    if len(live) != ADMITTED_INTERFACE_SIZE or len(frozen) != ADMITTED_INTERFACE_SIZE:
        raise RuntimeError("live admitted interface differs from frozen existing 11")
    if len(set(live)) != len(live) or len(set(frozen)) != len(frozen):
        raise RuntimeError("live admitted interface differs from frozen existing 11")
    canonical_key = lambda row: (row[1], row[0], row[2])
    if sorted(live, key=canonical_key) != sorted(frozen, key=canonical_key):
        raise RuntimeError("live admitted interface differs from frozen existing 11")


def _invoke(runner: Any, *, initialize_only: bool, observer: Any | None = None) -> Mapping[str, Any]:
    protocol, records, table = m7d_adapter._protocol()
    if len(records) != 42 or len(table) != 42 or sum(bool(x["neural_motor_admission"]) for x in table) != 11:
        raise RuntimeError("survey requires exactly 42 actions and the existing 11 admissions")
    frozen = survey.load_inventory()["admitted_11_inventory"]
    live_admitted = [(x["actuator"], x["action_index"], x["coordinate_sign"])
                     for x in table if x["neural_motor_admission"]]
    frozen_admitted = [(x["joint"], x["action_index"], x["coordinate_sign"]) for x in frozen]
    _assert_admitted_interface_identity(live_admitted, frozen_admitted)
    return runner(protocol=protocol, condition=CONDITION, condition_number=1,
        progress=lambda *_: "motor population survey", cached_admission_assertion=m6c.assert_physical_admission,
        cached_records=records, cached_table=table, initialize_only=initialize_only,
        duration_ms=survey.DURATION_MS, condition_names=(CONDITION,), contribution_gate=_gate,
        compact_telemetry=True, runtime_factory=m7d_adapter._runtime, proprioception_only=True,
        fixed_initial_baseline=True, read_only_neural_observer=observer)


def preflight(runner: Any = _runner) -> dict[str, Any]:
    survey.assert_outputs_available(); inventory = survey.load_inventory(); survey.verify_preregistration()
    state = _invoke(runner, initialize_only=True,
                    observer=survey.PopulationActivityObserver(inventory))
    if state["physics_steps"] or state["neural_steps"] or state["motor_interventions"]:
        raise RuntimeError("preflight crossed a transition boundary")
    if state["admission_vector_length"] != 42:
        raise RuntimeError("physical action size changed")
    return {"schema": "MOTOR-POPULATION-ACTIVITY-SURVEY-PREFLIGHT.1", "status": "PASS",
        "scientific_run_executed": False, "neural_transitions": 0, "physics_transitions": 0,
        "inventory_sha256": survey.INVENTORY_SHA256,
        "preregistration_sha256": survey.PREREGISTRATION_SHA256,
        "population_count": 102, "admitted_motor_channels": 11, "physical_action_entries": 42,
        "no_stimulation": True, "no_extra_forces": True, "observer_initialized_from_live_state": True}


def _write_exclusive(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream: stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    return __import__("hashlib").sha256(payload).hexdigest()


def execute(runner: Any = _runner) -> Mapping[str, Any]:
    """Execute once; callers must invoke :func:`preflight` immediately first."""
    survey.assert_outputs_available(); inventory = survey.load_inventory(); prereg = survey.verify_preregistration()
    observer = survey.PopulationActivityObserver(inventory)
    result = _invoke(runner, initialize_only=False, observer=observer)
    if result["physics_steps"] != survey.PHYSICS_TRANSITIONS or result["neural_steps"] != survey.NEURAL_TRANSITIONS:
        raise RuntimeError("frozen transition count mismatch")
    if result.get("unauthorized_contribution_count") or result.get("physics_instability"):
        raise RuntimeError("action admission or numerical integrity failure")
    observed = result["read_only_observer_result"]
    report = {"schema": "MOTOR-POPULATION-ACTIVITY-SURVEY-REPORT.1", "status": "COMPLETE",
        "interpretation": prereg["interpretation_boundary"], "runtime": prereg["runtime_configuration"],
        "population_count": len(observed["populations"]), "populations": observed["populations"]}
    # Compact raw contains only non-redundant binned and aggregate numeric arrays.
    import io, numpy as np
    buffer = io.BytesIO(); np.savez_compressed(buffer,
        total_spike_increments=np.asarray([p["total_spike_increments"] for p in observed["populations"]], dtype=np.uint64),
        binned_spike_increments=np.asarray([[b["total_spike_increments"] for b in p["bins"]] for p in observed["populations"]], dtype=np.uint64),
        binned_mean_filtered_rate_hz=np.asarray([[b["mean_filtered_rate_hz"] for b in p["bins"]] for p in observed["populations"]], dtype=np.float64),
        binned_peak_filtered_rate_hz=np.asarray([[b["peak_filtered_rate_hz"] for b in p["bins"]] for p in observed["populations"]], dtype=np.float64))
    raw_hash = _write_exclusive(survey.RAW_PATH, buffer.getvalue())
    report_hash = _write_exclusive(survey.REPORT_PATH, survey.canonical_json(report).encode())
    environment = {"python": platform.python_version(), "platform": platform.platform(),
        "flygym": importlib.metadata.version("flygym"), "mujoco": importlib.metadata.version("mujoco"),
        "numpy": importlib.metadata.version("numpy")}
    execution = {"schema": "MOTOR-POPULATION-ACTIVITY-SURVEY-EXECUTION.1", "status": "COMPLETE",
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "inventory_sha256": survey.INVENTORY_SHA256, "preregistration_sha256": survey.PREREGISTRATION_SHA256,
        "environment": environment, "neural_transitions": result["neural_steps"],
        "physics_transitions": result["physics_steps"], "admitted_motor_channels": 11,
        "physical_action_entries": 42, "stimulation_applied": False, "extra_forces_applied": False}
    execution_hash = _write_exclusive(survey.EXECUTION_MANIFEST_PATH, survey.canonical_json(execution).encode())
    final = {"schema": "MOTOR-POPULATION-ACTIVITY-SURVEY-FINAL.1", "status": "COMPLETE",
        "artifacts": {survey.RAW_PATH.name: raw_hash, survey.REPORT_PATH.name: report_hash,
                      survey.EXECUTION_MANIFEST_PATH.name: execution_hash}}
    _write_exclusive(survey.FINAL_MANIFEST_PATH, survey.canonical_json(final).encode())
    return report
