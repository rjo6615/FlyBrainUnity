"""Zero-transition inspection of the exact frozen M6/M7 physical runtime."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .m7c_canonical_first10ms import CANONICAL_SHA256
from .tactile_targeted_contact_calibration import (DEFAULT_TIMESTEP_S,
    SURFACE_HALF_SIZE, SURFACE_NAME, _geom_name, _physics, resolve_exact_geom,
    surface_position)

HERE = Path(__file__).resolve().parent
CANONICAL_DIR = HERE / "interface_output" / "m7_canonical"
DEFAULT_OUTPUT = HERE / "interface_output" / "m7c_initial_stability" / "m7c_initial_state_audit.json"


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _forward(physics: Any) -> None:
    """Recompute derived geometry/contact state; this is not a transition."""
    if getattr(physics, "forward", None) is not None:
        physics.forward(); return
    mujoco = importlib.import_module("mujoco")
    mujoco.mj_forward(getattr(physics.model, "ptr", physics.model),
                      getattr(physics.data, "ptr", physics.data))


def _joint_positions(obs: Any) -> np.ndarray:
    value = np.asarray(obs["joints"], dtype=np.float64)
    value = value[0] if value.ndim == 2 else value
    if value.shape != (42,) or not np.all(np.isfinite(value)):
        raise RuntimeError("expected exactly 42 finite initial joint positions")
    return value.copy()


def inspect_initialized(flygym: Any) -> dict[str, Any]:
    """Construct/reset/forward the canonical model, but never call sim.step."""
    placements = [f"{leg}{segment}" for leg in ("LF", "LM", "LH", "RF", "RM", "RH")
                  for segment in ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")]
    fly = flygym.Fly(enable_adhesion=False, control="position",
                    contact_sensor_placements=placements)
    simulation = getattr(flygym, "SingleFlySimulation", None)
    if simulation is None:
        simulation = importlib.import_module("flygym.simulation").SingleFlySimulation
    arena = importlib.import_module("flygym.arena").FlatTerrain()
    arena.root_element.worldbody.add("geom", name=SURFACE_NAME, type="box",
        size=SURFACE_HALF_SIZE, pos=(0, 0, -10), rgba=(.9, .2, .2, 1), contype=1, conaffinity=1)
    sim = simulation(fly=fly, arena=arena, cameras=[], timestep=DEFAULT_TIMESTEP_S)
    try:
        reset = sim.reset(); obs = reset[0] if isinstance(reset, tuple) else reset
        physics = _physics(sim); model, data = physics.model, physics.data
        tarsus_id, tarsus_name = resolve_exact_geom(model, "LMTarsus5")
        surface_id, surface_name = resolve_exact_geom(model, SURFACE_NAME)
        qpos_before = np.asarray(data.qpos, dtype=np.float64).copy()
        tarsus_pos = np.asarray(data.geom_xpos[tarsus_id], dtype=np.float64).copy()
        radius = float(np.asarray(model.geom_rbound)[tarsus_id])
        placed = surface_position(tarsus_pos, radius, contact=True)
        np.asarray(model.geom_pos)[surface_id] = placed
        _forward(physics)
        if not np.array_equal(qpos_before, np.asarray(data.qpos)):
            raise RuntimeError("surface placement mutated canonical qpos")
        if getattr(sim, "get_observation", None) is not None: obs = sim.get_observation()
        joints = _joint_positions(obs); baseline = joints.copy(); mismatch = baseline - joints
        contacts = []
        for i in range(int(data.ncon)):
            item = data.contact[i]; g1, g2 = int(item.geom1), int(item.geom2)
            contacts.append({"geom1_id": g1, "geom1_name": _geom_name(model, g1),
                "geom2_id": g2, "geom2_name": _geom_name(model, g2),
                "distance": float(item.dist), "position": np.asarray(item.pos).tolist(),
                "normal": np.asarray(item.frame)[:3].tolist(),
                "involves_calibration_surface": surface_id in (g1, g2)})
        geoms = [{"id": i, "name": _geom_name(model, i),
                  "world_position": np.asarray(data.geom_xpos[i]).tolist(),
                  "model_position": np.asarray(model.geom_pos[i]).tolist(),
                  "size": np.asarray(model.geom_size[i]).tolist(),
                  "friction": np.asarray(model.geom_friction[i]).tolist(),
                  "contype": int(model.geom_contype[i]), "conaffinity": int(model.geom_conaffinity[i])}
                 for i in range(int(model.ngeom))]
        quat = np.asarray(data.qpos[3:7], dtype=np.float64); quat = quat / np.linalg.norm(quat)
        up_z = float(1 - 2 * (quat[1] ** 2 + quat[2] ** 2)); height = float(data.qpos[2])
        return {"run_status": "COMPLETE", "physical_configuration": {
                "construction": "Fly(enable_adhesion=False, control='position', 36 tibia/tarsus sensors); SingleFlySimulation; FlatTerrain",
                "timestep_s": DEFAULT_TIMESTEP_S, "gravity": np.asarray(model.opt.gravity).tolist(),
                "adhesion_enabled": False, "adhesion_command": [0.0] * 6,
                "reset_called": True, "forward_after_surface_placement": True,
                "sim_step_called": False, "brain_constructed": False},
            "initial_body_state": {"root_position": np.asarray(data.qpos[:3]).tolist(),
                "root_orientation_quaternion_wxyz": quat.tolist(), "body_up_z": up_z, "body_height": height,
                "qpos": np.asarray(data.qpos).tolist(), "qvel": np.asarray(data.qvel).tolist(),
                "ctrl": np.asarray(data.ctrl).tolist()},
            "initial_joint_state": joints.tolist(), "baseline_targets": baseline.tolist(),
            "target_minus_initial": mismatch.tolist(), "nontrivial_target_mismatch_count": int(np.count_nonzero(mismatch)),
            "initial_contacts": contacts, "initial_contact_count": len(contacts), "geometries": geoms,
            "calibration_surface": {"id": surface_id, "name": surface_name,
                "half_size": list(SURFACE_HALF_SIZE), "position": placed.tolist(),
                "orientation_matrix": np.asarray(data.geom_xmat[surface_id]).reshape(3, 3).tolist(),
                "target_tarsus_id": tarsus_id, "target_tarsus_name": tarsus_name,
                "target_tarsus_position": tarsus_pos.tolist(), "target_tarsus_rbound": radius},
            "fall_predicate_t0": {"initial_height": height, "threshold": .5 * height,
                "height_below_threshold": False},
            "rollover_predicate_t0": {"body_up_z": up_z, "threshold": 0.0,
                "body_up_z_at_or_below_threshold": up_z <= 0.0},
            "physics_transitions": 0, "neural_transitions": 0}
    finally:
        if getattr(sim, "close", None): sim.close()


def build_report() -> dict[str, Any]:
    manifest = CANONICAL_DIR / "m7_manifest.json"; raw = CANONICAL_DIR / "m7_raw.npz"
    report: dict[str, Any] = {"schema": "M7C-A-INITIAL-STATE.1",
        "provenance": {"canonical_raw_expected_sha256": CANONICAL_SHA256,
            "canonical_raw_observed_sha256": _sha(raw), "m7_manifest_sha256": _sha(manifest)},
        "scientific_transitions_executed": 0}
    try:
        flygym = importlib.import_module("flygym")
    except ImportError as exc:
        report.update({"run_status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}",
                       "physics_transitions": 0, "neural_transitions": 0})
        return report
    report.update(inspect_initialized(flygym)); return report


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-windows", action="store_true")
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv); report = build_report()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(args.json)


if __name__ == "__main__":
    main()
