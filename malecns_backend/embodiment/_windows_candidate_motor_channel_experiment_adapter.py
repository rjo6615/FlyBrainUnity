"""Explicit Windows execution boundary for the three-candidate experiment."""
from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import candidate_motor_channel_experiment as experiment
from . import _windows_m7d_corrected_spontaneous_adapter as m7runner
from . import _windows_m8_live_condition as kernel


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _source_identity(path: Path) -> dict[str, Any]:
    return {"sha256": experiment.sha256_file(path), "byte_size": path.stat().st_size}


def _environment_manifest() -> dict[str, Any]:
    import numpy as np
    versions = {}
    for distribution in ("mujoco", "flygym"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    sources = [Path(experiment.__file__), Path(__file__), Path(kernel.__file__),
               Path(m7runner.__file__), Path(__file__).with_name("motor.py"),
               Path(__file__).with_name("tactile_motor_matched_control.py")]
    return {"schema": "THREE-CANDIDATE-EXECUTION-MANIFEST.1", "status": "STARTED",
        "preregistration_path": str(experiment.PREREGISTRATION_PATH.relative_to(experiment.ROOT)),
        "preregistration_sha256": experiment.PREREGISTRATION_SHA256,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=experiment.ROOT,
                                               text=True).strip(),
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "mujoco_version": versions["mujoco"], "flygym_version": versions["flygym"],
        "source_hashes": {str(path.relative_to(experiment.ROOT)): _source_identity(path) for path in sources},
        "seed": experiment.SEED,
        "timestep_configuration": {"duration_ms": experiment.DURATION_MS,
            "physics_dt_ms": experiment.PHYSICS_DT_MS, "neural_dt_ms": experiment.NEURAL_DT_MS,
            "physics_to_neural_transition_ratio": 5},
        "candidates": [{"joint": name, "action_index": index, "coordinate_sign": sign}
                       for name, index, sign in experiment.CANDIDATES],
        "start_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "machine": {"platform": platform.platform(), "system": platform.system(),
                    "release": platform.release(), "machine": platform.machine(),
                    "processor": platform.processor()}}


def contribution_gate(values: Mapping[str, float], condition: str,
                      admitted: tuple[str, ...]) -> dict[str, float]:
    """Leave decoding intact; experimental zeroing occurs after safety processing."""
    if condition not in experiment.CONDITIONS or tuple(values) != tuple(admitted) or len(admitted) != 1:
        raise RuntimeError("candidate decoder inventory or condition mismatch")
    return {admitted[0]: float(values[admitted[0]])}


def final_gate(name: str, action_index: int, contribution: float, condition: str) -> float:
    expected = {candidate: index for candidate, index, _ in experiment.CANDIDATES}
    if expected.get(name) != action_index:
        raise RuntimeError("candidate identity mismatch at final motor boundary")
    return experiment.authorize_contribution(action_index, contribution, condition)[2]


def admission_assertion(selected_index: int):
    def validate(vector: Any, _table: Any) -> None:
        values = tuple(float(value) for value in vector)
        if len(values) != 42:
            raise RuntimeError("physical neural contribution vector is not length 42")
        nonzero = tuple(index for index, value in enumerate(values) if value != 0.0)
        if nonzero not in ((), (selected_index,)):
            raise RuntimeError("unauthorized neural contribution occurred")
        if any(values[index] != 0.0 for index in experiment.CURRENT_11_INDICES):
            raise RuntimeError("current admitted 11-channel contribution occurred")
    return validate


