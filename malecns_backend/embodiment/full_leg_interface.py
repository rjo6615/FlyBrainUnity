"""Read-only, joint-centric MaleCNS/FlyGym interface inventory (M5A).

The M4A map remains the annotation authority.  This module only reorganizes
its associations around physical actuators and, when FlyGym is available,
reads MuJoCo metadata from the same position-controlled ``Fly`` used by M4B.
It never resets or steps a simulation and contains no command path.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

from .six_leg_audit import ALLOWED_STATUS, OUTPUT as M4A_OUTPUT, generate_map, serialized_map

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "interface_output" / "full_leg_interface_audit.json"
CONFIDENCE = tuple(ALLOWED_STATUS)
LEG_ORDER = ("LF", "LM", "LH", "RF", "RM", "RH")
TIBIA_BASELINE = {
    "LF": (5, "EXACT", "SUPPORTED", ("chordotonal T1 left",), ("Acc. ti flexor MN T1 left", "Ti extensor MN T1 left", "Ti flexor MN T1 left")),
    "LM": (12, "EXACT", "EXACT", ("chordotonal T2 left",), ("Ti extensor MN T2 left", "Ti flexor MN T2 left")),
    "LH": (19, "EXACT", "SUPPORTED", ("chordotonal T3 left",), ("Acc. ti flexor MN T3 left", "Ti extensor MN T3 left", "Ti flexor MN T3 left")),
    "RF": (26, "EXACT", "SUPPORTED", ("chordotonal T1 right",), ("Acc. ti flexor MN T1 right", "Ti extensor MN T1 right", "Ti flexor MN T1 right")),
    "RM": (33, "EXACT", "SUPPORTED", ("chordotonal T2 right",), ("Acc. ti flexor MN T2 right", "Ti extensor MN T2 right", "Ti flexor MN T2 right")),
    "RH": (40, "EXACT", "SUPPORTED", ("chordotonal T3 right",), ("Acc. ti flexor MN T3 right", "Ti extensor MN T3 right", "Ti flexor MN T3 right")),
}
TIBIA_ASSOCIATION_DIGESTS = {
    "LF": "a9a71ca013ac4832f1ae72695e97afc1fe49eb8e1145b7e9d2d003a4f6f54789",
    "LM": "838abe4c022c6082c18e0c54e6f6a63c41434c28af01ffda5c66d0003e99a14d",
    "LH": "09a6a65a8e82e86b9ef5e3ffbf6aeab027a0362bb7eee27e0b794c1dc4bfdf0d",
    "RF": "afd5b05afb3c535185f58dd4546a67ed708e53b6d96eb97eaae7cc86985d6f37",
    "RM": "f62f26c58c74b3c3f90abb17347c963acc3dc665aea66d7585cb06d02009f09c",
    "RH": "fcc41d1c5daedb742ad752fb041fdbc33bda18037a6cf7d7edd053464a2c5c48",
}


def _ordered_population(population: dict[str, Any]) -> dict[str, Any]:
    """Return the M4A evidence with stable keys and sorted, unique body IDs."""
    metadata = population["evidence"]["bodymap_metadata"]
    direction = population.get("direction")
    role = "other"
    function = str(population.get("function") or "")
    if direction == 1 or "extensor" in function.lower():
        role = "extensor"
    elif direction == -1 or "flexor" in function.lower():
        role = "flexor"
    return {
        "population_name": population["name"],
        "body_ids": sorted(set(int(value) for value in population["body_ids"])),
        "distinct_neuron_count": len(set(population["body_ids"])),
        "category": population["category"],
        "role": role,
        "annotation": metadata,
        "source_provenance": population["source_artifact"],
        "provenance": population["provenance"],
    }


def _candidate(population: dict[str, Any], association: dict[str, Any], actuator: dict[str, Any]) -> dict[str, Any]:
    result = _ordered_population(population)
    result.update({
        "physical_actuator_association": actuator["name"],
        "relationship_to_physical_joint": association["reason"],
        "mapping_confidence": association["status"],
    })
    return result


def _fallback_metadata(actuator: dict[str, Any]) -> dict[str, Any]:
    """Represent unavailable live metadata explicitly; never invent addresses."""
    return {
        "joint_name": actuator["name"],
        "joint_type": "unavailable_without_flygym",
        "qpos_range": None,
        "dof_range": None,
        "actuator_control_range": list(actuator["position_range_rad"]),
        "metadata_source": "M4A committed physical inventory; live MuJoCo introspection unavailable",
    }


def enumerate_live_actuators() -> list[dict[str, Any]]:
    """Construct the M4B FlyGym stack and inspect its compiled MuJoCo model.

    ``Fly.model`` is an MJCF source element, not an ``MjModel``.  Compilation
    happens in ``SingleFlySimulation``; this follows the same construction path
    as :class:`FlyGymBody` but deliberately does not reset or step it.
    """
    flygym = importlib.import_module("flygym")
    fly = flygym.Fly(enable_adhesion=False, control="position")
    names = tuple(getattr(fly, "actuated_joints"))
    simulation = getattr(flygym, "SingleFlySimulation", None)
    if simulation is None:
        simulation = importlib.import_module("flygym.simulation").SingleFlySimulation
    sim = simulation(fly=fly, cameras=[], timestep=.0001)
    physics = None
    for owner in (sim, getattr(sim, "env", None), getattr(sim, "_env", None)):
        if owner is not None and getattr(owner, "physics", None) is not None:
            physics = owner.physics
            break
    if physics is None or getattr(physics, "model", None) is None:
        raise RuntimeError("installed FlyGym simulation exposes no compiled MuJoCo physics model")
    model = physics.model
    mujoco = importlib.import_module("mujoco")
    joint_transmission = int(mujoco.mjtTrn.mjTRN_JOINT)

    def model_name(kind: str, object_id: int) -> str:
        """Use dm_control's compiled-model name table, never the MJCF tree."""
        method = getattr(model, "id2name", None)
        if method is None:
            raise RuntimeError("compiled MuJoCo model exposes no id2name API")
        for args in ((object_id, kind), (kind, object_id)):
            try:
                value = method(*args)
            except (TypeError, ValueError, KeyError):
                continue
            if value is not None:
                return str(value)
        raise RuntimeError(f"compiled MuJoCo {kind} id {object_id} has no name")

    # FlyGym builds one ordered MJCF actuator for every entry in
    # ``actuated_joints`` and applies the action with physics.bind(_actuators).
    # Once the fly is attached, dm_control qualifies both joint and actuator
    # names, so the unqualified public name need not be in the compiled table.
    source_actuators = getattr(fly, "_actuators", None)
    if isinstance(source_actuators, dict):
        source_actuators = tuple(source_actuators.values())
    elif source_actuators is not None:
        source_actuators = tuple(source_actuators)

    def source_identifiers(element: Any) -> tuple[str, ...]:
        values = []
        for attribute in ("full_identifier", "name"):
            value = getattr(element, attribute, None)
            if value is not None and str(value) not in values:
                values.append(str(value))
        return tuple(values)

    compiled = []
    for actuator_id in range(int(model.nu)):
        transmission_type = int(model.actuator_trntype[actuator_id])
        transmission_ids = [int(value) for value in model.actuator_trnid[actuator_id]]
        joint_id = transmission_ids[0] if transmission_type == joint_transmission else None
        if joint_id is not None and not 0 <= joint_id < int(model.njnt):
            raise RuntimeError(f"actuator {actuator_id} has invalid joint transmission id {joint_id}")
        compiled.append({
            "actuator_id": actuator_id,
            "actuator_name": model_name("actuator", actuator_id),
            "transmission_type": transmission_type,
            "transmission_ids": transmission_ids,
            "joint_id": joint_id,
            "joint_name": model_name("joint", joint_id) if joint_id is not None else None,
        })

    def qualification(compiled_name: str, source_name: str) -> str | None:
        """Return dm_control's attachment prefix for an exact identifier.

        Attachment can replace an MJCF root's identifier (for example ``fly``)
        with a numeric one.  The element's local ``name`` remains authoritative;
        accepting it only as a complete slash-delimited component keeps Coxa,
        Coxa_roll, and Coxa_yaw distinct.
        """
        if compiled_name == source_name:
            return ""
        suffix = f"/{source_name}"
        if compiled_name.endswith(suffix):
            return compiled_name[:-len(source_name)]
        return None

    def diagnostic(index: int, logical_name: str) -> str:
        token = logical_name.removeprefix("joint_").casefold()
        plausible = [item for item in compiled if token in item["actuator_name"].casefold()
                     or (item["joint_name"] is not None and token in item["joint_name"].casefold())]
        return json.dumps({"logical_action_index": index, "logical_name": logical_name,
                           "plausible_compiled_associations": plausible}, sort_keys=True)

    records = []
    for index, name in enumerate(names):
        association = None
        source = (source_actuators[index] if source_actuators is not None
                  and len(source_actuators) == len(names) else None)
        if source is not None:
            identifiers = source_identifiers(source)
            matches = []
            for item in compiled:
                actuator_prefixes = {
                    prefix for value in identifiers
                    if (prefix := qualification(item["actuator_name"], value)) is not None
                }
                joint_prefix = (qualification(item["joint_name"], str(name))
                                if item["joint_name"] is not None else None)
                # The ordered FlyGym actuator must transmit the exact logical
                # joint in the same compiled attachment namespace.
                if joint_prefix is not None and joint_prefix in actuator_prefixes:
                    matches.append(item)
            if len({item["actuator_id"] for item in matches}) == 1:
                association = matches[0]
        # Compatibility for versions without exposed ordered actuator elements.
        if association is None:
            matches = [item for item in compiled if item["joint_name"] is not None
                       and qualification(item["joint_name"], str(name)) is not None]
            if len(matches) == 1:
                association = matches[0]
        if association is None or association["transmission_type"] != joint_transmission:
            raise RuntimeError(
                f"no compiled joint actuator transmission for FlyGym joint {name}; "
                f"compiled inventory diagnostic: {diagnostic(index, str(name))}")
        aid, jid = association["actuator_id"], association["joint_id"]
        q0, d0 = int(model.jnt_qposadr[jid]), int(model.jnt_dofadr[jid])
        q1 = int(model.jnt_qposadr[jid + 1]) if jid + 1 < model.njnt else int(model.nq)
        d1 = int(model.jnt_dofadr[jid + 1]) if jid + 1 < model.njnt else int(model.nv)
        records.append({"index": index, "name": str(name), "mujoco_metadata": {
            "source_actuator_name": (str(getattr(source, "name"))
                                     if source is not None and getattr(source, "name", None) is not None
                                     else None),
            "source_actuator_full_identifier": (str(getattr(source, "full_identifier"))
                                                if source is not None and getattr(source, "full_identifier", None) is not None
                                                else None),
            "actuator_id": aid, "actuator_name": association["actuator_name"],
            "actuator_transmission_type": association["transmission_type"],
            "actuator_transmission_ids": association["transmission_ids"],
            "joint_id": jid, "joint_name": model_name("joint", jid),
            "joint_type": int(model.jnt_type[jid]),
            "qpos_range": [q0, q1], "dof_range": [d0, d1],
            "actuator_control_range": list(map(float, model.actuator_ctrlrange[aid])),
            "metadata_source": "live FlyGym simulation physics.model compiled MuJoCo model",
        }})
    return records


