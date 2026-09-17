"""Bounded real MaleCNS ↔ FlyGym experiment (never substitutes a fake body)."""
import json
from pathlib import Path
import time

from malecns_backend import MaleCNSBrain, load_malecns
from malecns_backend.loader import process_memory_bytes
from .body import FlyGymBody
from .diagnostics import OUTCOME_CRITERIA, classify_weak_link
from .loop import EmbodimentLoop
from .mappings import load_selected_pathway
from .motor import MotorActivityObserver, MotorDecoder
from .sensory import SensoryEncoder
from .telemetry import JSONLTelemetry
from .temporal import (TemporalRecorder, classify_temporal, directed_distances,
                       motor_connectivity)


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


def summarize_experiment(brain, pathway, loop, rows, initial, final, telemetry_path,
                         recorder=None, duration_ms=None, event_trace_path=None):
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
    result = {
        "duration_ms": duration_ms,
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
    if recorder is not None:
        motor_inputs = recorder.motor_results()
        # With an identically zero neural offset the measured trajectory is a
        # direct passive/held-position baseline; no subtraction is performed.
        passive = max_displacement if peak_raw == 0 else None
        commanded = 0.0 if peak_raw == 0 else None
        result.update({
            "downstream_events": recorder.downstream_events,
            "motor_input_diagnostics": motor_inputs,
            "maximum_observed_propagation_hop": max(
                (x["hop_distance_from_selected_sensory_population"]
                 for x in recorder.downstream_events
                 if x["hop_distance_from_selected_sensory_population"] is not None), default=None),
            "temporal_classification": classify_temporal(
                motor_inputs, peak_raw, max_displacement,
                max_displacement if passive is None else passive),
            "displacement_attribution": {
                "passive_physics_displacement_rad": passive,
                "neurally_commanded_displacement_rad": commanded,
                "method": ("zero decoded neural offset makes this run its own passive baseline"
                           if peak_raw == 0 else
                           "not separable without a matched zero-command body replay"),
            },
            "activity_bins": activity_bins(recorder, duration_ms, motor_indices),
            "event_trace": str(Path(event_trace_path).resolve()) if event_trace_path else None,
            "actuator_target_update_explanation": (
                "The target position follows the newly measured joint position when decoder offset is "
                "zero. This is measured-state synchronization/held-position semantics, not nonzero "
                "neural decoder output."),
        })
    return result


def activity_bins(recorder, duration_ms, motor_indices,
                  boundaries=(0, 10, 25, 50, 100, 250, 500)):
    """Aggregate bounded event activity in non-overlapping milestone bins."""
    sensor_seen, downstream_seen = set(), set()
    motor_set = set(motor_indices)
    bins = []
    limits = [x for x in boundaries if x < duration_ms] + [duration_ms]
    for start, end in zip(limits, limits[1:]):
        events = [(t, i) for t, i in recorder.all_spike_events if start < t <= end]
        sensors = {i for _, i in events if i in recorder.sensors}
        downstream = {i for _, i in events if i not in recorder.sensors}
        bins.append({
            "start_ms": start, "end_ms": end,
            "new_sensory_neurons": len(sensors - sensor_seen),
            "new_downstream_neurons": len(downstream - downstream_seen),
            "spikes": len(events),
            "maximum_propagation_depth": max(
                (int(recorder.distances[i]) for i in downstream
                 if recorder.distances[i] >= 0), default=None),
            "motor_pool_input_events": sum(
                1 for _, pre in events for post in motor_set
                if post in recorder.data.target_indices[
                    recorder.data.row_ptr[pre]:recorder.data.row_ptr[pre + 1]]),
            "motor_spikes": sum(i in motor_set for _, i in events),
        })
        sensor_seen.update(sensors); downstream_seen.update(downstream)
    return bins


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
    if not isinstance(duration_ms, (int, float)) or not 0 < duration_ms <= 60_000:
        raise ValueError("duration_ms must be finite and in (0, 60000]")
    if duration_ms % 1:
        raise ValueError("duration_ms must be a whole 1 ms control interval")
    pathway = load_selected_pathway()
    data = load_malecns()
    brain = MaleCNSBrain(data); brain.reset(seed)
    distances = directed_distances(data, pathway.sensor.dense_indices)
    motor_indices = pathway.extensor.dense_indices + pathway.flexor.dense_indices
    recorder = TemporalRecorder(data, pathway.sensor.dense_indices, motor_indices,
                                pathway, distances)
    brain.diagnostic_observer = recorder
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
        event_path = Path(telemetry_path).with_name(Path(telemetry_path).stem + "_events.jsonl")
        with event_path.open("w", encoding="utf-8") as out:
            for event in recorder.downstream_events:
                out.write(json.dumps(event, separators=(",", ":")) + "\n")
        result = summarize_experiment(brain, pathway, loop, rows, initial, final, telemetry_path,
                                      recorder, duration_ms, event_path)
        result["motor_connectivity"] = motor_connectivity(
            data, brain, pathway.sensor.dense_indices, motor_indices, distances)
    finally:
        body.close()
    passive = run_passive_body_baseline(duration_ms, pathway)
    result["displacement_attribution"] = {
        "passive_physics_displacement_rad": passive["maximum_displacement_rad"],
        "neurally_commanded_displacement_rad": (
            max(0.0, result["physical"]["maximum_displacement_rad"] -
                passive["maximum_displacement_rad"])),
        "method": "independent fresh-body zero-neural-command replay; analysis-only difference",
    }
    result["temporal_classification"] = classify_temporal(
        result["motor_input_diagnostics"], result["motor"]["peak_raw_command_rad"],
        result["physical"]["maximum_displacement_rad"], passive["maximum_displacement_rad"])
    print_diagnostic_report(result)
    return result


def run_passive_body_baseline(duration_ms, pathway):
    """Replay physics with a zero decoder offset; never modifies the actual run."""
    body = FlyGymBody(selected_joint_index=pathway.flygym_joint_index)
    decoder = MotorDecoder(pathway)
    rates = {pathway.extensor.name: 0.0, pathway.flexor.name: 0.0}
    try:
        initial = body.observe()
        rows = []
        for _ in range(int(duration_ms)):
            before = body.observe()
            command = decoder.decode(rates, before.frame.tibia_angle_rad, .001)
            after = body.step(command, 10)
            rows.append({"before": before, "after": after, "command": command})
        return calculate_physical_metrics(initial, body.observe(), rows)
    finally:
        body.close()


def run_duration_series(durations_ms=(10, 25, 50, 100, 250, 500), seed=1,
                        output_dir=Path("malecns_backend/embodiment/temporal_output")):
    """Run fresh, same-seed independent replays; never extend a prior simulation."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for duration in durations_ms:
        started = time.perf_counter()
        result = run_real_experiment(
            duration, seed, output_dir / f"temporal_{duration:g}ms.jsonl")
        result["series_total_wall_clock_s"] = time.perf_counter() - started
        (output_dir / f"temporal_{duration:g}ms_summary.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8")
        print_temporal_funnel(result)
        results.append(result)
    return results


def print_temporal_funnel(result):
    """Print a compact temporal funnel rather than whole-CNS state."""
    ext_ids = set(result["extensor"]["body_ids"])
    inputs = result["motor_input_diagnostics"]
    ext = [x for x in inputs if x["body_id"] in ext_ids]
    flex = [x for x in inputs if x["body_id"] not in ext_ids]
    def aggregate(items):
        return (sum(x["presynaptic_spiking_neurons"] for x in items),
                sum(x["excitatory_events"] + x["inhibitory_events"] for x in items),
                max((x["peak_voltage"] for x in items), default=None),
                min((x["closest_threshold_margin"] for x in items), default=None),
                sum(x["threshold_crossed"] for x in items))
    print(f"\n=== TEMPORAL PROPAGATION: {result['duration_ms']:g} ms ===")
    print(f"Sensory neurons spiking: {result['sensory']['spiking_neurons']}")
    print(f"Sensory spikes: {result['sensory']['total_spikes']}")
    downstream_ids = {x["dense_index"] for x in result["downstream_events"]}
    print(f"Non-sensory neurons spiking: {len(downstream_ids)}")
    print(f"Non-sensory spikes: {len(result['downstream_events'])}")
    print(f"Maximum observed propagation hop: {result['maximum_observed_propagation_hop']}")
    for label, items in (("Extensor", ext), ("Flexor", flex)):
        pre, events, voltage, margin, spikes = aggregate(items)
        print(f"{label} presynaptic active neurons: {pre}")
        print(f"{label} synaptic events: {events}")
        print(f"{label} peak voltage: {voltage}")
        print(f"{label} closest threshold margin: {margin}")
        print(f"{label} spikes: {spikes}")
    print(f"Decoded motor signal: {result['motor']['peak_raw_command_rad']}")
    print(f"Maximum physical displacement: {result['physical']['maximum_displacement_rad']}")
    print(f"Scientific outcome: {result['temporal_classification']}")
