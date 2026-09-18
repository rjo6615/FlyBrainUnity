"""Windows live runner for M5D-4A pre-motor physical equivalence.

Every run uses a fresh FlyGym simulation, encoder, MaleCNS, decoder set and
RNG.  Neural motor output is decoded for observation but is unconditionally
blocked from ``sim.step`` in every condition.
"""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import traceback

import numpy as np

from malecns_backend import MaleCNSBrain, load_malecns
from .six_tibia import IsolatedTibiaDecoder, LEG_ORDER
from .tactile_contact import TactileContactConfig, TactileContactEncoder
from .tactile_motor_loop import ACTUATOR_INDICES, CONTACT_FORCE_ROW, NEURAL_DT_MS, validated_interfaces
from .tactile_propagation import rng_digest
from . import tactile_targeted_contact_calibration as contact
from .tactile_motor_equivalence_diagnostic import (
    DURATION_MS, SEED, TIMESTEP_S, atomic_write_report, base_report, classify,
    compare_initialization, compare_trajectories,
)

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "interface_output" / "tactile_motor_equivalence_diagnostic.json"


def _name(model, kind, index):
    method = getattr(model, "id2name", None)
    if method:
        for args in ((index, kind), (kind, index)):
            try:
                value = method(*args)
                if value is not None: return str(value)
            except (TypeError, ValueError, KeyError):
                pass
    try:
        mujoco = importlib.import_module("mujoco")
        enum = getattr(mujoco.mjtObj, "mjOBJ_" + kind.upper())
        return mujoco.mj_id2name(getattr(model, "ptr", model), enum, index)
    except (ImportError, AttributeError, ValueError):
        return None


def _array(owner, name):
    value = getattr(owner, name, None)
    return None if value is None else np.asarray(value).tolist()


def _model_snapshot(model, data, surface_id):
    scalar = ("nq", "nv", "nu", "na", "nbody", "njnt", "ngeom")
    arrays = ("body_mass", "body_inertia", "jnt_type", "jnt_axis", "jnt_range",
              "dof_damping", "jnt_stiffness", "actuator_gainprm", "actuator_biasprm",
              "actuator_dynprm", "actuator_ctrlrange", "geom_type", "geom_size",
              "geom_pos", "geom_quat", "geom_friction", "geom_solref", "geom_solimp")
    option = getattr(model, "opt")
    model_values = {name: int(getattr(model, name)) for name in scalar}
    model_values["nactuator"] = int(model.nu)
    model_values.update({name: _array(model, name) for name in arrays})
    model_values["gravity"] = _array(option, "gravity")
    model_values["solver"] = {name: (getattr(option, name, None).item()
                              if isinstance(getattr(option, name, None), np.generic)
                              else getattr(option, name, None)) for name in
                              ("timestep", "solver", "integrator", "iterations", "ls_iterations",
                               "tolerance", "noslip_iterations")}
    state = {name: _array(data, name) for name in
             ("qpos", "qvel", "qacc", "act", "ctrl", "mocap_pos", "mocap_quat", "userdata")}
    state["ncon_at_reset"] = int(data.ncon)
    surface = {"geom_id": surface_id, "name": _name(model, "geom", surface_id)}
    for key in ("geom_type", "geom_size", "geom_pos", "geom_quat", "geom_friction",
                "geom_solref", "geom_solimp"):
        value = getattr(model, key, None)
        surface[key] = None if value is None else np.asarray(value[surface_id]).tolist()
    return {"model": model_values, "state": state, "surface": surface}


