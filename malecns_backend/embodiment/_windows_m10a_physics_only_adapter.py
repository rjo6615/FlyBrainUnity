"""Pinned physics-only execution boundary for a future authorized M10A run.

This module contains no neural, sensory, motor-decoding, controller, reward,
or reference-trajectory interface.  Importing it is inert.
"""
from __future__ import annotations

import hashlib
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
from . import m7c_b2_pose_geometry_audit as pose_geometry
from . import m7c_b4_stability as corrected_static
from . import m8_contact_kinematics as contact
from . import m10a_physics_only_calibration as m10a

RAW_PATH = m10a.OUTPUT_DIR / "m10a_raw.npz"


def _modules() -> tuple[Any, Any, dict[str, Any]]:
    np, flygym = (importlib.import_module(name) for name in ("numpy", "flygym"))
    versions = {name: importlib.metadata.version(name) for name in ("flygym", "mujoco")}
    if versions != {"flygym": "1.2.1", "mujoco": "3.2.7"}:
        raise RuntimeError(f"pinned physics versions required; found {versions}")
    versions["module_paths"] = {name: str(Path(importlib.import_module(name).__file__).resolve())
        for name in ("numpy", "flygym", "mujoco")}
    return np, flygym, versions


def _runtime(flygym: Any) -> tuple[Any, Any, Any]:
    np = importlib.import_module("numpy")
    surface = corrected_static._surface()
    sim = corrected_static._make_sim(flygym, surface)
    reset = sim.reset()
    observation = reset[0] if isinstance(reset, tuple) else reset
    physics = pose_geometry._physics(sim)
    forward = getattr(physics, "forward", None)
    if forward:
        forward()
    refresh = getattr(sim, "get_observation", None)
    if refresh:
        observation = refresh()
    commands = np.asarray(observation["joints"], dtype=float)
    if commands.ndim == 2:
        commands = commands[0]
    if commands.shape != (42,):
        raise RuntimeError("corrected baseline must contain exactly 42 joint targets")
    expected = json.loads(corrected_static.B3_PATH.read_text(encoding="utf-8"))["zero_step_reconstruction"]["controlled_joint_positions"]
    if (not np.array_equal(commands, expected) or tuple(physics.data.qpos[:3]) != m7d.SPAWN_POS
            or not corrected_static._calibration_unchanged(
                sim, np, importlib.import_module("mujoco"), surface)):
        sim.close()
        raise RuntimeError("exact frozen corrected static initialization was not reproduced")
    return sim, physics, commands.copy()


def _body_identity(model: Any) -> dict[str, Any]:
    names = {index: contact.compiled_name(model, "body", index) for index in range(int(model.nbody))}
    matches = [index for index, name in names.items()
        if contact.namespace_component(name) == m10a.APPLICATION_BODY_SOURCE]
    if len(matches) != 1 or matches[0] == 0:
        raise RuntimeError("authoritative Thorax must resolve uniquely to a non-world body")
    index = matches[0]
    return {"body_id": index, "body_name": names[index],
        "source_body_name": m10a.APPLICATION_BODY_SOURCE,
        "resolution": "unique exact terminal slash-delimited component"}


def _sample(np: Any, physics: Any, identity: Mapping[str, Any], body_id: int) -> dict[str, Any]:
    qpos, qvel = np.asarray(physics.data.qpos), np.asarray(physics.data.qvel)
    quaternion = qpos[3:7].copy()
    body_up_z = 1.0 - 2.0 * (quaternion[1] ** 2 + quaternion[2] ** 2)
    contacts, feet = contact.sample(physics, identity)
    velocity = np.asarray(physics.data.cvel[body_id], dtype=float)
    fields = (qpos, qvel, velocity, feet)
    return {"time_ms": float(physics.data.time * 1000.0),
        "thorax_com_position": np.asarray(physics.data.xipos[body_id], dtype=float).copy(),
        "root_position": qpos[:3].copy(), "root_orientation_wxyz": quaternion,
        "body_up_z": float(body_up_z), "linear_velocity": velocity[3:6].copy(),
        "angular_velocity": velocity[:3].copy(), "height": float(qpos[2]),
        "joint_positions": qpos[7:49].copy(), "ground_contact": contacts.copy(),
        "distal_tarsus_positions": feet.copy(),
        "finite": bool(all(np.isfinite(field).all() for field in fields))}


def _run_condition(np: Any, flygym: Any, magnitude: float) -> tuple[dict[str, Any], dict[str, Any]]:
    sim, physics, commands = _runtime(flygym)
    try:
        body, identity = _body_identity(physics.model), contact.resolve(physics.model)
        if not identity["available"]:
            raise RuntimeError("authoritative contact identity unavailable")
        rows = []
        for state_index in range(m10a.STATES):
            row = _sample(np, physics, identity, body["body_id"])
            if not math.isclose(row["time_ms"], state_index * m10a.DT_MS, abs_tol=1e-7):
                raise RuntimeError("physics clock/cadence mismatch")
            force = np.asarray(m10a.force_at_transition(magnitude, state_index), dtype=float) \
                if state_index < m10a.TRANSITIONS else np.zeros(3)
            row["applied_external_force"] = force.copy()
            rows.append(row)
            if state_index == m10a.TRANSITIONS:
                break
            physics.data.xfrc_applied[:] = 0.0
            physics.data.xfrc_applied[body["body_id"], :3] = force
            physics.data.xfrc_applied[body["body_id"], 3:] = 0.0
            nonzero = np.flatnonzero(np.any(np.asarray(physics.data.xfrc_applied) != 0, axis=1))
            if (force.any() and nonzero.tolist() != [body["body_id"]]) or (not force.any() and nonzero.size):
                raise RuntimeError("external force escaped its body or interval")
            sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})
        arrays = {key: np.asarray([row[key] for row in rows]) for key in rows[0]}
        provenance = {"force_body": body, "contact_identity": identity,
            "fixed_commands_sha256": hashlib.sha256(commands.tobytes()).hexdigest()}
        return arrays, provenance
    finally:
        sim.close()


