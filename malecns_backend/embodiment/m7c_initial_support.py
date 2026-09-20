"""M7C-B preregistration, zero-step Windows preflight, and physics-only runner.

FlyGym and MuJoCo are imported dynamically and only by the two explicit Windows
modes.  In particular, this module has no dependency on (and never constructs)
MaleCNS or any neural runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import math
from pathlib import Path
from typing import Any, Mapping

np: Any = None  # loaded only by an explicit Windows runtime mode
SURFACE_NAME = "m5d2c_calibration_surface"

TIMESTEP_S = 0.0001
DURATION_MS = 100.0
TRANSITIONS = 1000
CHECKPOINT_TRANSITION = 130
FALL_HEIGHT = 0.25
ROLLOVER_UP_Z = 0.0
CANONICAL_ROOT = (0.0, 0.0, 0.5)
LEGS = ("LF", "LM", "LH", "RF", "RM", "RH")
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "interface_output" / "m7c_initial_stability"
PREREGISTRATION = OUTPUT / "m7c_b_preregistration.json"
RESULT = OUTPUT / "m7c_b_initial_support_result.json"
PREFLIGHT = OUTPUT / "m7c_b_windows_preflight.json"
AUDIT = OUTPUT / "m7c_initial_state_audit.json"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha_value(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _foot_geometry(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return conservative distal support bounds from the recorded mesh AABBs.

    Tarsus5 is a mesh.  ``max(geom_size)`` is not rotation invariant and was the
    defect in preregistration schema 1.  The Euclidean norm of the three AABB
    half-extents is the enclosing-sphere radius (MuJoCo ``geom_rbound``), so
    center-z minus that radius is conservative for every mesh orientation.
    """
    geoms = {g["name"].rsplit("/", 1)[-1]: g for g in audit["geometries"]}
    feet = []
    for leg in LEGS:
        geom = geoms[f"{leg}Tarsus5"]
        radius = math.sqrt(sum(float(x) ** 2 for x in geom["size"]))
        center = [float(x) for x in geom["world_position"]]
        feet.append({"leg": leg, "geom": geom["name"], "center_world_xyz": center,
                     "aabb_half_extents": [float(x) for x in geom["size"]],
                     "enclosing_radius": radius,
                     "conservative_lower_z": center[2] - radius})
    return feet


