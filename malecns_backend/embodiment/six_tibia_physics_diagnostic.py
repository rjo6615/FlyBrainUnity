"""Passive matched MuJoCo diagnostics for the reproducible M4C-2 ``-RH`` failure.

This module observes the existing condition runner.  It does not alter a model,
an action, or a MuJoCo data array and it never retries a failed call.
"""
from __future__ import annotations

import argparse
from collections import deque
import importlib
import json
from pathlib import Path

import numpy as np

from .body import SixTibiaFlyGymBody
from .six_tibia import LEG_ORDER, load_six_tibia_interfaces
from .six_tibia_causal import CANONICAL_SEED
from .six_tibia_perturbation import CANONICAL_DURATION_MS, _run_condition, physics_error_types

DIAGNOSTIC_DOF = 39
BUFFER_DURATION_MS = 20
COMPARISON_TIMES_MS = (475, 480, 485, 490, 495)
ENGINEERING_DIVERGENCE_TOLERANCE = 1e-9


def _values(value):
    return np.asarray(value).reshape(-1)


def _name(model, kind, object_id):
    """Use the instantiated model's name table; return None when unavailable."""
    method = getattr(model, "id2name", None)
    if method is not None:
        for args in ((object_id, kind), (kind, object_id)):
            try:
                value = method(*args)
            except (TypeError, ValueError, KeyError):
                continue
            if value is not None:
                return str(value)
    try:
        mujoco = importlib.import_module("mujoco")
        enum = getattr(mujoco.mjtObj, "mjOBJ_" + kind.upper())
        value = mujoco.mj_id2name(getattr(model, "ptr", model), enum, object_id)
        return None if value is None else str(value)
    except (ImportError, AttributeError, TypeError, ValueError):
        return None


def resolve_dof(model, dof_index=DIAGNOSTIC_DOF, tibia_actuator_names=()):
    """Resolve a qvel index solely through live ``mjModel`` address metadata."""
    dof_addresses = _values(model.jnt_dofadr).astype(int)
    qpos_addresses = _values(model.jnt_qposadr).astype(int)
    nv, nq = int(model.nv), int(model.nq)
    if not 0 <= dof_index < nv:
        return {"resolved": False, "dof_index": dof_index,
                "reason": f"DOF index outside model nv={nv}"}
    candidates = [j for j, start in enumerate(dof_addresses)
                  if start <= dof_index < (dof_addresses[j + 1] if j + 1 < len(dof_addresses) else nv)]
    if len(candidates) != 1:
        return {"resolved": False, "dof_index": dof_index,
                "reason": f"metadata matched {len(candidates)} joints"}
    joint_id = candidates[0]
    dof_start = int(dof_addresses[joint_id])
    dof_end = int(dof_addresses[joint_id + 1]) if joint_id + 1 < len(dof_addresses) else nv
    qpos_start = int(qpos_addresses[joint_id])
    qpos_end = int(qpos_addresses[joint_id + 1]) if joint_id + 1 < len(qpos_addresses) else nq
    body_id = int(_values(model.jnt_bodyid)[joint_id])
    joint_name = _name(model, "joint", joint_id)
    joint_types = {0: "free", 1: "ball", 2: "slide", 3: "hinge"}
    limited = bool(_values(model.jnt_limited)[joint_id]) if hasattr(model, "jnt_limited") else None
    limits = (_values(model.jnt_range).reshape(-1, 2)[joint_id].astype(float).tolist()
              if limited and hasattr(model, "jnt_range") else None)
    actuators = []
    if hasattr(model, "actuator_trnid"):
        for actuator_id, transmission in enumerate(np.asarray(model.actuator_trnid)):
            if int(np.asarray(transmission).flat[0]) == joint_id:
                actuators.append({"id": actuator_id, "name": _name(model, "actuator", actuator_id)})
    actuator_names = {item["name"] for item in actuators if item["name"] is not None}
    tibia_matches = sorted(actuator_names.intersection(tibia_actuator_names))
    return {"resolved": True, "dof_index": dof_index, "joint_id": joint_id,
            "joint_name": joint_name, "joint_type": joint_types.get(int(_values(model.jnt_type)[joint_id]),
                                                                      "unknown"),
            "body_id": body_id, "body_name": _name(model, "body", body_id),
            "qpos_address_range": [qpos_start, qpos_end],
            "dof_address_range": [dof_start, dof_end], "actuators": actuators,
            "is_six_tibia_actuator": bool(tibia_matches),
            "six_tibia_actuator_matches": tibia_matches,
            "joint_limited": limited, "joint_range_rad": limits}


