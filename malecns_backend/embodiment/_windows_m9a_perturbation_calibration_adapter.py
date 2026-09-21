"""Live FlyGym/MuJoCo boundary for M9A; contains no neural-runtime import."""
from __future__ import annotations

import importlib
import importlib.metadata
import io
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping

from . import m7d_corrected_spontaneous as m7d
from . import m8_contact_kinematics as contact
from . import m9a_perturbation_calibration as m9a
from . import _windows_m7d_corrected_spontaneous_adapter as m7d_live


def _modules() -> tuple[Any, Any, Any, dict[str, Any]]:
    np, flygym, mujoco = (importlib.import_module(x) for x in ("numpy", "flygym", "mujoco"))
    versions = {"flygym": importlib.metadata.version("flygym"), "mujoco": importlib.metadata.version("mujoco")}
    if versions != {"flygym": "1.2.1", "mujoco": "3.2.7"}:
        raise RuntimeError(f"M9A requires FlyGym 1.2.1 and MuJoCo 3.2.7; found {versions}")
    versions["module_paths"] = {name: str(Path(module.__file__).resolve())
        for name, module in (("flygym", flygym), ("mujoco", mujoco), ("numpy", np))}
    return np, flygym, mujoco, versions


def _body_identity(model: Any, mujoco: Any) -> dict[str, Any]:
    names = {i: (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) or "")
             for i in range(int(model.nbody))}
    matches = [i for i, name in names.items() if name == m9a.APPLICATION_BODY_EXACT]
    if len(matches) != 1 or matches[0] == 0:
        raise RuntimeError("authoritative compiled MuJoCo Thorax body identity is not unique")
    return {"body_id": matches[0], "body_name": names[matches[0]],
        "resolution": "exact compiled MuJoCo body name", "all_body_names": names}


def _runtime(flygym: Any) -> tuple[Any, Any, Any, Any]:
    sim, physics, obs, _, _ = m7d_live._runtime(flygym, None)
    commands = importlib.import_module("numpy").asarray(obs["joints"], dtype=float)
    if commands.ndim == 2: commands = commands[0]
    return sim, physics, obs, commands.copy()


def _inspect(np: Any, physics: Any, identity: Mapping[str, Any], body_id: int) -> dict[str, Any]:
    qpos, qvel = np.asarray(physics.data.qpos), np.asarray(physics.data.qvel)
    quat = qpos[3:7]; up = 1.0 - 2.0 * (quat[1] ** 2 + quat[2] ** 2)
    flags, feet = contact.sample(physics, identity)
    cvel = np.asarray(physics.data.cvel[body_id], dtype=float)
    return {"time_ms": float(physics.data.time * 1000.0), "root_position": qpos[:3].copy(),
        "orientation_wxyz": quat.copy(), "body_up_z": float(up),
        "linear_velocity": cvel[3:6].copy(), "angular_velocity": cvel[:3].copy(),
        "ground_contact": flags.copy(), "distal_tarsus_positions": feet.copy(),
        "finite": bool(all(np.isfinite(x).all() for x in (qpos, qvel, cvel, feet)))}


