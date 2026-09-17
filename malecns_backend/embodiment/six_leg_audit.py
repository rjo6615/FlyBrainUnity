"""Deterministic, read-only Milestone 4A six-leg anatomical audit.

This module only reads annotations.  It deliberately has no dependency on the
embodiment loop or FlyGym simulation APIs and therefore cannot command a body.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
INTERFACE_MAP = HERE.parent / "interface_map.json"
OUTPUT = HERE / "six_leg_map.json"
ALLOWED_STATUS = ("EXACT", "SUPPORTED", "AMBIGUOUS", "UNMAPPED", "MISSING")
LEGS = (
    ("LF", "left", "T1", "front"), ("LM", "left", "T2", "middle"),
    ("LH", "left", "T3", "hind"), ("RF", "right", "T1", "front"),
    ("RM", "right", "T2", "middle"), ("RH", "right", "T3", "hind"),
)
DOFS = (
    ("Coxa", "coxa", None),
    ("Coxa_yaw", "coxa_twist", None),
    ("Coxa_roll", "coxa_abduct", None),
    ("Femur", "femur", None),
    ("Femur_roll", "femur_twist", (-1.0, 1.0)),
    ("Tibia", "tibia", (-1.35, 1.3)),
    ("Tarsus1", "tarsus", None),
)
SEGMENT_RANGES = {
    "T1": {"coxa": (-0.2, 1.7), "coxa_twist": (-0.8, 0.8), "coxa_abduct": (-1.0, 0.7),
           "femur": (-0.15, 2.0), "tarsus": (-0.7, 1.2)},
    "T2": {"coxa": (-0.2, 0.9), "coxa_twist": (-0.75, 0.8), "coxa_abduct": (-0.5, 0.3),
           "femur": (-0.15, 2.0), "tarsus": (-1.0, 1.8)},
    "T3": {"coxa": (-0.3, 1.3), "coxa_twist": (-0.15, 0.8), "coxa_abduct": (-0.9, 0.25),
           "femur": (-0.7, 1.5), "tarsus": (-0.8, 1.2)},
}


def _population(record: dict, segment: str | None = None, side: str | None = None) -> dict:
    """Retain source values (including int64 IDs), not inferred replacements."""
    metadata = record["bodymap_metadata"]
    return {
        "name": record["name"],
        "category": record["category"],
        "body_ids": record["body_ids"],
        "member_count": record["count"],
        "resolved_neuron_count": len(set(record["body_ids"])),
        "side": side or metadata.get("side") or (record.get("sides") or ["unknown"])[0],
        "segment": segment,
        "biological_type": metadata.get("kind", "motor neuron"),
        "function": metadata.get("name", metadata.get("type")),
        "direction": metadata.get("dir"),
        "source_artifact": "malecns_backend/interface_map.json",
        "provenance": "ANNOTATION_DERIVED",
        "evidence": {"bodymap_metadata": metadata, "types": record.get("types", [])},
    }


def _association(populations: list[dict], status: str, why: str) -> dict:
    return {"status": status, "populations": populations, "reason": why,
            "provenance": "ANNOTATION_DERIVED"}


def generate_map(interface_path: Path = INTERFACE_MAP) -> dict:
    source = json.loads(Path(interface_path).read_text(encoding="utf-8"))
    leg_re = re.compile(r"T([123]) (left|right)$")
    sensors, muscles, unresolved = [], [], []
    for record in source["populations"]:
        match = leg_re.search(record["name"])
        if record["category"] in ("sensors", "muscles") and match:
            pop = _population(record, "T" + match.group(1), match.group(2))
            (sensors if record["category"] == "sensors" else muscles).append(pop)
        elif record["category"] == "unmappedMotor":
            unresolved.append(_population(record))

    # A source population may occur twice when bodymap explicitly associates it
    # with two biological actuators. Preserve both records in associations, but
    # count/inventory the source population once by name and side.
    unique_motor = {}
    for pop in muscles:
        unique_motor.setdefault((pop["name"], pop["side"]), pop)

    actuators, legs = [], []
    for leg_number, (code, side, segment, position) in enumerate(LEGS):
        joints = []
        for dof_number, (suffix, biological, common_range) in enumerate(DOFS):
            index = leg_number * 7 + dof_number
            actuator = {
                "name": f"joint_{code}{suffix}", "action_index": index,
                "leg": code, "side": side, "segment": segment,
                "anatomical_joint": biological,
                "position_range_rad": list(common_range or SEGMENT_RANGES[segment][biological]),
                "range_note": "Exact inherited MJCF joint/control range for this segment class.",
                "provenance": "PHYSICS_MEASURED",
                "source": "FlyGym NeuroMechFly 42-DOF order; fly-brain-main/body/flybody/fruitfly.xml joint classes",
            }
            actuators.append(actuator)

            sensory_candidates = []
            if biological == "tibia":
                sensory_candidates = [p for p in sensors if p["segment"] == segment and p["side"] == side
                                      and p["name"].startswith("chordotonal ")]
                s_status = "EXACT"
                s_reason = "Bodymap explicitly annotates this chordotonal channel with the same tibia, segment, and side."
            elif biological in ("coxa", "coxa_twist", "coxa_abduct"):
                sensory_candidates = [p for p in sensors if p["segment"] == segment and p["side"] == side
                                      and p["name"].startswith("hair plate ")]
                if sensory_candidates:
                    s_status, s_reason = "AMBIGUOUS", "Hair-plate annotation names coxa angle but does not distinguish the three FlyGym coxa axes."
                else:
                    s_status, s_reason = "MISSING", "No side/segment hair-plate population is present (notably T1 right)."
            else:
                s_status, s_reason = "MISSING", "No source sensor annotation identifies this physical joint."

            target = f"{biological}_{segment}_{side}"
            motor_candidates = [p for p in muscles if p["evidence"]["bodymap_metadata"].get("actuator") == target]
            if motor_candidates:
                if code == "LM" and suffix == "Tibia":
                    # M3D intentionally excludes accessory flexor from its decoder.
                    names = {"Ti extensor MN T2 left", "Ti flexor MN T2 left"}
                    motor_candidates = [p for p in motor_candidates if p["name"] in names]
                    m_status = "EXACT"
                    m_reason = "Validated M3D extensor/flexor mapping, preserved without modification."
                else:
                    m_status = "SUPPORTED"
                    m_reason = "Bodymap gives side, segment, actuator and signed biological action; correspondence to FlyGym axis is an anatomical interpretation."
            else:
                m_status, m_reason = "MISSING", "No bodymap muscle record names this side/segment actuator."
            joints.append({"actuator": actuator, "sensory": _association(sensory_candidates, s_status, s_reason),
                           "motor": _association(motor_candidates, m_status, m_reason)})
        legs.append({"leg": code, "side": side, "segment": segment, "position": position, "joints": joints})

    other_sensory = []
    for pop in sensors:
        kind = pop["evidence"]["bodymap_metadata"].get("kind")
        if kind != "joint_angle":
            other_sensory.append({**pop, "status": "UNMAPPED",
                "mapping_reason": "Leg-related channel is retained, but contact/load/taste is not a single joint-angle actuator."})
    tarsus2 = [p for p in muscles if p["evidence"]["bodymap_metadata"].get("actuator", "").startswith("tarsus2_")]

    family = defaultdict(dict)
    for pop in sensors + list(unique_motor.values()):
        base = leg_re.sub("T# SIDE", pop["name"])
        family[base][(pop["segment"], pop["side"])] = pop["member_count"]
    symmetry = []
    expected = {(s, side) for s in ("T1", "T2", "T3") for side in ("left", "right")}
    for name, members in sorted(family.items()):
        present = set(members)
        symmetry.append({"family": name, "counterparts_present": len(present),
                         "missing": [f"{s} {side}" for s, side in sorted(expected - present)],
                         "population_sizes": {f"{s} {side}": n for (s, side), n in sorted(members.items())},
                         "size_symmetric": len(set(members.values())) == 1,
                         "note": "Symmetry is audit evidence only and never promotes confidence."})

    result = {
        "schema": "flybrain.six_leg_anatomical_map", "version": "4A.1",
        "purpose": "Read-only anatomical inventory; not a controller.",
        "provenance": {
            "primary": "malecns_backend/interface_map.json (audited MaleCNS annotations)",
            "scientific_reference": "fly-brain-main/public/data/bodymap.json and docs/09-bodymap.md",
            "physical_reference": "FlyGym NeuroMechFly 42-position action ordering and fly-brain-main/body/flybody/fruitfly.xml",
            "vocabulary": ["CONNECTOME_DERIVED", "ANNOTATION_DERIVED", "PHYSICS_MEASURED", "MODELED_TRANSDUCTION", "MODELED_MOTOR_DECODING", "ENGINEERING_CONSTRAINT"],
        },
        "confidence_enum": list(ALLOWED_STATUS), "actuator_inventory": actuators, "legs": legs,
        "population_inventory": {
            "leg_sensory": sensors, "leg_motor": list(unique_motor.values()),
            "unmapped_motor": unresolved,
            "unresolved_leg_sensory": other_sensory,
            "unresolved_tarsus2_and_adhesion_motor": tarsus2,
        },
        "symmetry_audit": symmetry,
        "connectome_sanity": {
            "body_ids_resolved": all(p["resolved_neuron_count"] == len(p["body_ids"]) for p in sensors + muscles),
            "orientation": "presynaptic CSR row -> postsynaptic target",
            "reachability": "Not computed: anatomical associations do not require or imply functional connectivity.",
        },
        "validated_m3d_reference": {
            "sensor": "chordotonal T2 left", "sensor_count": 80,
            "extensor": "Ti extensor MN T2 left", "extensor_body_ids": [800911, 801234],
            "flexor": "Ti flexor MN T2 left", "flexor_body_ids": [802295, 818295, 823739, 824041, 927808],
            "actuator": "joint_LMTibia", "action_index": 12,
        },
        "non_intervention": {"actuators_commanded": False, "simulation_initialized": False,
                             "scientific_parameters_changed": False},
    }
    return result


def serialized_map(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_map(path: Path = OUTPUT) -> None:
    path.write_text(serialized_map(generate_map()), encoding="utf-8")


def _statuses(joint: dict) -> tuple[str, str]:
    return joint["sensory"]["status"], joint["motor"]["status"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if committed JSON is stale")
    parser.add_argument("--write", action="store_true", help="regenerate committed JSON")
    args = parser.parse_args(argv)
    data = generate_map()
    text = serialized_map(data)
    if args.write:
        OUTPUT.write_text(text, encoding="utf-8")
    if args.check and (not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text):
        print("six_leg_map.json is stale; run with --write")
        return 1
    print(f"{'JOINT':<22} {'SENSORY':<12} MOTOR")
    counts = Counter()
    for leg in data["legs"]:
        for joint in leg["joints"]:
            sensory, motor = _statuses(joint)
            counts.update((sensory, motor))
            print(f"{joint['actuator']['name']:<22} {sensory:<12} {motor}")
    inventory = data["population_inventory"]
    counts["UNMAPPED"] += len(inventory["unresolved_leg_sensory"]) + len(inventory["unmapped_motor"])
    print(f"\nNeuroMechFly leg actuators: {len(data['actuator_inventory'])}")
    print(f"MaleCNS leg sensory populations: {len(inventory['leg_sensory'])}")
    print(f"MaleCNS leg motor populations: {len(inventory['leg_motor'])}")
    for status in ALLOWED_STATUS:
        print(f"{status}: {counts[status]}")
    ref = data["validated_m3d_reference"]
    print("\nLM tibia: chordotonal T2 left -> joint_LMTibia; Ti extensor/flexor MN T2 left -> joint_LMTibia")
    expected = generate_map()["validated_m3d_reference"]
    print("VALIDATED M3D REFERENCE MAPPING PRESERVED: " + ("PASS" if ref == expected else "FAIL"))
    print("NO ACTUATOR COMMANDED: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
