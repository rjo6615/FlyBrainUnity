"""M7C-B2 fail-closed, zero-transition static-pose geometry audit.

This module deliberately has no dependency on MaleCNS.  FlyGym, MuJoCo, and
NumPy are imported only after the explicit ``--windows-audit`` entry point is
selected.  Simulation stepping is structurally prohibited by ``StepForbidden``.
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
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "interface_output" / "m7c_initial_stability" / "m7c_b2_pose_geometry_audit.json"
M7C_AUDIT = HERE / "interface_output" / "m7c_initial_stability" / "m7c_initial_state_audit.json"
SURFACE_NAME = "m5d2c_calibration_surface"
POSES = (
    {"id": "canonical_stretch", "init_pose": "stretch", "spawn_pos": [0.0, 0.0, 0.5]},
    {"id": "default_tripod", "init_pose": "tripod", "spawn_pos": None},
    {"id": "default_zero", "init_pose": "zero", "spawn_pos": None},
)
LEGS = ("LF", "LM", "LH", "RF", "RM", "RH")
MATERIAL_PENETRATION_TOLERANCE = 1e-6
DISTAL_PENETRATION_TOLERANCE = 1e-3
CONTACT_TOLERANCE = 1e-6


class StepForbidden:
    """Proxy that makes an accidental physics transition impossible."""

    def __init__(self, simulation: Any):
        self._simulation = simulation

    def step(self, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("sim.step() is forbidden by the M7C-B2 zero-transition protocol")

    def __getattr__(self, name: str) -> Any:
        return getattr(self._simulation, name)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(values: Any) -> bool:
    if isinstance(values, Mapping):
        return all(finite(v) for v in values.values())
    if isinstance(values, (list, tuple)):
        return all(finite(v) for v in values)
    try:
        return math.isfinite(float(values))
    except (TypeError, ValueError):
        return False


def _base(name: str | None) -> str:
    return "" if name is None else str(name).replace("\\", "/").rsplit("/", 1)[-1]


def _part(name: str | None) -> str:
    base = _base(name)
    if base in {"ground", SURFACE_NAME}:
        return base
    for segment in ("Tarsus5", "Tarsus4", "Tarsus3", "Tarsus2", "Tarsus1",
                    "Tibia", "Femur", "Coxa"):
        if segment in base:
            return segment
    return "body"


def geometry_gate(contacts: Sequence[Mapping[str, Any]], *, state_finite: bool,
                  calibration_surface_unchanged: bool) -> dict[str, Any]:
    """Classify contacts without hiding findings behind one permissive boolean."""
    ground_contacts, surface_contacts, self_contacts = [], [], []
    proximal, body, distal = [], [], []
    support_surfaces: set[str] = set()
    for item in contacts:
        c = dict(item)
        names = (c.get("geom1"), c.get("geom2"))
        bases = {_base(x) for x in names}
        distance = float(c["distance"])
        fly_names = [x for x in names if _base(x) not in {"ground", SURFACE_NAME}]
        if "ground" in bases:
            ground_contacts.append(c)
            part = _part(fly_names[0] if fly_names else None)
            if part == "body" and distance < -MATERIAL_PENETRATION_TOLERANCE:
                body.append(c)
            elif part in {"Coxa", "Femur", "Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4"} and distance < -MATERIAL_PENETRATION_TOLERANCE:
                proximal.append(c)
            elif part == "Tarsus5":
                distal.append(c)
                if distance <= CONTACT_TOLERANCE:
                    support_surfaces.add("ground")
        elif SURFACE_NAME in bases:
            surface_contacts.append(c)
            if any(_part(x) == "Tarsus5" for x in fly_names) and distance <= CONTACT_TOLERANCE:
                support_surfaces.add("calibration_surface")
        elif len(fly_names) == 2:
            self_contacts.append(c)
    excessive_distal = [c for c in distal if float(c["distance"]) < -DISTAL_PENETRATION_TOLERANCE]
    labels = {
        "VALID_SUPPORT_CONTACT": bool(support_surfaces) and not body and not proximal and not excessive_distal,
        "NO_SUPPORT_CONTACT": not support_surfaces,
        "BODY_GROUND_PENETRATION": bool(body),
        "PROXIMAL_LEG_GROUND_PENETRATION": bool(proximal),
        "EXCESSIVE_DISTAL_PENETRATION": bool(excessive_distal),
        "SELF_COLLISION_PRESENT": bool(self_contacts),
        "CALIBRATION_SURFACE_CONTACT": bool(surface_contacts),
        "MIXED_SUPPORT_SURFACES": len(support_surfaces) > 1,
    }
    valid = (state_finite and calibration_surface_unchanged and labels["VALID_SUPPORT_CONTACT"]
             and not labels["MIXED_SUPPORT_SURFACES"])
    return {"valid": valid, "state_finite": state_finite,
            "calibration_surface_unchanged": calibration_surface_unchanged,
            "tolerances": {"material_penetration": MATERIAL_PENETRATION_TOLERANCE,
                           "distal_penetration": DISTAL_PENETRATION_TOLERANCE,
                           "contact": CONTACT_TOLERANCE},
            "classifications": labels, "support_surfaces": sorted(support_surfaces),
            "ground_contacts": ground_contacts, "calibration_surface_contacts": surface_contacts,
            "self_contacts": self_contacts, "body_penetrations": body,
            "proximal_penetrations": proximal, "distal_contacts": distal}


def derive_vertical_translation(geom_minima: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Derive one translation from actual Tarsus5 collision geometry, never sweep."""
    distal = [float(g["minimum_z"]) for g in geom_minima if _part(g["name"]) == "Tarsus5"]
    forbidden = [float(g["minimum_z"]) for g in geom_minima if _part(g["name"]) != "Tarsus5"]
    if not distal or not forbidden:
        return {"status": "INCOMPATIBLE", "reason": "missing distal or non-distal collision geometry"}
    dz = -min(distal)
    resulting_forbidden_min = min(forbidden) + dz
    if resulting_forbidden_min < -MATERIAL_PENETRATION_TOLERANCE:
        return {"status": "GEOMETRICALLY_INCOMPATIBLE_WITH_SIMPLE_VERTICAL_TRANSLATION",
                "translation_z": dz, "resulting_non_distal_minimum_z": resulting_forbidden_min}
    return {"status": "ANALYTIC_CANDIDATE", "translation_z": dz,
            "resulting_non_distal_minimum_z": resulting_forbidden_min,
            "derivation": "negative of the minimum actual Tarsus5 mesh-vertex height"}


