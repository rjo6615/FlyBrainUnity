"""Global, annotation-first M5C inventory of MaleCNS leg mechanosensors.

This module is deliberately descriptive.  It reads the complete population
table, then compares the result with M5A; it does not import a simulator or
provide a sensory encoding path.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import Any

from .full_leg_interface import build_audit

HERE = Path(__file__).resolve().parent
INTERFACE_MAP = HERE.parent / "interface_map.json"
DEFAULT_OUTPUT = HERE / "interface_output" / "m5c_leg_sensory_inventory.json"
OLD_FEMALE_SOURCE = HERE.parents[1] / "fly-brain-main" / "src" / "sim" / "senses.js"
LEG_CODE = {("T1", "left"): "LF", ("T2", "left"): "LM", ("T3", "left"): "LH",
            ("T1", "right"): "RF", ("T2", "right"): "RM", ("T3", "right"): "RH"}


def _location(metadata: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    text = " ".join(str(metadata.get(k, "")) for k in ("name", "joint", "site", "sensor"))
    match = re.search(r"\b(T[123])_(left|right)\b|\b(T[123]) (left|right)\b", text)
    if not match:
        return None, None, None
    segment, side = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), match.group(4))
    return LEG_CODE[(segment, side)], side, segment


def discover_candidates(populations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select from *all* populations using source fields, never name alone."""
    result = []
    for source_index, population in enumerate(populations):
        metadata = population.get("bodymap_metadata") or {}
        leg, side, segment = _location(metadata)
        kind = metadata.get("kind")
        classes = {value for value in (population.get("classes") or []) if isinstance(value, str)}
        supported_mechanism = (
            isinstance(kind, str) and kind in {"joint_angle", "load", "contact"}
            and bool(classes & {"mechanosensory_proprioceptive", "mechanosensory_tactile"})
        )
        # A leg locus and mechanosensory source metadata are both required.
        if population.get("category") != "sensors" or leg is None or not supported_mechanism:
            continue
        result.append({"source_index": source_index, "source": population, "metadata": metadata,
                       "leg": leg, "side": side, "segment": segment})
    return result


def classify_source(metadata: dict[str, Any], classes: list[str], connectivity: Any = None) -> str:
    """Classify annotation evidence; ``connectivity`` is intentionally ignored."""
    kind = metadata.get("kind")
    if kind in {"load", "contact"}:
        return "LOAD_OR_CONTACT"
    if kind == "joint_angle" and metadata.get("joint"):
        return "JOINT_SPECIFIC"
    if any(metadata.get(k) for k in ("segment", "site")):
        return "SEGMENT_SPECIFIC"
    if any(c.startswith("mechanosensory") for c in classes):
        return "OTHER_MECHANOSENSORY"
    return "UNCERTAIN"


def _interfaces(m5a: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}
    for record in m5a["actuator_records"]:
        for candidate in record["sensory_candidates"]:
            found.setdefault(candidate["population_name"], []).append({
                "physical_interface": record["actuator_name"], "action_index": record["actuator_index"],
                "axis": record["axis"], "confidence": record["sensory_confidence"],
            })
    return found