def _physics(body):
    for owner in (body.sim, getattr(body.sim, "env", None), getattr(body.sim, "_env", None)):
        value = getattr(owner, "physics", None)
        if value is not None:
            return value
    raise RuntimeError("UNRESOLVED: FlyGym simulation exposes no MuJoCo physics object")


class PhysicsRingRecorder:
    """Bounded pre-call snapshots; all NumPy values are copied to plain JSON values."""
    def __init__(self, interfaces, timestep_s, duration_ms=BUFFER_DURATION_MS):
        self.interfaces = dict(interfaces)
        self.capacity = max(1, int(round(duration_ms / (timestep_s * 1000))))
        self.states = deque(maxlen=self.capacity)
        self.sparse_checkpoints = {}
        self.failed_call_input = None
        self.last_successful_state = None
        self.metadata = None
        self.control_time_ms = None
        self.actuation = None

    def set_control_context(self, control_time_ms, actuation):
        self.control_time_ms = int(control_time_ms)
        self.actuation = actuation

    def _snapshot(self, body, action):
        physics = _physics(body); model, data = physics.model, physics.data
        if self.metadata is None:
            self.metadata = resolve_dof(model, DIAGNOSTIC_DOF,
                tuple(interface.actuator_name for interface in self.interfaces.values()))
        mapping = self.metadata
        qpos = np.array(data.qpos, dtype=float, copy=True)
        qvel = np.array(data.qvel, dtype=float, copy=True)
        qacc = np.array(data.qacc, dtype=float, copy=True) if hasattr(data, "qacc") else np.array([])
        ctrl = np.array(data.ctrl, dtype=float, copy=True) if hasattr(data, "ctrl") else np.array([])
        force = (np.array(data.actuator_force, dtype=float, copy=True)
                 if hasattr(data, "actuator_force") else np.array([]))
        joint_id = mapping.get("joint_id") if mapping.get("resolved") else None
        qa = mapping.get("qpos_address_range", [0, 0])
        joint_position = qpos[qa[0]:qa[1]].tolist() if joint_id is not None else None
        actuator_rows = []
        for actuator in mapping.get("actuators", []):
            i = actuator["id"]
            actuator_rows.append({**actuator, "control": float(ctrl[i]) if i < len(ctrl) else None,
                                  "force": float(force[i]) if i < len(force) else None})
        tibia_positions = {}; tibia_velocities = {}
        observation = np.asarray(body.observation["joints"], dtype=float)
        positions = observation[0] if observation.ndim == 2 else observation
        velocities = observation[1] if observation.ndim == 2 and observation.shape[0] > 1 else np.zeros_like(positions)
        for leg, interface in self.interfaces.items():
            tibia_positions[leg] = float(positions[interface.action_index])
            tibia_velocities[leg] = float(velocities[interface.action_index])
        limits = mapping.get("joint_range_rad")
        proximity = None
        if limits and joint_position and len(joint_position) == 1:
            proximity = min(joint_position[0] - limits[0], limits[1] - joint_position[0])
        max_qvel_i = int(np.argmax(np.abs(qvel))) if qvel.size else None
        max_qacc_i = int(np.argmax(np.abs(qacc))) if qacc.size else None
        fly = np.asarray(body.observation.get("fly", ()), dtype=float).reshape(-1)
        orientation = np.asarray(body.observation.get("fly_orientation", ()), dtype=float).reshape(-1)
        state = {"control_time_ms": self.control_time_ms, "simulation_time_ms": float(data.time * 1000),
            "dof_qpos": joint_position,
            "dof_qvel": float(qvel[DIAGNOSTIC_DOF]) if DIAGNOSTIC_DOF < len(qvel) else None,
            "dof_qacc": float(qacc[DIAGNOSTIC_DOF]) if DIAGNOSTIC_DOF < len(qacc) else None,
            "joint_position": joint_position,
            "joint_velocity": float(qvel[DIAGNOSTIC_DOF]) if DIAGNOSTIC_DOF < len(qvel) else None,
            "joint_limit_proximity_rad": proximity, "associated_actuators": actuator_rows,
            "six_tibia_positions_rad": tibia_positions, "six_tibia_velocities_rad_s": tibia_velocities,
            "six_tibia_actuator_targets_rad": {leg: float(action["joints"][interface.action_index])
                                                 for leg, interface in self.interfaces.items()},
            "six_decoded_offsets_rad": {leg: float(self.actuation[leg]["decoded_offset_rad"])
                                          for leg in LEG_ORDER} if self.actuation else None,
            "body_position_m": fly[:3].tolist(), "body_orientation": orientation.tolist(),
            "max_abs_qvel": float(abs(qvel[max_qvel_i])) if max_qvel_i is not None else None,
            "max_abs_qvel_dof": max_qvel_i,
            "max_abs_qacc": float(abs(qacc[max_qacc_i])) if max_qacc_i is not None else None,
            "max_abs_qacc_dof": max_qacc_i,
            "all_tracked_values_finite": bool(all(np.isfinite(x).all() for x in
                (qpos, qvel, qacc, ctrl, force, fly, orientation)))}
        return state

    def before_physics_step(self, body, action):
        state = self._snapshot(body, action)
        self.states.append(state)
        rounded = round(state["simulation_time_ms"])
        if rounded in COMPARISON_TIMES_MS and abs(state["simulation_time_ms"] - rounded) < 1e-7:
            self.sparse_checkpoints[str(rounded)] = state
        return state

    def successful_physics_step(self, body, action, state):
        # Capture the valid post-call state separately.  This is deliberately
        # not attempted in the exception path.
        self.last_successful_state = self._snapshot(body, action)

    def failed_physics_step(self, state):
        self.failed_call_input = state

    def result(self):
        return {"capacity": self.capacity, "retained_state_count": len(self.states),
                "dof_metadata": self.metadata, "last_successful_state": self.last_successful_state,
                "input_to_failed_physics_step": self.failed_call_input,
                "sparse_checkpoints": self.sparse_checkpoints,
                "pre_failure_ring_buffer": list(self.states)}