def _print_order_comparison(physical: list[dict[str, Any]],
                            live_actuators: list[dict[str, Any]]) -> None:
    """Print the complete, deterministic M4A/live ordering regression evidence."""
    live_by_index = {item["index"]: item for item in live_actuators}
    rows = []
    for source in physical:
        m4a_index = source["action_index"]
        live = live_by_index.get(m4a_index)
        metadata = live.get("mujoco_metadata", {}) if live is not None else {}
        matches = live is not None and live.get("name") == source["name"]
        rows.append((
            m4a_index,
            source["name"],
            live.get("index") if live is not None else None,
            live.get("name") if live is not None else None,
            metadata.get("source_actuator_name"),
            metadata.get("source_actuator_full_identifier"),
            metadata.get("actuator_id"),
            metadata.get("actuator_name"),
            metadata.get("joint_id"),
            metadata.get("joint_name"),
            "MATCH" if matches else "MISMATCH",
        ))

    def shown(value: Any) -> str:
        return "<unavailable>" if value is None else str(value)

    print("LIVE FLYGYM / AUTHORITATIVE M4A ACTION ORDER COMPARISON")
    print("M4A IDX | M4A NAME | LIVE IDX | LIVE LOGICAL NAME | "
          "SOURCE NAME | SOURCE FULL_IDENTIFIER | COMPILED ACTUATOR ID/NAME | "
          "TRANSMITTED JOINT ID/NAME | STATUS")
    for row in rows:
        print(f"{row[0]} | {row[1]} | {shown(row[2])} | {shown(row[3])} | "
              f"{shown(row[4])} | {shown(row[5])} | {shown(row[6])}/{shown(row[7])} | "
              f"{shown(row[8])}/{shown(row[9])} | {row[10]}")
    mismatch_indices = [row[0] for row in rows if row[10] == "MISMATCH"]
    print(f"TOTAL: {len(rows)}")
    print(f"MATCHES: {len(rows) - len(mismatch_indices)}")
    print(f"MISMATCHES: {len(mismatch_indices)}")
    print("MISMATCH INDICES:")
    print(json.dumps(mismatch_indices))


