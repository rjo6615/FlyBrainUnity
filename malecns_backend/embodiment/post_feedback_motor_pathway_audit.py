"""Offline M5D-5C audit of the immutable M5D-5B result.

This module only reduces recorded evidence and, when source neuron identities
exist, may inspect the read-only connectome.  It never invokes an experiment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "M5D-5C.0"
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "malecns_backend/embodiment"
AUTHORITATIVE_ARTIFACT = BASE / "interface_output/proprioceptive_closed_loop_100ms.json"
DEFAULT_OUTPUT = BASE / "interface_output/post_feedback_motor_pathway_audit.json"
M5D5B_LOCKS = {
    "interface_output/proprioceptive_closed_loop_100ms.json":
        "2dc15d8b3a3820823358f73673e45920f18a4e3bb9dd504dbeb35aa677982a10",
    "proprioceptive_closed_loop.py":
        "2f95c6b38d373d7026272c538b37437b400d92fd6168306a87dc0ca14c6480e9",
    "proprioceptive_closed_loop_audit.py":
        "01601e7008c948eb2b92c46105288550682ceecea62d7b4bec69d3c54669f30e",
    "_windows_proprioceptive_closed_loop_adapter.py":
        "487c83bdbbba663f0aba8ed0600e225d5d51cfcb3831f4d3a4e4cdb6ecb804e9",
}
REQUIRED_MILESTONES = ("C6", "C7", "C8", "C9", "C10", "C11", "C12")
CONDITIONS = ("CLOSED_LOOP_ENABLED", "MOTOR_OUTPUT_DISABLED")


def canonical_lf(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _field(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def validate_authoritative_semantics(artifact: Mapping[str, Any]) -> None:
    required = {
        "schema": "M5D-5B.0", "run_status": "COMPLETE",
        "classification": "CLOSED_LOOP_TO_CNS_CONFIRMED",
        "provenance.verified": True, "rng.aligned": True,
        "physics_safety.stable": True,
        "aggregate.directly_driven_proprioceptive_neurons": 392,
    }
    bad = {path: _field(artifact, path) for path, expected in required.items()
           if _field(artifact, path) != expected}
    missing = [key for key in REQUIRED_MILESTONES
               if _field(artifact, f"milestones.{key}") is None]
    if bad or missing:
        raise RuntimeError(
            f"M5D-5B authoritative semantic mismatch: fields={bad!r}, milestones={missing!r}")


def verify_provenance() -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify raw artifact bytes, canonical-LF sources, then semantics."""
    observed = {}
    for relative, expected in M5D5B_LOCKS.items():
        raw = (BASE / relative).read_bytes()
        digest = hashlib.sha256(raw if relative.endswith(".json") else canonical_lf(raw)).hexdigest()
        observed[relative] = digest
        if digest != expected:
            raise RuntimeError(f"M5D-5B provenance mismatch for {relative}: {digest}")
    artifact = json.loads(AUTHORITATIVE_ARTIFACT.read_bytes())
    validate_authoritative_semantics(artifact)
    return artifact, {"verified": True, "lock_method": {
        "authoritative_artifact": "raw-byte SHA-256",
        "implementation_sources": "canonical-LF SHA-256"}, "observed_locks": observed}


def _mapped_motor_inventory() -> list[dict[str, Any]]:
    interface = json.loads((ROOT / "malecns_backend/interface_map.json").read_text(encoding="utf-8"))
    result = []
    for record in interface["populations"]:
        if record["category"] == "muscles" and (
                record["name"].startswith("Ti extensor MN T") or
                record["name"].startswith("Ti flexor MN T")):
            result.append({"population": record["name"],
                           "body_ids": record["body_ids"],
                           "dense_indices": record["dense_indices"],
                           "neuron_count": len(record["dense_indices"]),
                           "provenance": "ANNOTATION_DERIVED"})
    return sorted(result, key=lambda item: item["population"])


