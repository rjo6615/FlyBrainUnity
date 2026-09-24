"""Explicit canonical M11B execution boundary.

This module has no import-time side effects.  It reuses the validated M10B
live-condition invocation and telemetry translation while replacing only its
force selector and final admitted-motor contribution gate.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
from typing import Any, Callable, Mapping

from . import m11_motor_channel_dissection as m11
from . import _windows_m10b_perturbation_scaling_adapter as m10runner
from . import _windows_m7d_corrected_spontaneous_adapter as m7runner
from . import m7d_corrected_spontaneous as m7d
from . import integrated_whole_leg_readiness as m6c

RAW_FIELDS = (
    "physics_time_ms", "root_thorax_position", "root_orientation_wxyz",
    "root_linear_velocity", "root_angular_velocity", "height",
    "joint_positions", "distal_tarsus_positions", "physical_contact_observations",
    "applied_external_force", "tibial_proprioceptive_physical_inputs",
    "modeled_sensory_encoding", "delivered_sensory_cns_state",
    "mapped_motor_population_state", "decoder_state_output",
    "admitted_neural_motor_pre_intervention",
    "admitted_neural_motor_physical_contribution", "physical_command_after_intervention",
    "neural_time_ms", "condition_identity", "ablated_channel_mask",
    "initialization_identity_sha256",
)

INITIALIZATION_IDENTITY_CANONICALIZATION = {
    "type": "PRE-EXECUTION implementation correction",
    "reason": "independently constructed runtimes add nonphysical per-runtime slash namespace prefixes to compiled MuJoCo body names",
    "scope": "initialization-audit comparison and initialization identity hash only",
    "field": "m8_contact_identity.body_names values",
    "rule": "exact terminal component of slash-namespaced compiled MuJoCo identities",
    "preserves": "body IDs, semantic body identities, contact IDs, identity method, and all physical state",
    "scientific_conditions_executed_before_correction": 0,
    "physics_transitions_before_correction": 0,
    "neural_transitions_before_correction": 0,
    "scientific_design_changed": False,
}


def _condition_ablations(condition: str) -> tuple[str, ...]:
    try:
        return dict(m11.CONDITIONS)[condition]
    except KeyError as exc:
        raise ValueError("unknown M11 condition") from exc


def contribution_gate(values: Mapping[str, float], condition: str,
                      admitted: tuple[str, ...]) -> dict[str, float]:
    """The sole intervention: after decode, immediately before application."""
    if tuple(admitted) != tuple(row[0] for row in m11.MOTOR_CHANNELS):
        raise RuntimeError("M11 admitted motor inventory mismatch")
    return m11.intervene(values, _condition_ablations(condition))


def _force(condition: str, transition: int) -> tuple[float, float, float]:
    _condition_ablations(condition)
    return m11.force_at_transition(transition)


def invoke(runner: Any, live: Any, records: Any, table: Any, condition: str,
           number: int, initialize_only: bool) -> Mapping[str, Any]:
    """Reuse M10B's validated M9 live loop with M11's boundary gate."""
    return runner(protocol=live, condition=condition, condition_number=number,
        progress=lambda n, c, f, s, cw, tw, eta: f"[{n}/13] {c} {f:.1%} step {s}/15000",
        cached_admission_assertion=m6c.assert_physical_admission,
        cached_records=records, cached_table=table, initialize_only=initialize_only,
        duration_ms=1500.0, condition_names=tuple(row[0] for row in m11.CONDITIONS),
        contribution_gate=contribution_gate, compact_telemetry=True,
        runtime_factory=m7runner._runtime, proprioception_only=True,
        fixed_initial_baseline=True, m8_extended_telemetry=True,
        external_force_by_transition=_force, m9b_extended_telemetry=True,
        m10b_extended_telemetry=True)


def _canonical_initialization_audit(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Remove only per-runtime slash namespaces from compiled body names.

    The copy is used solely as an audit identity.  Runtime/model data and every
    other audit field remain untouched and therefore subject to exact equality.
    """
    canonical = copy.deepcopy(dict(audit))
    if "m8_contact_identity" not in canonical:
        return canonical
    contact = canonical["m8_contact_identity"]
    if not isinstance(contact, dict):
        raise TypeError("m8_contact_identity must be a mapping")
    if "body_names" not in contact:
        return canonical
    body_names = contact["body_names"]
    if not isinstance(body_names, dict):
        raise TypeError("m8_contact_identity.body_names must be a mapping")
    contact["body_names"] = {
        body_id: str(name).rsplit("/", 1)[-1]
        for body_id, name in body_names.items()
    }
    return canonical


