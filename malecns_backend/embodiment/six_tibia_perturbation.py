"""Six-tibia leave-one-out sensory-delivery perturbation (Milestone 4C-2).

The intervention is deliberately narrow: all six encoders run normally and
MaleCNS samples all six external spike candidates normally.  Candidate events
from one selected population are withheld only after sampling and immediately
before CNS delivery.  No anatomical or physical object is removed.
"""
from __future__ import annotations

import math
import sys
import time
from collections import Counter

import numpy as np

from .body import SixTibiaFlyGymBody
from .six_tibia import LEG_ORDER, load_six_tibia_interfaces
from .six_tibia_causal import CANONICAL_SEED, SixTibiaRuntime
from .six_tibia_pathway_audit import CANONICAL

CANONICAL_DURATION_MS = 500
SAMPLE_TIMES_MS = (50, 100, 250, 500)
TOLERANCE = 1e-12


def _peak_rss():
    if sys.platform == "win32": return None
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def _first_pair(control, intervention, predicate, not_before=None):
    return next((a["time_ms"] for a, b in zip(intervention, control)
                 if (not_before is None or a["time_ms"] >= not_before) and predicate(a, b)), None)


def first_spike_delta(value, baseline):
    """Signed timing delta, or ``None`` if either event is undefined."""
    return None if value is None or baseline is None else float(value - baseline)


def motor_influence_matrix(baseline_counts, intervention_counts):
    """Return signed intervention-minus-control motor spike differences."""
    return {source: {target: int(intervention_counts[source][target] - baseline_counts[target])
                     for target in LEG_ORDER} for source in LEG_ORDER}


def split_own_cross(source, deltas):
    return {"own_leg_motor_delta": int(deltas[source]),
            "cross_leg_motor_deltas": {leg: int(deltas[leg]) for leg in LEG_ORDER if leg != source}}


def classify_trace(valid, cns, motor, applied, physical, returned, later_cns, later_motor):
    """Engineering causal trace stage; stages require all prior prerequisites."""
    if not valid: return "P0"
    stage = 1
    if cns is not None: stage = 2
    if stage >= 2 and motor is not None: stage = 3
    if stage >= 3 and applied is not None and physical is not None and physical >= applied: stage = 4
    if stage >= 4 and returned is not None and returned >= physical: stage = 5
    if stage >= 5 and later_cns is not None and later_cns >= returned: stage = 6
    if stage >= 6 and later_motor is not None and later_motor >= returned: stage = 7
    return f"P{stage}"


def _motor_summary(rows, runtime, leg):
    interface = runtime.interfaces[leg]
    by_population = {p.name: sum(int(row["motor"][leg]["increments"].get(p.name, 0))
                                  for row in rows) for p in interface.motor_populations}
    by_role = {"extensor": 0, "flexor": 0, "accessory_flexor": 0}
    for population in interface.motor_populations:
        role = population.function.lower().replace("-", "_").replace(" ", "_")
        bucket = ("accessory_flexor" if "accessory" in role and "flexor" in role else
                  "flexor" if "flexor" in role else "extensor" if "extensor" in role else None)
        if bucket: by_role[bucket] += by_population[population.name]
    peaks = [float(value) for row in rows for value in row["motor"][leg]["filtered_hz"].values()]
    return {"selected_mapped_motor_spikes": int(sum(by_population.values())),
            "first_mapped_motor_spike_ms": runtime.events.first_motor[leg],
            "population_spikes": by_population,
            "extensor_spikes": by_role["extensor"], "flexor_spikes": by_role["flexor"],
            "accessory_flexor_spikes": by_role["accessory_flexor"],
            "peak_filtered_motor_activity_hz": max(peaks, default=0.),
            "peak_decoded_offset_rad": max((abs(float(row["actuation"][leg]["decoded_offset_rad"]))
                                             for row in rows), default=0.)}


def summarize_run(rows, runtime, wall_seconds):
    sensors = set(i for leg in LEG_ORDER for i in runtime.interfaces[leg].sensor.dense_indices)
    fired = [set(map(int, row["spiking_neuron_indices"])) for row in rows]
    all_fired = set().union(*fired) if fired else set()
    nonsensory = [indices - sensors for indices in fired]
    return {"withheld_sensory_population": runtime.withheld_sensory,
        "sensory": {leg: {
            "counterfactual_encoded_spikes": sum(row["counterfactual_sensory_increments"][leg] for row in rows),
            "intervention_delivered_spikes": sum(row["delivered_sensory_increments"][leg] for row in rows),
            "counterfactual_provenance": "MODELED_TRANSDUCTION",
            "delivered_provenance": ("ENGINEERED_SENSORY_WITHHOLDING"
                                     if leg == runtime.withheld_sensory else "MODELED_TRANSDUCTION")}
            for leg in LEG_ORDER},
        "motor": {leg: _motor_summary(rows, runtime, leg) for leg in LEG_ORDER},
        "cns": {"total_spikes": sum(row["cns_spike_increment"] for row in rows),
            "distinct_spiking_neurons": len(all_fired),
            "nonsensory_spikes": sum(len(x) for x in nonsensory),
            "distinct_nonsensory_spiking_neurons": len(set().union(*nonsensory) if nonsensory else set())},
        "performance": {"wall_seconds": wall_seconds,
            "real_time_factor": (CANONICAL_DURATION_MS / 1000) / wall_seconds if wall_seconds else None,
            "peak_rss_platform_units": _peak_rss()}}


