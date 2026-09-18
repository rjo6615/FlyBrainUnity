import hashlib
import json
from pathlib import Path

from malecns_backend.embodiment.m5c_leg_sensory_inventory import (
    build_inventory, classify_source, discover_candidates, serialized_inventory,
)

ROOT = Path(__file__).parents[1]
LOCKED = {
    "malecns_backend/embodiment/six_leg_map.json": "575186602ac1e5a6e3b2c6d680309880266f5d80e18fff44f989440f6cd0a4bc",
    "malecns_backend/embodiment/interface_output/full_leg_interface_audit.json": "758850ea659e49fd93a36a9606bea07a1d329739fbf6be8089060ee6d706c52e",
    "malecns_backend/embodiment/interface_output/m5b_proprioceptive_dissection.json": "9fd5cbac34273e4c37f06646a86b1a370ce2769515b58f7414a78c7ea95e0c91",
    "malecns_backend/embodiment/interface_output/m5b_multi_axis_coxa_audit.json": "1f68bfcc06dc5aa9c904fcd27ed8b9e08a1b8a8345611739896606ca247ec973",
}


def population(name, kind, *, joint=None, site=None, sensor=None, ids=(1,)):
    metadata = {"name": name, "kind": kind}
    metadata.update({k: v for k, v in {"joint": joint, "site": site, "sensor": sensor}.items() if v})
    cls = "mechanosensory_tactile" if kind == "contact" else "mechanosensory_proprioceptive"
    return {"name": name, "category": "sensors", "count": len(ids), "body_ids": list(ids),
            "bodymap_metadata": metadata, "classes": [cls], "types": ["synthetic"]}


def m5a(*candidate_names):
    candidates = [{"population_name": name} for name in candidate_names]
    return {"actuator_records": [{"actuator_name": "joint_LFTibia", "actuator_index": 5,
                                   "axis": "Tibia", "sensory_confidence": "EXACT",
                                   "sensory_candidates": candidates}]}


def test_global_search_is_not_restricted_to_m5a_populations_and_separates_usage():
    used = population("known T1 left", "joint_angle", joint="tibia_T1_left")
    unused = population("new T2 right", "joint_angle", joint="femur_T2_right", ids=(2,))
    result = build_inventory({"populations": [used, unused]}, m5a("known T1 left"))
    assert result["search"]["population_table_size"] == 2
    assert [(r["population_name"], r["currently_used"]) for r in result["populations"]] == [
        ("known T1 left", True), ("new T2 right", False)]
    assert result["populations"][1]["candidate_level"] == "HIGH_PRIORITY"


def test_classification_uses_metadata_not_suggestive_name():
    fake = {"name": "femoral chordotonal T1 left", "category": "sensors", "count": 1,
            "body_ids": [1], "bodymap_metadata": {"name": "femoral chordotonal T1 left", "kind": "odor"},
            "classes": ["olfactory"]}
    assert discover_candidates([fake]) == []
    assert classify_source({"kind": "joint_angle", "joint": "tibia_T1_left"}, []) == "JOINT_SPECIFIC"


def test_load_and_connectivity_cannot_promote_anatomical_specificity():
    graph_claim = {"downstream": "tibia motor neuron", "invented_joint": "femur-tibia"}
    assert classify_source({"kind": "load", "sensor": "force_tarsus_T1_left"},
                           ["mechanosensory_proprioceptive"], graph_claim) == "LOAD_OR_CONTACT"
    assert classify_source({"kind": "contact", "site": "claw_T1_left"},
                           ["mechanosensory_tactile"], graph_claim) == "LOAD_OR_CONTACT"


def test_duplicate_population_is_detected():
    pop = population("joint sensor T1 left", "joint_angle", joint="coxa_T1_left")
    fixture = m5a("joint sensor T1 left")
    fixture["actuator_records"].append({**fixture["actuator_records"][0],
                                        "actuator_name": "joint_LFCoxa_roll", "actuator_index": 1})
    result = build_inventory({"populations": [pop]}, fixture)
    assert result["populations"][0]["duplicated_across_dofs"] is True
    assert result["aggregate_summary"]["duplicated_across_dofs"] == 1


def test_real_inventory_counts_and_deterministic_serialization():
    first = build_inventory()
    second = build_inventory()
    assert first["aggregate_summary"] == {
        "total_leg_sensory_populations_discovered": 23, "total_distinct_neurons": 2341,
        "joint_specific": 11, "segment_specific": 0, "broad_leg": 0,
        "load_or_contact": 12, "other_mechanosensory": 0, "uncertain": 0,
        "currently_used": 11, "duplicated_across_dofs": 5, "unused": 12,
        "unrepresentable": 12, "needs_modeled_transduction": 23,
        "high_priority": 0, "investigate": 0, "broad_only": 11, "not_joint_state": 12,
    }
    assert serialized_inventory(first) == serialized_inventory(second)
    assert json.loads(serialized_inventory(first)) == first


def test_locked_artifact_hashes_are_unchanged():
    for relative, expected in LOCKED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
