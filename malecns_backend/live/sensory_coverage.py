"""Offline modeled-angle coverage and optional open-loop neural recruitment assay.

No physics, pose server, motor commands, or live-session modifications.
"""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path

import numpy as np

from malecns_backend.embodiment.sensory import LegSensoryFrame, SensoryEncoder
from malecns_backend.embodiment.six_tibia import load_six_tibia_interfaces


def angle_at(condition, fraction, bounds):
    lo, hi = bounds
    if condition == "midpoint":
        return (lo + hi) / 2
    if condition == "sweep_up":
        return lo + (hi - lo) * fraction
    if condition == "sweep_down":
        return hi - (hi - lo) * fraction
    raise ValueError("unknown angle condition")


def encoder_coverage(interfaces, points=101):
    if points < 2:
        raise ValueError("coverage requires at least two angle samples")
    result = {}
    for leg, interface in interfaces.items():
        encoder = SensoryEncoder(interface)
        angles = np.linspace(*interface.joint_range_rad, points)
        rates = np.array([encoder.encode(LegSensoryFrame(0., float(q))).rates_hz for q in angles])
        n = len(interface.sensor.body_ids)
        if n == 0 or len(set(interface.sensor.dense_indices)) != n:
            raise ValueError("sensory population must have unique, nonempty indices")
        result[leg] = {
            "joint_range_rad": list(interface.joint_range_rad),
            "sampled_angles_rad": angles.tolist(),
            "minimum_active_neurons": int(np.count_nonzero(rates, axis=1).min()),
            "neurons": [{"body_id": int(body), "dense_index": int(index),
                         "modeled_preferred_angle_rad": float(encoder.angle_min_rad +
                             (k + .5) / n * (encoder.angle_max_rad - encoder.angle_min_rad)),
                         "peak_rate_hz": float(rates[:, k].max()),
                         "active_angle_samples": int(np.count_nonzero(rates[:, k])),
                         "midpoint_rate_hz": float(encoder.encode(LegSensoryFrame(
                             0., angle_at("midpoint", 0., interface.joint_range_rad))).rates_hz[k])}
                        for k, (body, index) in enumerate(zip(interface.sensor.body_ids,
                                                              interface.sensor.dense_indices))]}
    return result