def validate_canonical_baseline(summary):
    checks = {}
    for leg, expected in CANONICAL.items():
        motor = summary["motor"][leg]; sensory = summary["sensory"][leg]
        checks[leg] = {
            "sensory_spikes": sensory["intervention_delivered_spikes"] == expected[0],
            "motor_spikes": motor["selected_mapped_motor_spikes"] == expected[1],
            "first_motor": motor["first_mapped_motor_spike_ms"] == expected[2],
            "peak_offset": abs(motor["peak_decoded_offset_rad"] - expected[3]) <= TOLERANCE}
    return checks, all(all(values.values()) for values in checks.values())


def compare_intervention(control, intervention, baseline, result, source, brain):
    sensory_indices = set(int(i) for leg in LEG_ORDER for i in control[0]["encoded"][leg].indices)
    cns = _first_pair(control, intervention, lambda a, b:
        (set(a["spiking_neuron_indices"]) - sensory_indices) !=
        (set(b["spiking_neuron_indices"]) - sensory_indices))
    motor = _first_pair(control, intervention, lambda a, b: any(
        a["motor"][leg]["increments"] != b["motor"][leg]["increments"] for leg in LEG_ORDER))
    decoded = _first_pair(control, intervention, lambda a, b: any(abs(
        a["actuation"][leg]["decoded_offset_rad"] - b["actuation"][leg]["decoded_offset_rad"]) > TOLERANCE
        for leg in LEG_ORDER))
    applied = _first_pair(control, intervention, lambda a, b: any(abs(
        a["actuation"][leg]["final_target_rad"] - b["actuation"][leg]["final_target_rad"]) > TOLERANCE
        for leg in LEG_ORDER))
    differences = np.asarray([[a["after"].angles_rad[leg] - b["after"].angles_rad[leg]
                               for leg in LEG_ORDER] for a, b in zip(intervention, control)])
    norms = np.linalg.norm(differences, axis=1)
    physical = next((row["time_ms"] for row, norm in zip(intervention, norms) if norm > TOLERANCE), None)
    returned = (_first_pair(control, intervention, lambda a, b: any(
        leg != source and not np.array_equal(a["encoded"][leg].rates_hz, b["encoded"][leg].rates_hz)
        for leg in LEG_ORDER), physical + 1) if physical is not None else None)
    later_cns = (_first_pair(control, intervention, lambda a, b:
        (set(a["spiking_neuron_indices"]) - sensory_indices) !=
        (set(b["spiking_neuron_indices"]) - sensory_indices), returned) if returned is not None else None)
    later_motor = (_first_pair(control, intervention, lambda a, b: any(
        a["motor"][leg]["increments"] != b["motor"][leg]["increments"] for leg in LEG_ORDER), returned)
        if returned is not None else None)
    motor_deltas = {leg: result["motor"][leg]["selected_mapped_motor_spikes"] -
                    baseline["motor"][leg]["selected_mapped_motor_spikes"] for leg in LEG_ORDER}
    for leg in LEG_ORDER:
        current, base = result["motor"][leg], baseline["motor"][leg]
        current.update({"delta_motor_spikes": int(motor_deltas[leg]),
            "delta_first_spike_ms": first_spike_delta(current["first_mapped_motor_spike_ms"], base["first_mapped_motor_spike_ms"]),
            "delta_peak_decoded_offset_rad": current["peak_decoded_offset_rad"] - base["peak_decoded_offset_rad"]})
    for field in list(result["cns"]):
        result["cns"][f"delta_{field}"] = result["cns"][field] - baseline["cns"][field]
    by_time = {row["time_ms"]: vector for row, vector in zip(intervention, differences)}
    result["physical"] = {"first_divergence_ms": physical,
        "angle_differences_rad": {str(t): {leg: float(by_time[t][i]) for i, leg in enumerate(LEG_ORDER)}
                                  for t in SAMPLE_TIMES_MS},
        "maximum_norm_rad": float(max(norms, default=0.)),
        "final_norm_rad": float(norms[-1]) if len(norms) else 0.,
        "rms_post_divergence_norm_rad": float(math.sqrt(np.mean(np.square(
            [n for row, n in zip(intervention, norms) if physical is not None and row["time_ms"] >= physical])))) if physical is not None else 0.}
    first_difference = next(((a, b) for a, b in zip(intervention, control)
                             if a["spiking_neuron_indices"] != b["spiking_neuron_indices"]), None)
    control_counts = Counter(i for row in control for i in row["spiking_neuron_indices"])
    intervention_counts = Counter(i for row in intervention for i in row["spiking_neuron_indices"])
    differing = {i for i in control_counts.keys() | intervention_counts.keys()
                 if control_counts[i] != intervention_counts[i]}
    first_index = min((set(first_difference[0]["spiking_neuron_indices"]) ^
                       set(first_difference[1]["spiking_neuron_indices"]))) if first_difference else None
    result["cns"].update({"first_divergence_ms": cns,
        "number_of_neurons_with_event_differences": len(differing),
        "first_differing_dense_index": first_index,
        "first_differing_body_id": int(brain.data.body_ids[first_index]) if first_index is not None and hasattr(brain, "data") else None})
    valid = (result["sensory"][source]["intervention_delivered_spikes"] == 0 and
             all(all(row["delivered_sensory_increments"][leg] == row["counterfactual_sensory_increments"][leg]
                     for row in intervention) for leg in LEG_ORDER if leg != source))
    result["causal_trace"] = {"classification": classify_trace(valid, cns, motor, applied, physical,
        returned, later_cns, later_motor), "direct_intervention": {"first_cns_divergence_ms": cns,
        "first_mapped_motor_divergence_ms": motor, "first_decoded_motor_divergence_ms": decoded,
        "first_applied_actuator_divergence_ms": applied, "first_physical_divergence_ms": physical},
        "returned_physical_feedback": {"first_nonwithheld_sensory_encoding_divergence_ms": returned,
            "first_later_cns_divergence_ms": later_cns, "first_later_mapped_motor_divergence_ms": later_motor}}
    result.update(split_own_cross(source, motor_deltas))
    return motor_deltas


