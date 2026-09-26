"""Dependency-gated FlyGym/MuJoCo runner for Coxa-yaw mechanics only."""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
from typing import Any

from . import coxa_yaw_sign_validation as spec
from . import _windows_candidate_motor_mechanical_validation as mechanics


def _digest(np: Any, *arrays: Any) -> str:
    digest = hashlib.sha256()
    for value in arrays:
        array = np.asarray(value)
        digest.update(str(array.dtype).encode()); digest.update(str(array.shape).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def _one_direction(flygym: Any, mujoco: Any, np: Any, joint: str,
                   action_index: int, delta: float) -> dict[str, Any]:
    """Measure one sign in a newly constructed simulation without stepping it."""
    fly = flygym.Fly(enable_adhesion=False, control="position")
    simulation = getattr(flygym, "SingleFlySimulation", None) or \
        importlib.import_module("flygym.simulation").SingleFlySimulation
    sim = simulation(fly=fly, cameras=[], timestep=.0001)
    try:
        sim.reset()
        physics = next((x.physics for x in (sim, getattr(sim, "env", None), getattr(sim, "_env", None))
                        if x is not None and getattr(x, "physics", None) is not None), None)
        if physics is None:
            raise RuntimeError("compiled FlyGym physics unavailable")
        model, data = physics.model, physics.data
        aid = mechanics._resolve_unique(model, "actuator", f"actuator_position_{joint}", int(model.nu))
        jid = mechanics._resolve_unique(model, "joint", joint, int(model.njnt))
        mechanics.validate_identity(tuple(fly.actuated_joints), action_index,
            mechanics._name(model, "actuator", aid), mechanics._name(model, "joint", jid),
            int(np.asarray(model.actuator_trnid)[aid, 0]), jid, joint)
        qidx = int(np.asarray(model.jnt_qposadr)[jid]); body_id = int(np.asarray(model.jnt_bodyid)[jid])
        endpoint_id = mechanics._resolve_unique(model, "body", joint[6:8] + "Tarsus5", int(model.nbody))
        mechanics._forward(physics, mujoco)
        baseline_qpos = np.asarray(data.qpos).copy(); baseline_qvel = np.asarray(data.qvel).copy()
        baseline_ctrl = np.asarray(data.ctrl).copy(); baseline_xmat = np.asarray(data.xmat[body_id]).copy()
        baseline_endpoint = np.asarray(data.xpos[endpoint_id]).copy()
        baseline_hash = _digest(np, baseline_qpos, baseline_qvel, baseline_ctrl,
                                baseline_xmat, baseline_endpoint)
        action = spec.isolated_action(action_index, delta)
        data.qpos[:] = baseline_qpos; data.qpos[qidx] += delta
        mechanics.assert_isolated(baseline_qpos, np.asarray(data.qpos), qidx,
                                  float(baseline_qpos[qidx] + delta))
        mechanics._forward(physics, mujoco)
        angle, direction = mechanics._rotation(np, data.xmat[body_id], baseline_xmat)
        axis = np.asarray(data.xaxis[jid], dtype=float) if hasattr(data, "xaxis") else \
            baseline_xmat.reshape(3, 3) @ np.asarray(model.jnt_axis[jid], dtype=float)
        axis /= np.linalg.norm(axis)
        signed_rotation = angle * float(np.dot(np.asarray(direction), axis))
        endpoint = np.asarray(data.xpos[endpoint_id]).copy()
        return {"baseline_identity_sha256": baseline_hash,
            "joint_delta_rad": float(data.qpos[qidx] - baseline_qpos[qidx]),
            "axis_projection_rad": signed_rotation,
            "world_joint_axis_baseline": axis.tolist(),
            "endpoint_position": endpoint.tolist(),
            "endpoint_displacement_from_baseline": (endpoint - baseline_endpoint).tolist(),
            "segment_orientation_baseline": baseline_xmat.tolist(),
            "segment_orientation_perturbed": np.asarray(data.xmat[body_id]).tolist(),
            "nonzero_action_indices": [i for i, x in enumerate(action) if x != 0.0],
            "physics_transitions": 0}
    finally:
        sim.close()


def execute() -> dict[str, Any]:
    """Run once, reserving output paths before importing/constructing mechanics."""
    spec.verify_preregistration()
    if not spec.output_available():
        raise FileExistsError("result/attempt namespace is occupied; overwrite refused")
    spec.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with spec.ATTEMPT_PATH.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump({"status": "STARTED", "preregistration_sha256": spec.PREREGISTRATION_SHA256}, stream,
                  indent=2, sort_keys=True); stream.write("\n")
    np, flygym, mujoco = (importlib.import_module(x) for x in ("numpy", "flygym", "mujoco"))
    versions = {}
    for package in ("numpy", "flygym", "mujoco"):
        versions[package] = importlib.metadata.version(package)
    evidence = {}
    for _, joint, index in spec.TARGETS:
        plus = _one_direction(flygym, mujoco, np, joint, index, spec.EPSILON_RAD)
        minus = _one_direction(flygym, mujoco, np, joint, index, -spec.EPSILON_RAD)
        evidence[joint] = {"positive": plus, "negative": minus,
            "fresh_baseline_identical": plus["baseline_identity_sha256"] == minus["baseline_identity_sha256"],
            "action_isolation": plus["nonzero_action_indices"] == minus["nonzero_action_indices"] == [index],
            "neural_transitions": 0, "stimulation": False, "extra_force": False}
    result = {"status": spec.classify(evidence), "scientific_run_executed": True,
              "mechanical_only": True, "physics_transitions": 0, "neural_transitions": 0,
              "environment_versions": versions, "anatomical_coordinate_signs": None,
              "active_interface_modified": False, "active_interface_count": 11,
              "stimulation": False, "extra_force": False, "evidence": evidence}
    with spec.RESULT_PATH.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write("\n")
    return result
