"""CLI for the M5D-3 matched physical-tactile MaleCNS audit."""
from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import tempfile

import numpy as np

from malecns_backend import MaleCNSBrain, load_malecns
from . import tactile_targeted_contact_calibration as physical
from .tactile_contact import TactileContactConfig, TactileContactEncoder
from .tactile_propagation import (
    CONTACT_FORCE_ROW, DEFAULT_DURATION_MS, DEFAULT_NEURAL_DT_MS, LEG,
    base_report, classify_causal, downstream_indices, motor_populations,
    physical_match, rng_digest, serialized_report, shortest_directed_distances,
    tactile_population,
)

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "interface_output" / "tactile_propagation.json"


def _forces(sample):
    values = np.zeros((36, 3), dtype=np.float64)
    values[CONTACT_FORCE_ROW] = sample["raw_tarsus5_vector"]
    return values


def _trace(result):
    qpos = result["pose_proof"]["qpos_before"]
    return [{"simulation_time_s": row["simulation_time_s"],
             "force_magnitude": row["magnitude"],
             "selected_pair_present": row["selected_pair_present"], "qpos": qpos}
            for row in result["samples"]]


def _run_neural(samples, data, *, enabled, seed):
    """Replay physical samples; withhold only at the external-drive boundary."""
    population = tactile_population()
    tactile = set(population.dense_indices)
    brain = MaleCNSBrain(data); brain.reset(seed)
    encoder = TactileContactEncoder(config=TactileContactConfig(seed=seed))
    dt_physical_ms = physical.DEFAULT_TIMESTEP_S * 1000
    stride = round(DEFAULT_NEURAL_DT_MS / dt_physical_ms)
    if not np.isclose(stride * dt_physical_ms, DEFAULT_NEURAL_DT_MS):
        raise RuntimeError("physics and neural timesteps are not commensurate")
    candidate_events = []; delivered_events = []; spike_events = []
    snapshots = []; checkpoints = []; pending = set()
    first_rate = first_candidate = first_delivered = None
    for number, sample in enumerate(samples):
        time_ms = float(sample["simulation_time_s"] * 1000)
        frame = encoder.encode(_forces(sample), time_ms, dt_physical_ms)[LEG]
        if frame.modeled_rate_hz > 0 and first_rate is None: first_rate = time_ms
        for index in frame.generated_dense_indices:
            candidate_events.append((time_ms, int(index))); pending.add(int(index))
            if first_candidate is None: first_candidate = time_ms
        checkpoints.append(rng_digest(encoder.rng[LEG]))
        if (number + 1) % stride or not number: continue
        brain.clear_external_drive()
        candidates = tuple(sorted(pending)); pending.clear()
        if candidates: brain.set_external_drive(candidates, 1000 / brain.config.dt)
        brain.external_drive_withheld_indices = (np.empty(0, np.intp) if enabled else
                                                   np.asarray(candidates, np.intp))
        fired = tuple(map(int, brain.step()))
        actually_delivered = tuple(map(int, brain._last_external_delivered))
        for index in actually_delivered:
            delivered_events.append((brain.time_ms, index))
            if first_delivered is None: first_delivered = brain.time_ms
        spike_events.extend((brain.time_ms, index) for index in fired)
        snapshots.append({"time_ms": brain.time_ms, "v": brain.v.copy(),
                          "g_exc": brain.g_exc.copy(), "g_inh": brain.g_inh.copy(),
                          "counts": brain.spike_counts.copy(), "spikes": fired})
    spikers = {index for _, index in spike_events}
    non_tactile_events = [(time, index) for time, index in spike_events if index not in tactile]
    return {"brain": brain, "candidates": candidate_events, "delivered": delivered_events,
            "spikes": spike_events, "non_tactile_spikes": non_tactile_events,
            "snapshots": snapshots, "checkpoints": checkpoints,
            "first_rate": first_rate, "first_candidate": first_candidate,
            "first_delivered": first_delivered,
            "summary": {"candidate_tactile_spikes": len(candidate_events),
              "delivered_tactile_spikes": len(delivered_events),
              "total_malecns_spikes": len(spike_events), "distinct_spiking_neurons": len(spikers),
              "non_tactile_cns_spikes": len(non_tactile_events),
              "distinct_non_tactile_cns_neurons": len({x[1] for x in non_tactile_events})}}


def _analyze(enabled, disabled, data):
    tactile = set(tactile_population().dense_indices)
    try:
        motors = motor_populations()
        motor_observation = {"result": "AVAILABLE", "source":
          "M4A six_leg_map.json population_inventory.leg_motor"}
    except Exception as error:
        # This observer is optional post-hoc evidence.  Fail closed for P7,
        # while preserving independently valid non-tactile propagation/P6.
        motors = {}
        motor_observation = {"result": "ERROR", "error_type": type(error).__name__,
                             "reason": str(error)}
    motor_union = set().union(*map(set, motors.values())) if motors else set()
    first_state = first_non = first_spike = first_motor = None; differing = set()
    for a, b in zip(enabled["snapshots"], disabled["snapshots"]):
        state = ((a["v"] != b["v"]) | (a["g_exc"] != b["g_exc"]) |
                 (a["g_inh"] != b["g_inh"]))
        indices = set(map(int, np.flatnonzero(state)))
        if indices and first_state is None: first_state = a["time_ms"]
        outside = indices - tactile
        if outside and first_non is None:
            first_non = a["time_ms"]; differing.update(outside)
        ca, cb = a["counts"], b["counts"]
        spike_diff = set(map(int, np.flatnonzero(ca != cb))) - tactile
        if spike_diff and first_spike is None: first_spike = a["time_ms"]
        if (spike_diff & motor_union) and first_motor is None: first_motor = a["time_ms"]
    first_indices = sorted(differing)[:25]
    distance = shortest_directed_distances(data.row_ptr, data.target_indices,
                                           tactile, first_indices)
    rows = [{"dense_index": i, "body_id": int(data.body_ids[i]),
             "type": str(data.types[i]),
             "shortest_directed_anatomical_distance": distance[i],
             "spike_count_differed": bool(enabled["brain"].spike_counts[i] != disabled["brain"].spike_counts[i])}
            for i in first_indices]
    motor_details = []
    for name, indices in motors.items():
        delta = enabled["brain"].spike_counts[list(indices)].astype(np.int64) - disabled["brain"].spike_counts[list(indices)]
        if np.any(delta): motor_details.append({"population": name, "spike_count_difference": int(delta.sum())})
    return {"first_state": first_state, "first_non": first_non, "first_spike": first_spike,
            "first_motor": first_motor, "rows": rows, "motor_details": motor_details,
            "state_diverged": first_non is not None, "spikes_diverged": first_spike is not None,
            "motor_diverged": first_motor is not None,
            "motor_observation": motor_observation}


