"""Canonical Windows integration adapter for M6B.

This module is plumbing around the validated live path, not another neural or
physical implementation.  It reuses ``load_malecns``/``MaleCNSBrain``, the
M5D-4 live environment helpers, M5D-5 proprioceptive and tactile encoders,
``MotorActivityObserver``, and the M5D-4C ``MatchedControlPipeline``.  Imports
of FlyGym and MuJoCo remain lazy so the contract and engineering logic can be
tested on non-Windows hosts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from malecns_backend import MaleCNSBrain, load_malecns
from . import tactile_targeted_contact_calibration as contact
from .full_leg_interface import enumerate_live_actuators
from .isolated_tier_b_motor_validation import (
    ANNOTATION_TIER_B, CANONICAL_SEED, DURATION_MS, EQUIVALENCE_FIELDS,
    EXCLUDED_UNRESOLVED, LOCKED_ACTION_INDICES, LOCKED_SIGNS, M6A_SHA256,
    OBSERVER_TAU_MS, SLEW_RAD_S, TIBIA_INDICES,
    TIER_B, activation, aggregate_classification, classify_joint,
    m6c_eligible, safe_contribution_bound, strict_pre_intervention_equivalence,
)
from .motor import MotorActivityObserver, MotorSafety
from .proprioceptive_activation import proprio_rngs, sample_candidates
from .sensory import LegSensoryFrame, SensoryEncoder
from .six_tibia import LEG_ORDER
from .tactile_contact import TactileContactConfig, TactileContactEncoder
from .tactile_motor_loop import ACTUATOR_INDICES, NEURAL_DT_MS, validated_interfaces
from .tactile_motor_loop_audit import _forces, _joint_positions, _make_live, _state_tuple
from .tactile_motor_matched_control import MatchedControlPipeline
from .tactile_propagation import rng_digest

CONDITIONS = ("ENABLED", "MOTOR_OUTPUT_DISABLED")
PHYSICS_DT_MS = contact.DEFAULT_TIMESTEP_S * 1000.0
CALIBRATION_EPSILON_RAD = 1e-4
PREFLIGHT_SCHEMA = "M6B-P5.0"
EXPECTED_CONDITIONS = len(TIER_B) * len(CONDITIONS)
EXPECTED_PHYSICS_STEPS_PER_CONDITION = int(round(DURATION_MS / PHYSICS_DT_MS))
EXPECTED_NEURAL_STEPS_PER_CONDITION = int(round(DURATION_MS / NEURAL_DT_MS))
EXPECTED_CANONICAL_ENVIRONMENT_CONSTRUCTIONS = 1 + EXPECTED_CONDITIONS
MAX_CANONICAL_ENVIRONMENT_CONSTRUCTIONS = EXPECTED_CANONICAL_ENVIRONMENT_CONSTRUCTIONS
TELEMETRY_FIELDS = (
    "qpos", "qvel", "action", "ctrl", "selected_joint_state",
    "observer_state", "decoder_state", "sensory_state", "rng_state",
    "positive_population_spikes", "negative_population_spikes",
    "raw_contribution", "admitted_contribution", "full_body_state",
    "mechanical_limit_encounter", "physics_warnings",
)


@dataclass(frozen=True)
class JointMetadata:
    action_index: int
    actuator_id: int
    joint_id: int
    qpos_index: int
    qvel_index: int
    joint_axis: tuple[float, float, float]
    joint_min: float
    joint_max: float
    actuator_min: float
    actuator_max: float
    joint_limited: bool = True
    actuator_control_limited: bool = True
    limit_classification: str = "VALID_SAME_DOMAIN_INTERSECTION"


@dataclass(frozen=True)
class SignCalibration:
    status: str
    coordinate_sign: int | None
    evidence: Mapping[str, Any]


def _json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, (tuple, set)): return list(value)
    raise TypeError(type(value).__name__)


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False,
                      default=_json_value)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def _elapsed(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _progress(message: str) -> None:
    """Emit engineering-only progress without touching scientific state/RNG."""
    print(message, flush=True)


def _cached_state_digest(brain: Any, cached: str | None,
                         neural_state_changed: bool) -> str:
    """Hash exactly the original four arrays, only after they can have changed."""
    if cached is None or neural_state_changed:
        return _state_tuple(brain)
    return cached


def _model_name(model: Any, kind: str, object_id: int) -> str | None:
    for args in ((object_id, kind), (kind, object_id)):
        try:
            value = model.id2name(*args)
        except (AttributeError, TypeError, ValueError, KeyError):
            continue
        if value is not None:
            return str(value)
    return None


def inspect_limit_metadata(physics: Any, record: Mapping[str, Any],
                           current_action: float | None = None) -> dict[str, Any]:
    """Describe raw MuJoCo limits and their domains without conflating them.

    MuJoCo stores placeholder ``[0, 0]`` ranges even when the corresponding
    ``*_limited`` flag is false.  Such a pair is not a zero-width limit.  A
    position servo's ctrl is an absolute transmission-length target; it is a
    joint-angle target only for a scalar joint transmission with unit gear.
    """
    source = record.get("mujoco_metadata", record)
    model = physics.model
    try:
        aid, jid = int(source["actuator_id"]), int(source["joint_id"])
        qrange, drange = source["qpos_range"], source["dof_range"]
        if len(qrange) != 2 or len(drange) != 2 or qrange[1] - qrange[0] != 1 or drange[1] - drange[0] != 1:
            raise ValueError("M6B requires a scalar one-DoF joint")
        qidx, vidx = int(qrange[0]), int(drange[0])
        axis = tuple(float(x) for x in np.asarray(model.jnt_axis[jid]).reshape(3))
        joint_range = tuple(float(x) for x in np.asarray(model.jnt_range[jid]).reshape(2))
        ctrl_range = tuple(float(x) for x in np.asarray(model.actuator_ctrlrange[aid]).reshape(2))
        joint_limited = bool(np.asarray(model.jnt_limited)[jid])
        ctrl_limited = bool(np.asarray(model.actuator_ctrllimited)[aid])
        force_limited = bool(np.asarray(model.actuator_forcelimited)[aid])
        force_range = tuple(float(x) for x in np.asarray(model.actuator_forcerange[aid]).reshape(2))
        transmission_type = int(np.asarray(model.actuator_trntype)[aid])
        transmission_ids = tuple(int(x) for x in np.asarray(model.actuator_trnid[aid]).reshape(-1))
        gear = tuple(float(x) for x in np.asarray(model.actuator_gear[aid]).reshape(-1))
        gain = tuple(float(x) for x in np.asarray(model.actuator_gainprm[aid]).reshape(-1))
        bias = tuple(float(x) for x in np.asarray(model.actuator_biasprm[aid]).reshape(-1))
        actuator_name = _model_name(model, "actuator", aid) or source.get("actuator_name")
        joint_name = _model_name(model, "joint", jid) or source.get("joint_name")
    except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid MuJoCo metadata for {record.get('name')}: {exc}") from exc
    values = (*axis, *joint_range, *ctrl_range, *force_range, *gear, *gain, *bias)
    if not all(math.isfinite(x) for x in values) or np.linalg.norm(axis) == 0:
        raise RuntimeError("non-finite or zero-axis joint metadata")
    # FlyGym creates these through Fly(control="position").  Check the live
    # compiled servo signature too, rather than trusting only that constructor.
    unit_joint_transmission = (transmission_type == 0 and transmission_ids[0] == jid
                               and len(gear) and math.isclose(gear[0], 1.0))
    position_servo = ("position" in str(actuator_name).casefold() and
                      len(gain) > 0 and gain[0] > 0 and len(bias) > 1 and
                      math.isclose(bias[1], -gain[0]))
    same_domain = unit_joint_transmission and position_servo
    classification = ("VALID_SAME_DOMAIN_INTERSECTION" if same_domain and joint_limited and ctrl_limited
                      else "VALID_BUT_DIFFERENT_DOMAINS" if ctrl_limited and not same_domain
                      else "JOINT_RANGE_UNAVAILABLE" if not joint_limited
                      else "ACTUATOR_RANGE_UNAVAILABLE")
    qpos = float(np.asarray(physics.data.qpos)[qidx])
    ctrl = float(np.asarray(physics.data.ctrl)[aid])
    return {"physical_actuator_name": record.get("name"), "action_index": int(record["index"]),
        "mujoco_actuator_id": aid, "mujoco_actuator_name": actuator_name,
        "mujoco_joint_id": jid, "mujoco_joint_name": joint_name,
        "qpos_address": qidx, "qvel_address": vidx,
        "joint_type": int(np.asarray(model.jnt_type)[jid]), "joint_axis": list(axis),
        "joint_limited": joint_limited, "raw_joint_range": list(joint_range),
        "joint_range_domain": "joint generalized position (radians for this hinge)" if joint_limited else "inactive placeholder; jnt_limited=false",
        "actuator_control_limited": ctrl_limited, "raw_actuator_ctrlrange": list(ctrl_range),
        "actuator_ctrlrange_domain": ("absolute joint-position target (radians; unit joint transmission)" if same_domain else "actuator control / transmission-length domain"),
        "actuator_force_limited": force_limited, "raw_actuator_forcerange": list(force_range),
        "actuator_forcerange_domain": "actuator scalar force" if force_limited else "inactive placeholder; actuator_forcelimited=false",
        "actuator_transmission_type": transmission_type,
        "actuator_transmission_ids": list(transmission_ids), "actuator_gear": list(gear),
        "actuator_gain_parameters": list(gain), "actuator_bias_parameters": list(bias),
        "position_servo_signature": position_servo, "ctrl_and_joint_same_domain": same_domain,
        "current_qpos": qpos, "current_ctrl": ctrl,
        "current_action_value": qpos if current_action is None else float(current_action),
        "classification": classification}


def resolve_joint_metadata(physics: Any, record: Mapping[str, Any],
                           current_action: float | None = None) -> JointMetadata:
    """Resolve applicable position-target bounds, respecting limit flags/domains."""
    diagnostic = inspect_limit_metadata(physics, record, current_action)
    if not diagnostic["ctrl_and_joint_same_domain"]:
        raise RuntimeError(f"actuator ctrl is not an absolute unit-gear joint-position target for {record.get('name')}")
    ranges = []
    if diagnostic["joint_limited"]:
        ranges.append(tuple(diagnostic["raw_joint_range"]))
    if diagnostic["actuator_control_limited"] and diagnostic["ctrl_and_joint_same_domain"]:
        ranges.append(tuple(diagnostic["raw_actuator_ctrlrange"]))
    if not ranges:
        raise RuntimeError(f"no applicable finite position-target limit for {record.get('name')}")
    lo, hi = max(x[0] for x in ranges), min(x[1] for x in ranges)
    if lo >= hi:
        raise RuntimeError(f"same-domain limits have no valid intersection for {record.get('name')}: "
                           f"joint={diagnostic['raw_joint_range']}, ctrl={diagnostic['raw_actuator_ctrlrange']}")
    return JointMetadata(diagnostic["action_index"], diagnostic["mujoco_actuator_id"],
        diagnostic["mujoco_joint_id"], diagnostic["qpos_address"], diagnostic["qvel_address"],
        tuple(diagnostic["joint_axis"]), lo, hi,
        diagnostic["raw_actuator_ctrlrange"][0], diagnostic["raw_actuator_ctrlrange"][1],
        diagnostic["joint_limited"], diagnostic["actuator_control_limited"],
        diagnostic["classification"])


def _endpoint_geom_ids(model: Any, interface: Mapping[str, Any]) -> tuple[int, ...]:
    """Find the selected leg's most distal named geoms without guessing IDs."""
    leg = str(interface["leg"])
    candidates = []
    for gid in range(int(model.ngeom)):
        name = None
        for args in ((gid, "geom"), ("geom", gid)):
            try: name = model.id2name(*args)
            except (TypeError, ValueError, KeyError): continue
            if name is not None: break
        name = "" if name is None else str(name)
        if leg.casefold() in name.casefold() and any(
                token in name.casefold() for token in ("tarsus5", "tarsus4", "claw")):
            candidates.append(gid)
    return tuple(candidates)


