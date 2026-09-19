"""M5D-5B locked six-tibia proprioceptive closed-loop contract.

The live adapter is separate.  This module deliberately contains only the
immutable protocol, the one-bit intervention, provenance, and fail-closed
evidence reduction so it remains testable without FlyGym or MuJoCo.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .motor import MotorDecoder, MotorSafety
from .proprioceptive_activation import (encoder_parameters, mapping_inventory,
    proprio_rngs, sample_candidates, verify_provenance as verify_m5d5a_chain)
from .six_tibia import LEG_ORDER
from .tactile_motor_loop import ACTUATOR_INDICES
from .tactile_motor_matched_control import MatchedControlPipeline

SCHEMA = "M5D-5B.0"
SEED, DURATION_MS, PHYSICS_DT_MS, NEURAL_DT_MS, AUTOMATIC_RETRIES = 1, 100.0, 0.1, 0.5, 0
CONDITIONS = ("CLOSED_LOOP_ENABLED", "MOTOR_OUTPUT_DISABLED")
ROOT = Path(__file__).resolve().parents[2]
M5D5A_LOCKS = {
    "interface_output/proprioceptive_activation_100ms.json": "3e0131be35d7b00004e1e014e5007ff7455b422b7fd67a2cd25a67eadead5ca9",
    "proprioceptive_activation.py": "0d6117d668e62d23de08c8148240c770785cabb8a6148669349c4f258b7c0a92",
    "proprioceptive_activation_audit.py": "468ecbfaef9e2c7b31236efe835e7fafc1673a899f851541b9086132d16a75b2",
}

M5D5A_AUTHORITATIVE_SEMANTICS = {
    "schema": "M5D-5A.0",
    "run_status": "COMPLETE",
    "classification": "SIX_TIBIA_PROPRIOCEPTIVE_PROPAGATION_CONFIRMED",
    "provenance.verified": True,
    "candidate_parity": True,
    "physics_identical": True,
    "aggregate.directly_driven_proprioceptive_neurons": 392,
    "protocol.seed": SEED,
    "protocol.duration_ms": DURATION_MS,
    "protocol.physics_dt_ms": PHYSICS_DT_MS,
    "protocol.neural_dt_ms": NEURAL_DT_MS,
    "protocol.automatic_retries": AUTOMATIC_RETRIES,
}


def _canonical_lf(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _field(artifact: Mapping[str, Any], path: str) -> Any:
    value: Any = artifact
    for component in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(component)
    return value


def validate_m5d5a_authoritative_semantics(artifact: Mapping[str, Any]) -> None:
    """Fail closed unless *artifact* is the locked scientific run and protocol."""
    mismatches = {path: _field(artifact, path)
        for path, expected in M5D5A_AUTHORITATIVE_SEMANTICS.items()
        if _field(artifact, path) != expected}
    if mismatches:
        raise RuntimeError(
            f"M5D-5A authoritative artifact semantic provenance mismatch: {mismatches!r}")


def verify_provenance() -> dict[str, Any]:
    base = ROOT / "malecns_backend/embodiment"
    observed = {}
    for name, expected in M5D5A_LOCKS.items():
        raw = (base / name).read_bytes()
        digest = hashlib.sha256(raw if name.endswith(".json") else _canonical_lf(raw)).hexdigest()
        observed[name] = digest
        if digest != expected:
            raise RuntimeError(f"M5D-5A provenance mismatch for {name}: {digest}")
    artifact = json.loads((base / next(iter(M5D5A_LOCKS))).read_text(encoding="utf-8"))
    validate_m5d5a_authoritative_semantics(artifact)
    verify_m5d5a_chain()
    return {"verified": True, "m5d5a_authoritative_complete": True,
        "raw_artifact_and_canonical_lf_source_locks": observed, "earlier_chain_verified": True}


def admit_neural_contribution(raw: float, condition: str) -> float:
    """The experiment's only condition-dependent operation."""
    if condition not in CONDITIONS:
        raise ValueError("unknown condition")
    return float(raw) if condition == CONDITIONS[0] else 0.0


