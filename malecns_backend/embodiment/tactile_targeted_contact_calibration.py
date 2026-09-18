"""M5D-2C targeted, environment-only LM Tarsus5 contact calibration.

Contact truth is the exact MuJoCo geom pair.  Force observations never create
ground truth, and this module intentionally contains no neural dependencies.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import importlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from .m5d_tarsal_contact_load import LEGS
from .tactile_contact import DISTAL_OFFSET, DISTAL_SEGMENT

DEFAULT_LEG = "LM"
DEFAULT_TIMESTEP_S = 0.0001
ENGINEERING_THRESHOLD = 1e-12
SURFACE_NAME = "m5d2c_calibration_surface"
SURFACE_HALF_SIZE = (0.025, 0.025, 0.002)
CONTROL_GAP = 0.01
CONTACT_PENETRATION = 0.0001
HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "interface_output" / "tactile_targeted_contact_calibration.json"


@dataclass(frozen=True)
class ContactPair:
    geom1_id: int
    geom1_name: str | None
    geom2_id: int
    geom2_name: str | None


def _basename(name: str | None) -> str | None:
    return None if name is None else name.rsplit("/", 1)[-1]


def resolve_exact_geom(model, expected_basename: str) -> tuple[int, str]:
    """Resolve exactly one geom by namespace-independent MuJoCo basename."""
    matches = [(i, _geom_name(model, i)) for i in range(int(model.ngeom))]
    matches = [(i, name) for i, name in matches if _basename(name) == expected_basename]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one geom named {expected_basename!r}; found {matches!r}")
    geom_id, name = matches[0]
    return geom_id, str(name)


def contact_metadata(pairs: Iterable[ContactPair], tarsus_id: int,
                     surface_id: int) -> dict:
    """Return contact evidence; only the unordered exact pair is accepted."""
    pairs = tuple(pairs)
    target = frozenset((int(tarsus_id), int(surface_id)))
    selected = [pair for pair in pairs
                if frozenset((pair.geom1_id, pair.geom2_id)) == target]
    return {
        "contact_count": len(pairs),
        "selected_pair_present": bool(selected),
        "selected_contact_pairs": [asdict(pair) for pair in selected],
        "all_contact_pairs": [asdict(pair) for pair in pairs],
    }


def magnitude_statistics(values: Iterable[float]) -> dict:
    values = np.asarray(tuple(values), dtype=np.float64)
    if not values.size:
        return {"count": 0, "min": None, "max": None, "mean": None,
                "median": None, "percentiles": {}, "exact_zero_fraction": None}
    return {"count": int(values.size), "min": float(values.min()),
            "max": float(values.max()), "mean": float(values.mean()),
            "median": float(np.median(values)),
            "percentiles": {str(p): float(np.percentile(values, p))
                            for p in (1, 5, 25, 50, 75, 95, 99)},
            "exact_zero_fraction": float(np.mean(values == 0))}


def classify_correspondence(confirmed_magnitudes: Iterable[float]) -> str:
    values = np.asarray(tuple(confirmed_magnitudes), dtype=np.float64)
    if not values.size:
        return "NO_VERIFIED_CONTACT"
    if np.any(values != 0):
        return "SENSOR_CORRESPONDENCE_CONFIRMED"
    return "CONTACT_CONFIRMED_SENSOR_ZERO"


def evaluate_threshold(no_contact: Iterable[float], confirmed_contact: Iterable[float],
                       correspondence: str,
                       threshold: float = ENGINEERING_THRESHOLD) -> dict:
    """Evaluate the provisional threshold only after sensor correspondence."""
    no_contact = np.asarray(tuple(no_contact), dtype=np.float64)
    confirmed = np.asarray(tuple(confirmed_contact), dtype=np.float64)
    result = {"threshold": float(threshold), "comparison": "magnitude > threshold",
              "evaluated": correspondence == "SENSOR_CORRESPONDENCE_CONFIRMED",
              "false_positives": None, "false_negatives": None,
              "classification": "CALIBRATION_INCONCLUSIVE"}
    if result["evaluated"]:
        result["false_positives"] = int(np.count_nonzero(no_contact > threshold))
        result["false_negatives"] = int(np.count_nonzero(confirmed <= threshold))
        result["classification"] = ("THRESHOLD_ACCEPTED" if not result["false_positives"]
                                    and not result["false_negatives"]
                                    else "THRESHOLD_REQUIRES_REVISION")
    return result


def surface_position(tarsus_position: Iterable[float], tarsus_radius: float,
                     *, contact: bool) -> np.ndarray:
    """Place box top below the conservative Tarsus5 world-space lower bound."""
    position = np.asarray(tuple(tarsus_position), dtype=np.float64).copy()
    lower_z = position[2] - float(tarsus_radius)
    delta = CONTACT_PENETRATION if contact else -CONTROL_GAP
    position[2] = lower_z - SURFACE_HALF_SIZE[2] + delta
    return position


def serialized_report(value: Mapping[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                      allow_nan=False) + "\n"


def _physics(sim):
    for owner in (sim, getattr(sim, "env", None), getattr(sim, "_env", None)):
        if getattr(owner, "physics", None) is not None:
            return owner.physics
    raise RuntimeError("FlyGym simulation exposes no MuJoCo physics object")


def _geom_name(model, geom_id: int) -> str | None:
    method = getattr(model, "id2name", None)
    if method is not None:
        for args in ((geom_id, "geom"), ("geom", geom_id)):
            try:
                name = method(*args)
            except (TypeError, ValueError, KeyError):
                continue
            if name is not None:
                return str(name)
    mujoco = importlib.import_module("mujoco")
    name = mujoco.mj_id2name(getattr(model, "ptr", model),
                             mujoco.mjtObj.mjOBJ_GEOM, geom_id)
    return None if name is None else str(name)


def _pairs(physics) -> tuple[ContactPair, ...]:
    return tuple(ContactPair(int(physics.data.contact[i].geom1),
                             _geom_name(physics.model, int(physics.data.contact[i].geom1)),
                             int(physics.data.contact[i].geom2),
                             _geom_name(physics.model, int(physics.data.contact[i].geom2)))
                 for i in range(int(physics.data.ncon)))


def _forward(physics) -> None:
    if getattr(physics, "forward", None) is not None:
        physics.forward()
    else:
        mujoco = importlib.import_module("mujoco")
        mujoco.mj_forward(getattr(physics.model, "ptr", physics.model),
                          getattr(physics.data, "ptr", physics.data))


def _make_arena(flygym):
    arena_module = importlib.import_module("flygym.arena")
    arena = arena_module.FlatTerrain()
    arena.root_element.worldbody.add(
        "geom", name=SURFACE_NAME, type="box", size=SURFACE_HALF_SIZE,
        pos=(0, 0, -10), rgba=(0.9, 0.2, 0.2, 1), contype=1, conaffinity=1)
    return arena


def _run_condition(flygym, leg: str, duration_s: float, timestep_s: float,
                   *, contact: bool) -> dict:
    placements = [f"{item_leg}{segment}" for item_leg in LEGS for segment in
                  ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")]
    fly = flygym.Fly(enable_adhesion=False, control="position",
                    contact_sensor_placements=placements)
    simulation_type = getattr(flygym, "SingleFlySimulation", None)
    if simulation_type is None:
        simulation_type = importlib.import_module("flygym.simulation").SingleFlySimulation
    sim = simulation_type(fly=fly, arena=_make_arena(flygym), cameras=[], timestep=timestep_s)
    try:
        reset = sim.reset()
        obs = reset[0] if isinstance(reset, tuple) else reset
        physics = _physics(sim)
        tarsus_id, tarsus_name = resolve_exact_geom(physics.model, f"{leg}{DISTAL_SEGMENT}")
        surface_id, surface_name = resolve_exact_geom(physics.model, SURFACE_NAME)
        qpos_before = np.asarray(physics.data.qpos, dtype=np.float64).copy()
        tarsus_pos = np.asarray(physics.data.geom_xpos[tarsus_id], dtype=np.float64).copy()
        radius = float(np.asarray(physics.model.geom_rbound)[tarsus_id])
        placed = surface_position(tarsus_pos, radius, contact=contact)
        np.asarray(physics.model.geom_pos)[surface_id] = placed
        _forward(physics)
        qpos_after = np.asarray(physics.data.qpos, dtype=np.float64).copy()
        if not np.array_equal(qpos_before, qpos_after):
            raise RuntimeError("environment placement changed fly qpos")
        refresh = getattr(sim, "get_observation", None)
        if refresh is not None:
            obs = refresh()
        joints = np.asarray(obs["joints"], dtype=np.float64)
        held = (joints[0] if joints.ndim == 2 else joints).copy()
        samples = []
        for step in range(int(np.ceil(duration_s / timestep_s)) + 1):
            vector = np.asarray(obs["contact_forces"], dtype=np.float64)[LEGS.index(leg) * 6 + DISTAL_OFFSET]
            metadata = contact_metadata(_pairs(physics), tarsus_id, surface_id)
            samples.append({"simulation_time_s": float(physics.data.time),
                            "raw_tarsus5_vector": [float(x) for x in vector],
                            "magnitude": float(np.linalg.norm(vector)),
                            "mujoco_ncon": int(physics.data.ncon),
                            "selected_pair_present": metadata["selected_pair_present"],
                            "ground_truth_state": "KNOWN_CONTACT" if metadata["selected_pair_present"] else "NO_CONTACT",
                            "contact_metadata": metadata})
            if step < int(np.ceil(duration_s / timestep_s)):
                obs = sim.step({"joints": held, "adhesion": np.zeros(6)})[0]
        return {"samples": samples,
                "tarsus_geom": {"id": tarsus_id, "name": tarsus_name},
                "surface_geom": {"id": surface_id, "name": surface_name},
                "placement": {"tarsus_world_position": tarsus_pos.tolist(),
                              "tarsus_conservative_radius": radius,
                              "tarsus_lower_bound_z": float(tarsus_pos[2] - radius),
                              "surface_position": placed.tolist(),
                              "surface_half_size": list(SURFACE_HALF_SIZE),
                              "gap": 0.0 if contact else CONTROL_GAP,
                              "penetration": CONTACT_PENETRATION if contact else 0.0},
                "pose_proof": {"qpos_before": qpos_before.tolist(),
                               "qpos_after_surface_placement": qpos_after.tolist(),
                               "exactly_equal": True}}
    finally:
        if getattr(sim, "close", None):
            sim.close()


def build_report(*, live: bool = False, leg: str = DEFAULT_LEG,
                 duration_s: float = 0.05, timestep_s: float = DEFAULT_TIMESTEP_S) -> dict:
    if leg not in LEGS:
        raise ValueError(f"leg must be one of {LEGS}")
    if duration_s <= 0 or timestep_s <= 0:
        raise ValueError("durations must be positive")
    base = {"schema_version": "M5D-2C.0", "selected_leg": leg,
            "selected_segment": DISTAL_SEGMENT, "duration_s": float(duration_s),
            "timestep_s": float(timestep_s), "units": "model force units",
            "surface_placement_method": "Tarsus5 geom_xpos z minus geom_rbound; box top has fixed 0.01 control gap or fixed 0.0001 penetration",
            "environmental_intervention_only": True, "neural_propagation": "NOT_RUN",
            "male_cns_used": False}
    if not live:
        correspondence = "NO_VERIFIED_CONTACT"
        base.update({"run_status": "NOT_RUN",
                     "reason": "invoke with --live in the validated FlyGym/MuJoCo environment",
                     "control": {"statistics": magnitude_statistics(())},
                     "contact": {"statistics": magnitude_statistics(())},
                     "verified_contact_sample_count": 0,
                     "contact_force_nonzero_sample_count": 0,
                     "sensor_correspondence_classification": correspondence,
                     "threshold_evaluation": evaluate_threshold((), (), correspondence)})
        return base
    try:
        flygym = importlib.import_module("flygym")
    except ImportError as exc:
        base.update({"run_status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"})
        correspondence = "NO_VERIFIED_CONTACT"
        base.update({"control": {"statistics": magnitude_statistics(())},
                     "contact": {"statistics": magnitude_statistics(())},
                     "verified_contact_sample_count": 0, "contact_force_nonzero_sample_count": 0,
                     "sensor_correspondence_classification": correspondence,
                     "threshold_evaluation": evaluate_threshold((), (), correspondence)})
        return base
    control = _run_condition(flygym, leg, duration_s, timestep_s, contact=False)
    targeted = _run_condition(flygym, leg, duration_s, timestep_s, contact=True)
    control_reset = np.asarray(control["pose_proof"]["qpos_before"])
    contact_reset = np.asarray(targeted["pose_proof"]["qpos_before"])
    if not np.array_equal(control_reset, contact_reset):
        raise RuntimeError("control and contact fly reset poses differ")
    no_contact = [s["magnitude"] for s in control["samples"]
                  if not s["selected_pair_present"]]
    confirmed = [s["magnitude"] for s in targeted["samples"]
                 if s["selected_pair_present"]]
    correspondence = classify_correspondence(confirmed)
    base.update({"run_status": "COMPLETE",
                 "matched_pose_proof": {
                     "control_and_contact_reset_qpos_exactly_equal": True,
                     "no_root_or_joint_displacement_by_intervention": True,
                 },
                 "control": {**control, "statistics": magnitude_statistics(no_contact)},
                 "contact": {**targeted, "statistics": magnitude_statistics(confirmed)},
                 "verified_contact_sample_count": len(confirmed),
                 "contact_force_nonzero_sample_count": int(np.count_nonzero(confirmed)),
                 "sensor_correspondence_classification": correspondence,
                 "threshold_evaluation": evaluate_threshold(no_contact, confirmed, correspondence)})
    return base


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--leg", choices=LEGS, default=DEFAULT_LEG)
    parser.add_argument("--duration-s", type=float, default=0.05)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = build_report(live=args.live, leg=args.leg, duration_s=args.duration_s)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(serialized_report(report), encoding="utf-8")
    print(args.json)


if __name__ == "__main__":
    main()