def _tier(sensor: str, motor: str) -> tuple[int, bool, list[str]]:
    blockers = []
    if sensor in ("MISSING", "UNMAPPED") or motor in ("MISSING", "UNMAPPED"):
        tier = 4
    elif sensor == "AMBIGUOUS" or motor == "AMBIGUOUS":
        tier = 3
    elif sensor == motor == "EXACT":
        tier = 1
    else:
        tier = 2
    if sensor not in ("EXACT", "SUPPORTED"):
        blockers.append(f"sensory mapping is {sensor}")
    if motor not in ("EXACT", "SUPPORTED"):
        blockers.append(f"motor mapping is {motor}")
    return tier, not blockers, blockers


def build_audit(live_actuators: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build 42 deterministic records without initializing or stepping physics."""
    m4a = generate_map()
    physical = m4a["actuator_inventory"]
    live_by_index = {item["index"]: item for item in (live_actuators or [])}
    if live_actuators is not None:
        if len(live_actuators) != 42:
            raise ValueError(f"expected 42 live FlyGym leg actuators, found {len(live_actuators)}")
        order_disagrees = any(
            (live := live_by_index.get(source["action_index"])) is None
            or live["name"] != source["name"]
            for source in physical
        )
        _print_order_comparison(physical, live_actuators)
        if order_disagrees:
            raise ValueError("live FlyGym actuator order disagrees with authoritative M4A inventory")

    joints = {j["actuator"]["action_index"]: j for leg in m4a["legs"] for j in leg["joints"]}
    records = []
    for actuator in sorted(physical, key=lambda item: item["action_index"]):
        association = joints[actuator["action_index"]]
        sensor, motor = association["sensory"], association["motor"]
        tier, eligible, blockers = _tier(sensor["status"], motor["status"])
        records.append({
            "actuator_index": actuator["action_index"], "actuator_name": actuator["name"],
            "leg": actuator["leg"], "side": actuator["side"],
            "segment_or_joint": actuator["anatomical_joint"],
            "axis": actuator["name"].removeprefix(f"joint_{actuator['leg']}"),
            "mujoco_metadata": live_by_index.get(actuator["action_index"], {}).get(
                "mujoco_metadata", _fallback_metadata(actuator)),
            "sensory_candidates": sorted((_candidate(p, sensor, actuator) for p in sensor["populations"]), key=lambda p: (p["population_name"], p["body_ids"])),
            "motor_candidates": sorted((_candidate(p, motor, actuator) for p in motor["populations"]), key=lambda p: (p["population_name"], p["body_ids"])),
            "sensory_confidence": sensor["status"], "motor_confidence": motor["status"],
            "overall_interface_confidence": (sensor["status"] if sensor["status"] == motor["status"] else f"SENSORY_{sensor['status']}/MOTOR_{motor['status']}"),
            "activation_tier": tier, "activation_eligible": eligible,
            "activation_blockers": blockers,
            "provenance": {"mapping": "M4A six_leg_audit.generate_map", "physical": actuator["source"]},
        })

    # M4B loads its six interfaces from the committed M4A document.  Requiring
    # byte equality detects changes in names, IDs, confidence, or ordering.
    if M4A_OUTPUT.read_text(encoding="utf-8") != serialized_map(m4a):
        raise ValueError("authoritative M4A map is stale; six-tibia regression cannot pass")
    regression = []
    for leg in LEG_ORDER:
        current = next(r for r in records if r["leg"] == leg and r["segment_or_joint"] == "tibia")
        source = next(j for l in m4a["legs"] if l["leg"] == leg for j in l["joints"] if j["actuator"]["anatomical_joint"] == "tibia")
        sensory_names = tuple(p["population_name"] for p in current["sensory_candidates"])
        motor_names = tuple(p["population_name"] for p in current["motor_candidates"])
        biological_projection = {
            key: {"status": source[key]["status"],
                  "populations": [{"name": p["name"], "body_ids": p["body_ids"]}
                                  for p in source[key]["populations"]]}
            for key in ("sensory", "motor")
        }
        association_digest = hashlib.sha256(json.dumps(
            biological_projection, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        passed = (current["actuator_name"] == source["actuator"]["name"]
                  and current["actuator_index"] == source["actuator"]["action_index"]
                  and sensory_names == tuple(sorted(p["name"] for p in source["sensory"]["populations"]))
                  and motor_names == tuple(sorted(p["name"] for p in source["motor"]["populations"]))
                  and current["sensory_confidence"] == source["sensory"]["status"]
                  and current["motor_confidence"] == source["motor"]["status"]
                  and (current["actuator_index"], current["sensory_confidence"],
                       current["motor_confidence"], sensory_names, motor_names)
                  == TIBIA_BASELINE[leg]
                  and association_digest == TIBIA_ASSOCIATION_DIGESTS[leg])
        regression.append({"leg": leg, "actuator": current["actuator_name"],
                           "action_index": current["actuator_index"],
                           "sensory_populations": list(sensory_names),
                           "motor_populations": list(motor_names),
                           "biological_association_sha256": association_digest,
                           "sensory_confidence": current["sensory_confidence"],
                           "motor_confidence": current["motor_confidence"], "passed": passed})
    if not all(item["passed"] for item in regression):
        raise ValueError("M5A disagrees with an established six-tibia interface")

    unresolved = sorted((_ordered_population(p) for p in m4a["population_inventory"]["unmapped_motor"]), key=lambda p: (p["population_name"], p["body_ids"]))
    counts = Counter(record["activation_tier"] for record in records)
    return {
        "schema": "flybrain.full_leg_interface_audit", "version": "5A.2",
        "purpose": "Read-only interface evidence inventory; not a controller.",
        "actuator_records": records,
        "unassociated_unmapped_motor_evidence": unresolved,
        "six_tibia_regression": {"passed": True, "interfaces": regression},
        "summary": {"total_actuators": len(records), **{f"tier_{i}": counts[i] for i in range(1, 5)},
                    "activation_eligible": sum(r["activation_eligible"] for r in records),
                    "sensory_mapped": sum(r["sensory_confidence"] in ("EXACT", "SUPPORTED") for r in records),
                    "motor_mapped": sum(r["motor_confidence"] in ("EXACT", "SUPPORTED") for r in records),
                    "both_mapped": sum(r["sensory_confidence"] in ("EXACT", "SUPPORTED") and r["motor_confidence"] in ("EXACT", "SUPPORTED") for r in records)},
        "confidence_categories": list(CONFIDENCE),
        "non_intervention": {"simulation_initialized": False, "physics_steps": 0, "actuators_commanded": False, "neural_constants_changed": False},
    }


def serialized_audit(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