def _serialized_audit(audit: Mapping[str, Any]) -> str:
    """Return the deterministic, exact JSON identity used by M11 readiness."""
    return json.dumps(audit, sort_keys=True, separators=(",", ":"), default=str)


def readiness(runner: Any) -> dict[str, Any]:
    """Construct 13 fresh states, check identity, and cross zero transitions."""
    live, records, table = m7runner._protocol()
    states = [invoke(runner, live, records, table, name, i, True)
              for i, (name, _) in enumerate(m11.CONDITIONS, 1)]
    if len(states) != 13:
        raise RuntimeError("M11 readiness requires exactly 13 fresh runtimes")
    if any(x["physics_steps"] or x["neural_steps"] for x in states):
        raise RuntimeError("M11 readiness crossed a transition boundary")
    snapshots = [x["pre_intervention_state"] for x in states]
    if not all(m6c.pre_intervention_equivalent(snapshots[0], x) for x in snapshots[1:]):
        raise RuntimeError("M11 fresh initial states differ")
    audits = [_serialized_audit(_canonical_initialization_audit(
        x["initial_physical_state_audit"])) for x in states]
    if len(set(audits)) != 1:
        raise RuntimeError("M11 physical initialization audits differ")
    return {"fresh_runtime_count": 13, "fresh_initialization_equivalent": True,
            "initialization_identity_sha256": hashlib.sha256(audits[0].encode()).hexdigest(),
            "initialization_identity_canonicalization": INITIALIZATION_IDENTITY_CANONICALIZATION,
            "physics_transitions": 0, "neural_transitions": 0}


def _diagnostic_value(value: Any) -> Any:
    """Return a JSON-renderable representation without altering comparisons."""
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError):
        return str(value)


def _audit_category(key: str, baseline: Any, comparison: Any) -> str:
    """Mechanically label a difference; the label has no audit semantics."""
    lowered = key.lower()
    if any(token in lowered for token in ("condition", "runtime", "identity", "name")):
        return "condition_or_runtime_metadata"

    def numeric(value: Any) -> bool:
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float, complex)):
            return True
        if isinstance(value, (list, tuple)):
            return bool(value) and all(numeric(item) for item in value)
        try:
            import numpy as np
            array = np.asarray(value)
            return array.size > 0 and np.issubdtype(array.dtype, np.number)
        except (ImportError, TypeError, ValueError):
            return False

    if numeric(baseline) and numeric(comparison):
        return "numeric_physical_state_value"
    return "other"


