"""M7C-B3 analytic tripod support-height audit (zero transitions only).

The Windows entry point constructs the unmodified static tripod twice: once at
z=0.5 to measure collision geometry and, only if the analytic interval is
feasible, once at the derived height.  It never calls ``sim.step`` and has no
MaleCNS dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import m7c_b2_pose_geometry_audit as b2

HERE = Path(__file__).resolve().parent
SOURCE_B2 = HERE / "interface_output" / "m7c_initial_stability" / "m7c_b2_pose_geometry_audit.json"
OUTPUT = HERE / "interface_output" / "m7c_initial_stability" / "m7c_b3_tripod_support_height.json"
ORIGINAL_SPAWN_Z = 0.5
ALLOWED_FLOOR_PARTS = tuple(f"{leg}Tarsus{segment}" for leg in b2.LEGS for segment in range(1, 6))
MATERIAL_TOLERANCE = b2.MATERIAL_PENETRATION_TOLERANCE
DISTAL_TOLERANCE = b2.DISTAL_PENETRATION_TOLERANCE
CONTACT_TOLERANCE = b2.CONTACT_TOLERANCE


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_allowed_floor_geom(name: str | None, allowed: Sequence[str] = ALLOWED_FLOOR_PARTS) -> bool:
    base = b2._base(name)
    return any(base.endswith(part) for part in allowed)


def solve_vertical_translation(geometries: Sequence[Mapping[str, Any]],
                               allowed: Sequence[str] = ALLOWED_FLOOR_PARTS) -> dict[str, Any]:
    """Solve the exact one-dimensional constraints; never sweep or optimize."""
    support = [g for g in geometries if is_allowed_floor_geom(str(g["name"]), allowed)]
    forbidden = [g for g in geometries if not is_allowed_floor_geom(str(g["name"]), allowed)]
    if not support or not forbidden:
        return {"classification": "TRIPOD_SIMPLE_VERTICAL_TRANSLATION_INFEASIBLE",
                "reason": "missing support or forbidden collision geometry", "analytic_dz": None}
    forbidden_required = max(0.0, max(-MATERIAL_TOLERANCE - float(g["minimum_z"]) for g in forbidden))
    distal_clearance_required = max(0.0, max(-DISTAL_TOLERANCE - float(g["minimum_z"]) for g in support))
    lower = max(forbidden_required, distal_clearance_required)
    contact_intervals = []
    feasible = []
    for geom in support:
        z = float(geom["minimum_z"])
        interval = [max(0.0, -CONTACT_TOLERANCE - z), CONTACT_TOLERANCE - z]
        if interval[0] <= interval[1]:
            contact_intervals.append({"geometry": geom["name"], "interval": interval})
            clipped = [max(lower, interval[0]), interval[1]]
            if clipped[0] <= clipped[1]:
                feasible.append({"support_geometry": geom["name"], "interval": clipped})
    if not feasible:
        return {"classification": "TRIPOD_SIMPLE_VERTICAL_TRANSLATION_INFEASIBLE",
                "forbidden_required_dz": forbidden_required,
                "distal_penetration_required_dz": distal_clearance_required,
                "distal_contact_dz_intervals": contact_intervals,
                "feasible_dz_intervals": [], "analytic_dz": None}
    dz = min(item["interval"][0] for item in feasible)
    return {"classification": "TRIPOD_ANALYTIC_SUPPORT_HEIGHT_FOUND",
            "forbidden_required_dz": forbidden_required,
            "distal_penetration_required_dz": distal_clearance_required,
            "distal_contact_dz_intervals": contact_intervals,
            "feasible_dz_intervals": feasible, "analytic_dz": dz,
            "corrected_spawn_z": ORIGINAL_SPAWN_Z + dz,
            "selection_rule": "minimum upward boundary satisfying forbidden, distal-penetration, and contact constraints"}


def eligibility(gate: Mapping[str, Any]) -> bool:
    return b2.candidate_eligible(gate)


def support_geometry_gate(contacts: Sequence[Mapping[str, Any]], *, state_finite: bool,
                          calibration_surface_unchanged: bool) -> dict[str, Any]:
    """B3 gate using FlyGym's complete Tarsus1--5 floor support set."""
    ground, surface, self_contacts, forbidden, distal, excessive = [], [], [], [], [], []
    for raw in contacts:
        contact = dict(raw); names = (contact.get("geom1"), contact.get("geom2"))
        bases = {b2._base(name) for name in names}; distance = float(contact["distance"])
        fly_names = [name for name in names if b2._base(name) not in {"ground", b2.SURFACE_NAME}]
        if "ground" in bases:
            ground.append(contact)
            if fly_names and is_allowed_floor_geom(fly_names[0]):
                distal.append(contact)
                if distance < -DISTAL_TOLERANCE: excessive.append(contact)
            elif distance < -MATERIAL_TOLERANCE:
                forbidden.append(contact)
        elif b2.SURFACE_NAME in bases:
            surface.append(contact)
        elif len(fly_names) == 2:
            self_contacts.append(contact)
    supported = any(float(c["distance"]) <= CONTACT_TOLERANCE for c in distal)
    labels = {"VALID_SUPPORT_CONTACT": supported and not forbidden and not excessive,
              "NO_SUPPORT_CONTACT": not supported, "FORBIDDEN_GROUND_PENETRATION": bool(forbidden),
              "EXCESSIVE_DISTAL_PENETRATION": bool(excessive), "SELF_COLLISION_PRESENT": bool(self_contacts),
              "CALIBRATION_SURFACE_CONTACT": bool(surface)}
    valid = bool(state_finite and calibration_surface_unchanged and labels["VALID_SUPPORT_CONTACT"])
    return {"valid": valid, "state_finite": state_finite,
            "calibration_surface_unchanged": calibration_surface_unchanged,
            "classifications": labels, "ground_contacts": ground,
            "forbidden_ground_penetrations": forbidden, "distal_ground_contacts": distal,
            "excessive_distal_penetrations": excessive, "calibration_surface_contacts": surface,
            "self_contacts": self_contacts}


