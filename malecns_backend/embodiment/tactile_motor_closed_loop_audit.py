"""Canonical, single-attempt Windows entry point for M5D-4D."""
from __future__ import annotations
import argparse
from pathlib import Path
import traceback
from . import tactile_motor_matched_control_audit as preflight_runner
from .tactile_motor_closed_loop import (DURATION_MS, SEED, base_report, classify,
    validate_prefix, verify_m5d4c_lock)
from .tactile_motor_matched_control import atomic_write, _first_difference, FIELDS

DEFAULT_OUTPUT = Path(__file__).with_name("interface_output") / "tactile_motor_closed_loop_100ms.json"

def run_live(duration_ms=DURATION_MS, seed=SEED):
    if duration_ms != DURATION_MS or seed != SEED:
        raise ValueError("M5D-4D protocol is fixed at 100.0 ms and seed 1")
    # Reuse the locked M5D-4C condition runner and, critically, its imported
    # MatchedControlPipeline. The temporary duration changes observation only.
    verify_m5d4c_lock(); preflight_runner.verify_provenance()
    import importlib
    flygym = importlib.import_module("flygym")
    from malecns_backend import load_malecns
    interfaces = preflight_runner.validated_interfaces(); data = load_malecns()
    old = preflight_runner.DURATION_MS
    try:
        preflight_runner.DURATION_MS = DURATION_MS
        enabled = preflight_runner._run_condition(flygym, data, interfaces, True)
        disabled = preflight_runner._run_condition(flygym, data, interfaces, False)
    finally:
        preflight_runner.DURATION_MS = old
    return analyze(enabled, disabled)

def _milestone(rows, predicate):
    for row in rows:
        match = predicate(row)
        if match is not None:
            leg, value = match
            return {"observed": True, "time_ms": row["time_ms"],
                "physical_step": row["physical_step"], "neural_step": row["neural_step"],
                "leg": leg, "value": value}
    return {"observed": False, "time_ms": None, "physical_step": None,
        "neural_step": None, "leg": None, "value": None}

def _difference_event(enabled, disabled, fields, after=None, contact=False):
    pairs = [(a, b) for a, b in zip(enabled, disabled)
             if after is None or a["time_ms"] >= after]
    found = _first_difference([a for a, _ in pairs], [b for _, b in pairs], fields, contact=contact)
    event = {"observed": bool(found), "time_ms": None, "physical_step": None,
        "neural_step": None, "leg": None, "value": None}
    if found: event.update(found)
    return event

