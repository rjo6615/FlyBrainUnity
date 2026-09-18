"""Deterministic, read-only M5B-2 broad-coxa interface audit.

This module describes evidence and possible engineering representations.  It
does not encode joint state, import FlyGym, or touch the neural runtime.
"""
from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any

from .full_leg_interface import build_audit
from .m5b_proprioceptive_dissection import build_dissection

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INTERFACE_MAP = HERE.parent / "interface_map.json"
MJCF = ROOT / "fly-brain-main" / "body" / "flybody" / "fruitfly.xml"
OLD_SENSES = ROOT / "fly-brain-main" / "src" / "sim" / "senses.js"
DEFAULT_OUTPUT = HERE / "interface_output" / "m5b_multi_axis_coxa_audit.json"
LEGS = ("LF", "LM", "LH", "RM", "RH")
AXES = ("Coxa", "Coxa_roll", "Coxa_yaw")
POPULATION_FOR_LEG = {
    "LF": "hair plate T1 left", "LM": "hair plate T2 left",
    "LH": "hair plate T3 left", "RM": "hair plate T2 right",
    "RH": "hair plate T3 right",
}
PHYSICS_NAME = {"Coxa": "coxa", "Coxa_roll": "coxa_abduct", "Coxa_yaw": "coxa_twist"}


