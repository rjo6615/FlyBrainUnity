"""Fail-closed, non-neural validation of the six FlyGym femur-roll coordinates.

The default audit reads existing identity evidence only.  ``--mechanical`` may
delegate to a dependency-gated forward-kinematics adapter; neither path runs a
MaleCNS transition, advances physics, authorizes an experiment, or admits a
motor channel.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INTERFACE_MAP = ROOT / "malecns_backend/interface_map.json"
BODYMAP = ROOT / "fly-brain-main/public/data/bodymap.json"
FULL_AUDIT = HERE / "interface_output/full_leg_interface_audit.json"
MAPPING_AUDIT = HERE / "interface_output/whole_leg_motor_mapping_audit.json"
INVENTORY = HERE / "interface_output/motor_population_activity_survey/motor_population_inventory.json"
REGISTRATION = HERE / "interface_output/flymimic_flygym_proximal_registration/flymimic_flygym_proximal_registration_result.json"
OUTPUT = HERE / "interface_output/femur_roll_validation.json"

CANDIDATES = {
    "joint_LFFemur_roll": (4, "Fe reductor MN T1 left", "left", "T1"),
    "joint_LMFemur_roll": (11, "Fe reductor MN T2 left", "left", "T2"),
    "joint_LHFemur_roll": (18, "Fe reductor MN T3 left", "left", "T3"),
    "joint_RFFemur_roll": (25, "Fe reductor MN T1 right", "right", "T1"),
    "joint_RMFemur_roll": (32, "Fe reductor MN T2 right", "right", "T2"),
    "joint_RHFemur_roll": (39, "Fe reductor MN T3 right", "right", "T3"),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serialize(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def dependencies_available() -> bool:
    return all(importlib.util.find_spec(name) is not None for name in ("flygym", "mujoco", "numpy"))


def _opposite_populations(muscles: list[dict[str, Any]], actuator: str, direction: int) -> list[str]:
    """Return only source populations explicitly assigned the opposite direction."""
    return sorted(item["name"] for item in muscles
                  if item.get("actuator") == actuator and item.get("dir") == -direction)


def build() -> dict[str, Any]:
    interface = json.loads(INTERFACE_MAP.read_text())
    bodymap = json.loads(BODYMAP.read_text())
    populations = {item["name"]: item for item in interface["populations"]}
    muscles = bodymap["muscles"]
    raw = {item["name"]: item for item in muscles}
    records: dict[str, Any] = {}
    for joint, (index, annotation, side, segment) in CANDIDATES.items():
        population = populations.get(annotation)
        source = raw.get(annotation)
        expected_actuator = f"femur_twist_{segment}_{side}"
        identity_ok = bool(
            population and source
            and population["bodymap_metadata"] == {key: source[key] for key in ("name", "actuator", "dir")}
            and source["actuator"] == expected_actuator and source["dir"] == 1
            and population["sides"] == [side]
            and population["dense_indices"] == source["idx"]
            and len(population["body_ids"]) == len(population["dense_indices"]) == population["count"]
            and len(set(population["body_ids"])) == population["count"]
            and len(set(population["dense_indices"])) == population["count"]
        )
        opposites = _opposite_populations(muscles, expected_actuator, 1)
        classification = "MECHANICAL_DIRECTION_UNRESOLVED" if identity_ok else "IDENTITY_FAILURE"
        records[joint] = {
            "action_index": index,
            "expected_compiled_actuator_name": f"actuator_position_{joint}",
            "expected_transmitted_joint_name": joint,
            "identity_valid": identity_ok,
            "annotation": {
                "exact_name": annotation,
                "actuator": expected_actuator,
                "source_direction": 1,
                "body_ids": population["body_ids"] if population else [],
                "dense_indices": population["dense_indices"] if population else [],
                "side": side,
                "thoracic_segment": segment,
            },
            "opposite_direction_population": {
                "present_in_source": bool(opposites),
                "exact_names": opposites,
                "synthesized": False,
                "status": None if opposites else "SOURCE_HAS_NO_ANTAGONIST_POPULATION",
            },
            "mechanics": None,
            "mechanical_coordinate_direction_resolved": False,
            "biological_coordinate_sign": None,
            "biological_direction_resolved": False,
            "classification": classification,
            "statuses": [classification] + ([] if opposites else ["SOURCE_HAS_NO_ANTAGONIST_POPULATION"]),
            "blocking_reason": "forward-kinematics evidence has not been collected"
                if identity_ok else "static annotation identity did not match exactly",
        }
    return {
        "schema": "SIX-FEMUR-ROLL-VALIDATION.1",
        "run_status": "STATIC_IDENTITY_ONLY",
        "scientific_operations": {"malecns_transitions": 0, "physics_steps": 0,
                                  "forward_kinematics_calls": 0, "neural_runtime_constructed": False},
        "scope": {"active_11_channel_interface_modified": False, "channels_admitted": 0,
                  "neural_experiment_run": False, "execution_authorization_created": False},
        "interpretation_boundary": "Mechanical coordinate direction does not establish the sign relating Fe reductor MN activity to that coordinate.",
        "candidate_channels": records,
        "source_hashes": {str(path.relative_to(ROOT)): _sha(path) for path in
                          (INTERFACE_MAP, BODYMAP, FULL_AUDIT, MAPPING_AUDIT, INVENTORY, REGISTRATION)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanical", action="store_true",
                        help="run dependency-gated MuJoCo forward kinematics only")
    args = parser.parse_args(argv)
    if args.mechanical and dependencies_available():
        adapter = __import__("malecns_backend.embodiment._femur_roll_mechanical_validation",
                             fromlist=["run"])
        return adapter.run()
    result = build()
    if args.mechanical:
        result["run_status"] = "SKIPPED_DEPENDENCIES_UNAVAILABLE"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(serialize(result), encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
