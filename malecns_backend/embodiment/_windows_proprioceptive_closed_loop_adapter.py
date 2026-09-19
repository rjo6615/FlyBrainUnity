"""Live Windows adapter for the M5D-5B paired causal experiment.

This is deliberately an integration adapter, not a second simulator.  It
composes the live FlyGym construction used by M5D-4C, the M5D-5A sensory
implementation, and the M5D-4C command pipeline.  The returned values are raw
condition traces; all scientific reduction remains in
``proprioceptive_closed_loop.analyze``.
"""
from __future__ import annotations

import importlib

import numpy as np

from malecns_backend import MaleCNSBrain, load_malecns
from . import tactile_targeted_contact_calibration as contact
from .proprioceptive_activation import proprio_rngs, sample_candidates
from .proprioceptive_closed_loop import (
    CONDITIONS, DURATION_MS, NEURAL_DT_MS, PHYSICS_DT_MS, SEED, analyze,
)
from .sensory import LegSensoryFrame, SensoryEncoder
from .six_tibia import IsolatedTibiaDecoder, LEG_ORDER
from .tactile_contact import TactileContactConfig, TactileContactEncoder
from .tactile_motor_loop import ACTUATOR_INDICES, validated_interfaces
from .tactile_motor_loop_audit import _forces, _joint_positions, _make_live, _state_tuple
from .tactile_motor_matched_control import MatchedControlPipeline, decode_raw
from .tactile_propagation import rng_digest


class PhysicsFailure(RuntimeError):
    """The real MuJoCo state became invalid during a condition."""