def _source_evidence(raw: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    metadata = raw["bodymap_metadata"]
    return {
        "population_name": raw["name"], "body_ids": list(raw["body_ids"]),
        "member_count": raw["count"], "kind": metadata.get("kind"),
        "joint": metadata.get("joint"), "modality": "proprioception",
        "classes": list(raw.get("classes", [])), "subclass_or_types": list(raw.get("types", [])),
        "source": "malecns_backend/interface_map.json",
        "provenance": {"mapping": raw.get("mapping_provenance"),
                       "m5b_1": candidate.get("source_provenance")},
        "direction_or_axis_fields": {"dir": metadata.get("dir"), "axis": metadata.get("axis")},
        "tuning_information": None,
        "additional_relevant_fields": {
            "category": raw.get("category"), "superclasses": raw.get("superclasses", []),
            "neurotransmitters": raw.get("neurotransmitters", []),
            "instances": raw.get("instances", []), "sides": raw.get("sides", []),
            "source_consumers": raw.get("source_consumers", []),
            "bodymap_metadata_complete": metadata,
        },
        "explicit_source_evidence": (
            "The annotation identifies this population as mechanosensory/proprioceptive, "
            "kind joint_angle, at the named coxa segment and side."
        ),
        "not_specified": ["which FlyGym coxa axis", "directional tuning", "response range",
                          "velocity sensitivity", "strain/contact sensitivity",
                          "a transformation from three coordinates to neural activity"],
        "modeling_possibility_not_biological_fact": (
            "One broad population could be driven by a modeled function of several coxa "
            "coordinates, but neither that dependency nor its geometry is annotated."
        ),
    }


def _class_defaults(root: ET.Element) -> dict[str, dict[str, str]]:
    """Resolve the joint attributes explicitly present in nested MJCF defaults."""
    result: dict[str, dict[str, str]] = {}

    def visit(default: ET.Element, inherited: dict[str, str]) -> None:
        attrs = dict(inherited)
        joint = default.find("joint")
        if joint is not None:
            attrs.update(joint.attrib)
        cls = default.get("class")
        if cls:
            result[cls] = attrs
        for child in default.findall("default"):
            visit(child, attrs)

    for node in root.findall("default"):
        visit(node, {})
    return result


def _physical_dofs(m5a: dict[str, Any]) -> list[dict[str, Any]]:
    root = ET.parse(MJCF).getroot()
    defaults = _class_defaults(root)
    m5a_by_name = {x["actuator_name"]: x for x in m5a["actuator_records"]}
    result = []
    for leg in LEGS:
        side = "left" if leg[0] == "L" else "right"
        segment = {"F": "T1", "M": "T2", "H": "T3"}[leg[1]]
        body_name = f"coxa_{segment}_{side}"
        body = root.find(f".//body[@name='{body_name}']")
        if body is None:
            raise ValueError(f"missing local MJCF body {body_name}")
        joints = {x.get("name"): x for x in body.findall("joint")}
        dofs = []
        for axis in AXES:
            logical = f"joint_{leg}{axis}"
            record = m5a_by_name[logical]
            physical = f"{PHYSICS_NAME[axis]}_{segment}_{side}"
            joint = joints[physical]
            attrs = defaults[joint.get("class", "")]
            dofs.append({
                "flygym_axis": axis, "logical_joint": logical,
                "live_action_index": record["actuator_index"], "mjcf_joint": physical,
                "mjcf_type": attrs.get("type", "hinge"),
                "axis_in_body_local_frame": [float(x) for x in attrs.get("axis", "0 0 1").split()],
                "range_rad": [float(x) for x in attrs["range"].split()],
                "joint_class": joint.get("class"), "owning_body": body_name,
                "parent_body": "thorax", "child_body": f"femur_{segment}_{side}",
            })
        result.append({
            "leg": leg, "population_name": POPULATION_FOR_LEG[leg], "physical_dofs": dofs,
            "demonstrated_structure": (
                "Three separately named hinge coordinates are declared on the same coxa body; "
                "the coxa body is attached beneath the thorax and contains the femur child body. "
                "They form a co-located compound rotational articulation in this MJCF, not three "
                "separately nested anatomical body segments."
            ),
            "coordinate_frame_note": (
                "Axes are inherited MJCF joint axes in the coxa body's local frame (the omitted "
                "abduction axis uses MuJoCo's default 0 0 1); body pose/quaternion orients that "
                "frame. Mechanical structure does not establish biological axis specificity."
            ),
        })
    return result


def _models() -> list[dict[str, Any]]:
    return [
        {"model": "A_DUPLICATED_SCALAR", "biological_assumptions_required":
         "Assumes every labeled neuron responds independently to every modeled coxa coordinate.",
         "engineering_assumptions_required": "Three scalar encoders and an unspecified aggregation/scheduling rule.",
         "risk_duplicate_sensory_drive": "HIGH", "risk_inventing_axis_specificity": "HIGH",
         "compatibility_existing_malecns_interface": "Poor: one body-ID population would be written three times.",
         "existing_evidence_supports_implementation": False},
        {"model": "B_COMBINED_JOINT_STATE", "biological_assumptions_required":
         "Assumes a scalar summary is an adequate biological stimulus.",
         "engineering_assumptions_required": "Choose normalization and a scalar function; no such geometry is sourced.",
         "risk_duplicate_sensory_drive": "LOW", "risk_inventing_axis_specificity": "MEDIUM",
         "compatibility_existing_malecns_interface": "Structurally compatible with one population, not calibrated.",
         "existing_evidence_supports_implementation": False},
        {"model": "C_VECTOR_OR_SUBPOPULATION", "biological_assumptions_required":
         "A vector input need not imply neuron tuning, but assigning components to neurons would require missing evidence.",
         "engineering_assumptions_required": "Define vector features and an interface capable of consuming them.",
         "risk_duplicate_sensory_drive": "LOW if encoded once", "risk_inventing_axis_specificity": "HIGH if neurons are partitioned",
         "compatibility_existing_malecns_interface": "Requires an extension; current population drive is scalar per neuron.",
         "existing_evidence_supports_implementation": False},
        {"model": "D_UNSPECIFIED_DO_NOT_MODEL", "biological_assumptions_required": "None beyond the annotated broad association.",
         "engineering_assumptions_required": "None.", "risk_duplicate_sensory_drive": "NONE",
         "risk_inventing_axis_specificity": "NONE", "compatibility_existing_malecns_interface":
         "Fully compatible with retaining ambiguity and making no runtime change.",
         "existing_evidence_supports_implementation": True},
    ]


def build_multi_axis_audit(m5a: dict[str, Any] | None = None,
                           m5b1: dict[str, Any] | None = None) -> dict[str, Any]:
    m5a = build_audit() if m5a is None else m5a
    m5b1 = build_dissection(m5a=m5a) if m5b1 is None else m5b1
    raw = {p["name"]: p for p in json.loads(INTERFACE_MAP.read_text(encoding="utf-8"))["populations"]}
    candidates = {p["population_name"]: p for p in m5b1["candidate_populations"]}
    populations = [_source_evidence(raw[POPULATION_FOR_LEG[leg]], candidates[POPULATION_FOR_LEG[leg]])
                   for leg in LEGS]
    classifications = [{
        "leg": leg, "population_name": POPULATION_FOR_LEG[leg],
        "classification": "BROAD_JOINT_SUPPORTED",
        "basis": "Biological association supported; transduction geometry unresolved.",
    } for leg in LEGS]
    return {
        "schema_version": "M5B-2.0", "purpose": "read-only interface-model audit",
        "source_evidence": populations, "physical_dof_relationship": _physical_dofs(m5a),
        "engineering_model_evaluations": _models(),
        "female_flywire_flygym_precedent": {
            "source": "fly-brain-main/src/sim/senses.js",
            "physical_inputs_used": ["st.joint[tibia_<T#_side>]", "st.joint[coxa_<T#_side>]", "st.load[T#_side]"],
            "coxa_population_received_multiple_joint_signals": False,
            "joint_axes_separated_for_hair_plate": False,
            "tuning_or_direction_engineered": (
                "Yes. Only the coxa promotion/remotion coordinate was passed to a Gaussian population "
                "code with engineered bounds -0.3 to 1.7 and preferred values distributed by neuron index."
            ),
            "biological_annotations_justified_assignments": (
                "The broad coxa joint-angle annotation supports coxa association, but local annotations "
                "do not justify choosing that single axis, those bounds, or neuron-wise directional tuning."
            ),
            "historical_only_do_not_copy": True,
        },
        "implementability_classification": classifications,
        "conclusion": {
            "scientifically_explicit_modeled_multi_axis_encoder_defensible_now": False,
            "finding": "Biological association supported; transduction geometry unresolved.",
            "future_encoder_would_require_explicit_engineering_assumptions": [
                "coordinate normalization and neutral/reference pose", "position versus velocity/strain dependence",
                "scalar combination or vector representation", "sign, gain, range, saturation, and temporal dynamics",
                "neuron tuning/allocation (which must not be called biological without new evidence)",
            ],
        },
        "non_intervention": {"encoder_implemented": False, "simulation_initialized": False,
                             "m4a_m5a_m5b1_modified": False, "activation_eligibility_modified": False,
                             "neural_or_physics_runtime_modified": False},
    }


def serialized_audit(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