MILESTONES = {f"C{i}": None for i in range(14)}


def base_report() -> dict[str, Any]:
    inventory = mapping_inventory()
    per_leg = {leg: {"action_index": ACTUATOR_INDICES[leg], "physical_tibia_angle_rad": None,
        "first_physical_source_divergence_ms": None, "maximum_angle_difference_rad": 0.0,
        "modeled_proprioceptive_rate_hz": None, "first_rate_divergence_ms": None,
        "maximum_rate_difference_hz": 0.0, "candidate_spike_count": {c: 0 for c in CONDITIONS},
        "first_candidate_divergence_ms": None, "delivered_spike_count": {c: 0 for c in CONDITIONS},
        "first_delivered_divergence_ms": None, "mapped_extensor_spike_count": {c: 0 for c in CONDITIONS},
        "mapped_flexor_spike_count": {c: 0 for c in CONDITIONS}, "decoder_filtered_states": None,
        "antagonist_signal": None, "raw_neural_contribution": None,
        "admitted_neural_contribution": None, "first_actuator_command_divergence_ms": None}
        for leg in LEG_ORDER}
    return {"schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "reason": "Authoritative Windows FlyGym/MuJoCo run has not been executed",
        "protocol": {"seed": SEED, "duration_ms": DURATION_MS, "physics_dt_ms": PHYSICS_DT_MS,
            "neural_dt_ms": NEURAL_DT_MS, "automatic_retries": AUTOMATIC_RETRIES,
            "conditions": list(CONDITIONS), "seed_sweep": False, "parameter_mutations": []},
        "architecture": {"sensory": "unchanged M5D-5A SensoryEncoder", "motor": "M5D-4C common MatchedControlPipeline",
            "condition_dependent_value": "admitted_neural_contribution", "both_conditions_proprioception": True,
            "both_conditions_tactile": True, "disabled_decoder_continues": True},
        "mappings": inventory, "actuator_indices": dict(ACTUATOR_INDICES), "encoder": encoder_parameters(),
        "decoder": {"observer": "spike counts converted to Hz; 40 ms low-pass", "half_activation_hz": MotorDecoder.half_activation_hz,
            "antagonist": "extensor_activation - flexor_activation", "maximum_offset_rad": MotorSafety().max_offset_rad,
            "joint_limits_rad": [MotorSafety().joint_min_rad, MotorSafety().joint_max_rad],
            "slew_limit_rad_s": MotorSafety().max_velocity_rad_s},
        "tactile": {"channel": "LM Tarsus5", "transduction_modified": False, "rng_modified": False},
        "rng": {"algorithm": "PCG64", "derivation": "SeedSequence(1).spawn(6) in LF,LM,LH,RF,RM,RH order",
            "common_random_numbers": True, "draw_counters": {c: {leg: 0 for leg in LEG_ORDER} for c in CONDITIONS},
            "aligned": None, "divergence_explanation": None},
        "provenance": {"verified": False, "expected_m5d5a_locks": M5D5A_LOCKS},
        "pre_intervention_equivalence": {"passed": None, "first_difference": None},
        "milestones": dict(MILESTONES), "per_leg": per_leg,
        "global": {"first_full_body_physical_divergence_ms": None,
            "first_six_tibia_source_divergence_ms": None, "first_proprioceptive_encoding_divergence_ms": None,
            "first_sensory_delivered_divergence_ms": None, "first_feedback_cns_state_divergence_ms": None,
            "first_feedback_cns_spike_divergence_ms": None, "first_subsequent_mapped_motor_divergence_ms": None,
            "downstream_nonproprioceptive_neurons_affected": 0,
            "downstream_nonproprioceptive_spiking_neurons": 0, "downstream_spikes_after_feedback": 0,
            "mapped_motor_populations_affected_after_feedback": [], "first_feedback_channel": None},
        "physics_safety": {"stable": None, "first_instability_ms": None, "affected_dof_or_joint": None},
        "aggregate": {"directly_driven_proprioceptive_neurons": 392,
            "directly_driven_neurons_excluded": True, "tactile_direct_neurons_separately_excluded": True},
        "science_controls": {"gait_controller": False, "cpg": False, "tripod_controller": False,
            "scripted_coordination": False, "new_drive_or_noise": False, "parameter_tuning": False},
        "limitations": ["Modeled interfaces only; this artifact makes no claim of natural walking, biological reflexes, or biological muscle control."]}