def _make_live(flygym):
    placements = [f"{leg}{segment}" for leg in contact.LEGS for segment in
                  ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")]
    fly = flygym.Fly(enable_adhesion=False, control="position", contact_sensor_placements=placements)
    simulation = getattr(flygym, "SingleFlySimulation", None) or importlib.import_module(
        "flygym.simulation").SingleFlySimulation
    sim = simulation(fly=fly, arena=contact._make_arena(flygym), cameras=[], timestep=TIMESTEP_S)
    reset = sim.reset(); obs = reset[0] if isinstance(reset, tuple) else reset
    physics = contact._physics(sim)
    tarsus_id, _ = contact.resolve_exact_geom(physics.model, "LMTarsus5")
    surface_id, _ = contact.resolve_exact_geom(physics.model, contact.SURFACE_NAME)
    qpos = np.asarray(physics.data.qpos).copy()
    tarsus_pos = np.asarray(physics.data.geom_xpos[tarsus_id]).copy()
    radius = float(np.asarray(physics.model.geom_rbound)[tarsus_id])
    np.asarray(physics.model.geom_pos)[surface_id] = contact.surface_position(tarsus_pos, radius, contact=True)
    contact._forward(physics)
    if not np.array_equal(qpos, physics.data.qpos):
        raise RuntimeError("surface placement changed initial qpos")
    if getattr(sim, "get_observation", None): obs = sim.get_observation()
    return sim, physics, obs, tarsus_id, surface_id


def _joint_positions(obs):
    values = np.asarray(obs["joints"], dtype=np.float64)
    return (values[0] if values.ndim == 2 else values).copy()


def _resolution(model):
    qpos = {}; qvel = {}; qacc = {}
    for joint in range(int(model.njnt)):
        start = int(model.jnt_qposadr[joint]); end = int(model.nq)
        if joint + 1 < int(model.njnt): end = int(model.jnt_qposadr[joint + 1])
        body = int(model.jnt_bodyid[joint]); info = {"joint_id": joint,
            "joint_name": _name(model, "joint", joint), "body_id": body,
            "body_name": _name(model, "body", body)}
        for index in range(start, end): qpos[str(index)] = {**info, "component": index - start}
    for dof in range(int(model.nv)):
        joint = int(model.dof_jntid[dof]); body = int(model.jnt_bodyid[joint])
        info = {"dof": dof, "joint_id": joint, "joint_name": _name(model, "joint", joint),
                "body_id": body, "body_name": _name(model, "body", body)}
        qvel[str(dof)] = info; qacc[str(dof)] = info
    ctrl = {str(i): {"actuator_index": i, "actuator_name": _name(model, "actuator", i),
                     "six_tibia_actuator": i in ACTUATOR_INDICES.values(),
                     "leg": next((leg for leg, value in ACTUATOR_INDICES.items() if value == i), None)}
            for i in range(int(model.nu))}
    return {"qpos": qpos, "qvel": qvel, "qacc": qacc, "ctrl": ctrl}


def _contacts(physics, tarsus_id, surface_id):
    model, data = physics.model, physics.data; all_contacts = []; selected = []
    mujoco = importlib.import_module("mujoco")
    for index in range(int(data.ncon)):
        item = data.contact[index]; g1, g2 = int(item.geom1), int(item.geom2)
        entry = {"contact_index": index, "geom1": g1, "geom2": g2,
                 "geom1_name": _name(model, "geom", g1), "geom2_name": _name(model, "geom", g2),
                 "distance": float(item.dist), "position": np.asarray(item.pos).tolist(),
                 "frame": np.asarray(item.frame).tolist(),
                 "friction": np.asarray(item.friction).tolist() if hasattr(item, "friction") else None}
        if frozenset((g1, g2)) == frozenset((tarsus_id, surface_id)):
            wrench = np.zeros(6); mujoco.mj_contactForce(getattr(model, "ptr", model),
                getattr(data, "ptr", data), index, wrench)
            entry["mujoco_contact_wrench"] = wrench.tolist(); selected.append(entry)
        all_contacts.append(entry)
    pair_set = sorted((min(x["geom1"], x["geom2"]), max(x["geom1"], x["geom2"])) for x in all_contacts)
    return pair_set, {"pair_present": bool(selected), "contacts": selected}, all_contacts


def _run(label, flygym, cns_data, interfaces):
    sim, physics, obs, tarsus_id, surface_id = _make_live(flygym)
    initial = _model_snapshot(physics.model, physics.data, surface_id)
    brain = MaleCNSBrain(cns_data); brain.reset(SEED)
    encoder = TactileContactEncoder(config=TactileContactConfig(seed=SEED))
    decoders = {leg: IsolatedTibiaDecoder(interfaces[leg]) for leg in LEG_ORDER}
    for decoder in decoders.values(): decoder.reset(brain.spike_counts)
    commands = _joint_positions(obs); pending = set(); rows = []
    stride = int(round(NEURAL_DT_MS / (TIMESTEP_S * 1000)))
    resolution = _resolution(physics.model)
    try:
        for step in range(int(round(DURATION_MS / (TIMESTEP_S * 1000))) + 1):
            time_ms = float(physics.data.time * 1000); forces = np.asarray(obs["contact_forces"], dtype=float)
            frame = encoder.encode(forces, time_ms, TIMESTEP_S * 1000)["LM"]
            pending.update(map(int, frame.generated_dense_indices)); decoded = {leg: 0.0 for leg in LEG_ORDER}
            delivered = (); measured = _joint_positions(obs); base_origin = "previous_command"
            if step and step % stride == 0:
                brain.clear_external_drive(); candidates = tuple(sorted(pending)); pending.clear()
                if candidates: brain.set_external_drive(candidates, 1000.0 / brain.config.dt)
                brain.external_drive_withheld_indices = np.empty(0, np.intp)
                brain.step(); delivered = tuple(map(int, brain._last_external_delivered)); base_origin = "current_measured_joint_position"
                for leg in LEG_ORDER:
                    _, command = decoders[leg].update(brain.spike_counts, NEURAL_DT_MS,
                        measured[ACTUATOR_INDICES[leg]], NEURAL_DT_MS / 1000,
                        apply_neural_offset=True)
                    decoded[leg] = float(command.magnitude_clamped_output_rad)
                    # Safety invariant: only the measured BASE/HOLD target is applied.
                    commands[ACTUATOR_INDICES[leg]] = measured[ACTUATOR_INDICES[leg]]
            pair_set, selected, all_contacts = _contacts(physics, tarsus_id, surface_id)
            row = {"time_ms": time_ms, "qpos": _array(physics.data, "qpos"),
                   "qvel": _array(physics.data, "qvel"), "qacc": _array(physics.data, "qacc"),
                   "ctrl": _array(physics.data, "ctrl"), "ncon": int(physics.data.ncon),
                   "measured_joint_positions": measured.tolist(),
                   "commanded_base_hold_targets": commands.tolist(),
                   "contact_set": pair_set, "selected_contact_metadata": selected,
                   "contacts": all_contacts, "contact_forces": forces.tolist(),
                   "selected_force_observation": forces[CONTACT_FORCE_ROW].tolist(),
                   "selected_force_magnitude": float(np.linalg.norm(forces[CONTACT_FORCE_ROW])),
                   "candidate_events": list(map(int, frame.generated_dense_indices)),
                   "delivered_events": list(delivered), "decoded_output": decoded,
                   "neural_application_flag": False, "applied_neural_output": 0.0,
                   "base_target_origin": base_origin, "encoder_rng_digest": rng_digest(encoder.rng["LM"]),
                   "resolution": resolution}
            rows.append(row)
            if step == int(round(DURATION_MS / (TIMESTEP_S * 1000))): break
            obs = sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})[0]
        return {"label": label, "initial": initial, "rows": rows}
    finally:
        if getattr(sim, "close", None): sim.close()


