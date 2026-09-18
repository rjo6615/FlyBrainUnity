"""Read-only M5B-1 dissection of ambiguous coxa proprioceptive mappings.

Anatomical classification is deliberately completed before (and independently
of) the optional graph summary.  Connectivity can describe a population, but
can never change its classification.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from .full_leg_interface import build_audit

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "interface_output" / "m5b_proprioceptive_dissection.json"
TARGET_LEGS = ("LF", "LM", "LH", "RM", "RH")
TARGET_AXES = ("Coxa", "Coxa_roll", "Coxa_yaw")
RESOLUTIONS = ("RESOLVABLE_EXACT", "RESOLVABLE_SUPPORTED",
               "BROAD_PROPRIOCEPTIVE", "CONFLICTING", "INSUFFICIENT")
INTERFACE_MAP = HERE.parent / "interface_map.json"


def _annotation(candidate: dict[str, Any]) -> dict[str, Any]:
    """Expose source vocabulary without translating it into a model axis."""
    metadata = candidate["annotation"]
    return {
        "population_name": candidate["population_name"],
        "bodymap_metadata": metadata,
        "source_types": candidate.get("source_types", []),
        "exact_source_terms": sorted({str(value) for value in metadata.values()
                                      if value is not None}),
        "axis_distinguishing_term_present": any(
            term in " ".join(str(v).casefold() for v in metadata.values())
            for term in ("roll", "yaw", "twist", "abduct", "adduct",
                         "protract", "retract", "flex", "extend", "rotation")),
        "interpretation": (
            "The source identifies a joint-angle hair-plate population for the "
            "coxa/segment/side, but contains no term distinguishing FlyGym's "
            "Coxa, Coxa_roll, and Coxa_yaw axes."
        ),
    }


def summarize_connectivity(data: Any, populations: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize outgoing CSR edges; suitable for small synthetic fixtures too."""
    result: dict[str, Any] = {}
    for population in populations:
        targets: set[int] = set()
        outgoing = 0
        represented = 0
        target_types: Counter[str] = Counter()
        for body_id in population["body_ids"]:
            index = data.body_id_to_index.get(int(body_id))
            if index is None:
                continue
            represented += 1
            for slot in range(int(data.row_ptr[index]), int(data.row_ptr[index + 1])):
                target = int(data.target_indices[slot])
                targets.add(target)
                outgoing += int(data.synapse_counts[slot])
                label = str(data.types[target] or "<unannotated>")
                target_types[label] += int(data.synapse_counts[slot])
        result[population["population_name"]] = {
            "total_population_members": population["member_count"],
            "represented_neurons": represented,
            "direct_downstream_neuron_count": len(targets),
            "represented_outgoing_synapse_count": outgoing,
            "direct_downstream_body_ids": sorted(int(data.body_ids[i]) for i in targets),
            "major_direct_downstream_annotated_types": [
                {"type": name, "synapse_count": count}
                for name, count in sorted(target_types.items(), key=lambda x: (-x[1], x[0]))[:10]
            ],
        }
    return result


def _connectivity_overlap(records: list[dict[str, Any]], summaries: dict[str, Any]) -> list[dict[str, Any]]:
    by_leg = {}
    for record in records:
        names = [p["population_name"] for p in record["candidate_populations"]]
        targets = set()
        for name in names:
            targets.update(summaries.get(name, {}).get("direct_downstream_body_ids", []))
        by_leg.setdefault(record["leg"], {})[record["axis"]] = targets
    output = []
    for leg, axes in sorted(by_leg.items()):
        for left_i, left in enumerate(TARGET_AXES):
            for right in TARGET_AXES[left_i + 1:]:
                output.append({"leg": leg, "axes": [left, right],
                               "shared_direct_downstream_body_ids": sorted(axes[left] & axes[right]),
                               "shared_count": len(axes[left] & axes[right])})
    return output


