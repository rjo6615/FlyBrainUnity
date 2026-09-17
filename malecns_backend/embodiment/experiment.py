"""Bounded real MaleCNS ↔ FlyGym experiment (never substitutes a fake body)."""
import json
from pathlib import Path

from malecns_backend import MaleCNSBrain, load_malecns
from malecns_backend.loader import process_memory_bytes
from .body import FlyGymBody
from .diagnostics import OUTCOME_CRITERIA, classify_weak_link
from .loop import EmbodimentLoop
from .mappings import load_selected_pathway
from .motor import MotorActivityObserver, MotorDecoder
from .sensory import SensoryEncoder
from .telemetry import JSONLTelemetry


def _peak(rows, value):
    return max((abs(value(row)) for row in rows), default=0.0)


def calculate_physical_metrics(initial, final, rows):
    angles = [initial.frame.tibia_angle_rad] + [r["after"].frame.tibia_angle_rad for r in rows]
    initial_angle, final_angle = angles[0], final.frame.tibia_angle_rad
    return {
        "initial_angle_rad": initial_angle, "final_angle_rad": final_angle,
        "minimum_angle_rad": min(angles), "maximum_angle_rad": max(angles),
        "maximum_displacement_rad": max(abs(x - initial_angle) for x in angles),
        "maximum_command_measured_error_rad": _peak(
            rows, lambda r: r["command"].target_position_rad-r["after"].frame.tibia_angle_rad),
        "peak_abs_velocity_rad_s": max(
            (abs(r["after"].joint_velocity_rad_s) for r in rows), default=0.0),
    }


def summarize_experiment(brain, pathway, loop, rows, initial, final, telemetry_path):
    """Reduce bounded interval samples without modifying simulation state."""
    ext_name, flex_name = pathway.extensor.name, pathway.flexor.name
    sensor_counts = brain.spike_counts[list(pathway.sensor.dense_indices)]
    ext_counts = brain.spike_counts[list(pathway.extensor.dense_indices)]
    flex_counts = brain.spike_counts[list(pathway.flexor.dense_indices)]
    sensory_spikes = int(sensor_counts.sum())
    all_spikes = int(brain.spike_counts.sum())
    nonsensory_spikes = all_spikes - sensory_spikes
    extensor_spikes, flexor_spikes = int(ext_counts.sum()), int(flex_counts.sum())
    motor_spikes = extensor_spikes + flexor_spikes
    physical = calculate_physical_metrics(initial, final, rows)
    initial_angle, final_angle = physical["initial_angle_rad"], physical["final_angle_rad"]
    final_change = abs(final_angle - initial_angle)
    max_displacement = physical["maximum_displacement_rad"]
    peak_antagonist = _peak(rows, lambda r: r["command"].antagonist_signal)
    peak_raw = _peak(rows, lambda r: r["command"].raw_decoder_output_rad)
    peak_final = _peak(rows, lambda r: r["command"].target_position_rad -
                       r["before"].frame.tibia_angle_rad)
    outcome = OUTCOME_CRITERIA.classify(motor_spikes, nonsensory_spikes, final_change)
    response_threshold = OUTCOME_CRITERIA.meaningful_body_response_rad
    metrics = {
        "sensory_spikes": sensory_spikes, "nonsensory_spikes": nonsensory_spikes,
        "motor_spikes": motor_spikes, "peak_antagonist_signal": peak_antagonist,
        "peak_raw_motor_command_rad": peak_raw,
        "peak_final_motor_command_rad": peak_final,
        "max_displacement_rad": max_displacement,
    }
    weak_link, evidence = classify_weak_link(metrics)
    performance = loop.performance()
    _, peak_rss = process_memory_bytes()
    performance.update({
        "peak_rss_bytes": peak_rss,
        "telemetry_file_size_bytes": Path(telemetry_path).stat().st_size,
    })
    return {
        "scientific_outcome": outcome,
        "outcome_criteria": {
            "neural_propagation": "nonsensory_spikes > 0",
            "observed_nonsensory_spikes": nonsensory_spikes,
            "meaningful_body_response": (
                f"motor_spikes > 0 and abs(final_angle - initial_angle) > "
                f"{response_threshold:g} rad"),
            "body_response_threshold_rad": response_threshold,
            "observed_final_joint_change_rad": final_change,
            "observed_motor_spikes": motor_spikes,
        },
        "sensory": {"targeted_neurons": len(sensor_counts),
                    "spiking_neurons": int((sensor_counts > 0).sum()),
                    "total_spikes": sensory_spikes},
        "network": {"spiking_neurons": int((brain.spike_counts > 0).sum()),
                    "total_spikes": all_spikes, "nonsensory_spikes": nonsensory_spikes},
        "extensor": {"body_ids": list(pathway.extensor.body_ids),
                     "cumulative_spikes_per_neuron": [int(x) for x in ext_counts],
                     "spiking_neurons": int((ext_counts > 0).sum()), "total_spikes": extensor_spikes,
                     "peak_filtered_hz": _peak(rows, lambda r: r["motor"]["filtered_hz"][ext_name])},
        "flexor": {"body_ids": list(pathway.flexor.body_ids),
                   "cumulative_spikes_per_neuron": [int(x) for x in flex_counts],
                   "spiking_neurons": int((flex_counts > 0).sum()), "total_spikes": flexor_spikes,
                   "peak_filtered_hz": _peak(rows, lambda r: r["motor"]["filtered_hz"][flex_name])},
        "motor": {"peak_antagonist_signal": peak_antagonist,
                  "peak_raw_command_rad": peak_raw, "peak_final_command_rad": peak_final},
        "physical": physical,
        "latency_s": loop.first_times_s,
        "first_weak_link": weak_link, "weak_link_evidence": evidence,
        "neural_health": brain.diagnostics(), "performance": performance,
        "telemetry": str(Path(telemetry_path).resolve()),
    }


