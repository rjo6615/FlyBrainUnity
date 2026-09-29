"""MuJoCo forward-kinematics-only validation for six femur-roll coordinates."""
from __future__ import annotations

import importlib
import math
from typing import Any, Mapping

from . import femur_roll_validation as audit

EPSILON = 0.0001


def _terminal(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def _name(model: Any, kind: str, object_id: int) -> str:
    for args in ((object_id, kind), (kind, object_id)):
        try:
            value = model.id2name(*args)
        except (AttributeError, TypeError, ValueError, KeyError):
            continue
        if value is not None:
            return str(value)
    raise RuntimeError(f"compiled {kind} id {object_id} has no name")


def _resolve_unique(model: Any, kind: str, suffix: str, count: int) -> int:
    matches = [i for i in range(count) if _terminal(_name(model, kind, i)) == suffix]
    if len(matches) != 1:
        raise RuntimeError(f"expected one compiled {kind} named {suffix}; found {len(matches)}")
    return matches[0]


def validate_identity(ordered: tuple[str, ...], index: int, actuator: str, joint: str,
                      transmitted: int, joint_id: int, candidate: str) -> None:
    if (index >= len(ordered) or ordered[index] != candidate
            or _terminal(actuator) != f"actuator_position_{candidate}"
            or _terminal(joint) != candidate or transmitted != joint_id):
        raise RuntimeError(f"actuator/joint identity differs from expected for {candidate}")


def assert_isolated(neutral: Any, perturbed: Any, qpos_index: int, expected: float) -> None:
    changed = [i for i, (after, before) in enumerate(zip(perturbed, neutral)) if after != before]
    if changed != [qpos_index] or not math.isclose(float(perturbed[qpos_index]), float(expected),
                                                   rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError("perturbation did not affect exactly the expected qpos coordinate")


def _forward(physics: Any, mujoco: Any) -> None:
    forward = getattr(physics, "forward", None)
    if forward is not None:
        forward()
    else:
        mujoco.mj_forward(getattr(physics.model, "ptr", physics.model),
                          getattr(physics.data, "ptr", physics.data))


def _rotation(np: Any, current: Any, neutral: Any) -> tuple[float, list[float]]:
    relative = np.asarray(current).reshape(3, 3) @ np.asarray(neutral).reshape(3, 3).T
    vector = np.array([relative[2, 1] - relative[1, 2], relative[0, 2] - relative[2, 0],
                       relative[1, 0] - relative[0, 1]])
    angle = math.acos(float(np.clip((np.trace(relative) - 1) / 2, -1, 1)))
    norm = float(np.linalg.norm(vector))
    if angle <= 1e-12 or norm <= 1e-12:
        raise RuntimeError("relative segment rotation is unresolved")
    return angle, (vector / norm).tolist()


def mechanical_direction_resolved(evidence: Mapping[str, Any], tolerance: float = 1e-10) -> bool:
    world = evidence["world_joint_axis_neutral"]
    dot = lambda a, b: sum(float(x) * float(y) for x, y in zip(a, b))
    displacement = evidence["positive_minus_negative_endpoint_displacement"]
    return (evidence["positive"]["relative_segment_rotation_rad"] > tolerance
            and evidence["negative"]["relative_segment_rotation_rad"] > tolerance
            and dot(evidence["positive"]["world_rotation_axis_direction"], world) > 1 - 1e-7
            and dot(evidence["negative"]["world_rotation_axis_direction"], world) < -1 + 1e-7
            and math.sqrt(sum(float(x) ** 2 for x in displacement)) > tolerance)


def _one(flygym: Any, mujoco: Any, np: Any, candidate: str, index: int) -> dict[str, Any]:
    fly = flygym.Fly(enable_adhesion=False, control="position")
    simulation = getattr(flygym, "SingleFlySimulation", None) or importlib.import_module("flygym.simulation").SingleFlySimulation
    sim = simulation(fly=fly, cameras=[], timestep=.0001)
    try:
        physics = next((owner.physics for owner in (sim, getattr(sim, "env", None), getattr(sim, "_env", None))
                        if owner is not None and getattr(owner, "physics", None) is not None), None)
        if physics is None:
            raise RuntimeError("compiled FlyGym physics is unavailable without advancing simulation")
        model, data = physics.model, physics.data
        aid = _resolve_unique(model, "actuator", f"actuator_position_{candidate}", int(model.nu))
        jid = _resolve_unique(model, "joint", candidate, int(model.njnt))
        actuator, joint = _name(model, "actuator", aid), _name(model, "joint", jid)
        transmitted = int(np.asarray(model.actuator_trnid)[aid, 0])
        validate_identity(tuple(fly.actuated_joints), index, actuator, joint, transmitted, jid, candidate)
        body_id = int(np.asarray(model.jnt_bodyid)[jid]); qidx = int(np.asarray(model.jnt_qposadr)[jid])
        endpoint_id = _resolve_unique(model, "body", candidate[6:8] + "Tarsus5", int(model.nbody))
        _forward(physics, mujoco)
        neutral_qpos = np.asarray(data.qpos).copy(); neutral_xmat = np.asarray(data.xmat[body_id]).copy()
        neutral_endpoint = np.asarray(data.xpos[endpoint_id]).copy()
        local_axis = np.asarray(model.jnt_axis[jid], dtype=float)
        world_axis = np.asarray(data.xaxis[jid], dtype=float) if hasattr(data, "xaxis") else neutral_xmat.reshape(3, 3) @ local_axis
        evidence: dict[str, Any] = {
            "epsilon_rad": EPSILON, "qpos_index": qidx, "actuator_id": aid, "actuator_name": actuator,
            "joint_id": jid, "joint_name": joint, "transmitted_joint_id": transmitted,
            "owning_body_id": body_id, "owning_body_name": _name(model, "body", body_id),
            "owning_body_transform_xmat_neutral": neutral_xmat.tolist(), "local_joint_axis": local_axis.tolist(),
            "world_joint_axis_neutral": (world_axis / np.linalg.norm(world_axis)).tolist(),
            "neutral_qpos_rad": float(neutral_qpos[qidx]), "endpoint_body_id": endpoint_id,
            "endpoint_body_name": _name(model, "body", endpoint_id), "neutral_endpoint_position": neutral_endpoint.tolist(),
        }
        for label, delta in (("positive", EPSILON), ("negative", -EPSILON)):
            data.qpos[:] = neutral_qpos; data.qpos[qidx] += delta
            assert_isolated(neutral_qpos, np.asarray(data.qpos), qidx, neutral_qpos[qidx] + delta)
            _forward(physics, mujoco)
            endpoint = np.asarray(data.xpos[endpoint_id]).copy()
            angle, axis = _rotation(np, data.xmat[body_id], neutral_xmat)
            evidence[label] = {"requested_delta_rad": delta, "resulting_qpos_rad": float(data.qpos[qidx]),
                               "endpoint_position": endpoint.tolist(),
                               "endpoint_displacement_from_neutral": (endpoint - neutral_endpoint).tolist(),
                               "relative_segment_rotation_rad": angle, "world_rotation_axis_direction": axis,
                               "segment_transform_xmat": np.asarray(data.xmat[body_id]).tolist()}
        evidence["positive_minus_negative_endpoint_displacement"] = (np.asarray(evidence["positive"]["endpoint_position"]) - np.asarray(evidence["negative"]["endpoint_position"])).tolist()
        evidence["mechanical_coordinate_direction_resolved"] = mechanical_direction_resolved(evidence)
        return evidence
    finally:
        sim.close()


def run() -> int:
    np, flygym, mujoco = (importlib.import_module(name) for name in ("numpy", "flygym", "mujoco"))
    result = audit.build()
    calls = 0
    for name, (index, _, _, _) in audit.CANDIDATES.items():
        record = result["candidate_channels"][name]
        try:
            evidence = _one(flygym, mujoco, np, name, index); calls += 3
            record["mechanics"] = evidence
            resolved = evidence["mechanical_coordinate_direction_resolved"]
            record["mechanical_coordinate_direction_resolved"] = resolved
            record["classification"] = "BIOLOGICAL_DIRECTION_UNRESOLVED" if resolved else "MECHANICAL_DIRECTION_UNRESOLVED"
            record["statuses"] = [record["classification"], "SOURCE_HAS_NO_ANTAGONIST_POPULATION"]
            record["blocking_reason"] = ("mechanical direction is resolved, but existing evidence does not relate Fe reductor MN action to FlyGym coordinate sign"
                                         if resolved else "forward kinematics did not independently resolve coordinate direction")
        except Exception as exc:
            record["classification"] = "IDENTITY_FAILURE"
            record["statuses"] = ["IDENTITY_FAILURE", "SOURCE_HAS_NO_ANTAGONIST_POPULATION"]
            record["blocking_reason"] = str(exc)
    result["scientific_operations"]["forward_kinematics_calls"] = calls
    result["run_status"] = "MECHANICAL_VALIDATION_COMPLETE_FAIL_CLOSED"
    audit.OUTPUT.write_text(audit.serialize(result), encoding="utf-8", newline="\n")
    print(f"wrote {audit.OUTPUT}")
    return 0
