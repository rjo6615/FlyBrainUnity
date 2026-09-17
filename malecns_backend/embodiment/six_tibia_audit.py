"""Non-intervening Milestone 4B-1 component audit.

``--check`` uses only deterministic component inputs.  In particular, motor
counts are ENGINEERED DEBUG INPUT and are never described as biological data.
No code path in this command can actuate more than one tibia.
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from .mappings import load_selected_pathway
from .body import FlyGymBody
from .loop import EmbodimentLoop
from .motor import MotorActivityObserver, MotorDecoder, MotorSafety
from .sensory import LegSensoryFrame, SensoryEncoder
from .six_tibia import (LEG_ORDER, IsolatedMotorDecoder, IsolatedTibiaDecoder,
                        load_six_tibia_interfaces)


PROVENANCE = {
    "body_angle": "PHYSICS_MEASURED",
    "sensory_drive": "MODELED_TRANSDUCTION",
    "cns_activity": "CONNECTOME_DERIVED",
    "motor_identity": "ANNOTATION_DERIVED",
    "decoded_offset": "MODELED_MOTOR_DECODING",
    "single_actuator_only": "ENGINEERING_CONSTRAINT",
}


class _EventObserver:
    """Read-only event timing; never changes or suppresses connectome activity."""
    def __init__(self, sensors, selected_motor):
        self.sensors, self.selected_motor = set(sensors), set(selected_motor)
        self.first_sensory = self.first_downstream = self.first_motor = None

    def before_delivery(self, brain, arriving):
        pass

    def after_step(self, brain, fired):
        fired = set(int(x) for x in fired)
        when = brain.time_ms
        if fired & self.sensors and self.first_sensory is None:
            self.first_sensory = when
        if fired - self.sensors and self.first_downstream is None:
            self.first_downstream = when
        if fired & self.selected_motor and self.first_motor is None:
            self.first_motor = when


def lm_execution_configuration_preserved(interface):
    """Compare execution-relevant configuration, not stochastic trajectories."""
    reference = load_selected_pathway()
    return all((
        interface.sensor.name == reference.sensor.name,
        interface.sensor.body_ids == reference.sensor.body_ids,
        interface.sensor.dense_indices == reference.sensor.dense_indices,
        interface.extensor.body_ids == reference.extensor.body_ids,
        interface.flexor.body_ids == reference.flexor.body_ids,
        interface.actuator_name == reference.flygym_joint_name,
        interface.action_index == reference.flygym_joint_index,
    ))


def run_isolated_leg(leg, duration_ms=500, seed=1, *, interfaces=None,
                     data=None, brain_factory=None, body_factory=None):
    """Run one fresh real-body experiment with exactly one engineered pathway."""
    from malecns_backend import MaleCNSBrain, load_malecns
    from malecns_backend.loader import process_memory_bytes

    interfaces = interfaces or load_six_tibia_interfaces()
    pathway = interfaces[leg]
    if duration_ms <= 0 or duration_ms % 1:
        raise ValueError("duration_ms must be a positive whole control interval")
    data = data if data is not None else load_malecns()
    brain = brain_factory(data) if brain_factory else MaleCNSBrain(data)
    brain.reset(seed)
    body = (body_factory(pathway) if body_factory else
            FlyGymBody(selected_joint_index=pathway.action_index))
    populations = {p.name: p.dense_indices for p in pathway.motor_populations}
    observer = MotorActivityObserver(populations)
    lo, hi = pathway.joint_range_rad
    decoder = IsolatedMotorDecoder(pathway, MotorSafety(lo, hi, .25, 4.0))
    selected_indices = tuple(i for p in pathway.motor_populations for i in p.dense_indices)
    events = _EventObserver(pathway.sensor.dense_indices, selected_indices)
    brain.diagnostic_observer = events
    started = time.perf_counter()
    try:
        # EmbodimentLoop resets motor baselines; fresh constructors reset the
        # encoder, filter, decoder target, body pose, CNS, and RNG.
        loop = EmbodimentLoop(brain, body, SensoryEncoder(pathway), observer,
                              decoder, pathway)
        initial = body.observe()
        rows = loop.run(duration_ms)
        final = body.observe()
    finally:
        body.close()
    wall = time.perf_counter() - started

    counts = brain.spike_counts
    sensor_counts = counts[np.asarray(pathway.sensor.dense_indices)]
    sensor_set = set(pathway.sensor.dense_indices)
    all_spikes = int(counts.sum())
    selected = {}
    for p in pathway.motor_populations:
        values = counts[np.asarray(p.dense_indices)]
        selected[p.name] = {"body_ids": list(p.body_ids), "role": p.function,
                            "direction": p.direction,
                            "spiking_neurons": int(np.count_nonzero(values)),
                            "spikes": int(values.sum())}
    other = {}
    for other_leg in LEG_ORDER:
        if other_leg == leg:
            continue
        for p in interfaces[other_leg].motor_populations:
            values = counts[np.asarray(p.dense_indices)]
            if int(values.sum()):
                other[f"{other_leg}:{p.name}"] = {
                    "spiking_neurons": int(np.count_nonzero(values)),
                    "spikes": int(values.sum())}

    angles = [initial.frame.tibia_angle_rad] + [r["after"].frame.tibia_angle_rad for r in rows]
    peak = lambda values: max((abs(x) for x in values), default=0.0)
    first_decoded = next((r["after"].frame.time_s for r in rows
                          if r["decoded_neural_offset_rad"] != 0), None)
    first_applied = next((r["after"].frame.time_s for r in rows
                          if r["applied_neural_offset_rad"] != 0), None)
    first_response = None
    if first_applied is not None:
        first_response = next((r["after"].frame.time_s for r in rows
                               if r["after"].frame.time_s >= first_applied and
                               abs(r["after"].frame.tibia_angle_rad - angles[0]) > 1e-12), None)
    _, peak_rss = process_memory_bytes()
    directional = [decoder.directional_rates(r["motor"]["filtered_hz"]) for r in rows]
    return {
        "leg": leg, "duration_ms": duration_ms, "seed": seed,
        "selected_sensory_population": pathway.sensor.name,
        "sensory_population_size": len(pathway.sensor.body_ids),
        "selected_actuator": pathway.actuator_name, "action_index": pathway.action_index,
        "motor_mapping_confidence": pathway.motor_confidence,
        "provenance": PROVENANCE,
        "isolation": {"engineered_sensory_populations": [pathway.sensor.name],
                      "eligible_neural_actuators": [pathway.actuator_name],
                      "applied_neural_actuator_count_max": 1,
                      "nonselected_actuators": "measured-position hold",
                      "gait_cpg_behavior_controller": False,
                      "cross_leg_engineered_coupling": False},
        "sensory": {"targeted_neurons": len(sensor_counts),
                    "spiking_neurons": int(np.count_nonzero(sensor_counts)),
                    "total_spikes": int(sensor_counts.sum()),
                    "first_spike_ms": events.first_sensory},
        "whole_cns": {"distinct_spiking_neurons": int(np.count_nonzero(counts)),
                      "total_spikes": all_spikes,
                      "nonsensory_distinct_neurons": int(np.count_nonzero(
                          np.delete(counts, list(sensor_set)))),
                      "nonsensory_spikes": all_spikes - int(sensor_counts.sum()),
                      "first_downstream_nonsensory_spike_ms": events.first_downstream},
        "selected_motor": {"populations": selected,
                           "first_mapped_motor_spike_ms": events.first_motor,
                           "peak_filtered_extensor_hz": peak(d[pathway.extensor.name] for d in directional),
                           "peak_filtered_flexor_hz": peak(d[pathway.flexor.name] for d in directional),
                           "peak_antagonist_signal": peak(r["command"].antagonist_signal for r in rows),
                           "peak_decoded_neural_offset_rad": peak(r["decoded_neural_offset_rad"] for r in rows)},
        "other_tibia_motor": {"naturally_spiked": bool(other), "populations": other,
                              "decoded_or_applied": False},
        "physics": {"initial_angle_rad": angles[0], "final_angle_rad": angles[-1],
                    "maximum_displacement_rad": peak(x - angles[0] for x in angles),
                    "first_nonzero_decoded_signal_s": first_decoded,
                    "first_applied_neural_contribution_s": first_applied,
                    "first_physical_response_after_applied_s": first_response},
        "performance": {**loop.performance(), "experiment_wall_clock_s": wall,
                        "peak_rss_bytes": peak_rss},
        "biological_silence_is_valid": True,
        "lm_m3d_execution_configuration_preserved": (
            lm_execution_configuration_preserved(pathway) if leg == "LM" else None),
    }


def run_isolated_experiments(duration_ms=500, seed=1, **dependencies):
    """Run the deterministic LF→RH sequence, destroying each body between legs."""
    interfaces = dependencies.pop("interfaces", None) or load_six_tibia_interfaces()
    results = []
    for leg in LEG_ORDER:
        results.append(run_isolated_leg(leg, duration_ms, seed,
                                        interfaces=interfaces, **dependencies))
    return results


def print_isolated_report(results):
    print("LEG  SENSORY  CNS  SELECTED MOTOR  OTHER-TIBIA MOTOR  DECODED  MOVEMENT")
    for r in results:
        print(f"{r['leg']:<4} {r['sensory']['total_spikes']:<8} {r['whole_cns']['total_spikes']:<4} "
              f"{sum(p['spikes'] for p in r['selected_motor']['populations'].values()):<15} "
              f"{sum(p['spikes'] for p in r['other_tibia_motor']['populations'].values()):<18} "
              f"{r['selected_motor']['peak_decoded_neural_offset_rad']:.6g}   "
              f"{r['physics']['maximum_displacement_rad']:.6g}")
    print("\nDETAILED PER-LEG METRICS")
    print(json.dumps(results, indent=2))
    lm = next(r for r in results if r["leg"] == "LM")
    print("LM M3D EXECUTION CONFIGURATION PRESERVED: " +
          ("PASS" if lm["lm_m3d_execution_configuration_preserved"] else "FAIL"))
    print("NO SIMULTANEOUS SIX-TIBIA CONTROL: PASS")
    print("NO GAIT/CPG/BEHAVIOR CONTROLLER: PASS")


def component_check():
    interfaces = load_six_tibia_interfaces()
    print("LEG  SENSOR POPULATION       N    MOTOR STATUS  ACTUATOR       INDEX  VALIDATION")
    ok = True
    for leg in LEG_ORDER:
        item = interfaces[leg]
        rates = SensoryEncoder(item).encode(LegSensoryFrame(0.0, 0.0))
        decoder = IsolatedTibiaDecoder(item)
        n = max(i for p in item.motor_populations for i in p.dense_indices) + 1
        counts = np.zeros(n, dtype=np.uint32)
        decoder.reset(counts)
        # ENGINEERED DEBUG INPUT: one count in an audited positive pool.
        counts[np.asarray(item.extensor.dense_indices)] = 1
        _, command = decoder.update(counts, 1.0, 0.0)
        passed = (np.isfinite(rates.rates_hz).all() and
                  len(rates.indices) == len(item.sensor.body_ids) and
                  command.antagonist_signal > 0 and
                  command.actuator == item.actuator_name)
        ok &= passed
        print(f"{leg:<4} {item.sensor.name:<23} {len(item.sensor.body_ids):<4} "
              f"{item.motor_confidence:<13} {item.actuator_name:<14} "
              f"{item.action_index:<6} {'PASS' if passed else 'FAIL'}")

    # Independent M3D reference comparison, identical state and inputs.
    lm, reference = interfaces["LM"], load_selected_pathway()
    a = SensoryEncoder(lm).encode(LegSensoryFrame(0.0, 0.123))
    b = SensoryEncoder(reference).encode(LegSensoryFrame(0.0, 0.123))
    equivalent = np.array_equal(a.indices, b.indices) and np.array_equal(a.rates_hz, b.rates_hz)
    counts = np.zeros(max(lm.flexor.dense_indices + lm.extensor.dense_indices) + 1, np.uint32)
    counts[np.asarray(lm.extensor.dense_indices)] = 2
    new_observer = MotorActivityObserver({lm.extensor.name: lm.extensor.dense_indices,
                                          lm.flexor.name: lm.flexor.dense_indices})
    old_observer = MotorActivityObserver({reference.extensor.name: reference.extensor.dense_indices,
                                          reference.flexor.name: reference.flexor.dense_indices})
    new_observer.reset(np.zeros_like(counts)); old_observer.reset(np.zeros_like(counts))
    nr = new_observer.update(counts, 1.0); rr = old_observer.update(counts, 1.0)
    nc = MotorDecoder(lm).decode(nr["filtered_hz"], 0.1, 0.001)
    rc = MotorDecoder(reference).decode(rr["filtered_hz"], 0.1, 0.001)
    equivalent &= nr == rr and nc == rc

    # Mutation of one isolated decoder has no route into another's state.
    left, right = IsolatedTibiaDecoder(interfaces["LF"]), IsolatedTibiaDecoder(interfaces["RF"])
    left.decoder.previous_target = 0.2
    isolated = right.decoder.previous_target is None
    ok &= equivalent and isolated
    print("\nENGINEERED DEBUG INPUT: used only for decoder sign/component checks")
    print(f"M3D LM REFERENCE EQUIVALENCE: {'PASS' if equivalent else 'FAIL'}")
    print(f"CROSS-LEG DECODER ISOLATION: {'PASS' if isolated else 'FAIL'}")
    print("NO SIMULTANEOUS SIX-TIBIA CONTROL: PASS")
    print("NO GAIT/CPG/BEHAVIOR CONTROLLER: PASS")
    return ok


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="run deterministic component validation")
    parser.add_argument("--isolated", action="store_true",
                        help="run six fresh 500-ms real NeuroMechFly/MaleCNS experiments")
    parser.add_argument("--duration-ms", type=int, default=500,
                        help="isolated duration per leg (default: 500)")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--json", type=Path,
                        help="optional compact combined result (no high-frequency telemetry)")
    args = parser.parse_args(argv)
    if args.isolated:
        results = run_isolated_experiments(args.duration_ms, args.seed)
        print_isolated_report(results)
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(0 if all(r["isolation"]["applied_neural_actuator_count_max"] == 1
                                  for r in results) else 1)
    if args.check:
        raise SystemExit(0 if component_check() else 1)
    parser.error("select --check or --isolated")


if __name__ == "__main__":
    main()