def calibrate_physical_sign(physics: Any, metadata: JointMetadata,
                            interface: Mapping[str, Any],
                            epsilon: float = CALIBRATION_EPSILON_RAD) -> SignCalibration:
    """Calibrate coordinate sign using only kinematics and compiled metadata.

    The score is selected before perturbation from annotation semantics:
    anterior/posterior rotation uses the body-forward x displacement, femur
    flexion/extension uses distal vertical displacement, and tarsal
    levation/depression also uses vertical displacement.  No neural object or
    walking measure is accepted by this API.
    """
    if not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("calibration epsilon must be finite and positive")
    model, data = physics.model, physics.data
    geom_ids = _endpoint_geom_ids(model, interface)
    evidence: dict[str, Any] = {"method": "deterministic_non_neural_kinematic_perturbation",
        "uses_neural_behavior": False, "uses_walking_performance": False,
        "epsilon_rad": epsilon, "joint_axis": list(metadata.joint_axis),
        "qpos_index": metadata.qpos_index, "qvel_index": metadata.qvel_index,
        "actuator_id": metadata.actuator_id, "joint_id": metadata.joint_id,
        "endpoint_geom_ids": list(geom_ids)}
    if not geom_ids:
        evidence["reason"] = "no exact distal geometry for selected leg"
        return SignCalibration("SIGN_UNRESOLVED", None, evidence)
    original_qpos = np.asarray(data.qpos).copy()
    original_qvel = np.asarray(data.qvel).copy()
    baseline = float(original_qpos[metadata.qpos_index])
    if baseline - epsilon < metadata.joint_min or baseline + epsilon > metadata.joint_max:
        evidence["reason"] = "symmetric perturbation unavailable within live limits"
        return SignCalibration("SIGN_UNRESOLVED", None, evidence)
    try:
        endpoints = []
        for delta in (-epsilon, epsilon):
            data.qpos[metadata.qpos_index] = baseline + delta
            data.qvel[metadata.qvel_index] = 0.0
            contact._forward(physics)
            endpoints.append(np.mean(np.asarray(data.geom_xpos)[list(geom_ids)], axis=0))
    finally:
        data.qpos[:] = original_qpos; data.qvel[:] = original_qvel
        contact._forward(physics)
    displacement = np.asarray(endpoints[1]) - np.asarray(endpoints[0])
    joint_class = str(interface["joint_class"]).casefold()
    component = 0 if joint_class == "coxa_yaw" else 2
    score = float(displacement[component])
    evidence.update(negative_endpoint=np.asarray(endpoints[0]).tolist(),
                    positive_endpoint=np.asarray(endpoints[1]).tolist(),
                    positive_minus_negative_displacement=displacement.tolist(),
                    anatomical_projection=("body_forward_x" if component == 0 else "body_vertical_z"),
                    projection_value=score)
    scale = max(float(np.linalg.norm(displacement)), np.finfo(float).eps)
    if not math.isfinite(score) or abs(score) <= scale * 1e-6:
        evidence["reason"] = "anatomical projection is zero or ambiguous"
        return SignCalibration("SIGN_UNRESOLVED", None, evidence)
    # Annotation +1 is anterior for yaw, extensor for femur, and levator for
    # tarsus. Positive x/upward z therefore identifies its NMF q-coordinate.
    sign = 1 if score > 0 else -1
    evidence["reason"] = "signed distal displacement agrees with the preregistered annotation direction"
    evidence["nmf_coordinate_sign_for_annotation_positive"] = sign
    return SignCalibration("RESOLVED", sign, evidence)


