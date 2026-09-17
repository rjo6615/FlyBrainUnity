"""Matched Milestone 3D causal-control experiment and measured analysis."""
import csv
import json
import math
from pathlib import Path
import time

import numpy as np

from malecns_backend import MaleCNSBrain, load_malecns
from .body import FlyGymBody
from .loop import EmbodimentLoop
from .mappings import load_selected_pathway
from .motor import MotorActivityObserver, MotorDecoder
from .sensory import SensoryEncoder

TOLERANCE = 1e-12


def _build(seed):
    pathway = load_selected_pathway()
    brain = MaleCNSBrain(load_malecns())
    brain.reset(seed)
    body = FlyGymBody(selected_joint_index=pathway.flygym_joint_index)
    observer = MotorActivityObserver({pathway.extensor.name: pathway.extensor.dense_indices,
                                      pathway.flexor.name: pathway.flexor.dense_indices})
    loop = EmbodimentLoop(brain, body, SensoryEncoder(pathway), observer,
                          MotorDecoder(pathway), pathway)
    return pathway, brain, body, loop


def row_record(row, step, pathway):
    encoded = row["encoded"]
    command = row["command"]
    return {
        "time_ms": step, "tibia_angle_rad": row["after"].frame.tibia_angle_rad,
        "tibia_velocity_rad_s": row["after"].joint_velocity_rad_s,
        "base_actuator_target_rad": row["base_actuator_target_rad"],
        "decoded_neural_offset_rad": row["decoded_neural_offset_rad"],
        "applied_neural_offset_rad": row["applied_neural_offset_rad"],
        "final_actuator_target_rad": command.target_position_rad,
        "sensory_rates_hz": encoded.rates_hz.tolist(),
        "sensory_spikes": row["sensory_spike_increment"],
        "whole_cns_spikes": row["cns_spike_increment"],
        "extensor_mn_spikes": row["motor"]["increments"][pathway.extensor.name],
        "flexor_mn_spikes": row["motor"]["increments"][pathway.flexor.name],
        "filtered_extensor_hz": row["motor"]["filtered_hz"][pathway.extensor.name],
        "filtered_flexor_hz": row["motor"]["filtered_hz"][pathway.flexor.name],
        "antagonist_signal": command.antagonist_signal,
    }


def analyze_matched(closed, control, tolerance=TOLERANCE):
    """Calculate equivalence, divergence, ordering and D0--D3 from samples."""
    if [r["time_ms"] for r in closed] != [r["time_ms"] for r in control]:
        raise ValueError("matched telemetry timestamps differ")
    decoded = next((r["time_ms"] for r in closed
                    if abs(r["decoded_neural_offset_rad"]) > tolerance), None)
    applied = next((r["time_ms"] for r in closed
                    if abs(r["applied_neural_offset_rad"]) > tolerance), None)
    extensor = next((r["time_ms"] for r in closed if r["extensor_mn_spikes"]), None)
    prior = [i for i, r in enumerate(closed) if decoded is None or r["time_ms"] < decoded]
    angle_d = [a["tibia_angle_rad"]-b["tibia_angle_rad"] for a, b in zip(closed, control)]
    velocity_d = [a["tibia_velocity_rad_s"]-b["tibia_velocity_rad_s"]
                  for a, b in zip(closed, control)]
    physical = next((r["time_ms"] for r, d in zip(closed, angle_d)
                     if decoded is not None and r["time_ms"] >= decoded and abs(d) > tolerance), None)
    def first_difference(key):
        return next((a["time_ms"] for a, b in zip(closed, control) if a[key] != b[key]), None)
    sensory_encoding = next((a["time_ms"] for a, b in zip(closed, control)
                             if not np.array_equal(a["sensory_rates_hz"], b["sensory_rates_hz"])), None)
    sensory_spikes = first_difference("sensory_spikes")
    cns = first_difference("whole_cns_spikes")
    motor = next((a["time_ms"] for a, b in zip(closed, control)
                  if (a["extensor_mn_spikes"], a["flexor_mn_spikes"]) !=
                     (b["extensor_mn_spikes"], b["flexor_mn_spikes"])), None)
    post = [d for r, d in zip(closed, angle_d) if decoded is not None and r["time_ms"] >= decoded]
    pre_angle = max((abs(angle_d[i]) for i in prior), default=0.0)
    pre_velocity = max((abs(velocity_d[i]) for i in prior), default=0.0)
    # The fifth Milestone 3D causal stage is specifically the first change in
    # encoded sensory rates.  The downstream spike divergences are reported as
    # separate observations, but are not substitutes for physical feedback.
    feedback = sensory_encoding
    motor_order = (extensor is not None and decoded is not None and applied is not None and
                   physical is not None and extensor <= decoded <= applied <= physical)
    feedback_order = feedback is None or (physical is not None and feedback >= physical)
    causal_order_valid = motor_order and feedback_order
    if (pre_angle > tolerance or pre_velocity > tolerance or
            (physical is not None and not causal_order_valid)):
        classification = "D0 — INVALID CONTROL"
    elif physical is None:
        classification = "D1 — MOTOR SIGNAL GENERATED, NO MEASURABLE PHYSICAL EFFECT"
    elif feedback is not None and causal_order_valid:
        classification = "D3 — PHYSICAL DIVERGENCE PRODUCES CLOSED-LOOP FEEDBACK DIVERGENCE"
    else:
        classification = "D2 — MOTOR SIGNAL CAUSES MEASURABLE PHYSICAL DIVERGENCE"
    by_time = {r["time_ms"]: d for r, d in zip(closed, angle_d)}
    return {
        "tolerance": tolerance, "first_extensor_spike_ms": extensor,
        "first_decoded_signal_ms": decoded, "first_applied_contribution_ms": applied,
        "pre_motor_max_angle_difference_rad": pre_angle,
        "pre_motor_max_velocity_difference_rad_s": pre_velocity,
        "first_physical_divergence_ms": physical,
        "angle_differences_rad": {str(t): by_time.get(t) for t in (50, 100, 250, 500)},
        "maximum_absolute_angle_difference_rad": max(map(abs, angle_d), default=0.0),
        "rms_post_motor_angle_difference_rad": math.sqrt(np.mean(np.square(post))) if post else 0.0,
        "maximum_absolute_velocity_difference_rad_s": max(map(abs, velocity_d), default=0.0),
        "final_angle_difference_rad": angle_d[-1] if angle_d else 0.0,
        "divergence_sign": ("positive/extensor direction" if angle_d and angle_d[-1] > 0
                            else "negative/flexor direction" if angle_d and angle_d[-1] < 0 else "zero"),
        "first_sensory_encoding_divergence_ms": sensory_encoding,
        "first_sensory_spike_divergence_ms": sensory_spikes,
        "first_cns_spike_divergence_ms": cns,
        "first_motor_population_divergence_ms": motor,
        "causal_order": [extensor, decoded, applied, physical, feedback],
        "causal_order_valid": causal_order_valid,
        "classification": classification,
    }


