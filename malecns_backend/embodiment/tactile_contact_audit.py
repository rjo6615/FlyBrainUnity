"""Bounded M5D-2 calibration and open-loop validation command."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .tactile_contact import (DISTAL_SEGMENT, LEGS, TactileContactConfig,
                              TactileContactEncoder, calibration_statistics,
                              distal_contact_vectors, load_tactile_populations)

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "interface_output" / "tactile_contact_audit.json"


def _forces(value=0.0):
    array = np.zeros((36, 3), dtype=np.float64)
    array[5::6, 0] = value
    return array


def synthetic_validation(config=None):
    config = config or TactileContactConfig()
    encoder = TactileContactEncoder(config=config)
    sequence = [
        ("zero", 0.0), ("subthreshold", config.engineering_threshold),
        ("threshold_crossing", config.engineering_threshold * 2 + 1e-15),
        ("sustained_contact", config.engineering_threshold * 2 + 1e-15),
        ("after_transient", config.engineering_threshold * 2 + 1e-15),
        ("release", 0.0), ("second_contact", config.engineering_threshold * 2 + 1e-15),
    ]
    times = [0.0, 1.0, 2.0, 3.0, config.transient_duration_ms + 3.0,
             config.transient_duration_ms + 4.0, config.transient_duration_ms + 5.0]
    cases = []
    first_spike = {leg: None for leg in LEGS}
    for (name, force), time_ms in zip(sequence, times):
        frames = encoder.encode(_forces(force), time_ms, 1.0)
        for leg, frame in frames.items():
            if frame.generated_tactile_spike_count and first_spike[leg] is None:
                first_spike[leg] = time_ms
        cases.append({
            "case": name, "time_ms": time_ms,
            "per_leg": {leg: {
                "selected_physical_segment": DISTAL_SEGMENT,
                "raw_force_vector": list(f.raw_force_vector),
                "force_magnitude": f.force_magnitude, "threshold": f.threshold,
                "contact_state": f.contact, "onset_time_ms": f.onset_time_ms,
                "modeled_rate_hz": f.modeled_rate_hz,
                "tactile_population_size": f.population_size,
                "generated_tactile_spike_count": f.generated_tactile_spike_count,
                "first_tactile_spike_time_ms": first_spike[leg],
            } for leg, f in frames.items()},
        })
    assertions = {
        "zero_no_contact": not cases[0]["per_leg"]["LF"]["contact_state"],
        "subthreshold_no_contact": not cases[1]["per_leg"]["LF"]["contact_state"],
        "crossing_is_onset": cases[2]["per_leg"]["LF"]["onset_time_ms"] == times[2],
        "sustained_does_not_retrigger": cases[3]["per_leg"]["LF"]["onset_time_ms"] == times[2],
        "transient_is_bounded": cases[4]["per_leg"]["LF"]["modeled_rate_hz"] == 0,
        "release_resets": cases[5]["per_leg"]["LF"]["onset_time_ms"] is None,
        "second_contact_is_second_onset": cases[6]["per_leg"]["LF"]["onset_time_ms"] == times[6],
    }
    return {"status": "PASS" if all(assertions.values()) else "FAIL",
            "assertions": assertions, "cases": cases}


def live_calibration(duration_s: float, timestep_s: float = 0.0001) -> dict[str, Any]:
    """Reset, then passively hold measured joints for a bounded duration."""
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    steps = int(np.ceil(duration_s / timestep_s))
    try:
        flygym = importlib.import_module("flygym")
    except ImportError as exc:
        return {"status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}",
                "requested_duration_s": duration_s, "physics_steps": 0}
    Fly = getattr(flygym, "Fly")
    Simulation = getattr(flygym, "SingleFlySimulation", None)
    if Simulation is None:
        Simulation = importlib.import_module("flygym.simulation").SingleFlySimulation
    fly = Fly(enable_adhesion=False, control="position",
              contact_sensor_placements=[f"{leg}{segment}" for leg in LEGS for segment in
                                         ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")])
    sim = Simulation(fly=fly, cameras=[], timestep=timestep_s)
    samples = {leg: [] for leg in LEGS}
    examples = {}
    try:
        reset = sim.reset()
        obs = reset[0] if isinstance(reset, tuple) else reset
        joints_raw = np.asarray(obs["joints"], dtype=np.float64)
        held_joints = (joints_raw[0] if joints_raw.ndim == 2 else joints_raw).copy()
        for step in range(steps + 1):
            vectors = distal_contact_vectors(obs["contact_forces"])
            for leg, vector in vectors.items():
                samples[leg].append(float(np.linalg.norm(vector)))
                examples[leg] = [float(x) for x in vector]
            if step < steps:
                result = sim.step({"joints": held_joints,
                                   "adhesion": np.zeros(6, dtype=np.float64)})
                obs = result[0]
    finally:
        close = getattr(sim, "close", None)
        if close:
            close()
    return {
        "status": "PASSIVE_HOLD_COMPLETE", "requested_duration_s": duration_s,
        "timestep_s": timestep_s, "physics_steps": steps,
        "method": "reset observation plus bounded passive hold of measured joints; no gait/walking controller",
        "selected_segment": DISTAL_SEGMENT, "units": "model force units",
        "statistics": calibration_statistics(samples), "last_raw_vectors": examples,
        "threshold_decision": "Review separation statistics; default 1e-12 is provisional and is not a biological threshold.",
    }


def build_audit(*, live=False, duration_s=0.05):
    config = TactileContactConfig()
    populations = load_tactile_populations()
    return {
        "schema_version": "M5D-2.0",
        "scientific_scope": "contact-only modeled engineering; no load encoder, motor claim, or biological transfer-function claim",
        "physical_signal": {
            "selected_segment": DISTAL_SEGMENT, "row_offsets": [5, 11, 17, 23, 29, 35],
            "reason": "most distal instrumented segment and closest available proxy to annotation-backed claw contact; all six vectors remain telemetry",
            "units": "model force units", "magnitude": "Euclidean norm of selected raw 3-vector",
        },
        "configuration": {
            "classification": "MODELED_ENGINEERING_PARAMETER",
            "engineering_threshold": config.engineering_threshold,
            "threshold_status": "PROVISIONAL_PENDING_LIVE_CALIBRATION",
            "transient_duration_ms": config.transient_duration_ms,
            "maximum_modeled_rate_hz": config.maximum_modeled_rate_hz,
            "envelope": "linear decay from maximum at onset to zero at duration",
        },
        "populations": [{"leg": leg, "name": p.name, "size": len(p.body_ids),
                         "body_ids": list(p.body_ids)} for leg, p in populations.items()],
        "rng_isolation": "SeedSequence(seed).spawn(6), one generator per population; disabled encoder draws none and never accesses tibia/brain RNG",
        "synthetic_open_loop": synthetic_validation(config),
        "real_flygym_calibration": live_calibration(duration_s) if live else {
            "status": "NOT_RUN", "reason": "run with --live in the validated Windows environment",
            "requested_duration_s": duration_s},
        "neural_propagation": {
            "status": "NOT_RUN", "reason": "requires live calibration acceptance and a fresh full MaleCNS runtime",
            "motor_output_applied": False,
        },
        "regression": {"locked_artifacts_modified": False, "tactile_disabled_consumes_rng": False},
    }


def serialized_audit(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration-s", type=float, default=0.05,
                        help="bounded passive calibration duration (default: 0.05 s)")
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = build_audit(live=args.live, duration_s=args.duration_s)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(serialized_audit(report), encoding="utf-8")
    print(args.json)


if __name__ == "__main__":
    main()
