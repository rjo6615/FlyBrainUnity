"""Windows entry point for the diagnosis-only M5D-4B 15-ms replay."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import traceback

import numpy as np

from malecns_backend import MaleCNSBrain, load_malecns
from .six_tibia import IsolatedTibiaDecoder, LEG_ORDER
from .tactile_contact import TactileContactConfig, TactileContactEncoder
from .tactile_motor_loop import ACTUATOR_INDICES, NEURAL_DT_MS, validated_interfaces, verify_locked_hashes
from .tactile_motor_loop_audit import _make_live, _joint_positions, _forces
from . import tactile_targeted_contact_calibration as contact
from .tactile_motor_boundary_diagnostic import (
    DURATION_MS, PIPELINE_STAGES, SEED, atomic_write, base_report, classify,
    compare_traces, semantic_digest,
)

DEFAULT_OUTPUT = Path(__file__).with_name("interface_output") / "tactile_motor_boundary_diagnostic.json"
ROOT = Path(__file__).resolve().parents[2]
M5D4 = ROOT / "malecns_backend/embodiment/interface_output/tactile_motor_loop.json"
M5D4A = ROOT / "malecns_backend/embodiment/interface_output/tactile_motor_equivalence_diagnostic.json"
M5D4_MANIFEST = {"run_status": "COMPLETE", "causal_classification": "PRE_MOTOR_EQUIVALENCE_FAILED",
    "protocol_configuration.duration_ms": 100, "protocol_configuration.seed": 1,
    "protocol_configuration.physical_timestep_s": 0.0001,
    "protocol_configuration.neural_timestep_ms": 0.5}
M5D4A_MANIFEST = {"run_status": "COMPLETE", "classification": "EXACT_REPEATABILITY_CONFIRMED",
    "protocol.duration_ms": 15.0, "protocol.seed": 1,
    "protocol.physics_timestep_s": 0.0001, "safety.neural_output_applied": False,
    "safety.applied_neural_output_sample_count": 0}


def verify_provenance() -> dict:
    prior = verify_locked_hashes()
    m5d4 = json.loads(M5D4.read_text(encoding="utf-8"))
    m5d4a = json.loads(M5D4A.read_text(encoding="utf-8"))
    return {"verified": True, "m5d2c_and_m5d3": prior,
        "m5d4_semantic_digest": semantic_digest(m5d4, M5D4_MANIFEST),
        "m5d4a_semantic_digest": semantic_digest(m5d4a, M5D4A_MANIFEST)}


def _run_condition(flygym, data, interfaces, apply_motor):
    sim, physics, obs, tarsus_id, surface_id = _make_live(flygym, interfaces)
    brain = MaleCNSBrain(data); brain.reset(SEED)
    encoder = TactileContactEncoder(config=TactileContactConfig(seed=SEED))
    decoders = {leg: IsolatedTibiaDecoder(interfaces[leg]) for leg in LEG_ORDER}
    for decoder in decoders.values(): decoder.reset(brain.spike_counts)
    commands = _joint_positions(obs); pending = set(); rows = []
    dt_ms = contact.DEFAULT_TIMESTEP_S * 1000; stride = int(round(NEURAL_DT_MS / dt_ms))
    for step in range(int(round(DURATION_MS / dt_ms)) + 1):
        time_ms = float(physics.data.time * 1000); measured = _joint_positions(obs)
        frame = encoder.encode(_forces(obs), time_ms, dt_ms)["LM"]
        pending.update(map(int, frame.generated_dense_indices)); stages = {}
        for leg in LEG_ORDER:
            index = ACTUATOR_INDICES[leg]; decoder = decoders[leg].decoder
            stages[leg] = {"measured_joint_position": float(measured[index]),
                "previous_target": decoder.previous_target,
                "base_hold_target": float(measured[index]),
                "raw_mapped_motor_spike_counts": 0, "motor_observer_state": {},
                "decoder_filtered_state": {}, "decoded_extensor_activation": 0.0,
                "decoded_flexor_activation": 0.0, "decoded_antagonist_signal": 0.0,
                "decoded_angular_offset": 0.0, "condition_application_flag": apply_motor,
                "requested_neural_contribution": 0.0, "gated_neural_contribution": 0.0,
                "candidate_target_before_clamp": float(measured[index]),
                "target_after_range_clamp": float(measured[index]),
                "target_before_slew_limiter": float(measured[index]),
                "target_after_slew_limiter": float(commands[index]),
                "final_target": float(commands[index]), "actual_mujoco_ctrl": None}
        neural_index = None
        if step and step % stride == 0:
            neural_index = step // stride; brain.clear_external_drive()
            candidates = tuple(sorted(pending)); pending.clear()
            if candidates: brain.set_external_drive(candidates, 1000.0 / brain.config.dt)
            brain.external_drive_withheld_indices = np.empty(0, np.intp); brain.step()
            for leg in LEG_ORDER:
                index = ACTUATOR_INDICES[leg]; wrapper = decoders[leg]
                previous = wrapper.decoder.previous_target
                observed, command = wrapper.update(brain.spike_counts, NEURAL_DT_MS,
                    measured[index], NEURAL_DT_MS / 1000, apply_neural_offset=apply_motor)
                gated = command.magnitude_clamped_output_rad if apply_motor else 0.0
                commands[index] = command.target_position_rad if apply_motor else measured[index]
                stages[leg].update({"previous_target": previous,
                    "raw_mapped_motor_spike_counts": int(sum(observed["increments"].values())),
                    "motor_observer_state": observed["neurons"],
                    "decoder_filtered_state": observed["filtered_hz"],
                    "decoded_extensor_activation": command.extensor_activation,
                    "decoded_flexor_activation": command.flexor_activation,
                    "decoded_antagonist_signal": command.antagonist_signal,
                    "decoded_angular_offset": command.magnitude_clamped_output_rad,
                    "requested_neural_contribution": command.magnitude_clamped_output_rad,
                    "gated_neural_contribution": gated,
                    "candidate_target_before_clamp": command.unclamped_position_rad,
                    "target_after_range_clamp": command.range_clamped_position_rad,
                    "target_before_slew_limiter": command.range_clamped_position_rad,
                    "target_after_slew_limiter": command.slew_clamped_position_rad,
                    "final_target": float(commands[index])})
        ctrl = np.asarray(physics.data.ctrl).copy()
        for leg, index in ACTUATOR_INDICES.items():
            stages[leg]["actual_mujoco_ctrl"] = float(ctrl[index]) if index < len(ctrl) else None
        pairs = contact._pairs(physics)
        row = {"time_ms": time_ms, "physical_step_index": step, "neural_step_index": neural_index,
            "condition_application_flag": apply_motor, "pipeline_by_leg": stages,
            "action_joints": commands.tolist(),
            "six_tibia_action": [float(commands[i]) for i in ACTUATOR_INDICES.values()],
            "adhesion": [0.0] * 6, "ctrl": ctrl.tolist(),
            "qacc": np.asarray(physics.data.qacc).tolist(), "qvel": np.asarray(physics.data.qvel).tolist(),
            "qpos": np.asarray(physics.data.qpos).tolist(),
            "contact_set": contact.contact_metadata(pairs, tarsus_id, surface_id),
            "contact_forces": _forces(obs).tolist()}
        # Flatten stages in exact leg order solely for generic exact comparison.
        for stage in PIPELINE_STAGES:
            row[stage] = [stages[leg][stage] for leg in LEG_ORDER]
        rows.append(row)
        if step == int(round(DURATION_MS / dt_ms)): break
        obs = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})[0]
    identities = {"simulation": id(sim), "physics_model": id(physics.model),
        "physics_data": id(physics.data), "brain": id(brain), "encoder": id(encoder),
        "commands": id(commands), **{f"decoder_{leg}": id(decoders[leg]) for leg in LEG_ORDER}}
    if getattr(sim, "close", None): sim.close()
    return rows, identities


def run_live() -> dict:
    provenance = verify_provenance(); flygym = importlib.import_module("flygym")
    interfaces = validated_interfaces(); data = load_malecns()
    enabled, enabled_ids = _run_condition(flygym, data, interfaces, True)
    disabled, disabled_ids = _run_condition(flygym, data, interfaces, False)
    comparison = compare_traces(enabled, disabled)
    original = json.loads(M5D4.read_text(encoding="utf-8"))
    reported = original["timing_milestones_ms"]["first_applied_neural_output"]
    report = base_report(); report.update(run_status="COMPLETE", reason=None, provenance=provenance,
        logical_condition_divergence=comparison["logical"],
        effective_physical_intervention=comparison["ctrl"], pipeline_comparisons=comparison,
        first_ctrl_divergence=comparison["ctrl"], first_qacc_divergence=comparison["qacc"],
        first_qvel_divergence=comparison["qvel"], first_qpos_divergence=comparison["qpos"],
        first_contact_divergence=comparison["contact"], first_force_divergence=comparison["force"])
    report["classification"] = classify(comparison, reported)
    report["mutable_state_audit"].update(live_object_identity_checked=True,
        object_ids={"enabled": enabled_ids, "disabled": disabled_ids},
        shared_mutable_state_found=bool(set(enabled_ids.values()) & set(disabled_ids.values())))
    ctrl, qacc, qvel, qpos = (comparison[x] for x in ("ctrl", "qacc", "qvel", "qpos"))
    times = [None if x is None else x["time_ms"] for x in (ctrl, qacc, qvel, qpos)]
    report["causal_ordering"] = {"established": all(x is not None for x in times) and times == sorted(times),
        "sequence": times}
    report["trajectories"] = {"enabled": enabled, "disabled": disabled}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--live", action="store_true")
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT); args = parser.parse_args(argv)
    report = base_report()
    if args.live:
        try: report = run_live()
        except (ImportError, ModuleNotFoundError) as error:
            report.update(run_status="UNAVAILABLE", reason=f"{type(error).__name__}: {error}")
        except Exception as error:
            report.update(run_status="FAILED", reason=f"{type(error).__name__}: {error}",
                          traceback=traceback.format_exc())
    atomic_write(args.json, report)
    print(f"M5D-4B {report['run_status']}: {report['classification']}"); print(f"wrote {args.json}")
    return 0 if report["run_status"] in ("COMPLETE", "NOT_RUN", "UNAVAILABLE") else 1


if __name__ == "__main__": raise SystemExit(main())
