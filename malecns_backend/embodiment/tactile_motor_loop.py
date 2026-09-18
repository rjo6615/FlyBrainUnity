"""M5D-4 tactile -> MaleCNS -> validated tibia actuator protocol.

The module contains the immutable protocol and analysis code.  Live FlyGym
construction is deliberately kept in :mod:`tactile_motor_loop_audit` so this
file can be imported and tested without MuJoCo.  No population name is parsed
to invent a motor mapping: the six M4A/M4B interfaces are loaded verbatim.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np

from .six_tibia import LEG_ORDER, SIX_LEG_MAP, load_six_tibia_interfaces
from .tactile_contact import TactileContactConfig
from .tactile_propagation import POPULATION_NAME, POPULATION_SIZE, tactile_population
from .tactile_targeted_contact_calibration import (
    CONTACT_PENETRATION, DEFAULT_TIMESTEP_S, ENGINEERING_THRESHOLD, SURFACE_NAME,
)

SCHEMA = "M5D-4.0"
CONDITIONS = ("TACTILE_MOTOR_ENABLED", "TACTILE_MOTOR_DISABLED")
DEFAULT_DURATION_MS = 100
DEFAULT_SEED = 1
NEURAL_DT_MS = 0.5
CONTACT_FORCE_ROW = 11
ACTUATOR_INDICES = {"LF": 5, "LM": 12, "LH": 19, "RF": 26, "RM": 33, "RH": 40}
SAMPLE_TIMES_MS = (25, 50, 75, 100)
TOLERANCE = 0.0

# M5D-3 is read only. Source/protocol locks use the SHA-256 of canonical LF
# bytes (rather than platform-dependent checkout bytes).  The M5D-3 result is
# a live-result lock: its static digest covers the scientifically relevant
# COMPLETE/P7 fields below and is accepted only after strict validation.
LOCKED_M5D3 = (
    "malecns_backend/embodiment/M5D3_TACTILE_PROPAGATION.md",
    "malecns_backend/embodiment/tactile_propagation.py",
    "malecns_backend/embodiment/tactile_propagation_audit.py",
    "malecns_backend/embodiment/interface_output/tactile_propagation.json",
)
LOCKED_PRIOR = (
    "malecns_backend/embodiment/tactile_contact.py",
    "malecns_backend/embodiment/tactile_targeted_contact_calibration.py",
    "malecns_backend/embodiment/interface_output/tactile_targeted_contact_calibration.json",
    "malecns_backend/embodiment/six_leg_map.json",
)
SOURCE_PROTOCOL_HASHES = MappingProxyType({
    "malecns_backend/embodiment/M5D3_TACTILE_PROPAGATION.md": "da5df00493e4701ac188c0f41d73348dcb00c61a1ace8e567487fb7b31ef4721",
    "malecns_backend/embodiment/tactile_propagation.py": "a1e07293c1676e5406500a00355c6f31979412f93aeab63edc16ec94934be3a6",
    "malecns_backend/embodiment/tactile_propagation_audit.py": "9fe739a94644224a3e6757b4ffc30d02630e8348ca653372eb6fe673aeddd003",
    "malecns_backend/embodiment/tactile_contact.py": "10fb5edb8c9d59036a703d4ebe1bfac9c67e986f0d42d1ea412666f7404011f9",
    "malecns_backend/embodiment/tactile_targeted_contact_calibration.py": "2c5de5a3de6c37d1d7d27093051b4c8f61ce6374641cb33eadeb6ec1294afcae",
    "malecns_backend/embodiment/interface_output/tactile_targeted_contact_calibration.json": "486ba63cc444b54d1012cd310be949e4bc35e088b2375a3b135342316df393df",
    "malecns_backend/embodiment/six_leg_map.json": "575186602ac1e5a6e3b2c6d680309880266f5d80e18fff44f989440f6cd0a4bc",
})

M5D3_LIVE_RESULT = MappingProxyType({
    "run_status": "COMPLETE",
    "causal_classification": "P7",
    "protocol_configuration.seed": 1,
    "protocol_configuration.duration_ms": 100,
    "protocol_configuration.neural_timestep_ms": 0.5,
    "protocol_configuration.physics_timestep_s": 0.0001,
    "protocol_configuration.neural_motor_output": False,
    "population.name": "tactile T2 left",
    "population.size": 378,
    "population.subsampled": False,
    "physical_contact_verification.verified": True,
    "physical_match_verification.matched": True,
    "physical_match_verification.maximum_qpos_absolute_difference": 0,
    "physical_match_verification.maximum_force_magnitude_difference": 0,
    "enabled_neural_summary.candidate_tactile_spikes": 404,
    "disabled_neural_summary.candidate_tactile_spikes": 404,
    "enabled_neural_summary.delivered_tactile_spikes": 296,
    "disabled_neural_summary.delivered_tactile_spikes": 0,
    "enabled_neural_summary.distinct_non_tactile_cns_neurons": 1474,
    "enabled_neural_summary.non_tactile_cns_spikes": 3128,
    "enabled_neural_summary.total_malecns_spikes": 3424,
    "disabled_neural_summary.non_tactile_cns_spikes": 0,
    "disabled_neural_summary.total_malecns_spikes": 0,
    "non_tactile_cns_divergence_summary.first_state": 5.0,
    "non_tactile_cns_divergence_summary.first_spike": 6.0,
    "mapped_motor_observational_summary.first_divergence_ms": 12.0,
    "mapped_motor_observational_summary.motor_output_decoded": False,
    "mapped_motor_observational_summary.motor_output_applied": False,
})
# SHA-256 of the sorted, compact JSON representation of M5D3_LIVE_RESULT.
# This is deliberately a literal, not calculated from the file being checked.
M5D3_LIVE_RESULT_SHA256 = "6f01c2b4aa16d6b51dbfba31055970dc7dea114ef317b688595bb1c9355b25cf"
EXPECTED_LOCKED_HASHES = MappingProxyType({
    **SOURCE_PROTOCOL_HASHES,
    "malecns_backend/embodiment/interface_output/tactile_propagation.json":
        M5D3_LIVE_RESULT_SHA256,
})


def _canonical_bytes(data: bytes) -> bytes:
    """Make text checkout hashes invariant under Git's Windows CRLF policy."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _nested_value(report: Mapping[str, Any], dotted_name: str) -> Any:
    value: Any = report
    for component in dotted_name.split("."):
        if not isinstance(value, Mapping) or component not in value:
            raise KeyError(dotted_name)
        value = value[component]
    return value


