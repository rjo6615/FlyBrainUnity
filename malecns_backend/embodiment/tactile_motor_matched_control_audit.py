"""Windows live runner for the M5D-4C 25-ms matched-control preflight."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import traceback

import numpy as np

from malecns_backend import MaleCNSBrain, load_malecns
from . import tactile_targeted_contact_calibration as contact
from .six_tibia import IsolatedTibiaDecoder, LEG_ORDER
from .tactile_contact import TactileContactConfig, TactileContactEncoder
from .tactile_motor_boundary_diagnostic import compare_contact_sets
from .tactile_motor_loop import ACTUATOR_INDICES, NEURAL_DT_MS, validated_interfaces, verify_locked_hashes
from .tactile_motor_loop_audit import _forces, _joint_positions, _make_live, _state_tuple
from .tactile_propagation import rng_digest
from .tactile_motor_matched_control import (
    DURATION_MS, SEED, MatchedControlPipeline, atomic_write, base_report,
    classify_traces, decode_raw, semantic_lock,
)

DEFAULT_OUTPUT = Path(__file__).with_name("interface_output") / "tactile_motor_matched_control_preflight.json"
ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = {
    "m5d4": ROOT / "malecns_backend/embodiment/interface_output/tactile_motor_loop.json",
    "m5d4a": ROOT / "malecns_backend/embodiment/interface_output/tactile_motor_equivalence_diagnostic.json",
    "m5d4b": ROOT / "malecns_backend/embodiment/interface_output/tactile_motor_boundary_diagnostic.json",
}
MANIFESTS = {
    "m5d4": {"run_status": "COMPLETE", "causal_classification": "PRE_MOTOR_EQUIVALENCE_FAILED",
        "protocol_configuration.duration_ms": 100, "protocol_configuration.seed": 1},
    "m5d4a": {"run_status": "COMPLETE", "classification": "EXACT_REPEATABILITY_CONFIRMED",
        "protocol.duration_ms": 15.0, "safety.neural_output_applied": False},
    "m5d4b": {"run_status": "COMPLETE", "classification": "EARLY_CONTROL_INTERVENTION_FOUND",
        "protocol.duration_ms": 15.0, "protocol.original_m5d4_branch_semantics": True},
}


def verify_provenance() -> dict:
    prior = verify_locked_hashes()
    digests = {name: semantic_lock(json.loads(path.read_text(encoding="utf-8")), MANIFESTS[name])
               for name, path in ARTIFACTS.items()}
    return {"verified": True, "m5d2c_and_m5d3": prior,
            **{f"{name}_semantic_digest": digest for name, digest in digests.items()}}


def _run_condition(flygym, data, interfaces, enabled):
    sim, physics, obs, tarsus_id, surface_id = _make_live(flygym, interfaces)
    brain = MaleCNSBrain(data); brain.reset(SEED)
    encoder = TactileContactEncoder(config=TactileContactConfig(seed=SEED))
    wrappers = {leg: IsolatedTibiaDecoder(interfaces[leg]) for leg in LEG_ORDER}
    for wrapper in wrappers.values(): wrapper.reset(brain.spike_counts)
    pipelines = {leg: MatchedControlPipeline(enabled, wrapper.decoder.safety)
                 for leg, wrapper in wrappers.items()}
    commands = _joint_positions(obs); pending = set(); rows = []
    dt_ms = contact.DEFAULT_TIMESTEP_S * 1000
    stride = int(round(NEURAL_DT_MS / dt_ms))
    for step in range(int(round(DURATION_MS / dt_ms)) + 1):
        time_ms = float(physics.data.time * 1000); measured = _joint_positions(obs)
        forces = _forces(obs); frame = encoder.encode(forces, time_ms, dt_ms)["LM"]
        generated = tuple(map(int, frame.generated_dense_indices)); pending.update(generated)
        motor_spikes = {leg: 0 for leg in LEG_ORDER}; raw = {leg: 0.0 for leg in LEG_ORDER}
        admitted = {leg: 0.0 for leg in LEG_ORDER}; observers = {}; decoder_states = {}
        baselines = {leg: float(measured[index]) for leg, index in ACTUATOR_INDICES.items()}
        previous = {leg: pipelines[leg].previous_physical_target for leg in LEG_ORDER}
        fired = (); delivered = (); neural_step = None
        if step and step % stride == 0:
            neural_step = step // stride; brain.clear_external_drive()
            candidates = tuple(sorted(pending)); pending.clear()
            if candidates: brain.set_external_drive(candidates, 1000.0 / brain.config.dt)
            brain.external_drive_withheld_indices = np.empty(0, np.intp)
            fired = tuple(map(int, brain.step())); delivered = tuple(map(int, brain._last_external_delivered))
            for leg in LEG_ORDER:
                wrapper = wrappers[leg]
                observed = wrapper.observer.update(brain.spike_counts, NEURAL_DT_MS)
                directional = wrapper.decoder.directional_rates(observed["filtered_hz"])
                decoded = decode_raw(wrapper.decoder, directional)
                result = pipelines[leg].update(measured[ACTUATOR_INDICES[leg]],
                                               decoded["raw_neural_contribution"],
                                               NEURAL_DT_MS / 1000)
                commands[ACTUATOR_INDICES[leg]] = result.actuator_command
                motor_spikes[leg] = int(sum(observed["increments"].values()))
                raw[leg] = result.raw_neural_contribution
                admitted[leg] = result.admitted_neural_contribution
                baselines[leg] = result.baseline_target
                previous[leg] = result.previous_physical_target
                observers[leg] = {"neurons": observed["neurons"],
                                  "filtered_hz": observed["filtered_hz"]}
                decoder_states[leg] = decoded
        metadata = contact.contact_metadata(contact._pairs(physics), tarsus_id, surface_id)
        row = {"time_ms": time_ms, "physical_step": step, "neural_step": neural_step,
            "measured_positions": {leg: float(measured[i]) for leg, i in ACTUATOR_INDICES.items()},
            "baseline_targets": baselines, "previous_physical_targets": previous,
            "raw_neural_contributions": raw, "admitted_neural_contributions": admitted,
            "observer_states": observers, "decoder_states": decoder_states,
            "motor_spikes": motor_spikes, "sensory_encoding": {"modeled_rate_hz": frame.modeled_rate_hz,
                "generated": generated, "delivered": delivered}, "rng_state": rng_digest(encoder.rng["LM"]),
            "cns_state": _state_tuple(brain), "cns_spikes": fired,
            "action_joints": commands.tolist(),
            "six_tibia_action": [float(commands[i]) for i in ACTUATOR_INDICES.values()],
            "adhesion": [0.0] * 6, "ctrl": np.asarray(physics.data.ctrl).tolist(),
            "qacc": np.asarray(physics.data.qacc).tolist(), "qvel": np.asarray(physics.data.qvel).tolist(),
            "qpos": np.asarray(physics.data.qpos).tolist(), "contact_forces": forces.tolist(),
            "contact_set": metadata}
        rows.append(row)
        if step == int(round(DURATION_MS / dt_ms)): break
        obs = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})[0]
    if getattr(sim, "close", None): sim.close()
    return rows


def _milestone(rows, predicate):
    for row in rows:
        match = predicate(row)
        if match:
            leg, value = match
            return {"time_ms": row["time_ms"], "physical_step": row["physical_step"],
                    "neural_step": row["neural_step"], "leg": leg, "value": value}
    return {"time_ms": None, "physical_step": None, "neural_step": None, "leg": None, "value": None}


def run_live(duration_ms=DURATION_MS, seed=SEED):
    if duration_ms != DURATION_MS or seed != SEED:
        raise ValueError("M5D-4C protocol is fixed at 25.0 ms and seed 1")
    provenance = verify_provenance()
    flygym = importlib.import_module("flygym"); interfaces = validated_interfaces(); data = load_malecns()
    enabled = _run_condition(flygym, data, interfaces, True)
    disabled = _run_condition(flygym, data, interfaces, False)
    admitted = _milestone(enabled, lambda r: next(((l, v) for l, v in r["admitted_neural_contributions"].items() if v != 0.0), None))
    raw = _milestone(enabled, lambda r: next(((l, v) for l, v in r["raw_neural_contributions"].items() if v != 0.0), None))
    spike = _milestone(enabled, lambda r: next(((l, v) for l, v in r["motor_spikes"].items() if v != 0), None))
    intervention_ms = admitted["time_ms"]
    classification, equivalence = classify_traces(enabled, disabled, intervention_ms)
    report = base_report(); report.update(run_status="COMPLETE", reason=None,
        classification=classification, provenance=provenance,
        pre_intervention_equivalence=equivalence,
        decoder_state_equivalence={"exactly_equal": not any(equivalence["differences"][x]
            for x in ("decoder", "baseline"))}, first_mapped_motor_spike=spike,
        first_raw_neural_contribution=raw,
        first_enabled_admitted_neural_contribution=admitted,
        first_raw_neural_contribution_ms=raw["time_ms"],
        first_enabled_admitted_neural_contribution_ms=admitted["time_ms"])
    # Keep live trajectories out of the artifact; record only first exact differences.
    from .tactile_motor_matched_control import _first_difference, FIELDS
    names = {"action": "first_action_divergence", "ctrl": "first_ctrl_divergence",
        "qacc": "first_qacc_divergence", "qvel": "first_qvel_divergence",
        "qpos": "first_qpos_divergence", "force": "first_force_divergence",
        "contact": "first_contact_divergence"}
    for group, key in names.items():
        found = _first_difference(enabled, disabled, FIELDS[group], contact=group == "contact")
        if found: report[key].update(found)
    report["first_action_divergence_ms"] = report["first_action_divergence"]["time_ms"]
    report["first_ctrl_divergence_ms"] = report["first_ctrl_divergence"]["time_ms"]
    report["first_physical_divergence_ms"] = min((report[key]["time_ms"] for key in
        ("first_qacc_divergence", "first_qvel_divergence", "first_qpos_divergence",
         "first_force_divergence", "first_contact_divergence")
        if report[key]["time_ms"] is not None), default=None)
    sequence = [report[x]["time_ms"] for x in ("first_enabled_admitted_neural_contribution",
        "first_action_divergence", "first_ctrl_divergence", "first_qacc_divergence",
        "first_qvel_divergence", "first_qpos_divergence")]
    observed = [x for x in sequence if x is not None]
    report["causal_ordering"] = {"established": classification == "PREFLIGHT_PASS",
        "sequence_ms": sequence,
        "physical_divergence_did_not_precede_intervention": bool(observed) and observed == sorted(observed)}
    for leg in LEG_ORDER:
        report["per_leg_summary"][leg].update(
            first_raw_neural_contribution_ms=next((r["time_ms"] for r in enabled if r["raw_neural_contributions"][leg] != 0), None),
            first_enabled_admitted_neural_contribution_ms=next((r["time_ms"] for r in enabled if r["admitted_neural_contributions"][leg] != 0), None),
            first_action_divergence_ms=next((a["time_ms"] for a, b in zip(enabled, disabled)
                if a["action_joints"][ACTUATOR_INDICES[leg]] != b["action_joints"][ACTUATOR_INDICES[leg]]), None))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration-ms", type=float, default=DURATION_MS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT); args = parser.parse_args(argv)
    report = base_report()
    if args.live:
        try: report = run_live(args.duration_ms, args.seed)
        except (ImportError, ModuleNotFoundError) as error:
            report.update(run_status="UNAVAILABLE", reason=f"{type(error).__name__}: {error}")
        except Exception as error:
            report.update(run_status="FAILED", classification="PHYSICS_FAILURE",
                          reason=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
    atomic_write(args.json, report)
    print(f"M5D-4C {report['run_status']}: {report['classification']}"); print(f"wrote {args.json}")
    return 0 if report["run_status"] in ("COMPLETE", "NOT_RUN", "UNAVAILABLE") else 1


if __name__ == "__main__": raise SystemExit(main())