def diagnose_initialization(runner: Any = m10runner._runner,
                              emit: Callable[[str], None] = print) -> dict[str, Any]:
    """Expose exact initialize-only audit differences without running conditions."""
    live, records, table = m7runner._protocol()
    states = []
    total = len(m11.CONDITIONS)
    for index, (name, _) in enumerate(m11.CONDITIONS, 1):
        emit(f"[{index}/{total}] constructing {name}")
        state = invoke(runner, live, records, table, name, index, True)
        physics = int(state["physics_steps"])
        neural = int(state["neural_steps"])
        emit(f"[{index}/{total}] complete: physics={physics} neural={neural}")
        if physics or neural:
            raise RuntimeError(
                f"M11 initialization diagnostic crossed a transition boundary: {name} "
                f"physics={physics} neural={neural}")
        states.append(state)

    baseline_snapshot = states[0]["pre_intervention_state"]
    baseline_audit = states[0]["initial_physical_state_audit"]
    baseline_canonical_audit = _canonical_initialization_audit(baseline_audit)
    all_keys = sorted({key for state in states
                       for key in state["initial_physical_state_audit"]})
    condition_reports = []
    for index, ((name, _), state) in enumerate(zip(m11.CONDITIONS, states)):
        audit = state["initial_physical_state_audit"]
        canonical_audit = _canonical_initialization_audit(audit)
        differences = []
        for key in all_keys:
            baseline_present = key in baseline_audit
            comparison_present = key in audit
            baseline_value = baseline_audit.get(key)
            comparison_value = audit.get(key)
            equal = (baseline_present == comparison_present and
                     json.dumps(baseline_value, sort_keys=True, separators=(",", ":"), default=str)
                     == json.dumps(comparison_value, sort_keys=True, separators=(",", ":"), default=str))
            if not equal:
                differences.append({
                    "field": key,
                    "baseline_present": baseline_present,
                    "comparison_present": comparison_present,
                    "baseline_value": _diagnostic_value(baseline_value),
                    "comparison_value": _diagnostic_value(comparison_value),
                    "category": _audit_category(key, baseline_value, comparison_value),
                })
        condition_reports.append({
            "condition": name,
            "physics_steps": int(state["physics_steps"]),
            "neural_steps": int(state["neural_steps"]),
            "pre_intervention_equivalent_to_condition_1": (
                True if index == 0 else
                bool(m6c.pre_intervention_equivalent(baseline_snapshot,
                                                     state["pre_intervention_state"]))),
            "differing_audit_fields": differences,
            "canonical_audit_equivalent_to_condition_1": (
                _serialized_audit(canonical_audit)
                == _serialized_audit(baseline_canonical_audit)),
            "raw_differences_disappear_under_canonical_audit_identity": (
                bool(differences) and _serialized_audit(canonical_audit)
                == _serialized_audit(baseline_canonical_audit)),
        })
    return {
        "mode": "INITIALIZATION_DIAGNOSTIC",
        "scientific_conditions_executed": 0,
        "physics_transitions": 0,
        "neural_transitions": 0,
        "baseline_condition": m11.CONDITIONS[0][0],
        "initial_physical_state_audit_keys": all_keys,
        "initialization_identity_canonicalization": INITIALIZATION_IDENTITY_CANONICALIZATION,
        "conditions": condition_reports,
        "canonical_outputs_published": False,
    }


def condition_arrays(result: Mapping[str, Any], condition: str,
                     initialization_identity: str) -> dict[str, Any]:
    import numpy as np
    raw = result["raw_arrays"]
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
        "ablated_channel_mask": np.asarray([n in _condition_ablations(condition)
                                             for n, _, _ in m11.MOTOR_CHANNELS]),
        "initialization_identity_sha256": np.asarray(initialization_identity),
    }
    validate_raw(arrays, condition)
    return arrays


def validate_raw(arrays: Mapping[str, Any], condition: str) -> None:
    import numpy as np
    if tuple(arrays) != RAW_FIELDS:
        raise RuntimeError("M11 raw field inventory mismatch")
    pre = np.asarray(arrays["admitted_neural_motor_pre_intervention"])
    post = np.asarray(arrays["admitted_neural_motor_physical_contribution"])
    force = np.asarray(arrays["applied_external_force"])
    if pre.shape != (3000, 11) or post.shape != (15000, 11) or force.shape != (15000, 3):
        raise RuntimeError("M11 intervention audit shape mismatch")
    expected_force = np.asarray([m11.force_at_transition(i) for i in range(15000)])
    if not np.array_equal(force, expected_force):
        raise RuntimeError(f"M11 force integrity mismatch: {condition}")
    mask = np.asarray(arrays["ablated_channel_mask"], bool)
    if np.any(post[:, mask]) or not np.array_equal(mask, [n in _condition_ablations(condition)
                                                          for n, _, _ in m11.MOTOR_CHANNELS]):
        raise RuntimeError(f"M11 intervention integrity mismatch: {condition}")
    for name, value in arrays.items():
        value = np.asarray(value)
        if value.dtype == object or (np.issubdtype(value.dtype, np.number)
                                     and not np.all(np.isfinite(value))):
            raise RuntimeError(f"M11 invalid raw field: {name}")


