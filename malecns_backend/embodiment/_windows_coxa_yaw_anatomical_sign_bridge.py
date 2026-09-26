"""Dependency-gated FlyGym/MuJoCo kinematics for the anatomical sign bridge."""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import platform
import subprocess
from typing import Any

from . import coxa_yaw_anatomical_sign_bridge as spec
from . import _windows_candidate_motor_mechanical_validation as mechanics


def _digest(np: Any, *arrays: Any) -> str:
    digest = hashlib.sha256()
    for value in arrays:
        array = np.asarray(value)
        digest.update(str(array.dtype).encode())
        digest.update(str(array.shape).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def _construct(flygym: Any) -> tuple[Any, Any, Any]:
    fly = flygym.Fly(enable_adhesion=False, control="position")
    simulation = getattr(flygym, "SingleFlySimulation", None) or \
        importlib.import_module("flygym.simulation").SingleFlySimulation
    sim = simulation(fly=fly, cameras=[], timestep=.0001)
    sim.reset()  # initialization, not a time-advancing dynamics transition
    physics = next((x.physics for x in (sim, getattr(sim, "env", None), getattr(sim, "_env", None))
                    if x is not None and getattr(x, "physics", None) is not None), None)
    if physics is None:
        sim.close()
        raise RuntimeError("compiled FlyGym physics unavailable")
    return fly, sim, physics


def _geometry_audit(model: Any, data: Any, np: Any, root_body_id: int) -> dict[str, Any]:
    """Capture the Coxa body and every downstream compiled body/geom/site."""
    def optional_name(kind: str, object_id: int) -> str | None:
        try:
            return mechanics._name(model, kind, object_id)
        except RuntimeError:
            return None

    descendants = {root_body_id}
    changed = True
    while changed:
        changed = False
        for body_id, parent_id in enumerate(np.asarray(model.body_parentid, dtype=int)):
            if parent_id in descendants and body_id not in descendants:
                descendants.add(body_id)
                changed = True
    bodies = [{"id": i, "name": mechanics._name(model, "body", i),
               "parent_id": int(model.body_parentid[i]),
               "position_world": np.asarray(data.xpos[i]).tolist(),
               "orientation_xmat_world": np.asarray(data.xmat[i]).tolist()}
              for i in sorted(descendants)]
    geoms = [{"id": i, "name": optional_name("geom", i), "body_id": int(body_id),
              "position_world": np.asarray(data.geom_xpos[i]).tolist(),
              "orientation_xmat_world": np.asarray(data.geom_xmat[i]).tolist()}
             for i, body_id in enumerate(np.asarray(model.geom_bodyid, dtype=int)) if body_id in descendants]
    sites = [{"id": i, "name": optional_name("site", i), "body_id": int(body_id),
              "position_world": np.asarray(data.site_xpos[i]).tolist(),
              "orientation_xmat_world": np.asarray(data.site_xmat[i]).tolist()}
             for i, body_id in enumerate(np.asarray(model.site_bodyid, dtype=int)) if body_id in descendants]
    return {"root_coxa_body_id": root_body_id, "bodies": bodies, "geoms": geoms, "sites": sites}


def _snapshot(flygym: Any, mujoco: Any, np: Any, joint: str, action_index: int,
              landmark_name: str, delta: float) -> dict[str, Any]:
    fly, sim, physics = _construct(flygym)
    try:
        model, data = physics.model, physics.data
        jid = mechanics._resolve_unique(model, "joint", joint, int(model.njnt))
        aid = mechanics._resolve_unique(model, "actuator", f"actuator_position_{joint}", int(model.nu))
        mechanics.validate_identity(tuple(fly.actuated_joints), action_index,
            mechanics._name(model, "actuator", aid), mechanics._name(model, "joint", jid),
            int(np.asarray(model.actuator_trnid)[aid, 0]), jid, joint)
        landmark_id = mechanics._resolve_unique(model, "body", landmark_name, int(model.nbody))
        thorax_id = mechanics._resolve_unique(model, "body", "Thorax", int(model.nbody))
        head_id = mechanics._resolve_unique(model, "body", "Head", int(model.nbody))
        abdomen_id = mechanics._resolve_unique(model, "body", "A1A2", int(model.nbody))
        qidx = int(np.asarray(model.jnt_qposadr)[jid])
        owner_id = int(np.asarray(model.jnt_bodyid)[jid])
        mechanics._forward(physics, mujoco)
        baseline_qpos = np.asarray(data.qpos).copy()
        baseline_qvel = np.asarray(data.qvel).copy()
        baseline_ctrl = np.asarray(data.ctrl).copy()
        thorax_xmat = np.asarray(data.xmat[thorax_id], dtype=float).reshape(3, 3).copy()
        anterior = thorax_xmat[:, 0].copy()
        anterior /= np.linalg.norm(anterior)
        thorax = np.asarray(data.xpos[thorax_id], dtype=float).copy()
        head = np.asarray(data.xpos[head_id], dtype=float).copy()
        abdomen = np.asarray(data.xpos[abdomen_id], dtype=float).copy()
        head_projection = float(np.dot(head - thorax, anterior))
        abdomen_projection = float(np.dot(abdomen - thorax, anterior))
        if not (head_projection > spec.METRIC_TOLERANCE and abdomen_projection < -spec.METRIC_TOLERANCE):
            raise RuntimeError("compiled head/abdomen landmarks do not establish Thorax +X as anterior")
        baseline_landmark = np.asarray(data.xpos[landmark_id], dtype=float).copy()
        baseline_owner_xmat = np.asarray(data.xmat[owner_id], dtype=float).copy()
        local_axis = np.asarray(model.jnt_axis[jid], dtype=float).copy()
        world_axis = np.asarray(data.xaxis[jid], dtype=float).copy() if hasattr(data, "xaxis") \
            else baseline_owner_xmat.reshape(3, 3) @ local_axis
        world_axis /= np.linalg.norm(world_axis)
        model_identity = _digest(np, model.jnt_axis, model.jnt_bodyid, model.jnt_qposadr,
                                 model.actuator_trnid, baseline_qpos, baseline_qvel, baseline_ctrl,
                                 thorax_xmat, thorax, head, abdomen, baseline_landmark)
        compiled_geometry = _geometry_audit(model, data, np, owner_id)
        action = spec.isolated_action(action_index, delta)
        data.qpos[:] = baseline_qpos
        data.qpos[qidx] += delta
        mechanics.assert_isolated(baseline_qpos, np.asarray(data.qpos), qidx,
                                  float(baseline_qpos[qidx] + delta))
        mechanics._forward(physics, mujoco)
        landmark = np.asarray(data.xpos[landmark_id], dtype=float).copy()
        displacement = landmark - baseline_landmark
        angle, direction = mechanics._rotation(np, data.xmat[owner_id], baseline_owner_xmat)
        signed_rotation = angle * float(np.dot(np.asarray(direction), world_axis))
        return {
            "model_identity_sha256": model_identity,
            "joint_id": jid, "actuator_id": aid, "qpos_index": qidx,
            "joint_axis_local": local_axis.tolist(), "joint_axis_world_baseline": world_axis.tolist(),
            "joint_range_rad": np.asarray(model.jnt_range[jid], dtype=float).tolist(),
            "joint_qpos_baseline_rad": float(baseline_qpos[qidx]),
            "joint_qpos_perturbed_rad": float(data.qpos[qidx]), "joint_delta_rad": delta,
            "thorax_body_id": thorax_id, "thorax_position_world": thorax.tolist(),
            "thorax_xmat_world": thorax_xmat.reshape(-1).tolist(),
            "anterior_axis_world": anterior.tolist(), "head_position_world": head.tolist(),
            "abdomen_position_world": abdomen.tolist(), "head_anterior_projection": head_projection,
            "abdomen_anterior_projection": abdomen_projection,
            "landmark_body_id": landmark_id, "landmark_body": landmark_name,
            "baseline_landmark_coordinates_world": baseline_landmark.tolist(),
            "perturbed_landmark_coordinates_world": landmark.tolist(),
            "landmark_displacement_world": displacement.tolist(),
            "baseline_metric": 0.0,
            "projected_anterior_displacement": float(np.dot(displacement, anterior)),
            "owner_orientation_baseline": baseline_owner_xmat.tolist(),
            "owner_orientation_perturbed": np.asarray(data.xmat[owner_id]).tolist(),
            "axis_projected_mechanical_rotation_rad": signed_rotation,
            "nonzero_action_indices": [i for i, value in enumerate(action) if value != 0.0],
            "compiled_coxa_and_downstream_geometry_baseline": compiled_geometry,
            "physics_transitions": 0, "kinematic_forwards": 2,
        }
    finally:
        sim.close()


def execute() -> dict[str, Any]:
    spec.preflight()
    spec.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with spec.ATTEMPT_PATH.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump({"status": "STARTED", "preregistration_sha256": spec.PREREGISTRATION_SHA256},
                  stream, indent=2, sort_keys=True)
        stream.write("\n")
    np, flygym, mujoco = (importlib.import_module(x) for x in ("numpy", "flygym", "mujoco"))
    legs = {}
    for leg, joint, index, landmark in spec.TARGETS:
        plus = _snapshot(flygym, mujoco, np, joint, index, landmark, spec.EPSILON_RAD)
        minus = _snapshot(flygym, mujoco, np, joint, index, landmark, -spec.EPSILON_RAD)
        baseline_distance = float(np.linalg.norm(
            np.asarray(plus["baseline_landmark_coordinates_world"]) -
            np.asarray(minus["baseline_landmark_coordinates_world"])))
        rotations = (plus["axis_projected_mechanical_rotation_rad"],
                     minus["axis_projected_mechanical_rotation_rad"])
        plus_displacement = np.asarray(plus["landmark_displacement_world"], dtype=float)
        minus_displacement = np.asarray(minus["landmark_displacement_world"], dtype=float)
        qpos_opposed = (abs(plus["joint_delta_rad"] - spec.EPSILON_RAD) <= 1e-12 and
                        abs(minus["joint_delta_rad"] + spec.EPSILON_RAD) <= 1e-12)
        endpoint_motion_opposed = (float(np.linalg.norm(plus_displacement)) > spec.METRIC_TOLERANCE and
                                   float(np.linalg.norm(minus_displacement)) > spec.METRIC_TOLERANCE and
                                   float(np.dot(plus_displacement, minus_displacement)) < 0.0)
        evidence = {
            "leg": leg, "joint": joint, "action_index": index,
            "body_fixed_anatomical_frame": "baseline compiled Thorax body frame; local +X is anterior",
            "landmark": landmark, "positive": plus, "negative": minus,
            "baseline_landmark_separation": baseline_distance,
            "fresh_baseline_identical": (plus["model_identity_sha256"] == minus["model_identity_sha256"] and
                                         baseline_distance <= spec.BASELINE_TOLERANCE),
            "geometry_identity_valid": (plus["nonzero_action_indices"] ==
                                        minus["nonzero_action_indices"] == [index]),
            "mechanical_valid": (qpos_opposed and endpoint_motion_opposed and
                                 rotations[0] > spec.METRIC_TOLERANCE and
                                 rotations[1] < -spec.METRIC_TOLERANCE),
            "mechanical_rotation_evidence": {
                "positive_axis_projection_rad": rotations[0],
                "negative_axis_projection_rad": rotations[1],
                "qpos_opposed": qpos_opposed,
                "landmark_displacement_dot_product": float(np.dot(plus_displacement, minus_displacement)),
                "landmark_motion_opposed": endpoint_motion_opposed,
            },
        }
        classification = spec.classify_leg(evidence)
        anterior_sign, posterior_sign = spec.coordinate_signs(classification)
        evidence.update(classification=classification,
                        derived_anterior_coordinate_sign=anterior_sign,
                        derived_posterior_coordinate_sign=posterior_sign)
        legs[leg] = evidence
    versions = {name: importlib.metadata.version(name) for name in ("flygym", "mujoco", "numpy")}
    try:
        git_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=spec.ROOT, check=True,
                                    capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        git_commit = None
    result = {
        "schema": "COXA-YAW-ANATOMICAL-SIGN-BRIDGE-RESULT.1", "scientific_execution_occurred": True,
        "geometry_only": True, "epsilon_rad": spec.EPSILON_RAD,
        "tolerances": {"metric": spec.METRIC_TOLERANCE, "baseline": spec.BASELINE_TOLERANCE,
                       "opposition": spec.OPPOSITION_TOLERANCE},
        "environment": {**versions, "python": platform.python_version(), "git_commit": git_commit},
        "neural_transitions": 0, "physics_transitions": 0, "stimulation": False,
        "extra_forces": False, "active_interface_count": 11, "active_interface_modified": False,
        "physical_motor_interface_length": 42, "physical_motor_interface_modified": False,
        "kinematic_propagation_only": True, "dynamics_step_called": False, "legs": legs,
    }
    with spec.RESULT_PATH.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return result
