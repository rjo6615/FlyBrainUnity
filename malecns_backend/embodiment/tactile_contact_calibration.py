"""M5D-2B physical-only Tarsus5 contact calibration.

This module deliberately has no dependency on the neural runtime.  A contact
label comes from MuJoCo's contact table, never from the force observation.
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
# FlyGym model length units.  This is one fixed intervention, not a pose search.
CONTACT_BODY_Z_OFFSET = -0.1
HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "interface_output" / "tactile_contact_calibration.json"


@dataclass(frozen=True)
class ContactPair:
    geom1_id: int
    geom1_name: str | None
    geom2_id: int
    geom2_name: str | None


def contact_metadata(pairs: Iterable[ContactPair], selected_geom_ids: Iterable[int]) -> dict:
    """Summarize independent MuJoCo contact evidence for one distal segment."""
    pairs = tuple(pairs)
    selected = frozenset(int(value) for value in selected_geom_ids)
    involved = [pair for pair in pairs
                if pair.geom1_id in selected or pair.geom2_id in selected]
    return {
        "contact_count": len(pairs),
        "selected_tarsus5_involved": bool(involved),
        "selected_contact_pairs": [asdict(pair) for pair in involved],
        "all_contact_pairs": [asdict(pair) for pair in pairs],
    }


def magnitude_statistics(values: Iterable[float]) -> dict:
    values = np.asarray(tuple(values), dtype=np.float64)
    if not values.size:
        return {"count": 0, "min": None, "max": None, "mean": None,
                "median": None, "percentiles": {},
                "exact_zero_fraction": None, "nonzero_fraction": None}
    return {
        "count": int(values.size), "min": float(values.min()),
        "max": float(values.max()), "mean": float(values.mean()),
        "median": float(np.median(values)),
        "percentiles": {str(p): float(np.percentile(values, p))
                        for p in (1, 5, 25, 50, 75, 95, 99)},
        "exact_zero_fraction": float(np.mean(values == 0)),
        "nonzero_fraction": float(np.mean(values != 0)),
    }


def evaluate_threshold(no_contact: Iterable[float], confirmed_contact: Iterable[float],
                       threshold: float = ENGINEERING_THRESHOLD,
                       *, verified_contact_occurred: bool | None = None) -> dict:
    """Evaluate the existing strict ``magnitude > threshold`` decision."""
    no_contact = np.asarray(tuple(no_contact), dtype=np.float64)
    confirmed = np.asarray(tuple(confirmed_contact), dtype=np.float64)
    verified = bool(confirmed.size) if verified_contact_occurred is None else bool(verified_contact_occurred)
    false_positives = int(np.count_nonzero(no_contact > threshold))
    false_negatives = int(np.count_nonzero(confirmed <= threshold))
    if not verified or not confirmed.size:
        classification = "CALIBRATION_INCONCLUSIVE"
    elif false_positives or false_negatives:
        classification = "THRESHOLD_REQUIRES_REVISION"
    else:
        classification = "THRESHOLD_ACCEPTED"
    return {"threshold": float(threshold), "comparison": "magnitude > threshold",
            "false_positives": false_positives,
            "false_negatives": false_negatives, "classification": classification}


def serialized_report(value: Mapping[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                      allow_nan=False) + "\n"


def _physics(sim):
    for owner in (sim, getattr(sim, "env", None), getattr(sim, "_env", None)):
        physics = getattr(owner, "physics", None)
        if physics is not None:
            return physics
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


def _live_pairs(physics) -> tuple[ContactPair, ...]:
    model, data = physics.model, physics.data
    return tuple(ContactPair(int(data.contact[i].geom1), _geom_name(model, int(data.contact[i].geom1)),
                             int(data.contact[i].geom2), _geom_name(model, int(data.contact[i].geom2)))
                 for i in range(int(data.ncon)))


def _selected_geom_ids(model, placement: str) -> tuple[int, ...]:
    matches = []
    for geom_id in range(int(model.ngeom)):
        name = _geom_name(model, geom_id)
        if name and placement.lower() in name.lower():
            matches.append(geom_id)
    if not matches:
        raise RuntimeError(f"no MuJoCo geom name contains selected placement {placement!r}")
    return tuple(matches)


def _lower_body_once(physics, offset: float = CONTACT_BODY_Z_OFFSET) -> dict:
    """Apply one deterministic root-free-joint height adjustment and forward."""
    model, data = physics.model, physics.data
    types = np.asarray(model.jnt_type).reshape(-1)
    free = np.flatnonzero(types == 0)
    if free.size != 1:
        raise RuntimeError(f"expected one root free joint, found {free.size}")
    joint_id = int(free[0]); qpos_address = int(np.asarray(model.jnt_qposadr).reshape(-1)[joint_id])
    before = float(data.qpos[qpos_address + 2])
    data.qpos[qpos_address + 2] = before + offset
    forward = getattr(physics, "forward", None)
    if forward is not None:
        forward()
    else:
        mujoco = importlib.import_module("mujoco")
        mujoco.mj_forward(getattr(model, "ptr", model), getattr(data, "ptr", data))
    return {"joint_id": joint_id, "qpos_z_address": qpos_address + 2,
            "before": before, "offset": float(offset),
            "after": float(data.qpos[qpos_address + 2])}


def _run_condition(flygym, leg: str, duration_s: float, timestep_s: float,
                   *, establish_contact: bool) -> dict:
    Fly = flygym.Fly
    Simulation = getattr(flygym, "SingleFlySimulation", None)
    if Simulation is None:
        Simulation = importlib.import_module("flygym.simulation").SingleFlySimulation
    placements = [f"{item_leg}{segment}" for item_leg in LEGS for segment in
                  ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")]
    fly = Fly(enable_adhesion=False, control="position",
              contact_sensor_placements=placements)
    sim = Simulation(fly=fly, cameras=[], timestep=timestep_s)
    samples = []
    intervention = None
    try:
        reset = sim.reset(); obs = reset[0] if isinstance(reset, tuple) else reset
        physics = _physics(sim); selected_ids = _selected_geom_ids(physics.model, f"{leg}{DISTAL_SEGMENT}")
        if establish_contact:
            intervention = _lower_body_once(physics)
            # Refresh observations after the one pose operation without advancing time.
            refresh = getattr(sim, "get_observation", None)
            if refresh is not None:
                obs = refresh()
        joints = np.asarray(obs["joints"], dtype=np.float64)
        held = (joints[0] if joints.ndim == 2 else joints).copy()
        steps = int(np.ceil(duration_s / timestep_s))
        for step in range(steps + 1):
            vector = np.asarray(obs["contact_forces"], dtype=np.float64)[LEGS.index(leg) * 6 + DISTAL_OFFSET]
            metadata = contact_metadata(_live_pairs(physics), selected_ids)
            samples.append({"simulation_time_s": float(physics.data.time),
                            "raw_tarsus5_vector": [float(x) for x in vector],
                            "magnitude": float(np.linalg.norm(vector)),
                            "mujoco_contact_confirmed": metadata["selected_tarsus5_involved"],
                            "ground_truth_state": ("KNOWN_CONTACT" if metadata["selected_tarsus5_involved"]
                                                   else "NO_CONTACT"),
                            "contact_metadata": metadata})
            if step < steps:
                result = sim.step({"joints": held, "adhesion": np.zeros(6)})
                obs = result[0]
        return {"samples": samples, "selected_geom_ids": list(selected_ids),
                "selected_geom_names": [_geom_name(physics.model, i) for i in selected_ids],
                "pose_intervention": intervention}
    finally:
        close = getattr(sim, "close", None)
        if close: close()


def build_report(*, live: bool = False, leg: str = DEFAULT_LEG,
                 duration_s: float = 0.05, timestep_s: float = DEFAULT_TIMESTEP_S) -> dict:
    if leg not in LEGS: raise ValueError(f"leg must be one of {LEGS}")
    if duration_s <= 0 or timestep_s <= 0: raise ValueError("durations must be positive")
    base = {"schema_version": "M5D-2B.0", "selected_leg": leg,
            "selected_segment": DISTAL_SEGMENT, "duration_s": float(duration_s),
            "timestep_s": float(timestep_s), "units": "model force units",
            "method": "one deterministic -0.1 model-unit root-body z adjustment after reset; measured joints then held passively",
            "neural_propagation": "NOT_RUN", "male_cns_used": False,
            "other_five_legs": "force magnitudes remain unvalidated"}
    if not live:
        base.update({"run_status": "NOT_RUN", "reason": "invoke with --live in the validated FlyGym/MuJoCo environment",
                     "no_contact": {"statistics": magnitude_statistics(())},
                     "confirmed_contact": {"statistics": magnitude_statistics(())},
                     "threshold_evaluation": evaluate_threshold((), (), verified_contact_occurred=False),
                     "lm_physical_contact_observability_validated": False})
        return base
    try:
        flygym = importlib.import_module("flygym")
    except ImportError as exc:
        base.update({"run_status": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}",
                     "no_contact": {"statistics": magnitude_statistics(())},
                     "confirmed_contact": {"statistics": magnitude_statistics(())},
                     "threshold_evaluation": evaluate_threshold((), (), verified_contact_occurred=False),
                     "lm_physical_contact_observability_validated": False})
        return base
    control = _run_condition(flygym, leg, duration_s, timestep_s, establish_contact=False)
    contact = _run_condition(flygym, leg, duration_s, timestep_s, establish_contact=True)
    no_contact_values = [s["magnitude"] for s in control["samples"]
                         if not s["mujoco_contact_confirmed"]]
    confirmed_values = [s["magnitude"] for s in contact["samples"]
                        if s["mujoco_contact_confirmed"]]
    evaluation = evaluate_threshold(no_contact_values, confirmed_values)
    base.update({"run_status": "COMPLETE", "no_contact": {**control,
                 "statistics": magnitude_statistics(no_contact_values)},
                 "confirmed_contact": {**contact,
                 "statistics": magnitude_statistics(confirmed_values)},
                 "threshold_evaluation": evaluation,
                 "lm_physical_contact_observability_validated": bool(leg == "LM" and confirmed_values)})
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