def _invoke(runner: Any, protocol: Mapping[str, Any], records: Any, table: Any,
            candidate: str, action_index: int, condition: str, number: int) -> Mapping[str, Any]:
    return runner(protocol=protocol, condition=condition, condition_number=number,
        progress=lambda n, c, f, s, cw, tw, eta: f"[{n}/6] {candidate} {c} {f:.1%} step {s}/10000",
        cached_admission_assertion=admission_assertion(action_index), cached_records=records,
        cached_table=table, initialize_only=False, duration_ms=experiment.DURATION_MS,
        condition_names=experiment.CONDITIONS, contribution_gate=contribution_gate,
        compact_telemetry=True, runtime_factory=m7runner._runtime, proprioception_only=True,
        fixed_initial_baseline=True, m8_extended_telemetry=True,
        motor_channel_names=(candidate,), detailed_motor_telemetry=True,
        final_contribution_gate=final_gate, isolated_candidate_telemetry=True)


def _diagnostic_invoke(runner: Any, protocol: Mapping[str, Any], records: Any,
                       table: Any, condition: str, number: int) -> Mapping[str, Any]:
    """Construct the authoritative runtime and return before any transition."""
    candidate, action_index, _ = experiment.CANDIDATES[0]
    return runner(protocol=protocol, condition=condition, condition_number=number,
        progress=lambda *_: "identity diagnostic", cached_admission_assertion=admission_assertion(action_index),
        cached_records=records, cached_table=table, initialize_only=True,
        duration_ms=experiment.DURATION_MS, condition_names=experiment.CONDITIONS,
        contribution_gate=contribution_gate, compact_telemetry=True,
        runtime_factory=m7runner._runtime, proprioception_only=True,
        fixed_initial_baseline=True, m8_extended_telemetry=True,
        motor_channel_names=(candidate,), detailed_motor_telemetry=True,
        final_contribution_gate=final_gate, isolated_candidate_telemetry=True,
        identity_diagnostics=True)


def diagnose_identity(runner: Any = kernel.run_condition) -> dict[str, Any]:
    """Compare four RF Femur constructions without commands, steps, or output."""
    preregistration = experiment.verify_preregistration()
    protocol, records, table = m7runner._protocol()
    labels = (("A1", "ENABLED"), ("A2", "ENABLED"),
              ("B1", "ZEROED"), ("B2", "ZEROED"))
    snapshots = {}
    counters = {}
    for number, (label, condition) in enumerate(labels, 1):
        result = _diagnostic_invoke(runner, copy.deepcopy(protocol), records, table,
                                    condition, number)
        counters[label] = {name: result[name] for name in (
            "physics_steps", "neural_steps", "sensory_updates", "decoder_updates",
            "motor_interventions")}
        if any(counters[label].values()):
            raise RuntimeError("identity diagnostic performed a scientific operation")
        snapshots[label] = result["physics_model_diagnostic_snapshot"]
    matrix = {left: {right: experiment.compare_physics_model_snapshots(
        snapshots[left], snapshots[right]) for right, _ in labels} for left, _ in labels}
    return {"schema": "THREE-CANDIDATE-IDENTITY-DIAGNOSTIC.1",
        "status": "NON_SCIENTIFIC_DIAGNOSTIC_ONLY", "candidate": "joint_RFFemur",
        "frozen_preregistration_sha256": preregistration,
        "canonical_experiment_result_written": False, "candidate_commands_applied": 0,
        "scientific_transitions": 0, "construction_counters": counters,
        "component_identity_matrix": matrix,
        "classification_performed": False}


def _initialization(result: Mapping[str, Any]) -> dict[str, Any]:
    state, audit = result["pre_intervention_state"], result["initial_physical_state_audit"]
    return {"initial_qpos": state["qpos"], "initial_qvel": state["qvel"],
        "initial_ctrl": state["ctrl"], "malecns_state_digest": state["malecns_state"],
        "sensory_state": {"encoders": state["sensory_encoder_state"], "rng": state["rng_state"]},
        "decoder_state": state["decoder_state"], "seed": experiment.SEED,
        "physics_model_identity": audit["physics_model_identity"],
        "timestep_configuration": {"physics_dt_ms": experiment.PHYSICS_DT_MS,
                                   "neural_dt_ms": experiment.NEURAL_DT_MS,
                                   "physics_to_neural_transition_ratio": 5}}


