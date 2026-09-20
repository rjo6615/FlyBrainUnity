"""Fail-closed, read-only analysis of the completed M7 telemetry archive.

This module deliberately imports no simulation, neural, sensory, or decoder
runtime.  It treats the NPZ as immutable evidence and only performs numerical
reductions over recorded arrays.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

from .m7_spontaneous_locomotion import CONDITIONS, THRESHOLDS

SCHEMA = "M7-POSTRUN-ANALYSIS.1"
CANONICAL_SHA256 = "155ef633a319711d44fc471c1f46c24cec0b36ea6e7326556c5b987e912fed47"
CHANNELS = (
    ("joint_LFTibia", "LF", "Tibia", "A", 5),
    ("joint_LMTibia", "LM", "Tibia", "A", 12),
    ("joint_LHTibia", "LH", "Tibia", "A", 19),
    ("joint_RFTibia", "RF", "Tibia", "A", 26),
    ("joint_RMTibia", "RM", "Tibia", "A", 33),
    ("joint_RHTibia", "RH", "Tibia", "A", 40),
    ("joint_LFFemur", "LF", "Femur", "B", 3),
    ("joint_LMFemur", "LM", "Femur", "B", 10),
    ("joint_LHFemur", "LH", "Femur", "B", 17),
    ("joint_RMFemur", "RM", "Femur", "B", 31),
    ("joint_RHFemur", "RH", "Femur", "B", 38),
)
PHYSICS_FIELDS = {
    "physics_time_ms", "physics_qpos", "physics_qvel", "physics_joint_position",
    "physics_action", "physics_ctrl", "physics_body_position",
    "physics_body_orientation", "physics_contact_forces", "physics_finite",
}
NEURAL_FIELDS = {
    "neural_time_ms", "neural_sensory_encoded", "neural_delivered_drive_count",
    "neural_aggregate_spikes", "neural_observer_outputs", "neural_decoder_outputs",
    "neural_admitted_contributions",
}
PHYSICS_SAMPLE_COUNT = 50_001
NEURAL_SAMPLE_COUNT = 10_000
PHYSICS_DT_MS = 0.1
NEURAL_DT_MS = 0.5


class EvidenceError(RuntimeError):
    """Canonical evidence differs from the frozen contract."""


def _accumulation_tolerance(expected: np.ndarray, dt_ms: float) -> np.ndarray:
    """Return a per-sample bound for a clock formed by repeated float64 adds.

    IEEE-754 round-to-nearest introduces at most half an ULP at each addition.
    Summing that bound through each timestamp models accumulated runtime-clock
    error.  One further ULP covers rounding in the vectorized ``i * dt``
    reference calculation.  This is deliberately scale- and length-dependent,
    rather than a fitted absolute tolerance for the canonical archive.
    """
    addition_ulp = np.spacing(np.maximum(np.abs(expected), abs(dt_ms)))
    return 0.5 * np.cumsum(addition_ulp) + np.spacing(np.maximum(np.abs(expected), abs(dt_ms)))


def _validate_time_vector(time: np.ndarray, *, sample_count: int, dt_ms: float,
                          first_step: int, label: str,
                          accumulated_tol: np.ndarray | None = None) -> np.ndarray:
    """Validate the count, representation, origin, endpoint, and cadence."""
    if time.dtype != np.dtype("float64"):
        raise EvidenceError(f"{label} time dtype mismatch")
    if time.shape != (sample_count,):
        raise EvidenceError(f"{label} time sample-count mismatch")
    if not np.all(np.isfinite(time)):
        raise EvidenceError(f"{label} time contains NaN/Inf")
    if not np.all(np.diff(time) > 0):
        raise EvidenceError(f"{label} time is not strictly increasing")

    # Physics records the initial state (first_step=0); neural telemetry is
    # post-update and therefore starts after the first 0.5-ms update (step=1).
    steps = np.arange(first_step, first_step + sample_count, dtype=np.float64)
    expected = steps * dt_ms
    if accumulated_tol is None:
        accumulated_tol = _accumulation_tolerance(expected, dt_ms)
    elif accumulated_tol.shape != time.shape:
        raise EvidenceError(f"{label} accumulated-tolerance shape mismatch")
    if abs(time[0] - expected[0]) > accumulated_tol[0]:
        raise EvidenceError(f"{label} time origin mismatch")
    if abs(time[-1] - expected[-1]) > accumulated_tol[-1]:
        raise EvidenceError(f"{label} time endpoint mismatch")
    if np.any(np.abs(time - expected) > accumulated_tol):
        raise EvidenceError(f"{label} accumulated time mismatch")

    # A subtraction can expose the rounding errors of both adjacent clock
    # values.  Two ULPs at their magnitude, plus one ULP of dt, bounds that
    # representation effect while remaining many orders below a real dt shift.
    adjacent_scale = np.maximum(np.abs(time[:-1]), np.abs(time[1:]))
    cadence_tol = 2 * np.spacing(np.maximum(adjacent_scale, abs(dt_ms))) + np.spacing(dt_ms)
    if np.any(np.abs(np.diff(time) - dt_ms) > cadence_tol):
        raise EvidenceError(f"{label} cadence mismatch")
    return accumulated_tol


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{path} is not a JSON object")
    return value


def validate_evidence(raw: Path, manifest_path: Path, summary_path: Path,
                      *, expected_sha256: str = CANONICAL_SHA256,
                      canonical: bool = True) -> tuple[dict[str, np.ndarray], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load with pickle disabled and validate every byte/schema invariant."""
    if not raw.is_file():
        raise EvidenceError(f"raw evidence does not exist: {raw}")
    raw_sha = _sha(raw)
    if raw_sha != expected_sha256:
        raise EvidenceError(f"raw SHA256 mismatch: expected {expected_sha256}, observed {raw_sha}")
    manifest, summary = _json(manifest_path), _json(summary_path)
    if manifest.get("raw_sha256") != raw_sha:
        raise EvidenceError("manifest raw SHA256 mismatch")
    if canonical and manifest.get("raw_byte_size") != raw.stat().st_size:
        raise EvidenceError("manifest raw byte-size mismatch")
    expected_conditions = list(CONDITIONS)
    if (manifest.get("schema") != "M7-MANIFEST.1" or manifest.get("seed") != 1 or
            manifest.get("duration_ms") != 5000 or manifest.get("conditions") != expected_conditions):
        raise EvidenceError("manifest protocol metadata mismatch")
    if (summary.get("schema") != "M7-RESULT.1" or summary.get("run_status") != "COMPLETE" or
            summary.get("seed") != 1 or summary.get("duration_ms") != 5000 or
            summary.get("conditions") != expected_conditions or summary.get("walking") is not None):
        raise EvidenceError("summary protocol metadata mismatch")
    if canonical and (summary.get("physics_transitions_per_condition") != 50_000 or
                      summary.get("neural_updates_per_condition") != 10_000):
        raise EvidenceError("summary sample-count metadata mismatch")
    declared = manifest.get("arrays")
    if not isinstance(declared, dict):
        raise EvidenceError("manifest array inventory missing")
    required = {f"{condition}__{field}" for condition in CONDITIONS
                for field in PHYSICS_FIELDS | NEURAL_FIELDS}
    if set(declared) != required:
        raise EvidenceError("manifest array inventory mismatch")
    try:
        archive = np.load(raw, allow_pickle=False)
        if set(archive.files) != required:
            raise EvidenceError("NPZ array inventory mismatch")
        arrays = {name: archive[name] for name in archive.files}
        archive.close()
    except (OSError, ValueError, TypeError) as exc:
        raise EvidenceError(f"NPZ cannot be loaded safely: {exc}") from exc
    for name, array in arrays.items():
        spec = declared[name]
        if array.dtype.hasobject:
            raise EvidenceError(f"object array forbidden: {name}")
        if list(array.shape) != spec.get("shape"):
            raise EvidenceError(f"shape mismatch: {name}")
        if str(array.dtype) != spec.get("dtype"):
            raise EvidenceError(f"dtype mismatch: {name}")
        if canonical:
            field = name.split("__", 1)[1]
            leading = 50_001 if field in PHYSICS_FIELDS else 10_000
            tails = {"physics_time_ms": (), "physics_qpos": (94,), "physics_qvel": (93,),
                "physics_joint_position": (42,), "physics_action": (42,), "physics_ctrl": (48,),
                "physics_body_position": (3,), "physics_body_orientation": (4,),
                "physics_contact_forces": (36,3), "physics_finite": (), "neural_time_ms": (),
                "neural_sensory_encoded": (6,), "neural_delivered_drive_count": (),
                "neural_aggregate_spikes": (), "neural_observer_outputs": (11,),
                "neural_decoder_outputs": (11,), "neural_admitted_contributions": (11,)}
            integer = field in ("neural_delivered_drive_count", "neural_aggregate_spikes")
            expected_dtype = "bool" if field == "physics_finite" else ("int64" if integer else "float64")
            if array.shape != (leading, *tails[field]) or str(array.dtype) != expected_dtype:
                raise EvidenceError(f"canonical shape/dtype contract mismatch: {name}")
        if name.endswith("physics_finite"):
            if array.dtype != np.dtype("bool") or not np.all(array):
                raise EvidenceError(f"finite-state flag failed: {name}")
        elif np.issubdtype(array.dtype, np.number) and not np.all(np.isfinite(array)):
            raise EvidenceError(f"nonfinite required telemetry: {name}")
    p_count = PHYSICS_SAMPLE_COUNT if canonical else len(arrays[f"{CONDITIONS[0]}__physics_time_ms"])
    n_count = NEURAL_SAMPLE_COUNT if canonical else len(arrays[f"{CONDITIONS[0]}__neural_time_ms"])
    for condition in CONDITIONS:
        pt = arrays[f"{condition}__physics_time_ms"]
        nt = arrays[f"{condition}__neural_time_ms"]
        physics_tol = _validate_time_vector(
            pt, sample_count=p_count, dt_ms=PHYSICS_DT_MS,
            first_step=0, label=f"{condition} physics")
        neural_stride = int(NEURAL_DT_MS / PHYSICS_DT_MS)
        if neural_stride * PHYSICS_DT_MS != NEURAL_DT_MS:
            raise EvidenceError("neural/physics cadence ratio is not integral")
        sampled_physics = pt[neural_stride::neural_stride]
        if sampled_physics.shape != nt.shape:
            raise EvidenceError(f"{condition} neural/physics sample-count mismatch")
        # The frozen recorder reads MuJoCo's clock once at the start of each
        # loop iteration.  On every fifth post-transition iteration that same
        # scalar is written first to neural telemetry and then to physics
        # telemetry.  It is not an independently accumulated 0.5-ms clock.
        if not np.array_equal(nt, sampled_physics):
            raise EvidenceError(f"{condition} neural clock provenance mismatch")
        _validate_time_vector(nt, sample_count=n_count, dt_ms=NEURAL_DT_MS,
                              first_step=1, label=f"{condition} neural",
                              accumulated_tol=physics_tol[neural_stride::neural_stride])
        for field in PHYSICS_FIELDS:
            if arrays[f"{condition}__{field}"].shape[0] != len(pt):
                raise EvidenceError(f"physics cadence mismatch: {field}")
        for field in NEURAL_FIELDS:
            if arrays[f"{condition}__{field}"].shape[0] != len(nt):
                raise EvidenceError(f"neural cadence mismatch: {field}")
    enabled, disabled = CONDITIONS
    for field in ("physics_time_ms", "neural_time_ms"):
        left = arrays[f"{enabled}__{field}"]
        right = arrays[f"{disabled}__{field}"]
        # Both conditions use the same deterministic frozen clock mechanism;
        # unlike comparison to an ideal decimal sequence, no independently
        # accumulated arithmetic is involved in this pairwise comparison.
        if not np.array_equal(left, right):
            raise EvidenceError(f"cross-condition clock mismatch: {field}")
    validation = {"status": "PASS", "allow_pickle": False, "raw_sha256": raw_sha,
                  "manifest_sha256": _sha(manifest_path), "object_arrays": False,
                  "all_required_values_finite": True, "physics_states_per_condition": len(pt),
                  "neural_samples_per_condition": len(nt), "conditions": expected_conditions,
                  "time_semantics": {
                      "physics": "initial state plus post-transition states; t[i] = i * 0.1 ms",
                      "neural": "post-neural-update states sampled exactly from physics_time_ms[5::5]; t[i] is nominally (i + 1) * 0.5 ms"},
                  "time_tolerance_policy": "physics uses cumulative half-ULP per repeated 0.1-ms float64 addition plus one reference ULP; neural uses the corresponding sampled physics bounds and must exactly equal physics_time_ms[5::5]; cadence is bounded by adjacent-value ULPs",
                  "cross_condition_clock_comparison": "exact float64 sample equality",
                  "cross_condition_clocks_equivalent": True}
    return arrays, manifest, summary, validation