def run_live():
    flygym = importlib.import_module("flygym"); interfaces = validated_interfaces(); cns_data = load_malecns()
    enabled = _run("TACTILE_MOTOR_ENABLED_LIKE_MOTOR_OFF", flygym, cns_data, interfaces)
    disabled = _run("TACTILE_MOTOR_DISABLED_LIKE_MOTOR_OFF", flygym, cns_data, interfaces)
    control_a = _run("CONTROL_A", flygym, cns_data, interfaces)
    control_b = _run("CONTROL_B", flygym, cns_data, interfaces)
    initial = compare_initialization(enabled["initial"], disabled["initial"])
    wrapper = compare_trajectories(enabled["rows"], disabled["rows"])
    repeat = compare_trajectories(control_a["rows"], control_b["rows"])
    classification = classify(initial, repeat, wrapper)
    order = {"performed": False, "outcome_follows": None}
    if classification in ("CONDITION_WRAPPER_MISMATCH", "CONTROL_COMMAND_MISMATCH",
                          "CONTACT_SOLVER_DIVERGENCE"):
        reverse_disabled = _run("TACTILE_MOTOR_DISABLED_LIKE_MOTOR_OFF", flygym, cns_data, interfaces)
        reverse_enabled = _run("TACTILE_MOTOR_ENABLED_LIKE_MOTOR_OFF", flygym, cns_data, interfaces)
        reversed_comparison = compare_trajectories(reverse_enabled["rows"], reverse_disabled["rows"])
        forward_times = {q: wrapper[q]["first_differing_time_ms"] for q in wrapper}
        reverse_times = {q: reversed_comparison[q]["first_differing_time_ms"] for q in reversed_comparison}
        def signature(comparison):
            return {q: (comparison[q]["first_differing_time_ms"],
                        comparison[q]["enabled_value"], comparison[q]["disabled_value"])
                    for q in comparison}
        forward_signature, reverse_signature = signature(wrapper), signature(reversed_comparison)
        swapped_reverse = {q: (value[0], value[2], value[1])
                           for q, value in reverse_signature.items()}
        follows = ("condition_label" if forward_signature == reverse_signature else
                   "run_order" if forward_signature == swapped_reverse else "unresolved")
        order = {"performed": True, "outcome_follows": follows, "comparison": reversed_comparison}
        classification = classify(initial, repeat, wrapper, follows)
    divergent = [(value["first_differing_time_ms"], key) for key, value in wrapper.items()
                 if key != "ctrl"
                 if value["first_differing_time_ms"] is not None]
    report = base_report(); report.update(run_status="COMPLETE", reason=None, classification=classification,
        initialization_audit=initial, comparisons={"condition_wrappers": wrapper,
        "same_condition_repeat": repeat}, order_reversal=order,
        earliest_physical_divergence=(None if not divergent else
            {"time_ms": min(divergent)[0], "quantity": min(divergent)[1]}))
    report["safety"]["applied_neural_output_sample_count"] = sum(
        row["applied_neural_output"] != 0 for run in (enabled, disabled, control_a, control_b) for row in run["rows"])
    report["control_command_audit"] = {"base_target_source": "current measured joint position at neural updates",
        "first_ctrl_divergence": wrapper["ctrl"], "decoded_contribution_zero_required": False,
        "application_flag_always_false": True}
    report["independence_audit"] = {
        "fresh_simulation_per_run": True, "fresh_flygym_model_and_data_per_run": True,
        "fresh_malecns_per_run": True, "fresh_decoder_set_per_run": True,
        "fresh_tactile_encoder_and_rng_per_run": True,
        "fresh_calibration_surface_arena_per_run": True,
        "module_mutable_runtime_state_used": False,
    }
    report["tactile_event_parity"] = {
        "candidate_events_exactly_equal": all(a["candidate_events"] == b["candidate_events"]
            for a, b in zip(enabled["rows"], disabled["rows"])),
        "delivered_events_exactly_equal": all(a["delivered_events"] == b["delivered_events"]
            for a, b in zip(enabled["rows"], disabled["rows"])),
        "encoder_rng_state_exactly_equal": all(a["encoder_rng_digest"] == b["encoder_rng_digest"]
            for a, b in zip(enabled["rows"], disabled["rows"])),
    }
    report["trajectories"] = {run["label"]: run["rows"] for run in (enabled, disabled, control_a, control_b)}
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
    atomic_write_report(args.json, report)
    print(f"M5D-4A {report['run_status']}: {report['classification']}"); print(f"wrote {args.json}")
    return 0 if report["run_status"] in ("COMPLETE", "NOT_RUN", "UNAVAILABLE") else 1


if __name__ == "__main__": raise SystemExit(main())