def build_dissection(m5a: dict[str, Any] | None = None, graph: Any | None = None) -> dict[str, Any]:
    """Build an audit without mutating the supplied M5A document or graph."""
    m5a = build_audit() if m5a is None else m5a
    raw_populations = json.loads(INTERFACE_MAP.read_text(encoding="utf-8"))["populations"]
    raw_by_name = {p["name"]: p for p in raw_populations}
    selected = [r for r in m5a["actuator_records"]
                if r["leg"] in TARGET_LEGS and r["axis"] in TARGET_AXES]
    selected.sort(key=lambda r: r["actuator_index"])
    if len(selected) != 15 or any(r["sensory_confidence"] != "AMBIGUOUS" for r in selected):
        raise ValueError("M5B-1 requires exactly 15 M5A AMBIGUOUS non-RF coxa interfaces")

    records = []
    population_index: dict[tuple[str, tuple[int, ...]], dict[str, Any]] = {}
    for source in selected:
        candidates = []
        for item in source["sensory_candidates"]:
            raw = raw_by_name[item["population_name"]]
            candidate = {
                "population_name": item["population_name"],
                "annotation_name": item["annotation"].get("name"),
                "member_count": item["distinct_neuron_count"],
                "body_ids": list(item["body_ids"]),
                "distinct_mapped_body_ids": len(item["body_ids"]),
                "annotation": item["annotation"],
                "source_types": list(raw.get("types", [])),
                "source_classes": list(raw.get("classes", [])),
                "source_superclasses": list(raw.get("superclasses", [])),
                "source_neurotransmitters": list(raw.get("neurotransmitters", [])),
                "source_instances": list(raw.get("instances", [])),
                "source_consumers": list(raw.get("source_consumers", [])),
                "provenance": item["provenance"],
                "source_provenance": item["source_provenance"],
                "relevance_fields": {"joint": item["annotation"].get("joint"),
                                     "kind": item["annotation"].get("kind"),
                                     "name": item["annotation"].get("name")},
            }
            candidates.append(candidate)
            population_index[(candidate["population_name"], tuple(candidate["body_ids"]))] = candidate
        records.append({
            "physical_actuator": source["actuator_name"], "action_index": source["actuator_index"],
            "leg": source["leg"], "axis": source["axis"], "current_sensory_confidence": "AMBIGUOUS",
            "candidate_populations": candidates,
            "m4a_reason": (candidates and source["sensory_candidates"][0]["relationship_to_physical_joint"]),
            "ambiguity_reasons": ["B_ONE_POPULATION_SPANNING_MULTIPLE_PHYSICAL_DOFS",
                                  "C_ANNOTATION_IDENTIFIES_BROADER_JOINT_OR_SEGMENT"],
        })

    overlaps = []
    for leg in TARGET_LEGS:
        leg_records = [r for r in records if r["leg"] == leg]
        axis_ids = {r["axis"]: sorted({bid for p in r["candidate_populations"] for bid in p["body_ids"]})
                    for r in leg_records}
        common = sorted(set.intersection(*(set(axis_ids[a]) for a in TARGET_AXES)))
        overlaps.append({"leg": leg, "axis_body_ids": axis_ids,
                         "shared_by_all_three_axes": common,
                         "unique_by_axis": {a: sorted(set(axis_ids[a]) - set().union(
                             *(set(axis_ids[b]) for b in TARGET_AXES if b != a))) for a in TARGET_AXES},
                         "same_broad_population_assigned_to_all_three":
                             len({tuple(axis_ids[a]) for a in TARGET_AXES}) == 1})

    populations = sorted(population_index.values(), key=lambda p: p["population_name"])
    connectivity = summarize_connectivity(graph, populations) if graph is not None else {
        p["population_name"]: {"status": "NOT_COMPUTED", "reason": "MaleCNS graph was not supplied"}
        for p in populations}
    classifications = [{"physical_actuator": r["physical_actuator"],
                         "action_index": r["action_index"], "result": "BROAD_PROPRIOCEPTIVE",
                         "basis": "Coxa joint-angle hair-plate evidence is relevant but has no axis-discriminating annotation; connectivity is not identity evidence."}
                        for r in records]
    counts = Counter(r["result"] for r in classifications)
    return {
        "schema_version": "M5B-1.0",
        "source/provenance": {"mapping": "M4A/M5A read-only projection",
                              "annotations": "malecns_backend/interface_map.json",
                              "connectivity": "MaleCNS outgoing CSR when supplied",
                              "scientific_constraint": "connectivity never determines anatomical classification"},
        "target_interfaces": records,
        "candidate_populations": populations,
        "annotation_evidence": [_annotation(p) for p in populations],
        "body_id_overlap": overlaps,
        "connectivity_summary": {"populations": connectivity,
                                 "sibling_candidate_target_overlap": _connectivity_overlap(records, connectivity)},
        "resolution_classification": classifications,
        "aggregate_summary": {"ambiguous_interfaces_examined": 15,
                              "resolvable_exact": counts["RESOLVABLE_EXACT"],
                              "resolvable_supported": counts["RESOLVABLE_SUPPORTED"],
                              "broad_proprioceptive": counts["BROAD_PROPRIOCEPTIVE"],
                              "conflicting": counts["CONFLICTING"],
                              "insufficient": counts["INSUFFICIENT"],
                              "newly_potentially_resolvable": counts["RESOLVABLE_EXACT"] + counts["RESOLVABLE_SUPPORTED"]},
        "non_intervention": {"m4a_or_m5a_modified": False, "simulation_initialized": False,
                             "connectivity_modified": False, "activation_eligibility_modified": False},
        "six_tibia_regression": m5a["six_tibia_regression"],
    }


def serialized_dissection(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
