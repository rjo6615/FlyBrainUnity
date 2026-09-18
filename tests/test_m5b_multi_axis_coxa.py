"""Contracts for the read-only M5B-2 broad-coxa audit."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from malecns_backend.embodiment.full_leg_interface import build_audit
from malecns_backend.embodiment.m5b_proprioceptive_dissection import build_dissection
from malecns_backend.embodiment.m5b_multi_axis_coxa import (
    AXES, build_multi_axis_audit, serialized_audit,
)


LOCKED_SHA256 = {
    "malecns_backend/embodiment/six_leg_map.json": "575186602ac1e5a6e3b2c6d680309880266f5d80e18fff44f989440f6cd0a4bc",
    "malecns_backend/embodiment/interface_output/full_leg_interface_audit.json": "758850ea659e49fd93a36a9606bea07a1d329739fbf6be8089060ee6d706c52e",
    "malecns_backend/embodiment/interface_output/m5b_proprioceptive_dissection.json": "9fd5cbac34273e4c37f06646a86b1a370ce2769515b58f7414a78c7ea95e0c91",
    "malecns_backend/embodiment/M5B_PROPRIOCEPTIVE_DISSECTION.md": "6895a3fc5ed5ea6d6f44044326dad1ae83fe46924f2f4eaf4c65bc579a89f54b",
    "malecns_backend/embodiment/m5b_proprioceptive_dissection.py": "84916304f7aebaf4e2cc057bcf66d95fe268e2adfe7cf3841942e59a6a77bf9a",
}


def test_exactly_five_populations_and_three_ambiguous_dofs_each():
    result = build_multi_axis_audit()
    assert len(result["source_evidence"]) == 5
    assert len({p["population_name"] for p in result["source_evidence"]}) == 5
    assert len(result["physical_dof_relationship"]) == 5
    for leg in result["physical_dof_relationship"]:
        assert tuple(d["flygym_axis"] for d in leg["physical_dofs"]) == AXES


def test_body_ids_exactly_agree_with_m5b1():
    m5b1 = build_dissection()
    expected = {p["population_name"]: p["body_ids"] for p in m5b1["candidate_populations"]}
    actual = {p["population_name"]: p["body_ids"] for p in build_multi_axis_audit()["source_evidence"]}
    assert actual == expected


def test_action_indices_exactly_agree_with_validated_m5a():
    m5a = build_audit()
    expected = {r["actuator_name"]: r["actuator_index"] for r in m5a["actuator_records"]}
    for leg in build_multi_axis_audit(m5a=m5a)["physical_dof_relationship"]:
        for dof in leg["physical_dofs"]:
            assert dof["live_action_index"] == expected[dof["logical_joint"]]


def test_no_biological_axis_specificity_is_invented():
    result = build_multi_axis_audit()
    for evidence in result["source_evidence"]:
        assert evidence["direction_or_axis_fields"] == {"dir": None, "axis": None}
        assert evidence["tuning_information"] is None
    assert {x["classification"] for x in result["implementability_classification"]} == {
        "BROAD_JOINT_SUPPORTED"
    }
    assert not result["conclusion"]["scientifically_explicit_modeled_multi_axis_encoder_defensible_now"]


def test_engineering_models_and_serialization_are_deterministic():
    first = build_multi_axis_audit()
    second = build_multi_axis_audit()
    assert first["engineering_model_evaluations"] == second["engineering_model_evaluations"]
    assert [x["model"] for x in first["engineering_model_evaluations"]] == [
        "A_DUPLICATED_SCALAR", "B_COMBINED_JOINT_STATE",
        "C_VECTOR_OR_SUBPOPULATION", "D_UNSPECIFIED_DO_NOT_MODEL",
    ]
    text = serialized_audit(first)
    assert text == serialized_audit(second)
    assert json.loads(text) == first
    artifact = Path("malecns_backend/embodiment/interface_output/m5b_multi_axis_coxa_audit.json")
    assert artifact.read_text(encoding="utf-8") == text


def test_inputs_and_locked_artifacts_are_unchanged():
    m5a, m5b1 = build_audit(), build_dissection()
    m5a_before, m5b1_before = deepcopy(m5a), deepcopy(m5b1)
    before = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in LOCKED_SHA256}
    build_multi_axis_audit(m5a=m5a, m5b1=m5b1)
    after = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in LOCKED_SHA256}
    assert m5a == m5a_before and m5b1 == m5b1_before
    assert before == after == LOCKED_SHA256
    assert build_multi_axis_audit()["non_intervention"] == {
        "encoder_implemented": False, "simulation_initialized": False,
        "m4a_m5a_m5b1_modified": False, "activation_eligibility_modified": False,
        "neural_or_physics_runtime_modified": False,
    }