def candidates(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the complete, outcome-independent, two-candidate freeze."""
    feet = _foot_geometry(audit)
    lowest = min(x["conservative_lower_z"] for x in feet)
    return [
        {"id": "canonical_control", "init_pose": "stretch",
         "root_position": list(CANONICAL_ROOT), "spawn_orientation": [0.0, 0.0, 0.0],
         "vertical_translation": 0.0,
         "derivation": "exact canonical M7 / FlyGym constructor-default initialization",
         "differences_from_canonical": []},
        {"id": "distal_tarsus_support_translation", "init_pose": "stretch",
         "root_position": [0.0, 0.0, CANONICAL_ROOT[2] - lowest],
         "spawn_orientation": [0.0, 0.0, 0.0], "vertical_translation": -lowest,
         "derivation": ("one vertical root translation: ground z=0 minus the minimum "
                        "Tarsus5 center-z-minus-enclosing-radius support bound"),
         "source_provenance": ("M7C-A zero-step geom_xpos and mesh AABB half-extents; "
                               "enclosing radius = Euclidean norm(half-extents)"),
         "differences_from_canonical": ["spawn_pos.z only"]},
    ]


def build_preregistration(audit: Mapping[str, Any]) -> dict[str, Any]:
    cs = candidates(audit)
    obsolete = {"schema": "M7C-B-PREREGISTRATION.1",
                "candidate_definition_sha256": "1c59b984bdcfd93558732255ee5fe9d8409f397dd01848c7e2e564db1ed9ac28",
                "correction": "max(geom_size) was not a rotation-invariant mesh support bound; never executed"}
    return {"schema": "M7C-B-PREREGISTRATION.2", "status": "FROZEN_BEFORE_EXECUTION",
        "correction_notice": obsolete, "audit_sha256": _sha_value(audit),
        "candidate_definition_sha256": _sha_value(cs), "candidates": cs,
        "candidate_count": len(cs), "candidate_c": None,
        "candidate_c_reason": ("not admitted: installed FlyGym 1.2.1 source has not yet established an "
                               "explicit supported/standing initialization; preflight fails if it finds one"),
        "arbitrary_height_sweep": False, "optimizer": False,
        "brain_constructed": False, "neural_transitions": 0,
        "physics": {"timestep_s": TIMESTEP_S, "duration_ms": DURATION_MS,
            "transitions": TRANSITIONS, "checkpoint_13ms_transition": CHECKPOINT_TRANSITION,
            "fall_height_lt": FALL_HEIGHT, "rollover_body_up_z_le": ROLLOVER_UP_Z},
        "controls": {"mode": "baseline position control only",
            "position_targets": "each candidate's post-reset measured 42-joint positions",
            "gait_controller": False, "balance_controller": False,
            "reference_trajectory": False, "reward_rl_ai": False,
            "sensory_driven_control": False, "adhesion_enabled": False,
            "adhesion_command": [0.0] * 6,
            "calibration_surface": "canonical world pose and dimensions, present and fixed"},
        "gate": {"fail_closed_nonfinite": True, "reject_body_penetration": True,
            "reject_severe_foot_penetration": True, "flag_self_collision": True,
            "require_distal_ground_support_for_translated_candidate": True,
            "reject_mixed_support_surfaces": True},
        "execution_environment": "validated Windows FlyGym 1.2.1/MuJoCo environment only"}


def finite_state(values: Mapping[str, Any]) -> bool:
    try:
        def scalars(value: Any):
            if isinstance(value, (list, tuple)):
                for item in value: yield from scalars(item)
            else: yield value
        return all(math.isfinite(float(x)) for value in values.values() for x in scalars(value))
    except (TypeError, ValueError):
        return False


def reconstruct(height: float, up_z: float) -> dict[str, bool]:
    return {"fall": float(height) < FALL_HEIGHT, "rollover": float(up_z) <= ROLLOVER_UP_Z}


def inspect_flygym_121(flygym: Any) -> dict[str, Any]:
    """Inventory the installed distribution without importing/running examples."""
    root = Path(flygym.__file__).resolve().parent
    text_suffixes = {".py", ".yaml", ".yml", ".json"}
    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in text_suffixes]
    pose_files = [p for p in files if "pose" in "/".join(x.lower() for x in p.parts)]
    named = sorted({p.stem for p in pose_files if p.suffix.lower() in {".yaml", ".yml", ".json"}})
    evidence: dict[str, list[dict[str, Any]]] = {k: [] for k in
        ("init_pose", "stretch", "standing", "walking", "spawn_pos", "settling",
         "adhesion", "inverse_kinematics", "supported_pose_helper")}
    needles = {"init_pose": ("init_pose",), "stretch": ("stretch",),
        "standing": ("standing", "stand_pose"), "walking": ("walking", "locomotion"),
        "spawn_pos": ("spawn_pos",), "settling": ("settle", "settling"),
        "adhesion": ("enable_adhesion",), "inverse_kinematics": ("inverse_kinematics", "ik_"),
        "supported_pose_helper": ("supported_pose", "standing_pose", "stand_pose")}
    for path in files:
        try: lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError: continue
        rel = path.relative_to(root).as_posix()
        for number, line in enumerate(lines, 1):
            lower = line.lower()
            for key, terms in needles.items():
                if any(term in lower for term in terms) and len(evidence[key]) < 80:
                    evidence[key].append({"file": rel, "line": number, "text": line.strip()[:300]})
    explicit_standing = sorted(set(named) & {"stand", "standing", "supported", "supported_stance"})
    return {"flygym_version": importlib.metadata.version("flygym"),
        "flygym_module_path": str(Path(flygym.__file__).resolve()),
        "fly_constructor_signature": str(inspect.signature(flygym.Fly)),
        "package_root": str(root), "text_file_count": len(files),
        "pose_resource_files": [{"path": str(p.relative_to(root)), "sha256": _sha_file(p)} for p in pose_files],
        "available_named_pose_resources": named, "stretch_definition": [
            x for x in evidence["stretch"] if "stretch" in x["file"].lower() or "pose" in x["file"].lower()],
        "explicit_standing_pose_resources": explicit_standing, "source_evidence": evidence}


def _forward(physics: Any) -> None:
    if getattr(physics, "forward", None): physics.forward(); return
    mujoco = importlib.import_module("mujoco")
    mujoco.mj_forward(getattr(physics.model, "ptr", physics.model), getattr(physics.data, "ptr", physics.data))


def _physics(sim: Any) -> Any:
    for owner in (sim, getattr(sim, "env", None), getattr(sim, "_env", None)):
        if getattr(owner, "physics", None) is not None: return owner.physics
    raise RuntimeError("FlyGym simulation exposes no MuJoCo physics object")


def _geom_name(model: Any, geom_id: int) -> str | None:
    method = getattr(model, "id2name", None)
    if method is not None:
        for args in ((geom_id, "geom"), ("geom", geom_id)):
            try: value = method(*args)
            except (TypeError, ValueError, KeyError): continue
            if value is not None: return str(value)
    mujoco = importlib.import_module("mujoco")
    value = mujoco.mj_id2name(getattr(model, "ptr", model), mujoco.mjtObj.mjOBJ_GEOM, geom_id)
    return None if value is None else str(value)


def _observation(sim: Any, reset: Any = None) -> Mapping[str, Any]:
    if getattr(sim, "get_observation", None): return sim.get_observation()
    value = reset[0] if isinstance(reset, tuple) else reset
    if not isinstance(value, Mapping): raise RuntimeError("FlyGym exposed no observation mapping")
    return value


def _surface_spec(audit: Mapping[str, Any]) -> dict[str, Any]:
    value = audit["calibration_surface"]
    return {"name": value["name"], "position": [float(x) for x in value["position"]],
            "half_size": [float(x) for x in value["half_size"]]}


def _make_sim(flygym: Any, candidate: Mapping[str, Any], audit: Mapping[str, Any]):
    placements = [f"{leg}{segment}" for leg in LEGS for segment in
                  ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")]
    fly = flygym.Fly(spawn_pos=tuple(candidate["root_position"]),
        spawn_orientation=tuple(candidate["spawn_orientation"]), init_pose=candidate["init_pose"],
        enable_adhesion=False, control="position", contact_sensor_placements=placements)
    simulation = getattr(flygym, "SingleFlySimulation", None) or importlib.import_module("flygym.simulation").SingleFlySimulation
    arena = importlib.import_module("flygym.arena").FlatTerrain()
    surface = _surface_spec(audit)
    arena.root_element.worldbody.add("geom", name=surface["name"], type="box",
        size=surface["half_size"], pos=surface["position"], rgba=(.9, .2, .2, 1),
        contype=1, conaffinity=1)
    return simulation(fly=fly, arena=arena, cameras=[], timestep=TIMESTEP_S)


def _contacts(model: Any, data: Any) -> list[dict[str, Any]]:
    out = []
    for i in range(int(data.ncon)):
        c = data.contact[i]; g1, g2 = int(c.geom1), int(c.geom2)
        out.append({"geom1": _geom_name(model, g1), "geom2": _geom_name(model, g2),
                    "distance": float(c.dist), "position": np.asarray(c.pos).tolist()})
    return out


def _state(sim: Any, obs: Mapping[str, Any]) -> dict[str, Any]:
    physics = _physics(sim); model, data = physics.model, physics.data
    quat = np.asarray(data.qpos[3:7], dtype=float); quat /= np.linalg.norm(quat)
    up_z = float(1 - 2 * (quat[1] ** 2 + quat[2] ** 2))
    joints = np.asarray(obs["joints"], dtype=float); joints = joints[0] if joints.ndim == 2 else joints
    forces = np.asarray(obs.get("contact_forces", np.zeros((36, 3))), dtype=float)
    state = {"body_xyz": np.asarray(data.qpos[:3]).tolist(), "body_quaternion_wxyz": quat.tolist(),
        "body_up_z": up_z, "qpos": np.asarray(data.qpos).tolist(), "qvel": np.asarray(data.qvel).tolist(),
        "joints": joints.tolist(), "contact_forces": forces.tolist(), "contacts": _contacts(model, data)}
    if not finite_state({k: state[k] for k in ("body_xyz", "body_quaternion_wxyz", "qpos", "qvel", "joints", "contact_forces")}):
        raise RuntimeError("nonfinite state")
    return state


def _geometry_gate(sim: Any, candidate: Mapping[str, Any], audit: Mapping[str, Any]) -> dict[str, Any]:
    physics = _physics(sim); model, data = physics.model, physics.data
    geom_ids = {str(_geom_name(model, i)).rsplit("/", 1)[-1]: i for i in range(int(model.ngeom))}
    ground = geom_ids["ground"]; surface = geom_ids[SURFACE_NAME]
    feet = []
    for leg in LEGS:
        i = geom_ids[f"{leg}Tarsus5"]
        radius = float(np.asarray(model.geom_rbound)[i])
        lower = float(data.geom_xpos[i][2]) - radius
        feet.append({"leg": leg, "center_z": float(data.geom_xpos[i][2]), "geom_rbound": radius,
                     "conservative_lower_z": lower})
    expected = next(x for x in candidates(audit) if x["id"] == candidate["id"])
    if _sha_value(candidate) != _sha_value(expected): raise RuntimeError("candidate differs from preregistration reconstruction")
    if candidate["id"] == "distal_tarsus_support_translation" and abs(min(x["conservative_lower_z"] for x in feet)) > 1e-7:
        raise RuntimeError("corrected support translation does not match live MuJoCo geom_rbound")
    surface_spec = _surface_spec(audit)
    surface_unchanged = (np.array_equal(np.asarray(model.geom_size[surface]), np.asarray(surface_spec["half_size"]))
                         and np.array_equal(np.asarray(data.geom_xpos[surface]), np.asarray(surface_spec["position"])))
    contacts = _contacts(model, data)
    ground_name, surface_name = _geom_name(model, ground), _geom_name(model, surface)
    distal_names = {f"0/{leg}Tarsus5" for leg in LEGS}
    support_surfaces = set()
    for contact in contacts:
        pair = {contact["geom1"], contact["geom2"]}
        if pair & distal_names:
            if ground_name in pair: support_surfaces.add("ground")
            if surface_name in pair: support_surfaces.add("calibration_surface")
    body_geoms = [i for i in range(int(model.ngeom)) if str(_geom_name(model, i)).startswith("0/")]
    body_penetration = any({int(c.geom1), int(c.geom2)} & {ground} and
                           {int(c.geom1), int(c.geom2)} & set(body_geoms) and float(c.dist) < -1e-6
                           for c in data.contact[:int(data.ncon)])
    if not surface_unchanged or body_penetration or len(support_surfaces) > 1:
        raise RuntimeError("initial geometry gate failed")
    return {"pass": True, "feet": feet, "contacts": contacts,
            "distal_support_surfaces": sorted(support_surfaces),
            "body_penetration": body_penetration, "calibration_surface_unchanged": surface_unchanged}


def _load_frozen() -> tuple[dict[str, Any], dict[str, Any]]:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8")); audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    expected = build_preregistration(audit)
    if prereg != expected: raise RuntimeError("preregistration content/provenance mismatch; regenerate before preflight")
    if prereg["candidate_definition_sha256"] != _sha_value(prereg["candidates"]): raise RuntimeError("candidate hash mismatch")
    return prereg, audit


def windows_preflight() -> dict[str, Any]:
    global np
    np = importlib.import_module("numpy")
    prereg, audit = _load_frozen(); flygym = importlib.import_module("flygym"); mujoco = importlib.import_module("mujoco")
    installed = inspect_flygym_121(flygym)
    if installed["flygym_version"] != "1.2.1": raise RuntimeError("preflight requires FlyGym == 1.2.1")
    if installed["explicit_standing_pose_resources"] or installed["source_evidence"]["supported_pose_helper"]:
        raise RuntimeError("installed explicit standing pose/helper found: preregistration correction/Candidate C review required")
    checks = []
    for candidate in prereg["candidates"]:
        sim = _make_sim(flygym, candidate, audit)
        try:
            reset = sim.reset(); _forward(_physics(sim)); obs = _observation(sim, reset)
            state = _state(sim, obs); gate = _geometry_gate(sim, candidate, audit)
            checks.append({"candidate": candidate["id"], "state": state, "geometry_gate": gate})
        finally:
            if getattr(sim, "close", None): sim.close()
    report = {"schema": "M7C-B-WINDOWS-PREFLIGHT.1", "status": "PASS",
        "preregistration_sha256": _sha_file(PREREGISTRATION), "installed_flygym": installed,
        "mujoco_version": getattr(mujoco, "__version__", importlib.metadata.version("mujoco")),
        "candidate_checks": checks, "physics_transitions": 0, "neural_transitions": 0,
        "brain_constructed": False, "planned_timestep_s": TIMESTEP_S,
        "planned_duration_ms": DURATION_MS, "planned_transitions": TRANSITIONS,
        "adhesion_enabled": False, "controllers": {"gait": False, "balance": False,
        "reference": False, "reward_rl_ai": False}}
    PREFLIGHT.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return report


def _validated_preflight() -> tuple[dict[str, Any], dict[str, Any]]:
    prereg, audit = _load_frozen()
    report = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if report.get("status") != "PASS" or report.get("physics_transitions") != 0 or report.get("neural_transitions") != 0:
        raise RuntimeError("a passing zero-transition Windows preflight is required")
    if report.get("preregistration_sha256") != _sha_file(PREREGISTRATION): raise RuntimeError("stale preflight provenance")
    return prereg, audit


def run_windows() -> dict[str, Any]:
    global np
    np = importlib.import_module("numpy")
    prereg, audit = _validated_preflight(); flygym = importlib.import_module("flygym")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if importlib.metadata.version("flygym") != "1.2.1": raise RuntimeError("runtime FlyGym version changed after preflight")
    mujoco = importlib.import_module("mujoco")
    current_mujoco = getattr(mujoco, "__version__", importlib.metadata.version("mujoco"))
    if current_mujoco != preflight["mujoco_version"] or str(Path(flygym.__file__).resolve()) != preflight["installed_flygym"]["flygym_module_path"]:
        raise RuntimeError("Windows runtime provenance changed after preflight")
    results = []
    for candidate in prereg["candidates"]:
        sim = _make_sim(flygym, candidate, audit)
        try:
            reset = sim.reset(); _forward(_physics(sim)); obs = _observation(sim, reset)
            gate = _geometry_gate(sim, candidate, audit); initial = _state(sim, obs)
            targets = np.asarray(initial["joints"], dtype=float); start = np.asarray(initial["body_xyz"], dtype=float)
            checkpoints = {"0_ms": initial}; first_fall = first_rollover = None
            min_h = max_h = float(start[2]); min_up = float(initial["body_up_z"])
            contact_evolution = [{"transition": 0, "contacts": initial["contacts"],
                                  "distal_force_norms": np.linalg.norm(np.asarray(initial["contact_forces"]), axis=1)[5::6].tolist()}]
            previous_pairs = {(x["geom1"], x["geom2"]) for x in initial["contacts"]}
            for transition in range(1, TRANSITIONS + 1):
                stepped = sim.step({"joints": targets.copy(), "adhesion": np.zeros(6)})
                obs = stepped[0] if isinstance(stepped, tuple) else stepped
                state = _state(sim, obs); height = float(state["body_xyz"][2]); up = float(state["body_up_z"])
                min_h, max_h, min_up = min(min_h, height), max(max_h, height), min(min_up, up)
                events = reconstruct(height, up)
                if events["fall"] and first_fall is None: first_fall = transition * TIMESTEP_S * 1000
                if events["rollover"] and first_rollover is None: first_rollover = transition * TIMESTEP_S * 1000
                pairs = {(x["geom1"], x["geom2"]) for x in state["contacts"]}
                if pairs != previous_pairs or transition in (CHECKPOINT_TRANSITION, TRANSITIONS):
                    contact_evolution.append({"transition": transition, "contacts": state["contacts"],
                        "distal_force_norms": np.linalg.norm(np.asarray(state["contact_forces"]), axis=1)[5::6].tolist()})
                previous_pairs = pairs
                if transition == CHECKPOINT_TRANSITION: checkpoints["13_ms"] = state
                if transition == TRANSITIONS: checkpoints["100_ms"] = state
            final = checkpoints["100_ms"]
            results.append({"candidate": candidate, "initial_geometry_gate": gate, "checkpoints": checkpoints,
                "first_fall_time_ms": first_fall, "first_rollover_time_ms": first_rollover,
                "min_height": min_h, "max_height": max_h, "min_body_up_z": min_up,
                "body_displacement": (np.asarray(final["body_xyz"]) - start).tolist(),
                "contact_support_and_self_collision_evolution": contact_evolution,
                "finite_state": True, "physics_transitions": TRANSITIONS, "neural_transitions": 0})
        finally:
            if getattr(sim, "close", None): sim.close()
    report = {"schema": "M7C-B-RESULT.2", "run_status": "COMPLETE", "experiment": "physics-only initial stability; not walking",
        "preregistration_sha256": _sha_file(PREREGISTRATION), "preflight_sha256": _sha_file(PREFLIGHT),
        "candidate_results": results, "brain_constructed": False, "neural_transitions": 0,
        "physics_transitions_per_candidate": TRANSITIONS, "adhesion_changed": False,
        "calibration_surface_changed": False}
    RESULT.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write-preregistration", action="store_true")
    modes.add_argument("--inspect-flygym", action="store_true")
    modes.add_argument("--windows-preflight", action="store_true")
    modes.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv); OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.write_preregistration:
        audit = json.loads(AUDIT.read_text(encoding="utf-8")); report = build_preregistration(audit)
        PREREGISTRATION.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"); print(PREREGISTRATION)
    elif args.inspect_flygym:
        print(json.dumps(inspect_flygym_121(importlib.import_module("flygym")), indent=2, sort_keys=True))
    elif args.windows_preflight:
        windows_preflight(); print("M7C-B WINDOWS PREFLIGHT PASS — CANDIDATES FROZEN — ZERO PHYSICS TRANSITIONS — ZERO NEURAL TRANSITIONS — ENGINEERING RUN NOT EXECUTED")
    else:
        run_windows(); print(RESULT)


if __name__ == "__main__": main()
