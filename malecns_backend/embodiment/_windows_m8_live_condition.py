"""M8-only copy of the validated live loop with identity-bearing telemetry.

No locomotion policy is present: every command is the independently decoded
output of one admitted mapped population, added to the current measured joint
position through the already validated safety pipeline.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import time
from typing import Any, Mapping, Sequence


def _legacy_neural_telemetry(*, admitted_names: Sequence[str], channels: Mapping[str, Any],
                             raw_values: Mapping[str, float], contributions: Mapping[str, float],
                             isolated_candidate_telemetry: bool) -> tuple[list[float], list[float], list[float]]:
    """Build only the historical 11-channel compact-telemetry payload."""
    if isolated_candidate_telemetry:
        return [0.0] * 11, [0.0] * 11, [0.0] * 11
    return ([channels[name]["peak_observer"] for name in admitted_names],
            [raw_values[name] for name in admitted_names],
            [contributions[name] for name in admitted_names])


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


def _scientific_transition_kernel(*, protocol: Mapping[str, Any], condition: str, condition_number: int,
                  progress: Any, cached_admission_assertion: Any,
                  cached_records: Sequence[Mapping[str, Any]],
                  cached_table: Sequence[Mapping[str, Any]],
                  initialize_only: bool = False, duration_ms: float | None = None,
                  condition_names: Sequence[str] | None = None,
                  contribution_gate: Any | None = None,
                  compact_telemetry: bool = False,
                  runtime_factory: Any | None = None,
                  proprioception_only: bool = False,
                  fixed_initial_baseline: bool = False,
                  m8_extended_telemetry: bool = True,
                  external_force_by_transition: Any | None = None,
                  m9b_extended_telemetry: bool = False,
                  m10b_extended_telemetry: bool = False,
                  motor_channel_names: Sequence[str] | None = None,
                  detailed_motor_telemetry: bool = False,
                  final_contribution_gate: Any | None = None,
                  isolated_candidate_telemetry: bool = False,
                  pause_at_states: bool = False,
                  continuous: bool = False) -> Mapping[str, Any]:
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
    sim, physics, obs, _, _ = (runtime_factory or _make_live)(flygym, tibia)
    phase = {"initialization": 0., "neural_stepping": 0., "mujoco_stepping": 0.,
        "sensory": 0., "observer_decoder": 0., "telemetry_hash": 0.,
        "admission_assertion": 0., "reduction_analysis": 0.}
    channels = {}; admitted_names = tuple(motor_channel_names or protocol["admitted_motor_interfaces"])
    if detailed_motor_telemetry and len(admitted_names) != 1:
        raise ValueError("detailed motor telemetry requires exactly one selected channel")
    if isolated_candidate_telemetry and not detailed_motor_telemetry:
        raise ValueError("isolated candidate telemetry requires detailed motor telemetry")
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
        commands = _joint_positions(obs); baseline_commands = commands.copy()
        pending = set(); stride = int(round(NEURAL_DT_MS / (DEFAULT_TIMESTEP_S * 1000)))
        final_step = (None if continuous else
                      int(round(run_duration_ms / (DEFAULT_TIMESTEP_S * 1000))))
        contributions = dict.fromkeys(admitted_names, 0.)
        neural_vector = [0.] * 42
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
        from .m8_contact_kinematics import resolve as resolve_contacts, sample as sample_contacts
        contact_identity = resolve_contacts(model)
        m8_contacts, m8_feet = [], []
        m9b_force, m9b_pre_zero, m9b_post_zero, m9b_body_up, m9b_fall_rollover = [], [], [], [], []
        m10b_physical_inputs, m10b_delivered, m10b_mapped_motor, m10b_physical_motor = [], [], [], []
        detailed_motor, detailed_physical_vectors = [], []
        thorax_ids = [i for i, name in enumerate(contact_identity.get("body_names", {}).values())
                      if str(name).split("/")[-1] == "Thorax"]
        if external_force_by_transition is not None and len(thorax_ids) != 1:
            raise RuntimeError("authoritative Thorax body identity is not unique")
        initial_audit = {"initial_pose_source": ("FlyGym default pose (no pose override)" if runtime_factory is None
                                                else "caller-supplied frozen physical runtime"),
                "body_position": np.asarray(physics.data.qpos[:3]).tolist(),
                "body_orientation_quaternion": np.asarray(physics.data.qpos[3:7]).tolist(),
                "joint_configuration": np.asarray(commands).tolist(),
                "qpos": np.asarray(physics.data.qpos).tolist(), "qvel": np.asarray(physics.data.qvel).tolist(),
                "ground": "FlyGym FlatTerrain plus static m5d2c_calibration_surface positioned once at reset under LMTarsus5",
                "ground_dynamic_after_reset": False,
                "gravity": np.asarray(model.opt.gravity).tolist(),
                "adhesion_enabled": False, "adhesion_command": [0.0] * 6,
                "adhesion_policy": "constant zero baseline; no schedule or controller",
                "control": "position", "locomotion_or_reference_controller": False,
                "m8_contact_identity": {"available": contact_identity["available"],
                    "method": contact_identity["method"],
                    "body_names": contact_identity["body_names"],
                    "ground_geom_ids": list(contact_identity["ground_geom_ids"]),
                    "tarsus5_body_ids": contact_identity["tarsus5_body_ids"],
                    "tarsal_geom_ids": {k: list(v) for k, v in contact_identity["tarsal_geom_ids"].items()}}}
        telemetry = None; schema_report = {}
        if compact_telemetry:
            if continuous:
                raise ValueError("continuous sessions cannot allocate finite compact telemetry")
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
            result = {"pre_intervention_state": pre_intervention_state,
                "initial_physical_state_audit": initial_audit,
                "telemetry_initialized": isinstance(trajectory, list),
                "telemetry_schema": schema_report,
                "telemetry_npz_roundtrip": bool(compact_telemetry),
                "telemetry_object_dtype": False if compact_telemetry else None,
                "admission_vector_length": len(initialization_vector),
                "neural_steps": 0, "physics_steps": 0,
                "sensory_updates": 0, "decoder_updates": 0,
                "motor_interventions": 0}
            if pause_at_states:
                yield {"time_ms": float(physics.data.time * 1000),
                    "qpos": physics.data.qpos, "qvel": physics.data.qvel,
                    "joint_positions": commands, "commands": commands,
                    "brain": brain, "finite": True, "initialization_only": True,
                    "physics_transition": 0, "neural_transition_count": 0,
                    "adhesion": (0.,) * 6}
            return result
        phase["initialization"] = time.perf_counter() - started
        condition_started = time.perf_counter()
        # Phase-1 finite-loop equivalent: for step in range(final_step + 1)
        steps = itertools.count() if continuous else range(final_step + 1)
        for step in steps:
            now_ms = float(physics.data.time * 1000); measured = _joint_positions(obs)
            sensory_started = time.perf_counter()
            if not proprioception_only:
                contact = tactile.encode(_forces(obs), now_ms, DEFAULT_TIMESTEP_S * 1000)["LM"]
                pending.update(map(int, contact.generated_dense_indices))
            delivered = ()
            phase["sensory"] += time.perf_counter() - sensory_started
            if step and step % stride == 0:
                neural_started = time.perf_counter(); brain.clear_external_drive(); candidates = set(pending); pending.clear()
                sensory_values, sensory_indices = {}, {}
                for leg in LEG_ORDER:
                    encoded = encoders[leg].encode(LegSensoryFrame(now_ms / 1000, float(measured[ACTUATOR_INDICES[leg]])))
                    sensory_values[leg] = tuple(map(float, encoded.rates_hz))
                    sensory_indices[leg] = tuple(map(int, encoded.indices))
                    local = sample_candidates(encoded.rates_hz, rngs[leg]); candidates.update(int(encoded.indices[i]) for i in local)
                if candidates: brain.set_external_drive(tuple(sorted(candidates)), 1000. / brain.config.dt)
                brain.external_drive_withheld_indices = np.empty(0, np.intp); brain.step()
                delivered = tuple(map(int, brain._last_external_delivered)); aggregate_spikes = int(np.sum(brain.spike_counts))
                if m10b_extended_telemetry:
                    delivered_set = set(delivered)
                    m10b_physical_inputs.append([float(measured[ACTUATOR_INDICES[leg]]) for leg in LEG_ORDER])
                    m10b_delivered.append([sum(index in delivered_set for index in sensory_indices[leg])
                                           for leg in LEG_ORDER])
                phase["neural_stepping"] += time.perf_counter() - neural_started
                decode_started = time.perf_counter(); raw_values, mapped_values = {}, {}
                for name, channel in channels.items():
                    observed = channel["observer"].update(brain.spike_counts, NEURAL_DT_MS)
                    channel["last_observed"] = observed
                    pos = _rate(channel["positive"], observed["filtered_hz"], channel["populations"])
                    neg = _rate(channel["negative"], observed["filtered_hz"], channel["populations"])
                    raw = compute_raw_contribution(pos, neg, channel["bound"], channel["sign"]); raw_values[name] = raw
                    increments = sum(observed["increments"].values()); channel["spikes"] += increments
                    peak_observer = max([abs(x) for x in observed["filtered_hz"].values()] or [0.])
                    mapped_values[name] = peak_observer
                    channel["peak_observer"] = max(channel["peak_observer"], peak_observer); channel["peak_raw"] = max(channel["peak_raw"], abs(raw))
                    if increments and channel["first_activity_ms"] is None: channel["first_activity_ms"] = now_ms
                    if raw and channel["first_decoder_output_ms"] is None: channel["first_decoder_output_ms"] = now_ms
                if m10b_extended_telemetry:
                    m10b_mapped_motor.append([mapped_values[name] for name in admitted_names])
                contributions = gate(raw_values, condition, admitted_names)
                if m9b_extended_telemetry:
                    m9b_pre_zero.append([raw_values[n] for n in admitted_names])
                    m9b_post_zero.append([contributions[n] for n in admitted_names])
                neural_vector_before = [0.] * 42
                neural_vector = [0.] * 42
                for name, channel in channels.items():
                    baseline = (baseline_commands[channel["index"]] if fixed_initial_baseline
                                else measured[channel["index"]])
                    result = channel["pipeline"].update(float(baseline), contributions[name], NEURAL_DT_MS / 1000)
                    physical_contribution = (result.admitted_neural_contribution
                        if final_contribution_gate is None else float(final_contribution_gate(
                            name, channel["index"], result.admitted_neural_contribution, condition)))
                    if not math.isfinite(physical_contribution):
                        raise RuntimeError("non-finite final neural contribution")
                    neural_vector_before[channel["index"]] = result.admitted_neural_contribution
                    commands[channel["index"]] = (result.actuator_command if final_contribution_gate is None
                        else result.baseline_target + physical_contribution)
                    neural_vector[channel["index"]] = physical_contribution
                    channel["peak_admitted"] = max(channel["peak_admitted"], abs(physical_contribution))
                    channel["saturation"] |= result.range_clamped_target != result.candidate_target
                    channel["slew_limited"] |= result.slew_limited_target != result.range_clamped_target
                    if result.admitted_neural_contribution and channel["first_admitted_contribution_ms"] is None: channel["first_admitted_contribution_ms"] = now_ms
                    if detailed_motor_telemetry:
                        used = channel["observer"].used
                        previous_counts = channel["observer"].last_counts
                        channel_observed = channel["last_observed"]
                        per_neuron_increment = []
                        for dense_index in used:
                            increment = 0
                            for population_name, population in channel_observed["neurons"].items():
                                indices = [int(x) for x in channel["populations"].get(
                                    population_name, ())]
                                if int(dense_index) in indices:
                                    increment = int(population["increments"][indices.index(int(dense_index))])
                                    break
                            per_neuron_increment.append(increment)
                        from .isolated_tier_b_motor_validation import activation
                        antagonist = activation(pos) - activation(neg)
                        detailed_motor.append({"time_ms": now_ms,
                            "transition_index": step // stride,
                            "dense_indices": [int(x) for x in used],
                            "cumulative_spike_counts": [int(x) for x in previous_counts],
                            "spike_increments": per_neuron_increment,
                            "per_neuron_filtered_rates_hz": [float(x) for x in channel["observer"].filtered_hz],
                            "positive_directional_mean_hz": float(pos),
                            "negative_directional_mean_hz": float(neg),
                            "raw_antagonist_signal": float(antagonist),
                            "signed_signal_after_coordinate_sign": float(channel["sign"] * antagonist),
                            "processed_decoder_state": float(raw_values[name]),
                            "slew_limited_contribution": float(result.slew_limited_target - result.baseline_target),
                            "range_limited_contribution": float(result.range_clamped_target - result.baseline_target),
                            "candidate_contribution_before_intervention": float(result.admitted_neural_contribution),
                            "candidate_contribution_after_intervention": float(physical_contribution),
                            "final_candidate_neural_contribution_before_experimental_zeroing": float(result.admitted_neural_contribution),
                            "final_applied_candidate_contribution": float(physical_contribution),
                            "neural_contribution_vector_before_intervention": list(neural_vector_before),
                            "neural_contribution_vector_after_intervention": list(neural_vector),
                            "authorized_indices": [channel["index"]],
                            "nonzero_indices": [i for i, value in enumerate(neural_vector) if value != 0.0]})
                assert_started = time.perf_counter(); cached_admission_assertion(neural_vector, cached_table)
                phase["admission_assertion"] += time.perf_counter() - assert_started
                phase["observer_decoder"] += time.perf_counter() - decode_started
                if compact_telemetry:
                    # The compact fields are the immutable historical 11-channel
                    # contract.  An isolated candidate is deliberately outside
                    # that inventory and has separate detailed telemetry above.
                    legacy_observer, legacy_decoder, legacy_admitted = _legacy_neural_telemetry(
                        admitted_names=admitted_names, channels=channels, raw_values=raw_values,
                        contributions=contributions,
                        isolated_candidate_telemetry=isolated_candidate_telemetry)
                    telemetry.record("neural", {
                        "neural_time_ms": now_ms,
                        "neural_sensory_encoded": sensory_channel_peaks(
                            [sensory_values[leg] for leg in LEG_ORDER]),
                        "neural_delivered_drive_count": len(delivered),
                        "neural_aggregate_spikes": aggregate_spikes,
                        "neural_observer_outputs": legacy_observer,
                        "neural_decoder_outputs": legacy_decoder,
                        "neural_admitted_contributions": legacy_admitted,
                    }, now_ms)
            if m8_extended_telemetry:
                contact_flags, foot_xyz = sample_contacts(physics, contact_identity)
                if not np.all(np.isfinite(foot_xyz)):
                    raise RuntimeError("authoritative Tarsus5 body identity unavailable")
                m8_contacts.append(contact_flags); m8_feet.append(foot_xyz)
            if m9b_extended_telemetry:
                quat = np.asarray(physics.data.qpos[3:7], dtype=float)
                norm = float(np.linalg.norm(quat))
                if not norm: raise RuntimeError("zero root quaternion")
                w, x, y, z = quat / norm
                up = np.asarray((2*(x*z+w*y), 2*(y*z-w*x), 1-2*(x*x+y*y)))
                m9b_body_up.append(up)
                # Descriptive machine-readable state; no biological label.
                m9b_fall_rollover.append((up[2] <= 0.0, up[2] < -0.5))
            if m10b_extended_telemetry and (final_step is None or step < final_step):
                m10b_physical_motor.append([float(neural_vector[channels[n]["index"]])
                                            if step and step % stride == 0 else
                                            float(commands[channels[n]["index"]] - baseline_commands[channels[n]["index"]])
                                            for n in admitted_names])
            if detailed_motor_telemetry:
                detailed_physical_vectors.append(list(neural_vector))
            telemetry_started = time.perf_counter(); arrays = (physics.data.qpos, physics.data.qvel, physics.data.ctrl)
            finite = all(np.all(np.isfinite(a)) for a in arrays); instability |= not finite
            if compact_telemetry:
                telemetry.record("physics", {"physics_time_ms": now_ms,
                    "physics_qpos": physics.data.qpos, "physics_qvel": physics.data.qvel,
                    "physics_joint_position": measured, "physics_action": commands,
                    "physics_ctrl": physics.data.ctrl, "physics_body_position": physics.data.qpos[:3],
                    "physics_body_orientation": physics.data.qpos[3:7],
                    "physics_contact_forces": _forces(obs), "physics_finite": finite}, now_ms)
            elif not pause_at_states:
                trajectory.append({"time_ms": now_ms, "qpos": np.asarray(physics.data.qpos).tolist(),
                "qvel": np.asarray(physics.data.qvel).tolist(), "action": np.asarray(commands).tolist(),
                "ctrl": np.asarray(physics.data.ctrl).tolist(), "body_position": np.asarray(physics.data.qpos[:3]).tolist(),
                "body_orientation": np.asarray(physics.data.qpos[3:7]).tolist(), "sensory": sensory_values if step and step % stride == 0 else {},
                "delivered_sensory_drive": delivered, "malecns_state_digest": _digest(brain),
                "aggregate_cns_spike_count": aggregate_spikes, "finite": finite})
            phase["telemetry_hash"] += time.perf_counter() - telemetry_started
            # Persistent sessions pause on an observational view. Legacy finite
            # runs set pause_at_states=False, so they execute the parent path
            # without snapshot copies, hashing, or generator suspension here.
            if pause_at_states:
                yield {"time_ms": now_ms, "qpos": physics.data.qpos,
                    "qvel": physics.data.qvel, "joint_positions": measured,
                    "commands": commands, "brain": brain,
                    "sensory": sensory_values if step and step % stride == 0 else {},
                    "sensory_candidates": tuple(sorted(candidates)) if step and step % stride == 0 else (),
                    "delivered_sensory_drive": delivered,
                    "decoder_outputs": raw_values if step and step % stride == 0 else {},
                    "admitted_motor_contributions": contributions,
                    "finite": bool(finite), "physics_transition": step,
                    "neural_transition_count": step // stride,
                    "neural_update": bool(step and step % stride == 0),
                    "adhesion": (0.,) * 6}
            # Phase-1 finite stop predicate: if not finite or step == final_step
            if not finite or (final_step is not None and step == final_step): break
            if external_force_by_transition is not None:
                force = np.asarray(external_force_by_transition(condition, step), dtype=float)
                if force.shape != (3,) or not np.all(np.isfinite(force)):
                    raise RuntimeError("invalid M9B external force")
                physics.data.xfrc_applied[:] = 0.0
                physics.data.xfrc_applied[thorax_ids[0], :3] = force
                physics.data.xfrc_applied[thorax_ids[0], 3:] = 0.0
                m9b_force.append(force.copy())
            sim_started = time.perf_counter(); obs = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})[0]
            phase["mujoco_stepping"] += time.perf_counter() - sim_started
            if final_step is not None and step and step % max(1, final_step // 10) == 0:
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
        if m8_extended_telemetry:
            raw_arrays["physics_tarsal_contact"] = np.asarray(m8_contacts, dtype=np.bool_)
            raw_arrays["physics_tarsus5_world_position"] = np.asarray(m8_feet, dtype=np.float64)
        if m9b_extended_telemetry:
            # Force is transition telemetry (N), while physical state telemetry
            # is N+1. Pre/post-zero vectors are neural-cadence decoder samples.
            raw_arrays["physics_external_force"] = np.asarray(m9b_force, dtype=np.float64)
            raw_arrays["neural_motor_pre_zero"] = np.asarray(m9b_pre_zero, dtype=np.float64)
            raw_arrays["neural_motor_post_zero"] = np.asarray(m9b_post_zero, dtype=np.float64)
            raw_arrays["physics_body_up_vector"] = np.asarray(m9b_body_up, dtype=np.float64)
            raw_arrays["physics_fall_rollover"] = np.asarray(m9b_fall_rollover, dtype=np.bool_)
        if m10b_extended_telemetry:
            raw_arrays["neural_sensory_physical_inputs"] = np.asarray(m10b_physical_inputs, dtype=np.float64)
            raw_arrays["neural_delivered_sensory_state"] = np.asarray(m10b_delivered, dtype=np.int64)
            raw_arrays["neural_mapped_motor_population_state"] = np.asarray(m10b_mapped_motor, dtype=np.float64)
            raw_arrays["physics_neural_motor_contribution"] = np.asarray(m10b_physical_motor, dtype=np.float64)
        if detailed_motor_telemetry:
            raw_arrays["detailed_motor_telemetry"] = detailed_motor
            raw_arrays["physics_neural_contribution_vector"] = np.asarray(
                detailed_physical_vectors, dtype=np.float64)
        return {"pre_intervention_equivalence": True, "pre_intervention_state": pre_intervention_state,
            "initial_physical_state_audit": initial_audit,
            "decoder_configuration": [{"name": name, "action_index": x["index"],
                "qpos_index": int(x["metadata"].qpos_index), "qvel_index": int(x["metadata"].qvel_index),
                "coordinate_sign": x["sign"], "joint_min_rad": float(x["metadata"].joint_min),
                "joint_max_rad": float(x["metadata"].joint_max), "safe_contribution_bound_rad": float(x["bound"]),
                "observer_tau_ms": OBSERVER_TAU_MS, "slew_limit_rad_s": SLEW_RAD_S}
                for name, x in channels.items()],
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


def create_scientific_session(**kwargs: Any):
    """Create an uninitialized persistent session for the frozen kernel."""
    from .scientific_session import ScientificSession

    return ScientificSession(lambda: _scientific_transition_kernel(
        **kwargs, pause_at_states=True))


def run_condition(**kwargs: Any) -> Mapping[str, Any]:
    """Finite M8 adapter over the shared scientific kernel.

    The no-pause policy retains the parent's return, telemetry, non-finite, and
    initialize-only semantics without constructing Live Fly snapshots.
    """
    kernel = _scientific_transition_kernel(**kwargs, pause_at_states=False)
    try:
        try:
            next(kernel)
        except StopIteration as stopped:
            return stopped.value
        raise RuntimeError("legacy finite kernel unexpectedly paused")
    finally:
        kernel.close()
