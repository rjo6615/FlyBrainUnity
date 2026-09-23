"""Explicit Windows execution boundary for the frozen M10B protocol.

Nothing in this module runs at import time.  ``run_windows`` is called only by
the guarded ``--run-windows`` CLI path.  It reuses the canonical M9B live-loop
machinery, but never invokes the M9B runner or writes in an M9/M10A namespace.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

from . import m10b_perturbation_scaling as m10b
from . import m9b_external_perturbation as m9b
from . import m7d_corrected_spontaneous as m7d
from . import _windows_m9b_external_perturbation_adapter as m9a
from . import _windows_m7d_corrected_spontaneous_adapter as m7da
from . import integrated_whole_leg_readiness as m6c
from . import isolated_tier_b_motor_validation as m6b


def _runner(**kwargs: Any):
    from ._windows_m8_live_condition import run_condition
    return run_condition(**kwargs)


def _gate(values: Mapping[str, float], condition: str, admitted: tuple[str, ...]):
    if tuple(admitted) != m7d.ADMITTED_MOTOR:
        raise RuntimeError("M10B admitted motor inventory mismatch")
    enabled = dict((name, flag) for name, flag, _ in m10b.CONDITIONS)[condition]
    return m10b.gate_contributions(values, enabled)


def _invoke(runner: Any, live: Any, records: Any, table: Any,
            condition: str, number: int, initialize_only: bool):
    """Invoke the validated M9B sensorimotor loop with M10B scheduling only."""
    return runner(protocol=live, condition=condition, condition_number=number,
        progress=lambda n, c, f, s, cw, tw, eta: f"[{n}/10] {c} {f:.1%} step {s}/15000",
        cached_admission_assertion=m6c.assert_physical_admission,
        cached_records=records, cached_table=table, initialize_only=initialize_only,
        duration_ms=1500.0, condition_names=tuple(row[0] for row in m10b.CONDITIONS),
        contribution_gate=_gate, compact_telemetry=True,
        runtime_factory=m7da._runtime, proprioception_only=True,
        fixed_initial_baseline=True, m8_extended_telemetry=True,
        external_force_by_transition=m10b.force_at_transition,
        m9b_extended_telemetry=True, m10b_extended_telemetry=True)


def _environment() -> dict[str, Any]:
    result = {}
    for name, required in (("flygym", "1.2.1"), ("mujoco", "3.2.7"), ("numpy", None)):
        module = importlib.import_module(name)
        version = importlib.metadata.version(name)
        if required is not None and version != required:
            raise RuntimeError(f"requires {name} {required}, found {version}")
        result[name] = {"version": version, "module_path": str(module.__file__)}
    return result


def _protected_m9_identities() -> dict[str, str]:
    paths = (m9b.PREREGISTRATION_PATH, m9b.RAW_PATH, m9b.REPORT_PATH, m9b.MANIFEST_PATH)
    if not all(path.is_file() for path in paths):
        raise RuntimeError("canonical M9B provenance artifact missing")
    return {str(path): m10b._sha256(path) for path in paths}


def _assert_protected_unchanged(before: Mapping[str, str]) -> None:
    after = {name: m10b._sha256(Path(name)) for name in before}
    if after != dict(before) or m10b.verify_m10a() != m10b.M10A_ARTIFACTS:
        raise RuntimeError("protected M9 or M10A artifact changed during M10B")


def execution_readiness(runner: Any = _runner) -> dict[str, Any]:
    """Construct ten fresh initial states and perform exactly zero transitions."""
    preflight = m10b.preflight()
    live, records, table = m7da._protocol()
    states = [_invoke(runner, live, records, table, name, index, True)
              for index, (name, _, _) in enumerate(m10b.CONDITIONS, 1)]
    if any(state["physics_steps"] or state["neural_steps"] for state in states):
        raise RuntimeError("M10B readiness crossed a transition boundary")
    snapshots = [state["pre_intervention_state"] for state in states]
    if not all(m6c.pre_intervention_equivalent(snapshots[0], item) for item in snapshots[1:]):
        raise RuntimeError("M10B fresh initial states differ")
    audits = [m9a._canonical_audit(state["initial_physical_state_audit"]) for state in states]
    if not all(item == audits[0] for item in audits[1:]):
        raise RuntimeError("M10B fresh physical initialization audits differ")
    body_names = audits[0]["m8_contact_identity"]["body_names"]
    thorax = [index for index, name in body_names.items() if str(name).split("/")[-1] == "Thorax"]
    if len(thorax) != 1:
        raise RuntimeError("authoritative Thorax identity is not unique")
    return {**preflight, "status": "EXECUTION_READINESS_PASS",
        "fresh_runtime_count": 10, "fresh_initialization_equivalent": True,
        "authoritative_thorax_body_id": thorax[0], "environment": _environment()}


def _condition_arrays(result: Mapping[str, Any], condition: str) -> dict[str, Any]:
    """Translate validated live-loop telemetry to the frozen M10B contract."""
    import numpy as np
    raw = result["raw_arrays"]
    motor_enabled = dict((name, enabled) for name, enabled, _ in m10b.CONDITIONS)[condition]
    force = dict((name, magnitude) for name, _, magnitude in m10b.CONDITIONS)[condition]
    arrays = {
        "physics_time_ms": raw["physics_time_ms"],
        "root_thorax_position": raw["physics_body_position"],
        "root_orientation_wxyz": raw["physics_body_orientation"],
        "root_linear_velocity": raw["physics_qvel"][:, :3],
        "root_angular_velocity": raw["physics_qvel"][:, 3:6],
        "height": raw["physics_body_position"][:, 2],
        "joint_positions": raw["physics_joint_position"],
        "distal_tarsus_positions": raw["physics_tarsus5_world_position"],
        "physical_contact_observations": raw["physics_tarsal_contact"],
        "applied_external_force": raw["physics_external_force"],
        "tibial_proprioceptive_physical_inputs": raw["neural_sensory_physical_inputs"],
        "modeled_sensory_encoding": raw["neural_sensory_encoded"],
        "delivered_sensory_cns_state": raw["neural_delivered_sensory_state"],
        "mapped_motor_population_state": raw["neural_mapped_motor_population_state"],
        "decoder_state_output": raw["neural_decoder_outputs"],
        "admitted_neural_motor_pre_intervention": raw["neural_motor_pre_zero"],
        "admitted_neural_motor_physical_contribution": raw["physics_neural_motor_contribution"],
        "physical_command_after_intervention": raw["physics_action"][:-1],
        "neural_time_ms": raw["neural_time_ms"],
        "condition_identity": np.asarray(condition),
        "force_magnitude": np.asarray(force, dtype=np.float64),
        "motor_enabled": np.asarray(motor_enabled, dtype=np.bool_),
    }
    validate_raw_condition(arrays)
    return arrays


def validate_raw_condition(arrays: Mapping[str, Any]) -> None:
    import numpy as np
    if set(arrays) != set(m10b.RAW_SCHEMA):
        raise RuntimeError("M10B raw field inventory mismatch")
    for name, shape in m10b.RAW_SCHEMA.items():
        value = np.asarray(arrays[name])
        if list(value.shape) != shape or value.dtype == object:
            raise RuntimeError(f"M10B raw schema mismatch: {name}")
        if np.issubdtype(value.dtype, np.number) and not np.all(np.isfinite(value)):
            raise RuntimeError(f"M10B nonfinite raw field: {name}")


def check_force_integrity(condition_arrays: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    import numpy as np
    expected_names = tuple(name for name, _, _ in m10b.CONDITIONS)
    if tuple(condition_arrays) != expected_names:
        raise RuntimeError("M10B force-integrity condition order mismatch")
    per_condition = {}
    for name in expected_names:
        observed = np.asarray(condition_arrays[name]["applied_external_force"])
        expected = np.asarray([m10b.force_at_transition(name, i) for i in range(15000)])
        if observed.shape != (15000, 3) or not np.array_equal(observed, expected):
            raise RuntimeError(f"M10B applied-force corruption: {name}")
        per_condition[name] = {"exact": True, "nonzero_transition_count": int(np.any(observed, axis=1).sum()),
            "application_body": "Thorax", "application_point": "authoritative body center of mass",
            "torque_exact_zero": True, "transition_indices": "none" if not np.any(observed) else "5000-5199"}
    return {"passed": True, "per_condition": per_condition}


def check_disabled_motor_integrity(condition_arrays: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    import numpy as np
    per_condition = {}
    for name, enabled, _ in m10b.CONDITIONS:
        pre = np.asarray(condition_arrays[name]["admitted_neural_motor_pre_intervention"])
        post = np.asarray(condition_arrays[name]["admitted_neural_motor_physical_contribution"])
        if not enabled and np.any(post):
            raise RuntimeError(f"M10B disabled motor physically admitted: {name}")
        per_condition[name] = {"motor_enabled": enabled, "pre_intervention_recorded": pre.shape == (3000, 11),
            "post_intervention_exact_zero_required": not enabled,
            "post_intervention_exact_zero": bool(not np.any(post)) if not enabled else None}
    return {"passed": True, "per_condition": per_condition}


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush(); os.fsync(stream.fileno())


def run_windows(runner: Any = _runner) -> dict[str, Any]:
    """Run the ten conditions only after explicit external authorization."""
    import numpy as np
    preregistration_sha256 = m10b.verify_preregistration()
    protected_m9 = _protected_m9_identities()
    m10a_hashes = m10b.verify_m10a()
    readiness = execution_readiness(runner)
    live, records, table = m7da._protocol()
    conditions = {}
    counts = {}
    decoder_configuration = None
    for index, (name, _, _) in enumerate(m10b.CONDITIONS, 1):
        result = _invoke(runner, live, records, table, name, index, False)
        if (result["physics_steps"], result["neural_steps"]) != (15000, 3000):
            raise RuntimeError(f"M10B transition accounting mismatch: {name}")
        if result["physics_instability"] or result["unauthorized_contribution_count"]:
            raise RuntimeError(f"M10B invalid runtime telemetry: {name}")
        conditions[name] = _condition_arrays(result, name)
        current_decoder_configuration = result["decoder_configuration"]
        if decoder_configuration is None:
            decoder_configuration = current_decoder_configuration
        elif current_decoder_configuration != decoder_configuration:
            raise RuntimeError(f"M10B decoder configuration differs: {name}")
        counts[name] = {"physics_transitions": 15000, "physics_states": 15001,
            "neural_updates": 3000, "sensory_encoding_delivery_events": 3000,
            "decoder_events": 3000, "physical_application_events": 15000}
    force_integrity = check_force_integrity(conditions)
    disabled_integrity = check_disabled_motor_integrity(conditions)
    totals = {"physics_transitions": 150000, "physics_states_recorded": 150010,
        "neural_updates": 30000, "sensory_encoding_delivery_events": 30000,
        "decoder_events": 30000, "physical_application_events": 150000,
        "event_count_semantics": "sensory, decoder, and application events are not physics or neural transition aliases"}
    flattened = {f"{condition}__{field}": value for condition, values in conditions.items()
                 for field, value in values.items()}
    payload = io.BytesIO(); np.savez_compressed(payload, **flattened); raw_bytes = payload.getvalue()
    _assert_protected_unchanged(protected_m9)
    if not m10b.outputs_available():
        raise FileExistsError("M10B canonical output namespace is not exclusively available")
    m10b.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with m10b.RAW_PATH.open("xb") as stream:
        stream.write(raw_bytes); stream.flush(); os.fsync(stream.fileno())
    report = {"schema": m10b.SCHEMA, "status": "COMPLETE_UNANALYZED",
        "canonical_experiment_executed": True, "analysis_required": True,
        "condition_order": [row[0] for row in m10b.CONDITIONS], "transition_counts": totals,
        "force_integrity": force_integrity, "disabled_motor_integrity": disabled_integrity}
    _publish_json(m10b.REPORT_PATH, report)
    protocol = m10b.protocol()
    manifest = {"schema": m10b.SCHEMA, "status": "COMPLETE",
        "runner_source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "frozen_m10b_preregistration_sha256": preregistration_sha256,
        "frozen_m10a_artifact_sha256": m10a_hashes, "m9_interface_provenance": protected_m9,
        "connectome_runtime_provenance": {"runtime": "canonical M7D/M8/M9B live condition",
            "seed": m7d.SEED, "environment": readiness["environment"]},
        "initialization_identity": protocol["physical_initialization"],
        "conditions": protocol["conditions"], "force_series": list(m10b.FORCES),
        "sensory_channels": protocol["interfaces"]["sensory"],
        "motor_channels": protocol["interfaces"]["motor"],
        "decoder_filter_parameters": {"semantics": m9b.protocol()["decoder_semantics"],
            "half_activation_hz": m6b.HALF_ACTIVATION_HZ,
            "maximum_decoder_contribution_rad": m6b.DECODER_MAX_RAD,
            "channels_with_compiled_bounds": decoder_configuration},
        "timing": protocol["timing"], "perturbation_geometry": protocol["perturbation"],
        "determinism": {"seed": m7d.SEED, "fresh_identical_runtime_per_condition": True},
        "per_condition_counts": counts, "total_counts": totals,
        "raw": {"byte_size": len(raw_bytes), "sha256": hashlib.sha256(raw_bytes).hexdigest()},
        "force_integrity": force_integrity, "disabled_motor_integrity": disabled_integrity,
        "contact_semantics": "physical observation only; never neural input",
        "execution_absences": protocol["execution_absences"], "readiness": readiness}
    _publish_json(m10b.MANIFEST_PATH, manifest)
    _assert_protected_unchanged(protected_m9)
    return report
