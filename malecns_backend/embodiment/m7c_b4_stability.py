"""M7C-B4 frozen-position, physics-only initial support experiment.

Importing this module is inert.  In particular it deliberately has no MaleCNS
dependency.  ``--windows-preflight`` performs reset/forward inspection only;
``--run-windows`` is the sole path which calls ``step``.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import m7c_b2_pose_geometry_audit as b2
from . import m7c_b3_tripod_support_height as b3
from .m7_protocol import THRESHOLDS

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "interface_output" / "m7c_initial_stability"
B3_PATH = OUTPUT_DIR / "m7c_b3_tripod_support_height.json"
SUMMARY_PATH = OUTPUT_DIR / "m7c_b4_stability_summary.json"
MANIFEST_PATH = OUTPUT_DIR / "m7c_b4_stability_manifest.json"
RAW_PATH = OUTPUT_DIR / "m7c_b4_stability_raw.npz"
SCHEMA = "M7C-B4-STABILITY.1"
DT = 0.0001
TRANSITIONS = 1000
STATES = 1001
INIT_POSE = "tripod"
SPAWN_POS = (0.0, 0.0, 0.6045752232266313)
SPAWN_ORIENTATION = (0.0, 0.0, 0.0)
ANALYTIC_DZ = 0.10457522322663132
CHECKPOINTS = (0, 72, 130, 1000)
COXA_PAIR = frozenset(("LHCoxa", "RHCoxa"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_b3(path: Path = B3_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError("canonical B3 artifact is absent")
    value = json.loads(path.read_text(encoding="utf-8"))
    solution, zero, protocol = value.get("analytic_solution", {}), value.get("zero_step_reconstruction", {}), value.get("protocol", {})
    required = {
        "schema": value.get("schema") == "M7C-B3-TRIPOD-SUPPORT-HEIGHT.1",
        "status": value.get("status") == "COMPLETE",
        "classification": solution.get("classification") == "TRIPOD_ANALYTIC_SUPPORT_HEIGHT_FOUND",
        "analytic_dz": solution.get("analytic_dz") == ANALYTIC_DZ,
        "corrected_spawn_z": solution.get("corrected_spawn_z") == SPAWN_POS[2],
        "tripod": value.get("tripod_pose", {}).get("relative_path") == "data/pose/pose_tripod.yaml",
        "original_spawn_z": value.get("original_spawn_z") == 0.5,
        "joints": zero.get("all_42_tripod_joints_unchanged") is True,
        "finite": zero.get("finite_state") is True,
        "eligible": zero.get("future_physics_eligible") is True,
        "gate": zero.get("geometry_gate", {}).get("valid") is True,
    }
    labels = zero.get("geometry_gate", {}).get("classifications", {})
    required.update({name: labels.get(name) is expected for name, expected in {
        "VALID_SUPPORT_CONTACT": True, "NO_SUPPORT_CONTACT": False,
        "FORBIDDEN_GROUND_PENETRATION": False, "EXCESSIVE_DISTAL_PENETRATION": False}.items()})
    required.update({name: protocol.get(name) == expected and type(protocol.get(name)) is type(expected) for name, expected in {
        "physics_transitions": 0, "neural_transitions": 0, "brain_constructed": False,
        "controller": False, "adhesion_enabled": False, "calibration_surface_changed": False,
        "height_sweep": False, "optimizer": False}.items()})
    failed = [key for key, ok in required.items() if not ok]
    if failed:
        raise RuntimeError("canonical B3 provenance mismatch: " + ", ".join(failed))
    return {"path": str(path.resolve()), "sha256": _sha(path), "artifact": value}


def _surface() -> dict[str, Any]:
    inherited = json.loads(b2.M7C_AUDIT.read_text(encoding="utf-8"))["calibration_surface"]
    required = ("name", "position", "half_size", "orientation_matrix", "target_tarsus_id", "target_tarsus_name")
    if any(key not in inherited for key in required) or inherited["name"] != b2.SURFACE_NAME:
        raise RuntimeError("incomplete calibration-surface provenance")
    return inherited


def _make_sim(flygym: Any, surface: Mapping[str, Any]) -> Any:
    fly = flygym.Fly(init_pose=INIT_POSE, spawn_pos=SPAWN_POS,
                     spawn_orientation=SPAWN_ORIENTATION, enable_adhesion=False,
                     control="position", contact_sensor_placements=[f"{leg}{seg}" for leg in b2.LEGS for seg in
                     ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")])
    arena = importlib.import_module("flygym.arena").FlatTerrain()
    arena.root_element.worldbody.add("geom", name=surface["name"], type="box", size=surface["half_size"],
        pos=surface["position"], rgba=(.9, .2, .2, 1), contype=1, conaffinity=1)
    cls = getattr(flygym, "SingleFlySimulation", None) or importlib.import_module("flygym.simulation").SingleFlySimulation
    return cls(fly=fly, arena=arena, cameras=[], timestep=DT)


def _modules() -> tuple[Any, Any, Any, dict[str, str]]:
    np, flygym, mujoco = (importlib.import_module(x) for x in ("numpy", "flygym", "mujoco"))
    fv, mv = importlib.metadata.version("flygym"), getattr(mujoco, "__version__", importlib.metadata.version("mujoco"))
    if (fv, mv) != ("1.2.1", "3.2.7"):
        raise RuntimeError(f"requires FlyGym 1.2.1 / MuJoCo 3.2.7, found {fv} / {mv}")
    paths = {x: str(Path(getattr(module, "__file__", "")).resolve()) for x, module in (("flygym", flygym), ("mujoco", mujoco), ("numpy", np))}
    return np, flygym, mujoco, {"flygym_version": fv, "mujoco_version": mv, "module_paths": paths}


def _contact_rows(np: Any, mujoco: Any, model: Any, data: Any) -> list[dict[str, Any]]:
    rows = b2._contacts(np, mujoco, model, data)
    for index, row in enumerate(rows):
        force = np.zeros(6, dtype=float)
        try:
            mujoco.mj_contactForce(getattr(model, "ptr", model), getattr(data, "ptr", data), index, force)
            row["force"] = force.tolist(); row["force_finite"] = bool(np.isfinite(force).all())
        except (AttributeError, TypeError):
            row["force"] = None; row["force_finite"] = None
    return rows


def _inspect(sim: Any, np: Any, mujoco: Any, *, reset: bool) -> dict[str, Any]:
    observation = sim.reset() if reset else (sim.get_observation() if getattr(sim, "get_observation", None) else {})
    if isinstance(observation, tuple): observation = observation[0]
    physics = b2._physics(sim); model, data = physics.model, physics.data
    if reset:
        (physics.forward() if getattr(physics, "forward", None) else mujoco.mj_forward(getattr(model, "ptr", model), getattr(data, "ptr", data)))
        if getattr(sim, "get_observation", None): observation = sim.get_observation()
    joints = np.asarray(observation["joints"], dtype=float); joints = joints[0] if joints.ndim == 2 else joints
    qpos, qvel = np.asarray(data.qpos, dtype=float), np.asarray(data.qvel, dtype=float)
    contacts = _contact_rows(np, mujoco, model, data)
    quat = qpos[3:7]; up_z = float(1 - 2 * (quat[1] ** 2 + quat[2] ** 2))
    return {"time": float(data.time), "root_xyz": qpos[:3].tolist(), "body_orientation_wxyz": quat.tolist(),
        "body_up_z": up_z, "qpos": qpos.tolist(), "qvel": qvel.tolist(), "joints": joints.tolist(),
        "ctrl": np.asarray(data.ctrl, dtype=float).tolist(), "contacts": contacts,
        "finite": bool(np.isfinite(qpos).all() and np.isfinite(qvel).all() and np.isfinite(joints).all())}


def _calibration_unchanged(sim: Any, np: Any, mujoco: Any, expected: Mapping[str, Any]) -> bool:
    physics = b2._physics(sim); model, data = physics.model, physics.data
    ids = [i for i in range(int(model.ngeom)) if b2._base(b2._name(mujoco, model, i)) == expected["name"]]
    if len(ids) != 1: return False
    gid = ids[0]
    return bool(np.array_equal(np.asarray(model.geom_size[gid]), expected["half_size"]) and
        np.array_equal(np.asarray(data.geom_xpos[gid]), expected["position"]) and
        np.array_equal(np.asarray(data.geom_xmat[gid]).reshape(3, 3), expected["orientation_matrix"]) and
        int(model.geom_contype[gid]) == 1 and int(model.geom_conaffinity[gid]) == 1)


def zero_step_gate(sim: Any, np: Any, mujoco: Any, provenance: Mapping[str, Any], surface: Mapping[str, Any]) -> tuple[dict[str, Any], Any]:
    state = _inspect(sim, np, mujoco, reset=True)
    expected = provenance["artifact"]["zero_step_reconstruction"]["controlled_joint_positions"]
    baseline = np.asarray(state["joints"], dtype=float)
    unchanged = baseline.size == 42 and np.array_equal(baseline, np.asarray(expected, dtype=float))
    surface_ok = _calibration_unchanged(sim, np, mujoco, surface)
    gate = b3.support_geometry_gate(state["contacts"], state_finite=state["finite"], calibration_surface_unchanged=surface_ok)
    root_ok = state["root_xyz"][2] == SPAWN_POS[2]
    valid = gate["valid"] and unchanged and root_ok and baseline.size == 42
    state.update({"baseline_targets": baseline.tolist(), "target_minus_measured": (baseline-baseline).tolist(),
        "all_42_tripod_joints_unchanged": unchanged, "corrected_spawn_z_exact": root_ok,
        "calibration_surface_unchanged": surface_ok, "geometry_gate": gate, "valid": bool(valid)})
    if not valid: raise RuntimeError("B3 zero-step geometry was not reproduced")
    return state, baseline


def telemetry_schema() -> dict[str, Any]:
    return {"states": STATES, "numeric": ["time", "root_xyz", "body_orientation_wxyz", "body_up_z", "qpos", "qvel",
        "joints", "commanded_targets", "action", "ctrl", "contact_count", "finite"],
        "json_utf8": ["contact_identities", "contact_depths", "contact_forces", "distal_support", "forbidden_ground",
                      "self_contacts", "calibration_surface_contacts"]}


def validate_trace(records: Sequence[Mapping[str, Any]], baseline: Any, np: Any) -> None:
    """Validate the no-adaptation and exact-cadence contract."""
    if len(records) != STATES:
        raise RuntimeError("wrong physical state count")
    target = np.asarray(baseline, dtype=float)
    if target.shape != (42,):
        raise RuntimeError("baseline target is not the 42-joint measured pose")
    for index, state in enumerate(records):
        if not state["finite"]:
            raise RuntimeError(f"nonfinite physics state at index {index}")
        if index and not np.array_equal(np.asarray(state["commanded_targets"]), target):
            raise RuntimeError(f"position target changed at index {index}")
        if index and not np.array_equal(np.asarray(state["action"])[42:], np.zeros(6)):
            raise RuntimeError(f"adhesion command changed at index {index}")


def _output_available() -> bool:
    for path in (SUMMARY_PATH, MANIFEST_PATH):
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "COMPLETE": return False
    return not RAW_PATH.exists()


def windows_preflight(*, simulator_factory: Any = None) -> dict[str, Any]:
    provenance = validate_b3(); np, flygym, mujoco, environment = _modules(); surface = _surface()
    if not _output_available(): raise FileExistsError("completed/canonical B4 output already exists")
    sim = (simulator_factory or _make_sim)(flygym, surface)
    try: initial, _ = zero_step_gate(sim, np, mujoco, provenance, surface)
    finally: sim.close()
    return {"schema": SCHEMA, "status": "PREFLIGHT_PASS", "b3": {k: v for k, v in provenance.items() if k != "artifact"},
        "environment": environment, "constants": {"init_pose": INIT_POSE, "spawn_pos": SPAWN_POS,
        "spawn_orientation": SPAWN_ORIENTATION, "control": "position", "adhesion_enabled": False, "dt": DT,
        "duration_seconds": .1, "physics_transitions": TRANSITIONS, "neural_transitions": 0},
        "zero_step_gate": initial, "telemetry_schema": telemetry_schema(), "physics_transitions_executed": 0,
        "neural_transitions_executed": 0, "brain_constructed": False, "prohibited_controller": False}


def _categories(contacts: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    gate = b3.support_geometry_gate(contacts, state_finite=True, calibration_surface_unchanged=True)
    return {"distal_support": gate["distal_ground_contacts"], "forbidden_ground": gate["forbidden_ground_penetrations"],
            "self_contacts": gate["self_contacts"], "calibration_surface_contacts": gate["calibration_surface_contacts"]}


def _write_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    with os.fdopen(os.open(path, flags, 0o644), "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")


def run_windows(*, simulator_factory: Any = None) -> dict[str, Any]:
    preflight = windows_preflight(simulator_factory=simulator_factory)
    np, flygym, mujoco, _ = _modules(); surface = _surface(); provenance = validate_b3()
    sim = (simulator_factory or _make_sim)(flygym, surface)
    records: list[dict[str, Any]] = []
    try:
        initial, baseline = zero_step_gate(sim, np, mujoco, provenance, surface)
        records.append(initial)
        action = {"joints": baseline.copy(), "adhesion": np.zeros(6, dtype=float)}
        for _ in range(TRANSITIONS):
            sim.step(action)
            state = _inspect(sim, np, mujoco, reset=False)
            if not state["finite"]: raise RuntimeError("nonfinite physics state")
            state["commanded_targets"] = baseline.tolist(); state["action"] = np.concatenate((baseline, np.zeros(6))).tolist()
            records.append(state)
    finally: sim.close()
    validate_trace(records, baseline, np)
    # Compact numeric arrays plus JSON strings avoid pickle/object arrays.
    arrays: dict[str, Any] = {}
    for key in ("time", "root_xyz", "body_orientation_wxyz", "body_up_z", "qpos", "qvel", "joints", "commanded_targets", "action", "ctrl", "finite"):
        if key == "commanded_targets" and key not in records[0]: records[0][key] = baseline.tolist()
        if key == "action" and key not in records[0]: records[0][key] = np.concatenate((baseline, np.zeros(6))).tolist()
        arrays[key] = np.asarray([row[key] for row in records])
    categories = [_categories(row["contacts"]) for row in records]
    arrays["contact_count"] = np.asarray([len(row["contacts"]) for row in records], dtype=np.int32)
    arrays["contacts_json"] = np.asarray([json.dumps(row["contacts"], separators=(",", ":")) for row in records])
    arrays["categories_json"] = np.asarray([json.dumps(row, separators=(",", ":")) for row in categories])
    with open(RAW_PATH, "xb") as stream: np.savez_compressed(stream, **arrays)
    raw_hash = _sha(RAW_PATH)
    heights = np.asarray([r["root_xyz"][2] for r in records]); ups = np.asarray([r["body_up_z"] for r in records])
    falls = np.flatnonzero(heights <= heights[0] * THRESHOLDS["fall_height_fraction"])
    rolls = np.flatnonzero(ups <= THRESHOLDS["rollover_body_up_z_max"])
    first_fall = None if not falls.size else float(falls[0] * DT); first_roll = None if not rolls.size else float(rolls[0] * DT)
    support = np.asarray([bool(c["distal_support"]) for c in categories]); losses = np.flatnonzero(~support)
    restorations = np.flatnonzero((~support[:-1]) & support[1:]) + 1
    coxa = [[c for c in cat["self_contacts"] if frozenset((b2._base(c["geom1"]), b2._base(c["geom2"]))) == COXA_PAIR] for cat in categories]
    coxa_depths = [c["penetration_depth"] for cs in coxa for c in cs]
    summary = {"schema": SCHEMA, "status": "COMPLETE", "classification": ("SUPPORTED_INITIALIZATION_FALLS_BEFORE_13MS" if first_fall is not None and first_fall < .013 else
        "SUPPORTED_INITIALIZATION_STABLE_100MS" if first_fall is None and first_roll is None else
        "SUPPORTED_INITIALIZATION_ROLLOVER" if first_roll is not None else "SUPPORTED_INITIALIZATION_FALLS_AFTER_13MS"),
        "physics_transitions": TRANSITIONS, "physics_states": STATES, "neural_transitions": 0,
        "first_fall_time_seconds": first_fall, "first_rollover_time_seconds": first_roll,
        "minimum_body_height": float(heights.min()), "minimum_body_up_z": float(ups.min()),
        "survived_past_7_2ms_without_fall": first_fall is None or first_fall > .0072,
        "survived_past_13ms_without_fall": first_fall is None or first_fall > .013,
        "survived_full_100ms_without_fall": first_fall is None, "survived_full_100ms_without_rollover": first_roll is None,
        "checkpoints": {str(i): records[i] for i in CHECKPOINTS},
        "support_analysis": {"first_loss_seconds": None if not losses.size else float(losses[0]*DT),
            "first_restoration_seconds": None if not restorations.size else float(restorations[0]*DT), "sample_fraction": float(support.mean()),
            "per_leg_duration_seconds": {leg: DT * sum(any(leg in b2._base(c["geom1"]) or leg in b2._base(c["geom2"]) for c in cat["distal_support"]) for cat in categories) for leg in b2.LEGS},
            "maximum_distal_penetration": max((c["penetration_depth"] for cat in categories for c in cat["distal_support"]), default=0.0),
            "any_forbidden_ground_contact": any(c["forbidden_ground"] for c in categories),
            "any_body_ground_contact": any(any("Thorax" in str(c) or "Abdomen" in str(c) or "Head" in str(c) for c in cat["forbidden_ground"]) for cat in categories),
            "any_calibration_surface_contact": any(c["calibration_surface_contacts"] for c in categories)},
        "self_collision_analysis": {"initial_coxa_penetration": max((c["penetration_depth"] for c in coxa[0]), default=None),
            "persists_after_dynamics_begin": bool(coxa[1]), "first_disappearance_seconds": next((i*DT for i, cs in enumerate(coxa) if not cs), None),
            "maximum_coxa_penetration": max(coxa_depths, default=None), "contact_forces_finite": all(c.get("force_finite") is not False for cs in coxa for c in cs),
            "additional_self_collisions": sorted({tuple(sorted((b2._base(c["geom1"]), b2._base(c["geom2"])))) for cat in categories for c in cat["self_contacts"] if frozenset((b2._base(c["geom1"]), b2._base(c["geom2"]))) != COXA_PAIR})},
        "raw_telemetry": {"path": str(RAW_PATH.resolve()), "byte_size": RAW_PATH.stat().st_size, "sha256": raw_hash},
        "preflight": {"status": preflight["status"], "b3": preflight["b3"]}}
    manifest = {"schema": SCHEMA, "status": "COMPLETE", "summary_path": str(SUMMARY_PATH.resolve()), "raw": summary["raw_telemetry"],
        "b3": preflight["b3"], "environment": preflight["environment"], "constants": preflight["constants"], "telemetry_schema": telemetry_schema()}
    _write_exclusive(SUMMARY_PATH, summary); _write_exclusive(MANIFEST_PATH, manifest)
    return summary


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--windows-preflight", action="store_true"); group.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv)
    if args.windows_preflight:
        windows_preflight(); print("M7C-B4 WINDOWS PREFLIGHT PASS — EXACT B3 SUPPORTED INITIALIZATION REPRODUCED — ZERO PHYSICS TRANSITIONS — ZERO NEURAL TRANSITIONS — 100MS PHYSICS-ONLY RUN NOT EXECUTED")
    else:
        result = run_windows()
        for key in ("classification", "physics_transitions", "neural_transitions", "first_fall_time_seconds", "first_rollover_time_seconds", "survived_past_7_2ms_without_fall", "survived_past_13ms_without_fall", "survived_full_100ms_without_fall"):
            print(f"{key}: {result[key]}")
        print(f"initial support contact: {result['checkpoints']['0']['geometry_gate']['distal_ground_contacts']}")
        print(f"support fraction: {result['support_analysis']['sample_fraction']}")
        print(f"initial coxa self-contact: {result['self_collision_analysis']['initial_coxa_penetration']}")
        print(f"maximum coxa self-contact penetration: {result['self_collision_analysis']['maximum_coxa_penetration']}")
        print(f"raw telemetry SHA-256: {result['raw_telemetry']['sha256']}")


if __name__ == "__main__": main()