def _nearest(states, time_ms):
    return min(states, key=lambda state: abs(state["simulation_time_ms"] - time_ms), default=None)


def compare_runs(all_six_states, minus_rh_states, metadata):
    actuator_ids = [item["id"] for item in (metadata or {}).get("actuators", [])]
    def compare(control, intervention):
        if control is None or intervention is None:
            return None
        def actuator_value(state):
            values = {item["id"]: item["control"] for item in state["associated_actuators"]}
            return [values.get(i) for i in actuator_ids]
        q0, q1 = control["joint_position"], intervention["joint_position"]
        return {"all_six_simulation_time_ms": control["simulation_time_ms"],
            "minus_rh_simulation_time_ms": intervention["simulation_time_ms"],
            "joint_position_difference_rad": ([a - b for a, b in zip(q1, q0)] if q0 and q1 else None),
            "joint_velocity_difference_rad_s": intervention["joint_velocity"] - control["joint_velocity"],
            "actuator_control_all_six": actuator_value(control),
            "actuator_control_minus_rh": actuator_value(intervention),
            "decoded_offset_difference_rad": {leg: intervention["six_decoded_offsets_rad"][leg] -
                control["six_decoded_offsets_rad"][leg] for leg in LEG_ORDER}}
    matched = {str(t): compare(_nearest(all_six_states, t), _nearest(minus_rh_states, t))
               for t in COMPARISON_TIMES_MS}
    if minus_rh_states:
        final_time = minus_rh_states[-1]["simulation_time_ms"]
        matched["last_valid_minus_rh"] = compare(_nearest(all_six_states, final_time), minus_rh_states[-1])
    first = None
    control_by_time = {round(s["simulation_time_ms"], 7): s for s in all_six_states}
    for state in minus_rh_states:
        control = control_by_time.get(round(state["simulation_time_ms"], 7))
        if control is not None and (abs(state["joint_velocity"] - control["joint_velocity"]) >
                                    ENGINEERING_DIVERGENCE_TOLERANCE or
            any(abs(a - b) > ENGINEERING_DIVERGENCE_TOLERANCE
                for a, b in zip(state["joint_position"] or (), control["joint_position"] or ()) )):
            first = state["simulation_time_ms"]; break
    return {"engineering_tolerance": ENGINEERING_DIVERGENCE_TOLERANCE,
            "first_dof_trajectory_divergence_ms": first, "checkpoints": matched}


