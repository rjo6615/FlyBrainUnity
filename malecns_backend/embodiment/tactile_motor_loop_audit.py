"""Command-line runner for the M5D-4 closed-loop motor-causality audit."""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import traceback

import numpy as np

from malecns_backend import MaleCNSBrain, load_malecns
from .six_tibia import IsolatedTibiaDecoder, LEG_ORDER
from .tactile_contact import TactileContactConfig, TactileContactEncoder
from .tactile_motor_loop import (
    ACTUATOR_INDICES, CONDITIONS, CONTACT_FORCE_ROW, DEFAULT_DURATION_MS,
    DEFAULT_SEED, NEURAL_DT_MS, analyze, atomic_write_report, base_report,
    classify, LOCKED_M5D3, LOCKED_PRIOR, validated_interfaces,
    verify_locked_hashes,
)
from .tactile_propagation import rng_digest
from . import tactile_targeted_contact_calibration as contact

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "interface_output" / "tactile_motor_loop.json"


def _make_live(flygym, interfaces):
    """Construct the locked contact arena without moving the fly."""
    placements = [f"{leg}{segment}" for leg in contact.LEGS for segment in
                  ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")]
    fly = flygym.Fly(enable_adhesion=False, control="position",
                    contact_sensor_placements=placements)
    simulation = getattr(flygym, "SingleFlySimulation", None)
    if simulation is None:
        simulation = importlib.import_module("flygym.simulation").SingleFlySimulation
    sim = simulation(fly=fly, arena=contact._make_arena(flygym), cameras=[],
                     timestep=contact.DEFAULT_TIMESTEP_S)
    reset = sim.reset(); obs = reset[0] if isinstance(reset, tuple) else reset
    physics = contact._physics(sim)
    tarsus_id, _ = contact.resolve_exact_geom(physics.model, "LMTarsus5")
    surface_id, _ = contact.resolve_exact_geom(physics.model, contact.SURFACE_NAME)
    qpos = np.asarray(physics.data.qpos).copy()
    tarsus_pos = np.asarray(physics.data.geom_xpos[tarsus_id]).copy()
    radius = float(np.asarray(physics.model.geom_rbound)[tarsus_id])
    np.asarray(physics.model.geom_pos)[surface_id] = contact.surface_position(tarsus_pos, radius, contact=True)
    contact._forward(physics)
    if not np.array_equal(qpos, np.asarray(physics.data.qpos)):
        raise RuntimeError("calibration surface placement changed initial fly qpos")
    refresh = getattr(sim, "get_observation", None)
    if refresh is not None: obs = refresh()
    return sim, physics, obs, tarsus_id, surface_id


def _joint_positions(obs):
    joints = np.asarray(obs["joints"], dtype=np.float64)
    return (joints[0] if joints.ndim == 2 else joints).copy()


def _forces(obs):
    return np.asarray(obs["contact_forces"], dtype=np.float64)


def _state_tuple(brain):
    # Bytes give strict equality while avoiding JSON's NaN and giant numeric lists.
    import hashlib
    digest = hashlib.sha256()
    for value in (brain.v, brain.g_exc, brain.g_inh, brain.spike_counts):
        digest.update(np.asarray(value).tobytes())
    return digest.hexdigest()


def _run_condition(flygym, data, interfaces, duration_ms, seed, apply_motor):
    sim, physics, obs, tarsus_id, surface_id = _make_live(flygym, interfaces)
    brain = MaleCNSBrain(data); brain.reset(seed)
    encoder = TactileContactEncoder(config=TactileContactConfig(seed=seed))
    decoders = {leg: IsolatedTibiaDecoder(interfaces[leg]) for leg in LEG_ORDER}
    for decoder in decoders.values(): decoder.reset(brain.spike_counts)
    pending = set(); rows = []; candidate_log = []; delivered_log = []
    dt_ms = contact.DEFAULT_TIMESTEP_S * 1000
    stride = int(round(NEURAL_DT_MS / dt_ms))
    commands = _joint_positions(obs); last_valid = None
    try:
        for step in range(int(round(duration_ms / dt_ms)) + 1):
            time_ms = float(physics.data.time * 1000)
            forces = _forces(obs)
            frame = encoder.encode(forces, time_ms, dt_ms)["LM"]
            generated = tuple(map(int, frame.generated_dense_indices))
            candidate_log.extend((time_ms, i) for i in generated); pending.update(generated)
            delivered = (); fired = (); motor_spikes = {leg: 0 for leg in LEG_ORDER}
            decoded = {leg: 0.0 for leg in LEG_ORDER}; applied = dict(decoded)
            decoder_state = {}
            if step and step % stride == 0:
                brain.clear_external_drive()
                candidates = tuple(sorted(pending)); pending.clear()
                if candidates: brain.set_external_drive(candidates, 1000.0 / brain.config.dt)
                brain.external_drive_withheld_indices = np.empty(0, np.intp)
                before_counts = brain.spike_counts.copy(); fired = tuple(map(int, brain.step()))
                delivered = tuple(map(int, brain._last_external_delivered))
                delivered_log.extend((brain.time_ms, i) for i in delivered)
                measured = _joint_positions(obs)
                for leg in LEG_ORDER:
                    observed, command = decoders[leg].update(
                        brain.spike_counts, NEURAL_DT_MS, measured[ACTUATOR_INDICES[leg]],
                        NEURAL_DT_MS / 1000, apply_neural_offset=apply_motor)
                    motor_spikes[leg] = int(sum(observed["increments"].values()))
                    decoded[leg] = float(command.magnitude_clamped_output_rad)
                    applied[leg] = decoded[leg] if apply_motor else 0.0
                    # Disabled computes the same candidate, but only the enabled
                    # target is allowed across the physical actuation boundary.
                    commands[ACTUATOR_INDICES[leg]] = (command.target_position_rad
                        if apply_motor else measured[ACTUATOR_INDICES[leg]])
                    decoder_state[leg] = {"filtered_hz": observed["filtered_hz"],
                                          "last_target_rad": float(command.target_position_rad)}
            pairs = contact._pairs(physics)
            metadata = contact.contact_metadata(pairs, tarsus_id, surface_id)
            positions = _joint_positions(obs)
            row = {"time_ms": time_ms,
              "tibia_qpos": {leg: float(positions[index]) for leg, index in ACTUATOR_INDICES.items()},
              "full_qpos": tuple(float(x) for x in np.asarray(physics.data.qpos)),
              "force_magnitude": float(np.linalg.norm(forces[CONTACT_FORCE_ROW])),
              "contact_metadata": metadata, "modeled_rate_hz": frame.modeled_rate_hz,
              "candidate_events": generated, "delivered_events": delivered,
              "cns_spikes": fired, "neural_state": _state_tuple(brain),
              "motor_spikes": motor_spikes, "decoder_state": decoder_state,
              "decoded_output": decoded, "applied_output": applied,
              "rng_digest": rng_digest(encoder.rng["LM"])}
            rows.append(row); last_valid = row
            if step == int(round(duration_ms / dt_ms)): break
            result = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})
            obs = result[0]
            for name, value in (("qpos", physics.data.qpos), ("qvel", physics.data.qvel),
                                ("qacc", physics.data.qacc)):
                if not np.all(np.isfinite(value)):
                    raise FloatingPointError(f"non-finite MuJoCo {name}")
        return {"rows": rows, "candidates": candidate_log, "delivered": delivered_log,
                "rng_final": rng_digest(encoder.rng["LM"]), "physics_failure": None}
    except Exception as error:
        failure = {"condition": CONDITIONS[0] if apply_motor else CONDITIONS[1],
          "last_valid_time_ms": None if last_valid is None else last_valid["time_ms"],
          "failing_time_ms": float(physics.data.time * 1000), "error_type": type(error).__name__,
          "message": str(error), "qpos": np.asarray(physics.data.qpos).tolist(),
          "qvel": np.asarray(physics.data.qvel).tolist(), "qacc": np.asarray(physics.data.qacc).tolist()}
        return {"rows": rows, "candidates": candidate_log, "delivered": delivered_log,
                "rng_final": rng_digest(encoder.rng["LM"]), "physics_failure": failure}
    finally:
        if getattr(sim, "close", None): sim.close()


