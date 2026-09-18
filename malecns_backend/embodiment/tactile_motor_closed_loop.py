"""Fail-closed evidence model for the locked M5D-4D experiment."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .tactile_motor_matched_control import (MatchedControlPipeline, atomic_write,
    decode_raw, serialize, _first_difference, FIELDS)
from .tactile_motor_loop import ACTUATOR_INDICES, NEURAL_DT_MS, _canonical_bytes
from .tactile_targeted_contact_calibration import DEFAULT_TIMESTEP_S
from .six_tibia import LEG_ORDER

SCHEMA = "M5D-4D.0"
SEED = 1
DURATION_MS = 100.0
CONDITIONS = ("TACTILE_MOTOR_ENABLED", "TACTILE_MOTOR_DISABLED")
ROOT = Path(__file__).resolve().parents[2]
M5D4C_ARTIFACT = ROOT / "malecns_backend/embodiment/interface_output/tactile_motor_matched_control_preflight.json"
M5D4C_IMPLEMENTATION = ROOT / "malecns_backend/embodiment/tactile_motor_matched_control.py"
M5D4C_LOCKS = {
    "artifact_sha256": "15e83fa88aa3e7a6206ea7bb736cd1ec446874dcf44079e0b79bcbf39c594901",
    "implementation_sha256": "0d75267b0203d9ad97e69bf9f75d57fdc5057beec682d925176479c00e8a2bc8",
}

def _event() -> dict[str, Any]:
    return {"observed": False, "time_ms": None, "physical_step": None,
            "neural_step": None, "leg": None, "value": None}

def verify_m5d4c_lock() -> dict[str, Any]:
    observed = {"artifact_sha256": hashlib.sha256(M5D4C_ARTIFACT.read_bytes()).hexdigest(),
        # Source locks elsewhere in the M5D provenance chain use canonical LF
        # bytes.  Keep this source lock fail-closed without making it depend on
        # Git's platform-specific checkout line endings.
        "implementation_sha256": hashlib.sha256(
            _canonical_bytes(M5D4C_IMPLEMENTATION.read_bytes())).hexdigest()}
    if observed != M5D4C_LOCKS:
        raise RuntimeError(f"M5D-4C provenance mismatch: {observed!r}")
    document = json.loads(M5D4C_ARTIFACT.read_text(encoding="utf-8"))
    expected = {"classification": "PREFLIGHT_PASS", "run_status": "COMPLETE"}
    if any(document.get(k) != v for k, v in expected.items()):
        raise RuntimeError("M5D-4C semantic provenance mismatch")
    return {"verified": True, "m5d4c": observed, "m5d4c_semantics": expected}

def base_report() -> dict[str, Any]:
    event_names = ("contact_evidence", "tactile_transduction_evidence", "tactile_delivery_evidence",
        "downstream_cns_evidence", "mapped_motor_evidence", "raw_neural_contribution_evidence",
        "admitted_neural_contribution_evidence", "action_divergence", "ctrl_divergence",
        "qacc_divergence", "qvel_divergence", "qpos_divergence",
        "modeled_sensory_encoding_divergence", "post_feedback_cns_divergence",
        "post_feedback_mapped_motor_divergence")
    report = {"schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "reason": "Validated Windows FlyGym/MuJoCo live execution has not been performed",
        "protocol": {"seed": SEED, "duration_ms": DURATION_MS,
            "physics_timestep_s": DEFAULT_TIMESTEP_S, "neural_timestep_ms": NEURAL_DT_MS,
            "conditions": list(CONDITIONS), "automatic_retries": 0},
        "provenance": {"verified": False, "m5d4c": M5D4C_LOCKS,
            "earlier_locks_verified": False},
        "m5d4c_prefix_validation": {"passed": None, "observed": None},
        "pre_intervention_equivalence": {"passed": None, "differences": None},
        "control_pipeline_definition": {"implementation": "tactile_motor_matched_control.MatchedControlPipeline",
            "reused_not_reimplemented": True, "condition_dependent_value": "admitted_neural_contribution",
            "order": ["measured_position", "baseline_target", "raw_decoded_neural_contribution",
                "experimental_gate", "admitted_neural_contribution", "sum", "range_clamp",
                "slew_limiter", "final_range_clamp", "actuator_command", "MuJoCo_ctrl"]},
        "intervention_definition": {"enabled": "admitted = raw", "disabled": "admitted = 0.0",
            "disabled_decoder_continues": True},
        "physical_sensory_divergence": {"contact_force": _event(), "semantic_contact": _event(),
            "proprioceptive_physical": _event()},
        "rng_parity": {"pre_feedback_exact": None, "random_stream_mismatch": None},
        "causal_milestones": {f"C{i}": None for i in range(15)},
        "causal_ordering": {"established": False, "sequence_ms": None},
        "per_leg_summary": {leg: {"actuator_index": ACTUATOR_INDICES[leg]} for leg in LEG_ORDER},
        "limitations": ["This artifact contains no fabricated live result.",
            "Claims apply only to the modeled embodiment, not biological reflexes or natural gait."]}
    report.update({name: _event() for name in event_names})
    return report

def classify(e: Mapping[str, Any]) -> str:
    if not e.get("provenance"): return "PROVENANCE_FAILURE"
    if not e.get("pre_equal"): return "PRE_INTERVENTION_DIVERGENCE"
    if not e.get("prefix"): return "PREFLIGHT_PREFIX_MISMATCH"
    if not e.get("intervention"): return "NO_NEURAL_INTERVENTION"
    if e.get("physical_before_intervention"): return "UNRESOLVED_CAUSAL_FAILURE"
    if not e.get("rng_parity"): return "RNG_PARITY_FAILURE"
    if not e.get("physical"): return "UNRESOLVED_CAUSAL_FAILURE"
    if not (e.get("physical_sensory") and e.get("sensory_encoding")):
        return "MOTOR_CAUSALITY_CONFIRMED_NO_FEEDBACK_WITHIN_WINDOW"
    if not e.get("post_cns"): return "MOTOR_TO_SENSORY_FEEDBACK_CONFIRMED"
    if not e.get("post_motor"): return "CLOSED_LOOP_TO_CNS_CONFIRMED"
    return "CLOSED_LOOP_CAUSAL_CHAIN_CONFIRMED"

def validate_prefix(report: Mapping[str, Any]) -> bool:
    expected = {"mapped": 14.5, "raw": 14.5, "admitted": 14.5,
        "action": 14.5, "ctrl": 14.6, "physical": 14.6}
    observed = report.get("m5d4c_prefix_validation", {}).get("observed") or {}
    return all(abs(float(observed.get(k, -1)) - v) < 1e-9 for k, v in expected.items())

def write_not_run(path: Path) -> None:
    report = base_report()
    try:
        from .tactile_motor_loop import verify_locked_hashes
        earlier = verify_locked_hashes(); current = verify_m5d4c_lock()
        report["provenance"] = {**current, "earlier_locks_verified": True,
            "earlier_locked_sha256": earlier}
    except Exception as error:
        report["classification"] = "PROVENANCE_FAILURE"; report["reason"] = str(error)
    atomic_write(path, report)
