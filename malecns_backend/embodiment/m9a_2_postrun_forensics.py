"""Read-only M9A/M9A-2 post-run forensics.

This module has no simulation imports.  It reads the eight canonical NPZ files,
compares telemetry, and atomically writes only to a separate forensic directory.
It intentionally fails closed when any canonical input is absent.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
ATTEMPT1_DIR = HERE / "interface_output" / "m9a_perturbation_calibration"
ATTEMPT2_DIR = HERE / "interface_output" / "m9a_2_perturbation_calibration"
OUTPUT_DIR = HERE / "interface_output" / "m9a_2_postrun_forensics"
REPORT_PATH = OUTPUT_DIR / "m9a_2_postrun_forensics.json"
DT_MS = 0.1
CANDIDATES = (
    (0.0001, ATTEMPT1_DIR / "candidate_0.0001_raw.npz"),
    (0.0002, ATTEMPT1_DIR / "candidate_0.0002_raw.npz"),
    (0.0004, ATTEMPT1_DIR / "candidate_0.0004_raw.npz"),
    (0.0008, ATTEMPT1_DIR / "candidate_0.0008_raw.npz"),
    (0.002, ATTEMPT2_DIR / "candidate_0.002000_raw.npz"),
    (0.008, ATTEMPT2_DIR / "candidate_0.008000_raw.npz"),
    (0.032, ATTEMPT2_DIR / "candidate_0.032000_raw.npz"),
    (0.128, ATTEMPT2_DIR / "candidate_0.128000_raw.npz"),
)
REQUIRED = ("time_ms", "root_position", "orientation_wxyz", "body_up_z",
            "linear_velocity", "angular_velocity", "ground_contact",
            "distal_tarsus_positions", "applied_force")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


def inventory() -> list[dict[str, Any]]:
    """Hash before parsing; absence is fatal rather than silently partial."""
    missing = [str(p) for _, p in CANDIDATES if not p.is_file()]
    if missing: raise FileNotFoundError("missing canonical raw evidence: " + ", ".join(missing))
    return [{"magnitude_native": m, "path": str(p.resolve()), "byte_size": p.stat().st_size,
             "sha256": _sha(p)} for m, p in CANDIDATES]


def _first(mask: Any, times: Any) -> float | None:
    import numpy as np
    i = np.flatnonzero(mask)
    return None if not i.size else float(times[int(i[0])])


def _load(np: Any, path: Path) -> dict[str, Any]:
    # allow_pickle=False is a deliberate evidence boundary.
    with np.load(path, allow_pickle=False) as z:
        absent = sorted(set(REQUIRED) - set(z.files))
        if absent: raise ValueError(f"{path}: missing arrays {absent}")
        return {name: np.array(z[name], copy=True) for name in z.files}


def _force_audit(np: Any, a: Mapping[str, Any], magnitude: float) -> dict[str, Any]:
    t, f = a["time_ms"], a["applied_force"]
    if f.shape != (len(t), 3): raise ValueError("applied_force shape mismatch")
    nz = np.flatnonzero(np.any(f != 0.0, axis=1)); intended = (t >= 500.0-1e-7) & (t < 520.0-1e-7)
    exact = np.array([0.0, magnitude, 0.0])
    return {"exists": True, "nonzero_sample_count": int(nz.size),
        "nonzero_indices": nz.tolist(), "first_scheduled_timestamp_ms": float(t[nz[0]]) if nz.size else None,
        "last_scheduled_timestamp_ms": float(t[nz[-1]]) if nz.size else None,
        "unique_nonzero_vectors": np.unique(f[nz], axis=0).tolist(),
        "exact_direction_xyz": [0.0, 1.0, 0.0], "exact_magnitude_native": magnitude,
        "all_nonzero_samples_exact": bool(nz.size and np.all(f[nz] == exact)),
        "zero_outside_window": bool(np.all(f[~intended] == 0.0)),
        "window_indices_exact": bool(np.array_equal(nz, np.flatnonzero(intended))),
        "recorded_impulse_native_force_ms": (f.sum(axis=0) * DT_MS).tolist(),
        "recorded_impulse_magnitude_native_force_ms": float(np.linalg.norm(f.sum(axis=0)*DT_MS))}


def _normmax(np: Any, x: Any) -> float:
    return float(np.linalg.norm(x.reshape((len(x), -1)), axis=1).max())


def _trajectory(np: Any, base: Mapping[str, Any], a: Mapping[str, Any]) -> dict[str, Any]:
    if not np.array_equal(base["time_ms"], a["time_ms"]): raise ValueError("timestamps are not exactly aligned")
    t = a["time_ms"]; fields = ("root_position", "linear_velocity", "orientation_wxyz",
        "body_up_z", "angular_velocity", "ground_contact", "distal_tarsus_positions")
    different = np.zeros(len(t), dtype=bool); maxima, windows = {}, {}
    for key in fields:
        d = a[key] != base[key]; row = d if d.ndim == 1 else np.any(d.reshape((len(t), -1)), axis=1)
        different |= row
        maxima[key] = (float(np.max(np.abs(a[key]-base[key]))) if key != "ground_contact"
                       else int(np.count_nonzero(d)))
        windows[key] = {name: (float(np.max(np.abs(a[key][mask]-base[key][mask]))) if np.any(mask) else None)
            for name, mask in (("pre_499.9_ms", t < 500), ("during_500_to_519.9_ms", (t>=500)&(t<520)),
                               ("post_from_520_ms", t>=520))}
    return {"first_exact_divergence_ms": _first(different, t), "max_absolute_component_difference": maxima,
            "window_max_absolute_component_difference": windows,
            "root_position_euclidean_max_mm": _normmax(np, a["root_position"]-base["root_position"]),
            "root_velocity_euclidean_max": _normmax(np, a["linear_velocity"]-base["linear_velocity"]),
            "angular_velocity_euclidean_max": _normmax(np, a["angular_velocity"]-base["angular_velocity"]),
            "distal_tarsus_euclidean_max_mm": float(np.linalg.norm(a["distal_tarsus_positions"]-base["distal_tarsus_positions"],axis=2).max())}


def _static_audit() -> dict[str, Any]:
    from . import _windows_m9a_2_perturbation_calibration_adapter as live
    source = inspect.getsource(live._run_candidate)
    return {"documented_mujoco_facts": {
        "source": "MuJoCo 3.2.7 documentation: Computation / General framework and API data field documentation",
        "xfrc_applied": "nbody x 6 Cartesian force/torque applied to each body; force precedes torque",
        "frame": "world coordinates", "point": "body center of mass"},
      "source_derived_facts": {"pinned_versions": {"flygym":"1.2.1","mujoco":"3.2.7"},
        "force_written_directly": "physics.data.xfrc_applied[body_id, :3] = force",
        "torque_zeroed": "physics.data.xfrc_applied[body_id, 3:] = 0",
        "array_cleared_before_each_transition": "physics.data.xfrc_applied[:] = 0",
        "force_then_step_order_verified": source.index("xfrc_applied[body") < source.index("sim.step("),
        "recording_semantics": "state t is inspected; force(t) is recorded; then the same force is written for outgoing t -> t+0.1 ms",
        "flygym_scaling_or_transform_at_callsite": "none; direct write through dm_control Physics.data before sim.step",
        "actuation": "fixed 42-joint baseline command and six zero adhesion commands are supplied every step",
        "overwrite_risk": "the repository callsite does not overwrite xfrc_applied after its write; whether deeper FlyGym/dm_control code clears it requires the exact installed source snapshot"},
      "model_facts": {"thorax_mass": None, "total_fly_mass": None,
        "unit_convention": "preregistration declares mm-ms-mg; exact authoritative compiled model is not preserved in NPZ telemetry",
        "determination": "not determinable from the repository/NPZs without the exact installed model or compiled-model dump"},
      "inference": "The ordering rules out an inspection-before-write/off-by-one error at this callsite. Telemetry proves scheduling, not that deeper code consumed the array."}


def analyze() -> dict[str, Any]:
    before = inventory()
    import numpy as np
    arrays = [_load(np, p) for _, p in CANDIDATES]
    force = [_force_audit(np, a, m) for (m, _), a in zip(CANDIDATES, arrays)]
    base = arrays[0]; comparisons = [{"magnitude_native": m, **_trajectory(np, base, a)}
        for (m, _), a in zip(CANDIDATES, arrays)]
    signal = [x["root_position_euclidean_max_mm"] for x in comparisons[1:]]
    monotonic = all(b >= a for a,b in zip(signal,signal[1:]))
    after = inventory()
    if before != after: raise RuntimeError("canonical evidence changed during analysis")
    static = _static_audit(); mass = static["model_facts"]["thorax_mass"]
    sanity = {"available": mass is not None, "formula": "delta_v = force * 20 ms / mass; acceleration = force / mass",
              "idealized": True, "caveat": "contacts, joints, constraints and actuators alter the response", "values": []}
    if mass:
        sanity["values"]=[{"magnitude_native":m,"acceleration_mm_per_ms2":m/mass,
            "delta_v_mm_per_ms":m*20/mass} for m,_ in CANDIDATES]
    max_shared = _normmax(np, base["root_position"]-base["root_position"][(base["time_ms"]>=450)&(base["time_ms"]<500)].mean(axis=0))
    max_between = max(signal)
    classification = ("FORCE_RESPONSE_PRESENT_AND_SCALING" if monotonic and max_between > 0 else
        "FORCE_EFFECT_NOT_DETECTABLE_IN_RECORDED_TRAJECTORIES" if max_between == 0 else
        "FORCE_RESPONSE_PRESENT_BUT_MASKED_BY_BASELINE_METRIC")
    return {"schema":"M9A-2-POSTRUN-FORENSICS.1", "status":"COMPLETE", "read_only":True,
      "physics_transitions":0,"neural_transitions":0,"male_cns_constructed":False,
      "evidence_before_and_after_identical":True,"evidence_inventory":before,"force_telemetry":force,
      "trajectory_comparisons_relative_to_0.0001":comparisons,
      "trajectory_scaling":{"root_position_difference_monotonic_non_decreasing":monotonic},
      "baseline_separation":{"smallest_candidate_motion_max_mm":max_shared,
        "largest_pairwise_force_dependent_position_difference_mm":max_between,
        "interpretation":"shared baseline dominates" if max_between < max_shared else "force-dependent difference is not smaller than shared motion",
        "compatible_zero_force_artifact":"none identified: M7D/M8 differ in duration and/or recorded schema and are not substituted"},
      "static_semantics_audit":static,"idealized_free_body_sanity_check":sanity,"classification":classification,
      "claim_limit":"Physical telemetry only; no biological-behavior classification."}


def write_report(report: Mapping[str, Any], path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); data=(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
    with os.fdopen(fd,"wb") as out: out.write(data); out.flush(); os.fsync(out.fileno())


def main(argv: Sequence[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--write-report",action="store_true"); args=p.parse_args(argv)
    report=analyze()
    if args.write_report: write_report(report)
    else: print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
    return 0

if __name__ == "__main__": raise SystemExit(main())