def _norm(np: Any, values: Any) -> Any:
    return np.linalg.norm(values.reshape((len(values), -1)), axis=1)


def _reduce(np: Any, candidate: Mapping[str, Any], control: Mapping[str, Any], magnitude: float) -> dict[str, Any]:
    if not np.array_equal(candidate["time_ms"], control["time_ms"]):
        raise RuntimeError("candidate/control timestamps differ")
    pre = candidate["time_ms"] <= m10a.START_MS
    for key in ("thorax_com_position", "root_position", "root_orientation_wxyz", "linear_velocity",
                "angular_velocity", "joint_positions", "ground_contact", "distal_tarsus_positions"):
        if not np.array_equal(candidate[key][pre], control[key][pre]):
            raise RuntimeError("candidate/control pre-force trajectories differ")
    position_delta = candidate["thorax_com_position"] - control["thorax_com_position"]
    quaternion_dot = np.abs(np.sum(candidate["root_orientation_wxyz"] * control["root_orientation_wxyz"], axis=1))
    orientation_delta = np.degrees(2.0 * np.arccos(np.clip(quaternion_dot, 0.0, 1.0)))
    feet_delta = np.linalg.norm(candidate["distal_tarsus_positions"] - control["distal_tarsus_positions"], axis=2)
    contact_delta = np.logical_xor(candidate["ground_contact"], control["ground_contact"])
    initial = candidate["root_position"][0]
    displacement = _norm(np, candidate["root_position"] - initial)
    tilt = np.degrees(np.arccos(np.clip(candidate["body_up_z"], -1.0, 1.0)))
    through_750 = candidate["time_ms"] <= 750.0
    catastrophic = bool(np.any(((candidate["height"] <= initial[2] * 0.5)
        | (candidate["body_up_z"] <= 0.0) | (displacement > 1.5)) & through_750))
    post = candidate["time_ms"] >= m10a.STOP_MS
    continuous = max(float(_norm(np, position_delta).max()), float(orientation_delta.max()),
        float(feet_delta.max()), float(_norm(np, candidate["linear_velocity"] - control["linear_velocity"]).max()),
        float(_norm(np, candidate["angular_velocity"] - control["angular_velocity"]).max()))
    return {"magnitude_native": magnitude,
        "finite": bool(candidate["finite"].all() and control["finite"].all()),
        "catastrophic_through_750ms": catastrophic,
        "max_absolute_root_displacement_mm": float(displacement.max()),
        "max_absolute_tilt_deg": float(tilt.max()),
        "post_force_observation_ms": m10a.DURATION_MS - m10a.STOP_MS,
        "max_continuous_divergence": continuous,
        "max_root_position_divergence_mm": float(_norm(np, position_delta).max()),
        "max_orientation_divergence_deg": float(orientation_delta.max()),
        "max_distal_tarsus_divergence_mm": float(feet_delta.max()),
        "contact_pattern_diverged": bool(contact_delta.any()),
        "peak_linear_velocity": float(_norm(np, candidate["linear_velocity"]).max()),
        "peak_angular_velocity": float(_norm(np, candidate["angular_velocity"]).max()),
        "post_perturbation_trajectory_deviation_mm": float(_norm(np, position_delta)[post].max())}


def _exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def run_windows() -> dict[str, Any]:
    """Execute only after separate authorization; never called by preflight."""
    preflight = m10a.preflight()
    m7d.verify_b4()
    m7d.verify_m7()
    np, flygym, environment = _modules()
    control, control_provenance = _run_condition(np, flygym, m10a.CONTROL_FORCE_NATIVE)
    raw = {f"control_{key}": value for key, value in control.items()}
    rows, provenance = [], {}
    for index, magnitude in enumerate(m10a.CANDIDATE_FORCE_NATIVE):
        candidate, candidate_provenance = _run_condition(np, flygym, magnitude)
        rows.append(_reduce(np, candidate, control, magnitude))
        provenance[f"candidate_{index}"] = candidate_provenance
        raw.update({f"candidate_{index}_{key}": value for key, value in candidate.items()})
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **raw)
    _exclusive(RAW_PATH, buffer.getvalue())
    selected = m10a.select_force_series(rows)
    report = {"schema": m10a.SCHEMA, "status": "COMPLETE", "protocol": m10a.protocol(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "preflight": preflight, "environment": environment, "control_provenance": control_provenance,
        "candidate_provenance": provenance, "candidate_results": rows,
        "selected_force_series_native": selected, "physics_only": True,
        "neural_transitions": 0, "sensory_encoding_or_delivery_count": 0,
        "neural_motor_decode_or_application_count": 0}
    _exclusive(m10a.REPORT_PATH, (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
    manifest = {"schema": m10a.SCHEMA, "status": "COMPLETE",
        "raw": {"path": RAW_PATH.name, "byte_size": RAW_PATH.stat().st_size,
            "sha256": hashlib.sha256(RAW_PATH.read_bytes()).hexdigest()},
        "report": {"path": m10a.REPORT_PATH.name, "byte_size": m10a.REPORT_PATH.stat().st_size,
            "sha256": hashlib.sha256(m10a.REPORT_PATH.read_bytes()).hexdigest()}}
    _exclusive(m10a.MANIFEST_PATH, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    return report


__all__ = ["run_windows"]