def _physics(sim: Any) -> Any:
    for owner in (sim, getattr(sim, "env", None), getattr(sim, "_env", None)):
        if getattr(owner, "physics", None) is not None:
            return owner.physics
    raise RuntimeError("FlyGym simulation exposes no MuJoCo physics object")


def _name(mujoco: Any, model: Any, geom_id: int) -> str | None:
    value = mujoco.mj_id2name(getattr(model, "ptr", model), mujoco.mjtObj.mjOBJ_GEOM, geom_id)
    return None if value is None else str(value)


def _contacts(np: Any, mujoco: Any, model: Any, data: Any) -> list[dict[str, Any]]:
    return [{"geom1": _name(mujoco, model, int(c.geom1)),
             "geom2": _name(mujoco, model, int(c.geom2)), "distance": float(c.dist),
             "penetration_depth": max(0.0, -float(c.dist)), "position": np.asarray(c.pos).tolist()}
            for c in data.contact[:int(data.ncon)]]


def _minimum_z(np: Any, mujoco: Any, model: Any, data: Any, gid: int) -> tuple[float, str]:
    """Return exact primitive support or transformed mesh-vertex minimum."""
    center = np.asarray(data.geom_xpos[gid], dtype=float)
    rotation = np.asarray(data.geom_xmat[gid], dtype=float).reshape(3, 3)
    size = np.asarray(model.geom_size[gid], dtype=float)
    kind = int(model.geom_type[gid])
    if kind == int(mujoco.mjtGeom.mjGEOM_MESH):
        mesh = int(model.geom_dataid[gid]); start = int(model.mesh_vertadr[mesh]); count = int(model.mesh_vertnum[mesh])
        vertices = np.asarray(model.mesh_vert[start:start + count], dtype=float)
        return float(np.min(vertices @ rotation[2, :] + center[2])), "transformed_mesh_vertices"
    if kind == int(mujoco.mjtGeom.mjGEOM_SPHERE):
        support = size[0]
    elif kind in (int(mujoco.mjtGeom.mjGEOM_CAPSULE), int(mujoco.mjtGeom.mjGEOM_CYLINDER)):
        axis_z = abs(rotation[2, 2]); radial = math.sqrt(max(0.0, 1.0 - axis_z * axis_z))
        support = (size[1] * axis_z + size[0] if kind == int(mujoco.mjtGeom.mjGEOM_CAPSULE)
                   else size[1] * axis_z + size[0] * radial)
    elif kind == int(mujoco.mjtGeom.mjGEOM_BOX):
        support = float(np.sum(np.abs(rotation[2, :]) * size))
    elif kind == int(mujoco.mjtGeom.mjGEOM_ELLIPSOID):
        support = float(np.linalg.norm(rotation[2, :] * size))
    else:
        return float(center[2] - model.geom_rbound[gid]), "conservative_geom_rbound"
    return float(center[2] - support), "analytic_primitive_support"


