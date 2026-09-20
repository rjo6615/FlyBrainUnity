"""Canonical live condition loop for M6C (lazy Windows/FlyGym imports).

No locomotion policy is present: every command is the independently decoded
output of one admitted mapped population, added to the current measured joint
position through the already validated safety pipeline.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Any, Mapping, Sequence


def _digest(brain: Any) -> str:
    """Return the validated MaleCNS state digest used by M5/M6."""
    from .tactile_motor_loop_audit import _state_tuple
    return _state_tuple(brain)


def _pre_intervention_snapshot(*, brain: Any, physics: Any, commands: Any,
                               encoders: Mapping[str, Any], channels: Mapping[str, Any],
                               rngs: Mapping[str, Any], cached_table: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Snapshot real runtime state before any sensory, neural, or physics step."""
    import numpy as np
    from .six_tibia import LEG_ORDER

    return {"qpos": np.asarray(physics.data.qpos).tolist(),
        "qvel": np.asarray(physics.data.qvel).tolist(), "action": np.asarray(commands).tolist(),
        "ctrl": np.asarray(physics.data.ctrl).tolist(),
        "sensory_encoder_state": {leg: {"actuator": encoders[leg].pathway.actuator_name,
            "sensor_body_ids": list(encoders[leg].pathway.sensor.body_ids)} for leg in LEG_ORDER},
        "malecns_state": _digest(brain), "spike_counts": np.asarray(brain.spike_counts).tolist(),
        "observer_state": {name: {"filtered_hz": x["observer"].filtered_hz.tolist(),
            "last_counts": x["observer"].last_counts.tolist()} for name, x in channels.items()},
        "decoder_state": {name: x["pipeline"].previous_physical_target for name, x in channels.items()},
        "rng_state": {leg: hashlib.sha256(repr(rngs[leg].bit_generator.state).encode()).hexdigest()
                      for leg in LEG_ORDER},
        "baseline_action": np.asarray(commands).tolist(),
        "admitted_actuator_metadata": [(x["actuator"], x["action_index"], x["coordinate_sign"])
                                         for x in cached_table if x["neural_motor_admission"]]}