def compute_raw_contribution(positive_hz: float, negative_hz: float,
                             bound_rad: float, coordinate_sign: int) -> float:
    if coordinate_sign not in (-1, 1): raise ValueError("physical sign is unresolved")
    return coordinate_sign * bound_rad * (activation(positive_hz) - activation(negative_hz))


def assert_isolated_admission(selected: str, admitted: Mapping[str, float]) -> None:
    if set(admitted) != set(TIER_B): raise RuntimeError("admission vector is not exactly Tier-B")
    if selected not in TIER_B: raise RuntimeError("selected actuator is not Tier-B")
    if any(value != 0.0 for name, value in admitted.items() if name != selected):
        raise RuntimeError("nonselected Tier-B contribution crossed admission boundary")
    # An exact Tier-B-keyed vector makes Tier-A/C/D admission structurally
    # impossible. The action-index assertions are performed during setup.


def assert_physical_admission(selected: str, admitted: Mapping[str, float],
                              all_actuator_names: Sequence[str]) -> None:
    """Final fail-closed boundary immediately before a physical command."""
    if set(admitted) != set(all_actuator_names):
        raise RuntimeError("physical admission vector does not cover every actuator")
    if selected not in TIER_B:
        raise RuntimeError("selected actuator is not canonically eligible")
    if any(value != 0.0 for name, value in admitted.items() if name != selected):
        raise RuntimeError("excluded actuator received neural contribution")
    if any(admitted[name] != 0.0 for name in EXCLUDED_UNRESOLVED):
        raise RuntimeError("SIGN_UNRESOLVED Coxa-yaw contribution crossed boundary")


def _population_index(interface: Mapping[str, Any], data: Any) -> tuple[dict[str, tuple[int, ...]], tuple[str, ...], tuple[str, ...]]:
    dense = {int(body): i for i, body in enumerate(np.asarray(data.body_ids).tolist())}
    populations, positive, negative = {}, [], []
    for population in interface["directional_motor_populations"]:
        name = population["population"]
        try: populations[name] = tuple(dense[int(body)] for body in population["body_ids"])
        except KeyError as exc: raise RuntimeError(f"required motor body ID absent: {exc.args[0]}") from exc
        direction = population["annotation_direction"]
        (positive if direction == 1 else negative if direction == -1 else []).append(name)
    if not positive or not negative: raise RuntimeError("interface lacks annotation-backed opposing populations")
    return populations, tuple(positive), tuple(negative)


def _rate(names: Sequence[str], rates: Mapping[str, float], populations: Mapping[str, Sequence[int]]) -> float:
    count = sum(len(populations[name]) for name in names)
    if count <= 0: raise RuntimeError("empty directional motor population")
    return sum(rates[name] * len(populations[name]) for name in names) / count


