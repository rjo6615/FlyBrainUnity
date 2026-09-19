"""M6B isolated Tier-B modeled motor-interface validation.

The committed artifact is a NOT_RUN protocol.  Live execution is deliberately
Windows-only and requires mechanical sign calibration before a contribution is
admitted.  This module does not alter MaleCNS, M5, or the six-tibia decoder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
M6A_PATH = HERE / "interface_output" / "whole_leg_motor_mapping_audit.json"
OUTPUT = HERE / "interface_output" / "isolated_tier_b_motor_validation.json"
M6A_SHA256 = "722ee9b3b1d6a0fad2bf8ef0f02fc63f49277c5f44e3bccf27898e6c4ea673d9"
SCHEMA = "M6B.0"
CANONICAL_SEED = 1
DURATION_MS = 500.0
OBSERVER_TAU_MS = 40.0
HALF_ACTIVATION_HZ = 17.0
DECODER_MAX_RAD = 0.25
SLEW_RAD_S = 4.0
TIER_B = (
    "joint_LFCoxa_yaw", "joint_LFFemur", "joint_LFTarsus1",
    "joint_LMCoxa_yaw", "joint_LMFemur", "joint_LHCoxa_yaw", "joint_LHFemur",
    "joint_RFCoxa_yaw", "joint_RFFemur", "joint_RFTarsus1",
    "joint_RMCoxa_yaw", "joint_RMFemur", "joint_RHCoxa_yaw", "joint_RHFemur",
)
TIBIA_INDICES = {5, 12, 19, 26, 33, 40}
PER_JOINT_CLASSIFICATIONS = (
    "ISOLATED_MOTOR_CAUSALITY_CONFIRMED", "NO_MAPPED_MOTOR_ACTIVITY",
    "MAPPED_MOTOR_ACTIVITY_NO_DECODER_OUTPUT", "DECODER_OUTPUT_NO_PHYSICAL_DIVERGENCE",
    "PRE_INTERVENTION_EQUIVALENCE_FAILURE", "PHYSICS_INSTABILITY", "SIGN_UNRESOLVED",
    "PROVENANCE_FAILURE", "INTERFACE_FAILURE",
)

class ValidationFailure(RuntimeError):
    def __init__(self, classification: str, message: str):
        super().__init__(message); self.classification = classification


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_locked_m6a(path: Path = M6A_PATH, expected_sha256: str = M6A_SHA256) -> dict[str, Any]:
    """Read and semantically verify the immutable, raw-byte-locked M6A artifact."""
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise ValidationFailure("PROVENANCE_FAILURE", "M6A raw-byte provenance mismatch")
    data = json.loads(path.read_text(encoding="utf-8"))
    required = (data.get("schema") == "M6A.0" and data.get("run_status") == "COMPLETE" and
                data.get("classification") == "WHOLE_LEG_MOTOR_AUDIT_COMPLETE" and
                data.get("summary", {}).get("tier_counts") == {"A": 6, "B": 14, "C": 18, "D": 4} and
                tuple(data.get("m6b_eligible", ())) == TIER_B and
                data.get("six_tibia_regression", {}).get("passed") is True)
    if not required:
        raise ValidationFailure("PROVENANCE_FAILURE", "M6A semantic lock mismatch")
    records = data.get("per_actuator", [])
    if [r["actuator"] for r in records if r.get("motor_embodiment_tier") == "B"] != list(TIER_B):
        raise ValidationFailure("PROVENANCE_FAILURE", "M6A Tier-B records differ")
    if sum(r.get("motor_embodiment_tier") == "A" for r in records) != 6:
        raise ValidationFailure("PROVENANCE_FAILURE", "M6A Tier-A regression differs")
    return data


def safe_contribution_bound(joint_min: float, joint_max: float, baseline: float,
                            decoder_max: float = DECODER_MAX_RAD) -> float:
    """Symmetric offset available at baseline, capped by decoder and joint range."""
    values = (joint_min, joint_max, baseline, decoder_max)
    if not all(math.isfinite(x) for x in values) or joint_min >= joint_max or not joint_min <= baseline <= joint_max or decoder_max <= 0:
        raise ValueError("invalid mechanical bound inputs")
    return max(0.0, min(decoder_max, baseline - joint_min, joint_max - baseline))


def activation(rate_hz: float) -> float:
    if not math.isfinite(rate_hz) or rate_hz < 0: raise ValueError("rate must be finite and nonnegative")
    return 1.0 - math.exp(-rate_hz * math.log(2.0) / HALF_ACTIVATION_HZ)


def decoded_contribution(positive_hz: float, negative_hz: float, bound_rad: float) -> float:
    if not 0 <= bound_rad <= DECODER_MAX_RAD: raise ValueError("unsafe contribution bound")
    return bound_rad * (activation(positive_hz) - activation(negative_hz))


def matched_control_gate(raw: float, condition: str) -> float:
    """The sole condition-dependent operation in the common actuator path."""
    if condition == "ENABLED": return float(raw)
    if condition == "MOTOR_OUTPUT_DISABLED": return 0.0
    raise ValueError("unknown condition")


def admitted_tier_b(selected: str, raw_by_actuator: Mapping[str, float], condition: str) -> dict[str, float]:
    if selected not in TIER_B or set(raw_by_actuator) - set(TIER_B): raise ValueError("non-Tier-B actuator")
    return {name: matched_control_gate(value, condition) if name == selected else 0.0
            for name, value in raw_by_actuator.items()}

EQUIVALENCE_FIELDS = ("qpos", "qvel", "action", "ctrl", "selected_joint_state",
                      "observer_state", "decoder_state", "sensory_state", "rng_state")

def strict_pre_intervention_equivalence(enabled: Sequence[Mapping[str, Any]],
                                        disabled: Sequence[Mapping[str, Any]],
                                        first_admitted_step: int | None) -> bool:
    if len(enabled) != len(disabled): return False
    stop = len(enabled) if first_admitted_step is None else first_admitted_step + 1
    for i, (left, right) in enumerate(zip(enabled[:stop], disabled[:stop])):
        for field in EQUIVALENCE_FIELDS:
            # At the boundary observer/decoder remain equal; action/ctrl may
            # diverge only after the admitted contribution is formed.
            if i == first_admitted_step and field in ("action", "ctrl"): continue
            if field not in left or field not in right or left[field] != right[field]: return False
    return True


def milestones_ordered(m: Mapping[str, int | None]) -> bool:
    """Permit causally valid same-update B0..B5 milestones."""
    values = [m.get(f"B{i}") for i in range(6)]
    present = [x for x in values if x is not None]
    return all(values[i] is not None for i in range(len(present))) and present == sorted(present)


def classify_joint(*, provenance: bool, sign_resolved: bool, equivalent: bool,
                   mapped_activity: bool, decoder_output: bool, admitted: bool,
                   joint_diverged: bool, divergence_before_admission: bool,
                   physics_valid: bool, interface_valid: bool = True) -> str:
    if not provenance: return "PROVENANCE_FAILURE"
    if not interface_valid: return "INTERFACE_FAILURE"
    if not sign_resolved: return "SIGN_UNRESOLVED"
    if not equivalent or divergence_before_admission: return "PRE_INTERVENTION_EQUIVALENCE_FAILURE"
    if not physics_valid: return "PHYSICS_INSTABILITY"
    if not mapped_activity: return "NO_MAPPED_MOTOR_ACTIVITY"
    if not decoder_output: return "MAPPED_MOTOR_ACTIVITY_NO_DECODER_OUTPUT"
    if not admitted or not joint_diverged: return "DECODER_OUTPUT_NO_PHYSICAL_DIVERGENCE"
    return "ISOLATED_MOTOR_CAUSALITY_CONFIRMED"


def m6c_eligible(per_joint: Sequence[Mapping[str, Any]]) -> list[str]:
    return [r["actuator"] for r in per_joint if r.get("classification") == "ISOLATED_MOTOR_CAUSALITY_CONFIRMED" and r.get("physical_sign_status") == "RESOLVED"]


def aggregate_classification(per_joint: Sequence[Mapping[str, Any]]) -> str:
    """Classify a complete 14-result set from observations, never intent."""
    if len(per_joint) != len(TIER_B) or {r.get("actuator") for r in per_joint} != set(TIER_B):
        raise ValueError("aggregate requires exactly one result for each Tier-B actuator")
    classes = [r.get("classification") for r in per_joint]
    if any(value == "PROVENANCE_FAILURE" for value in classes): return "PROVENANCE_FAILURE"
    if any(value == "INTERFACE_FAILURE" for value in classes): return "INTERFACE_SETUP_FAILURE"
    causal = classes.count("ISOLATED_MOTOR_CAUSALITY_CONFIRMED")
    if causal == 14: return "ISOLATED_TIER_B_VALIDATION_COMPLETE"
    if causal: return "ISOLATED_TIER_B_VALIDATION_COMPLETE_WITH_PARTIAL_CAUSALITY"
    return "ISOLATED_TIER_B_VALIDATION_COMPLETE_NO_CAUSAL_RESPONSES"


def _interfaces(m6a: Mapping[str, Any]) -> list[dict[str, Any]]:
    populations = {p["population_name"]: p for p in m6a["motor_populations"]}
    output = []
    for source in m6a["per_actuator"]:
        if source["actuator"] not in TIER_B: continue
        directional = []
        for candidate in source["candidates"]:
            p = populations[candidate["population"]]
            directional.append({
                "population": p["population_name"], "body_ids": p["body_ids"],
                "population_size": p["distinct_mapped_neuron_count"],
                "annotation_terminology": p["annotation_terminology"],
                "annotation_direction": p["explicit_direction"],
                "anatomical_direction": p["directional_label"],
            })
        output.append({
            "action_index": source["global_action_index"], "physical_joint": source["actuator"],
            "leg": source["leg"], "side": source["side"], "thoracic_segment": source["segment"],
            "joint_class": source["joint_class"], "directional_motor_populations": directional,
            "m6a_directional_classification": source["directional_structure"],
            "annotation_positive_group": [p["population"] for p in directional if p["annotation_direction"] == 1],
            "annotation_negative_group": [p["population"] for p in directional if p["annotation_direction"] == -1],
            "nmf_positive_group": None, "nmf_negative_group": None,
            "physical_sign_status": "PHYSICAL_SIGN_CALIBRATION_REQUIRED",
            "sign_assignment_justification": "M6A establishes anatomical opposition only; deterministic MuJoCo-axis perturbation and geometric inspection must establish the NMF coordinate sign before admission.",
            "mechanical_calibration": {"method": "deterministic ±epsilon qpos perturbation with MuJoCo joint-axis metadata and geometric endpoint displacement", "uses_neural_behavior": False, "status": "NOT_RUN"},
            "safe_contribution_bound_rad": None,
        })
    return output


def build_not_run_artifact() -> dict[str, Any]:
    m6a = load_locked_m6a()
    interfaces = _interfaces(m6a)
    return {
        "schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "protocol": {"canonical_seed": CANONICAL_SEED, "seed_sweep": False,
            "duration_ms_per_condition": DURATION_MS, "duration_frozen_before_live_run": True,
            "fresh_simulation_per_joint_and_condition": True, "conditions": ["ENABLED", "MOTOR_OUTPUT_DISABLED"],
            "observer_tau_ms": OBSERVER_TAU_MS, "half_activation_hz": HALF_ACTIVATION_HZ,
            "decoder_max_contribution_rad": DECODER_MAX_RAD, "slew_limit_rad_s": SLEW_RAD_S,
            "only_selected_tier_b_admitted": True, "tier_a_neural_contribution": False,
            "matched_control_condition_dependent_value": "admitted_neural_contribution",
            "synthetic_diagnostic": {"classification": "SYNTHETIC_INTERFACE_DIAGNOSTIC_ONLY", "part_of_scientific_result": False}},
        "m6a_lock": {"relative_path": str(M6A_PATH.relative_to(ROOT)), "hash_policy": "raw-bytes",
            "expected_sha256": M6A_SHA256, "actual_sha256": _sha256(M6A_PATH), "verified": True,
            "semantic_requirements": {"schema": "M6A.0", "run_status": "COMPLETE",
                "classification": "WHOLE_LEG_MOTOR_AUDIT_COMPLETE", "tier_counts": {"A": 6, "B": 14, "C": 18, "D": 4},
                "six_tibia_regression": "PASS", "exact_m6b_eligible": list(TIER_B)}},
        "interfaces": interfaces, "per_joint": [],
        "aggregate": {"total_tier_b_planned": 14, "total_tier_b_tested": 0, "sign_resolved": 0,
            "sign_unresolved": 14, "mapped_motor_active": 0, "decoder_active": 0,
            "causal_physical_response_confirmed": 0, "silent": 0, "failed_equivalence": 0, "unstable": 0,
            "by_joint_class": {}, "by_leg": {}, "by_left_right": {}, "by_thoracic_segment": {}},
        "m6c_eligible": [],
        "limitations": ["No scientific simulation has been executed.",
            "Annotation-backed anatomical direction is not an NMF coordinate sign.",
            "M6B can establish modeled isolated motor-interface causality, not biological motor function."],
        "provenance": {"verified": True, "artifact_kind": "PRE_REGISTERED_NOT_RUN_PROTOCOL",
            "scientific_run_number": None, "scientific_results_fabricated": False,
            "preservation_policy": "Scientific Run #1 is immutable; pre-simulation setup failures do not consume it."},
    }


def serialize(data: Mapping[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-not-run", action="store_true")
    parser.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv)
    if args.run_windows:
        # Fail before simulation rather than silently substituting a noncanonical runtime.
        try:
            from ._windows_isolated_tier_b_motor_validation_adapter import run_canonical
        except ImportError as exc:
            raise SystemExit(f"INTERFACE_SETUP_FAILURE: canonical Windows adapter unavailable: {exc}")
        run_canonical(build_not_run_artifact(), OUTPUT)
        return 0
    data = build_not_run_artifact(); text = serialize(data)
    if args.write_not_run: OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    if args.check and (not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != text):
        print("PROVENANCE_FAILURE: committed NOT_RUN artifact is stale"); return 1
    print("M6B NOT_RUN protocol verified"); return 0

if __name__ == "__main__": raise SystemExit(main())