def _run_candidate(np: Any, flygym: Any, mujoco: Any, magnitude: float) -> tuple[dict[str, Any], dict[str, Any]]:
    sim, physics, _obs, baseline = _runtime(flygym)
    try:
        body = _body_identity(physics.model, mujoco); identity = contact.resolve(physics.model)
        if not identity["available"]: raise RuntimeError("authoritative ground/tarsus identity unavailable")
        rows = []
        for step in range(m9a.STATES):
            state = _inspect(np, physics, identity, body["body_id"])
            scheduled_ms = step * m9a.DT_MS
            if not math.isclose(state["time_ms"], scheduled_ms, abs_tol=1e-7):
                raise RuntimeError("MuJoCo clock deviated from the frozen 0.1-ms cadence")
            force = np.asarray(m9a.force_at(scheduled_ms, magnitude), dtype=float)
            state["applied_force"] = force.copy(); rows.append(state)
            if step == m9a.TRANSITIONS: break
            physics.data.xfrc_applied[:] = 0.0
            physics.data.xfrc_applied[body["body_id"], :3] = force
            physics.data.xfrc_applied[body["body_id"], 3:] = 0.0
            nonzero = np.flatnonzero(np.any(np.asarray(physics.data.xfrc_applied) != 0.0, axis=1))
            if ((force != 0).any() and nonzero.tolist() != [body["body_id"]]) or ((force == 0).all() and nonzero.size):
                raise RuntimeError("external force escaped intended authoritative body/window")
            sim.step({"joints": baseline.copy(), "adhesion": np.zeros(6)})
        arrays = {key: np.asarray([r[key] for r in rows]) for key in rows[0]}
        return _reduce(np, arrays, magnitude, body, identity), arrays
    finally:
        sim.close()


def _reduce(np: Any, a: Mapping[str, Any], magnitude: float, body: Mapping[str, Any], identity: Mapping[str, Any]) -> dict[str, Any]:
    t, pos, up = a["time_ms"], a["root_position"], a["body_up_z"]
    pre = (t >= 450) & (t < 500); post = t >= 520; late = t >= 1250
    base_pos, base_up = pos[pre].mean(axis=0), float(up[pre].mean())
    displacement = np.linalg.norm(pos - base_pos, axis=1)
    tilt = np.degrees(np.arccos(np.clip(up, -1.0, 1.0)))
    base_tilt = float(np.degrees(np.arccos(np.clip(base_up, -1.0, 1.0))))
    tilt_delta = np.abs(tilt - base_tilt)
    peak_d, peak_t = float(displacement[post].max()), float(tilt_delta[post].max())
    late_d, late_t = float(displacement[late].mean()), float(tilt_delta[late].mean())
    reduce_d = 0.0 if peak_d == 0 else max(0.0, min(1.0, 1.0 - late_d / peak_d))
    reduce_t = 0.0 if peak_t == 0 else max(0.0, min(1.0, 1.0 - late_t / peak_t))
    initial_contacts = a["ground_contact"][pre][-1]
    changed = bool(np.any(a["ground_contact"][post] != initial_contacts, axis=1).any())
    fall = pos[:, 2] <= pos[0, 2] * 0.5; rollover = up <= 0.0; early = t <= 600
    def first(mask: Any) -> float | None:
        idx = np.flatnonzero(mask); return None if not idx.size else float(t[int(idx[0])])
    return {"magnitude_native": magnitude, "duration_ms": 20.0,
        "impulse_native_force_ms": magnitude * 20.0, "direction_xyz": list(m9a.DIRECTION),
        "application_body": {k: v for k, v in body.items() if k != "all_body_names"},
        "application_point": "body center of mass", "torque_xyz": [0.0, 0.0, 0.0],
        "finite": bool(a["finite"].all()), "first_fall_ms": first(fall),
        "first_rollover_ms": first(rollover),
        "fall_or_rollover_by_600ms": bool(np.any((fall | rollover) & early)),
        "maximum_root_displacement_mm": peak_d, "maximum_tilt_deg": peak_t,
        "maximum_linear_speed": float(np.linalg.norm(a["linear_velocity"], axis=1).max()),
        "maximum_angular_speed": float(np.linalg.norm(a["angular_velocity"], axis=1).max()),
        "authoritative_contact_pattern_changed": changed,
        "per_leg_contact_fraction": {leg: float(a["ground_contact"][:, i].mean()) for i, leg in enumerate(contact.LEGS)},
        "pre_state": {"root_position": base_pos.tolist(), "body_up_z": base_up,
            "distal_tarsus_positions": a["distal_tarsus_positions"][pre].mean(axis=0).tolist()},
        "final_state": {"root_position": pos[-1].tolist(), "body_height": float(pos[-1, 2]),
            "orientation_wxyz": a["orientation_wxyz"][-1].tolist(), "body_up_z": float(up[-1]),
            "linear_velocity": a["linear_velocity"][-1].tolist(), "angular_velocity": a["angular_velocity"][-1].tolist(),
            "ground_contact": a["ground_contact"][-1].tolist(),
            "distal_tarsus_positions": a["distal_tarsus_positions"][-1].tolist()},
        "post_force_displacement_reduction_fraction": reduce_d,
        "post_force_tilt_reduction_fraction": reduce_t,
        "returns_toward_pre_perturbation_state": max(reduce_d, reduce_t) >= 0.25}