def _condition_arrays(result: Mapping[str, Any], candidate: str,
                      action_index: int, condition: str) -> dict[str, Any]:
    import numpy as np
    raw = result["raw_arrays"]
    details = raw["detailed_motor_telemetry"]
    configuration = result["decoder_configuration"][0]
    legacy = np.asarray(raw["neural_admitted_contributions"], dtype=np.float64)
    if legacy.shape != (2000, 11) or np.any(legacy):
        raise RuntimeError("historical 11-channel telemetry contract changed")
    before_vectors = np.asarray([row["neural_contribution_vector_before_intervention"]
                                 for row in details], dtype=np.float64)
    after_vectors = np.asarray([row["neural_contribution_vector_after_intervention"]
                                for row in details], dtype=np.float64)
    if before_vectors.shape != (2000, 42) or after_vectors.shape != (2000, 42):
        raise RuntimeError("candidate neural vector telemetry shape mismatch")
    other_indices = [index for index in range(42) if index != action_index]
    if np.any(before_vectors[:, other_indices]) or np.any(after_vectors[:, other_indices]):
        raise RuntimeError("non-selected candidate contribution in neural telemetry")
    if condition == "ZEROED" and np.any(after_vectors):
        raise RuntimeError("ZEROED candidate survived final intervention boundary")
    vectors = np.asarray(raw["physics_neural_contribution_vector"], dtype=np.float64)
    if vectors.shape != (10001, 42):
        raise RuntimeError("candidate physical vector telemetry shape mismatch")
    permitted = np.zeros_like(vectors, dtype=bool); permitted[:, action_index] = True
    if np.any(vectors[~permitted]) or (condition == "ZEROED" and np.any(vectors)):
        raise RuntimeError("unauthorized physical contribution in raw telemetry")
    field = lambda name, dtype=np.float64: np.asarray([row[name] for row in details], dtype=dtype)
    arrays = {key: value for key, value in raw.items() if key != "detailed_motor_telemetry"}
    interface = json.loads((experiment.ROOT / "malecns_backend" / "interface_map.json").read_text())
    from .candidate_motor_channel_validation import POOLS
    populations = {row["name"]: row for row in interface["populations"]}
    positive_dense = {int(index) for name in POOLS[candidate]["positive"]
                      for index in populations[name]["dense_indices"]}
    negative_dense = {int(index) for name in POOLS[candidate]["negative"]
                      for index in populations[name]["dense_indices"]}
    dense_to_body = {int(dense): int(body) for population in interface["populations"]
                     for dense, body in zip(population["dense_indices"], population["body_ids"])}
    dense_indices = [int(value) for value in details[0]["dense_indices"]]
    arrays.update({
        "candidate_dense_indices": np.asarray(dense_indices, dtype=np.int64),
        "candidate_body_root_ids": np.asarray([dense_to_body[index] for index in dense_indices], dtype=np.int64),
        "candidate_positive_pool_membership": np.asarray([index in positive_dense for index in dense_indices]),
        "candidate_negative_pool_membership": np.asarray([index in negative_dense for index in dense_indices]),
        "candidate_cumulative_spike_counts": field("cumulative_spike_counts", np.uint64),
        "candidate_spike_increments": field("spike_increments", np.uint64),
        "candidate_per_neuron_filtered_rates_hz": field("per_neuron_filtered_rates_hz"),
        "candidate_positive_directional_mean_hz": field("positive_directional_mean_hz"),
        "candidate_negative_directional_mean_hz": field("negative_directional_mean_hz"),
        "candidate_raw_antagonist_signal": field("raw_antagonist_signal"),
        "candidate_signed_signal": field("signed_signal_after_coordinate_sign"),
        "candidate_processed_decoder_state": field("processed_decoder_state"),
        "candidate_slew_limited_contribution": field("slew_limited_contribution"),
        "candidate_range_limited_contribution": field("range_limited_contribution"),
        "candidate_contribution_before_intervention": field("candidate_contribution_before_intervention"),
        "candidate_contribution_after_intervention": field("candidate_contribution_after_intervention"),
        "candidate_neural_contribution_vector_before_intervention": field(
            "neural_contribution_vector_before_intervention"),
        "candidate_neural_contribution_vector_after_intervention": field(
            "neural_contribution_vector_after_intervention"),
        "candidate_authorized_indices": field("authorized_indices", np.int64),
        # Fixed-width exact index telemetry: -1 means the nonzero set is empty.
        "candidate_nonzero_index_after_intervention": np.asarray([
            row["nonzero_indices"][0] if row["nonzero_indices"] else -1
            for row in details], dtype=np.int64),
        "candidate_nonzero_mask": vectors != 0.0,
        "selected_joint_qpos": np.asarray(raw["physics_qpos"])[:, configuration["qpos_index"]],
        "selected_joint_qvel": np.asarray(raw["physics_qvel"])[:, configuration["qvel_index"]],
        "selected_physical_command": np.asarray(raw["physics_action"])[:, action_index],
        "candidate_action_index": np.asarray(action_index), "candidate_joint": np.asarray(candidate),
        "condition": np.asarray(condition)})
    if any(np.asarray(value).dtype == object for value in arrays.values()):
        raise RuntimeError("object dtype is forbidden in raw numerical artifact")
    return arrays


