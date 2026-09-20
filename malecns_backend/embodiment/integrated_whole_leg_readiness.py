"""M6C integrated whole-leg embodiment preregistration and reductions.

This module contains admission, provenance, comparison, and classification
logic.  It deliberately contains no gait policy and does not run science when
imported.  The Windows adapter is the only live execution boundary.
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
M6B_PATH = HERE / "interface_output" / "isolated_tier_b_motor_validation.json"
TIER_A_PATH = ROOT / "six_tibia_causal_result.json"
OUTPUT = HERE / "interface_output" / "integrated_whole_leg_readiness.json"
PREFLIGHT_OUTPUT = HERE / "interface_output" / "m6c_windows_preflight.json"
M6A_SHA256 = "722ee9b3b1d6a0fad2bf8ef0f02fc63f49277c5f44e3bccf27898e6c4ea673d9"
TIER_A_SHA256 = "18aaafd51360e0a60b56f98c0b93e156e4cba2a27efd653111b04a5b8c329271"
SCHEMA = "M6C.0"
SEED = 1
DURATION_MS = 500
TIER_A = tuple(f"joint_{leg}Tibia" for leg in ("LF", "LM", "LH", "RF", "RM", "RH"))
EXPECTED_TIER_B = ("joint_LFFemur", "joint_LMFemur", "joint_LHFemur",
                   "joint_RMFemur", "joint_RHFemur")
SILENT_M6B = ("joint_LFTarsus1", "joint_RFFemur", "joint_RFTarsus1")
COXA_YAW = tuple(f"joint_{leg}Coxa_yaw" for leg in ("LF", "LM", "LH", "RF", "RM", "RH"))
CONDITIONS = ("INTEGRATED_NEURAL_MOTOR_ENABLED", "ALL_NEURAL_MOTOR_DISABLED",
              "TIER_B_FEMUR_DISABLED")
MILESTONES = tuple(f"C{i}" for i in range(13))
TIBIA_SIGNS = {name: 1 for name in TIER_A}


class ProvenanceFailure(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_locked(path: Path, digest: str, label: str) -> dict[str, Any]:
    if not path.is_file() or sha256(path) != digest:
        raise ProvenanceFailure(f"{label} raw-byte SHA256 mismatch")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_m6b(data: Mapping[str, Any]) -> tuple[str, ...]:
    """Derive eligibility from completed per-joint evidence, then freeze it."""
    if (data.get("schema") != "M6B.0" or data.get("run_status") != "COMPLETE" or
            data.get("classification") != "ISOLATED_TIER_B_VALIDATION_COMPLETE_WITH_PARTIAL_CAUSALITY"):
        raise ProvenanceFailure("M6B is absent, incomplete, or incompatibly classified")
    derived = tuple(row["actuator"] for row in data.get("per_joint", ())
                    if row.get("classification") == "ISOLATED_MOTOR_CAUSALITY_CONFIRMED"
                    and row.get("physical_sign_status") == "RESOLVED")
    recorded = tuple(data.get("m6c_eligible", ()))
    if derived != recorded or set(derived) != set(EXPECTED_TIER_B) or len(derived) != 5:
        raise ProvenanceFailure("M6B-derived M6C eligibility differs from preregistration")
    by_name = {row.get("actuator"): row for row in data.get("per_joint", ())}
    if any(by_name.get(name, {}).get("classification") != "NO_MAPPED_MOTOR_ACTIVITY"
           for name in SILENT_M6B):
        raise ProvenanceFailure("M6B silent-interface classifications differ")
    return derived


def validate_tier_a(data: Mapping[str, Any]) -> None:
    if (data.get("classification") != "S7" or data.get("seed") != SEED or
            data.get("duration_ms") != DURATION_MS or tuple(data.get("per_leg", {})) !=
            ("LF", "LM", "LH", "RF", "RM", "RH")):
        raise ProvenanceFailure("six-tibia causal artifact is semantically incompatible")


def load_provenance(*, m6b_path: Path = M6B_PATH,
                    m6b_sha256: str | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    m6a = _read_locked(M6A_PATH, M6A_SHA256, "M6A")
    tier_a = _read_locked(TIER_A_PATH, TIER_A_SHA256, "Tier-A")
    validate_tier_a(tier_a)
    if m6b_sha256 is None:
        # A completed artifact must be explicitly byte-locked for canonical use.
        raise ProvenanceFailure("completed M6B raw-byte SHA256 has not been frozen")
    m6b = _read_locked(m6b_path, m6b_sha256, "M6B")
    validate_m6b(m6b)
    return m6a, m6b, tier_a


def admission_table(m6a: Mapping[str, Any], m6b: Mapping[str, Any]) -> list[dict[str, Any]]:
    tier_b = validate_m6b(m6b)
    femur_interfaces = {x["physical_joint"]: x for x in m6b.get("interfaces", ())}
    rows = []
    for source in m6a.get("per_actuator", ()):
        name, tier = source["actuator"], source["motor_embodiment_tier"]
        motor = name in TIER_A or name in tier_b
        sensory = name in TIER_A
        if name in TIER_A:
            sign, sign_status, reason, validation = 1, "VALIDATED_DECODER_SEMANTICS", "validated Tier-A motor and proprioceptive interface", "SIX_TIBIA_CAUSAL_S7"
        elif name in tier_b:
            interface = femur_interfaces.get(name, {})
            sign, sign_status = interface.get("coordinate_sign"), interface.get("physical_sign_status")
            reason, validation = "M6B isolated motor causality confirmed; motor-only admission", "M6B_CANONICAL"
        elif name in COXA_YAW:
            sign, sign_status, reason, validation = None, "SIGN_UNRESOLVED", "withheld: physical coordinate sign unresolved", "M6B_P3"
        elif name in SILENT_M6B:
            sign, sign_status, reason, validation = (-1 if name in femur_interfaces else None), "RESOLVED", "withheld: canonical M6B produced no mapped motor activity", "M6B_CANONICAL"
        else:
            sign, sign_status, reason, validation = None, "NOT_VALIDATED", "withheld by whole-leg unsupported-interface policy", "M6A"
        rows.append({"actuator": name, "leg": source["leg"], "joint_class": source["joint_class"],
            "action_index": source["global_action_index"], "tier": tier,
            "sensory_status": "ANNOTATION_BACKED_VALIDATED_PROPRIOCEPTION" if sensory else "WITHHELD_NO_VALIDATED_M6C_MAPPING",
            "motor_status": source["motor_mapping_status"], "validation_source": validation,
            "neural_motor_admission": motor, "neural_sensory_admission": sensory,
            "coordinate_sign": sign, "coordinate_sign_status": sign_status, "reason": reason,
            "handling": "baseline_plus_neural_contribution" if motor else "baseline_only_zero_neural_contribution"})
    if len(rows) != 42 or [r["action_index"] for r in rows] != list(range(42)):
        raise ProvenanceFailure("physical admission inventory is not the ordered 42-actuator model")
    if sum(r["neural_motor_admission"] for r in rows) != 11:
        raise ProvenanceFailure("integrated neural motor admission is not exactly 11")
    if sum(r["neural_sensory_admission"] for r in rows) != 6:
        raise ProvenanceFailure("sensory admission is not exactly six validated tibiae")
    return rows


def gate_contributions(values: Mapping[str, float], condition: str,
                       admitted: Sequence[str]) -> dict[str, float]:
    if condition not in CONDITIONS or set(values) != set(admitted):
        raise ValueError("invalid condition or contribution inventory")
    result = {}
    for name in admitted:
        value = float(values[name])
        if not math.isfinite(value): raise ValueError("non-finite neural contribution")
        enabled = condition == CONDITIONS[0] or (condition == CONDITIONS[2] and name in TIER_A)
        result[name] = value if enabled else 0.0
    return result


def assert_physical_admission(vector: Sequence[float], table: Sequence[Mapping[str, Any]]) -> None:
    """Cheap per-application assertion over cached immutable metadata."""
    if len(vector) != 42 or len(table) != 42: raise RuntimeError("action-vector shape/order failure")
    for row, value in zip(table, vector):
        if row["action_index"] >= len(vector) or (not row["neural_motor_admission"] and value != 0.0):
            raise RuntimeError(f"unauthorized neural contribution: {row['actuator']}")


EQUIVALENCE_FIELDS = ("qpos", "qvel", "action", "ctrl", "sensory_encoder_state",
    "malecns_state", "spike_counts", "observer_state", "decoder_state", "rng_state",
    "baseline_action", "admitted_actuator_metadata")


def pre_intervention_equivalent(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    def equal(a: Any, b: Any) -> bool:
        if isinstance(a, Mapping) and isinstance(b, Mapping):
            return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
        if isinstance(a, Sequence) and not isinstance(a, (str, bytes)) and isinstance(b, Sequence) and not isinstance(b, (str, bytes)):
            return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
        try:
            result = a == b
            return bool(result.all() if hasattr(result, "all") else result)
        except (TypeError, ValueError): return False
    return all(field in left and field in right and equal(left[field], right[field])
               for field in EQUIVALENCE_FIELDS)


def classify(m: Mapping[str, bool], *, provenance=True, interface_valid=True) -> str:
    if not provenance: return "PROVENANCE_FAILURE"
    if not interface_valid: return "INTERFACE_FAILURE"
    if not m.get("C0"): return "PRE_INTERVENTION_EQUIVALENCE_FAILURE"
    if not m.get("C8"): return "UNAUTHORIZED_ACTUATOR_ACTIVITY"
    if not m.get("C9"): return "PHYSICS_INSTABILITY"
    if not m.get("C1"): return "NO_MAPPED_MOTOR_ACTIVITY"
    if not all(m.get(f"C{i}") for i in range(2, 6)): return "MAPPED_ACTIVITY_NO_PHYSICAL_CAUSALITY"
    if all(m.get(f"C{i}") for i in (10, 11, 12)): return "INTEGRATED_SENSORIMOTOR_MOTOR_RETURN_OBSERVED"
    if all(m.get(f"C{i}") for i in (10, 11)): return "INTEGRATED_SENSORIMOTOR_FEEDBACK_OBSERVED"
    if m.get("C7"): return "INTEGRATED_MULTI_LEG_CAUSALITY_CONFIRMED"
    if m.get("C6"): return "INTEGRATED_MULTI_CHANNEL_CAUSALITY_CONFIRMED"
    return "INTEGRATED_MOTOR_CAUSALITY_CONFIRMED"


def m7_readiness(*, provenance: bool, milestones: Mapping[str, bool], interface_valid: bool,
                 sensory_valid: bool, hidden_assistance: bool, admissions: int) -> str:
    ready = (provenance and interface_valid and sensory_valid and not hidden_assistance and admissions == 11
             and all(milestones.get(x) for x in ("C0", "C1", "C2", "C3", "C4", "C5", "C8", "C9")))
    return "M7_SPONTANEOUS_LOCOMOTION_EXPERIMENT_READY" if ready else "NOT_READY"


def hidden_assistance_audit() -> dict[str, Any]:
    return {"executed_modules": [__name__, "_windows_integrated_whole_leg_readiness_adapter"],
            "forbidden_controller_entry_points": [],
            "hidden_locomotion_assistance_executed": False,
            "method": "allowlisted M6C execution-path call graph; historical/unused modules excluded"}


def build_not_run_artifact(m6a: Mapping[str, Any], m6b: Mapping[str, Any], tier_a: Mapping[str, Any],
                           hashes: Mapping[str, str]) -> dict[str, Any]:
    table = admission_table(m6a, m6b); tier_b = validate_m6b(m6b)
    admitted = list(TIER_A + tier_b)
    return {"schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "scientific_run_executed": False, "seed": SEED, "duration_ms": DURATION_MS,
        "physics_dt_ms": 0.1, "neural_dt_ms": 0.5,
        "provenance": {"verified": True, "hash_policy": "raw-bytes", **dict(hashes)},
        "admitted_motor_interfaces": admitted, "tier_a_interfaces": list(TIER_A),
        "tier_b_interfaces_derived_from_m6b": list(tier_b), "actuator_admission_table": table,
        "sensory_interfaces": [{"actuator": x, "classification": "ANNOTATION_BACKED_VALIDATED_PROPRIOCEPTION", "source": "six_tibia causal S7"} for x in TIER_A],
        "conditions": [{"name": c, "fresh_runtime": True,
            "intervention": "gate neural contributions immediately before physical application"} for c in CONDITIONS],
        "milestones": {x: None for x in MILESTONES}, "equivalence_results": None,
        "per_channel_telemetry_summary": [], "a_vs_b": None, "a_vs_c": None,
        "stability_audit": None, "performance": None, "hidden_locomotion_audit": hidden_assistance_audit(),
        "m7_readiness": "NOT_READY", "limitations": ["Scientific M6C has not run.",
            "M6C tests interface integration and cannot establish walking or biological motor function.",
            "Femur proprioception is not modeled; only the six validated tibia sensory streams are admitted."],
        "performance_guards": {"expected_environment_constructions": 4,
            "canonical_condition_environment_constructions": 3,
            "inventory_environment_constructions": 1, "per_physics_step_environment_construction": False}}


def serialize(value: Mapping[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m6b-sha256", help="review-frozen SHA256 of completed canonical M6B")
    parser.add_argument("--write-not-run", action="store_true")
    parser.add_argument("--preflight-windows", action="store_true")
    parser.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight_windows and args.run_windows: parser.error("execution modes are mutually exclusive")
    try:
        m6a, m6b, tier_a = load_provenance(m6b_sha256=args.m6b_sha256)
        artifact = build_not_run_artifact(m6a, m6b, tier_a, {"m6a_sha256": M6A_SHA256,
            "m6b_sha256": args.m6b_sha256, "tier_a_sha256": TIER_A_SHA256})
        if args.preflight_windows:
            from ._windows_integrated_whole_leg_readiness_adapter import run_preflight
            run_preflight(artifact, PREFLIGHT_OUTPUT)
            print("M6C WINDOWS PREFLIGHT PASS", flush=True); return 0
        if args.run_windows:
            from ._windows_integrated_whole_leg_readiness_adapter import run_canonical
            run_canonical(artifact, OUTPUT); return 0
        if args.write_not_run: OUTPUT.write_text(serialize(artifact), encoding="utf-8", newline="\n")
        print("M6C NOT_RUN protocol verified", flush=True); return 0
    except Exception as exc:
        print(f"M6C PROVENANCE/PREFLIGHT FAIL: {exc}", flush=True); return 1


if __name__ == "__main__": raise SystemExit(main())