def _fly_geometries(np: Any, mujoco: Any, model: Any, data: Any) -> list[dict[str, Any]]:
    rows = []
    for gid in range(int(model.ngeom)):
        name = b2._name(mujoco, model, gid)
        base = b2._base(name)
        if base in {"ground", b2.SURFACE_NAME, ""}:
            continue
        # FlyGym can enable floor collision through explicit pairs even when a
        # geom's masks are zero, so masks must not be used to omit fly geoms.
        if not any(token in base for token in ("Coxa", "Femur", "Tibia", "Tarsus", "Thorax", "Head", "Abdomen")):
            continue
        minimum, method = b2._minimum_z(np, mujoco, model, data, gid)
        rows.append({"name": name, "minimum_z": minimum, "minimum_method": method,
                     "contype": int(model.geom_contype[gid]), "conaffinity": int(model.geom_conaffinity[gid])})
    return rows


def _inspect(sim: Any, np: Any, mujoco: Any, expected_joints: Sequence[float] | None = None) -> dict[str, Any]:
    reset = sim.reset()
    physics = b2._physics(sim); model, data = physics.model, physics.data
    if getattr(physics, "forward", None): physics.forward()
    else: mujoco.mj_forward(getattr(model, "ptr", model), getattr(data, "ptr", data))
    obs = reset[0] if isinstance(reset, tuple) else reset
    if getattr(sim, "get_observation", None): obs = sim.get_observation()
    joints = np.asarray(obs["joints"]); joints = joints[0] if joints.ndim == 2 else joints
    joint_values = joints.tolist()
    return {"finite_state": b2.finite({"qpos": np.asarray(data.qpos).tolist(), "qvel": np.asarray(data.qvel).tolist()}),
            "root_xyz": np.asarray(data.qpos[:3]).tolist(), "controlled_joint_positions": joint_values,
            "all_42_tripod_joints_unchanged": len(joint_values) == 42 and
                (expected_joints is None or np.array_equal(joints, np.asarray(expected_joints))),
            "collision_geometries": _fly_geometries(np, mujoco, model, data),
            "contacts": b2._contacts(np, mujoco, model, data)}


def windows_audit() -> dict[str, Any]:
    np = importlib.import_module("numpy"); flygym = importlib.import_module("flygym"); mujoco = importlib.import_module("mujoco")
    if importlib.metadata.version("flygym") != "1.2.1" or getattr(mujoco, "__version__", "") != "3.2.7":
        raise RuntimeError("M7C-B3 requires FlyGym 1.2.1 and MuJoCo 3.2.7")
    inherited = json.loads(b2.M7C_AUDIT.read_text(encoding="utf-8"))["calibration_surface"]
    surface = {"name": inherited["name"], "position": inherited["position"], "half_size": inherited["half_size"]}
    pose = {"id": "tripod_analytic_source", "init_pose": "tripod", "spawn_pos": [0, 0, ORIGINAL_SPAWN_Z]}
    source_sim = b2._make_sim(flygym, pose, surface)
    try: source = _inspect(source_sim, np, mujoco)
    finally: source_sim.close()
    solution = solve_vertical_translation(source["collision_geometries"])
    reconstructed = None
    if solution["analytic_dz"] is not None:
        pose["spawn_pos"] = [0, 0, solution["corrected_spawn_z"]]
        final_sim = b2._make_sim(flygym, pose, surface)
        try: reconstructed = _inspect(final_sim, np, mujoco, source["controlled_joint_positions"])
        finally: final_sim.close()
        gate = support_geometry_gate(reconstructed["contacts"], state_finite=reconstructed["finite_state"], calibration_surface_unchanged=True)
        reconstructed["geometry_gate"] = gate
        reconstructed["future_physics_eligible"] = eligibility(gate) and reconstructed["all_42_tripod_joints_unchanged"]
    tripod_resource = json.loads(SOURCE_B2.read_text(encoding="utf-8"))["installed_source"]["pose_resources"]["tripod"]
    report = {"schema": "M7C-B3-TRIPOD-SUPPORT-HEIGHT.1", "status": "COMPLETE",
              "classifications": [solution["classification"]], "source_m7c_b2": {"path": str(SOURCE_B2), "sha256": sha256(SOURCE_B2)},
              "tripod_pose": tripod_resource, "original_spawn_z": ORIGINAL_SPAWN_Z,
              "allowed_floor_contact_geometry": list(ALLOWED_FLOOR_PARTS),
              "forbidden_geometry": "all fly collision geometry other than configured Tarsus1-Tarsus5 geoms",
              "analytic_solution": solution, "source_zero_step": source, "zero_step_reconstruction": reconstructed,
              "self_collision_assessment": "SELF_COLLISION_REQUIRES_DYNAMICS_VALIDATION",
              "protocol": {"physics_transitions": 0, "neural_transitions": 0, "brain_constructed": False,
                           "sim_step_prohibited": True, "height_sweep": False, "optimizer": False,
                           "adhesion_enabled": False, "controller": False, "reward_rl_ai": False,
                           "calibration_surface_changed": False}}
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows-audit", action="store_true", required=True)
    parser.parse_args(argv); windows_audit()
    print("M7C-B3 WINDOWS ZERO-TRANSITION ANALYTIC SUPPORT AUDIT COMPLETE")


if __name__ == "__main__":
    main()