def _metrics(arrays: Mapping[str, Any]) -> dict[str, Any]:
    import numpy as np
    rates = np.asarray(arrays["candidate_per_neuron_filtered_rates_hz"])
    increments = np.asarray(arrays["candidate_spike_increments"])
    before = np.asarray(arrays["candidate_contribution_before_intervention"])
    positive = np.asarray(arrays["candidate_positive_directional_mean_hz"])
    negative = np.asarray(arrays["candidate_negative_directional_mean_hz"])
    antagonist = np.asarray(arrays["candidate_raw_antagonist_signal"])
    nonzero = int(np.count_nonzero(before))
    metrics = {"underlying_candidate_neurons_fired": bool(np.any(increments)),
        "total_spike_increments": int(np.sum(increments)),
        "peak_filtered_rate_hz": float(np.max(rates, initial=0.0)),
        "mean_per_neuron_filtered_rate_hz": float(np.mean(rates)) if rates.size else 0.0,
        "positive_directional_mean_hz": {"peak": float(np.max(positive, initial=0.0)),
                                            "mean": float(np.mean(positive))},
        "negative_directional_mean_hz": {"peak": float(np.max(negative, initial=0.0)),
                                            "mean": float(np.mean(negative))},
        "positive_peak_hz": float(np.max(positive, initial=0.0)),
        "negative_peak_hz": float(np.max(negative, initial=0.0)),
        "peak_absolute_raw_antagonist_signal": float(np.max(np.abs(antagonist), initial=0.0)),
        "peak_absolute_contribution": float(np.max(np.abs(before), initial=0.0)),
        "nonzero_contribution_transition_count": nonzero,
        "nonzero_contribution_transition_fraction": nonzero / 2000,
        "unauthorized_neural_contribution_occurred": bool(np.any(
            np.asarray(arrays["physics_neural_contribution_vector"])[:,
                       [i for i in range(42) if i != int(arrays["candidate_action_index"])]]))}
    metrics["classification"] = experiment.classify(metrics)
    return metrics