def classify(e: Mapping[str, Any]) -> str:
    if not e.get("provenance"): return "PROVENANCE_FAILURE"
    if not e.get("physics_stable"): return "PHYSICS_FAILURE"
    if not e.get("rng_aligned"): return "RNG_PARITY_FAILURE"
    if not e.get("pre_equal"): return "PRE_INTERVENTION_DIVERGENCE"
    if not e.get("C3"): return "NO_NEURAL_MOTOR_INTERVENTION"
    if not e.get("C6"): return "UNRESOLVED_CAUSAL_FAILURE"
    if not (e.get("C7") and e.get("C8") and e.get("C10")):
        return "MOTOR_CAUSALITY_CONFIRMED_NO_PROPRIOCEPTIVE_FEEDBACK_WITHIN_WINDOW"
    if not (e.get("C11") and e.get("C12")): return "MOTOR_TO_PROPRIOCEPTIVE_FEEDBACK_CONFIRMED"
    if not e.get("C13"): return "CLOSED_LOOP_TO_CNS_CONFIRMED"
    return "PROPRIOCEPTIVE_CLOSED_LOOP_CAUSAL_CHAIN_CONFIRMED"


def validate_order(m: Mapping[str, float | None]) -> None:
    chains = (("C3", "C4", "C5", "C6"), ("C3", "C7", "C8", "C10", "C11", "C12", "C13"))
    for chain in chains:
        values = [m[x] for x in chain if m.get(x) is not None]
        if values != sorted(values):
            raise ValueError(f"causal milestone ordering failure: {chain}")
    if m.get("C10") is not None:
        for key in ("C11", "C12"):
            if m.get(key) is not None and m[key] <= m["C10"]:
                raise ValueError(f"{key} must be strictly after C10")
    boundary = m.get("C11") if m.get("C11") is not None else m.get("C12")
    if m.get("C13") is not None and (boundary is None or m["C13"] <= boundary):
        raise ValueError("C13 must be after qualified feedback CNS divergence")


def _equal(left: Any, right: Any) -> bool:
    """Exact equality for trace values, including NumPy arrays."""
    try:
        import numpy as np
        if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
            return bool(np.array_equal(left, right))
    except ImportError:  # The pure contract remains importable without NumPy.
        pass
    return left == right


def _first_difference(enabled, disabled, field, after=None):
    for left, right in zip(enabled, disabled):
        if after is not None and left["time_ms"] < after:
            continue
        if not _equal(left[field], right[field]):
            return left["time_ms"]
    return None


