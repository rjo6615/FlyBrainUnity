"""M5D-5A six-tibia proprioceptive activation contract and reduction.

The live adapter is deliberately separate (``proprioceptive_activation_audit``).
This module contains the immutable protocol, provenance checks, candidate-event
sampler, and pure evidence reduction so that the intervention is unit testable
without FlyGym.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .sensory import SensoryEncoder
from .six_tibia import LEG_ORDER, load_six_tibia_interfaces

SCHEMA = "M5D-5A.0"
SEED = 1
DURATION_MS = 100.0
PHYSICS_DT_MS = 0.1
NEURAL_DT_MS = 0.5
CONDITIONS = ("PROPRIO_ENABLED", "PROPRIO_DISABLED")
ROOT = Path(__file__).resolve().parents[2]
LOCKS = {
    "sensory_feedback_boundary_100ms.json": "151eb07263b4c7d5e5af8668f8405738e320faac451742a1eecc765dd3fa20f9",
    "sensory_feedback_boundary.py": "71f8dabb2cca77670a32e493dc028619ec5f070097b5bf3aac04ad0432388585",
    "sensory_feedback_boundary_audit.py": "e61d501d856895519f320739a79ef17e8eef376f18cef1df5960496366e10732",
    "tactile_motor_closed_loop_100ms.json": "d684f38cd50edf6f494f00678d33a67c8cd89b50a34fd4815d5af90f05611e09",
    "tactile_motor_closed_loop.py": "8434a6a8e946c2405a1a2271956a9aa88e8f4ba412b0861c55e109b33637d1d6",
    "tactile_motor_closed_loop_audit.py": "450a98112047a4a271d01a29caafff76b960a9bf79b22af68fbc25106cb653c8",
}

M5D4E_SEMANTIC_LOCK = {
    "schema": "M5D-4E.0",
    "run_status": "COMPLETE",
    "classification": "NO_SENSOR_RELEVANT_PHYSICAL_DIVERGENCE",
    "first_blocked_boundary": "body physics -> active sensor physical source",
    "provenance.verified": True,
    "runner.exact_m5d4d_runner_reused": True,
    "prefix_reproduction.passed": True,
    "telemetry_validation.blind_spot": False,
    "telemetry_validation.m5d4d_was_correct": True,
}


def _lock_paths():
    base = ROOT / "malecns_backend/embodiment"
    return {
        "sensory_feedback_boundary_100ms.json": base / "interface_output/sensory_feedback_boundary_100ms.json",
        "sensory_feedback_boundary.py": base / "sensory_feedback_boundary.py",
        "sensory_feedback_boundary_audit.py": base / "sensory_feedback_boundary_audit.py",
        "tactile_motor_closed_loop_100ms.json": base / "interface_output/tactile_motor_closed_loop_100ms.json",
        "tactile_motor_closed_loop.py": base / "tactile_motor_closed_loop.py",
        "tactile_motor_closed_loop_audit.py": base / "tactile_motor_closed_loop_audit.py",
    }


def _validate_m5d4e_artifact(artifact: Mapping[str, Any]) -> None:
    """Fail closed unless the exact locked M5D-4E scientific result is present."""
    observed = {
        "schema": artifact.get("schema"),
        "run_status": artifact.get("run_status"),
        "classification": artifact.get("classification"),
        "first_blocked_boundary": artifact.get("first_blocked_boundary"),
        "provenance.verified": artifact.get("provenance", {}).get("verified"),
        "runner.exact_m5d4d_runner_reused": artifact.get("runner", {}).get(
            "exact_m5d4d_runner_reused"),
        "prefix_reproduction.passed": artifact.get("prefix_reproduction", {}).get("passed"),
        "telemetry_validation.blind_spot": artifact.get("telemetry_validation", {}).get(
            "blind_spot"),
        "telemetry_validation.m5d4d_was_correct": artifact.get(
            "telemetry_validation", {}).get("m5d4d_was_correct"),
    }
    if observed != M5D4E_SEMANTIC_LOCK:
        raise RuntimeError(f"M5D-4E semantic provenance mismatch: {observed!r}")


def verify_provenance() -> dict[str, Any]:
    """Verify raw artifacts, canonical-LF sources, and the embedded older chain."""
    observed = {}
    for name, path in _lock_paths().items():
        raw = path.read_bytes()
        if name.endswith(".py"):
            raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        observed[name] = hashlib.sha256(raw).hexdigest()
    if observed != LOCKS:
        raise RuntimeError(f"locked M5D-4E/M5D-4D provenance mismatch: {observed!r}")
    artifact = json.loads(_lock_paths()["sensory_feedback_boundary_100ms.json"].read_text(encoding="utf-8"))
    _validate_m5d4e_artifact(artifact)
    from .sensory_feedback_boundary import verify_provenance as verify_m5d4e_chain
    verify_m5d4e_chain()
    return {"verified": True, "locks": observed, "earlier_chain_verified": True}


def mapping_inventory() -> dict[str, dict[str, Any]]:
    return {leg: {"action_index": item.action_index, "joint_name": item.actuator_name,
        "population": item.sensor.name, "mapped_neuron_count": len(item.sensor.dense_indices),
        "dense_indices": list(item.sensor.dense_indices)}
        for leg, item in load_six_tibia_interfaces().items()}


def encoder_parameters() -> dict[str, Any]:
    return {"implementation": "malecns_backend.embodiment.sensory.SensoryEncoder",
        "angle_range_rad": [SensoryEncoder.angle_min_rad, SensoryEncoder.angle_max_rad],
        "preferred_positions": "(k + 0.5) / population_size",
        "gaussian_width_normalized": SensoryEncoder.width_normalized,
        "maximum_rate_hz": SensoryEncoder.maximum_rate_hz,
        "cutoff_hz": SensoryEncoder.cutoff_hz, "baseline_hz": SensoryEncoder.baseline_hz,
        "normalization": "(angle-angle_min)/(angle_max-angle_min)",
        "event_probability": "rate_hz * 0.5 / 1000"}


def proprio_rngs(seed: int = SEED):
    """Independent, stable per-leg PCG64 streams; recreate once per condition."""
    children = np.random.SeedSequence(seed).spawn(len(LEG_ORDER))
    return {leg: np.random.default_rng(child) for leg, child in zip(LEG_ORDER, children)}


def sample_candidates(rates_hz, rng, dt_ms: float = NEURAL_DT_MS):
    rates = np.asarray(rates_hz, dtype=np.float64)
    return np.flatnonzero(rng.random(len(rates)) < rates * dt_ms / 1000.0).astype(np.int32)


def classify(e: Mapping[str, Any]) -> str:
    if not e.get("provenance"): return "PROVENANCE_FAILURE"
    if not e.get("physics_ok"): return "PHYSICS_MISMATCH"
    if not e.get("rng_parity"): return "RNG_PARITY_FAILURE"
    if not e.get("pre_equal"): return "PRE_DELIVERY_NEURAL_DIVERGENCE"
    legs = e.get("propagated_legs", 0)
    if legs == 6: return "SIX_TIBIA_PROPRIOCEPTIVE_PROPAGATION_CONFIRMED"
    if legs: return "PARTIAL_PROPRIOCEPTIVE_PROPAGATION"
    if e.get("delivered"): return "PROPRIOCEPTIVE_DELIVERY_NO_DOWNSTREAM_EFFECT"
    if e.get("nonzero_rate") and not e.get("candidate"): return "NO_PROPRIOCEPTIVE_SPIKES"
    return "UNRESOLVED_PROPRIOCEPTIVE_FAILURE"


def base_report() -> dict[str, Any]:
    per_leg = {leg: {"physical_angle_range_rad": [None, None], "modeled_rate_range_hz": [None, None],
        "candidate_spike_count": 0, "delivered_spike_count": 0,
        "first_candidate_spike_ms": None, "first_delivered_spike_ms": None,
        "milestones": {f"P{i}": None for i in range(8)}} for leg in LEG_ORDER}
    return {"schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "reason": "Authoritative Windows FlyGym/MuJoCo run has not been executed",
        "protocol": {"seed": SEED, "duration_ms": DURATION_MS, "physics_dt_ms": PHYSICS_DT_MS,
            "neural_dt_ms": NEURAL_DT_MS, "conditions": list(CONDITIONS), "automatic_retries": 0,
            "parameter_mutations": []}, "mappings": mapping_inventory(),
        "encoder": encoder_parameters(), "rng": {"algorithm": "PCG64",
            "derivation": "SeedSequence(1).spawn(6), one stream per LEG_ORDER; recreated identically per condition",
            "candidate_common_random_numbers": True},
        "intervention": {"only_difference": "proprioceptive delivery gate",
            "enabled": "candidate proprioceptive indices admitted through MaleCNS external drive",
            "disabled": "same candidates computed and withheld", "motor_output_applied": False,
            "neural_motor_contribution_to_actuators": 0.0},
        "tactile": {"channel": "LM_Tarsus5_tactile", "encoder_modified": False,
            "external_drive_kind": "tactile", "proprioceptive_drive_kind": "proprioceptive"},
        "provenance": {"verified": False, "expected": LOCKS}, "pre_delivery_equivalence": None,
        "physics_identical": None, "candidate_parity": None, "per_leg": per_leg,
        "aggregate": {"directly_driven_proprioceptive_neurons": sum(x["mapped_neuron_count"] for x in mapping_inventory().values()),
            "candidate_spike_count": 0, "delivered_spike_count": 0,
            "distinct_downstream_state_divergent_neurons": 0,
            "distinct_downstream_spiking_neurons": 0, "downstream_spike_count": 0,
            "mapped_motor_populations_that_differ": []},
        "limitations": ["Modeled interface validation only; no claim of biological proprioception, gait, coordination, CPG activity, reflex behavior, or autonomous locomotion."]}


def analyze(enabled: Sequence[Mapping[str, Any]], disabled: Sequence[Mapping[str, Any]], provenance=None):
    """Reduce complete paired traces. Direct sensory neurons are excluded."""
    if len(enabled) != len(disabled) or not enabled: raise ValueError("paired nonempty traces required")
    report = base_report(); report.update(run_status="COMPLETE", reason=None,
        provenance=provenance or {"verified": True})
    inventory = report["mappings"]
    direct = {i for x in inventory.values() for i in x["dense_indices"]}
    first_delivery = next((r["time_ms"] for r in enabled if any(r["proprio"][l]["delivered"] for l in LEG_ORDER)), None)
    physics_equal = all(a["physics"] == b["physics"] for a, b in zip(enabled, disabled))
    parity = all(a["proprio"][l]["candidate"] == b["proprio"][l]["candidate"]
                 for a, b in zip(enabled, disabled) for l in LEG_ORDER)
    pre = [(a, b) for a, b in zip(enabled, disabled) if first_delivery is None or a["time_ms"] < first_delivery]
    pre_equal = all(a["physics"] == b["physics"] and a["tactile"] == b["tactile"] and
        a["neural_state"] == b["neural_state"] and a["motor"] == b["motor"] for a, b in pre)
    downstream_state, downstream_spiking, downstream_count, motor_diff = set(), set(), 0, set()
    propagated = 0
    for leg in LEG_ORDER:
        angles = [float(r["proprio"][leg]["angle_rad"]) for r in enabled]
        rates = [float(x) for r in enabled for x in r["proprio"][leg]["rates_hz"]]
        candidates = [(r["time_ms"], i) for r in enabled for i in r["proprio"][leg]["candidate"]]
        delivered = [(r["time_ms"], i) for r in enabled for i in r["proprio"][leg]["delivered"]]
        leg_boundary = delivered[0][0] if delivered else None
        state_time = spike_time = motor_time = None
        for a, b in zip(enabled, disabled):
            changed = {i for i, (x, y) in enumerate(zip(a["neural_state"], b["neural_state"])) if x != y} - direct
            spikes = (set(a["cns_spikes"]) ^ set(b["cns_spikes"])) - direct
            after_leg_delivery = leg_boundary is not None and a["time_ms"] >= leg_boundary
            if changed and after_leg_delivery and state_time is None: state_time = a["time_ms"]
            if spikes and after_leg_delivery and spike_time is None: spike_time = a["time_ms"]
            if changed: downstream_state.update(changed)
            if spikes: downstream_spiking.update(spikes); downstream_count += len(spikes)
            different_motors = {k for k in a["motor"] if a["motor"][k] != b["motor"][k]}
            if different_motors and after_leg_delivery and motor_time is None: motor_time = a["time_ms"]
            motor_diff.update(different_motors)
        p = report["per_leg"][leg]; p.update(physical_angle_range_rad=[min(angles), max(angles)],
            modeled_rate_range_hz=[min(rates), max(rates)], candidate_spike_count=len(candidates),
            delivered_spike_count=len(delivered), first_candidate_spike_ms=candidates[0][0] if candidates else None,
            first_delivered_spike_ms=delivered[0][0] if delivered else None)
        p["milestones"] = {"P0": enabled[0]["time_ms"], "P1": next((r["time_ms"] for r in enabled if any(r["proprio"][leg]["rates_hz"])), None),
            "P2": candidates[0][0] if candidates else None, "P3": delivered[0][0] if delivered else None,
            "P4": delivered[0][0] if delivered else None, "P5": state_time, "P6": spike_time, "P7": motor_time}
        if delivered and state_time is not None: propagated += 1
    report.update(physics_identical=physics_equal, candidate_parity=parity,
        pre_delivery_equivalence={"passed": pre_equal, "before_ms": first_delivery})
    report["aggregate"].update(candidate_spike_count=sum(x["candidate_spike_count"] for x in report["per_leg"].values()),
        delivered_spike_count=sum(x["delivered_spike_count"] for x in report["per_leg"].values()),
        distinct_downstream_state_divergent_neurons=len(downstream_state),
        distinct_downstream_spiking_neurons=len(downstream_spiking), downstream_spike_count=downstream_count,
        mapped_motor_populations_that_differ=sorted(motor_diff))
    report["classification"] = classify({"provenance": report["provenance"].get("verified"),
        "physics_ok": physics_equal, "rng_parity": parity, "pre_equal": pre_equal,
        "propagated_legs": propagated, "delivered": bool(report["aggregate"]["delivered_spike_count"]),
        "nonzero_rate": any(x["modeled_rate_range_hz"][1] > 0 for x in report["per_leg"].values()),
        "candidate": bool(report["aggregate"]["candidate_spike_count"])})
    return report
