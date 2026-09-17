"""Six-tibia leave-one-out sensory-delivery perturbation (Milestone 4C-2).

The intervention is deliberately narrow: all six encoders run normally and
MaleCNS samples all six external spike candidates normally.  Candidate events
from one selected population are withheld only after sampling and immediately
before CNS delivery.  No anatomical or physical object is removed.
"""
from __future__ import annotations

import math
import importlib
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
PHYSICS_INVALID_STATE = "PHYSICS_INVALID_STATE"


def physics_error_types():
    """Resolve dm_control's narrow physics exception without requiring it for unit tests."""
    try:
        return (importlib.import_module("dm_control.rl.control").PhysicsError,)
    except ModuleNotFoundError:
        return ()


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


def motor_influence_matrix(baseline_counts, intervention_counts, run_metadata=None):
    """Return signed intervention-minus-control motor spike differences."""
    values = {source: {target: int(intervention_counts[source][target] - baseline_counts[source][target]
                                      if isinstance(baseline_counts.get(source), dict)
                                      else intervention_counts[source][target] - baseline_counts[target])
                       for target in LEG_ORDER} for source in LEG_ORDER}
    if run_metadata is None:
        return values
    return {source: {target: {"value": values[source][target],
                              "complete": run_metadata[source]["completed"],
                              "observation_duration_ms": run_metadata[source]["completed_duration_ms"]}
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


def _snapshot_dict(snapshot):
    if snapshot is None: return None
    values = ([*snapshot.angles_rad.values(), *snapshot.velocities_rad_s.values(),
               *getattr(snapshot, "body_position_m", ()), *getattr(snapshot, "body_orientation", ())])
    return {"simulation_time_ms": float(snapshot.time_s * 1000),
            "tibia_angles_rad": {leg: float(snapshot.angles_rad[leg]) for leg in LEG_ORDER},
            "tibia_velocities_rad_s": {leg: float(snapshot.velocities_rad_s[leg]) for leg in LEG_ORDER},
            "body_position_m": list(getattr(snapshot, "body_position_m", ())),
            "body_orientation": list(getattr(snapshot, "body_orientation", ())),
            "all_values_finite": bool(np.isfinite(values).all())}


def summarize_run(rows, runtime, wall_seconds, requested_duration_ms=CANONICAL_DURATION_MS,
                  failure=None):
    sensors = set(i for leg in LEG_ORDER for i in runtime.interfaces[leg].sensor.dense_indices)
    fired = [set(map(int, row["spiking_neuron_indices"])) for row in rows]
    all_fired = set().union(*fired) if fired else set()
    nonsensory = [indices - sensors for indices in fired]
    completed = failure is None
    completed_ms = rows[-1]["time_ms"] if rows else 0
    checkpoints = {}
    for checkpoint in SAMPLE_TIMES_MS:
        reached = next((row for row in rows if row["time_ms"] == checkpoint), None)
        checkpoints[str(checkpoint)] = (None if reached is None else {
            "cns_spikes": int(sum(row["cns_spike_increment"] for row in rows
                                  if row["time_ms"] <= checkpoint)),
            "motor_spikes": {leg: int(sum(sum(row["motor"][leg]["increments"].values())
                                               for row in rows if row["time_ms"] <= checkpoint))
                             for leg in LEG_ORDER}})
    last = rows[-1] if rows else None
    result = {"withheld_sensory_population": runtime.withheld_sensory,
        "completed": completed, "physically_stable_through_requested_duration": completed,
        "requested_duration_ms": requested_duration_ms, "completed_duration_ms": completed_ms,
        "last_successful_control_step": completed_ms,
        "last_successful_simulation_time_ms": (float(last["after"].time_s * 1000) if last else None),
        "termination_reason": None if completed else PHYSICS_INVALID_STATE,
        "run_status": "COMPLETE" if completed else "PHYSICS_UNSTABLE",
        "metrics_scope": {"partial": not completed, "observation_duration_ms": completed_ms},
        "checkpoints": checkpoints,
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
            "real_time_factor": (completed_ms / 1000) / wall_seconds if wall_seconds else None,
            "peak_rss_platform_units": _peak_rss()},
        "last_valid_physical_state": _snapshot_dict(last["after"] if last else None),
        "last_valid_actuator_targets_rad": ({leg: float(last["actuation"][leg]["final_target_rad"])
                                              for leg in LEG_ORDER} if last else None),
        "last_valid_decoded_offsets_rad": ({leg: float(last["actuation"][leg]["decoded_offset_rad"])
                                             for leg in LEG_ORDER} if last else None),
        "failed_step_attempt": None,
        "mujoco_dof_39_mapping": "UNRESOLVED"}
    if failure is not None:
        result.update({"exception_type": type(failure).__name__, "exception_message": str(failure),
                       "mujoco_warning": ("mjWARN_BADQACC" if "mjWARN_BADQACC" in str(failure) else None)})
        attempt = getattr(runtime, "last_step_attempt", None)
        if attempt:
            result["failed_step_attempt"] = {"control_time_ms": attempt["time_ms"],
                "pre_step_physical_state": _snapshot_dict(attempt["before"]),
                "actuator_targets_rad": {leg: float(attempt["actuation"][leg]["final_target_rad"]) for leg in LEG_ORDER},
                "decoded_offsets_rad": {leg: float(attempt["actuation"][leg]["decoded_offset_rad"]) for leg in LEG_ORDER}}
    else:
        result.update({"exception_type": None, "exception_message": None, "mujoco_warning": None})
    return result


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
        "angle_differences_rad": {str(t): ({leg: float(by_time[t][i]) for i, leg in enumerate(LEG_ORDER)}
                                             if t in by_time else None) for t in SAMPLE_TIMES_MS},
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


def _run_condition(label, withheld, duration_ms, seed, interfaces, data, make_brain, make_body,
                   physics_errors=None):
    """Construct and run one fresh condition; never retries."""
    brain = make_brain(data); body = make_body(interfaces); runtime = None; rows = []
    started = time.perf_counter(); failure = None
    errors = physics_error_types() if physics_errors is None else physics_errors
    try:
        runtime = SixTibiaRuntime(brain, body, interfaces, seed, True, withheld_sensory=withheld)
        for t in range(1, duration_ms + 1):
            try:
                rows.append(runtime.step(t))
            except errors as exc:
                failure = exc
                break
    finally:
        body.close()
    summary = summarize_run(rows, runtime, time.perf_counter() - started, duration_ms, failure)
    summary["condition"] = label
    return rows, runtime, summary


def run_perturbation_experiment(duration_ms=CANONICAL_DURATION_MS, seed=CANONICAL_SEED, *,
                                interfaces=None, data=None, brain_factory=None, body_factory=None,
                                progress=None, condition=None, physics_errors=None):
    """Run one all-six baseline followed by six fresh leave-one-out runs."""
    if duration_ms != CANONICAL_DURATION_MS: raise ValueError("canonical duration is fixed at 500 ms")
    if seed != CANONICAL_SEED: raise ValueError("M4C-2 canonical seed is fixed at 1")
    from malecns_backend import MaleCNSBrain, load_malecns
    interfaces = interfaces or load_six_tibia_interfaces(); data = data if data is not None else load_malecns()
    make_brain = brain_factory or MaleCNSBrain; make_body = body_factory or SixTibiaFlyGymBody
    rows_by_run = {}; summaries = {}; runtimes = {}; total_start = time.perf_counter()
    conditions = (("ALL SIX", None),) + tuple((f"-{leg}", leg) for leg in LEG_ORDER)
    if condition is not None:
        normalized = "ALL SIX" if condition in ("ALL-SIX", "ALL SIX") else condition
        matches = tuple(item for item in conditions if item[0] == normalized)
        if not matches: raise ValueError(f"unknown condition: {condition}")
        conditions = matches
    for ordinal, (label, withheld) in enumerate(conditions, 1):
        if progress: progress(f"[{ordinal}/{len(conditions)}] {label}")
        rows, runtime, summary = _run_condition(label, withheld, duration_ms, seed, interfaces,
            data, make_brain, make_body, physics_errors)
        rows_by_run[label] = rows; runtimes[label] = runtime
        summaries[label] = summary
        if withheld is None:
            checks, passed = validate_canonical_baseline(summaries[label])
            if not passed: raise RuntimeError("BASELINE REPRODUCTION: FAIL; interventions were not run")
    if condition is not None:
        return {"milestone": "4C-2", "condition": condition, "seed": seed,
                "duration_ms": duration_ms, "runs": summaries,
                "performance": {"total_wall_seconds": time.perf_counter() - total_start,
                                "run_count": 1}, "single_condition_diagnostic": True}
    baseline = summaries["ALL SIX"]
    for leg in LEG_ORDER:
        observed = summaries[f"-{leg}"]["completed_duration_ms"]
        matched_baseline = summarize_run(rows_by_run["ALL SIX"][:observed], runtimes["ALL SIX"], 0,
                                         observed)
        compare_intervention(rows_by_run["ALL SIX"][:observed], rows_by_run[f"-{leg}"], matched_baseline,
                             summaries[f"-{leg}"], leg, runtimes[f"-{leg}"].brain)
        summaries[f"-{leg}"]["causal_trace"]["observed_before_termination"] = not summaries[f"-{leg}"]["completed"]
    matrix = motor_influence_matrix(
        {source: {leg: sum(sum(row["motor"][leg]["increments"].values())
                           for row in rows_by_run["ALL SIX"][:summaries[f'-{source}']["completed_duration_ms"]])
                  for leg in LEG_ORDER} for source in LEG_ORDER},
        {source: {target: summaries[f"-{source}"]["motor"][target]["selected_mapped_motor_spikes"]
                  for target in LEG_ORDER} for source in LEG_ORDER},
        {source: summaries[f"-{source}"] for source in LEG_ORDER})
    checks, _ = validate_canonical_baseline(baseline)
    return {"milestone": "4C-2", "condition": "500 ms seed-1 modeled embodiment",
        "seed": seed, "duration_ms": duration_ms, "baseline_reproduction": "PASS",
        "baseline_checks": checks, "runs": summaries, "motor_spike_delta_matrix": matrix,
        "performance": {"total_wall_seconds": time.perf_counter() - total_start,
            "run_count": 7},
        "scientific_safeguards": ["sensory delivery withholding only", "common random numbers",
            "physical legs retained", "motor systems retained", "connectome retained",
            "model constants unchanged", "no gait, CPG, descending drive, or behavior controller"]}