def analyze(enabled: Sequence[Mapping[str, Any]], disabled: Sequence[Mapping[str, Any]],
            provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce the two raw live traces without manufacturing observations."""
    if not enabled or len(enabled) != len(disabled):
        raise ValueError("paired, nonempty, equally sized condition traces required")
    if any(a["time_ms"] != b["time_ms"] for a, b in zip(enabled, disabled)):
        raise ValueError("condition sample schedules differ")
    report = base_report()
    report.update(run_status="COMPLETE", reason=None, provenance=dict(provenance))

    def first(predicate, after=None):
        for a, b in zip(enabled, disabled):
            if after is None or a["time_ms"] >= after:
                if predicate(a, b):
                    return a["time_ms"]
        return None

    milestones = {
        "C0": first(lambda a, b: any(a["proprio"][leg]["delivered"] for leg in LEG_ORDER)),
        "C1": first(lambda a, b: any(sum(v.values()) for v in a["motor_spikes"].values())),
        "C2": first(lambda a, b: any(v != 0.0 for v in a["raw_neural_contributions"].values())),
        "C3": first(lambda a, b: any(v != 0.0 for v in a["admitted_neural_contributions"].values())),
        "C4": _first_difference(enabled, disabled, "action_joints"),
        "C5": _first_difference(enabled, disabled, "ctrl"),
    }
    milestones["C6"] = min((value for value in (
        _first_difference(enabled, disabled, "qacc"),
        _first_difference(enabled, disabled, "qvel"),
        _first_difference(enabled, disabled, "qpos")) if value is not None), default=None)
    milestones["C7"] = _first_difference(enabled, disabled, "physical_tibia_angles")
    milestones["C8"] = first(lambda a, b: any(
        a["proprio"][leg]["rates_hz"] != b["proprio"][leg]["rates_hz"] for leg in LEG_ORDER))
    milestones["C9"] = first(lambda a, b: any(
        a["proprio"][leg]["candidate"] != b["proprio"][leg]["candidate"] and
        a["proprio"][leg]["rng_before"] == b["proprio"][leg]["rng_before"]
        for leg in LEG_ORDER), milestones["C8"])
    milestones["C10"] = first(lambda a, b: any(
        a["proprio"][leg]["delivered"] != b["proprio"][leg]["delivered"]
        for leg in LEG_ORDER), milestones["C8"])

    direct = set(enabled[0]["direct_proprio_indices"])
    direct_tactile = set(enabled[0]["direct_tactile_indices"])
    feedback_boundary = milestones["C10"]
    downstream_state_indices = set()
    downstream_spike_indices = set()
    first_state = first_spike = None
    if feedback_boundary is not None:
        for a, b in zip(enabled, disabled):
            if a["time_ms"] <= feedback_boundary or a["neural_state"] is None:
                continue
            changed = ({int(i) for i in
                (a["neural_state"] != b["neural_state"]).nonzero()[0]}
                - direct - direct_tactile)
            spike_delta = ((set(a["cns_spikes"]) ^ set(b["cns_spikes"]))
                - direct - direct_tactile)
            if changed and first_state is None: first_state = a["time_ms"]
            if spike_delta and first_spike is None: first_spike = a["time_ms"]
            downstream_state_indices.update(changed)
            downstream_spike_indices.update(spike_delta)
    milestones["C11"], milestones["C12"] = first_state, first_spike
    qualified = min((x for x in (first_state, first_spike) if x is not None), default=None)
    milestones["C13"] = (first(lambda a, b: a["time_ms"] > qualified and
        a["motor_spikes"] != b["motor_spikes"], qualified) if qualified is not None else None)
    validate_order(milestones)
    report["milestones"] = milestones

    intervention = milestones["C3"]
    pre_fields = ("qpos", "qvel", "qacc", "contact_forces", "contact_set",
        "physical_tibia_angles", "proprio", "tactile", "sensory_delivered",
        "cns_state_digest", "cns_spikes", "motor_spikes", "observer_states",
        "decoder_states", "raw_neural_contributions", "baseline_targets",
        "previous_physical_targets", "action_joints", "ctrl")
    first_pre = None
    for a, b in zip(enabled, disabled):
        if intervention is not None and a["time_ms"] >= intervention: break
        for field in pre_fields:
            if not _equal(a[field], b[field]):
                first_pre = {"time_ms": a["time_ms"], "field": field}; break
        if first_pre: break
    report["pre_intervention_equivalence"] = {
        "passed": first_pre is None, "first_difference": first_pre}

    rng_aligned = all(a["rng_draw_counts"] == b["rng_draw_counts"] and all(
        a["proprio"][leg]["rng_before"] == b["proprio"][leg]["rng_before"] and
        a["proprio"][leg]["rng_after"] == b["proprio"][leg]["rng_after"]
        for leg in LEG_ORDER) for a, b in zip(enabled, disabled))
    report["rng"].update(aligned=rng_aligned,
        draw_counters={CONDITIONS[0]: enabled[-1]["rng_draw_counts"],
            CONDITIONS[1]: disabled[-1]["rng_draw_counts"]},
        divergence_explanation=(None if rng_aligned else "random stream state or draw count diverged"))
    physics_stable = all(all(__import__("numpy").all(__import__("numpy").isfinite(r[field]))
        for field in ("qpos", "qvel", "qacc", "ctrl", "contact_forces"))
        for r in (*enabled, *disabled))
    report["physics_safety"]["stable"] = bool(physics_stable)

    report["global"].update(first_full_body_physical_divergence_ms=milestones["C6"],
        first_six_tibia_source_divergence_ms=milestones["C7"],
        first_proprioceptive_encoding_divergence_ms=milestones["C8"],
        first_sensory_delivered_divergence_ms=milestones["C10"],
        first_feedback_cns_state_divergence_ms=milestones["C11"],
        first_feedback_cns_spike_divergence_ms=milestones["C12"],
        first_subsequent_mapped_motor_divergence_ms=milestones["C13"],
        downstream_nonproprioceptive_neurons_affected=len(downstream_state_indices),
        downstream_nonproprioceptive_spiking_neurons=len(downstream_spike_indices),
        downstream_spikes_after_feedback=sum(len((set(a["cns_spikes"]) ^
            set(b["cns_spikes"])) - direct - direct_tactile)
            for a, b in zip(enabled, disabled)
            if feedback_boundary is not None and a["time_ms"] > feedback_boundary),
        mapped_motor_populations_affected_after_feedback=sorted({leg
            for a, b in zip(enabled, disabled)
            for leg in LEG_ORDER if qualified is not None and a["time_ms"] > qualified
            and a["motor_spikes"][leg] != b["motor_spikes"][leg]}))
    for leg in LEG_ORDER:
        left = [r["proprio"][leg] for r in enabled]
        right = [r["proprio"][leg] for r in disabled]
        angles_a = [r["physical_tibia_angles"][leg] for r in enabled]
        angles_b = [r["physical_tibia_angles"][leg] for r in disabled]
        rates_a = [x for row in left for x in row["rates_hz"]]
        rates_b = [x for row in right for x in row["rates_hz"]]
        target = report["per_leg"][leg]
        target.update(physical_tibia_angle_rad={CONDITIONS[0]: angles_a,
                CONDITIONS[1]: angles_b},
            maximum_angle_difference_rad=max(abs(a-b) for a, b in zip(angles_a, angles_b)),
            modeled_proprioceptive_rate_hz={CONDITIONS[0]: rates_a,
                CONDITIONS[1]: rates_b},
            maximum_rate_difference_hz=max((abs(a-b) for a, b in zip(rates_a, rates_b)), default=0.0),
            candidate_spike_count={CONDITIONS[0]: sum(len(x["candidate"]) for x in left),
                CONDITIONS[1]: sum(len(x["candidate"]) for x in right)},
            delivered_spike_count={CONDITIONS[0]: sum(len(x["delivered"]) for x in left),
                CONDITIONS[1]: sum(len(x["delivered"]) for x in right)},
            first_physical_source_divergence_ms=first(lambda a,b,l=leg:
                a["physical_tibia_angles"][l] != b["physical_tibia_angles"][l]),
            first_rate_divergence_ms=first(lambda a,b,l=leg:
                a["proprio"][l]["rates_hz"] != b["proprio"][l]["rates_hz"]),
            first_candidate_divergence_ms=first(lambda a,b,l=leg:
                a["proprio"][l]["candidate"] != b["proprio"][l]["candidate"]),
            first_delivered_divergence_ms=first(lambda a,b,l=leg:
                a["proprio"][l]["delivered"] != b["proprio"][l]["delivered"]),
            first_actuator_command_divergence_ms=first(lambda a,b,l=leg:
                a["final_tibia_targets"][l] != b["final_tibia_targets"][l]))
    evidence = {"provenance": provenance.get("verified"), "physics_stable": physics_stable,
        "rng_aligned": rng_aligned, "pre_equal": first_pre is None,
        **{key: value is not None for key, value in milestones.items()}}
    report["classification"] = classify(evidence)
    return report


def serialize(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
