"""M6A deterministic, read-only whole-leg motor mapping audit.

This module projects locked M4A/M5A annotation evidence.  It does not import a
runtime, initialize physics, decode activity, or issue an actuator command.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from . import full_leg_interface as m5a
from .six_leg_audit import generate_map

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "interface_output" / "whole_leg_motor_mapping_audit.json"

LEGS = ("LF", "LM", "LH", "RF", "RM", "RH")
JOINT_CLASSES = ("Coxa", "Coxa_roll", "Coxa_yaw", "Femur", "Femur_roll", "Tibia", "Tarsus1")
TIBIA_INDICES = {"LF": 5, "LM": 12, "LH": 19, "RF": 26, "RM": 33, "RH": 40}
ASSOCIATION_CLASSES = ("EXACT", "SUPPORTED", "AMBIGUOUS", "UNMAPPED", "MISSING")
MAPPING_STATUSES = ("VALIDATED", "SUPPORTED", "AMBIGUOUS", "UNMAPPED")
DECODER_READINESS = ("VALIDATED_EXISTING", "DIRECTIONALLY_RESOLVABLE", "MAGNITUDE_ONLY",
                     "AMBIGUOUS_DIRECTION", "INSUFFICIENT_EVIDENCE")
DIRECTIONAL_CLASSES = ("EXPLICIT_ANTAGONIST_PAIR", "EXPLICIT_SINGLE_DIRECTION",
                       "MULTIPLE_DIRECTIONAL_GROUPS", "NO_DIRECTIONAL_INFORMATION",
                       "AMBIGUOUS_DIRECTIONAL_INFORMATION")
TIERS = ("A", "B", "C", "D")

# Historical generated artifacts are locked as raw bytes.  Source locks use
# canonical LF so a checkout's newline convention cannot alter its identity.
PROVENANCE_LOCKS = {
    "malecns_backend/embodiment/six_leg_map.json":
        ("575186602ac1e5a6e3b2c6d680309880266f5d80e18fff44f989440f6cd0a4bc", "raw-bytes"),
    "malecns_backend/embodiment/interface_output/full_leg_interface_audit.json":
        ("758850ea659e49fd93a36a9606bea07a1d329739fbf6be8089060ee6d706c52e", "raw-bytes"),
    "malecns_backend/interface_map.json":
        ("24b7229bea6f24ff0e65fe09b202d42dc06819fe234194e3c3ab95b596319e0b", "raw-bytes"),
    "malecns_backend/embodiment/six_tibia.py":
        ("5fefc84d9abdf7b9fc1ddbe65c35a6576812ed4d43f364c8a634091bdf6a1bad", "canonical-lf"),
    "malecns_backend/embodiment/full_leg_interface.py":
        ("d8449c8f1beaf493bb43e04c23d1b423fe7f9fd93bc657740cfc64137cbfae6e", "canonical-lf"),
}

EXPECTED_M4_TOTALS = {"EXACT": 7, "SUPPORTED": 37, "AMBIGUOUS": 15,
                      "UNMAPPED": 303, "MISSING": 25}
EXPECTED_M5_SUMMARY = {"total_actuators": 42, "tier_1": 1, "tier_2": 5, "tier_3": 15,
                       "tier_4": 21, "activation_eligible": 6, "sensory_mapped": 6,
                       "motor_mapped": 38, "both_mapped": 6}


class AuditFailure(RuntimeError):
    """Fail-closed M6A error carrying a terminal classification."""
    def __init__(self, classification: str, message: str):
        super().__init__(message)
        self.classification = classification


def _bytes(path: Path, policy: str) -> bytes:
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n") if policy == "canonical-lf" else data


def verify_provenance(locks: dict[str, tuple[str, str]] = PROVENANCE_LOCKS) -> list[dict[str, Any]]:
    records = []
    for relative, (expected, policy) in locks.items():
        path = ROOT / relative
        actual = hashlib.sha256(_bytes(path, policy)).hexdigest() if path.is_file() else None
        records.append({"relative_path": relative, "sha256": actual, "expected_sha256": expected,
                        "hash_policy": policy, "verified": actual == expected})
    if not all(record["verified"] for record in records):
        failed = [r["relative_path"] for r in records if not r["verified"]]
        raise AuditFailure("PROVENANCE_FAILURE", f"authoritative input provenance mismatch: {failed}")
    return records


def _m4_totals(m4: dict[str, Any]) -> dict[str, int]:
    counts = Counter()
    for leg in m4["legs"]:
        for joint in leg["joints"]:
            counts.update((joint["sensory"]["status"], joint["motor"]["status"]))
    counts["UNMAPPED"] += len(m4["population_inventory"]["unresolved_leg_sensory"])
    counts["UNMAPPED"] += len(m4["population_inventory"]["unmapped_motor"])
    return {key: counts[key] for key in ASSOCIATION_CLASSES}


def _terms(candidate: dict[str, Any]) -> list[str]:
    metadata = candidate["annotation"]
    values = [candidate["population_name"], metadata.get("name"), metadata.get("type"),
              metadata.get("actuator")]
    return [str(value) for value in values if value not in (None, "")]


def _population_record(candidate: dict[str, Any], used: bool, unmapped: bool) -> dict[str, Any]:
    metadata = candidate["annotation"]
    direction = metadata.get("dir")
    label = "extensor" if direction == 1 else "flexor" if direction == -1 else None
    return {
        "population_name": candidate["population_name"], "body_ids": candidate["body_ids"],
        "distinct_mapped_neuron_count": candidate["distinct_neuron_count"],
        "side": metadata.get("side", "unknown"), "segment": candidate.get("segment") or "unknown",
        "annotation_terminology": _terms(candidate), "motor_class": metadata.get("kind") or metadata.get("subclass"),
        "directional_label": label, "explicit_direction": direction,
        "source_annotation_evidence": metadata, "source_provenance": candidate["source_provenance"],
        "used_by_six_tibia_decoder": used, "present_in_unmappedMotor": unmapped,
        "ambiguity": ("unmappedMotor supplies no annotation-backed leg joint association" if unmapped else None),
    }


def _directional(candidates: list[dict[str, Any]], shared: bool) -> tuple[str, list[str], bool]:
    labels = [p["directional_label"] for p in candidates if p["directional_label"]]
    terminology = sorted({term for p in candidates for term in p["annotation_terminology"]
                          if any(word in term.lower() for word in
                                 ("flex", "extens", "promot", "remot", "abduct", "adduct",
                                  "rotator", "levator", "depressor", "reductor", "tergotr", "sternotr"))})
    signs = {p["explicit_direction"] for p in candidates if p["explicit_direction"] in (-1, 1)}
    if shared:
        return "AMBIGUOUS_DIRECTIONAL_INFORMATION", terminology, False
    if signs == {-1, 1}:
        kind = "MULTIPLE_DIRECTIONAL_GROUPS" if len(candidates) > 2 else "EXPLICIT_ANTAGONIST_PAIR"
        return kind, terminology, True
    if signs:
        return "EXPLICIT_SINGLE_DIRECTION", terminology, False
    return "NO_DIRECTIONAL_INFORMATION", terminology, False


def _breakdown(records: list[dict[str, Any]], key: str) -> dict[str, Any]:
    result = {}
    for value in sorted({str(r[key]) for r in records}):
        subset = [r for r in records if str(r[key]) == value]
        result[value] = {
            "total": len(subset), "with_candidate": sum(bool(r["candidates"]) for r in subset),
            "unique_mapping": sum(r["unique_physical_mapping"] for r in subset),
            "ambiguous_mapping": sum(r["motor_mapping_status"] == "AMBIGUOUS" for r in subset),
            "directionally_resolvable_future": sum(r["decoder_readiness"] == "DIRECTIONALLY_RESOLVABLE" for r in subset),
            "tiers": {tier: sum(r["motor_embodiment_tier"] == tier for r in subset) for tier in TIERS},
        }
    return result


def build_audit(*, live_actuators: list[dict[str, Any]] | None = None,
                provenance_locks: dict[str, tuple[str, str]] = PROVENANCE_LOCKS) -> dict[str, Any]:
    provenance = verify_provenance(provenance_locks)
    m4, old = generate_map(), m5a.build_audit(live_actuators=live_actuators)
    if _m4_totals(m4) != EXPECTED_M4_TOTALS or old["summary"] != EXPECTED_M5_SUMMARY:
        raise AuditFailure("ANNOTATION_AUDIT_FAILURE", "locked M4A/M5A quantitative constraints differ")
    records = old["actuator_records"]
    expected_names = [f"joint_{leg}{joint}" for leg in LEGS for joint in JOINT_CLASSES]
    if len(records) != 42 or [r["actuator_name"] for r in records] != expected_names:
        raise AuditFailure("ACTUATOR_ORDER_FAILURE", "physical actuator order differs from locked M4A")

    six_names = {name for item in old["six_tibia_regression"]["interfaces"]
                 for name in item["motor_populations"]}
    if (not old["six_tibia_regression"]["passed"] or
            {i["leg"]: i["action_index"] for i in old["six_tibia_regression"]["interfaces"]} != TIBIA_INDICES):
        raise AuditFailure("SIX_TIBIA_REGRESSION_FAILURE", "six-tibia interface differs from locked M5")

    # Build forward candidates first, retaining historical association classes.
    forward: dict[str, list[dict[str, Any]]] = {}
    pop_source: dict[str, dict[str, Any]] = {}
    for record in records:
        items = []
        for candidate in record["motor_candidates"]:
            population = _population_record(candidate, candidate["population_name"] in six_names, False)
            population["segment"] = next(a["segment"] for a in m4["actuator_inventory"]
                                          if a["action_index"] == record["actuator_index"])
            pop_source.setdefault(population["population_name"], population)
            items.append({"population": population["population_name"], "body_ids": population["body_ids"],
                          "classification": candidate["mapping_confidence"],
                          "why": candidate["relationship_to_physical_joint"]})
        forward[record["actuator_name"]] = items

    # The population inventory is broader than forward M4A associations: it
    # also contains tarsus2/adhesion annotations (there is no corresponding
    # 42-action actuator) and the LM accessory tibia population intentionally
    # excluded by the locked decoder.  Inventory them without promoting them
    # to a physical association or changing the six-tibia interface.
    forward_names = set(pop_source)
    for raw in m4["population_inventory"]["leg_motor"]:
        candidate = m5a._ordered_population(raw)
        population = _population_record(candidate, candidate["population_name"] in six_names, False)
        population["segment"] = raw.get("segment") or "unknown"
        if population["population_name"] not in forward_names:
            population["ambiguity"] = (
                "annotation-backed leg motor population is retained, but locked M4A supplies no "
                "candidate association to one of the 42 physical actuators")
        pop_source.setdefault(population["population_name"], population)

    reverse = defaultdict(list)
    for actuator, items in forward.items():
        for item in items:
            reverse[item["population"]].append({"actuator": actuator, "classification": item["classification"]})
    shared_names = {name for name, associations in reverse.items()
                    if len({a["actuator"] for a in associations}) > 1}

    per_actuator, physical = [], []
    m4_actuators = {a["action_index"]: a for a in m4["actuator_inventory"]}
    for record in records:
        index, name = record["actuator_index"], record["actuator_name"]
        source = m4_actuators[index]
        joint_class = name.removeprefix(f"joint_{record['leg']}")
        candidates = forward[name]
        conflict = any(item["population"] in shared_names for item in candidates)
        validated = index == TIBIA_INDICES[record["leg"]]
        population_records = [pop_source[item["population"]] for item in candidates]
        directional_class, directional_terms, pair = _directional(population_records, conflict)
        unique = bool(candidates) and not conflict
        if validated:
            mapping, readiness, tier = "VALIDATED", "VALIDATED_EXISTING", "A"
        elif not candidates:
            mapping, readiness, tier = "UNMAPPED", "INSUFFICIENT_EVIDENCE", "D"
        elif conflict:
            mapping, readiness, tier = "AMBIGUOUS", "AMBIGUOUS_DIRECTION", "C"
        elif pair:
            mapping, readiness, tier = "SUPPORTED", "DIRECTIONALLY_RESOLVABLE", "B"
        else:
            mapping, readiness, tier = "SUPPORTED", "MAGNITUDE_ONLY", "C"
        candidate_axes = sorted({entry["actuator"] for item in candidates
                                 for entry in reverse[item["population"]]}) or [name]
        reason = ("population is annotation-associated with multiple FlyGym axes" if conflict else
                  "annotation actuator term selects this physical axis" if candidates else
                  "no annotation-backed candidate")
        physical.append({"global_action_index": index, "leg": record["leg"],
                         "physical_joint_name": name, "canonical_joint_class": joint_class,
                         "current_m5_activation_status": {"tier": record["activation_tier"],
                                                          "eligible": record["activation_eligible"]},
                         "validated_six_tibia": validated})
        per_actuator.append({
            "global_action_index": index, "actuator": name, "leg": record["leg"],
            "side": record["side"], "segment": source["segment"], "joint_class": joint_class,
            "candidates": candidates, "association_classification": record["motor_confidence"],
            "association_reason": (candidates[0]["why"] if candidates else
                                   "No bodymap muscle record names this side/segment actuator."),
            "motor_mapping_status": mapping, "decoder_readiness": readiness,
            "directional_structure": directional_class, "explicit_directional_terminology": directional_terms,
            "explicit_signed_pair": pair, "candidate_physical_axes": candidate_axes,
            "physical_axis_evidence": [{"axis": axis, "evidence": reason} for axis in candidate_axes],
            "unique_physical_mapping": unique, "physical_axis_reason": reason,
            "unresolved_shared_population_conflict": conflict, "motor_embodiment_tier": tier,
            "m6b_eligible": tier == "B",
        })

    # Include all annotation-backed mapped leg populations and retain every
    # unresolved unmappedMotor record without pretending it identifies a leg.
    unmapped = []
    for candidate in old["unassociated_unmapped_motor_evidence"]:
        unmapped.append(_population_record(candidate, False, True))
    motor_populations = sorted([*pop_source.values(), *unmapped],
                               key=lambda p: (p["population_name"], p["body_ids"]))
    reverse_records = []
    for population in sorted(reverse):
        reverse_records.append({"population": population, "body_ids": pop_source[population]["body_ids"],
                                "candidate_actuators": sorted(reverse[population], key=lambda x: x["actuator"]),
                                "physical_axis_decomposition_ambiguity": population in shared_names})
    conflicts = [r for r in reverse_records if r["physical_axis_decomposition_ambiguity"]]

    tiers = Counter(r["motor_embodiment_tier"] for r in per_actuator)
    summary = {
        "total_physical_actuators": 42,
        "actuators_with_any_annotation_backed_motor_candidate": sum(bool(r["candidates"]) for r in per_actuator),
        "actuators_with_unique_motor_mapping": sum(r["unique_physical_mapping"] for r in per_actuator),
        "actuators_with_ambiguous_mapping": sum(r["motor_mapping_status"] == "AMBIGUOUS" for r in per_actuator),
        "actuators_with_explicit_antagonist_or_directional_information": sum(
            r["directional_structure"] not in ("NO_DIRECTIONAL_INFORMATION", "AMBIGUOUS_DIRECTIONAL_INFORMATION")
            for r in per_actuator),
        "actuators_with_directionally_resolvable_future_decoder": sum(
            r["decoder_readiness"] == "DIRECTIONALLY_RESOLVABLE" for r in per_actuator),
        "actuators_with_magnitude_only_information": sum(r["decoder_readiness"] == "MAGNITUDE_ONLY" for r in per_actuator),
        "actuators_with_insufficient_evidence": sum(r["decoder_readiness"] == "INSUFFICIENT_EVIDENCE" for r in per_actuator),
        "shared_populations_spanning_multiple_physical_axes": len(conflicts),
        "tier_counts": {tier: tiers[tier] for tier in TIERS},
        "by_leg": _breakdown(per_actuator, "leg"), "by_joint_class": _breakdown(per_actuator, "joint_class"),
        "by_left_right": _breakdown(per_actuator, "side"), "by_thoracic_segment": _breakdown(per_actuator, "segment"),
    }
    eligible = [r["actuator"] for r in per_actuator if r["m6b_eligible"]]
    classification = ("WHOLE_LEG_MOTOR_AUDIT_COMPLETE" if eligible else
                      "WHOLE_LEG_MOTOR_AUDIT_COMPLETE_NO_M6B_ELIGIBLE_JOINTS")
    return {
        "schema": "M6A.0", "run_status": "COMPLETE", "classification": classification,
        "physical_actuators": physical, "motor_populations": motor_populations,
        "per_actuator": per_actuator, "reverse_population_mapping": reverse_records,
        "shared_population_conflicts": conflicts,
        "six_tibia_regression": {**old["six_tibia_regression"],
                                  "decoder_semantics": "explicit annotation sign; per-neuron directional mean; unchanged M5 IsolatedMotorDecoder"},
        "summary": summary, "m6b_eligible": eligible,
        "limitations": [
            "Annotation-backed candidate association is not demonstrated biological function.",
            "Connectivity, firing correlations, body motion, and desired locomotion were not used to infer mappings or sign.",
            "unmappedMotor records lack sufficient joint/segment annotation and remain unresolved.",
            "M6A neither authorizes activation nor constructs a decoder.",
        ],
        "provenance": {"verified": True, "inputs": provenance,
                       "semantic_constraints": {"m4_mapping_totals": EXPECTED_M4_TOTALS,
                                                "m5_summary": EXPECTED_M5_SUMMARY,
                                                "actuator_order": list(JOINT_CLASSES),
                                                "tibia_indices": TIBIA_INDICES}},
        "non_intervention": {"simulation_initialized": False, "physics_steps": 0,
                             "actuators_commanded": False, "decoders_added": False,
                             "sensory_encoders_added": False, "neural_dynamics_changed": False},
    }


def serialized_audit(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--live", action="store_true", help="read live adapter metadata without reset/step")
    args = parser.parse_args(argv)
    try:
        live = m5a.enumerate_live_actuators() if args.live else None
        result = build_audit(live_actuators=live)
    except AuditFailure as exc:
        print(f"{exc.classification}: {exc}")
        return 1
    text = serialized_audit(result)
    if args.write:
        OUTPUT.write_text(text, encoding="utf-8")
    if args.check and (not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != text):
        print("ANNOTATION_AUDIT_FAILURE: committed M6A artifact is stale")
        return 1
    print(result["classification"])
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