def run_causal_control(duration_ms=500, seed=1,
                       output_dir=Path("malecns_backend/embodiment/causal_output")):
    """Run two fresh same-seed bodies; only neural-offset application differs."""
    if duration_ms != 500:
        raise ValueError("Milestone 3D primary matched experiment duration is fixed at 500 ms")
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    results, performances = [], []
    for name, apply in (("causal_closed_loop", True), ("causal_motor_disabled", False)):
        pathway, brain, body, loop = _build(seed)
        started = time.perf_counter()
        try:
            raw = loop.run(duration_ms, apply_neural_motor=apply)
            records = [row_record(row, i, pathway) for i, row in enumerate(raw, 1)]
        finally:
            body.close()
        path = output_dir / f"{name}.jsonl"
        path.write_text("".join(json.dumps(x, separators=(",", ":")) + "\n" for x in records),
                        encoding="utf-8")
        results.append(records)
        performances.append({**loop.performance(), "total_wall_clock_s": time.perf_counter()-started})
    closed, control = results
    comparison = output_dir / "causal_difference.csv"
    with comparison.open("w", newline="", encoding="utf-8") as out:
        fields = ("time_ms", "closed_loop_angle", "control_angle", "angle_difference",
                  "closed_loop_velocity", "control_velocity", "velocity_difference",
                  "closed_loop_neural_offset", "control_observed_neural_offset")
        writer = csv.DictWriter(out, fieldnames=fields); writer.writeheader()
        for a, b in zip(closed, control):
            writer.writerow(dict(time_ms=a["time_ms"], closed_loop_angle=a["tibia_angle_rad"],
                control_angle=b["tibia_angle_rad"], angle_difference=a["tibia_angle_rad"]-b["tibia_angle_rad"],
                closed_loop_velocity=a["tibia_velocity_rad_s"], control_velocity=b["tibia_velocity_rad_s"],
                velocity_difference=a["tibia_velocity_rad_s"]-b["tibia_velocity_rad_s"],
                closed_loop_neural_offset=a["decoded_neural_offset_rad"],
                control_observed_neural_offset=b["decoded_neural_offset_rad"]))
    analysis = analyze_matched(closed, control)
    analysis.update({"seed": seed, "duration_ms": duration_ms,
                     "matched_fresh_instances": True,
                     "actuator_equation": "candidate=current_measured_position+(apply? decoded_offset:0); final=joint_range_clamp(slew_clamp(previous_target,candidate,4 rad/s * 0.001 s))",
                     "telemetry": [str((output_dir/f"causal_closed_loop.jsonl").resolve()),
                                   str((output_dir/f"causal_motor_disabled.jsonl").resolve()),
                                   str(comparison.resolve())], "performance": performances})
    (output_dir/"causal_summary.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    return analysis
