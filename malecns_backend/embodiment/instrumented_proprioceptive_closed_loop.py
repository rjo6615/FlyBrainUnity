"""M5D-5D contract and observational reduction.

The experiment deliberately calls the locked M5D-5B live condition runner.
This module adds no update rule: it snapshots the returned trace and performs
paired, post-run analysis.  Large arrays live in a compressed NPZ sidecar.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .post_feedback_motor_pathway_audit import canonical_lf
SCHEMA = "M5D-5D.0"
SEED, DURATION_MS, PHYSICS_DT_MS, NEURAL_DT_MS, AUTOMATIC_RETRIES = 1, 100.0, 0.1, 0.5, 0
CONDITIONS = ("CLOSED_LOOP_ENABLED", "MOTOR_OUTPUT_DISABLED")
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "malecns_backend/embodiment"
TELEMETRY_SCHEMA = "M5D-5D-TELEMETRY.0"
RAW_ARTIFACT_LOCKS = {
    "interface_output/proprioceptive_closed_loop_100ms.json": "2dc15d8b3a3820823358f73673e45920f18a4e3bb9dd504dbeb35aa677982a10",
    # M5D-5C was generated on Windows.  Its authoritative CRLF bytes are
    # preserved by .gitattributes and deliberately receive no normalization.
    "interface_output/post_feedback_motor_pathway_audit.json": "7dd802b893c7c94f498a6742d1d3f6538019f5ec6fba54ac68c67714d5e32d48",
}
CANONICAL_SOURCE_LOCKS = {
    "proprioceptive_closed_loop.py": "2f95c6b38d373d7026272c538b37437b400d92fd6168306a87dc0ca14c6480e9",
    "proprioceptive_closed_loop_audit.py": "01601e7008c948eb2b92c46105288550682ceecea62d7b4bec69d3c54669f30e",
    "_windows_proprioceptive_closed_loop_adapter.py": "487c83bdbbba663f0aba8ed0600e225d5d51cfcb3831f4d3a4e4cdb6ecb804e9",
    "post_feedback_motor_pathway_audit.py": "ac067dd0c1d21a33e93ba9573e5a41233530eb6af7d01e9f17bbed87a6b8cb6c",
}
LOCKS = {**RAW_ARTIFACT_LOCKS, **CANONICAL_SOURCE_LOCKS}
M5D5C_LIMITATIONS = [
    "No experiment was rerun and no parameter, decoder, sensory interface, physics, duration, drive, noise, or behavior logic was changed.",
    "CONNECTOME-DERIVED means MaleCNS anatomy/simulated dynamics; MODELED means transduction, decoding, and embodiment; OBSERVED means recorded condition differences.",
    "An anatomical path would not establish functional recruitment.",
    "The audit makes no claim of natural walking, biological proprioception or reflexes, emergent gait, CPG discovery, natural coordination, or biological muscle control.",
]


def _field(value: Mapping[str, Any], path: str) -> Any:
    for part in path.split("."):
        if not isinstance(value, Mapping): return None
        value = value.get(part)
    return value


def verify_provenance() -> dict[str, Any]:
    """Lock bytes, historical semantics, and the complete M5D-5B chain."""
    observed = {}
    for relative, expected in RAW_ARTIFACT_LOCKS.items():
        raw = (BASE / relative).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        observed[relative] = digest
        if digest != expected:
            raise RuntimeError(f"M5D-5D provenance mismatch for {relative}: {digest}")
    for relative, expected in CANONICAL_SOURCE_LOCKS.items():
        digest = hashlib.sha256(canonical_lf((BASE / relative).read_bytes())).hexdigest()
        observed[relative] = digest
        if digest != expected:
            raise RuntimeError(f"M5D-5D provenance mismatch for {relative}: {digest}")
    b = json.loads((BASE / "interface_output/proprioceptive_closed_loop_100ms.json").read_text())
    c = json.loads((BASE / "interface_output/post_feedback_motor_pathway_audit.json").read_text())
    required_b = {"run_status": "COMPLETE", "classification": "CLOSED_LOOP_TO_CNS_CONFIRMED",
        "provenance.verified": True, "physics_safety.stable": True, "rng.aligned": True}
    required_c = {"schema": "M5D-5C.0", "run_status": "COMPLETE",
        "classification": "MIXED_OR_UNRESOLVED", "provenance.verified": True,
        "authoritative_m5d5b_result.artifact_modified": False,
        "feedback_population.status": "PARTIAL_AGGREGATE_ONLY",
        "feedback_population.directly_driven_proprioceptive_neurons_counted_as_downstream": False,
        "sensory_attribution.classification": "INSUFFICIENT_TELEMETRY",
        "anatomical_reachability.status": "INSUFFICIENT_TELEMETRY",
        "anatomical_reachability.functional_connectivity_claimed": False,
        "dynamic_propagation.status": "INSUFFICIENT_TELEMETRY",
        "mapped_motor_subthreshold.status": "INSUFFICIENT_TELEMETRY",
        "mapped_motor_subthreshold.c13_observed": False,
        "decoder_analysis.status": "INSUFFICIENT_TELEMETRY"}
    bad = {f"M5D-5B.{k}": _field(b, k) for k, v in required_b.items() if _field(b, k) != v}
    bad.update({f"M5D-5C.{k}": _field(c, k) for k, v in required_c.items() if _field(c, k) != v})
    if c.get("limitations") != M5D5C_LIMITATIONS:
        bad["M5D-5C.limitations"] = c.get("limitations")
    if bad: raise RuntimeError(f"M5D-5D authoritative semantics mismatch: {bad!r}")
    return {"verified": True, "historical_artifacts_modified": False,
        "m5d5b_scientific_run": 2, "m5d5c_audit": "authoritative",
        "lock_method": {"authoritative_artifacts": "raw-byte SHA-256",
            "implementation_sources": "canonical-LF SHA-256"},
        "observed_locks": observed}


def base_report() -> dict[str, Any]:
    return {"schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "reason": "Canonical Windows Scientific Run #1 has not been executed",
        "protocol": {"seed": SEED, "duration_ms": DURATION_MS,
            "physics_dt_ms": PHYSICS_DT_MS, "neural_dt_ms": NEURAL_DT_MS,
            "automatic_retries": AUTOMATIC_RETRIES, "conditions": list(CONDITIONS)},
        "architecture": {"scientific_update_path": "locked M5D-5B _run_condition",
            "recorder": "post-step observational snapshot; no RNG calls",
            "only_intervention": "admitted_neural_contribution: raw versus zero"},
        "provenance": {"verified": False, "expected_locks": LOCKS},
        "telemetry": {"schema": TELEMETRY_SCHEMA,
            "format": "NumPy compressed NPZ (lossless arrays) plus JSON manifest",
            "path": "instrumented_proprioceptive_closed_loop_telemetry.npz",
            "sha256": None, "sample_counts": None},
        "replication_guard": {"passed": None, "comparison": "M5D-5B Scientific Run #2",
            "exact_pre_intervention_equivalence": None, "causal_prefix_ordered": None},
        "milestones": {f"C{i}": None for i in range(14)},
        "post_feedback_source_set": {"state_divergent": [], "spike_divergent": []},
        "sensory_attribution": {"classification": None},
        "c1_resolution": {"classification": "C1_STILL_UNRESOLVED"},
        "c13_resolution": {"classification": "NO_POST_FEEDBACK_MOTOR_DIVERGENCE_WITHIN_WINDOW"},
        "anatomical_reachability": {"orientation": "presynaptic_to_postsynaptic", "depths": {}},
        "dynamic_path_analysis": {"depths": {}},
        "limitations": ["CONNECTOME-DERIVED anatomy/dynamics, MODELED transduction/decoding/embodiment, and OBSERVED paired differences remain distinct.",
            "No claim of natural walking, biological proprioception or reflex, emergent gait, CPG, natural coordination, or biological muscle control."]}


def classify(e: Mapping[str, Any]) -> str:
    if not e.get("provenance"): return "PROVENANCE_FAILURE"
    if not e.get("physics_stable"): return "PHYSICS_FAILURE"
    if not e.get("rng_aligned"): return "RNG_PARITY_FAILURE"
    if not e.get("instrumentation_complete"): return "INSTRUMENTATION_FAILURE"
    if not e.get("pre_equal"): return "REPLICATION_FAILED_PRE_INTERVENTION_EQUIVALENCE"
    if not e.get("prefix"): return "REPLICATION_FAILED_PREFIX"
    if e.get("C13"): return "INSTRUMENTED_FULL_CLOSED_LOOP_REPLICATED"
    if e.get("C11") and e.get("C12"): return "INSTRUMENTED_CLOSED_LOOP_TO_CNS_REPLICATED"
    return "REPLICATION_MOTOR_CAUSALITY_ONLY"


def sensory_attribution(proprio_ms, tactile_ms) -> str:
    if tactile_ms is None: return "NO_TACTILE_DIVERGENCE_WITHIN_WINDOW"
    if proprio_ms is None or tactile_ms < proprio_ms:
        return "TACTILE_FEEDBACK_PRECEDES_PROPRIOCEPTIVE_DELIVERY_DIVERGENCE"
    if proprio_ms < tactile_ms:
        return "PROPRIOCEPTIVE_FEEDBACK_PRECEDES_OTHER_ACTIVE_SENSORY_DIVERGENCE"
    return "SIMULTANEOUS_OR_MIXED_SENSORY_FEEDBACK"


def serialize(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