def build_report(conditions: Mapping[str, Mapping[str, Any]], counts: Mapping[str, Any],
                 initialization: Mapping[str, Any]) -> dict[str, Any]:
    """Build deterministic preregistered reductions from complete raw trajectories."""
    import numpy as np
    # Late import keeps module import, --help, and preflight independent of the
    # numerical analysis stack, just as the physics runtime is late-bound.
    from . import m10c_m10b_analysis as m10c
    deviations: dict[str, Any] = {}
    for condition, arrays in conditions.items():
        times = np.asarray(arrays["physics_time_ms"])
        # The common force-onset state is the deterministic matched baseline.
        origin = 5000
        series = {
            "thorax_com_deviation_mm": m10c.euclidean_deviation(
                arrays["root_thorax_position"],
                np.broadcast_to(arrays["root_thorax_position"][origin], (15001, 3))),
            "root_orientation_shortest_arc_deg": m10c.quaternion_shortest_arc_deg(
                arrays["root_orientation_wxyz"],
                np.broadcast_to(arrays["root_orientation_wxyz"][origin], (15001, 4))),
        }
        deviations[condition] = {metric: {window: float(np.max(values[m10c.window_mask(times, rule)]))
            for window, rule in m11.WINDOWS.items()} for metric, values in series.items()}
    full = deviations["full_11_enabled"]
    estimands = {}
    for channel, _, _ in m11.MOTOR_CHANNELS:
        condition = f"leave_one_out__{channel}"
        estimands[channel] = {metric: {
            "effect": m11.ablation_effect(deviations[condition][metric]["later_post_force"],
                                          full[metric]["later_post_force"]),
        } for metric in m11.THRESHOLDS}
        for metric, row in estimands[channel].items():
            row["classification"] = m11.classify(row["effect"], m11.THRESHOLDS[metric])
    return {"schema": m11.SCHEMA, "status": "COMPLETE", "preregistration": {
        "sha256": m11.PREREGISTRATION_SHA256, "byte_size": m11.PREREGISTRATION_BYTE_SIZE},
        "upstream_artifacts": m11.UPSTREAM_ARTIFACTS,
        "condition_order": [x[0] for x in m11.CONDITIONS],
        "motor_inventory": m11.protocol()["motor_channels"], "perturbation": m11.PERTURBATION,
        "timing": m11.TIMING, "transition_counts": counts, "initialization": initialization,
        "metric_definitions": {"thorax_com_deviation_mm": "Euclidean Thorax/root COM displacement in mm",
            "root_orientation_shortest_arc_deg": "quaternion shortest-arc orientation displacement in degrees"},
        "windows": m11.WINDOWS, "thresholds": m11.THRESHOLDS,
        "per_condition_deviations": deviations, "later_post_force_estimands": estimands,
        "interpretation_boundaries": {"boundary_557_ms": "inherited engineering boundary; not biological latency",
            "contact": "observational only; not neural sensory input",
            "scope": "No inference about biological balance, righting, reflexes, recovery, natural locomotion, natural gait, or biological motor function is licensed."}}


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def publish_transaction(output_dir: Path, raw_bytes: bytes, report: Mapping[str, Any],
                        manifest_base: Mapping[str, Any]) -> dict[str, Any]:
    """Validate in staging and publish all names, rolling back any partial move."""
    if not m11.outputs_available(output_dir):
        raise FileExistsError("M11 future output namespace is occupied; overwrite forbidden")
    output_dir.mkdir(parents=True, exist_ok=True)
    staging = output_dir / f".m11b-tmp-{os.getpid()}"
    staging.mkdir(exist_ok=False)
    published: list[Path] = []
    try:
        (staging / m11.FUTURE_OUTPUTS["raw"]).write_bytes(raw_bytes)
        report_bytes = _json_bytes(report)
        (staging / m11.FUTURE_OUTPUTS["report"]).write_bytes(report_bytes)
        manifest = {**manifest_base, "outputs": {
            m11.FUTURE_OUTPUTS["raw"]: {"byte_size": len(raw_bytes),
                "sha256": hashlib.sha256(raw_bytes).hexdigest()},
            m11.FUTURE_OUTPUTS["report"]: {"byte_size": len(report_bytes),
                "sha256": hashlib.sha256(report_bytes).hexdigest()}}}
        manifest_bytes = _json_bytes(manifest)
        (staging / m11.FUTURE_OUTPUTS["manifest"]).write_bytes(manifest_bytes)
        # Re-read and validate every staged byte before canonical names exist.
        json.loads((staging / m11.FUTURE_OUTPUTS["report"]).read_text())
        json.loads((staging / m11.FUTURE_OUTPUTS["manifest"]).read_text())
        for key in ("raw", "report", "manifest"):
            destination = output_dir / m11.FUTURE_OUTPUTS[key]
            os.replace(staging / m11.FUTURE_OUTPUTS[key], destination)
            published.append(destination)
        staging.rmdir()
        return manifest
    except BaseException:
        for path in published:
            path.unlink(missing_ok=True)
        shutil.rmtree(staging, ignore_errors=True)
        raise