def _source_audit(flygym: Any) -> dict[str, Any]:
    root = Path(flygym.__file__).resolve().parent
    resources = {}
    for pose in ("stretch", "tripod", "zero"):
        matches = list(root.rglob(f"pose_{pose}.yaml"))
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one installed pose_{pose}.yaml")
        path = matches[0]
        yaml = importlib.import_module("yaml")
        resources[pose] = {"path": str(path), "relative_path": path.relative_to(root).as_posix(),
                           "sha256": _sha(path), "definition": yaml.safe_load(path.read_text(encoding="utf-8"))}
    source_files = [p for p in root.rglob("*.py") if p.is_file()]
    evidence = []
    for path in source_files:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for number, line in enumerate(lines, 1):
            low = line.lower()
            if any(term in low for term in ('init_pose="tripod"', "init_pose='tripod'", "pose_tripod", "walking pose", "stretch")):
                evidence.append({"path": path.relative_to(root).as_posix(), "line": number, "text": line.strip()})
    return {"package_root": str(root), "pose_resources": resources,
            "source_evidence": evidence,
            "kinematic_pose_source": {"path": inspect.getsourcefile(importlib.import_module("flygym.state.kinematic_pose")),
                                      "sha256": _sha(Path(inspect.getsourcefile(importlib.import_module("flygym.state.kinematic_pose"))))},
            "finding": "tripod is named static pose data; loading it supplies no controller or dynamic assistance"}


