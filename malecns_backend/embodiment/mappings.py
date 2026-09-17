"""Explicit anatomical correspondence selected from the immutable 3A audit.

Nothing in this module discovers a population by fuzzy neuron-name matching.
Names below are primary keys into ``interface_map.json`` and all IDs are checked
against that audited record when the mapping is loaded.
"""
from dataclasses import dataclass
import json
from pathlib import Path


INTERFACE_MAP = Path(__file__).parents[1] / "interface_map.json"


@dataclass(frozen=True)
class AuditedPopulation:
    name: str
    category: str
    dense_indices: tuple[int, ...]
    body_ids: tuple[int, ...]
    side: str
    body_target: str
    direction: int | None
    provenance: str = "ANNOTATION_DERIVED"


@dataclass(frozen=True)
class LegPathway:
    leg: str
    side: str
    joint: str
    flygym_leg: str
    flygym_joint_name: str
    flygym_joint_index: int
    sensor: AuditedPopulation
    extensor: AuditedPopulation
    flexor: AuditedPopulation
    selection_reason: str


SELECTED_PATHWAY = {
    "leg": "T2", "side": "left", "joint": "tibia",
    "flygym_leg": "LM", "flygym_joint_name": "joint_LMTibia",
    # FlyGym action order is LF, LM, LH, RF, RM, RH; tibia is DOF 5 of 7.
    "flygym_joint_index": 12,
    "sensor_name": "chordotonal T2 left",
    "extensor_name": "Ti extensor MN T2 left",
    "flexor_name": "Ti flexor MN T2 left",
    "selection_reason": (
        "The audited map explicitly ties the large 80-neuron T2-left "
        "chordotonal population to tibia_T2_left and supplies separately "
        "annotated, oppositely directed tibia extensor and flexor motor pools "
        "for the same leg, side, and actuator."
    ),
}


def _population(record):
    metadata = record["bodymap_metadata"]
    side = "left" if record["name"].endswith(" left") else "right"
    return AuditedPopulation(
        name=record["name"], category=record["category"],
        dense_indices=tuple(record["dense_indices"]),
        body_ids=tuple(record["body_ids"]), side=side,
        body_target=metadata.get("joint", metadata.get("actuator", "")),
        direction=metadata.get("dir"),
        provenance=record["mapping_provenance"],
    )


def load_selected_pathway(path=INTERFACE_MAP):
    """Resolve exact selected records and reject ambiguous/changed audits."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    by_key = {}
    for record in raw["populations"]:
        by_key.setdefault((record["category"], record["name"]), []).append(record)

    def exactly_one(category, name):
        matches = by_key.get((category, name), [])
        if len(matches) != 1:
            raise ValueError(f"expected one audited {category} population {name!r}, found {len(matches)}")
        return _population(matches[0])

    p = SELECTED_PATHWAY
    sensor = exactly_one("sensors", p["sensor_name"])
    extensor = exactly_one("muscles", p["extensor_name"])
    flexor = exactly_one("muscles", p["flexor_name"])
    expected_target = "tibia_T2_left"
    if sensor.body_target != expected_target or extensor.body_target != expected_target or flexor.body_target != expected_target:
        raise ValueError("selected populations no longer share the audited tibia_T2_left target")
    if (sensor.side, extensor.side, flexor.side) != ("left", "left", "left"):
        raise ValueError("selected population side changed")
    if (extensor.direction, flexor.direction) != (1, -1):
        raise ValueError("selected antagonist directions changed")
    return LegPathway(
        p["leg"], p["side"], p["joint"], p["flygym_leg"],
        p["flygym_joint_name"], p["flygym_joint_index"], sensor,
        extensor, flexor, p["selection_reason"],
    )