def run_live(duration_ms=DEFAULT_DURATION_MS, seed=1):
    flygym = importlib.import_module("flygym")
    duration_s = duration_ms / 1000
    physical_runs = [physical._run_condition(flygym, LEG, duration_s,
                                              physical.DEFAULT_TIMESTEP_S, contact=True)
                     for _ in range(2)]
    match = physical_match(_trace(physical_runs[0]), _trace(physical_runs[1]))
    data = load_malecns()
    enabled = _run_neural(physical_runs[0]["samples"], data, enabled=True, seed=seed)
    disabled = _run_neural(physical_runs[1]["samples"], data, enabled=False, seed=seed)
    parity = (enabled["candidates"] == disabled["candidates"] and
              enabled["checkpoints"] == disabled["checkpoints"])
    analysis = _analyze(enabled, disabled, data)
    verified = all(any(s["selected_pair_present"] for s in run["samples"])
                   for run in physical_runs)
    correspondence = all(any(s["magnitude"] > physical.ENGINEERING_THRESHOLD
                             for s in run["samples"] if s["selected_pair_present"])
                         for run in physical_runs)
    classification = ("PHYSICAL_MATCH_FAILED" if not match["matched"] else classify_causal(
        physical_contact=verified, sensor_correspondence=correspondence,
        candidate_count=len(enabled["candidates"]), delivered_count=len(enabled["delivered"]),
        non_tactile_state_diverged=analysis["state_diverged"],
        non_tactile_spikes_diverged=analysis["spikes_diverged"],
        mapped_motor_diverged=analysis["motor_diverged"],
        mapped_motor_observation_valid=analysis["motor_observation"]["result"] == "AVAILABLE"))
    report = base_report(duration_ms, seed); report.update(run_status="COMPLETE")
    report["reason"] = None
    report["physical_contact_verification"]["verified"] = verified
    report["physical_match_verification"] = match
    report["rng_parity_checkpoints"] = {"parity": parity,
      "enabled": enabled["checkpoints"], "disabled": disabled["checkpoints"]}
    report["tactile_candidate_events"] = {"count": len(enabled["candidates"]), "events": enabled["candidates"]}
    report["tactile_delivered_events"] = {"enabled_count": len(enabled["delivered"]),
      "disabled_count": len(disabled["delivered"]), "enabled_events": enabled["delivered"]}
    report["enabled_neural_summary"] = enabled["summary"]
    report["disabled_neural_summary"] = disabled["summary"]
    report["non_tactile_cns_divergence_summary"] = {k: analysis[k] for k in
      ("first_state", "first_non", "first_spike", "state_diverged", "spikes_diverged")}
    report["first_differing_neurons"] = analysis["rows"]
    report["anatomical_context"] = {"neurons": analysis["rows"],
      "warning": "directed paths are anatomical context, not proof of dynamic causality"}
    report["mapped_motor_observational_summary"] = {"motor_output_decoded": False,
      "motor_output_applied": False, "first_divergence_ms": analysis["first_motor"],
      "differing_populations": analysis["motor_details"], **analysis["motor_observation"]}
    report["causal_classification"] = classification
    milestones = report["timing_milestones_ms"]
    for key, predicate in (("first_mujoco_contact", lambda s:s["selected_pair_present"]),
                           ("first_nonzero_force", lambda s:s["magnitude"] > physical.ENGINEERING_THRESHOLD)):
        milestones[key] = next((s["simulation_time_s"]*1000 for s in physical_runs[0]["samples"] if predicate(s)), None)
    milestones.update(first_modeled_rate=enabled["first_rate"], first_candidate_spike=enabled["first_candidate"],
      first_delivered_spike=enabled["first_delivered"], first_neural_state_divergence=analysis["first_state"],
      first_non_tactile_divergence=analysis["first_non"], first_non_tactile_spike_divergence=analysis["first_spike"],
      first_mapped_motor_divergence=analysis["first_motor"])
    return report


def _write_report_atomic(path: Path, report) -> None:
    """Replace a report only after a complete strict-JSON file is durable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp",
                                         delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(serialized_report(report))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration-ms", type=int, default=DEFAULT_DURATION_MS)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if args.duration_ms <= 0: parser.error("--duration-ms must be positive")
    report = run_live(args.duration_ms, args.seed) if args.live else base_report(args.duration_ms, args.seed)
    _write_report_atomic(args.json, report)
    print(args.json)


if __name__ == "__main__": main()