def _make_sim(flygym: Any, pose: Mapping[str, Any], surface: Mapping[str, Any]) -> StepForbidden:
    kwargs = {"init_pose": pose["init_pose"], "enable_adhesion": False, "control": "position",
              "contact_sensor_placements": [f"{leg}{seg}" for leg in LEGS for seg in ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")]}
    if pose["spawn_pos"] is not None:
        kwargs["spawn_pos"] = tuple(pose["spawn_pos"])
    fly = flygym.Fly(**kwargs)
    arena = importlib.import_module("flygym.arena").FlatTerrain()
    arena.root_element.worldbody.add("geom", name=surface["name"], type="box", size=surface["half_size"],
                                     pos=surface["position"], rgba=(.9, .2, .2, 1), contype=1, conaffinity=1)
    cls = getattr(flygym, "SingleFlySimulation", None) or importlib.import_module("flygym.simulation").SingleFlySimulation
    return StepForbidden(cls(fly=fly, arena=arena, cameras=[], timestep=.0001))


def windows_audit() -> dict[str, Any]:
    """Run reset/forward-only inspection in the validated Windows environment."""
    np = importlib.import_module("numpy"); flygym = importlib.import_module("flygym"); mujoco = importlib.import_module("mujoco")
    if importlib.metadata.version("flygym") != "1.2.1":
        raise RuntimeError("M7C-B2 requires installed FlyGym == 1.2.1")
    inherited = json.loads(M7C_AUDIT.read_text(encoding="utf-8"))["calibration_surface"]
    surface = {"name": inherited["name"], "position": inherited["position"], "half_size": inherited["half_size"]}
    results = []
    for pose in POSES:
        sim = _make_sim(flygym, pose, surface)
        try:
            reset = sim.reset()  # initialization, not a physics transition
            physics = _physics(sim); model, data = physics.model, physics.data
            if getattr(physics, "forward", None): physics.forward()
            else: mujoco.mj_forward(getattr(model, "ptr", model), getattr(data, "ptr", data))
            obs = reset[0] if isinstance(reset, tuple) else reset
            if getattr(sim, "get_observation", None): obs = sim.get_observation()
            geoms = []
            for gid in range(int(model.ngeom)):
                name = _name(mujoco, model, gid)
                if not str(name).startswith(("0/", "1/")) or not (int(model.geom_contype[gid]) or int(model.geom_conaffinity[gid])): continue
                minimum, method = _minimum_z(np, mujoco, model, data, gid)
                geoms.append({"name": name, "center": np.asarray(data.geom_xpos[gid]).tolist(),
                              "geom_rbound": float(model.geom_rbound[gid]), "minimum_z": minimum,
                              "minimum_method": method})
            contact_rows = _contacts(np, mujoco, model, data)
            surface_gid = next(i for i in range(int(model.ngeom)) if _base(_name(mujoco, model, i)) == SURFACE_NAME)
            unchanged = (np.array_equal(np.asarray(model.geom_size[surface_gid]), np.asarray(surface["half_size"])) and
                         np.array_equal(np.asarray(data.geom_xpos[surface_gid]), np.asarray(surface["position"])))
            joints = np.asarray(obs["joints"]); joints = joints[0] if joints.ndim == 2 else joints
            if joints.size != 42:
                raise RuntimeError(f"expected 42 controlled joint positions, got {joints.size}")
            state = {"root_xyz": np.asarray(data.qpos[:3]).tolist(), "root_orientation_wxyz": np.asarray(data.qpos[3:7]).tolist(),
                     "qpos": np.asarray(data.qpos).tolist(), "qvel": np.asarray(data.qvel).tolist(),
                     "controlled_joint_positions": joints.tolist()}
            is_finite = finite(state)
            gate = geometry_gate(contact_rows, state_finite=is_finite, calibration_surface_unchanged=unchanged)
            feet = [g for g in geoms if _part(g["name"]) == "Tarsus5"]
            derivation = None if gate["support_surfaces"] else derive_vertical_translation(geoms)
            eligible = is_finite and not gate["classifications"]["BODY_GROUND_PENETRATION"] and not gate["classifications"]["PROXIMAL_LEG_GROUND_PENETRATION"]
            results.append({"pose": dict(pose), "state": state, "finite_state": is_finite,
                            "collision_enabled_fly_geometries": geoms, "distal_tarsus5": feet,
                            "contacts": contact_rows, "geometry_gate": gate,
                            "analytic_spawn_height_correction": derivation,
                            "candidate_eligible": eligible,
                            "usable_distal_support_geometry": "collision-enabled Tarsus5 mesh vertices/contact pairs, not its bounding sphere"})
        finally:
            if getattr(sim, "close", None): sim.close()
    report = {"schema": "M7C-B2-POSE-GEOMETRY-AUDIT.1", "status": "COMPLETE",
              "flygym_version": importlib.metadata.version("flygym"),
              "mujoco_version": getattr(mujoco, "__version__", importlib.metadata.version("mujoco")),
              "installed_source": _source_audit(flygym), "pose_audits": results,
              "protocol": {"brain_constructed": False, "neural_transitions": 0, "physics_transitions": 0,
                           "sim_step_prohibited": True, "adhesion_enabled": False,
                           "gait_controller": False, "balance_controller": False, "walking_reference_trajectory": False,
                           "reward_rl_ai": False, "height_sweep": False, "optimizer": False,
                           "adaptive_candidate_generation": False, "calibration_surface_changed": False},
              "statement": "No dynamics were executed."}
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows-audit", action="store_true", required=True)
    parser.parse_args(argv)
    windows_audit()
    print("M7C-B2 ZERO-TRANSITION WINDOWS POSE-GEOMETRY AUDIT COMPLETE")


if __name__ == "__main__":
    main()