def run_live(duration_ms=DEFAULT_DURATION_MS, seed=DEFAULT_SEED):
    if duration_ms != DEFAULT_DURATION_MS:
        raise ValueError("canonical M5D-4 duration is fixed at 100 ms")
    flygym = importlib.import_module("flygym")
    interfaces = validated_interfaces(); data = load_malecns()
    enabled = _run_condition(flygym, data, interfaces, duration_ms, seed, True)
    disabled = _run_condition(flygym, data, interfaces, duration_ms, seed, False)
    report = base_report(duration_ms, seed)
    failures = [x["physics_failure"] for x in (enabled, disabled) if x["physics_failure"]]
    report["physics_stability"] = {"stable": not failures, "failure": failures or None,
                                    "retry_or_retuning_permitted": False}
    if failures:
        report.update(run_status="FAILED", reason="MuJoCo physics instability",
                      causal_classification="PHYSICS_UNSTABLE")
        return report
    result = analyze(enabled["rows"], disabled["rows"])
    rows_a, rows_b = enabled["rows"], disabled["rows"]
    verified = all(any(r["contact_metadata"]["selected_pair_present"] for r in rows)
                   for rows in (rows_a, rows_b))
    delivered = bool(enabled["delivered"] and disabled["delivered"])
    physical = result["timing_milestones_ms"]["first_physical_qpos_divergence"] is not None
    contact_feedback = any(result[x]["first_divergence_ms"] is not None for x in
                           ("contact_force_feedback",)) or result["timing_milestones_ms"]["first_exact_contact_state_divergence"] is not None
    tactile_fb = result["tactile_feedback_divergence"]["first_divergence_ms"] is not None
    cns_fb = result["downstream_cns_feedback_divergence"]["first_divergence_ms"] is not None
    motor_fb = result["subsequent_mapped_motor_divergence"]["first_divergence_ms"] is not None
    downstream = any(len(r["cns_spikes"]) > len(r["delivered_events"]) for r in rows_a)
    motor = result["timing_milestones_ms"]["first_mapped_tibia_motor_spike"] is not None
    decoded = result["timing_milestones_ms"]["first_nonzero_decoded_tibia_output"] is not None
    classification = classify(contact=verified, tactile_delivered=delivered, downstream=downstream,
      motor_spike=motor, decoded=decoded, physical=physical, contact_feedback=contact_feedback,
      tactile_and_cns_feedback=tactile_fb and cns_fb, motor_feedback=motor_fb,
      pre_motor_equivalent=result["pre_motor_equivalence"]["passed"])
    report.update(result); report.update(run_status="COMPLETE", reason=None,
                                         causal_classification=classification)
    report["physical_contact_verification"]["verified"] = verified
    milestones = report["timing_milestones_ms"]
    analyzed = result["timing_milestones_ms"]
    milestones.update(analyzed)
    milestones["first_verified_contact"] = next((r["time_ms"] for r in rows_a
      if r["contact_metadata"]["selected_pair_present"]), None)
    milestones["first_nonzero_force"] = next((r["time_ms"] for r in rows_a
      if r["force_magnitude"] > contact.ENGINEERING_THRESHOLD), None)
    milestones["first_modeled_tactile_rate"] = next((r["time_ms"] for r in rows_a
      if r["modeled_rate_hz"] > 0), None)
    milestones["first_candidate_tactile_spike"] = (enabled["candidates"][0][0]
      if enabled["candidates"] else None)
    milestones["first_delivered_tactile_spike"] = (enabled["delivered"][0][0]
      if enabled["delivered"] else None)
    sensory_time = result["timing_milestones_ms"]["first_sensory_feedback_divergence"]
    paired_rows = [(a, b) for a, b in zip(rows_a, rows_b)
                   if sensory_time is None or a["time_ms"] < sensory_time]
    pre_feedback_rng = all(a["rng_digest"] == b["rng_digest"] for a, b in paired_rows)
    candidates_equal = all(a["candidate_events"] == b["candidate_events"] for a, b in paired_rows)
    delivered_equal = all(a["delivered_events"] == b["delivered_events"] for a, b in paired_rows)
    report["rng_parity"] = {"passed_before_feedback": pre_feedback_rng,
      "candidate_events_identical_before_feedback": candidates_equal,
      "delivered_events_identical_before_feedback": delivered_equal,
      "final_state_identical": enabled["rng_final"] == disabled["rng_final"],
      "enabled_final_digest": enabled["rng_final"], "disabled_final_digest": disabled["rng_final"]}
    def summary(run):
        return {"candidate_tactile_spikes": len(run["candidates"]),
                "delivered_tactile_spikes": len(run["delivered"]),
                "mapped_tibia_motor_spikes": sum(sum(r["motor_spikes"].values()) for r in run["rows"])}
    report["enabled_condition_summary"] = summary(enabled)
    report["disabled_condition_summary"] = summary(disabled)
    report["mapped_tibia_motor_activity"] = {c: summary(x)["mapped_tibia_motor_spikes"]
      for c, x in zip(CONDITIONS, (enabled, disabled))}
    report["decoded_outputs"] = {"computed_in_both_conditions": True}
    report["applied_outputs"] = {"enabled": True, "disabled": False,
                                  "disabled_withholds_application_only": True}
    post_run = verify_locked_hashes()
    report["locked_provenance"]["post_run_m5d3_unchanged"] = {
        name: post_run[name] for name in LOCKED_M5D3}
    report["locked_provenance"]["post_run_prior_unchanged"] = {
        name: post_run[name] for name in LOCKED_PRIOR}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration-ms", type=int, default=DEFAULT_DURATION_MS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = base_report(args.duration_ms, args.seed)
    if args.live:
        try: report = run_live(args.duration_ms, args.seed)
        except (ImportError, ModuleNotFoundError) as error:
            report.update(run_status="UNAVAILABLE", reason=f"{type(error).__name__}: {error}")
        except Exception as error:
            report.update(run_status="FAILED", reason=f"{type(error).__name__}: {error}")
            report["physics_stability"]["failure"] = {"traceback": traceback.format_exc()}
    atomic_write_report(args.json, report)
    print(f"M5D-4 {report['run_status']}: {report['causal_classification']}")
    print(f"wrote {args.json}")
    return 0 if report["run_status"] in ("COMPLETE", "NOT_RUN", "UNAVAILABLE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