def run_physics_diagnostic():
    """Run fresh ALL-SIX and -RH through the existing condition runner, once each."""
    from malecns_backend import MaleCNSBrain, load_malecns
    interfaces = load_six_tibia_interfaces(); data = load_malecns()
    recorders = {}
    def make_body(condition):
        def factory(current_interfaces):
            body = SixTibiaFlyGymBody(current_interfaces)
            recorder = PhysicsRingRecorder(current_interfaces, body.timestep_s)
            body.physics_diagnostic = recorder; recorders[condition] = recorder
            return body
        return factory
    runs = {}
    for label, withheld in (("ALL SIX", None), ("-RH", "RH")):
        _, _, summary = _run_condition(label, withheld, CANONICAL_DURATION_MS, CANONICAL_SEED,
            interfaces, data, MaleCNSBrain, make_body(label), physics_error_types())
        runs[label] = summary
    all_states = list(recorders["ALL SIX"].sparse_checkpoints.values()) + list(recorders["ALL SIX"].states)
    minus_states = list(recorders["-RH"].sparse_checkpoints.values()) + list(recorders["-RH"].states)
    all_states.sort(key=lambda state: state["simulation_time_ms"])
    minus_states.sort(key=lambda state: state["simulation_time_ms"])
    metadata = recorders["-RH"].metadata
    return {"milestone": "M4C-2A", "seed": CANONICAL_SEED,
        "interpretation": "reproducible physical/numerical divergence under the modeled -RH sensory-withholding counterfactual",
        "model_behavior_changed": False, "automatic_retry": False,
        "runs": runs, "diagnostics": {label: recorder.result() for label, recorder in recorders.items()},
        "matched_comparison": compare_runs(all_states, minus_states, metadata)}


def print_report(result):
    metadata = result["diagnostics"]["-RH"]["dof_metadata"] or {"resolved": False}
    print("DOF 39:")
    for key in ("joint_name", "joint_type", "body_name", "qpos_address_range", "dof_address_range",
                "actuators", "is_six_tibia_actuator"):
        print(f"    {key} = {metadata.get(key, 'UNRESOLVED')}")
    for label in ("-RH", "ALL SIX"):
        run = result["runs"][label]
        print(f"{label}: status = {run['run_status']}; last valid = {run['last_successful_simulation_time_ms']}")
    failed = result["diagnostics"]["-RH"]["input_to_failed_physics_step"]
    if failed:
        print("PRE-FAILURE:")
        print(f"    qpos = {failed['dof_qpos']}; qvel = {failed['dof_qvel']}; qacc = {failed['dof_qacc']}")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=Path(
        "malecns_backend/embodiment/perturbation_output/six_tibia_minus_rh_physics_diagnostic.json"))
    args = parser.parse_args(argv)
    result = run_physics_diagnostic(); print_report(result)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
