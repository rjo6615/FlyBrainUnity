"""Deterministic, read-only motor-population/physical-interface audit.

This module reads committed annotation and mapping artifacts.  It does not
import a neural runtime or FlyGym and cannot initialize or step a simulation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "interface_output/motor_population_activity_survey/motor_population_inventory.json"
SOURCES = (
    ROOT / "fly-brain-main/public/data/bodymap.json",
    ROOT / "fly-brain-main/body/flybody/fruitfly.xml",
    ROOT / "malecns_backend/interface_map.json",
    HERE / "six_leg_map.json",
    HERE / "interface_output/whole_leg_motor_mapping_audit.json",
    HERE / "m9b_external_perturbation.py",
    HERE / "candidate_motor_channel_validation.py",
)
ADMITTED = (
    ("joint_LFTibia", 5, 1), ("joint_LMTibia", 12, 1), ("joint_LHTibia", 19, 1),
    ("joint_RFTibia", 26, 1), ("joint_RMTibia", 33, 1), ("joint_RHTibia", 40, 1),
    ("joint_LFFemur", 3, -1), ("joint_LMFemur", 10, -1), ("joint_LHFemur", 17, -1),
    ("joint_RMFemur", 31, -1), ("joint_RHFemur", 38, -1),
)
ATTEMPT4 = (("joint_RFFemur", 24, -1), ("joint_LFTarsus1", 6, -1),
            ("joint_RFTarsus1", 27, -1))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate() -> dict:
    interface = json.loads((ROOT / "malecns_backend/interface_map.json").read_text())
    m4 = json.loads((HERE / "six_leg_map.json").read_text())
    m6 = json.loads((HERE / "interface_output/whole_leg_motor_mapping_audit.json").read_text())
    source_by_name = {p["name"]: p for p in interface["populations"]}
    admitted_by_name = {n: (i, s) for n, i, s in ADMITTED}
    attempt_by_name = {n: (i, s) for n, i, s in ATTEMPT4}
    actuator_rows = {x["actuator"]: x for x in m6["per_actuator"]}
    pop_to_joints: dict[str, list[str]] = {}
    for row in m6["per_actuator"]:
        for candidate in row["candidates"]:
            pop_to_joints.setdefault(candidate["population"], []).append(row["actuator"])

    populations = []
    for base in sorted(m4["population_inventory"]["leg_motor"], key=lambda x: x["name"]):
        raw = source_by_name[base["name"]]
        joints = sorted(set(pop_to_joints.get(base["name"], [])),
                        key=lambda n: actuator_rows[n]["global_action_index"])
        ambiguous = len(joints) > 1 or any(not actuator_rows[j]["unique_physical_mapping"] for j in joints)
        surveyability = ("AMBIGUOUS_MAPPING_BUT_NEURALLY_SURVEYABLE" if ambiguous
                          else "DIRECTLY_SURVEYABLE")
        signs = {admitted_by_name[j][1] for j in joints if j in admitted_by_name}
        signs.update(attempt_by_name[j][1] for j in joints if j in attempt_by_name)
        populations.append({
            "canonical_name": base["name"], "neuron_ids": sorted(set(base["body_ids"])),
            "neuron_count": len(set(base["body_ids"])),
            "dense_neural_indices": sorted(set(raw.get("dense_indices", []))),
            "leg": next((x for x, side, seg, _ in (("LF","left","T1",0),("LM","left","T2",0),("LH","left","T3",0),("RF","right","T1",0),("RM","right","T2",0),("RH","right","T3",0)) if base["side"] == side and base["segment"] == seg), None),
            "anatomical_association": base["evidence"]["bodymap_metadata"].get("actuator"),
            "anatomical_role": base.get("function"), "explicit_direction": base.get("direction"),
            "candidate_flygym_joints": joints,
            "candidate_action_indices": [actuator_rows[j]["global_action_index"] for j in joints],
            "coordinate_sign": next(iter(signs)) if len(signs) == 1 else None,
            "mapping_evidence": "MaleCNS body-map actuator annotation projected by M6A",
            "ambiguity_status": "AMBIGUOUS" if ambiguous else ("UNIQUE" if joints else "UNMAPPED"),
            "unique_mapping": bool(joints) and not ambiguous,
            "admitted_11": any(j in admitted_by_name for j in joints),
            "attempt4_silent_candidate": any(j in attempt_by_name for j in joints),
            "possible_coxa_yaw": any(j.endswith("Coxa_yaw") for j in joints),
            "surveyability": surveyability,
            "surveyability_reason": "dense indices are present in the existing interface map; physical mapping is not required for observation",
        })

    physical = []
    for actuator in sorted(m4["actuator_inventory"], key=lambda x: x["action_index"]):
        row = actuator_rows[actuator["name"]]
        candidates = [x["population"] for x in row["candidates"]]
        known_sign = (admitted_by_name.get(actuator["name"]) or attempt_by_name.get(actuator["name"]))
        physical.append({
            "action_index": actuator["action_index"], "joint_name": actuator["name"],
            "leg": actuator["leg"], "joint_type_axis": actuator["anatomical_joint"],
            "currently_admitted": actuator["name"] in admitted_by_name,
            "has_annotation_backed_candidate": bool(candidates), "candidate_populations": candidates,
            "mapping": "UNIQUE" if row["unique_physical_mapping"] else ("AMBIGUOUS" if candidates else "MISSING"),
            "mechanically_validated_coordinate_sign": known_sign[1] if known_sign else None,
            "unresolved_blocker": None if actuator["name"] in admitted_by_name else
                ("Attempt-4 supported but silent; not admitted" if actuator["name"] in attempt_by_name else
                 ("shared-axis anatomical ambiguity" if candidates and not row["unique_physical_mapping"] else
                  "coordinate sign and/or experimental activity/admission evidence absent")),
        })

    admitted = []
    for name, index, sign in ADMITTED:
        admitted.append({"joint": name, "action_index": index, "coordinate_sign": sign,
                         "mapped_populations": [x["population"] for x in actuator_rows[name]["candidates"]],
                         "mapping_source": "M6A annotation audit plus frozen Tier-A/M6B validation",
                         "activity_used_by_decoder": True})
    attempts = [{"joint": n, "action_index": i, "coordinate_sign": s,
                 "mechanical_status": "MECHANICALLY_SUPPORTED",
                 "experimental_status": "EXPERIMENTALLY_SUPPORTED_BUT_SILENT",
                 "admission_status": "NOT_ADMITTED", "freeze_commit": "05926f4"}
                for n, i, s in ATTEMPT4]
    coxa = []
    for row in physical:
        if row["joint_name"].endswith("Coxa_yaw"):
            ps = [p for p in populations if row["joint_name"] in p["candidate_flygym_joints"]]
            coxa.append({"leg": row["leg"], "annotation_names": [p["canonical_name"] for p in ps],
                         "populations": [{"name": p["canonical_name"], "neuron_ids": p["neuron_ids"], "count": p["neuron_count"], "interpretation": p["anatomical_role"]} for p in ps],
                         "candidate_joints": [row["joint_name"]], "action_indices": [row["action_index"]],
                         "anatomical_mapping_unique": True, "coordinate_sign": None,
                         "admission_blocker": "anatomical anterior/posterior labels do not establish FlyGym coordinate sign; mechanical sign validation is required"})
    survey = Counter(p["surveyability"] for p in populations)
    return {
        "schema": "flybrain.motor_population_inventory", "version": "1.0.0",
        "artifact_kind": "READ_ONLY_AUDIT_NOT_EXPERIMENTAL_EVIDENCE",
        "generation_commit": "WORKTREE (deterministic from source hashes)",
        "source_files": [{"path": str(p.relative_to(ROOT)), "sha256": _hash(p)} for p in SOURCES],
        "summary": {"motor_population_count": len(populations),
                    "neuron_membership_count": sum(p["neuron_count"] for p in populations),
                    "unique_neuron_id_count": len({n for p in populations for n in p["neuron_ids"]}),
                    "physical_hinge_count": len(physical),
                    "hinges_with_candidates": sum(x["has_annotation_backed_candidate"] for x in physical),
                    "unique_physical_mappings": sum(x["mapping"] == "UNIQUE" for x in physical),
                    "ambiguous_physical_mappings": sum(x["mapping"] == "AMBIGUOUS" for x in physical),
                    "admitted_channel_count": len(admitted), "surveyability_counts": dict(sorted(survey.items()))},
        "population_inventory": populations, "physical_joint_inventory": physical,
        "admitted_11_inventory": admitted, "attempt4_candidates": attempts,
        "coxa_yaw_audit": coxa,
        "ambiguity_records": [x for x in physical if x["mapping"] == "AMBIGUOUS"],
        "interpretation_boundary": ["Annotation/mapping structure only", "No neural activity survey was run", "Does not establish natural motor function, locomotion, walking, gait, balance, stabilization, righting, reflex behavior, or biological necessity"],
        "non_intervention": {"simulation_run": False, "runtime_modified": False, "active_interface_count": 11, "live_fly_modified": False},
    }


def serialized(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = serialized(generate())
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(text)
    if args.check and (not OUTPUT.exists() or OUTPUT.read_text() != text):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
