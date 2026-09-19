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
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from malecns_backend import MaleCNSBrain, load_malecns
from . import tactile_targeted_contact_calibration as contact
from .full_leg_interface import enumerate_live_actuators
from .isolated_tier_b_motor_validation import (
    CANONICAL_SEED, DURATION_MS, EQUIVALENCE_FIELDS, M6A_SHA256,
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
PREFLIGHT_SCHEMA = "M6B-WINDOWS-PREFLIGHT.0"
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


def resolve_joint_metadata(physics: Any, record: Mapping[str, Any]) -> JointMetadata:
    """Resolve and validate the selected 1-DoF joint from compiled MuJoCo data."""
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
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid MuJoCo metadata for {record.get('name')}: {exc}") from exc
    values = (*axis, *joint_range, *ctrl_range)
    if not all(math.isfinite(x) for x in values) or np.linalg.norm(axis) == 0:
        raise RuntimeError("non-finite or zero-axis joint metadata")
    lo, hi = max(joint_range[0], ctrl_range[0]), min(joint_range[1], ctrl_range[1])
    if lo >= hi:
        raise RuntimeError("joint and actuator limits have no valid intersection")
    return JointMetadata(int(record["index"]), aid, jid, qidx, vidx, axis,
                         lo, hi, ctrl_range[0], ctrl_range[1])


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


def _run_condition(flygym: Any, data: Any, tibia_interfaces: Mapping[str, Any],
                   interface: Mapping[str, Any], metadata_record: Mapping[str, Any],
                   calibration: SignCalibration, condition: str) -> list[dict[str, Any]]:
    if condition not in CONDITIONS: raise ValueError("unknown M6B condition")
    if calibration.status != "RESOLVED" or calibration.coordinate_sign not in (-1, 1):
        raise RuntimeError("SIGN_UNRESOLVED interfaces cannot receive neural actuation")
    runtime = _fresh_runtime(flygym, data, tibia_interfaces, interface, metadata_record, condition)
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
    try:
        for step in range(final_step + 1):
            time_ms = float(physics.data.time * 1000.0); measured = _joint_positions(obs)
            forces = _forces(obs); tactile = tactile_encoder.encode(forces, time_ms, PHYSICS_DT_MS)["LM"]
            pending.update(map(int, tactile.generated_dense_indices))
            if step and step % stride == 0:
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
                "brain_state_digest": _state_tuple(brain)}
            if set(TELEMETRY_FIELDS) - set(row): raise RuntimeError("telemetry contract incomplete")
            rows.append(row)
            if not valid: break
            if step == final_step: break
            obs = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})[0]
    finally:
        if getattr(sim, "close", None): sim.close()
    return rows


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
    return flygym, data, tibia, records, by_name


def run_preflight(protocol: Mapping[str, Any], output_path: Path) -> dict[str, Any]:
    """Perform engineering construction/calibration only; never run 500-ms trials."""
    report: dict[str, Any] = {"schema": PREFLIGHT_SCHEMA, "artifact_kind": "NON_SCIENTIFIC_PREFLIGHT",
        "scientific_run_executed": False, "scientific_run_number_consumed": None,
        "m6a_sha256": M6A_SHA256, "checks": {}, "interfaces": []}
    flygym, data, tibia, records, by_name = _live_setup(protocol)
    report["checks"].update(dependencies_import=True, malecns_loaded=True,
        action_order_42=True, tier_b_indices=True, tibia_indices_unchanged=True,
        motor_body_ids=True, matched_control_pipeline=True,
        telemetry_contract=set(EQUIVALENCE_FIELDS).issubset(TELEMETRY_FIELDS))
    # One environment is constructed and perturbed for engineering calibration;
    # _run_condition is deliberately never called here.
    sim, physics, obs, _, _ = _make_live(flygym, tibia)
    try:
        for interface in protocol["interfaces"]:
            record = by_name[interface["physical_joint"]]
            if record["index"] != interface["action_index"]: raise RuntimeError("M6A/live action index mismatch")
            _population_index(interface, data)
            metadata = resolve_joint_metadata(physics, record)
            baseline = float(_joint_positions(obs)[record["index"]])
            bound = safe_contribution_bound(metadata.joint_min, metadata.joint_max, baseline)
            safety = MotorSafety(metadata.joint_min, metadata.joint_max,
                                 bound, SLEW_RAD_S)
            # Construct both sides of the exact M5D-4C path, but do not update
            # or step them during engineering preflight.
            MatchedControlPipeline(True, safety)
            MatchedControlPipeline(False, safety)
            calibration = calibrate_physical_sign(physics, metadata, interface)
            # Unresolved is a valid, fail-closed calibration result. Machinery
            # failure is not; retain the evidence for Windows review.
            report["interfaces"].append({"actuator": interface["physical_joint"],
                "metadata": asdict(metadata), "safe_contribution_bound_rad": bound,
                "sign_calibration": asdict(calibration)})
    finally:
        if getattr(sim, "close", None): sim.close()
    report["checks"].update(joint_metadata=True, joint_limits=True,
        sign_calibration_machinery=True, environment_constructed=True,
        fresh_runtime_factory=callable(_fresh_runtime), scientific_runner_not_called=True)
    _atomic_write(output_path, report)
    return report


def run_canonical(protocol: Mapping[str, Any], output_path: Path) -> dict[str, Any]:
    """Execute each immutable M6B pair once, using fresh condition runtimes."""
    flygym, data, tibia, records, by_name = _live_setup(protocol)
    # Calibrate all joints before the first scientific condition.
    calibrations = {}
    sim, physics, obs, _, _ = _make_live(flygym, tibia)
    try:
        for interface in protocol["interfaces"]:
            record = by_name[interface["physical_joint"]]
            metadata = resolve_joint_metadata(physics, record)
            calibrations[interface["physical_joint"]] = calibrate_physical_sign(physics, metadata, interface)
    finally:
        if getattr(sim, "close", None): sim.close()
    per_joint = []
    for interface in protocol["interfaces"]:
        name = interface["physical_joint"]; calibration = calibrations[name]
        if calibration.status != "RESOLVED":
            per_joint.append({"actuator": name, "action_index": interface["action_index"],
                "physical_sign_status": "SIGN_UNRESOLVED", "sign_calibration": asdict(calibration),
                "classification": "SIGN_UNRESOLVED", "scientific_conditions_executed": False})
            continue
        enabled = _run_condition(flygym, data, tibia, interface, by_name[name], calibration, CONDITIONS[0])
        disabled = _run_condition(flygym, data, tibia, interface, by_name[name], calibration, CONDITIONS[1])
        per_joint.append(_reduce_pair(interface, calibration, enabled, disabled))
    report = dict(protocol); report.update(run_status="COMPLETE",
        classification=aggregate_classification(per_joint), per_joint=per_joint,
        m6c_eligible=m6c_eligible(per_joint),
        provenance={**protocol["provenance"], "scientific_run_number": 1,
            "scientific_results_fabricated": False, "windows_adapter": __name__})
    _atomic_write(output_path, report)
    return report


__all__ = ["CALIBRATION_EPSILON_RAD", "CONDITIONS", "JointMetadata",
    "PREFLIGHT_SCHEMA", "SignCalibration", "TELEMETRY_FIELDS",
    "assert_isolated_admission", "calibrate_physical_sign",
    "compute_raw_contribution", "resolve_joint_metadata", "run_canonical",
    "run_preflight"]