def analyze(artifact: Mapping[str, Any], provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Make only deductions supported by fields persisted in M5D-5B."""
    validate_authoritative_semantics(artifact)
    c10 = artifact["milestones"]["C10"]
    unavailable = "INSUFFICIENT_TELEMETRY"
    populations = _mapped_motor_inventory()
    per_population = [{**p, "membrane_state_difference": unavailable,
        "spike_count_difference": unavailable, "earliest_state_difference_ms": None,
        "earliest_spike_difference_ms": None, "decoder_observer_difference": unavailable,
        "decoder_filtered_state_difference": unavailable,
        "extensor_or_flexor_activation_difference": unavailable,
        "raw_decoded_contribution_difference": unavailable} for p in populations]
    depths = {str(depth): {"status": unavailable, "anatomically_eligible_neurons": None,
        "state_divergent_after_C10": None, "spike_divergent_after_C10": None,
        "earliest_state_divergence_ms": None, "earliest_spike_divergence_ms": None,
        "spike_count_difference": None} for depth in range(1, 6)}
    return {
        "schema": SCHEMA, "run_status": "COMPLETE",
        "classification": "MIXED_OR_UNRESOLVED",
        "reason": ("M5D-5B retained aggregate downstream counts and mapped-motor non-divergence, "
                   "but not paired neuron identities/state trajectories, motor observer/filter "
                   "trajectories, or tactile trajectories required to localize the pathway failure."),
        "provenance": dict(provenance),
        "authoritative_m5d5b_result": {
            "schema": artifact["schema"], "run_status": artifact["run_status"],
            "classification": artifact["classification"], "milestones": artifact["milestones"],
            "rng_aligned": artifact["rng"]["aligned"],
            "physics_stable": artifact["physics_safety"]["stable"],
            "artifact_modified": False},
        "feedback_population": {
            "status": "PARTIAL_AGGREGATE_ONLY", "after_delivered_proprio_divergence_ms": c10,
            "directly_driven_proprioceptive_neurons": 392,
            "directly_driven_proprioceptive_neurons_counted_as_downstream": False,
            "directly_driven_tactile_neurons": unavailable,
            "state_divergent_downstream_neuron_count": artifact["global"]["downstream_nonproprioceptive_neurons_affected"],
            "spike_divergent_downstream_neuron_count": artifact["global"]["downstream_nonproprioceptive_spiking_neurons"],
            "first_state_divergence_ms": artifact["milestones"]["C11"],
            "first_spike_divergence_ms": artifact["milestones"]["C12"],
            "aggregate_spike_difference_events": artifact["global"]["downstream_spikes_after_feedback"],
            "per_neuron_body_ids_annotations_and_spike_differences": unavailable,
            "mapped_tibia_motor_neurons": populations},
        "sensory_attribution": {"classification": "INSUFFICIENT_TELEMETRY",
            "proprioceptive_timing_ms": {key: artifact["milestones"][key]
                for key in ("C7", "C8", "C9", "C10", "C11", "C12")},
            "tactile_physical_source_first_divergence_ms": None,
            "tactile_rate_first_divergence_ms": None,
            "tactile_candidate_first_divergence_ms": None,
            "tactile_delivered_first_divergence_ms": None,
            "reason": "The artifact records that tactile was enabled but persists no paired tactile trace."},
        "anatomical_reachability": {"status": unavailable,
            "connectome_available": True, "orientation": "presynaptic_to_postsynaptic",
            "targets": populations,
            "reason": "Aggregate M5D-5B evidence does not identify feedback-responsive source neurons; graph traversal from invented sources is prohibited.",
            "functional_connectivity_claimed": False},
        "path_depth_summary": depths,
        "dynamic_propagation": {"status": unavailable, "layers": depths,
            "disappearance_location": unavailable,
            "reason": "M5D-5B did not persist paired per-neuron traces or feedback-responsive identities."},
        "mapped_motor_subthreshold": {"status": unavailable, "populations": per_population,
            "c13_observed": artifact["milestones"]["C13"] is not None,
            "mapped_motor_populations_affected_after_feedback": artifact["global"]["mapped_motor_populations_affected_after_feedback"]},
        "decoder_analysis": {"status": unavailable,
            "reason": "Per-leg decoder observer, filter, activation, and raw contribution trajectories are null in the authoritative artifact."},
        "c1_telemetry": {"classification": "C1_TELEMETRY_INSUFFICIENT",
            "C1_ms": artifact["milestones"]["C1"], "first_raw_contribution_ms": artifact["milestones"]["C2"],
            "originating_population": None, "new_motor_spike_at_update": None,
            "already_nonzero_filter_state": None, "extensor_activation": None,
            "flexor_activation": None, "antagonist_signal": None,
            "filtered_state_before": None, "filtered_state_at_contribution": None},
        "limitations": [
            "No experiment was rerun and no parameter, decoder, sensory interface, physics, duration, drive, noise, or behavior logic was changed.",
            "CONNECTOME-DERIVED means MaleCNS anatomy/simulated dynamics; MODELED means transduction, decoding, and embodiment; OBSERVED means recorded condition differences.",
            "An anatomical path would not establish functional recruitment.",
            "The audit makes no claim of natural walking, biological proprioception or reflexes, emergent gait, CPG discovery, natural coordination, or biological muscle control."]}


def serialize(report: Mapping[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
