"""Command-line audit for the Milestone 4C-2 perturbation matrix."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .six_tibia import LEG_ORDER
from .six_tibia_perturbation import run_perturbation_experiment


def print_report(result):
    if result.get("single_condition_diagnostic"):
        label, run = next(iter(result["runs"].items()))
        print("SINGLE CONDITION:", label)
        print("RUN STATUS:", run["run_status"])
        print("COMPLETED DURATION MS:", run["completed_duration_ms"])
        return
    print("BASELINE REPRODUCTION:", result["baseline_reproduction"])
    print("MOTOR SPIKE DELTA VS ALL-SIX")
    print("             " + " ".join(f"{leg:>5}" for leg in LEG_ORDER))
    for source in LEG_ORDER:
        cells = result["motor_spike_delta_matrix"][source]
        print(f"-{source:<10}" + " ".join(
            f"{str(cells[target]['value']) + ('*' if not cells[target]['complete'] else ''):>5}"
            for target in LEG_ORDER))
    if any(not result["motor_spike_delta_matrix"][source][target]["complete"]
           for source in LEG_ORDER for target in LEG_ORDER):
        print("* intervention terminated early due to physical instability; value covers valid interval only")
    for source in LEG_ORDER:
        run = result["runs"][f"-{source}"]; trace = run["causal_trace"]
        print(f"-{source}: {trace['classification']}")
        print("  own-leg motor delta:", run["own_leg_motor_delta"])
        print("  cross-leg motor deltas:", run["cross_leg_motor_deltas"])
        print("  first CNS divergence:", trace["direct_intervention"]["first_cns_divergence_ms"])
        print("  first motor divergence:", trace["direct_intervention"]["first_mapped_motor_divergence_ms"])
        print("  first physical divergence:", trace["direct_intervention"]["first_physical_divergence_ms"])
        print("  first returned sensory-feedback divergence:",
              trace["returned_physical_feedback"]["first_nonwithheld_sensory_encoding_divergence_ms"])


def main(argv=None):
    parser = argparse.ArgumentParser(); parser.add_argument("--json", type=Path)
    parser.add_argument("--condition", choices=("ALL-SIX",) + tuple(f"-{leg}" for leg in LEG_ORDER),
                        help="run exactly one fresh diagnostic condition (no retry)")
    args = parser.parse_args(argv)
    result = run_perturbation_experiment(progress=lambda message: print(message, file=sys.stderr),
                                         condition=args.condition)
    print_report(result)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