def _first(mask: np.ndarray, time: np.ndarray) -> float | None:
    hits = np.flatnonzero(mask)
    return float(time[hits[0]]) if hits.size else None


def _episodes(active: np.ndarray, dt_ms: float) -> tuple[int, float]:
    active = np.asarray(active, bool)
    starts = active & np.r_[True, ~active[:-1]]
    return int(starts.sum()), float(active.sum() * dt_ms)


def _divergence(name: str, a: np.ndarray, b: np.ndarray, time: np.ndarray,
                threshold: float | None, causal_class: str) -> dict[str, Any]:
    delta = np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float))
    magnitude = delta if delta.ndim == 1 else np.max(delta, axis=tuple(range(1, delta.ndim)))
    scale = np.maximum(np.max(np.abs(a), axis=tuple(range(1, a.ndim))) if a.ndim > 1 else np.abs(a),
                       np.max(np.abs(b), axis=tuple(range(1, b.ndim))) if b.ndim > 1 else np.abs(b))
    tol = np.finfo(float).eps * np.maximum(1.0, scale) * 8
    exact = _first(magnitude != 0, time)
    numerical = _first(magnitude > tol, time)
    threshold_time = _first(magnitude > threshold, time) if threshold is not None else None
    return {"quantity": name, "causal_class": causal_class,
            "first_exact_inequality_ms": exact,
            "first_descriptive_numerical_inequality_ms": numerical,
            "numerical_tolerance_policy": "8 * float64 epsilon * max(1, instantaneous scale)",
            "frozen_threshold": threshold, "first_frozen_threshold_crossing_ms": threshold_time,
            "peak_absolute_divergence": float(magnitude.max()),
            "final_absolute_divergence": float(magnitude[-1])}