def run_condition(brain, interfaces, targets, condition, duration_s, seed=1, *,
                  pathway_definitions=None):
    """Use the same two-stage event pathway as the live scientific kernel."""
    from malecns_backend.embodiment.proprioceptive_activation import proprio_rngs, sample_candidates
    if not math.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("duration must be finite and positive")
    steps = int(round(duration_s * 1000 / brain.config.dt))
    if steps < 2:
        raise ValueError("duration must span at least two neural steps")
    angle_at(condition, 0., (0., 1.))  # Validate before mutating the brain.
    brain.reset(seed)
    brain.clear_external_drive()
    probe = None
    channels = {}
    if pathway_definitions is not None:
        from malecns_backend.embodiment.motor import MotorActivityObserver
        from .upstream_diagnostics import CandidateUpstreamProbe
        for name, definition in pathway_definitions.items():
            populations = {population: tuple(brain.data.body_id_to_index[body] for body in bodies)
                           for direction in ("positive_populations", "negative_populations")
                           for population, bodies in definition[direction].items()}
            resolved = tuple(index for indices in populations.values() for index in indices)
            if resolved != tuple(targets[name]):
                raise ValueError("pathway targets must match reported motor targets")
            observer = MotorActivityObserver(populations)
            observer.reset(brain.spike_counts)
            channels[name] = {"populations": populations, "observer": observer}
        probe = CandidateUpstreamProbe(brain, channels, pathway_definitions,
                    sensory_sources={leg: interface.sensor.dense_indices
                                     for leg, interface in interfaces.items()})
    pathway_state = None
    rngs = proprio_rngs(seed)
    encoders = {leg: SensoryEncoder(interface) for leg, interface in interfaces.items()}
    delivered = np.zeros(brain.n, dtype=np.int64)
    for step in range(steps):
        candidates = set()
        encoded_rates = {} if probe is not None else None
        brain.clear_external_drive()
        for leg, encoder in encoders.items():
            q = angle_at(condition, step / (steps - 1), interfaces[leg].joint_range_rad)
            encoded = encoder.encode(LegSensoryFrame(step * brain.config.dt / 1000, q))
            if encoded_rates is not None:
                encoded_rates.update(zip(map(int, encoded.indices), map(float, encoded.rates_hz)))
            local = sample_candidates(encoded.rates_hz, rngs[leg], dt_ms=brain.config.dt)
            candidates.update(int(encoded.indices[i]) for i in local)
        if candidates:
            brain.set_external_drive(tuple(sorted(candidates)), 1000. / brain.config.dt)
        brain.step()
        np.add.at(delivered, brain._last_external_delivered, 1)
        if probe is not None:
            for channel in channels.values():
                channel["observer"].update(brain.spike_counts, brain.config.dt)
            pathway_state = probe.sample(brain, encoded_sensory=encoded_rates)
    def row(index):
        return {"body_id": int(brain.data.body_ids[index]), "dense_index": int(index),
                "spikes": int(brain.spike_counts[index])}
    result = {"condition": condition, "neural_steps": steps,
            "actual_duration_s": steps * brain.config.dt / 1000,
            "sensory": {leg: [dict(row(int(i)), delivered_events=int(delivered[i]))
                               for i in interface.sensor.dense_indices]
                        for leg, interface in interfaces.items()},
            "candidate_motors": {name: [row(i) for i in indices] for name, indices in targets.items()}}

    if pathway_state is not None:
        result["pathway_diagnostics"] = pathway_state
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--neural", action="store_true", help="also load the full CNS and run three matched conditions")
    parser.add_argument("--pathway-diagnostics", action="store_true",
                        help="requires --neural; sample existing candidate/intermediate probe each step")
    parser.add_argument("--duration-s", type=float, default=10., help="simulated seconds PER neural condition")
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration_s) or args.duration_s <= 0:
        parser.error("--duration-s must be finite and positive")
    if args.pathway_diagnostics and not args.neural:
        parser.error("--pathway-diagnostics requires --neural")
    interfaces = load_six_tibia_interfaces()
    report = {"schema": "proprioceptive-coverage-v1", "provenance": "MODELED_ANGLE_INTERVENTION",
              "physics_running": False, "seed": 1,
              "interpretation": "Prescribed synchronous angles; modeled list-order tuning; no gait or causal proof. Midpoint is not the measured live resting posture.",
              "encoder": {key: getattr(SensoryEncoder, key) for key in (
                  "angle_min_rad", "angle_max_rad", "width_normalized", "maximum_rate_hz", "cutoff_hz")},
              "coverage": encoder_coverage(interfaces), "neural_conditions": []}
    if args.neural:
        from malecns_backend.loader import load_malecns
        from malecns_backend.neural import MaleCNSBrain
        from malecns_backend.embodiment.live_v3_motor_interface import CANDIDATE_MOTOR_CHANNELS
        print("Loading CNS; three conditions will reset to seed 1.", flush=True)
        brain = MaleCNSBrain(load_malecns())
        for interface in interfaces.values():
            for body, index in zip(interface.sensor.body_ids, interface.sensor.dense_indices):
                if int(brain.data.body_ids[index]) != int(body):
                    raise ValueError("sensory body ID / dense index mismatch")
        targets = {name: tuple(brain.data.body_id_to_index[body]
                              for direction in ("positive_populations", "negative_populations")
                              for bodies in definition[direction].values() for body in bodies)
                   for name, definition in CANDIDATE_MOTOR_CHANNELS.items()}
        report["neural_config"] = asdict(brain.config)
        for condition in ("midpoint", "sweep_up", "sweep_down"):
            print(f"Running {condition} ({args.duration_s:g} simulated seconds)", flush=True)
            report["neural_conditions"].append(run_condition(
                brain, interfaces, targets, condition, args.duration_s,
                pathway_definitions=CANDIDATE_MOTOR_CHANNELS if args.pathway_diagnostics else None))
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Saved {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