def run_condition(*, protocol: Mapping[str, Any], condition: str, condition_number: int,
                  progress: Any, cached_admission_assertion: Any,
                  cached_records: Sequence[Mapping[str, Any]],
                  cached_table: Sequence[Mapping[str, Any]],
                  initialize_only: bool = False, duration_ms: float | None = None,
                  condition_names: Sequence[str] | None = None,
                  contribution_gate: Any | None = None,
                  compact_telemetry: bool = False) -> Mapping[str, Any]:
    """Create, run, close, and summarize one fresh frozen runtime.

    The optional arguments are used by M7 to reuse this exact M6C embodiment.
    M6C callers receive the original behaviour by default.
    """
    import numpy as np
    import flygym
    from malecns_backend import MaleCNSBrain, load_malecns
    from .integrated_whole_leg_readiness import CONDITIONS, DURATION_MS, EXPECTED_TIER_B, SEED, TIER_A, gate_contributions
    from .isolated_tier_b_motor_validation import OBSERVER_TAU_MS, SLEW_RAD_S, safe_contribution_bound
    from ._windows_isolated_tier_b_motor_validation_adapter import (_population_index, _rate,
        compute_raw_contribution, resolve_joint_metadata)
    from .motor import MotorActivityObserver, MotorSafety
    from .proprioceptive_activation import proprio_rngs, sample_candidates
    from .sensory import LegSensoryFrame, SensoryEncoder
    from .six_tibia import LEG_ORDER, load_six_tibia_interfaces
    from .tactile_contact import TactileContactConfig, TactileContactEncoder
    from .tactile_motor_loop import ACTUATOR_INDICES, NEURAL_DT_MS
    from .tactile_motor_loop_audit import _forces, _joint_positions, _make_live
    from .tactile_motor_matched_control import MatchedControlPipeline
    from .tactile_targeted_contact_calibration import DEFAULT_TIMESTEP_S
    from .m7_telemetry import (CompactTelemetry, build_schema, roundtrip_minimal,
                               sensory_channel_peaks)

    allowed_conditions = tuple(condition_names or CONDITIONS)
    if condition not in allowed_conditions: raise ValueError("unknown canonical condition")
    run_duration_ms = float(DURATION_MS if duration_ms is None else duration_ms)
    gate = contribution_gate or gate_contributions
    started = time.perf_counter(); data = load_malecns(); tibia = load_six_tibia_interfaces()
    sim, physics, obs, _, _ = _make_live(flygym, tibia)
    phase = {"initialization": 0., "neural_stepping": 0., "mujoco_stepping": 0.,
        "sensory": 0., "observer_decoder": 0., "telemetry_hash": 0.,
        "admission_assertion": 0., "reduction_analysis": 0.}
    channels = {}; admitted_names = tuple(protocol["admitted_motor_interfaces"])
    by_record = {r["name"]: r for r in cached_records}
    table_by_name = {r["actuator"]: r for r in cached_table}
    m6b_interfaces = {x["physical_joint"]: x for x in json.loads(
        __import__("pathlib").Path(__file__).with_name("interface_output").joinpath(
            "isolated_tier_b_motor_validation.json").read_text())["interfaces"]}
    try:
        brain = MaleCNSBrain(data); brain.reset(SEED)
        # Every channel owns observer, decoder safety, slew history, and telemetry.
        for name in admitted_names:
            row = table_by_name[name]; index = row["action_index"]
            metadata = resolve_joint_metadata(physics, by_record[name])
            baseline = float(_joint_positions(obs)[index])
            bound = safe_contribution_bound(metadata.joint_min, metadata.joint_max, baseline)
            if name in TIER_A:
                interface = tibia[row["leg"]]
                populations = {p.name: p.dense_indices for p in interface.motor_populations}
                positive = tuple(p.name for p in interface.motor_populations if p.direction == 1)
                negative = tuple(p.name for p in interface.motor_populations if p.direction == -1)
                sign = 1
            else:
                interface = m6b_interfaces[name]
                populations, positive, negative = _population_index(interface, data)
                sign = int(row["coordinate_sign"])
            observer = MotorActivityObserver(populations, OBSERVER_TAU_MS); observer.reset(brain.spike_counts)
            channels[name] = {"index": index, "metadata": metadata, "bound": bound,
                "populations": populations, "positive": positive, "negative": negative, "sign": sign,
                "observer": observer, "pipeline": MatchedControlPipeline(True,
                    MotorSafety(metadata.joint_min, metadata.joint_max, bound, SLEW_RAD_S)),
                "spikes": 0, "peak_observer": 0., "peak_raw": 0., "peak_admitted": 0.,
                "first_activity_ms": None, "first_decoder_output_ms": None,
                "first_admitted_contribution_ms": None, "saturation": False, "slew_limited": False}
        tactile = TactileContactEncoder(config=TactileContactConfig(seed=SEED))
        encoders = {leg: SensoryEncoder(tibia[leg]) for leg in LEG_ORDER}; rngs = proprio_rngs(SEED)
        commands = _joint_positions(obs); pending = set(); stride = int(round(NEURAL_DT_MS / (DEFAULT_TIMESTEP_S * 1000)))
        final_step = int(round(run_duration_ms / (DEFAULT_TIMESTEP_S * 1000))); contributions = dict.fromkeys(admitted_names, 0.)
        trajectory = []
        aggregate_spikes = 0; instability = False; unauthorized = 0
        pre_intervention_state = _pre_intervention_snapshot(brain=brain, physics=physics,
            commands=commands, encoders=encoders, channels=channels, rngs=rngs,
            cached_table=cached_table)
        # Construct and validate the exact admitted command shape during both
        # preflight and science initialization.  This is deliberately before
        # every sensory, decoder, neural, and physics transition.
        initialization_vector = [0.] * 42
        cached_admission_assertion(initialization_vector, cached_table)
        model = physics.model
        initial_audit = {"initial_pose_source": "FlyGym default pose (no pose override)",
                "body_position": np.asarray(physics.data.qpos[:3]).tolist(),
                "body_orientation_quaternion": np.asarray(physics.data.qpos[3:7]).tolist(),
                "joint_configuration": np.asarray(commands).tolist(),
                "qpos": np.asarray(physics.data.qpos).tolist(), "qvel": np.asarray(physics.data.qvel).tolist(),
                "ground": "FlyGym FlatTerrain plus static m5d2c_calibration_surface positioned once at reset under LMTarsus5",
                "ground_dynamic_after_reset": False,
                "gravity": np.asarray(model.opt.gravity).tolist(),
                "adhesion_enabled": False, "adhesion_command": [0.0] * 6,
                "adhesion_policy": "constant zero baseline; no schedule or controller",
                "control": "position", "locomotion_or_reference_controller": False}
        telemetry = None; schema_report = {}
        if compact_telemetry:
            telemetry_schema = build_schema(qpos_shape=np.asarray(physics.data.qpos).shape,
                qvel_shape=np.asarray(physics.data.qvel).shape, ctrl_shape=np.asarray(physics.data.ctrl).shape,
                contact_forces_shape=np.asarray(_forces(obs)).shape,
                joint_shape=np.asarray(commands).shape, action_shape=np.asarray(commands).shape)
            # Preflight uses a one-sample payload; science allocates the frozen
            # full capacities. Both paths validate the identical field schema.
            roundtrip_minimal(telemetry_schema)
            telemetry = CompactTelemetry(telemetry_schema,
                physics_capacity=(1 if initialize_only else final_step + 1),
                neural_capacity=(1 if initialize_only else final_step // stride))
            schema_report = {name: {"sample_shape": list(field.sample_shape),
                "dtype": str(field.dtype), "cadence": field.cadence, "meaning": field.meaning}
                for name, field in telemetry_schema.items()}
        if initialize_only:
            return {"pre_intervention_state": pre_intervention_state,
                "initial_physical_state_audit": initial_audit,
                "telemetry_initialized": isinstance(trajectory, list),
                "telemetry_schema": schema_report,
                "telemetry_npz_roundtrip": bool(compact_telemetry),
                "telemetry_object_dtype": False if compact_telemetry else None,
                "admission_vector_length": len(initialization_vector),
                "neural_steps": 0, "physics_steps": 0,
                "sensory_updates": 0, "decoder_updates": 0,
                "motor_interventions": 0}
        phase["initialization"] = time.perf_counter() - started
        condition_started = time.perf_counter()
        for step in range(final_step + 1):
            now_ms = float(physics.data.time * 1000); measured = _joint_positions(obs)
            sensory_started = time.perf_counter()
            contact = tactile.encode(_forces(obs), now_ms, DEFAULT_TIMESTEP_S * 1000)["LM"]
            pending.update(map(int, contact.generated_dense_indices)); delivered = ()
            phase["sensory"] += time.perf_counter() - sensory_started
            if step and step % stride == 0:
                neural_started = time.perf_counter(); brain.clear_external_drive(); candidates = set(pending); pending.clear()
                sensory_values = {}
                for leg in LEG_ORDER:
                    encoded = encoders[leg].encode(LegSensoryFrame(now_ms / 1000, float(measured[ACTUATOR_INDICES[leg]])))
                    sensory_values[leg] = tuple(map(float, encoded.rates_hz))
                    local = sample_candidates(encoded.rates_hz, rngs[leg]); candidates.update(int(encoded.indices[i]) for i in local)
                if candidates: brain.set_external_drive(tuple(sorted(candidates)), 1000. / brain.config.dt)
                brain.external_drive_withheld_indices = np.empty(0, np.intp); brain.step()
                delivered = tuple(map(int, brain._last_external_delivered)); aggregate_spikes = int(np.sum(brain.spike_counts))
                phase["neural_stepping"] += time.perf_counter() - neural_started
                decode_started = time.perf_counter(); raw_values = {}
                for name, channel in channels.items():
                    observed = channel["observer"].update(brain.spike_counts, NEURAL_DT_MS)
                    pos = _rate(channel["positive"], observed["filtered_hz"], channel["populations"])
                    neg = _rate(channel["negative"], observed["filtered_hz"], channel["populations"])
                    raw = compute_raw_contribution(pos, neg, channel["bound"], channel["sign"]); raw_values[name] = raw
                    increments = sum(observed["increments"].values()); channel["spikes"] += increments
                    peak_observer = max([abs(x) for x in observed["filtered_hz"].values()] or [0.])
                    channel["peak_observer"] = max(channel["peak_observer"], peak_observer); channel["peak_raw"] = max(channel["peak_raw"], abs(raw))
                    if increments and channel["first_activity_ms"] is None: channel["first_activity_ms"] = now_ms
                    if raw and channel["first_decoder_output_ms"] is None: channel["first_decoder_output_ms"] = now_ms
                contributions = gate(raw_values, condition, admitted_names)
                neural_vector = [0.] * 42
                for name, channel in channels.items():
                    result = channel["pipeline"].update(float(measured[channel["index"]]), contributions[name], NEURAL_DT_MS / 1000)
                    commands[channel["index"]] = result.actuator_command; neural_vector[channel["index"]] = result.admitted_neural_contribution
                    channel["peak_admitted"] = max(channel["peak_admitted"], abs(result.admitted_neural_contribution))
                    channel["saturation"] |= result.range_clamped_target != result.candidate_target
                    channel["slew_limited"] |= result.slew_limited_target != result.range_clamped_target
                    if result.admitted_neural_contribution and channel["first_admitted_contribution_ms"] is None: channel["first_admitted_contribution_ms"] = now_ms
                assert_started = time.perf_counter(); cached_admission_assertion(neural_vector, cached_table)
                phase["admission_assertion"] += time.perf_counter() - assert_started
                phase["observer_decoder"] += time.perf_counter() - decode_started
                if compact_telemetry:
                    telemetry.record("neural", {
                        "neural_time_ms": now_ms,
                        "neural_sensory_encoded": sensory_channel_peaks(
                            [sensory_values[leg] for leg in LEG_ORDER]),
                        "neural_delivered_drive_count": len(delivered),
                        "neural_aggregate_spikes": aggregate_spikes,
                        "neural_observer_outputs": [channels[n]["peak_observer"] for n in admitted_names],
                        "neural_decoder_outputs": [raw_values[n] for n in admitted_names],
                        "neural_admitted_contributions": [contributions[n] for n in admitted_names],
                    }, now_ms)
            telemetry_started = time.perf_counter(); arrays = (physics.data.qpos, physics.data.qvel, physics.data.ctrl)
            finite = all(np.all(np.isfinite(a)) for a in arrays); instability |= not finite
            if compact_telemetry:
                telemetry.record("physics", {"physics_time_ms": now_ms,
                    "physics_qpos": physics.data.qpos, "physics_qvel": physics.data.qvel,
                    "physics_joint_position": measured, "physics_action": commands,
                    "physics_ctrl": physics.data.ctrl, "physics_body_position": physics.data.qpos[:3],
                    "physics_body_orientation": physics.data.qpos[3:7],
                    "physics_contact_forces": _forces(obs), "physics_finite": finite}, now_ms)
            else:
                trajectory.append({"time_ms": now_ms, "qpos": np.asarray(physics.data.qpos).tolist(),
                "qvel": np.asarray(physics.data.qvel).tolist(), "action": np.asarray(commands).tolist(),
                "ctrl": np.asarray(physics.data.ctrl).tolist(), "body_position": np.asarray(physics.data.qpos[:3]).tolist(),
                "body_orientation": np.asarray(physics.data.qpos[3:7]).tolist(), "sensory": sensory_values if step and step % stride == 0 else {},
                "delivered_sensory_drive": delivered, "malecns_state_digest": _digest(brain),
                "aggregate_cns_spike_count": aggregate_spikes, "finite": finite})
            phase["telemetry_hash"] += time.perf_counter() - telemetry_started
            if not finite or step == final_step: break
            sim_started = time.perf_counter(); obs = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})[0]
            phase["mujoco_stepping"] += time.perf_counter() - sim_started
            if step and step % max(1, final_step // 10) == 0:
                elapsed = time.perf_counter() - started
                print(progress(condition_number, condition, step / final_step, step,
                    time.perf_counter() - condition_started, elapsed, elapsed / max(step, 1) * (final_step-step)), flush=True)
        active_channels = [name for name, x in channels.items() if x["peak_admitted"] > 0]
        legs = {table_by_name[name]["leg"] for name in active_channels}
        local = {"C1": any(x["spikes"] for x in channels.values()), "C2": any(x["peak_raw"] for x in channels.values()),
            "C3": bool(active_channels), "C6": len(active_channels) >= 2, "C7": len(legs) >= 2}
        summaries = []
        for name, x in channels.items():
            status = ("NO_MAPPED_MOTOR_ACTIVITY" if not x["spikes"] else
                "MAPPED_MOTOR_ACTIVITY_NO_DECODER_OUTPUT" if not x["peak_raw"] else
                "DECODER_OUTPUT_NO_ADMITTED_OUTPUT" if not x["peak_admitted"] else
                "MAPPED_MOTOR_ACTIVITY_AND_PHYSICAL_OUTPUT")
            summaries.append({"actuator": name, "status": status, **{k: v for k, v in x.items()
                if k in ("spikes", "peak_observer", "peak_raw", "peak_admitted", "first_activity_ms",
                         "first_decoder_output_ms", "first_admitted_contribution_ms", "saturation", "slew_limited")}})
        raw_arrays = telemetry.export() if compact_telemetry else {}
        return {"pre_intervention_equivalence": True, "pre_intervention_state": pre_intervention_state,
            "initial_physical_state_audit": initial_audit,
            "local_milestones": local,
            "unauthorized_contribution_count": unauthorized, "physics_instability": instability,
            "per_channel": summaries, "trajectory": trajectory, "raw_arrays": raw_arrays,
            "physics_steps": final_step if not instability else (
                telemetry.counts["physics"] - 1 if compact_telemetry else len(trajectory) - 1),
            "neural_steps": telemetry.counts["neural"] if compact_telemetry else final_step // stride,
            "feedback_milestones": {}, "performance": phase}
    finally:
        close = getattr(sim, "close", None)
        if close: close()