def _activation(arrays: Mapping[str, np.ndarray], condition: str) -> dict[str, Any]:
    time = arrays[f"{condition}__neural_time_ms"]
    obs = arrays[f"{condition}__neural_observer_outputs"]
    dec = arrays[f"{condition}__neural_decoder_outputs"]
    adm = arrays[f"{condition}__neural_admitted_contributions"]
    rows = []
    for i, (name, leg, joint, tier, _) in enumerate(CHANNELS):
        active = adm[:, i] != 0
        episodes, duration = _episodes(active, float(np.diff(time).mean()))
        def stats(x: np.ndarray) -> tuple[float | None, float, float]:
            peak = int(np.argmax(np.abs(x)))
            return _first(x != 0, time), float(x[peak]), float(time[peak])
        fo, po, pto = stats(obs[:, i]); fd, pd, ptd = stats(dec[:, i]); fa, pa, pta = stats(adm[:, i])
        rows.append({"interface": name, "leg": leg, "joint": joint, "tier": f"Tier {tier}",
                     "first_nonzero_observer_ms": fo, "first_nonzero_decoder_ms": fd,
                     "first_nonzero_admitted_ms": fa, "peak_observer_hz": po,
                     "peak_observer_time_ms": pto, "peak_decoder_magnitude": pd,
                     "peak_decoder_time_ms": ptd, "peak_admitted_contribution": pa,
                     "peak_admitted_time_ms": pta, "active_duration_ms": duration,
                     "activation_episodes": episodes})
    recruitment = sorted((r["first_nonzero_admitted_ms"], r["interface"], r["leg"])
                         for r in rows if r["first_nonzero_admitted_ms"] is not None)
    overlap = np.sum(adm != 0, axis=1)
    return {"condition": condition, "channels": rows,
            "first_active_channel": recruitment[0][1] if recruitment else None,
            "first_active_leg": recruitment[0][2] if recruitment else None,
            "recruitment_order": [x[1] for x in recruitment],
            "silent_channels": [r["interface"] for r in rows if r["first_nonzero_admitted_ms"] is None],
            "maximum_simultaneously_active_channels": int(overlap.max()),
            "samples_with_simultaneous_channels": int(np.count_nonzero(overlap > 1))}