def _run_condition(flygym, data, interfaces, condition: str):
    """Run one real condition through a single common implementation path."""
    enabled = condition == CONDITIONS[0]
    if condition not in CONDITIONS:
        raise ValueError(f"unknown M5D-5B condition {condition!r}")

    sim, physics, obs, tarsus_id, surface_id = _make_live(flygym, interfaces)
    brain = MaleCNSBrain(data)
    brain.reset(SEED)
    if float(brain.config.dt) != NEURAL_DT_MS:
        raise RuntimeError(f"MaleCNS neural dt changed: {brain.config.dt!r} ms")
    tactile_encoder = TactileContactEncoder(config=TactileContactConfig(seed=SEED))
    sensory_encoders = {leg: SensoryEncoder(interfaces[leg]) for leg in LEG_ORDER}
    sensory_rngs = proprio_rngs(SEED)
    wrappers = {leg: IsolatedTibiaDecoder(interfaces[leg]) for leg in LEG_ORDER}
    for wrapper in wrappers.values():
        wrapper.reset(brain.spike_counts)
    pipelines = {leg: MatchedControlPipeline(enabled, wrappers[leg].decoder.safety)
                 for leg in LEG_ORDER}

    commands = _joint_positions(obs)
    pending_tactile: set[int] = set()
    rows = []
    stride = int(round(NEURAL_DT_MS / PHYSICS_DT_MS))
    final_step = int(round(DURATION_MS / PHYSICS_DT_MS))
    draw_counts = {leg: 0 for leg in LEG_ORDER}
    direct_proprio = {int(i) for leg in LEG_ORDER
                      for i in interfaces[leg].sensor.dense_indices}
    direct_tactile = {int(i) for i in
                      tactile_encoder.populations["LM"].dense_indices}
    try:
        for step in range(final_step + 1):
            time_ms = float(physics.data.time * 1000.0)
            measured = _joint_positions(obs)
            forces = _forces(obs)
            tactile_before = rng_digest(tactile_encoder.rng["LM"])
            tactile_frame = tactile_encoder.encode(forces, time_ms, PHYSICS_DT_MS)["LM"]
            tactile_after = rng_digest(tactile_encoder.rng["LM"])
            tactile_generated = tuple(map(int, tactile_frame.generated_dense_indices))
            pending_tactile.update(tactile_generated)

            proprio = {leg: {"angle_rad": float(measured[ACTUATOR_INDICES[leg]]),
                "rates_hz": (), "candidate": (), "delivered": (),
                "rng_before": None, "rng_after": None,
                "draw_count_before": draw_counts[leg],
                "draw_count_after": draw_counts[leg]} for leg in LEG_ORDER}
            motor_spikes = {leg: {"extensor": 0, "flexor": 0} for leg in LEG_ORDER}
            raw = {leg: 0.0 for leg in LEG_ORDER}
            admitted = {leg: 0.0 for leg in LEG_ORDER}
            observers = {}
            decoder_states = {}
            baselines = {leg: float(measured[index]) for leg, index in ACTUATOR_INDICES.items()}
            previous = {leg: pipelines[leg].previous_physical_target for leg in LEG_ORDER}
            targets = {leg: float(commands[index]) for leg, index in ACTUATOR_INDICES.items()}
            fired = ()
            delivered = set()
            tactile_candidates = ()
            neural_step = None
            neural_state = None

            if step and step % stride == 0:
                neural_step = step // stride
                brain.clear_external_drive()
                tactile_candidates = tuple(sorted(pending_tactile))
                pending_tactile.clear()
                candidates_by_leg = {}
                for leg in LEG_ORDER:
                    encoded = sensory_encoders[leg].encode(LegSensoryFrame(
                        time_ms / 1000.0, proprio[leg]["angle_rad"]))
                    before = rng_digest(sensory_rngs[leg])
                    local = sample_candidates(encoded.rates_hz, sensory_rngs[leg])
                    after = rng_digest(sensory_rngs[leg])
                    candidates = tuple(int(encoded.indices[i]) for i in local)
                    candidates_by_leg[leg] = candidates
                    draw_counts[leg] += len(encoded.rates_hz)
                    proprio[leg].update(rates_hz=tuple(map(float, encoded.rates_hz)),
                        candidate=candidates, rng_before=before, rng_after=after,
                        draw_count_after=draw_counts[leg])
                all_candidates = tuple(sorted(set(tactile_candidates).union(
                    *(set(values) for values in candidates_by_leg.values()))))
                if all_candidates:
                    brain.set_external_drive(all_candidates, 1000.0 / brain.config.dt)
                brain.external_drive_withheld_indices = np.empty(0, np.intp)
                fired = tuple(map(int, brain.step()))
                delivered = set(map(int, brain._last_external_delivered))
                for leg in LEG_ORDER:
                    proprio[leg]["delivered"] = tuple(
                        i for i in candidates_by_leg[leg] if i in delivered)

                # The observers, decoder, baseline/history, clamps, slew, and
                # action construction are identical. MatchedControlPipeline's
                # admission bit is the sole condition-dependent operation.
                for leg in LEG_ORDER:
                    wrapper = wrappers[leg]
                    observed = wrapper.observer.update(brain.spike_counts, NEURAL_DT_MS)
                    directional = wrapper.decoder.directional_rates(observed["filtered_hz"])
                    decoded = decode_raw(wrapper.decoder, directional)
                    result = pipelines[leg].update(measured[ACTUATOR_INDICES[leg]],
                        decoded["raw_neural_contribution"], NEURAL_DT_MS / 1000.0)
                    commands[ACTUATOR_INDICES[leg]] = result.actuator_command
                    raw[leg] = result.raw_neural_contribution
                    admitted[leg] = result.admitted_neural_contribution
                    baselines[leg] = result.baseline_target
                    previous[leg] = result.previous_physical_target
                    targets[leg] = result.actuator_command
                    increments = observed["increments"]
                    extensor_names = {population.name for population in
                        wrapper.decoder.pathway.motor_populations
                        if population.direction == "extensor"}
                    flexor_names = {population.name for population in
                        wrapper.decoder.pathway.motor_populations
                        if population.direction == "flexor"}
                    motor_spikes[leg] = {
                        "extensor": int(sum(increments[name] for name in extensor_names)),
                        "flexor": int(sum(increments[name] for name in flexor_names))}
                    observers[leg] = {"neurons": observed["neurons"],
                        "filtered_hz": observed["filtered_hz"]}
                    decoder_states[leg] = decoded
                # Preserve per-neuron membrane state only at neural cadence.
                # The reducer needs this to exclude the 392 directly driven
                # neurons rather than confusing direct drive with feedback.
                neural_state = np.asarray(brain.v).copy()

            metadata = contact.contact_metadata(
                contact._pairs(physics), tarsus_id, surface_id)
            state_arrays = (physics.data.qpos, physics.data.qvel, physics.data.qacc,
                            physics.data.ctrl, forces)
            if not all(np.all(np.isfinite(value)) for value in state_arrays):
                raise PhysicsFailure(f"non-finite MuJoCo state at {time_ms} ms")
            rows.append({"condition": condition, "time_ms": time_ms,
                "physical_step": step, "neural_step": neural_step,
                "physical_tibia_angles": {leg: float(measured[i])
                    for leg, i in ACTUATOR_INDICES.items()}, "proprio": proprio,
                "tactile": {"source_forces": forces.tolist(),
                    "modeled_rate_hz": tactile_frame.modeled_rate_hz,
                    "generated": tactile_generated,
                    "pending_at_neural_step": tactile_candidates,
                    "delivered": tuple(i for i in tactile_candidates if i in delivered),
                    "rng_before": tactile_before, "rng_after": tactile_after},
                "sensory_delivered": tuple(sorted(delivered)),
                "rng_draw_counts": dict(draw_counts), "cns_state_digest": _state_tuple(brain),
                "neural_state": neural_state, "cns_spikes": fired,
                "direct_proprio_indices": direct_proprio,
                "direct_tactile_indices": direct_tactile,
                "motor_spikes": motor_spikes, "observer_states": observers,
                "decoder_states": decoder_states, "raw_neural_contributions": raw,
                "admitted_neural_contributions": admitted,
                "baseline_targets": baselines, "previous_physical_targets": previous,
                "final_tibia_targets": targets, "action_joints": commands.copy(),
                "adhesion": (0.0,) * 6, "ctrl": np.asarray(physics.data.ctrl).copy(),
                "qpos": np.asarray(physics.data.qpos).copy(),
                "qvel": np.asarray(physics.data.qvel).copy(),
                "qacc": np.asarray(physics.data.qacc).copy(),
                "contact_forces": forces.copy(), "contact_set": metadata})
            if step == final_step:
                break
            obs = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})[0]
    finally:
        if getattr(sim, "close", None):
            sim.close()
    return rows


def run_canonical_pair(*, provenance):
    """Construct both real conditions and pass their raw traces to the reducer."""
    if float(contact.DEFAULT_TIMESTEP_S * 1000.0) != PHYSICS_DT_MS:
        raise RuntimeError(
            f"FlyGym physics dt changed: {contact.DEFAULT_TIMESTEP_S!r} s")
    flygym = importlib.import_module("flygym")
    interfaces = validated_interfaces()
    data = load_malecns()
    enabled = _run_condition(flygym, data, interfaces, CONDITIONS[0])
    disabled = _run_condition(flygym, data, interfaces, CONDITIONS[1])
    return analyze(enabled, disabled, provenance=provenance)