def _comparison(enabled: Mapping[str, Any], zeroed: Mapping[str, Any]) -> dict[str, Any]:
    import numpy as np
    difference = lambda field: np.asarray(enabled[field]) - np.asarray(zeroed[field])
    qpos = difference("selected_joint_qpos"); qvel = difference("selected_joint_qvel")
    root = difference("physics_body_position"); quat = difference("physics_body_orientation")
    return {"selected_joint_qpos_difference": qpos.tolist(),
        "selected_joint_qpos_peak_absolute_divergence": float(np.max(np.abs(qpos), initial=0.0)),
        "selected_joint_qvel_difference": qvel.tolist(),
        "selected_joint_qvel_peak_absolute_divergence": float(np.max(np.abs(qvel), initial=0.0)),
        "root_position_difference_xyz": root.tolist(),
        "root_position_peak_euclidean_divergence": float(np.max(np.linalg.norm(root, axis=1), initial=0.0)),
        "root_quaternion_component_difference_wxyz": quat.tolist(),
        "root_quaternion_peak_component_divergence": float(np.max(np.abs(quat), initial=0.0))}


def execute(runner: Any = kernel.run_condition) -> dict[str, Any]:
    """Execute exactly six fresh conditions and transactionally retain evidence."""
    preflight = experiment.preflight()
    output = Path(preflight["output_directory"])
    output.mkdir(parents=True, exist_ok=False)
    start_hash = experiment.sha256_file(experiment.PREREGISTRATION_PATH)
    manifest = {**_environment_manifest(), "attempt": preflight["attempt"],
        "prior_attempts": preflight["prior_attempts"]}
    (output / experiment.OUTPUTS[0]).write_bytes(_json_bytes(manifest))
    protocol, records, table = m7runner._protocol()
    all_arrays, report_candidates = {}, {}
    condition_number = 0
    for candidate, action_index, sign in experiment.CANDIDATES:
        results, arrays = {}, {}
        for condition in experiment.CONDITIONS:
            condition_number += 1
            result = _invoke(runner, copy.deepcopy(protocol), records, table, candidate,
                             action_index, condition, condition_number)
            if (result["physics_steps"], result["neural_steps"]) != (10000, 2000):
                raise RuntimeError("exact 1000-ms transition count not obtained")
            results[condition] = result
            arrays[condition] = _condition_arrays(result, candidate, action_index, condition)
            all_arrays.update({f"{candidate}__{condition}__{key}": value
                               for key, value in arrays[condition].items()})
        identities = {condition: _initialization(results[condition]) for condition in experiment.CONDITIONS}
        experiment.require_matched_initialization(identities["ENABLED"], identities["ZEROED"])
        report_candidates[candidate] = {"action_index": action_index, "coordinate_sign": sign,
            "initialization": identities, "matched_initialization": True,
            "conditions": {condition: _metrics(arrays[condition]) for condition in experiment.CONDITIONS},
            "enabled_vs_zeroed": _comparison(arrays["ENABLED"], arrays["ZEROED"])}
    import numpy as np
    payload = io.BytesIO(); np.savez_compressed(payload, **all_arrays)
    raw_path = output / experiment.OUTPUTS[1]; raw_path.write_bytes(payload.getvalue())
    report = {"schema": "THREE-CANDIDATE-MOTOR-CHANNEL-EXPERIMENT.1", "status": "COMPLETE",
        "preregistration_sha256": start_hash, "duration_ms": experiment.DURATION_MS,
        "seed": experiment.SEED, "candidates": report_candidates,
        "interpretation_boundary": "Quantitative modeled-channel observation only; no claim of walking, gait, balance, stabilization, righting, reflex, or natural motor function."}
    report_path = output / experiment.OUTPUTS[2]; report_path.write_bytes(_json_bytes(report))
    if experiment.verify_preregistration() != start_hash:
        raise RuntimeError("preregistration changed during execution")
    final = {**manifest, "status": "COMPLETE", "completion_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "transition_counts": {"conditions": 6, "physics_per_condition": 10000,
                              "neural_per_condition": 2000, "physics_total": 60000,
                              "neural_total": 12000},
        "preregistration_remained_unchanged": True,
        "output_hashes": {path.name: _source_identity(path) for path in (output / experiment.OUTPUTS[0], raw_path, report_path)}}
    final_path = output / experiment.OUTPUTS[3]; final_path.write_bytes(_json_bytes(final))
    return report