def execute_canonical(runner: Any = m10runner._runner) -> dict[str, Any]:
    """Execute exactly 13 conditions; callable only from the explicit CLI."""
    preflight = m11.preflight()  # all fail-closed checks precede construction
    protected = m11.verify_upstream()
    import importlib.metadata
    import numpy as np
    ready = readiness(runner)
    live, records, table = m7runner._protocol()
    conditions, per_condition = {}, {}
    for index, (name, _) in enumerate(m11.CONDITIONS, 1):
        result = invoke(runner, live, records, table, name, index, False)
        actual = (int(result["physics_steps"]), int(result["neural_steps"]))
        if actual != (15000, 3000):
            raise RuntimeError(f"M11 transition accounting mismatch: {name}")
        conditions[name] = condition_arrays(result, name, ready["initialization_identity_sha256"])
        per_condition[name] = {"physics_transitions": actual[0], "neural_transitions": actual[1]}
    totals = {"physics_transitions": sum(x["physics_transitions"] for x in per_condition.values()),
              "neural_transitions": sum(x["neural_transitions"] for x in per_condition.values())}
    if totals != {"physics_transitions": m11.TOTAL_PHYSICS_TRANSITIONS,
                  "neural_transitions": m11.TOTAL_NEURAL_TRANSITIONS}:
        raise RuntimeError("M11 aggregate transition accounting mismatch")
    counts = {"per_condition": per_condition, "aggregate": totals}
    report = build_report(conditions, counts, ready)
    flattened = {f"{condition}__{field}": value for condition, arrays in conditions.items()
                 for field, value in arrays.items()}
    payload = io.BytesIO(); np.savez_compressed(payload, **flattened)
    if m11.verify_upstream() != protected:
        raise RuntimeError("M11 protected M10B/M10C inputs changed")
    manifest = {"schema": m11.SCHEMA, "status": "COMPLETE", "completion_status": "COMPLETE",
        "preregistration": {"sha256": m11.PREREGISTRATION_SHA256,
                            "byte_size": m11.PREREGISTRATION_BYTE_SIZE},
        "source_code": {Path(__file__).name: {"sha256": m11._sha256(Path(__file__)),
                                               "byte_size": Path(__file__).stat().st_size},
                        Path(m11.__file__).name: {"sha256": m11._sha256(Path(m11.__file__)),
                                                 "byte_size": Path(m11.__file__).stat().st_size}},
        "upstream_artifacts": protected, "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "runtime_versions": {name: importlib.metadata.version(name) for name in ("flygym", "mujoco")},
        "determinism": ready, "output_filenames": list(m11.FUTURE_OUTPUTS.values()),
        "transition_counts": counts, "condition_count": len(m11.CONDITIONS)}
    publish_transaction(m11.OUTPUT_DIR, payload.getvalue(), report, manifest)
    if m11.verify_upstream() != protected:
        raise RuntimeError("M11 protected M10B/M10C inputs changed after publication")
    return report