def validate_m5d3_live_result(report: Mapping[str, Any]) -> str:
    """Fail closed unless *report* is the authoritative M5D-3 COMPLETE/P7 run."""
    discrepancies = []
    observed = {}
    for name, expected in M5D3_LIVE_RESULT.items():
        try:
            actual = _nested_value(report, name)
        except KeyError:
            discrepancies.append(f"{name}: missing (expected {expected!r})")
            continue
        # bool is an int subclass, so equality alone would accept 0/1 here.
        if type(actual) is not type(expected) or actual != expected:
            discrepancies.append(f"{name}: {actual!r} (expected {expected!r})")
        observed[name] = actual
    if discrepancies:
        raise RuntimeError("M5D-3 live-result semantic validation failed: "
                           + "; ".join(discrepancies))
    canonical = json.dumps(observed, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != M5D3_LIVE_RESULT_SHA256:
        raise RuntimeError("M5D-3 live-result semantic manifest digest changed")
    return digest


def file_hashes(names: Sequence[str], root: Path | None = None) -> dict[str, str]:
    root = root or Path(__file__).resolve().parents[2]
    return {name: hashlib.sha256(_canonical_bytes((root / name).read_bytes())).hexdigest()
            for name in names}


def verify_locked_hashes(root: Path | None = None) -> dict[str, str]:
    root = root or Path(__file__).resolve().parents[2]
    source_names = tuple(SOURCE_PROTOCOL_HASHES)
    actual = file_hashes(source_names, root)
    changed = sorted(name for name, digest in actual.items()
                     if SOURCE_PROTOCOL_HASHES.get(name) != digest)
    if changed:
        raise RuntimeError(f"locked milestone artifacts changed: {changed}")
    result_name = "malecns_backend/embodiment/interface_output/tactile_propagation.json"
    try:
        report = json.loads((root / result_name).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read locked M5D-3 live result: {error}") from error
    actual[result_name] = validate_m5d3_live_result(report)
    return actual


def serialized_report(report: Mapping[str, Any]) -> str:
    """Stable strict JSON: scientific artifacts may never contain NaN/Inf."""
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False,
                      allow_nan=False) + "\n"


def atomic_write_report(path: Path, report: Mapping[str, Any]) -> None:
    """Atomically replace *path* after strict deterministic serialization."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized_report(report)); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


def validated_interfaces():
    interfaces = load_six_tibia_interfaces()
    actual = {leg: item.action_index for leg, item in interfaces.items()}
    if tuple(interfaces) != LEG_ORDER or actual != ACTUATOR_INDICES:
        raise RuntimeError(f"locked six-tibia actuator mapping changed: {actual}")
    if not all(item.active_antagonist_supported for item in interfaces.values()):
        raise RuntimeError("all six locked tibia antagonist interfaces are required")
    return interfaces


def classify(*, contact: bool, tactile_delivered: bool, downstream: bool,
             motor_spike: bool, decoded: bool, physical: bool, contact_feedback: bool,
             tactile_and_cns_feedback: bool, motor_feedback: bool,
             pre_motor_equivalent: bool = True, physics_stable: bool = True) -> str:
    """Return the greatest conservatively established engineering C-stage."""
    if not physics_stable: return "PHYSICS_UNSTABLE"
    if not pre_motor_equivalent: return "PRE_MOTOR_EQUIVALENCE_FAILED"
    if not contact: return "C0"
    if not tactile_delivered: return "C1"
    # The requested ladder has no separate label for delivered input that did
    # not propagate downstream; conservatively retain it at C1.
    if not downstream: return "C1"
    if not motor_spike: return "C2"
    if not decoded: return "C3"
    if not physical: return "C4"
    if not contact_feedback: return "C5"
    if not tactile_and_cns_feedback: return "C6"
    if not motor_feedback: return "C7"
    return "C8"


def first_time(rows, predicate):
    return next((float(row["time_ms"]) for row in rows if predicate(row)), None)


def analyze(enabled: Sequence[Mapping], disabled: Sequence[Mapping], *, tolerance=TOLERANCE) -> dict:
    """Compare matched telemetry with feedback stages gated in causal order.

    Rows are post-step samples.  Exact comparisons are intentional before the
    intervention.  A feedback event only counts strictly after the first body
    divergence; initial contact is therefore never mislabeled as feedback.
    """
    if len(enabled) != len(disabled) or [x["time_ms"] for x in enabled] != [x["time_ms"] for x in disabled]:
        raise ValueError("condition sample schedules differ")
    def different(a, b): return not np.array_equal(np.asarray(a), np.asarray(b))
    applied = first_time(enabled, lambda r: any(abs(r["applied_output"][l]) > tolerance for l in LEG_ORDER))
    motor = first_time(enabled, lambda r: any(r["motor_spikes"][l] for l in LEG_ORDER))
    decoded = first_time(enabled, lambda r: any(abs(r["decoded_output"][l]) > tolerance for l in LEG_ORDER))
    deltas = np.asarray([[a["tibia_qpos"][l] - b["tibia_qpos"][l] for l in LEG_ORDER]
                         for a, b in zip(enabled, disabled)], dtype=float)
    physical = next((float(a["time_ms"]) for a, d in zip(enabled, deltas)
                     if np.any(np.abs(d) > tolerance)), None)
    force = next((float(a["time_ms"]) for a, b in zip(enabled, disabled)
                  if physical is not None and a["time_ms"] >= physical and
                  a["force_magnitude"] != b["force_magnitude"]), None)
    exact_contact = next((float(a["time_ms"]) for a, b in zip(enabled, disabled)
                          if physical is not None and a["time_ms"] >= physical and
                          a["contact_metadata"] != b["contact_metadata"]), None)
    sensory = next((float(a["time_ms"]) for a, b in zip(enabled, disabled)
                    if physical is not None and a["time_ms"] >= physical and
                    (a["modeled_rate_hz"] != b["modeled_rate_hz"] or
                     a["candidate_events"] != b["candidate_events"] or
                     a["delivered_events"] != b["delivered_events"])), None)
    cns = next((float(a["time_ms"]) for a, b in zip(enabled, disabled)
                if sensory is not None and a["time_ms"] >= sensory and
                (a["cns_spikes"] != b["cns_spikes"] or different(a["neural_state"], b["neural_state"]))), None)
    motor_fb = next((float(a["time_ms"]) for a, b in zip(enabled, disabled)
                     if cns is not None and a["time_ms"] >= cns and
                     a["motor_spikes"] != b["motor_spikes"]), None)
    pre = [i for i, row in enumerate(enabled) if applied is None or row["time_ms"] < applied]
    fields = ("tibia_qpos", "full_qpos", "force_magnitude", "contact_metadata",
              "candidate_events", "delivered_events", "neural_state", "motor_spikes",
              "decoder_state", "decoded_output")
    pre_equal = all(all(enabled[i][key] == disabled[i][key] for key in fields) for i in pre)
    per_leg = {}
    for j, leg in enumerate(LEG_ORDER):
        series = deltas[:, j] if len(deltas) else np.asarray([])
        by_time = {float(r["time_ms"]): float(d) for r, d in zip(enabled, series)}
        per_leg[leg] = {"difference_rad_at_ms": {str(t): by_time.get(float(t)) for t in SAMPLE_TIMES_MS},
          "final_difference_rad": float(series[-1]) if len(series) else 0.0,
          "maximum_absolute_difference_rad": float(np.max(np.abs(series))) if len(series) else 0.0}
    norms = np.linalg.norm(deltas, axis=1) if len(deltas) else np.asarray([])
    full_differences = [np.asarray(a["full_qpos"]) - np.asarray(b["full_qpos"])
                        for a, b in zip(enabled, disabled)]
    full_max = max((float(np.max(np.abs(x))) for x in full_differences), default=0.0)
    return {"pre_motor_equivalence": {"passed": pre_equal, "strict_equality": True,
              "sample_count": len(pre), "first_applied_output_ms": applied},
      "timing_milestones_ms": {"first_mapped_tibia_motor_spike": motor,
        "first_nonzero_decoded_tibia_output": decoded, "first_applied_neural_output": applied,
        "first_physical_qpos_divergence": physical, "first_lm_tarsus5_force_divergence": force,
        "first_exact_contact_state_divergence": exact_contact,
        "first_sensory_feedback_divergence": sensory,
        "first_subsequent_cns_divergence": cns,
        "first_subsequent_mapped_motor_divergence": motor_fb},
      "per_leg_physical_divergence": per_leg,
      "six_tibia_trajectory": {"l2_norm": float(np.linalg.norm(deltas)),
        "rms_difference_rad": float(math.sqrt(np.mean(np.square(deltas)))) if deltas.size else 0.0,
        "maximum_sample_l2_norm_rad": float(max(norms, default=0.0))},
      "full_body_physical_divergence": {"maximum_absolute_qpos_difference": full_max,
        "direct_actuation_interpretation": False},
      "contact_force_feedback": {"first_divergence_ms": force},
      "tactile_feedback_divergence": {"first_divergence_ms": sensory},
      "downstream_cns_feedback_divergence": {"first_divergence_ms": cns},
      "subsequent_mapped_motor_divergence": {"first_divergence_ms": motor_fb}}


def base_report(duration_ms=DEFAULT_DURATION_MS, seed=DEFAULT_SEED, *,
                verify_provenance: bool = True) -> dict:
    """Build the protocol report, validating provenance before other setup.

    ``verify_provenance=False`` exists only for static configuration tests; the
    audit entry point never uses it.
    """
    locked = (verify_locked_hashes() if verify_provenance else
              dict(EXPECTED_LOCKED_HASHES))
    population = tactile_population(); interfaces = validated_interfaces()
    tactile = TactileContactConfig(seed=seed)
    mapping_hash = hashlib.sha256(SIX_LEG_MAP.read_bytes()).hexdigest()
    return {"schema_version": SCHEMA, "run_status": "NOT_RUN",
      "reason": "requires validated Windows FlyGym/MuJoCo/MaleCNS runtime; invoke with --live",
      "protocol_configuration": {"conditions": list(CONDITIONS), "duration_ms": duration_ms,
        "seed": seed, "physical_timestep_s": DEFAULT_TIMESTEP_S, "neural_timestep_ms": NEURAL_DT_MS,
        "only_intended_difference": "decoded tibia contribution applied to physical actuators"},
      "locked_provenance": {"m5d3_live_result_semantically_validated": verify_provenance,
        "m5d3_locked_digest": {x: locked[x] for x in LOCKED_M5D3},
        "prior_milestone_sha256": {x: locked[x] for x in LOCKED_PRIOR}},
      "physical_contact_verification": {"leg": "LM", "segment": "Tarsus5",
        "contact_forces_row": CONTACT_FORCE_ROW, "surface": SURFACE_NAME,
        "penetration_model_units": CONTACT_PENETRATION, "threshold": ENGINEERING_THRESHOLD,
        "exact_unordered_geom_pair_required": True, "verified": None},
      "biological_tactile_population": {"name": population.name, "size": len(population.body_ids),
        "body_ids": list(population.body_ids), "dense_indices": list(population.dense_indices), "subsampled": False},
      "tactile_encoder_parameters": {"maximum_modeled_rate_hz": tactile.maximum_modeled_rate_hz,
        "transient_duration_ms": tactile.transient_duration_ms, "envelope": "linear decay",
        "sustained_contact_retrigger": False, "release_rearms": True},
      "motor_mapping_provenance": {"source": str(SIX_LEG_MAP.relative_to(SIX_LEG_MAP.parents[2])),
        "sha256": mapping_hash, "mapping": "existing validated M4A/M4B six-tibia mapping",
        "new_assignments_inferred": False},
      "decoder_parameters": {"implementation": "six_tibia.IsolatedMotorDecoder + motor.MotorDecoder",
        "filter_tau_ms": 40.0, "half_max_hz": 17.0, "activation": "1-exp(-Hz*ln(2)/17)",
        "antagonist": "extensor-flexor", "maximum_offset_rad": 0.25,
        "slew_limit_rad_s": 4.0, "base": "current measured joint position",
        "order": ["candidate target", "actuator range clamp", "slew limit", "final actuator clamp"]},
      "actuator_indices": ACTUATOR_INDICES,
      "physical_neural_actuation_targets": [{"leg": leg, "joint": "Tibia",
        "actuator": interfaces[leg].actuator_name, "index": interfaces[leg].action_index} for leg in LEG_ORDER],
      "excluded_actuation_joints": ["coxa", "coxa_roll", "coxa_yaw", "femur", "femur_roll", "tarsus1"],
      "rng_parity": {"passed": None}, "pre_motor_equivalence": {"passed": None},
      "timing_milestones_ms": {name: None for name in ("first_verified_contact", "first_nonzero_force",
        "first_modeled_tactile_rate", "first_candidate_tactile_spike", "first_delivered_tactile_spike",
        "first_non_tactile_cns_state_change", "first_mapped_tibia_motor_spike",
        "first_nonzero_decoded_tibia_output", "first_applied_neural_output",
        "first_physical_qpos_divergence", "first_lm_tarsus5_force_divergence",
        "first_exact_contact_state_divergence", "first_sensory_feedback_divergence",
        "first_subsequent_cns_divergence", "first_subsequent_mapped_motor_divergence")},
      "enabled_condition_summary": None, "disabled_condition_summary": None,
      "mapped_tibia_motor_activity": None, "decoded_outputs": None, "applied_outputs": None,
      "per_leg_physical_divergence": None, "full_body_physical_divergence": None,
      "contact_force_feedback": None, "tactile_feedback_divergence": None,
      "downstream_cns_feedback_divergence": None, "subsequent_mapped_motor_divergence": None,
      "causal_classification": "NOT_RUN", "physics_stability": {"stable": None,
        "failure": None, "retry_or_retuning_permitted": False},
      "limitations": ["This is an engineering motor-causality protocol, not a gait, behavior, or reflex experiment.",
        "Tactile transduction and motor decoding are modeled interfaces, not measured biological transfer functions.",
        "Passive or mechanically coupled non-tibia movement is not direct neural actuation.",
        "No scientific result was generated in this environment."]}
