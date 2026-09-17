"""Headless Milestone 4C-1 observational pathway-dissection command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

if sys.platform != "win32":
    import resource

from .body import SixTibiaFlyGymBody
from .pathway_diagnostics import PathwayObserver, pathway_graph_report
from .six_tibia import LEG_ORDER, load_six_tibia_interfaces
from .six_tibia_causal import (CANONICAL_SEED, analyze_matched, ISOLATED_BASELINE,
                               run_matched_closed_control)


CANONICAL = {
    "LF": (584, 0, None, 0.), "LM": (1598, 34, 31.5, .2396206263827794),
    "LH": (2435, 0, None, 0.), "RF": (351, 0, None, 0.),
    "RM": (1690, 12, 49., .1794759502657556),
    "RH": (2029, 10, 24.5, .20141031339759963),
}
CANONICAL_CAUSAL = {"motor_spike": 25, "decoded_output": 25,
    "applied_output": 25, "physical_divergence": 25,
    "sensory_encoding_divergence": 26, "cns_divergence": 35,
    "mapped_motor_divergence": 49}


def validate_baseline(legs, causal_summary):
    """Strictly validate discrete outcomes and canonical causal timestamps."""
    checks = {}
    for leg, expected in CANONICAL.items():
        actual = legs[leg]
        checks[leg] = {"sensory_spikes": actual["sensory_spikes"] == expected[0],
            "motor_spikes": actual["selected_motor_spikes"] == expected[1],
            "first_motor": actual["first_motor_spike_ms"] == expected[2],
            "peak_offset": abs(actual["peak_decoded_offset_rad"] - expected[3]) <= 1e-12,
            "active_identity": actual["active"] == (expected[1] > 0)}
    causal_match = causal_summary == CANONICAL_CAUSAL
    return checks, causal_match, all(all(x.values()) for x in checks.values()) and causal_match


def _peak_rss():
    return (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform != "win32" else None)


def run_pathway_audit(duration_ms=500, seed=CANONICAL_SEED, *, interfaces=None, data=None,
                      brain_factory=None, body_factory=None, graph_analysis=True):
    """Re-run the canonical matched experiment with diagnostics on CLOSED only."""
    if duration_ms != 500: raise ValueError("canonical duration is fixed at 500 ms")
    from malecns_backend import MaleCNSBrain, load_malecns
    interfaces = interfaces or load_six_tibia_interfaces()
    data = data if data is not None else load_malecns()
    make_brain = brain_factory or (lambda d: MaleCNSBrain(d))
    make_body = body_factory or (lambda i: SixTibiaFlyGymBody(i))
    start = time.perf_counter()
    # Construct diagnostics before either runtime, then use the exact 4B-2
    # CLOSED/CONTROL constructor and execution loop.
    observer = PathwayObserver(interfaces)
    runs, runtimes = run_matched_closed_control(
        duration_ms, seed, interfaces, data, make_brain, make_body, observer)
    (closed, control), (closed_runtime, _) = runs, runtimes
    closed_brain = closed_runtime.brain
    causal = analyze_matched(closed, control, closed_runtime.events)
    neural = observer.report(closed_brain)
    graph = pathway_graph_report(closed_brain, interfaces, observer) if graph_analysis else {
        "status": "skipped by explicit test/diagnostic option"}
    legs = {}
    for leg in LEG_ORDER:
        interface = interfaces[leg]
        target_ids = [str(body_id) for p in interface.motor_populations for body_id in p.body_ids]
        records = [neural["motor_neurons"][body_id] for body_id in target_ids]
        motor_spikes = sum(sum(row["motor"][leg]["increments"].values()) for row in closed)
        peak = max(abs(row["actuation"][leg]["decoded_offset_rad"]) for row in closed)
        sensory = sum(row["sensory_increments"][leg] for row in closed)
        first = causal["per_leg"][leg]["first_mapped_motor_spike_ms"]
        closest = min((x["closest_to_threshold_mV"] for x in records), default=None)
        contributors = {x["body_id"] for record in records
                        for x in record["active_direct_presynaptic_contributors"]}
        legs[leg] = {"sensory_population_size": len(interface.sensor.dense_indices),
            "sensory_spikes": sensory, "selected_motor_population_size": len(target_ids),
            "selected_motor_spikes": motor_spikes, "first_motor_spike_ms": first,
            "closest_motor_threshold_margin_mV": closest,
            "peak_excitatory_input": max((x["input"]["peak_excitatory"] for x in records), default=0.),
            "peak_inhibitory_input": min((x["input"]["peak_inhibitory"] for x in records), default=0.),
            "peak_net_input": max((x["input"]["peak_net"] for x in records), key=abs, default=0.),
            "cumulative_excitatory_input": sum(x["input"]["excitatory"] for x in records),
            "cumulative_inhibitory_input": sum(x["input"]["inhibitory"] for x in records),
            "cumulative_net_input": sum(x["input"]["net"] for x in records),
            "active_direct_presynaptic_contributors": len(contributors),
            "earliest_direct_presynaptic_activity_ms": min(
                (x["first_spike_ms"] for record in records
                 for x in record["active_direct_presynaptic_contributors"]), default=None),
            "peak_decoded_offset_rad": peak,
            "active": motor_spikes > 0,
            "population_detail": [{"name": p.name, "role": p.function,
                "direction": p.direction, "body_ids": list(p.body_ids),
                "spike_count": sum(neural["motor_neurons"][str(i)]["spike_count"] for i in p.body_ids)}
                for p in interface.motor_populations],
            "simultaneous_vs_isolated": {"isolated_motor_spikes": ISOLATED_BASELINE[leg][0],
                "motor_spike_difference": motor_spikes - ISOLATED_BASELINE[leg][0],
                "isolated_first_motor_ms": ISOLATED_BASELINE[leg][1],
                "isolated_peak_offset_rad": ISOLATED_BASELINE[leg][2]},
            "isolated_detailed_pathway_diagnostics": "unavailable"}
    checks, causal_match, baseline_pass = validate_baseline(
        legs, causal["global_causal_order_ms"])
    return {"milestone": "4C-1", "classification": "OBSERVATIONAL_PATHWAY_DISSECTION",
        "seed": seed, "duration_ms": duration_ms, "baseline_reproduction": "PASS" if baseline_pass else "FAIL",
        "baseline_checks": checks, "causal_timestamps_match": causal_match,
        "causal_summary": causal["global_causal_order_ms"],
        "legs": legs, "motor_neuron_diagnostics": neural, "pathways": graph,
        "interpretation_guard": "Temporal compatibility and candidate convergence are not causal proof.",
        "performance": {"wall_seconds": time.perf_counter() - start,
            "peak_rss_platform_units": _peak_rss(),
            "storage": "target motor trajectories plus sparse active contributors; no dense adjacency/time-edge tensor"}}


def print_report(result):
    print("BASELINE REPRODUCTION:", result["baseline_reproduction"])
    print("LEG SENSORY MOTOR FIRST CLOSEST_MV PEAK_EXC PEAK_INH PEAK_NET CONTRIBUTORS FIRST_PRE PEAK_OFFSET")
    for leg in LEG_ORDER:
        x = result["legs"][leg]
        print(leg, x["sensory_spikes"], x["selected_motor_spikes"], x["first_motor_spike_ms"],
              x["closest_motor_threshold_margin_mV"], x["peak_excitatory_input"],
              x["peak_inhibitory_input"], x["peak_net_input"],
              x["active_direct_presynaptic_contributors"],
              x["earliest_direct_presynaptic_activity_ms"], x["peak_decoded_offset_rad"])
    print("CANDIDATE CROSS-LEG CONVERGENCE: observational details are in JSON; not causal proof")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path); parser.add_argument("--seed", type=int, default=CANONICAL_SEED)
    args = parser.parse_args(argv)
    result = run_pathway_audit(seed=args.seed); print_report(result)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