def analyze(enabled, disabled):
    """Reduce two full traces to compact, auditable boundary evidence."""
    report = base_report(); report["run_status"] = "COMPLETE"; report["reason"] = None
    earlier = preflight_runner.verify_provenance(); report["provenance"] = {
        **verify_m5d4c_lock(), "earlier_locks_verified": earlier["verified"], "earlier": earlier}
    mapped = _milestone(enabled, lambda r: next(((l, v) for l, v in r["motor_spikes"].items() if v), None))
    raw = _milestone(enabled, lambda r: next(((l, v) for l, v in r["raw_neural_contributions"].items() if v), None))
    admitted = _milestone(enabled, lambda r: next(((l, v) for l, v in r["admitted_neural_contributions"].items() if v), None))
    report.update(mapped_motor_evidence=mapped, raw_neural_contribution_evidence=raw,
        admitted_neural_contribution_evidence=admitted)
    intervention = admitted["time_ms"]
    pre_diffs = {name: _first_difference(enabled, disabled, fields, intervention,
        contact=name == "contact") for name, fields in FIELDS.items()}
    pre_equal = not any(pre_diffs.values())
    report["pre_intervention_equivalence"] = {"passed": pre_equal, "differences": pre_diffs,
        "before_ms": intervention}
    for group, key in (("action", "action_divergence"), ("ctrl", "ctrl_divergence"),
            ("qacc", "qacc_divergence"), ("qvel", "qvel_divergence"), ("qpos", "qpos_divergence")):
        report[key] = _difference_event(enabled, disabled, FIELDS[group], contact=False)
    force = _difference_event(enabled, disabled, FIELDS["force"])
    semantic = _difference_event(enabled, disabled, FIELDS["contact"], contact=True)
    proprio = min((report[k] for k in ("qvel_divergence", "qpos_divergence") if report[k]["observed"]),
        key=lambda x: x["time_ms"], default=report["physical_sensory_divergence"]["proprioceptive_physical"])
    report["physical_sensory_divergence"] = {"contact_force": force,
        "semantic_contact": semantic, "proprioceptive_physical": proprio}
    physical_times = [report[k]["time_ms"] for k in ("qacc_divergence", "qvel_divergence", "qpos_divergence") if report[k]["observed"]]
    physical = min(physical_times, default=None)
    sensory_after = min((x["time_ms"] for x in (force, semantic, proprio) if x["observed"]), default=None)
    sensory = _difference_event(enabled, disabled, FIELDS["sensory"], after=physical)
    report["modeled_sensory_encoding_divergence"] = sensory
    feedback_time = sensory["time_ms"] if sensory["observed"] else None
    report["post_feedback_cns_divergence"] = _difference_event(enabled, disabled, ("cns_state", "cns_spikes"), after=feedback_time) if feedback_time is not None else report["post_feedback_cns_divergence"]
    report["post_feedback_mapped_motor_divergence"] = _difference_event(enabled, disabled, ("motor_spikes",), after=feedback_time) if feedback_time is not None else report["post_feedback_mapped_motor_divergence"]
    report["contact_evidence"] = _milestone(enabled, lambda r: ("LM", r["contact_set"]) if r["contact_set"].get("target_contact") else None)
    report["tactile_transduction_evidence"] = _milestone(enabled, lambda r: ("LM", r["sensory_encoding"]["modeled_rate_hz"]) if r["sensory_encoding"]["modeled_rate_hz"] > 0 else None)
    report["tactile_delivery_evidence"] = _milestone(enabled, lambda r: ("LM", r["sensory_encoding"]["delivered"]) if r["sensory_encoding"]["delivered"] else None)
    observed = {"mapped": mapped["time_ms"], "raw": raw["time_ms"], "admitted": intervention,
        "action": report["action_divergence"]["time_ms"], "ctrl": report["ctrl_divergence"]["time_ms"], "physical": physical}
    report["m5d4c_prefix_validation"] = {"passed": False, "observed": observed}; report["m5d4c_prefix_validation"]["passed"] = validate_prefix(report)
    rng_pre = pre_diffs["sensory"] is None
    report["rng_parity"] = {"pre_feedback_exact": rng_pre, "random_stream_mismatch": not rng_pre}
    evidence = {"provenance": True, "pre_equal": pre_equal, "prefix": report["m5d4c_prefix_validation"]["passed"],
        "intervention": intervention is not None, "physical_before_intervention": physical is not None and physical < intervention,
        "rng_parity": rng_pre, "physical": physical is not None, "physical_sensory": sensory_after is not None,
        "sensory_encoding": sensory["observed"], "post_cns": report["post_feedback_cns_divergence"]["observed"],
        "post_motor": report["post_feedback_mapped_motor_divergence"]["observed"]}
    report["classification"] = classify(evidence)
    sequence = [report[k]["time_ms"] for k in ("contact_evidence", "tactile_transduction_evidence",
        "tactile_delivery_evidence", "mapped_motor_evidence", "raw_neural_contribution_evidence",
        "admitted_neural_contribution_evidence", "action_divergence", "ctrl_divergence",
        "qacc_divergence", "modeled_sensory_encoding_divergence", "post_feedback_cns_divergence",
        "post_feedback_mapped_motor_divergence")]
    values = [x for x in sequence if x is not None]
    report["causal_ordering"] = {"established": values == sorted(values), "sequence_ms": sequence}
    report["causal_milestones"] = {f"C{i}": (sequence[i] if i < len(sequence) else None) for i in range(15)}
    return report

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration-ms", type=float, default=DURATION_MS); parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT); args = parser.parse_args(argv)
    report = base_report()
    if args.live:
        try: report = run_live(args.duration_ms, args.seed)
        except Exception as error:
            report.update(run_status="FAILED", classification="UNRESOLVED_CAUSAL_FAILURE",
                reason=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
    atomic_write(args.json, report); print(f"M5D-4D {report['run_status']}: {report['classification']}")
    return 0 if report["run_status"] == "NOT_RUN" else 1

if __name__ == "__main__": raise SystemExit(main())