def print_diagnostic_report(result):
    def latency(value):
        return "NEVER" if value is None else f"{value:.9g} s"
    s, n, e, f = result["sensory"], result["network"], result["extensor"], result["flexor"]
    m, p, c = result["motor"], result["physical"], result["outcome_criteria"]
    print("\n=== CLOSED-LOOP CAUSAL FUNNEL ===")
    for label, value in (
        ("Sensory neurons targeted", s["targeted_neurons"]),
        ("Sensory neurons that actually spiked", s["spiking_neurons"]),
        ("Total sensory spikes", s["total_spikes"]),
        ("Whole-CNS neurons that spiked", n["spiking_neurons"]),
        ("Total whole-CNS spikes", n["total_spikes"]),
        ("Extensor MN neurons that spiked", e["spiking_neurons"]),
        ("Extensor MN total spikes", e["total_spikes"]),
        ("Peak extensor filtered Hz", e["peak_filtered_hz"]),
        ("Flexor MN neurons that spiked", f["spiking_neurons"]),
        ("Flexor MN total spikes", f["total_spikes"]),
        ("Peak flexor filtered Hz", f["peak_filtered_hz"]),
        ("Peak antagonist motor signal", m["peak_antagonist_signal"]),
        ("Peak raw motor command", m["peak_raw_command_rad"]),
        ("Peak final motor command", m["peak_final_command_rad"]),
        ("Initial tibia angle", p["initial_angle_rad"]),
        ("Final tibia angle", p["final_angle_rad"]),
        ("Maximum tibia displacement", p["maximum_displacement_rad"]),
    ):
        print(f"{label}: {value}")
    print("\n=== CAUSAL LATENCY ===")
    for key, value in result["latency_s"].items():
        print(f"First {key.replace('_', ' ')} time: {latency(value)}")
    print(f"\nFIRST WEAK LINK: {result['first_weak_link']}")
    print(f"EVIDENCE: {result['weak_link_evidence']}")
    print(f"\nOutcome {result['scientific_outcome'].split('.', 1)[0]} because:")
    print(f"- neural propagation criterion = {c['neural_propagation']}")
    print(f"- observed value = {c['observed_nonsensory_spikes']} nonsensory spikes")
    print(f"- body response criterion = {c['meaningful_body_response']}")
    print(f"- observed value = motor_spikes={c['observed_motor_spikes']}, "
          f"final_joint_change_rad={c['observed_final_joint_change_rad']}")
    print("\n=== REAL EXPERIMENT PERFORMANCE ===")
    print(json.dumps(result["performance"], indent=2))
    print(f"Telemetry output path: {result['telemetry']}")


def run_real_experiment(duration_ms=10, seed=1,
                        telemetry_path=Path("malecns_backend/embodiment/closed_loop.jsonl")):
    """Run the unchanged Test 4 trajectory with passive causal observation."""
    pathway = load_selected_pathway()
    brain = MaleCNSBrain(load_malecns()); brain.reset(seed)
    body = FlyGymBody(selected_joint_index=pathway.flygym_joint_index)
    observer = MotorActivityObserver({pathway.extensor.name: pathway.extensor.dense_indices,
                                      pathway.flexor.name: pathway.flexor.dense_indices})
    try:
        with JSONLTelemetry(telemetry_path) as telemetry:
            loop = EmbodimentLoop(brain, body, SensoryEncoder(pathway), observer,
                                  MotorDecoder(pathway), pathway, telemetry=telemetry)
            initial = body.observe()
            rows = loop.run(duration_ms)
            final = body.observe()
        result = summarize_experiment(brain, pathway, loop, rows, initial, final, telemetry_path)
    finally:
        body.close()
    print_diagnostic_report(result)
    return result
