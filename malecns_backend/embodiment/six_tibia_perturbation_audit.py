"""Command-line audit for the Milestone 4C-2 perturbation matrix."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .six_tibia import LEG_ORDER
from .six_tibia_perturbation import run_perturbation_experiment


def print_report(result):
    print("BASELINE REPRODUCTION:", result["baseline_reproduction"])
    print("MOTOR SPIKE DELTA VS ALL-SIX")
    print("             " + " ".join(f"{leg:>5}" for leg in LEG_ORDER))
    for source in LEG_ORDER:
        print(f"-{source:<10}" + " ".join(f"{result['motor_spike_delta_matrix'][source][target]:5d}" for target in LEG_ORDER))
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
    args = parser.parse_args(argv)
    result = run_perturbation_experiment(progress=lambda message: print(message, file=sys.stderr))
    print_report(result)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