def run_perturbation_experiment(duration_ms=CANONICAL_DURATION_MS, seed=CANONICAL_SEED, *,
                                interfaces=None, data=None, brain_factory=None, body_factory=None,
                                progress=None):
    """Run one all-six baseline followed by six fresh leave-one-out runs."""
    if duration_ms != CANONICAL_DURATION_MS: raise ValueError("canonical duration is fixed at 500 ms")
    if seed != CANONICAL_SEED: raise ValueError("M4C-2 canonical seed is fixed at 1")
    from malecns_backend import MaleCNSBrain, load_malecns
    interfaces = interfaces or load_six_tibia_interfaces(); data = data if data is not None else load_malecns()
    make_brain = brain_factory or MaleCNSBrain; make_body = body_factory or SixTibiaFlyGymBody
    rows_by_run = {}; summaries = {}; runtimes = {}; total_start = time.perf_counter()
    conditions = (("ALL SIX", None),) + tuple((f"-{leg}", leg) for leg in LEG_ORDER)
    for ordinal, (label, withheld) in enumerate(conditions, 1):
        if progress: progress(f"[{ordinal}/7] {label}")
        brain = make_brain(data); body = make_body(interfaces); runtime = None
        started = time.perf_counter()
        try:
            runtime = SixTibiaRuntime(brain, body, interfaces, seed, True, withheld_sensory=withheld)
            rows = [runtime.step(t) for t in range(1, duration_ms + 1)]
        finally: body.close()
        rows_by_run[label] = rows; runtimes[label] = runtime
        summaries[label] = summarize_run(rows, runtime, time.perf_counter() - started)
        if withheld is None:
            checks, passed = validate_canonical_baseline(summaries[label])
            if not passed: raise RuntimeError("BASELINE REPRODUCTION: FAIL; interventions were not run")
    baseline = summaries["ALL SIX"]
    for leg in LEG_ORDER:
        compare_intervention(rows_by_run["ALL SIX"], rows_by_run[f"-{leg}"], baseline,
                             summaries[f"-{leg}"], leg, runtimes[f"-{leg}"].brain)
    matrix = motor_influence_matrix(
        {leg: baseline["motor"][leg]["selected_mapped_motor_spikes"] for leg in LEG_ORDER},
        {source: {target: summaries[f"-{source}"]["motor"][target]["selected_mapped_motor_spikes"]
                  for target in LEG_ORDER} for source in LEG_ORDER})
    checks, _ = validate_canonical_baseline(baseline)
    return {"milestone": "4C-2", "condition": "500 ms seed-1 modeled embodiment",
        "seed": seed, "duration_ms": duration_ms, "baseline_reproduction": "PASS",
        "baseline_checks": checks, "runs": summaries, "motor_spike_delta_matrix": matrix,
        "performance": {"total_wall_seconds": time.perf_counter() - total_start,
            "run_count": 7},
        "scientific_safeguards": ["sensory delivery withholding only", "common random numbers",
            "physical legs retained", "motor systems retained", "connectome retained",
            "model constants unchanged", "no gait, CPG, descending drive, or behavior controller"]}