def _joint_metrics(signal: np.ndarray, time: np.ndarray) -> dict[str, Any]:
    dt = float(np.diff(time).mean()) / 1000.0
    velocity = np.diff(signal) / dt
    centered = signal - signal.mean()
    spectrum = np.abs(np.fft.rfft(centered))
    frequency = np.fft.rfftfreq(len(signal), dt)
    spectrum[0] = 0
    peak = int(np.argmax(spectrum))
    extrema = np.diff(np.sign(np.diff(signal))) != 0
    return {"initial_angle": float(signal[0]), "final_angle": float(signal[-1]),
            "minimum": float(signal.min()), "maximum": float(signal.max()),
            "range_of_motion": float(np.ptp(signal)),
            "total_variation": float(np.abs(np.diff(signal)).sum()),
            "angular_velocity_mean": float(velocity.mean()),
            "angular_velocity_std": float(velocity.std()),
            "angular_velocity_peak_abs": float(np.abs(velocity).max()),
            "extrema_count": int(extrema.sum()),
            "dominant_frequency_hz_descriptive": float(frequency[peak]) if spectrum[peak] > 0 else None,
            "dominant_frequency_amplitude": float(spectrum[peak] / len(signal))}


def _fall(arrays: Mapping[str, np.ndarray], condition: str) -> dict[str, Any]:
    time = arrays[f"{condition}__physics_time_ms"]
    pos = arrays[f"{condition}__physics_body_position"]
    quat = arrays[f"{condition}__physics_body_orientation"]
    up_z = 1 - 2 * (quat[:, 1] ** 2 + quat[:, 2] ** 2)
    fall_mask = pos[:, 2] < THRESHOLDS["fall_height_fraction"] * pos[0, 2]
    rollover_mask = up_z <= THRESHOLDS["rollover_body_up_z_max"]
    def event(mask: np.ndarray) -> dict[str, Any]:
        hit = np.flatnonzero(mask)
        if not hit.size: return {"time_ms": None}
        i = int(hit[0]); before = max(0, i - 1)
        return {"time_ms": float(time[i]), "sample_index": i,
                "body_position_immediately_before": pos[before].tolist(),
                "body_orientation_immediately_before": quat[before].tolist()}
    fall, roll = event(fall_mask), event(rollover_mask)
    event_times = [x["time_ms"] for x in (fall, roll) if x["time_ms"] is not None]
    cutoff = min(event_times) if event_times else float(time[-1])
    ni = np.searchsorted(arrays[f"{condition}__neural_time_ms"], cutoff, side="left")
    pi = np.searchsorted(time, cutoff, side="left")
    admitted = arrays[f"{condition}__neural_admitted_contributions"][:ni]
    joints = arrays[f"{condition}__physics_joint_position"][:, [c[4] for c in CHANNELS]]
    return {"condition": condition, "fall": fall, "rollover": roll,
            "usable_pre_event_duration_ms": float(cutoff),
            "neural_motor_activity_preceded_first_event": bool(np.any(admitted != 0)),
            "joint_total_variation_in_final_10ms_before_event":
                np.abs(np.diff(joints[max(0, pi - 100):max(1, pi)], axis=0)).sum(axis=0).tolist()}