def _female_cross_check(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = {record["population_name"] for record in records}
    checks = []
    for mechanism, prefix, physical_input in (
        ("tibia angle", "chordotonal", "st.joint[tibia_<T#_side>]"),
        ("coxa angle", "hair plate", "st.joint[coxa_<T#_side>]"),
        ("tarsal load", "campaniform", "st.load[T#_side]"),
        ("leg/tarsal contact", "tactile", "st.touch[T#_side] and obstacle contact"),
    ):
        matches = sorted(name for name in names if name.startswith(prefix + " "))
        used = [r for r in records if r["population_name"] in matches and r["currently_used"]]
        status = "PRESENT_AND_USED" if used else ("PRESENT_BUT_UNUSED" if matches else "NOT_FOUND")
        checks.append({"female_interface": mechanism, "historical_physical_input": physical_input,
                       "male_populations": matches, "status": status,
                       "note": "Historical modeled correspondence only; it is not promoted by M5C."})
    return checks


def build_inventory(interface: dict[str, Any] | None = None,
                    m5a: dict[str, Any] | None = None,
                    connectivity: Any = None) -> dict[str, Any]:
    interface = json.loads(INTERFACE_MAP.read_text(encoding="utf-8")) if interface is None else interface
    m5a = build_audit() if m5a is None else m5a
    current = _interfaces(m5a)
    records = []
    for item in discover_candidates(interface["populations"]):
        source, metadata = item["source"], item["metadata"]
        body_ids = sorted(set(int(x) for x in source.get("body_ids", [])))
        classification = classify_source(metadata, source.get("classes", []), connectivity)
        interfaces = sorted(current.get(source["name"], []), key=lambda x: x["action_index"])
        used, duplicated = bool(interfaces), len(interfaces) > 1
        if classification == "LOAD_OR_CONTACT":
            level = "NOT_JOINT_STATE"
        elif not used and classification in {"JOINT_SPECIFIC", "SEGMENT_SPECIFIC"}:
            level = "HIGH_PRIORITY"
        elif not used:
            level = "INVESTIGATE"
        else:
            level = "BROAD_ONLY"
        joint = metadata.get("joint")
        structure = joint or metadata.get("site") or metadata.get("sensor") or item["segment"]
        records.append({
            "population_name": source["name"], "body_ids": body_ids,
            "distinct_body_id_count": len(body_ids), "leg": item["leg"], "side": item["side"],
            "segment": item["segment"], "joint": joint, "biological_structure": structure,
            "sensory_kind": metadata.get("kind"), "modality": (
                "proprioception" if metadata.get("kind") in {"joint_angle", "load"} else "mechanosensory contact"),
            "classes": list(source.get("classes", [])), "subclasses": list(source.get("subclasses", [])),
            "types": list(source.get("types", [])), "source_provenance": {
                "artifact": "malecns_backend/interface_map.json", "population_source_index": item["source_index"],
                "mapping_provenance": source.get("mapping_provenance"), "metadata": metadata},
            "direction_axis_fields": {k: metadata.get(k) for k in ("dir", "direction", "axis")},
            "tuning_fields": {k: metadata.get(k) for k in ("tuning", "preferred_angle", "range")},
            "existing_bodymap_consumers": list(source.get("source_consumers", [])),
            "source_classification": classification,
            "classification_basis": "bodymap kind/joint/site/sensor fields plus source mechanosensory class; connectivity excluded",
            "currently_used": used, "physical_interfaces": interfaces,
            "duplicated_across_dofs": duplicated, "unused": not used,
            "unrepresentable_with_current_flygym_interface": classification == "LOAD_OR_CONTACT",
            "needs_modeled_transduction": True, "coverage_reason": (
                "M5A associates this source population with multiple position DOFs." if duplicated else
                "M5A associates this source population with one position DOF." if used else
                "No M5A 42-position-DOF sensory association exists."),
            "candidate_level": level,
        })
    records.sort(key=lambda x: (x["leg"], x["sensory_kind"], x["population_name"]))

    def count(field: str, values: list[str]) -> dict[str, int]:
        values_count = Counter(r[field] for r in records)
        return {value.lower(): values_count[value] for value in values}

    classes = ["JOINT_SPECIFIC", "SEGMENT_SPECIFIC", "BROAD_LEG", "LOAD_OR_CONTACT",
               "OTHER_MECHANOSENSORY", "UNCERTAIN"]
    levels = ["HIGH_PRIORITY", "INVESTIGATE", "BROAD_ONLY", "NOT_JOINT_STATE"]
    aggregate = {
        "total_leg_sensory_populations_discovered": len(records),
        "total_distinct_neurons": len({body for record in records for body in record["body_ids"]}),
        **count("source_classification", classes),
        "currently_used": sum(r["currently_used"] for r in records),
        "duplicated_across_dofs": sum(r["duplicated_across_dofs"] for r in records),
        "unused": sum(r["unused"] for r in records),
        "unrepresentable": sum(r["unrepresentable_with_current_flygym_interface"] for r in records),
        "needs_modeled_transduction": sum(r["needs_modeled_transduction"] for r in records),
        **count("candidate_level", levels),
    }
    return {
        "schema_version": "M5C-1.0", "purpose": "global read-only leg sensory discovery",
        "search": {"population_table_size": len(interface["populations"]),
                   "selected_population_source_indices": [r["source_provenance"]["population_source_index"] for r in records],
                   "selection_rule": "leg locus AND source kind AND source mechanosensory class; names alone are insufficient"},
        "populations": records, "aggregate_summary": aggregate,
        "counts": {"sensory_mechanism": dict(sorted(Counter(r["sensory_kind"] for r in records).items())),
                   "leg": dict(sorted(Counter(r["leg"] for r in records).items())),
                   "side": dict(sorted(Counter(r["side"] for r in records).items())),
                   "biological_structure": dict(sorted(Counter(str(r["biological_structure"]) for r in records).items())),
                   "coverage": {k: aggregate[k] for k in ("currently_used", "duplicated_across_dofs", "unused", "unrepresentable", "needs_modeled_transduction")}},
        "interesting_unused": [r for r in records if r["unused"]],
        "female_interface_cross_check": _female_cross_check(records),
        "connectivity": {"used_for_anatomical_classification": False,
                         "status": "NOT_COMPUTED" if connectivity is None else "DESCRIPTIVE_ONLY"},
        "non_intervention": {"mapping_promoted": False, "encoder_implemented": False,
                             "runtime_or_physics_modified": False, "locked_artifacts_modified": False},
    }


def serialized_inventory(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
