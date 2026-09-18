"""Deterministic M5B-1 read-only audit contracts."""
from array import array
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from malecns_backend.embodiment.full_leg_interface import build_audit, serialized_audit
from malecns_backend.embodiment.m5b_proprioceptive_dissection import (
    build_dissection, serialized_dissection,
)


def _tiny_graph(body_ids):
    ids = sorted(set(body_ids))
    # Each represented candidate has one deterministic edge to the next body.
    targets = [(i + 1) % len(ids) for i in range(len(ids))]
    return SimpleNamespace(body_ids=array("q", ids), body_id_to_index={v: i for i, v in enumerate(ids)},
                           row_ptr=array("I", range(len(ids) + 1)), target_indices=array("I", targets),
                           synapse_counts=array("H", [3] * len(ids)), types=["fixture_type"] * len(ids))


def test_targets_candidates_and_rf_exclusion():
    result = build_dissection()
    targets = result["target_interfaces"]
    assert len(targets) == 15
    assert not any(r["leg"] == "RF" for r in targets)
    assert all(r["current_sensory_confidence"] == "AMBIGUOUS" for r in targets)
    assert all(len(r["candidate_populations"]) == 1 for r in targets)
    for leg in ("LF", "LM", "LH", "RM", "RH"):
        candidates = [r["candidate_populations"] for r in targets if r["leg"] == leg]
        assert candidates[0] == candidates[1] == candidates[2]


def test_overlap_and_deterministic_classification():
    result = build_dissection()
    assert all(x["same_broad_population_assigned_to_all_three"] for x in result["body_id_overlap"])
    assert all(not any(x["unique_by_axis"].values()) for x in result["body_id_overlap"])
    assert {x["result"] for x in result["resolution_classification"]} == {"BROAD_PROPRIOCEPTIVE"}
    assert result["aggregate_summary"] == {
        "ambiguous_interfaces_examined": 15, "resolvable_exact": 0,
        "resolvable_supported": 0, "broad_proprioceptive": 15,
        "conflicting": 0, "insufficient": 0, "newly_potentially_resolvable": 0,
    }


def test_synthetic_connectivity_and_candidate_preservation():
    static = build_dissection()
    ids = [bid for p in static["candidate_populations"] for bid in p["body_ids"]]
    result = build_dissection(graph=_tiny_graph(ids))
    for pop in result["candidate_populations"]:
        summary = result["connectivity_summary"]["populations"][pop["population_name"]]
        assert summary["represented_neurons"] == pop["member_count"]
        assert summary["direct_downstream_neuron_count"] == pop["member_count"]
        assert summary["represented_outgoing_synapse_count"] == 3 * pop["member_count"]


def test_no_m4a_m5a_mutation_and_tibia_regression():
    locked = [Path("malecns_backend/embodiment/six_leg_map.json"),
              Path("malecns_backend/embodiment/interface_output/full_leg_interface_audit.json")]
    file_hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in locked}
    m5a = build_audit()
    before = hashlib.sha256(serialized_audit(m5a).encode()).hexdigest()
    result = build_dissection(m5a=m5a)
    assert hashlib.sha256(serialized_audit(m5a).encode()).hexdigest() == before
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in locked} == file_hashes
    assert m5a == deepcopy(m5a)
    assert result["six_tibia_regression"]["passed"]
    assert {x["leg"]: x["action_index"] for x in result["six_tibia_regression"]["interfaces"]} == {
        "LF": 5, "LM": 12, "LH": 19, "RF": 26, "RM": 33, "RH": 40}


def test_serialization_is_deterministic():
    first = serialized_dissection(build_dissection())
    assert first == serialized_dissection(build_dissection())
    assert json.loads(first)["schema_version"] == "M5B-1.0"
