"""CLI for staged M4C-3 candidate discovery and causal interventions."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import time

from .body import SixTibiaFlyGymBody
from .lh_lm_pathway import (CANONICAL_DURATION_MS, CANONICAL_SEED,
    LH_WITHHELD_LM_DELTA, LM_BASELINE_SPIKES, LM_TARGET_BASELINE, MAX_CANDIDATES,
    MAX_PATH_EDGES, SOURCE_LEG, TARGET_BODY_IDS, SpikeTimelineObserver,
    configure_transmission_withholding, discover_candidates, early_window_summary, make_groups)
from .six_tibia import LEG_ORDER, load_six_tibia_interfaces
from .six_tibia_causal import SixTibiaRuntime
from .six_tibia_perturbation import physics_error_types, summarize_run, validate_canonical_baseline


def _run_condition(body_ids, interfaces, data, brain_factory, body_factory,
                   duration_ms=CANONICAL_DURATION_MS, seed=CANONICAL_SEED,
                   observer=None, physics_errors=None):
    """One fresh run; catch only PhysicsError and always close the body."""
    brain = brain_factory(data); body = body_factory(interfaces); rows = []; failure = None
    started = time.perf_counter(); runtime = None
    try:
        runtime = SixTibiaRuntime(brain, body, interfaces, seed, True,
                                  diagnostic_observer=observer)
        configure_transmission_withholding(brain, body_ids)
        errors = physics_error_types() if physics_errors is None else physics_errors
        for millisecond in range(1, duration_ms + 1):
            try: rows.append(runtime.step(millisecond))
            except errors as exc:
                failure = exc; break
    finally:
        body.close()
    summary = summarize_run(rows, runtime, time.perf_counter() - started, duration_ms, failure)
    summary["withheld_transmission_body_ids"] = list(map(int, body_ids))
    return rows, runtime, summary


def run_candidate_discovery(*, interfaces=None, data=None, brain_factory=None, body_factory=None,
                            physics_errors=None):
    """Phase A only: canonical all-six activity followed by bounded graph analysis."""
    from malecns_backend import MaleCNSBrain, load_malecns
    interfaces = interfaces or load_six_tibia_interfaces(); data = data or load_malecns()
    brain_factory = brain_factory or MaleCNSBrain; body_factory = body_factory or SixTibiaFlyGymBody
    timeline = SpikeTimelineObserver()
    rows, runtime, baseline = _run_condition([], interfaces, data, brain_factory, body_factory,
                                              observer=timeline, physics_errors=physics_errors)
    _, valid = validate_canonical_baseline(baseline)
    if not valid: raise RuntimeError("BASELINE REPRODUCTION: FAIL; no candidates selected")
    candidates = discover_candidates(runtime.brain, interfaces[SOURCE_LEG].sensor.dense_indices,
                                      timeline.times)
    return {"milestone": "M4C-3", "phase": "A_CANDIDATE_DISCOVERY_ONLY", "seed": CANONICAL_SEED,
        "duration_ms": CANONICAL_DURATION_MS, "source": {"leg": SOURCE_LEG,
        "population": "LH chordotonal sensory", "body_ids": list(interfaces[SOURCE_LEG].sensor.body_ids)},
        "targets": list(TARGET_BODY_IDS), "max_path_edges": MAX_PATH_EDGES,
        "temporal_filter": {"cutoff_ms": 35.0, "semantics": "observed-active only; not causal"},
        "baseline": baseline, "candidates": [x.to_dict() for x in candidates],
        "shortlist_body_ids": [x.body_id for x in candidates[:MAX_CANDIDATES]],
        "groups": make_groups(candidates[:MAX_CANDIDATES]),
        "interpretation_guard": "Topology and temporal compatibility are observational, not causal."}


def _first_divergence(control, intervention, field):
    return next((a["time_ms"] for a, b in zip(intervention, control) if field(a) != field(b)), None)


def _physical_divergence(control, intervention):
    for a, b in zip(intervention, control):
        if any(abs(a["after"].angles_rad[leg] - b["after"].angles_rad[leg]) > 1e-12 for leg in LEG_ORDER):
            return a["time_ms"]
    return None


def _intervention_result(body_ids, control_rows, rows, runtime, summary, baseline):
    target_indices = [runtime.brain.data.dense_index(x) for x in TARGET_BODY_IDS]
    physical = _physical_divergence(control_rows, rows)
    summary["early_network_effect"] = early_window_summary(rows, target_indices,
        [runtime.brain.data.dense_index(x) for x in body_ids], physical)
    summary["early_network_effect"].update({
        "cns_divergence_ms": _first_divergence(control_rows, rows, lambda x: x["spiking_neuron_indices"]),
        "mapped_motor_divergence_ms": _first_divergence(control_rows, rows,
            lambda x: tuple(x["motor"][leg]["increments"] for leg in LEG_ORDER))})
    counts = Counter(i for row in rows for i in row["spiking_neuron_indices"])
    summary["full_closed_loop_effect"] = {"lm_mapped_motor_spikes": summary["motor"]["LM"]["selected_mapped_motor_spikes"],
        "lm_delta_from_34": summary["motor"]["LM"]["selected_mapped_motor_spikes"] - LM_BASELINE_SPIKES,
        "lm_targets": {str(body): {"spikes": counts[index], "delta_from_17": counts[index] - LM_TARGET_BASELINE[body]}
                       for body, index in zip(TARGET_BODY_IDS, target_indices)},
        "first_lm_mapped_motor_spike_ms": summary["motor"]["LM"]["first_mapped_motor_spike_ms"],
        "peak_decoded_lm_offset_rad": summary["motor"]["LM"]["peak_decoded_offset_rad"],
        "all_leg_mapped_motor_spikes": {leg: summary["motor"][leg]["selected_mapped_motor_spikes"] for leg in LEG_ORDER},
        "comparison_note": f"Whole LH sensory withholding has LM delta {LH_WITHHELD_LM_DELTA}; no mediation percentage is inferred."}
    early = summary["early_network_effect"]; full_delta = summary["full_closed_loop_effect"]["lm_delta_from_34"]
    labels = []
    control_early = early_window_summary(control_rows, target_indices, [], None)["lm_mapped_motor_spikes"]
    if early["lm_mapped_motor_spikes"] != control_early: labels.append("EARLY_LM_EFFECT")
    elif full_delta: labels.append("LATE_CLOSED_LOOP_EFFECT")
    else: labels.append("NO_DETECTABLE_LM_EFFECT")
    changed_legs = sum(summary["motor"][leg]["selected_mapped_motor_spikes"] != baseline["motor"][leg]["selected_mapped_motor_spikes"] for leg in LEG_ORDER)
    if changed_legs > 1: labels.append("BROAD_NETWORK_EFFECT")
    if not summary["completed"]: labels.append("PHYSICS_UNSTABLE")
    summary["interpretation_classes"] = labels
    return summary


def run_interventions(candidate_document, *, interfaces=None, data=None, brain_factory=None,
                      body_factory=None, physics_errors=None):
    """Phase B is explicit and consumes a previously inspected Phase-A document."""
    from malecns_backend import MaleCNSBrain, load_malecns
    interfaces = interfaces or load_six_tibia_interfaces(); data = data or load_malecns()
    brain_factory = brain_factory or MaleCNSBrain; body_factory = body_factory or SixTibiaFlyGymBody
    selected = list(map(int, candidate_document.get("selected_body_ids") or
                        candidate_document.get("shortlist_body_ids", ())))
    if not 1 <= len(selected) <= MAX_CANDIDATES: raise ValueError("Phase B requires 1-6 explicit candidate body IDs")
    control_rows, _, baseline = _run_condition([], interfaces, data, brain_factory, body_factory,
                                                physics_errors=physics_errors)
    _, valid = validate_canonical_baseline(baseline)
    if not valid: raise RuntimeError("BASELINE REPRODUCTION: FAIL; interventions were not run")
    runs = []
    for body_id in selected:
        rows, runtime, summary = _run_condition([body_id], interfaces, data, brain_factory,
                                                 body_factory, physics_errors=physics_errors)
        runs.append(_intervention_result([body_id], control_rows, rows, runtime, summary, baseline))
    return {"milestone": "M4C-3", "phase": "B_CAUSAL_TRANSMISSION_WITHHOLDING",
            "seed": CANONICAL_SEED, "duration_ms": CANONICAL_DURATION_MS,
            "baseline": baseline, "interventions": runs,
            "semantics": "counterfactual spikes retained; only outgoing transmission withheld"}


def print_candidates(result):
    print("LH -> LM CANDIDATES")
    print("body_id      type          sign    path    first_spike    target")
    for x in result["candidates"][:20]:
        target = ",".join(str(t) for t, key in zip(TARGET_BODY_IDS,
            ("directly_contacts_800911", "directly_contacts_801234")) if x[key]) or "indirect"
        print(f'{x["body_id"]:<12} {x["cell_type"]:<13} {x["sign"]:>4g}    {x["path_length_from_lh"]}       {str(x["first_canonical_spike_ms"]):<13} {target}')


def print_interventions(result):
    print("INTERVENTION              LM SPIKES    DELTA    EARLY EFFECT    STATUS")
    for run in result["interventions"]:
        full = run["full_closed_loop_effect"]; early = run["early_network_effect"]
        print(run["withheld_transmission_body_ids"], full["lm_mapped_motor_spikes"],
              full["lm_delta_from_34"], early["lm_mapped_motor_spikes"], run["run_status"])
        print("  800911:", full["lm_targets"]["800911"], "801234:", full["lm_targets"]["801234"])


def main(argv=None):
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--candidates", action="store_true")
    mode.add_argument("--interventions", type=Path, metavar="PHASE_A_JSON")
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args(argv)
    result = (run_candidate_discovery() if args.candidates else
              run_interventions(json.loads(args.interventions.read_text(encoding="utf-8"))))
    print_candidates(result) if args.candidates else print_interventions(result)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