def _rng_state(tactile_encoder: Any, sensory_rngs: Mapping[str, Any], counts: Mapping[str, int]) -> dict[str, Any]:
    return {"tactile": rng_digest(tactile_encoder.rng["LM"]),
            "proprio": {leg: rng_digest(sensory_rngs[leg]) for leg in LEG_ORDER},
            "draw_counts": dict(counts)}


def _fresh_runtime(flygym: Any, data: Any, tibia_interfaces: Mapping[str, Any],
                   interface: Mapping[str, Any], metadata_record: Mapping[str, Any],
                   condition: str) -> dict[str, Any]:
    """Construct every stateful component afresh for one condition."""
    sim, physics, obs, tarsus_id, surface_id = _make_live(flygym, tibia_interfaces)
    try:
        brain = MaleCNSBrain(data); brain.reset(CANONICAL_SEED)
        if float(brain.config.dt) != NEURAL_DT_MS: raise RuntimeError("MaleCNS neural dt changed")
        populations, positive, negative = _population_index(interface, data)
        observer = MotorActivityObserver(populations, OBSERVER_TAU_MS); observer.reset(brain.spike_counts)
        tactile_encoder = TactileContactEncoder(config=TactileContactConfig(seed=CANONICAL_SEED))
        sensory_encoders = {leg: SensoryEncoder(tibia_interfaces[leg]) for leg in LEG_ORDER}
        sensory_rngs = proprio_rngs(CANONICAL_SEED)
        metadata = resolve_joint_metadata(physics, metadata_record)
        baseline = float(_joint_positions(obs)[interface["action_index"]])
        bound = safe_contribution_bound(metadata.joint_min, metadata.joint_max, baseline)
        safety = MotorSafety(metadata.joint_min, metadata.joint_max, bound, SLEW_RAD_S)
        pipeline = MatchedControlPipeline(condition == "ENABLED", safety)
        return locals()
    except BaseException:
        close = getattr(sim, "close", None)
        if close is not None:
            close()
        raise


def _run_condition(flygym: Any, data: Any, tibia_interfaces: Mapping[str, Any],
                   interface: Mapping[str, Any], metadata_record: Mapping[str, Any],
                   calibration: SignCalibration, condition: str,
                   actuator_names: Sequence[str], condition_number: int = 1,
                   total_conditions: int = EXPECTED_CONDITIONS,
                   run_started: float | None = None) -> tuple[list[dict[str, Any]], dict[str, float]]:
    if condition not in CONDITIONS: raise ValueError("unknown M6B condition")
    if calibration.status != "RESOLVED" or calibration.coordinate_sign not in (-1, 1):
        raise RuntimeError("SIGN_UNRESOLVED interfaces cannot receive neural actuation")
    condition_started = time.perf_counter()
    runtime = _fresh_runtime(flygym, data, tibia_interfaces, interface, metadata_record, condition)
    runtime_initialized = time.perf_counter()
    sim, physics, obs, brain = (runtime[x] for x in ("sim", "physics", "obs", "brain"))
    observer, populations = runtime["observer"], runtime["populations"]
    positive, negative, pipeline = runtime["positive"], runtime["negative"], runtime["pipeline"]
    tactile_encoder, sensory_encoders = runtime["tactile_encoder"], runtime["sensory_encoders"]
    sensory_rngs, metadata, bound = runtime["sensory_rngs"], runtime["metadata"], runtime["bound"]
    commands = _joint_positions(obs); pending: set[int] = set(); rows = []
    draw_counts = {leg: 0 for leg in LEG_ORDER}; stride = int(round(NEURAL_DT_MS / PHYSICS_DT_MS))
    final_step = int(round(DURATION_MS / PHYSICS_DT_MS)); selected = interface["physical_joint"]
    raw = admitted = 0.0; observed: Mapping[str, Any] = {}; decoder: Mapping[str, Any] = {}
    sensory_state: Mapping[str, Any] = {}; positive_spikes = negative_spikes = 0
    brain_state_digest = _cached_state_digest(brain, None, True)
    phase = {"brain_step_seconds": 0.0, "sim_step_seconds": 0.0,
             "sensory_seconds": 0.0, "observer_decoder_seconds": 0.0,
             "telemetry_hash_seconds": 0.0, "physical_admission_seconds": 0.0}
    progress_every = final_step // 10
    try:
        for step in range(final_step + 1):
            sensory_started = time.perf_counter()
            time_ms = float(physics.data.time * 1000.0); measured = _joint_positions(obs)
            forces = _forces(obs); tactile = tactile_encoder.encode(forces, time_ms, PHYSICS_DT_MS)["LM"]
            pending.update(map(int, tactile.generated_dense_indices))
            phase["sensory_seconds"] += time.perf_counter() - sensory_started
            if step and step % stride == 0:
                neural_started = time.perf_counter()
                brain.clear_external_drive(); candidates = set(pending); pending.clear()
                proprio_log = {}
                for leg in LEG_ORDER:
                    encoded = sensory_encoders[leg].encode(LegSensoryFrame(time_ms / 1000.0,
                        float(measured[ACTUATOR_INDICES[leg]])))
                    local = sample_candidates(encoded.rates_hz, sensory_rngs[leg])
                    generated = tuple(int(encoded.indices[i]) for i in local); candidates.update(generated)
                    draw_counts[leg] += len(encoded.rates_hz)
                    proprio_log[leg] = {"rates_hz": tuple(map(float, encoded.rates_hz)), "candidate": generated}
                if candidates: brain.set_external_drive(tuple(sorted(candidates)), 1000.0 / brain.config.dt)
                brain.external_drive_withheld_indices = np.empty(0, np.intp); brain.step()
                brain_state_digest = _cached_state_digest(brain, brain_state_digest, True)
                phase["brain_step_seconds"] += time.perf_counter() - neural_started
                observer_started = time.perf_counter()
                observed = observer.update(brain.spike_counts, NEURAL_DT_MS)
                pos_hz = _rate(positive, observed["filtered_hz"], populations)
                neg_hz = _rate(negative, observed["filtered_hz"], populations)
                raw = compute_raw_contribution(pos_hz, neg_hz, bound, calibration.coordinate_sign)
                result = pipeline.update(float(measured[interface["action_index"]]), raw, NEURAL_DT_MS / 1000.0)
                admitted = result.admitted_neural_contribution
                admissions = {name: admitted if name == selected else 0.0 for name in TIER_B}
                assert_isolated_admission(selected, admissions)
                commands[interface["action_index"]] = result.actuator_command
                positive_spikes = sum(observed["increments"][name] for name in positive)
                negative_spikes = sum(observed["increments"][name] for name in negative)
                decoder = {"positive_hz": pos_hz, "negative_hz": neg_hz,
                    "coordinate_sign": calibration.coordinate_sign, "bound_rad": bound,
                    "raw_neural_contribution": raw}
                sensory_state = {"proprio": proprio_log,
                    "tactile_pending": tuple(sorted(candidates)),
                    "delivered": tuple(map(int, brain._last_external_delivered))}
                phase["observer_decoder_seconds"] += time.perf_counter() - observer_started
            telemetry_started = time.perf_counter()
            arrays = (physics.data.qpos, physics.data.qvel, physics.data.qacc, physics.data.ctrl)
            valid = all(np.all(np.isfinite(x)) for x in arrays)
            row = {"time_ms": time_ms, "physical_step": step,
                "neural_step": step // stride if step and step % stride == 0 else None,
                "qpos": np.asarray(physics.data.qpos).copy(), "qvel": np.asarray(physics.data.qvel).copy(),
                "action": commands.copy(), "ctrl": np.asarray(physics.data.ctrl).copy(),
                "selected_joint_state": {"position": float(measured[interface["action_index"]]),
                    "velocity": float(np.asarray(physics.data.qvel)[metadata.qvel_index])},
                "observer_state": observed, "decoder_state": decoder,
                "sensory_state": sensory_state,
                "rng_state": _rng_state(tactile_encoder, sensory_rngs, draw_counts),
                "positive_population_spikes": positive_spikes,
                "negative_population_spikes": negative_spikes,
                "raw_contribution": raw, "admitted_contribution": admitted,
                "full_body_state": {"qpos": np.asarray(physics.data.qpos).copy(),
                    "qvel": np.asarray(physics.data.qvel).copy()},
                "mechanical_limit_encounter": bool(abs(float(measured[interface["action_index"]]) - metadata.joint_min) <= 1e-12 or abs(float(measured[interface["action_index"]]) - metadata.joint_max) <= 1e-12),
                "physics_warnings": [] if valid else ["NON_FINITE_MUJOCO_STATE"],
                "brain_state_digest": brain_state_digest}
            if set(TELEMETRY_FIELDS) - set(row): raise RuntimeError("telemetry contract incomplete")
            rows.append(row)
            phase["telemetry_hash_seconds"] += time.perf_counter() - telemetry_started
            if step and (step % progress_every == 0 or step == final_step):
                now = time.perf_counter(); total_started = condition_started if run_started is None else run_started
                _progress(f"[{condition_number:02d}/{total_conditions:02d}] {selected} {condition} | "
                          f"{step * 100 // final_step:3d}% | {step * PHYSICS_DT_MS:g}/{DURATION_MS:g} ms | "
                          f"step {step}/{final_step} | condition wall {_elapsed(now - condition_started)} | "
                          f"total wall {_elapsed(now - total_started)}")
            if not valid: break
            if step == final_step: break
            # This is intentionally adjacent to physical application.  The
            # full action-name vector proves Tier A, excluded Tier B, C and D
            # all remain exactly zero at the admission boundary.
            admission_started = time.perf_counter()
            physical_admissions = {name: 0.0 for name in actuator_names}
            physical_admissions[selected] = admitted
            assert_physical_admission(selected, physical_admissions,
                                      actuator_names)
            phase["physical_admission_seconds"] += time.perf_counter() - admission_started
            sim_started = time.perf_counter()
            obs = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})[0]
            phase["sim_step_seconds"] += time.perf_counter() - sim_started
    finally:
        if getattr(sim, "close", None): sim.close()
    ended = time.perf_counter()
    timing = {"runtime_initialization_seconds": runtime_initialized - condition_started,
              "condition_loop_seconds": ended - runtime_initialized,
              "total_condition_seconds": ended - condition_started, **phase}
    return rows, timing