def windows_preflight() -> dict[str, Any]:
    m9a.validate_protocol(m9a.protocol()); m7d.verify_b4(); m7d.verify_m7()
    np, flygym, mujoco, environment = _modules(); sim, physics, _, baseline = _runtime(flygym)
    try:
        body, identity = _body_identity(physics.model, mujoco), contact.resolve(physics.model)
        if not identity["available"]: raise RuntimeError("authoritative contact identity unavailable")
        if baseline.shape != (42,) or tuple(physics.data.qpos[:3]) != m7d.SPAWN_POS:
            raise RuntimeError("frozen corrected initialization mismatch")
    finally: sim.close()
    return {"schema": m9a.SCHEMA, "status": "PREFLIGHT_PASS", "environment": environment,
        "authoritative_force_body": {k: v for k, v in body.items() if k != "all_body_names"},
        "authoritative_contact_identity": {"method": identity["method"], "available": identity["available"]},
        "physics_transitions": 0, "neural_transitions": 0, "male_cns_constructed": False}


def _exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), "wb") as out:
        out.write(payload); out.flush(); os.fsync(out.fileno())


def run_windows() -> dict[str, Any]:
    if m9a.REPORT_PATH.exists() or m9a.MANIFEST_PATH.exists():
        raise FileExistsError("refusing to overwrite M9A calibration evidence")
    preflight = windows_preflight(); np, flygym, mujoco, environment = _modules()
    results, raw_evidence = [], []
    for magnitude in m9a.CANDIDATE_FORCE_NATIVE:
        row, arrays = _run_candidate(np, flygym, mujoco, magnitude)
        path = m9a.OUTPUT_DIR / f"candidate_{magnitude:.4f}_raw.npz"
        buffer = io.BytesIO(); np.savez_compressed(buffer, **arrays); _exclusive(path, buffer.getvalue())
        row["raw"] = {"path": str(path.resolve()), "sha256": m9a.sha256(path), "byte_size": path.stat().st_size}
        results.append(row); raw_evidence.append(row["raw"])
    selected = m9a.choose_candidate(results)
    report = {"schema": m9a.SCHEMA, "status": "COMPLETE", "classification": "EXTERNAL_PHYSICAL_PERTURBATION_CALIBRATED",
        "claim_limit": "M9A does not demonstrate balance, postural control, reflexes, biological function, or neural recovery.",
        "protocol": m9a.protocol(), "environment": environment, "preflight": preflight,
        "candidate_results": results, "selected_force_magnitude_native": selected,
        "selection_used_neural_behavior": False, "male_cns_constructed": False,
        "male_cns_transitions": 0, "neural_transitions": 0,
        "provenance": {"source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "m7d_b4_and_m7": {"b4": m7d.verify_b4(), "m7": m7d.verify_m7()}}}
    encoded = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(); _exclusive(m9a.REPORT_PATH, encoded)
    manifest = {"schema": m9a.SCHEMA, "status": "COMPLETE", "report": {"path": str(m9a.REPORT_PATH.resolve()),
        "sha256": m9a.sha256(m9a.REPORT_PATH), "byte_size": m9a.REPORT_PATH.stat().st_size}, "raw": raw_evidence,
        "male_cns_transitions": 0, "neural_transitions": 0}
    _exclusive(m9a.MANIFEST_PATH, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    return report


__all__ = ["run_windows", "windows_preflight"]
