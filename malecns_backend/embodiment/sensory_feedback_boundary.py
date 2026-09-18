"""Pure evidence reduction for the M5D-4E sensory-boundary audit.

This module does not alter an encoder or simulation.  It reduces the complete
row traces emitted by the locked M5D-4D condition runner and deliberately
distinguishes active external drive from observationally reconstructed inputs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "M5D-4E.0"
SEED = 1
DURATION_MS = 100.0
NEURAL_DT_MS = 0.5
DEFAULT_TIMESTEP_S = 0.0001
LEG_ORDER = ("LF", "LM", "LH", "RF", "RM", "RH")
ROOT = Path(__file__).resolve().parents[2]
M5D4D_ARTIFACT = ROOT / "malecns_backend/embodiment/interface_output/tactile_motor_closed_loop_100ms.json"
M5D4D_IMPLEMENTATIONS = (
    ROOT / "malecns_backend/embodiment/tactile_motor_closed_loop.py",
    ROOT / "malecns_backend/embodiment/tactile_motor_closed_loop_audit.py",
)
M5D4D_LOCKS = {
    "artifact_raw_sha256": "d684f38cd50edf6f494f00678d33a67c8cd89b50a34fd4815d5af90f05611e09",
    "implementation_lf_sha256": {
        "tactile_motor_closed_loop.py": "8434a6a8e946c2405a1a2271956a9aa88e8f4ba412b0861c55e109b33637d1d6",
        "tactile_motor_closed_loop_audit.py": "450a98112047a4a271d01a29caafff76b960a9bf79b22af68fbc25106cb653c8",
    },
}


def verify_provenance() -> dict[str, Any]:
    """Fail closed on raw artifact bytes, canonical-LF source, and semantics."""
    observed = {
        "artifact_raw_sha256": hashlib.sha256(M5D4D_ARTIFACT.read_bytes()).hexdigest(),
        "implementation_lf_sha256": {p.name: hashlib.sha256(
            p.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()
                                      for p in M5D4D_IMPLEMENTATIONS},
    }
    if observed != M5D4D_LOCKS:
        raise RuntimeError(f"M5D-4D provenance mismatch: {observed!r}")
    document = json.loads(M5D4D_ARTIFACT.read_text(encoding="utf-8"))
    if (document.get("run_status"), document.get("classification")) != (
            "COMPLETE", "MOTOR_CAUSALITY_CONFIRMED_NO_FEEDBACK_WITHIN_WINDOW"):
        raise RuntimeError("M5D-4D semantic provenance mismatch")
    if not document.get("m5d4c_prefix_validation", {}).get("passed"):
        raise RuntimeError("M5D-4D does not contain a validated M5D-4C prefix")
    recorded = document.get("provenance", {})
    if not (recorded.get("verified") and recorded.get("earlier_locks_verified")
            and recorded.get("earlier", {}).get("verified")):
        raise RuntimeError("M5D-4D recorded earlier provenance is not verified")
    # Recheck the immediate M5D-4C raw artifact and canonical-LF implementation
    # rather than merely trusting the booleans embedded in M5D-4D.
    c_artifact = ROOT / "malecns_backend/embodiment/interface_output/tactile_motor_matched_control_preflight.json"
    c_source = ROOT / "malecns_backend/embodiment/tactile_motor_matched_control.py"
    c_observed = (hashlib.sha256(c_artifact.read_bytes()).hexdigest(), hashlib.sha256(
        c_source.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest())
    if c_observed != ("15e83fa88aa3e7a6206ea7bb736cd1ec446874dcf44079e0b79bcbf39c594901",
                      "0d75267b0203d9ad97e69bf9f75d57fdc5057beec682d925176479c00e8a2bc8"):
        raise RuntimeError(f"M5D-4C provenance mismatch: {c_observed!r}")
    return {"verified": True, **observed, "earlier_locks_verified": True}


def active_channel_inventory() -> list[dict[str, Any]]:
    """Inventory external drive in M5D-4D (not every available encoder)."""
    interface = json.loads((ROOT / "malecns_backend/interface_map.json").read_text(encoding="utf-8"))
    pop = next(p for p in interface["populations"] if p["name"] == "tactile T2 left")
    return [{
        "channel_name": "LM_Tarsus5_tactile", "modality": "tactile_contact_onset",
        "biological_population": pop["name"], "mapped_neuron_count": len(pop["dense_indices"]),
        "mapped_dense_indices": pop["dense_indices"],
        "physical_source": "contact_forces[LM Tarsus5]", "physical_source_indices": [11, [0, 1, 2]],
        "sampling_cadence_ms": DEFAULT_TIMESTEP_S * 1000,
        "transduction_function": "norm(force)>threshold; 120 Hz linear 20 ms onset transient",
        "threshold_tuning_parameters": {"engineering_threshold": 1e-12,
            "maximum_modeled_rate_hz": 120.0, "transient_duration_ms": 20.0},
        "stateful_encoder_variables": ["_contact['LM']", "_onset['LM']"],
        "rng_stream": "SeedSequence(1).spawn(6)[LM=1] / PCG64",
        "external_drive_destination": "MaleCNSBrain.set_external_drive via pending LM dense indices",
    }]


def available_but_inactive_proprioception() -> list[dict[str, Any]]:
    audit = json.loads((ROOT / "malecns_backend/embodiment/six_leg_map.json").read_text(encoding="utf-8"))
    result = []
    for leg_record in audit["legs"]:
        joint = next(j for j in leg_record["joints"] if j["actuator"]["anatomical_joint"] == "tibia")
        sensor = joint["sensory"]["populations"][0]; actuator = joint["actuator"]
        result.append({"leg": leg_record["leg"], "population": sensor["name"],
            "mapped_neuron_count": len(sensor["body_ids"]),
            "physical_source": f"measured_positions['{leg_record['leg']}']",
            "observation_action_index": actuator["action_index"],
            "active_external_drive_in_m5d4d": False,
            "reason": "M5D-4D constructs motor observers/decoders only; no SensoryEncoder is constructed or applied"})
    return result


def _first(rows_a, rows_b, value, after=0.0):
    for a, b in zip(rows_a, rows_b):
        if a["time_ms"] >= after and value(a) != value(b):
            return a["time_ms"]
    return None


def _maximum(rows_a, rows_b, value):
    values = [(abs(float(value(a)) - float(value(b))), a["time_ms"]) for a, b in zip(rows_a, rows_b)]
    return {"value": max(values)[0], "time_ms": max(values)[1]} if values else {"value": None, "time_ms": None}


def _maximum_vector(rows_a, rows_b, value):
    values = [(max((abs(float(x) - float(y)) for x, y in zip(value(a), value(b))), default=0.0),
               a["time_ms"]) for a, b in zip(rows_a, rows_b)]
    return {"value": max(values)[0], "time_ms": max(values)[1]} if values else {"value": None, "time_ms": None}


def classify(evidence: Mapping[str, Any]) -> str:
    if not evidence.get("provenance"): return "PROVENANCE_FAILURE"
    if not evidence.get("prefix"): return "PREFIX_REPRODUCTION_FAILURE"
    if not evidence.get("rng_parity"): return "RNG_PARITY_FAILURE"
    if evidence.get("telemetry_blind_spot"): return "M5D4D_TELEMETRY_BLIND_SPOT"
    if evidence.get("delivered") and evidence.get("cns") and evidence.get("motor"): return "FEEDBACK_REACHED_MAPPED_MOTOR"
    if evidence.get("delivered") and evidence.get("cns"): return "FEEDBACK_REACHED_CNS_NOT_MOTOR"
    if evidence.get("delivered"): return "SENSORY_SPIKES_DIVERGED_NO_CNS_EFFECT"
    if evidence.get("rate"): return "ENCODING_DIVERGED_NO_SPIKE_DIVERGENCE"
    if evidence.get("sensor_source"): return "SENSOR_SOURCE_DIVERGED_ENCODER_INSENSITIVE"
    return "NO_SENSOR_RELEVANT_PHYSICAL_DIVERGENCE"


def base_report() -> dict[str, Any]:
    nulls = {name: None for name in ("first_source_physics_divergence_ms", "first_encoder_sample_divergence_ms",
        "first_transduced_rate_divergence_ms", "first_candidate_spike_divergence_ms",
        "first_delivered_spike_divergence_ms", "first_downstream_cns_divergence_ms")}
    return {"schema": SCHEMA, "run_status": "NOT_RUN", "classification": None,
        "reason": "Live FlyGym/MuJoCo execution was not requested or is unavailable",
        "protocol": {"seed": SEED, "duration_ms": DURATION_MS, "physics_timestep_ms": .1,
            "neural_timestep_ms": NEURAL_DT_MS, "automatic_retries": 0, "parameter_mutations": []},
        "runner": {"implementation": "tactile_motor_closed_loop_audit.run_live",
            "exact_m5d4d_runner_reused": True, "instrumentation": "post-run trace reduction only"},
        "provenance": {"verified": False, "expected": M5D4D_LOCKS},
        "prefix_reproduction": {"passed": None, "observed": None},
        "active_sensory_channels": active_channel_inventory(),
        "available_but_inactive_proprioception": available_but_inactive_proprioception(),
        "full_body_physics": {"first_divergence_ms": None},
        "sensor_relevant_physics": {"first_divergence_ms": None},
        "contact_set_audit": {"first_global_divergence_ms": None, "affects_active_source": None},
        "channels": {"LM_Tarsus5_tactile": dict(nulls)},
        "inactive_proprioceptive_observations": {leg: dict(nulls) for leg in LEG_ORDER},
        "rng_accounting": {"aligned_before_input_divergence": None,
            "same_draw_counterfactual_checked": None, "desynchronization": None},
        "telemetry_validation": {"m5d4d_was_correct": None, "blind_spot": None},
        "first_blocked_boundary": None,
        "limitations": ["No result is a claim about a natural biological reflex.",
            "The six tibia proprioceptive mappings are not active sensory channels in the locked M5D-4D runner."],
    }


def analyze(enabled: Sequence[Mapping[str, Any]], disabled: Sequence[Mapping[str, Any]],
            *, _m5d4d_analyze=None) -> dict[str, Any]:
    """Audit complete locked-runner traces without changing their simulation."""
    import numpy as np
    from .sensory import LegSensoryFrame, SensoryEncoder
    from .six_tibia import load_six_tibia_interfaces
    # ``run_live`` supplies the function object captured before it substitutes
    # the runner's reducer. The fallback supports ordinary, unpatched calls.
    # Looking up the runner attribute from inside the substituted call would
    # find this M5D-4E reducer and recurse indefinitely.
    if _m5d4d_analyze is None:
        from .tactile_motor_closed_loop_audit import analyze as _m5d4d_analyze
    provenance = verify_provenance(); original = _m5d4d_analyze(enabled, disabled)
    report = base_report(); report.update(run_status="COMPLETE", reason=None, provenance=provenance)
    report["prefix_reproduction"] = original["m5d4c_prefix_validation"]
    physical = min((original[k]["time_ms"] for k in ("qacc_divergence", "qvel_divergence", "qpos_divergence")
                    if original[k]["observed"]), default=None)
    report["full_body_physics"] = {"first_divergence_ms": physical,
        "first_qacc": original["qacc_divergence"], "first_qvel": original["qvel_divergence"],
        "first_qpos": original["qpos_divergence"],
        "first_contact_force": original["physical_sensory_divergence"]["contact_force"]}
    # The active tactile source is row 11, never the global first-difference row 24.
    vector = lambda r: tuple(r["contact_forces"][11])
    magnitude = lambda r: float(np.linalg.norm(r["contact_forces"][11]))
    source = _first(enabled, disabled, vector, physical or 0.0)
    sample = _first(enabled, disabled, magnitude, physical or 0.0)
    rate = _first(enabled, disabled, lambda r: r["sensory_encoding"]["modeled_rate_hz"], physical or 0.0)
    candidate = _first(enabled, disabled, lambda r: tuple(r["sensory_encoding"]["generated"]), physical or 0.0)
    delivered = _first(enabled, disabled, lambda r: tuple(r["sensory_encoding"]["delivered"]), physical or 0.0)
    cns = (_first(enabled, disabled, lambda r: (r["cns_state"], tuple(r["cns_spikes"])), delivered)
           if delivered is not None else None)
    motor = (_first(enabled, disabled, lambda r: tuple(sorted(r["motor_spikes"].items())), cns)
             if cns is not None else None)
    tactile = report["channels"]["LM_Tarsus5_tactile"]
    tactile.update(first_source_physics_divergence_ms=source, first_encoder_sample_divergence_ms=sample,
        first_transduced_rate_divergence_ms=rate, first_candidate_spike_divergence_ms=candidate,
        first_delivered_spike_divergence_ms=delivered,
        first_downstream_cns_divergence_ms=cns,
        first_subsequent_mapped_motor_divergence_ms=motor,
        source_row=11, global_first_force_row=24,
        global_first_force_is_encoder_source=False,
        maximum_force_magnitude_difference=_maximum(enabled, disabled, magnitude),
        both_contact_before_motor=all(magnitude(r) > 1e-12 for r in (enabled[0], disabled[0])),
        differential_release=False, differential_recontact_or_retrigger=False)
    # If boolean contact ever differs, explicitly expose release/retrigger rather than infer it.
    contacts_a = [magnitude(r) > 1e-12 for r in enabled]; contacts_b = [magnitude(r) > 1e-12 for r in disabled]
    tactile["differential_release"] = any(a != b for a, b in zip(contacts_a, contacts_b))
    tactile["differential_recontact_or_retrigger"] = any(i and contacts_a[i] != contacts_a[i-1] and
        contacts_a[i] != contacts_b[i] or i and contacts_b[i] != contacts_b[i-1] and contacts_a[i] != contacts_b[i]
        for i in range(len(contacts_a)))
    sensor_times = [x for x in (source,) if x is not None]
    report["sensor_relevant_physics"]["first_divergence_ms"] = min(sensor_times, default=None)
    semantic = original["physical_sensory_divergence"]["semantic_contact"]
    report["contact_set_audit"] = {"first_global_divergence_ms": semantic["time_ms"],
        "example": {"enabled": semantic.get("enabled_value"), "disabled": semantic.get("disabled_value")},
        "affects_active_source": "LM_Tarsus5" in (semantic.get("enabled_value"), semantic.get("disabled_value"))}
    # Reconstruct the six validated angle/rate mappings observationally. They did not feed MaleCNS.
    interfaces = load_six_tibia_interfaces()
    for leg in LEG_ORDER:
        angle = lambda r, leg=leg: r["measured_positions"][leg]
        enc = SensoryEncoder(interfaces[leg])
        rates = lambda r, enc=enc, angle=angle: tuple(enc.encode(LegSensoryFrame(r["time_ms"] / 1000, angle(r))).rates_hz)
        item = report["inactive_proprioceptive_observations"][leg]
        item.update(first_source_physics_divergence_ms=_first(enabled, disabled, angle, physical or 0.0),
            first_encoder_sample_divergence_ms=None, first_transduced_rate_divergence_ms=None,
            reconstructed_first_rate_divergence_ms=_first(enabled, disabled, rates, physical or 0.0),
            maximum_absolute_angle_difference=_maximum(enabled, disabled, angle),
            maximum_absolute_reconstructed_rate_difference=_maximum_vector(enabled, disabled, rates))
    rng_equal = _first(enabled, disabled, lambda r: r["rng_state"], 0.0) is None
    report["rng_accounting"] = {"aligned_before_input_divergence": rng_equal,
        "same_draw_counterfactual_checked": rate is None, "desynchronization": not rng_equal}
    blind = rate is not None and not original["modeled_sensory_encoding_divergence"]["observed"]
    report["telemetry_validation"] = {"m5d4d_was_correct": not blind, "blind_spot": blind}
    evidence = {"provenance": True, "prefix": report["prefix_reproduction"]["passed"],
        "rng_parity": rng_equal, "telemetry_blind_spot": blind, "sensor_source": source is not None,
        "rate": rate is not None, "delivered": delivered is not None,
        "cns": cns is not None, "motor": motor is not None}
    report["classification"] = classify(evidence)
    report["first_blocked_boundary"] = ("body physics -> active sensor physical source" if source is None else
        "sensor source -> transduced modeled rate" if rate is None else
        "modeled rate -> candidate sensory spikes" if candidate is None else
        "candidate -> delivered sensory spikes" if delivered is None else "delivered sensory spikes -> MaleCNS")
    return report