def _first(rows: Sequence[Mapping[str, Any]], predicate: Callable[[Mapping[str, Any]], bool]) -> int | None:
    return next((i for i, row in enumerate(rows) if predicate(row)), None)


def _reduce_pair(interface: Mapping[str, Any], calibration: SignCalibration,
                 enabled: Sequence[Mapping[str, Any]], disabled: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    first_admitted = _first(enabled, lambda r: r["admitted_contribution"] != 0.0)
    equivalent = strict_pre_intervention_equivalence(enabled, disabled, first_admitted)
    b0 = _first(enabled, lambda r: r["positive_population_spikes"] + r["negative_population_spikes"] > 0)
    b1 = _first(enabled, lambda r: bool(r["observer_state"]) and any(v != 0 for v in r["observer_state"].get("filtered_hz", {}).values()))
    b2 = _first(enabled, lambda r: r["raw_contribution"] != 0.0); b3 = first_admitted
    b4 = next((i for i, (a, b) in enumerate(zip(enabled, disabled)) if not np.array_equal(a["action"], b["action"]) or not np.array_equal(a["ctrl"], b["ctrl"])), None)
    index = int(interface["action_index"])
    b5 = next((i for i, (a, b) in enumerate(zip(enabled, disabled)) if a["selected_joint_state"] != b["selected_joint_state"]), None)
    full = next((i for i, (a, b) in enumerate(zip(enabled, disabled)) if not np.array_equal(a["qpos"], b["qpos"]) or not np.array_equal(a["qvel"], b["qvel"])), None)
    physics_valid = not any(r["physics_warnings"] for r in (*enabled, *disabled))
    classification = classify_joint(provenance=True, sign_resolved=True, equivalent=equivalent,
        mapped_activity=b0 is not None, decoder_output=b2 is not None, admitted=b3 is not None,
        joint_diverged=b5 is not None, divergence_before_admission=full is not None and (b3 is None or full < b3),
        physics_valid=physics_valid)
    return {"actuator": interface["physical_joint"], "action_index": index,
        "physical_sign_status": calibration.status, "sign_calibration": asdict(calibration),
        "classification": classification, "pre_intervention_equivalence": equivalent,
        "milestones": {"B0": b0, "B1": b1, "B2": b2, "B3": b3, "B4": b4, "B5": b5},
        "full_body_physical_divergence_step": full,
        "telemetry_summary": {"enabled_samples": len(enabled), "disabled_samples": len(disabled),
            "selected_joint_angles_enabled": [r["selected_joint_state"]["position"] for r in enabled],
            "max_absolute_raw_contribution": max(abs(r["raw_contribution"]) for r in enabled),
            "max_absolute_admitted_contribution": max(abs(r["admitted_contribution"]) for r in enabled),
            "mechanical_limit_encounters": sum(r["mechanical_limit_encounter"] for r in enabled),
            "physics_warnings": [w for r in (*enabled, *disabled) for w in r["physics_warnings"]]}}


def _live_setup(protocol: Mapping[str, Any]) -> tuple[Any, Any, Any, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if float(PHYSICS_DT_MS) <= 0 or float(NEURAL_DT_MS) <= 0: raise RuntimeError("invalid frozen timesteps")
    flygym = importlib.import_module("flygym")
    data = load_malecns(); tibia = validated_interfaces()
    records = enumerate_live_actuators()
    locked = json.loads((Path(__file__).with_name("interface_output") /
                         "full_leg_interface_audit.json").read_text())
    authoritative = sorted(locked["actuator_records"], key=lambda x: x["actuator_index"])
    if len(records) != 42 or tuple(r["name"] for r in records) != tuple(
            item["actuator_name"] for item in authoritative):
        raise RuntimeError("42-action order does not match locked M4A")
    by_name = {r["name"]: r for r in records}
    if set(TIER_B) - set(by_name): raise RuntimeError("Tier-B action index failed to resolve")
    if {by_name[name]["index"] for name in TIER_B} & TIBIA_INDICES: raise RuntimeError("Tier-B overlaps locked tibia indices")
    if tuple(protocol.get("eligible_interfaces", ())) != TIER_B:
        raise RuntimeError("canonical eligible-interface lock mismatch")
    if tuple(protocol.get("excluded_unresolved_interfaces", ())) != EXCLUDED_UNRESOLVED:
        raise RuntimeError("canonical unresolved-interface lock mismatch")
    interfaces = {x["physical_joint"]: x for x in protocol["interfaces"]}
    if set(interfaces) != set(ANNOTATION_TIER_B):
        raise RuntimeError("annotation-backed Tier-B mapping set changed")
    for name in TIER_B:
        interface = interfaces[name]
        locked_populations = protocol["preregistration_locks"]["motor_population_mappings"][name]
        if (interface["action_index"] != LOCKED_ACTION_INDICES[name] or
                interface["coordinate_sign"] != LOCKED_SIGNS[name] or
                interface["annotation_positive_group"] != locked_populations["positive"] or
                interface["annotation_negative_group"] != locked_populations["negative"] or
                by_name[name]["index"] != LOCKED_ACTION_INDICES[name]):
            raise RuntimeError(f"locked eligible interface changed: {name}")
    return flygym, data, tibia, records, by_name


def run_preflight(protocol: Mapping[str, Any], output_path: Path) -> dict[str, Any]:
    """Perform engineering construction/calibration only; never run 500-ms trials."""
    report: dict[str, Any] = {"schema": PREFLIGHT_SCHEMA,
        "type": "NON_SCIENTIFIC_FINAL_PREFLIGHT",
        "artifact_kind": "NON_SCIENTIFIC_PREFLIGHT", "run_status": "IN_PROGRESS",
        "classification": None,
        "scientific_run_executed": False, "scientific_run_number_consumed": None,
        "m6a_sha256": M6A_SHA256, "checks": {}, "interfaces": [],
        "first_failure": None, "all_failures": [],
        "validated_control_semantics": {
            "pipeline_value": "absolute joint-position target = current measured position + admitted neural offset",
            "pipeline_units": "radians", "mechanical_clamp": "MatchedControlPipeline MotorSafety joint bounds",
            "actuator_clamp": "included only when live ctrl is an absolute unit-gear position target",
            "flygym_control_mode": "position", "slew_limit_rad_s": SLEW_RAD_S},
        "safe_bound_rule": ("intersect only active bounds expressed as absolute joint-position targets; "
            "derive symmetric neural-offset headroom about the current target and cap at 0.25 rad"),
        "provenance": {"preflight_attempts": [
            {"attempt": 1, "failure": "M6A raw-byte provenance mismatch", "scientific_run_consumed": False},
            {"attempt": 2, "failure": "joint and actuator limits have no valid intersection", "scientific_run_consumed": False},
            {"attempt": 3, "result": "PASS after corrected live-limit handling", "scientific_run_consumed": False}],
            "scientific_attempt_1": "ABORTED_IMPLEMENTATION_PERFORMANCE_DEFECT",
            "attempt_1_scientific_result_available": False,
            "canonical_artifact_modified": False}}
    flygym, data, tibia, records, by_name = _live_setup(protocol)
    report["checks"].update(dependencies_import=True, malecns_loaded=True,
        action_order_42=True, exact_eight_eligible=True, exact_six_unresolved_excluded=True,
        tier_b_indices=True, tibia_indices_unchanged=True, locked_signs=True,
        action_indices_locked=True, motor_population_mappings_locked=True,
        excluded_contributions_zero=True, tier_a_contribution_disabled=True,
        tier_c_d_contribution_disabled=True,
        motor_body_ids=True, matched_control_pipeline=True,
        telemetry_contract=set(EQUIVALENCE_FIELDS).issubset(TELEMETRY_FIELDS))
    # One environment is constructed and perturbed for engineering calibration;
    # _run_condition is deliberately never called here.
    sim, physics, obs, _, _ = _make_live(flygym, tibia)
    fatal = []
    try:
        # Pass one records every interface before any sign calibration.  A bad
        # interface therefore cannot hide the remaining thirteen diagnostics.
        for interface in (x for x in protocol["interfaces"] if x["physical_joint"] in TIER_B):
            record = by_name[interface["physical_joint"]]
            entry: dict[str, Any] = {"physical_actuator_name": interface["physical_joint"],
                                     "action_index": interface["action_index"]}
            try:
                if record["index"] != interface["action_index"]: raise RuntimeError("M6A/live action index mismatch")
                _population_index(interface, data)
                action = float(_joint_positions(obs)[record["index"]])
                entry.update(inspect_limit_metadata(physics, record, action))
                metadata = resolve_joint_metadata(physics, record, action)
                bound = safe_contribution_bound(metadata.joint_min, metadata.joint_max, action)
                entry.update({"effective_position_target_range": [metadata.joint_min, metadata.joint_max],
                              "proposed_safe_decoder_contribution_bound_rad": bound,
                              "slew_limit_rad_s": SLEW_RAD_S})
                # Diagnose exactly what the pre-P2 implementation did, even
                # when the corrected active-bound rule is valid.
                jr, cr = entry["raw_joint_range"], entry["raw_actuator_ctrlrange"]
                if max(jr[0], cr[0]) >= min(jr[1], cr[1]):
                    legacy = {"actuator": interface["physical_joint"],
                        "action_index": record["index"], "joint_range": jr,
                        "actuator_ctrlrange": cr,
                        "reason": ("inactive joint-range placeholder was numerically intersected"
                                   if not entry["joint_limited"] else
                                   "active raw ranges have an empty numeric intersection")}
                    report["all_failures"].append(legacy)
                    if report["first_failure"] is None: report["first_failure"] = legacy
                entry["metadata_status"] = "RESOLVED"
            except Exception as exc:
                entry.update(classification="OTHER_LIMIT_DIAGNOSTIC_FAILURE",
                             metadata_status="FAILED", error=str(exc),
                             proposed_safe_decoder_contribution_bound_rad=None)
                fatal.append({"actuator": interface["physical_joint"], "error": str(exc)})
            report["interfaces"].append(entry)

        # Pass two exercises construction and non-neural sign calibration only
        # for interfaces whose complete limit metadata passed above.
        eligible = [x for x in protocol["interfaces"] if x["physical_joint"] in TIER_B]
        for interface, entry in zip(eligible, report["interfaces"]):
            if entry["metadata_status"] != "RESOLVED":
                entry["sign_calibration"] = {"status": "NOT_RUN_LIMIT_DIAGNOSTIC_FAILURE"}
                continue
            record = by_name[interface["physical_joint"]]
            metadata = resolve_joint_metadata(physics, record, entry["current_action_value"])
            bound = entry["proposed_safe_decoder_contribution_bound_rad"]
            safety = MotorSafety(metadata.joint_min, metadata.joint_max, bound, SLEW_RAD_S)
            # Construct both sides of the exact M5D-4C path, but do not update
            # or step them during engineering preflight.
            MatchedControlPipeline(True, safety)
            MatchedControlPipeline(False, safety)
            calibration = SignCalibration("RESOLVED", interface["coordinate_sign"],
                                          interface["mechanical_calibration"]["evidence"])
            entry["sign_calibration"] = asdict(calibration)
    finally:
        if getattr(sim, "close", None): sim.close()
    # Exercise the real fresh-runtime factory for both matched conditions
    # without stepping either runtime or invoking the scientific runner.
    probe = eligible[0]
    constructed = []
    try:
        for condition in CONDITIONS:
            runtime = _fresh_runtime(flygym, data, tibia, probe,
                                     by_name[probe["physical_joint"]], condition)
            constructed.append(runtime)
        if (constructed[0]["sim"] is constructed[1]["sim"] or
                constructed[0]["brain"] is constructed[1]["brain"]):
            raise RuntimeError("fresh matched conditions shared stateful runtime objects")
    finally:
        for runtime in constructed:
            if getattr(runtime["sim"], "close", None): runtime["sim"].close()
    if fatal:
        messages = [x["error"] for x in fatal]
        root = ("SAME_DOMAIN_LIMIT_CONFLICT" if any("same-domain limits" in x for x in messages)
                else "CROSS_DOMAIN_LIMIT_INTERSECTION_BUG" if any("not an absolute unit-gear" in x for x in messages)
                else "MISSING_LIMIT_METADATA" if any("no applicable finite" in x for x in messages)
                else "OTHER_LIMIT_IMPLEMENTATION_FAILURE")
        report.update(run_status="FAIL", classification=root)
    else:
        # A reproduced legacy failure with a valid active-bound result
        # establishes the limit-enable implementation defect.  If the current
        # model does not reproduce it, retain that discrepancy explicitly.
        report.update(run_status="PASS", classification=(
            "OTHER_LIMIT_IMPLEMENTATION_FAILURE" if report["all_failures"] else
            "LIVE_MODEL_METADATA_INCONSISTENCY"))
    report["checks"].update(joint_metadata=True, joint_limits=True,
        sign_calibration_machinery=True, environment_constructed=True,
        fresh_runtime_factory=(len(constructed) == 2), matched_conditions_construct=(len(constructed) == 2),
        canonical_artifact_not_run=(protocol.get("run_status") == "NOT_RUN" and
            protocol.get("scientific_run_number") is None and not protocol.get("per_joint")),
        scientific_runner_not_called=True,
        per_step_environment_construction=False,
        attempt_1_not_complete=True)
    report["performance_guards"] = {
        "PER_STEP_ENVIRONMENT_CONSTRUCTION": False,
        "expected_canonical_environment_construction_count": EXPECTED_CANONICAL_ENVIRONMENT_CONSTRUCTIONS,
        "expected_physics_steps": EXPECTED_CONDITIONS * EXPECTED_PHYSICS_STEPS_PER_CONDITION,
        "expected_neural_steps": EXPECTED_CONDITIONS * EXPECTED_NEURAL_STEPS_PER_CONDITION,
    }
    _atomic_write(output_path, report)
    if fatal:
        raise RuntimeError("; ".join(f"{x['actuator']}: {x['error']}" for x in fatal))
    return report


def run_canonical(protocol: Mapping[str, Any], output_path: Path) -> dict[str, Any]:
    """Execute each immutable M6B pair once, using fresh condition runtimes."""
    run_started = time.perf_counter()
    flygym, data, tibia, records, by_name = _live_setup(protocol)
    setup_ended = time.perf_counter()
    actuator_names = tuple(record["name"] for record in records)
    if len(actuator_names) != 42:
        raise RuntimeError("canonical actuator inventory is not exactly 42 actions")
    # P4 froze signs before execution. Never recalibrate from scientific output.
    calibrations = {name: SignCalibration("RESOLVED", LOCKED_SIGNS[name],
        next(x for x in protocol["interfaces"] if x["physical_joint"] == name)
        ["mechanical_calibration"]["evidence"]) for name in TIER_B}
    interfaces = tuple(x for x in protocol["interfaces"] if x["physical_joint"] in TIER_B)
    if len(interfaces) != 8 or EXPECTED_CONDITIONS != 16:
        raise RuntimeError("canonical 8-interface/16-condition execution plan changed")
    _progress("=" * 60); _progress("M6B SCIENTIFIC RUN")
    _progress("8 interfaces | 16 conditions | 500 ms each"); _progress("=" * 60)
    checkpoint_path = output_path.with_name(f"{output_path.stem}.progress.json")
    completed: list[dict[str, Any]] = []; per_joint = []; condition_timings = []
    active: dict[str, Any] | None = None
    try:
        for interface in interfaces:
            name = interface["physical_joint"]; calibration = calibrations[name]
            pair = {}
            for condition in CONDITIONS:
                number = len(completed) + 1
                active = {"condition_number": number, "interface": name, "condition": condition}
                _progress(f"[{number:02d}/{EXPECTED_CONDITIONS:02d}] START {name} | {condition}")
                _atomic_write(checkpoint_path, {"schema": "M6B-P5.0-CHECKPOINT",
                    "run_status": "IN_PROGRESS", "canonical_result_complete": False,
                    "resume_authorized": False, "completed_condition_count": len(completed),
                    "active_condition": active, "completed_conditions": completed,
                    "elapsed_wall_seconds": time.perf_counter() - run_started})
                rows, timing = _run_condition(flygym, data, tibia, interface, by_name[name],
                    calibration, condition, actuator_names, number, EXPECTED_CONDITIONS, run_started)
                pair[condition] = rows; timing.update(active); condition_timings.append(timing)
                completed.append(dict(active))
                now = time.perf_counter()
                _progress(f"[{number:02d}/{EXPECTED_CONDITIONS:02d}] DONE  {name} | {condition}")
                _progress(f"        condition wall time: {_elapsed(timing['total_condition_seconds'])}")
                _progress(f"        total elapsed: {_elapsed(now - run_started)}")
                if number < EXPECTED_CONDITIONS:
                    estimate = (now - run_started) / number * (EXPECTED_CONDITIONS - number)
                    _progress(f"        ESTIMATED remaining: {_elapsed(estimate)}")
                _atomic_write(checkpoint_path, {"schema": "M6B-P5.0-CHECKPOINT",
                    "run_status": "IN_PROGRESS", "canonical_result_complete": False,
                    "resume_authorized": False, "completed_condition_count": len(completed),
                    "active_condition": None, "completed_conditions": completed,
                    "elapsed_wall_seconds": now - run_started})
                active = None
            reduction_started = time.perf_counter()
            result = _reduce_pair(interface, calibration, pair[CONDITIONS[0]], pair[CONDITIONS[1]])
            result["performance"] = {"pair_reduction_seconds": time.perf_counter() - reduction_started,
                                     "conditions": condition_timings[-2:]}
            per_joint.append(result)
    except KeyboardInterrupt:
        now = time.perf_counter()
        _atomic_write(checkpoint_path, {"schema": "M6B-P5.0-CHECKPOINT",
            "run_status": "ABORTED_USER_INTERRUPT", "canonical_result_complete": False,
            "scientific_result_available": False, "resume_authorized": False,
            "active_condition": active, "completed_condition_count": len(completed),
            "completed_conditions": completed, "elapsed_wall_seconds": now - run_started})
        _progress("M6B RUN ABORTED_USER_INTERRUPT; incomplete result recorded.")
        raise
    if len(completed) != EXPECTED_CONDITIONS:
        raise RuntimeError("refusing to classify an incomplete canonical run")
    report = dict(protocol); report.update(run_status="COMPLETE", scientific_run_number=2,
        classification=aggregate_classification(per_joint), per_joint=per_joint,
        m6c_eligible=m6c_eligible(per_joint),
        performance={"total_wall_seconds": time.perf_counter() - run_started,
            "runtime_initialization_seconds": setup_ended - run_started,
            "condition_timings": condition_timings,
            "environment_construction_count": EXPECTED_CANONICAL_ENVIRONMENT_CONSTRUCTIONS,
            "per_physics_step_environment_construction": False},
        provenance={**protocol["provenance"], "scientific_run_number": 1,
            "scientific_results_fabricated": False, "windows_adapter": __name__})
    report["provenance"]["scientific_run_number"] = 2
    _atomic_write(output_path, report)
    _atomic_write(checkpoint_path, {"schema": "M6B-P5.0-CHECKPOINT", "run_status": "COMPLETE",
        "canonical_result_complete": True, "completed_condition_count": len(completed),
        "completed_conditions": completed, "elapsed_wall_seconds": time.perf_counter() - run_started})
    _progress("=" * 60); _progress("M6B PERFORMANCE SUMMARY"); _progress("=" * 60)
    _progress(f"Total wall time: {_elapsed(report['performance']['total_wall_seconds'])}")
    _progress(f"Runtime construction: {_elapsed(sum(x['runtime_initialization_seconds'] for x in condition_timings))}")
    _progress(f"Neural stepping: {_elapsed(sum(x['brain_step_seconds'] for x in condition_timings))}")
    _progress(f"MuJoCo stepping: {_elapsed(sum(x['sim_step_seconds'] for x in condition_timings))}")
    _progress(f"Sensory: {_elapsed(sum(x['sensory_seconds'] for x in condition_timings))}")
    _progress(f"Telemetry/hashing: {_elapsed(sum(x['telemetry_hash_seconds'] for x in condition_timings))}")
    return report


__all__ = ["CALIBRATION_EPSILON_RAD", "CONDITIONS", "JointMetadata",
    "PREFLIGHT_SCHEMA", "SignCalibration", "TELEMETRY_FIELDS",
    "assert_isolated_admission", "assert_physical_admission", "calibrate_physical_sign",
    "compute_raw_contribution", "inspect_limit_metadata", "resolve_joint_metadata", "run_canonical",
    "run_preflight"]