def _trajectory(arrays: Mapping[str, np.ndarray], condition: str) -> dict[str, Any]:
    time = arrays[f"{condition}__physics_time_ms"]
    pos = arrays[f"{condition}__physics_body_position"]
    quat = arrays[f"{condition}__physics_body_orientation"]
    dt = np.diff(time) / 1000
    step = np.linalg.norm(np.diff(pos, axis=0), axis=1)
    speed = step / dt
    dots = np.clip(np.abs(np.sum(quat[1:] * quat[:-1], axis=1)), 0, 1)
    orientation_step = 2 * np.arccos(dots)
    return {"condition": condition, "initial_xyz": pos[0].tolist(), "final_xyz": pos[-1].tolist(),
            "net_displacement_xyz": (pos[-1] - pos[0]).tolist(),
            "net_displacement_m": float(np.linalg.norm(pos[-1] - pos[0])),
            "path_length_m": float(step.sum()), "mean_speed_m_s": float(speed.mean()),
            "peak_speed_m_s": float(speed.max()), "height_min_m": float(pos[:, 2].min()),
            "height_max_m": float(pos[:, 2].max()),
            "cumulative_orientation_change_rad": float(orientation_step.sum())}


def _lag(x: np.ndarray, y: np.ndarray, dt_ms: float, max_lag: int = 200) -> dict[str, Any]:
    x, y = np.asarray(x, float), np.asarray(y, float)
    x, y = x - x.mean(), y - y.mean()
    if not np.any(x) or not np.any(y): return {"lag_ms": None, "correlation": None}
    best = (0.0, 0)
    for lag in range(-min(max_lag, len(x)//4), min(max_lag, len(x)//4) + 1):
        a, b = (x[-lag:], y[:len(y)+lag]) if lag < 0 else (x[:len(x)-lag or None], y[lag:])
        denominator = np.linalg.norm(a) * np.linalg.norm(b)
        corr = float(np.dot(a, b) / denominator) if denominator else 0.0
        if abs(corr) > abs(best[0]): best = (corr, lag)
    return {"lag_ms": float(best[1] * dt_ms), "correlation": best[0]}


def analyze(arrays: Mapping[str, np.ndarray], validation: Mapping[str, Any],
            manifest_sha256: str, code_version: str | None = None) -> dict[str, Any]:
    enabled, control = CONDITIONS
    pt = arrays[f"{enabled}__physics_time_ms"]; nt = arrays[f"{enabled}__neural_time_ms"]
    indices = [c[4] for c in CHANNELS]
    qa, qb = (arrays[f"{x}__physics_body_orientation"] for x in CONDITIONS)
    orientation_angle = 2 * np.arccos(np.clip(np.abs(np.sum(qa * qb, axis=1)), 0, 1))
    divergence = [
        _divergence("admitted_neural_motor_contribution", arrays[f"{enabled}__neural_admitted_contributions"], arrays[f"{control}__neural_admitted_contributions"], nt, None, "intervention_driven"),
        _divergence("commanded_actuator_action", arrays[f"{enabled}__physics_action"], arrays[f"{control}__physics_action"], pt, None, "downstream"),
        _divergence("measured_admitted_joint_position", arrays[f"{enabled}__physics_joint_position"][:, indices], arrays[f"{control}__physics_joint_position"][:, indices], pt, THRESHOLDS["joint_divergence_rad"], "downstream"),
        _divergence("whole_body_qpos", arrays[f"{enabled}__physics_qpos"], arrays[f"{control}__physics_qpos"], pt, None, "downstream"),
        _divergence("body_position", arrays[f"{enabled}__physics_body_position"], arrays[f"{control}__physics_body_position"], pt, THRESHOLDS["com_displacement_m"], "downstream"),
        _divergence("body_orientation_angular_distance_rad", orientation_angle, np.zeros_like(orientation_angle), pt, THRESHOLDS["orientation_divergence_rad"], "downstream"),
        _divergence("validated_sensory_encoding", arrays[f"{enabled}__neural_sensory_encoded"], arrays[f"{control}__neural_sensory_encoded"], nt, None, "feedback_downstream"),
        _divergence("aggregate_cns_spike_trajectory", arrays[f"{enabled}__neural_aggregate_spikes"], arrays[f"{control}__neural_aggregate_spikes"], nt, None, "feedback_downstream"),
    ]
    divergence.sort(key=lambda x: math.inf if x["first_descriptive_numerical_inequality_ms"] is None else x["first_descriptive_numerical_inequality_ms"])
    fall = {c: _fall(arrays, c) for c in CONDITIONS}
    joint = {}
    for condition in CONDITIONS:
        jp = arrays[f"{condition}__physics_joint_position"][:, indices]
        joint[condition] = {CHANNELS[i][0]: _joint_metrics(jp[:, i], pt) for i in range(11)}
    spontaneous_joints = arrays[f"{enabled}__physics_joint_position"][:, indices][::5]
    coord_pairs = []
    for a, b in ((0,3),(1,4),(2,5),(0,1),(1,2),(3,4),(4,5),(0,4),(1,5),(3,1),(4,2)):
        full = _lag(spontaneous_joints[:, a], spontaneous_joints[:, b], 0.5)
        cutoff = fall[enabled]["usable_pre_event_duration_ms"]
        n = max(2, int(cutoff / 0.5))
        pre = _lag(spontaneous_joints[:n, a], spontaneous_joints[:n, b], 0.5)
        coord_pairs.append({"channel_a": CHANNELS[a][0], "channel_b": CHANNELS[b][0],
                            "entire_run": full, "pre_fall_or_rollover": pre})
    stages = [arrays[f"{enabled}__neural_sensory_encoded"].mean(axis=1),
              arrays[f"{enabled}__neural_aggregate_spikes"],
              arrays[f"{enabled}__neural_observer_outputs"].mean(axis=1),
              arrays[f"{enabled}__neural_decoder_outputs"].mean(axis=1),
              arrays[f"{enabled}__neural_admitted_contributions"].mean(axis=1),
              np.linalg.norm(np.diff(arrays[f"{enabled}__physics_body_position"][::5], axis=0), axis=1)]
    names = ["sensory_encoding", "aggregate_cns_spikes", "observer_output", "decoder_output", "admitted_contribution", "body_displacement_rate"]
    sensorimotor = []
    for i in range(len(stages)-1):
        n = min(len(stages[i]), len(stages[i+1]))
        sensorimotor.append({"from": names[i], "to": names[i+1], **_lag(stages[i][:n], stages[i+1][:n], 0.5)})
    return {"schema": SCHEMA, "source_raw_sha256": validation["raw_sha256"],
            "source_manifest_sha256": manifest_sha256, "analysis_code_version": code_version,
            "evidence_validation": dict(validation), "divergence_timeline": divergence,
            "motor_activation_timeline": {c: _activation(arrays, c) for c in CONDITIONS},
            "joint_metrics": joint,
            "coordination_metrics": {"method": "descriptive normalized lag correlation; no fitting",
                "pairwise": coord_pairs, "tripod_gait_classification": None,
                "stable_pattern_conclusion": "No validated gait classification is performed."},
            "fall_rollover_timeline": fall,
            "body_trajectory_metrics": {c: _trajectory(arrays, c) for c in CONDITIONS},
            "sensorimotor_temporal_metrics": {"scope": "within-condition descriptive associations only", "adjacent_stage_lags": sensorimotor},
            "limitations": ["Aggregate telemetry cannot establish neuron-level causal pathways.",
                "Frequency, phase, and lag results are descriptive only.",
                "Fall/rollover restricts interpretable pre-event coordination time.",
                "Recorded joint coordinates are not biological muscle force."],
            "interpretation_guardrails": {"walking": None, "natural_gait_claim": False,
                "biological_locomotion_claim": False, "biological_muscle_force_claim": False,
                "biological_motor_function_claim": False,
                "causal_inference": "Only the enabled neural motor contribution versus matched disabled control intervention supports causal attribution; within-condition lags are associations."}}


def _svg_plot(path: Path, series: Sequence[tuple[str, np.ndarray]], title: str) -> None:
    """Write a dependency-free compact SVG line plot."""
    width, height, margin = 900, 360, 45
    values = np.concatenate([np.asarray(v, float).ravel() for _, v in series])
    lo, hi = float(values.min()), float(values.max())
    if hi == lo: hi = lo + 1
    colors = ("#1565c0", "#c62828", "#2e7d32", "#6a1b9a", "#ef6c00", "#00838f", "#5d4037")
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>', f'<text x="45" y="22" font-family="sans-serif" font-size="16">{title}</text>',
             f'<path d="M{margin},{margin} V{height-margin} H{width-margin}" fill="none" stroke="#555"/>']
    for j, (label, value) in enumerate(series):
        value = np.asarray(value, float).ravel(); step = max(1, len(value)//1500); value = value[::step]
        points = " ".join(f"{margin+i*(width-2*margin)/max(1,len(value)-1):.1f},{height-margin-(x-lo)*(height-2*margin)/(hi-lo):.1f}" for i,x in enumerate(value))
        lines += [f'<polyline points="{points}" fill="none" stroke="{colors[j%len(colors)]}" stroke-width="1"/>',
                  f'<text x="{margin+120*(j%6)}" y="{height-8-14*(j//6)}" fill="{colors[j%len(colors)]}" font-family="sans-serif" font-size="11">{label}</text>']
    lines.append('</svg>')
    path.write_text("\n".join(lines), encoding="utf-8")


def write_plots(arrays: Mapping[str, np.ndarray], directory: Path,
                fall_data: Mapping[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    e, c = CONDITIONS; idx = [x[4] for x in CHANNELS]
    ep, cp = arrays[f"{e}__physics_body_position"], arrays[f"{c}__physics_body_position"]
    _svg_plot(directory/"body_xyz_vs_time.svg", [(f"enabled {a}",ep[:,i]) for i,a in enumerate("XYZ")]+[(f"control {a}",cp[:,i]) for i,a in enumerate("XYZ")], "Recorded body XYZ versus time")
    _svg_plot(directory/"top_down_xy.svg", [("enabled X",ep[:,0]),("enabled Y",ep[:,1]),("control X",cp[:,0]),("control Y",cp[:,1])], "Top-down coordinate traces")
    _svg_plot(directory/"body_height.svg", [("enabled",ep[:,2]),("control",cp[:,2])], "Recorded body height")
    for cond,label in ((e,"enabled"),(c,"control")):
        p=arrays[f"{cond}__physics_body_position"]; speed=np.r_[0,np.linalg.norm(np.diff(p,axis=0),axis=1)/0.0001]
        _svg_plot(directory/f"body_speed_{label}.svg", [(label,speed)], "Recorded body speed")
    _svg_plot(directory/"joint_trajectories.svg", [(CHANNELS[i][0],arrays[f"{e}__physics_joint_position"][:,j]) for i,j in enumerate(idx)], "11 admitted physical joint trajectories")
    _svg_plot(directory/"joint_control_relative_divergence.svg", [(CHANNELS[i][0],arrays[f"{e}__physics_joint_position"][:,j]-arrays[f"{c}__physics_joint_position"][:,j]) for i,j in enumerate(idx)], "Control-relative joint divergence")
    for field,title,file in (("neural_admitted_contributions","Admitted contributions","admitted_contributions.svg"),("neural_observer_outputs","Observer outputs","observer_outputs.svg")):
        _svg_plot(directory/file, [(CHANNELS[i][0],arrays[f"{e}__{field}"][:,i]) for i in range(11)], title)
    _svg_plot(directory/"sensory_channels.svg", [(leg,arrays[f"{e}__neural_sensory_encoded"][:,i]) for i,leg in enumerate(("LF","LM","LH","RF","RM","RH"))], "Six validated sensory channels")
    _svg_plot(directory/"aggregate_cns_spikes.svg", [("enabled",arrays[f"{e}__neural_aggregate_spikes"]),("control",arrays[f"{c}__neural_aggregate_spikes"])], "Aggregate CNS spikes")
    _svg_plot(directory/"activation_raster.svg", [(CHANNELS[i][0],(arrays[f"{e}__neural_admitted_contributions"][:,i]!=0).astype(float)+i) for i in range(11)], "Activation timeline (vertically offset)")
    cutoff=fall_data[e]["usable_pre_event_duration_ms"]; n=max(2,int(cutoff/0.1))
    _svg_plot(directory/"pre_fall_coordination.svg", [(CHANNELS[i][0],arrays[f"{e}__physics_joint_position"][:n,j]) for i,j in enumerate(idx)], "Pre-fall/rollover joint coordination")


def _report(result: Mapping[str, Any]) -> str:
    activation = result["motor_activation_timeline"][CONDITIONS[0]]
    first = result["divergence_timeline"][0]
    lines = ["# M7 canonical post-run analysis", "", "## Evidence", "",
        f"The archive passed fail-closed verification. Raw SHA256: `{result['source_raw_sha256']}`.", "",
        "## What happened and when", "",
        f"The earliest descriptive divergence was **{first['quantity']}** at **{first['first_descriptive_numerical_inequality_ms']} ms**.",
        f"The first admitted active channel was **{activation['first_active_channel']}** on leg **{activation['first_active_leg']}**.", "",
        "## Motor recruitment", "", "Recruitment order: " + ", ".join(activation["recruitment_order"]) + ".", "",
        "## Body trajectory and fall/rollover", ""]
    for c in CONDITIONS:
        t=result["body_trajectory_metrics"][c]; f=result["fall_rollover_timeline"][c]
        lines.append(f"* **{c}:** net displacement {t['net_displacement_m']:.6g} m; path length {t['path_length_m']:.6g} m; fall {f['fall']['time_ms']} ms; rollover {f['rollover']['time_ms']} ms; usable pre-event interval {f['usable_pre_event_duration_ms']} ms.")
    lines += ["", "## Coordination", "", "Lag, phase, frequency, and correlation results are descriptive and are reported separately for the entire run and pre-fall/rollover interval. No validated biological gait classification was performed.", "",
        "## Scientific interpretation", "", "The matched disabled-control intervention permits causal attribution to enabling the recorded admitted neural motor contribution. It does not establish neuron-level pathways. These observations do **not** demonstrate natural walking, natural gait, biological locomotion, biological muscle force, or biological motor function. `walking` remains `null`.", ""]
    return "\n".join(lines)


def _git_version() -> str | None:
    try: return subprocess.run(["git","rev-parse","HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError): return None


def run(raw: Path, manifest: Path, summary: Path, output: Path, report: Path,
        plots: Path, *, expected_sha256: str = CANONICAL_SHA256) -> dict[str, Any]:
    arrays, _, _, validation = validate_evidence(raw, manifest, summary, expected_sha256=expected_sha256)
    result = analyze(arrays, validation, validation["manifest_sha256"], _git_version())
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    output.write_text(payload, encoding="utf-8", newline="\n")
    report.write_text(_report(result), encoding="utf-8", newline="\n")
    write_plots(arrays, plots, result["fall_rollover_timeline"])
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--raw",type=Path,required=True)
    parser.add_argument("--manifest",type=Path); parser.add_argument("--summary",type=Path)
    parser.add_argument("--output",type=Path); parser.add_argument("--report",type=Path); parser.add_argument("--plots",type=Path)
    args=parser.parse_args(argv); base=args.raw.parent
    run(args.raw,args.manifest or base/"m7_manifest.json",args.summary or base/"m7_summary.json",
        args.output or base/"m7_postrun_analysis.json",args.report or base/"M7_POSTRUN_REPORT.md",args.plots or base/"plots")
    print("M7 canonical post-run analysis complete; scientific transitions executed: 0"); return 0


if __name__ == "__main__": raise SystemExit(main())
