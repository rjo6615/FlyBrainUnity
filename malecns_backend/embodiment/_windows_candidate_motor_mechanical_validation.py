"""Dependency-gated, non-neural mechanical validation of three candidates.

This module is intentionally imported only by ``--mechanical``.  It mutates
qpos solely for kinematic ``forward`` calls: it never steps physics, constructs
MaleCNS, observes neural activity, or executes the future experiment.
"""
from __future__ import annotations

import importlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from . import candidate_motor_channel_validation as audit

EPSILON = 0.0001
EXPECTED_SIGN = -1


def _name(model: Any, kind: str, object_id: int) -> str:
    for args in ((object_id, kind), (kind, object_id)):
        try:
            value = model.id2name(*args)
        except (AttributeError, TypeError, ValueError, KeyError):
            continue
        if value is not None:
            return str(value)
    raise RuntimeError(f"compiled {kind} id {object_id} has no name")


def _terminal(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def decide_sign(evidence: Mapping[str, Any], tolerance: float = 1e-10) -> int | None:
    """Resolve sign only when endpoint and rotation evidence both agree."""
    displacement = tuple(float(x) for x in evidence["positive_minus_negative_endpoint_displacement"])
    plus_axis = tuple(float(x) for x in evidence["positive"]["world_rotation_axis_direction"])
    minus_axis = tuple(float(x) for x in evidence["negative"]["world_rotation_axis_direction"])
    world_axis = tuple(float(x) for x in evidence["world_joint_axis_neutral"])
    dot = lambda left, right: sum(a * b for a, b in zip(left, right))
    plus_angle = float(evidence["positive"]["relative_segment_rotation_rad"])
    minus_angle = float(evidence["negative"]["relative_segment_rotation_rad"])
    rotation_ok = (dot(plus_axis, world_axis) > 1 - 1e-7 and
                   dot(minus_axis, world_axis) < -1 + 1e-7 and
                   plus_angle > tolerance and minus_angle > tolerance)
    if not rotation_ok or not all(math.isfinite(x) for x in displacement) or abs(displacement[2]) <= tolerance:
        return None
    return 1 if displacement[2] > 0 else -1


def validate_identity(ordered_names: tuple[str, ...], action_index: int, actuator_name: str,
                      joint_name: str, transmission_joint_id: int, joint_id: int,
                      candidate: str) -> None:
    if (action_index >= len(ordered_names) or ordered_names[action_index] != candidate or
            _terminal(actuator_name) != f"actuator_position_{candidate}" or
            _terminal(joint_name) != candidate or transmission_joint_id != joint_id):
        raise RuntimeError(f"actuator/joint identity differs from expected for {candidate}")


def assert_isolated(neutral: Any, perturbed: Any, qpos_index: int, expected: float) -> None:
    changed = [index for index, (after, before) in enumerate(zip(perturbed, neutral)) if after != before]
    if changed != [qpos_index] or not math.isclose(float(perturbed[qpos_index]), expected,
                                                   rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError("perturbation did not affect exactly the expected joint")


def _rotation(np: Any, current: Any, neutral: Any) -> tuple[float, list[float]]:
    relative = np.asarray(current).reshape(3, 3) @ np.asarray(neutral).reshape(3, 3).T
    vector = np.array([relative[2, 1] - relative[1, 2], relative[0, 2] - relative[2, 0],
                       relative[1, 0] - relative[0, 1]])
    angle = math.acos(float(np.clip((np.trace(relative) - 1) / 2, -1, 1)))
    if angle <= 1e-12 or np.linalg.norm(vector) <= 1e-12:
        raise RuntimeError("relative segment rotation is unresolved")
    return angle, (vector / np.linalg.norm(vector)).tolist()


def _forward(physics: Any, mujoco: Any) -> None:
    method = getattr(physics, "forward", None)
    if method is not None:
        method()
    else:
        mujoco.mj_forward(getattr(physics.model, "ptr", physics.model),
                          getattr(physics.data, "ptr", physics.data))


def _resolve_unique(model: Any, kind: str, suffix: str, count: int) -> int:
    matches = [i for i in range(count) if _terminal(_name(model, kind, i)) == suffix]
    if len(matches) != 1:
        raise RuntimeError(f"expected one compiled {kind} named {suffix}; found {len(matches)}")
    return matches[0]


def _one_candidate(flygym: Any, mujoco: Any, np: Any, candidate: str, action_index: int) -> dict[str, Any]:
    fly = flygym.Fly(enable_adhesion=False, control="position")
    ordered = tuple(fly.actuated_joints)
    simulation = getattr(flygym, "SingleFlySimulation", None) or \
        importlib.import_module("flygym.simulation").SingleFlySimulation
    sim = simulation(fly=fly, cameras=[], timestep=.0001)
    try:
        sim.reset()
        physics = next((owner.physics for owner in (sim, getattr(sim, "env", None), getattr(sim, "_env", None))
                        if owner is not None and getattr(owner, "physics", None) is not None), None)
        if physics is None:
            raise RuntimeError("compiled FlyGym physics is unavailable")
        model, data = physics.model, physics.data
        aid = _resolve_unique(model, "actuator", f"actuator_position_{candidate}", int(model.nu))
        jid = _resolve_unique(model, "joint", candidate, int(model.njnt))
        actuator_name, joint_name = _name(model, "actuator", aid), _name(model, "joint", jid)
        transmitted = int(np.asarray(model.actuator_trnid)[aid, 0])
        validate_identity(ordered, action_index, actuator_name, joint_name, transmitted, jid, candidate)
        body_id = int(np.asarray(model.jnt_bodyid)[jid]); body_name = _name(model, "body", body_id)
        qidx = int(np.asarray(model.jnt_qposadr)[jid])
        endpoint_id = _resolve_unique(model, "body", candidate[6:8] + "Tarsus5", int(model.nbody))
        _forward(physics, mujoco)
        neutral_qpos = np.asarray(data.qpos).copy()
        neutral_xmat = np.asarray(data.xmat[body_id]).copy()
        neutral_endpoint = np.asarray(data.xpos[endpoint_id]).copy()
        local_axis = np.asarray(model.jnt_axis[jid], dtype=float)
        world_axis = np.asarray(data.xaxis[jid], dtype=float) if hasattr(data, "xaxis") \
            else neutral_xmat.reshape(3, 3) @ local_axis
        evidence: dict[str, Any] = {"epsilon_rad": EPSILON, "actuator_index": aid,
            "actuator_name": actuator_name, "transmitted_joint_id": jid, "transmitted_joint_name": joint_name,
            "owning_body_id": body_id, "owning_body_name": body_name,
            "owning_body_transform_xmat_neutral": neutral_xmat.tolist(), "local_joint_axis": local_axis.tolist(),
            "world_joint_axis_neutral": (world_axis / np.linalg.norm(world_axis)).tolist(),
            "joint_range_rad": np.asarray(model.jnt_range[jid], dtype=float).tolist(),
            "neutral_qpos_rad": float(neutral_qpos[qidx]), "neutral_endpoint_body_id": endpoint_id,
            "neutral_endpoint_body_name": _name(model, "body", endpoint_id),
            "neutral_endpoint_position": neutral_endpoint.tolist(),
            "relevant_segment_orientation_xmat_neutral": neutral_xmat.tolist()}
        for label, delta in (("positive", EPSILON), ("negative", -EPSILON)):
            data.qpos[:] = neutral_qpos
            data.qpos[qidx] += delta
            assert_isolated(neutral_qpos, np.asarray(data.qpos), qidx, neutral_qpos[qidx] + delta)
            _forward(physics, mujoco)
            endpoint = np.asarray(data.xpos[endpoint_id]).copy()
            angle, axis = _rotation(np, data.xmat[body_id], neutral_xmat)
            evidence[label] = {"requested_delta_rad": delta, "resulting_joint_qpos_rad": float(data.qpos[qidx]),
                "endpoint_position": endpoint.tolist(), "endpoint_displacement_from_neutral": (endpoint-neutral_endpoint).tolist(),
                "relative_segment_rotation_rad": angle, "world_rotation_axis_direction": axis,
                "relevant_segment_orientation_xmat": np.asarray(data.xmat[body_id]).tolist()}
        evidence["positive_minus_negative_endpoint_displacement"] = \
            (np.asarray(evidence["positive"]["endpoint_position"]) - np.asarray(evidence["negative"]["endpoint_position"])).tolist()
        sign = decide_sign(evidence)
        evidence["decided_coordinate_sign"] = sign
        evidence["historical_sign_reproduced"] = sign == EXPECTED_SIGN
        if sign != EXPECTED_SIGN:
            raise RuntimeError(f"physical evidence did not independently reproduce sign -1 for {candidate}")
        return evidence
    finally:
        sim.close()


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(audit.serialize(dict(value)), encoding="utf-8", newline="\n")


def run() -> int:
    np, flygym, mujoco = (importlib.import_module(name) for name in ("numpy", "flygym", "mujoco"))
    result = audit.build()
    try:
        measured = {name: _one_candidate(flygym, mujoco, np, name, index)
                    for name, index in audit.CANDIDATES.items()}
        for name, evidence in measured.items():
            result["candidate_channels"][name]["mechanics"] = evidence
        result.update(run_status="MECHANICAL_REVALIDATION_PASSED", mechanical_validation_passed=True,
                      preregistration_created=True, preregistration_withheld_reason=None)
        digest = audit.create_preregistration_after_mechanics(result)
        result["future_preregistration"] = {"path": str(audit.PREREGISTRATION.relative_to(audit.ROOT)),
            "sha256": digest, "status": "NOT_RUN"}
    except Exception as exc:
        result.update(run_status="MECHANICAL_FAILURE", mechanical_validation_passed=False,
                      preregistration_created=False, preregistration_withheld_reason=f"fail-closed: {exc}")
        audit.PREREGISTRATION.unlink(missing_ok=True)
        _write(audit.OUTPUT, result)
        raise
    _write(audit.OUTPUT, result)
    print(f"wrote {audit.OUTPUT} and unexecuted {audit.PREREGISTRATION}")
    return 0
