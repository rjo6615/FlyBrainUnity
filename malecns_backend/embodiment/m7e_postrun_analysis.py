"""Deterministic, read-only analysis of immutable M7D telemetry.

This module deliberately imports only the Python standard library and NumPy.
It neither imports nor calls a simulation, neural runtime, or M7/M7D runner.
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

HERE = Path(__file__).resolve().parent
M7D_DIR = HERE / "interface_output" / "m7d_corrected_spontaneous"
RAW_PATH = M7D_DIR / "m7d_raw.npz"
SUMMARY_PATH = M7D_DIR / "m7d_summary.json"
MANIFEST_PATH = M7D_DIR / "m7d_manifest.json"
OUTPUT_DIR = HERE / "interface_output" / "m7e_postrun_analysis"
ANALYSIS_PATH = OUTPUT_DIR / "m7e_analysis.json"
OUTPUT_MANIFEST_PATH = OUTPUT_DIR / "m7e_manifest.json"

SCHEMA = "M7E-POSTRUN-ANALYSIS.1"
CANONICAL_SIZE = 16_737_088
CANONICAL_SHA256 = "92b5c645a88fe74e5d6aa0988478c374e8fde3a0e923d42cc13974a3e60d8444"
CONDITIONS = ("CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT", "CORRECTED_ALL_NEURAL_MOTOR_DISABLED")
PHYSICS_COUNT, NEURAL_COUNT = 5001, 1000
PHYSICS_DT_MS, NEURAL_DT_MS = 0.1, 0.5
PHYSICS_FIELDS = {
    "physics_time_ms": (), "physics_qpos": (94,), "physics_qvel": (93,),
    "physics_joint_position": (42,), "physics_action": (42,), "physics_ctrl": (48,),
    "physics_body_position": (3,), "physics_body_orientation": (4,),
    "physics_contact_forces": (36, 3), "physics_finite": (),
}
NEURAL_FIELDS = {
    "neural_time_ms": (), "neural_sensory_encoded": (6,),
    "neural_delivered_drive_count": (), "neural_aggregate_spikes": (),
    "neural_observer_outputs": (11,), "neural_decoder_outputs": (11,),
    "neural_admitted_contributions": (11,),
}
JOINT_NAMES = tuple(f"joint_{leg}{part}" for leg in ("LF", "LM", "LH", "RF", "RM", "RH")
                    for part in ("Coxa", "Coxa_roll", "Coxa_yaw", "Femur", "Femur_roll", "Tibia", "Tarsus1"))
LEGS = ("LF", "LM", "LH", "RF", "RM", "RH")
ADMITTED = ("joint_LFTibia", "joint_LMTibia", "joint_LHTibia", "joint_RFTibia",
            "joint_RMTibia", "joint_RHTibia", "joint_LFFemur", "joint_LMFemur",
            "joint_LHFemur", "joint_RMFemur", "joint_RHFemur")
SENSORY = tuple(f"joint_{leg}Tibia" for leg in LEGS)
CHANNEL_INDEX = {name: i for i, name in enumerate(ADMITTED)}
JOINT_INDEX = {name: i for i, name in enumerate(JOINT_NAMES)}


class EvidenceError(RuntimeError):
    """M7D evidence failed a frozen provenance or schema invariant."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON evidence is not an object: {path}")
    return value


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _expected_inventory() -> set[str]:
    return {f"{condition}__{field}" for condition in CONDITIONS
            for field in (*PHYSICS_FIELDS, *NEURAL_FIELDS)}


def output_available(output_dir: Path = OUTPUT_DIR) -> bool:
    """Return false when either completed output would be overwritten."""
    for name in ("m7e_analysis.json", "m7e_manifest.json"):
        path = output_dir / name
        if path.exists() and _json(path).get("status") == "COMPLETE":
            return False
    return True


def validate_evidence(raw_path: Path = RAW_PATH, manifest_path: Path = MANIFEST_PATH,
                      summary_path: Path = SUMMARY_PATH, *,
                      expected_sha256: str = CANONICAL_SHA256,
                      expected_size: int = CANONICAL_SIZE,
                      physics_count: int = PHYSICS_COUNT,
                      neural_count: int = NEURAL_COUNT,
                      canonical: bool = True) -> tuple[dict[str, np.ndarray], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Fail closed, load with pickle disabled, and validate the full archive."""
    if not raw_path.is_file():
        raise EvidenceError(f"canonical M7D raw evidence is absent: {raw_path}")
    size = raw_path.stat().st_size
    if size != expected_size:
        raise EvidenceError(f"raw byte-size mismatch: expected {expected_size}, observed {size}")
    digest = _sha256(raw_path)
    if digest != expected_sha256:
        raise EvidenceError(f"raw SHA-256 mismatch: expected {expected_sha256}, observed {digest}")
    manifest, summary = _json(manifest_path), _json(summary_path)
    if manifest.get("status") != "COMPLETE" or summary.get("status") != "COMPLETE":
        raise EvidenceError("M7D summary and manifest must both have status COMPLETE")
    raw_spec = manifest.get("raw", {})
    if canonical and (raw_spec.get("byte_size") != size or raw_spec.get("sha256") != digest):
        raise EvidenceError("M7D manifest raw identity mismatch")
    if summary.get("raw_telemetry", {}).get("sha256") != digest:
        raise EvidenceError("M7D summary raw identity mismatch")
    if (manifest.get("schema") != "M7D-CORRECTED-SPONTANEOUS.1" or
            summary.get("schema") != "M7D-CORRECTED-SPONTANEOUS.1"):
        raise EvidenceError("M7D schema mismatch")
    if canonical and (summary.get("physics_states_per_condition") != PHYSICS_COUNT or
                      summary.get("neural_updates_per_condition") != NEURAL_COUNT or
                      set(summary.get("condition_completion", {})) != set(CONDITIONS) or
                      not all(summary["condition_completion"].values())):
        raise EvidenceError("M7D condition/sample metadata mismatch")
    declared = manifest.get("arrays")
    required = _expected_inventory()
    if not isinstance(declared, dict) or set(declared) != required:
        raise EvidenceError("manifest array inventory mismatch")
    try:
        with np.load(raw_path, allow_pickle=False) as archive:
            if set(archive.files) != required:
                raise EvidenceError("NPZ array inventory mismatch")
            arrays = {key: archive[key].copy() for key in archive.files}
    except (OSError, TypeError, ValueError) as exc:
        raise EvidenceError(f"NPZ cannot be loaded with allow_pickle=False: {exc}") from exc
    for key, array in arrays.items():
        field = key.split("__", 1)[1]
        count = physics_count if field in PHYSICS_FIELDS else neural_count
        tail = (PHYSICS_FIELDS | NEURAL_FIELDS)[field]
        dtype = "bool" if field == "physics_finite" else (
            "int64" if field in {"neural_delivered_drive_count", "neural_aggregate_spikes"} else "float64")
        if array.dtype.hasobject:
            raise EvidenceError(f"object dtype forbidden: {key}")
        if array.shape != (count, *tail) or str(array.dtype) != dtype:
            raise EvidenceError(f"shape/dtype mismatch: {key}")
        spec = declared[key]
        if spec.get("shape") != list(array.shape) or spec.get("dtype") != str(array.dtype):
            raise EvidenceError(f"manifest shape/dtype mismatch: {key}")
        if field == "physics_finite":
            if not np.all(array): raise EvidenceError(f"finite flag failed: {key}")
        elif not np.all(np.isfinite(array)):
            raise EvidenceError(f"nonfinite value forbidden: {key}")
    for condition in CONDITIONS:
        pt = arrays[f"{condition}__physics_time_ms"]
        nt = arrays[f"{condition}__neural_time_ms"]
        if not np.all(np.diff(pt) > 0) or not np.all(np.diff(nt) > 0):
            raise EvidenceError(f"non-monotonic time: {condition}")
        if not np.allclose(np.diff(pt), PHYSICS_DT_MS, rtol=0, atol=1e-10):
            raise EvidenceError(f"physics cadence mismatch: {condition}")
        if not np.array_equal(nt, pt[5::5]):
            raise EvidenceError(f"neural clock provenance mismatch: {condition}")
    for field in ("physics_time_ms", "neural_time_ms"):
        if not np.array_equal(arrays[f"{CONDITIONS[0]}__{field}"], arrays[f"{CONDITIONS[1]}__{field}"]):
            raise EvidenceError(f"cross-condition clock mismatch: {field}")
    validation = {"status": "PASS", "allow_pickle": False, "raw_byte_size": size,
                  "raw_sha256": digest, "conditions": list(CONDITIONS),
                  "physics_states_per_condition": physics_count,
                  "neural_samples_per_condition": neural_count,
                  "all_required_values_finite": True, "object_arrays": False}
    return arrays, manifest, summary, validation


def _tolerance(*signals: np.ndarray) -> float:
    scale = max((float(np.max(np.abs(x))) for x in signals if x.size), default=1.0)
    return float(32 * np.finfo(np.float64).eps * max(1.0, scale))


def _first(mask: np.ndarray, time: np.ndarray) -> float | None:
    indices = np.flatnonzero(mask)
    return float(time[indices[0]]) if indices.size else None


def signal_metrics(signal: np.ndarray, time_ms: np.ndarray) -> dict[str, Any]:
    x = np.asarray(signal, dtype=np.float64)
    tol = _tolerance(x)
    active = np.abs(x) > tol
    changes = np.diff(np.sign(np.where(np.abs(x) > tol, x, 0)))
    starts = active & np.r_[True, ~active[:-1]]
    peak = int(np.argmax(np.abs(x)))
    dt_s = float(np.median(np.diff(time_ms))) / 1000 if len(time_ms) > 1 else 0.0
    return {"first_nonzero_ms": _first(x != 0, time_ms), "first_meaningful_ms": _first(active, time_ms),
            "meaningful_tolerance": tol, "peak_absolute_value": float(np.abs(x[peak])),
            "peak_signed_value": float(x[peak]), "peak_time_ms": float(time_ms[peak]),
            "mean": float(np.mean(x)), "rms": float(np.sqrt(np.mean(x*x))),
            "integrated_absolute_activity": float(np.sum(np.abs(x)) * dt_s),
            "active_duration_ms": float(active.sum() * dt_s * 1000),
            "active_fraction": float(np.mean(active)), "sign_changes": int(np.count_nonzero(np.abs(changes) == 2)),
            "burst_episodes": int(starts.sum())}


def trajectory_difference(a: np.ndarray, b: np.ndarray, time_ms: np.ndarray) -> dict[str, Any]:
    delta = np.asarray(a, float) - np.asarray(b, float)
    magnitude = np.abs(delta) if delta.ndim == 1 else np.linalg.norm(delta, axis=1)
    tol = _tolerance(a, b)
    peak = int(np.argmax(magnitude))
    return {"max_absolute_divergence": float(np.max(np.abs(delta))),
            "max_vector_divergence": float(magnitude[peak]),
            "rms_divergence": float(np.sqrt(np.mean(delta*delta))),
            "first_exact_divergence_ms": _first(magnitude != 0, time_ms),
            "first_meaningful_divergence_ms": _first(magnitude > tol, time_ms),
            "meaningful_tolerance": tol, "time_of_max_divergence_ms": float(time_ms[peak]),
            "signed_integrated_difference": (np.trapz(delta, time_ms / 1000, axis=0).tolist()
                                                if delta.ndim > 1 else float(np.trapz(delta, time_ms / 1000)))}


def periodicity_metrics(signal: np.ndarray, time_ms: np.ndarray) -> dict[str, Any]:
    x = np.asarray(signal, float); centered = x - np.mean(x); tol = _tolerance(x)
    duration_s = float(time_ms[-1] - time_ms[0]) / 1000 if len(x) > 1 else 0.0
    variance = float(np.dot(centered, centered))
    if len(x) < 4 or variance <= tol*tol*len(x):
        return {"label": "NO_REPEATED_STRUCTURE", "zero_crossings": 0, "local_extrema": 0,
                "dominant_non_dc_frequency_hz": None, "periodicity_strength": 0.0,
                "approximate_cycle_count": 0.0, "frequency_resolution_hz": None,
                "autocorrelation_peak_nonzero": None}
    signs = np.sign(np.where(np.abs(centered) > tol, centered, 0)); nonzero = signs[signs != 0]
    crossings = int(np.count_nonzero(np.diff(nonzero) != 0)) if len(nonzero) > 1 else 0
    derivative = np.diff(x); extrema = int(np.count_nonzero(np.diff(np.sign(np.where(np.abs(derivative) > tol, derivative, 0))) != 0))
    dt_s = float(np.median(np.diff(time_ms))) / 1000
    power = np.abs(np.fft.rfft(centered)) ** 2; frequencies = np.fft.rfftfreq(len(x), dt_s); power[0] = 0
    peak = int(np.argmax(power)); total = float(power.sum()); strength = float(power[peak] / total) if total else 0.0
    frequency = float(frequencies[peak]) if total else None
    cycles = frequency * duration_s if frequency is not None else 0.0
    autocorr = np.correlate(centered, centered, mode="full")[len(x)-1:] / variance
    ac_peak = float(np.max(autocorr[1:])) if len(autocorr) > 1 else None
    if cycles < 2:
        label = "INSUFFICIENT_DURATION_FOR_PERIODICITY"
    elif crossings >= 4 and extrema >= 4 and strength >= 0.5:
        label = "OSCILLATORY_CANDIDATE"
    elif crossings >= 2 or extrema >= 2:
        label = "REPEATED_NONPERIODIC"
    else:
        label = "TRANSIENT_OR_BURSTLIKE"
    return {"label": label, "zero_crossings": crossings, "local_extrema": extrema,
            "dominant_non_dc_frequency_hz": frequency, "periodicity_strength": strength,
            "approximate_cycle_count": cycles, "frequency_resolution_hz": 1/duration_s if duration_s else None,
            "autocorrelation_peak_nonzero": ac_peak,
            "limitation": "A 500-ms record cannot establish a stable oscillator from a spectral peak alone."}


def cross_correlation(a: np.ndarray, b: np.ndarray, dt_ms: float) -> dict[str, Any]:
    x, y = np.asarray(a, float), np.asarray(b, float); xa, ya = x-x.mean(), y-y.mean()
    sx, sy = float(np.linalg.norm(xa)), float(np.linalg.norm(ya)); tol = _tolerance(x, y)
    overlap = int(np.count_nonzero((np.abs(x) > tol) & (np.abs(y) > tol)))
    if sx == 0 or sy == 0:
        return {"maximum_normalized_correlation": None, "lag_at_maximum_ms": None,
                "zero_lag_correlation": None, "relationship": "no clear relationship",
                "overlapping_active_samples": overlap}
    corr = np.correlate(xa, ya, mode="full") / (sx*sy); lags = np.arange(-len(x)+1, len(x))
    peak = int(np.argmax(np.abs(corr))); value = float(corr[peak])
    zero = float(corr[len(x)-1]); relationship = "temporally correlated" if value > 0 else "anti-correlated"
    if lags[peak]: relationship = "lagged relationship; " + relationship
    return {"maximum_normalized_correlation": value, "lag_at_maximum_ms": float(lags[peak]*dt_ms),
            "zero_lag_correlation": zero, "relationship": relationship,
            "overlapping_active_samples": overlap}


def _body(position: np.ndarray, quaternion: np.ndarray, time: np.ndarray) -> dict[str, Any]:
    delta = np.diff(position, axis=0); net = position[-1]-position[0]
    # M7D stores MuJoCo scalar-first quaternions (w, x, y, z).
    q = quaternion / np.linalg.norm(quaternion, axis=1, keepdims=True)
    up_z = 1 - 2*(q[:, 1]**2 + q[:, 2]**2)
    dot = float(np.clip(abs(np.dot(q[0], q[-1])), 0, 1))
    yaw = np.unwrap(np.arctan2(2*(q[:, 0]*q[:, 3]+q[:, 1]*q[:, 2]),
                               1-2*(q[:, 2]**2+q[:, 3]**2)))
    dt = np.diff(time)/1000; velocity = delta/dt[:, None]
    fall = position[:, 2] < .5 * position[0, 2]
    rollover = up_z <= 0
    return {"initial_root_position": position[0].tolist(), "final_root_position": position[-1].tolist(),
            "net_displacement_vector": net.tolist(), "horizontal_displacement_magnitude": float(np.linalg.norm(net[:2])),
            "vertical_displacement": float(net[2]), "total_3d_path_length": float(np.linalg.norm(delta, axis=1).sum()),
            "horizontal_path_length": float(np.linalg.norm(delta[:, :2], axis=1).sum()),
            "maximum_distance_from_initial": float(np.linalg.norm(position-position[0], axis=1).max()),
            "body_up_z": {"initial": float(up_z[0]), "final": float(up_z[-1]), "minimum": float(up_z.min())},
            "orientation_change_radians": float(2*math.acos(dot)), "yaw_change_radians": float(yaw[-1]-yaw[0]),
            "velocity_rms": float(np.sqrt(np.mean(velocity*velocity))),
            "minimum_body_height": float(position[:, 2].min()),
            "first_fall_time_ms": _first(fall, time), "first_rollover_time_ms": _first(rollover, time),
            "survived_through_500ms": bool(not fall[-1] and not rollover[-1]),
            "event_threshold_provenance": "Frozen M7: height < 0.5 * initial height; body-up Z <= 0."}


def _joint(signal: np.ndarray, time: np.ndarray) -> dict[str, Any]:
    diff = np.diff(signal); dt = np.diff(time)/1000; tol = _tolerance(signal)
    meaningful = np.sign(np.where(np.abs(diff) > tol, diff, 0)); meaningful = meaningful[meaningful != 0]
    return {"initial": float(signal[0]), "final": float(signal[-1]),
            "total_signed_change": float(signal[-1]-signal[0]), "range": float(np.ptp(signal)),
            "standard_deviation": float(np.std(signal)), "rms_velocity": float(np.sqrt(np.mean((diff/dt)**2))),
            "total_variation": float(np.abs(diff).sum()),
            "direction_reversals": int(np.count_nonzero(np.diff(meaningful) != 0)) if len(meaningful)>1 else 0,
            "direction_tolerance": tol}


def _milestones(arrays: Mapping[str, np.ndarray]) -> dict[str, Any]:
    a, b = CONDITIONS; pt = arrays[f"{a}__physics_time_ms"]; nt = arrays[f"{a}__neural_time_ms"]
    def first(field: str, time: np.ndarray, columns: Sequence[int] | None = None) -> float | None:
        x, y = arrays[f"{a}__{field}"], arrays[f"{b}__{field}"]
        if columns is not None: x, y = x[:, columns], y[:, columns]
        d = np.abs(x-y); magnitude = d if d.ndim == 1 else np.max(d, axis=1)
        return _first(magnitude > _tolerance(x, y), time)
    admitted_indices = [JOINT_INDEX[name] for name in ADMITTED]
    return {"D0_pre_intervention_equivalent": bool(np.array_equal(arrays[f"{a}__physics_joint_position"][0], arrays[f"{b}__physics_joint_position"][0])),
            "D1_first_mapped_motor_activity_ms": _first(np.any(np.abs(arrays[f"{a}__neural_admitted_contributions"]) > _tolerance(arrays[f"{a}__neural_admitted_contributions"]), axis=1), nt),
            "D2_first_observer_divergence_ms": first("neural_observer_outputs", nt),
            "D3_first_decoder_or_admitted_divergence_ms": (lambda values: min(values) if values else None)([x for x in (first("neural_decoder_outputs", nt), first("neural_admitted_contributions", nt)) if x is not None]),
            "D4_first_action_divergence_ms": first("physics_action", pt),
            "D5_first_admitted_joint_divergence_ms": first("physics_joint_position", pt, admitted_indices),
            "D6_first_whole_body_divergence_ms": first("physics_qpos", pt),
            "D7_first_tibial_sensory_divergence_ms": first("neural_sensory_encoded", nt),
            "D8_first_delivered_sensory_drive_divergence_ms": first("neural_delivered_drive_count", nt),
            "D9_first_downstream_cns_divergence_ms": first("neural_aggregate_spikes", nt),
            "D10_first_later_motor_divergence_ms": first("neural_observer_outputs", nt),
            "definition_note": "Derived from recorded numerical inequality tolerance; unavailable events are null."}


def analyze_arrays(arrays: Mapping[str, np.ndarray], summary: Mapping[str, Any]) -> dict[str, Any]:
    a, b = CONDITIONS; pt = arrays[f"{a}__physics_time_ms"]; nt = arrays[f"{a}__neural_time_ms"]
    body = {}; joints = {}; neural = {}; sensory = {}; legs = {}
    for condition in CONDITIONS:
        body[condition] = _body(arrays[f"{condition}__physics_body_position"],
                                arrays[f"{condition}__physics_body_orientation"], pt)
        joints[condition] = {name: _joint(arrays[f"{condition}__physics_joint_position"][:, i], pt)
                             for i, name in enumerate(JOINT_NAMES)}
        neural[condition] = {}
        for i, name in enumerate(ADMITTED):
            neural[condition][name] = {field: signal_metrics(arrays[f"{condition}__neural_{field}"][:, i], nt)
                for field in ("observer_outputs", "decoder_outputs", "admitted_contributions")}
    body["enabled_minus_disabled"] = trajectory_difference(arrays[f"{a}__physics_body_position"], arrays[f"{b}__physics_body_position"], pt)
    admitted = {}
    for name in ADMITTED:
        i, ni = JOINT_INDEX[name], CHANNEL_INDEX[name]; x = arrays[f"{a}__physics_joint_position"][:, i]; y = arrays[f"{b}__physics_joint_position"][:, i]
        contribution = arrays[f"{a}__neural_admitted_contributions"][:, ni]; onset = signal_metrics(contribution, nt)["first_meaningful_ms"]
        admitted[name] = {"difference": trajectory_difference(x, y, pt), "periodicity": periodicity_metrics(x-y, pt),
                          "contribution_periodicity": periodicity_metrics(contribution, nt),
                          "movement_before_contribution": float(np.abs(np.diff(x[pt <= onset])).sum()) if onset is not None else float(np.abs(np.diff(x)).sum()),
                          "movement_after_contribution": float(np.abs(np.diff(x[pt >= onset])).sum()) if onset is not None else 0.0,
                          "contribution_to_motion_correlation": cross_correlation(np.interp(pt, nt, contribution, left=0), x-y, PHYSICS_DT_MS)}
    for i, name in enumerate(SENSORY):
        x, y = arrays[f"{a}__neural_sensory_encoded"][:, i], arrays[f"{b}__neural_sensory_encoded"][:, i]
        sensory[name] = trajectory_difference(x, y, nt)
    sensory["delivered_drive_count"] = {condition: signal_metrics(arrays[f"{condition}__neural_delivered_drive_count"], nt) for condition in CONDITIONS}
    sensory["temporal_relationships"] = {
        "sensory_AB_to_later_CNS_AB": cross_correlation(np.sum(arrays[f"{a}__neural_sensory_encoded"]-arrays[f"{b}__neural_sensory_encoded"], axis=1), arrays[f"{a}__neural_aggregate_spikes"]-arrays[f"{b}__neural_aggregate_spikes"], NEURAL_DT_MS),
        "sensory_AB_to_later_motor_AB": cross_correlation(np.sum(arrays[f"{a}__neural_sensory_encoded"]-arrays[f"{b}__neural_sensory_encoded"], axis=1), np.sum(arrays[f"{a}__neural_observer_outputs"]-arrays[f"{b}__neural_observer_outputs"], axis=1), NEURAL_DT_MS)}
    for leg in LEGS:
        names = [n for n in JOINT_NAMES if n.startswith(f"joint_{leg}")]; admitted_names = [n for n in ADMITTED if n.startswith(f"joint_{leg}")]
        diffs = np.column_stack([arrays[f"{a}__physics_joint_position"][:, JOINT_INDEX[n]]-arrays[f"{b}__physics_joint_position"][:, JOINT_INDEX[n]] for n in admitted_names])
        mag = np.linalg.norm(diffs, axis=1); tol = _tolerance(diffs); peak = int(np.argmax(mag))
        legs[leg] = {"summed_joint_total_variation": {c: float(sum(joints[c][n]["total_variation"] for n in names)) for c in CONDITIONS},
                     "normalized_joint_total_variation": {c: float(np.mean([joints[c][n]["total_variation"] for n in names])) for c in CONDITIONS},
                     "admitted_joint_AB_rms": float(np.sqrt(np.mean(diffs*diffs))), "onset_of_divergence_ms": _first(mag > tol, pt),
                     "peak_movement_time_ms": float(pt[peak]), "activity_duration_ms": float(np.count_nonzero(mag > tol)*PHYSICS_DT_MS),
                     "repeated_movement_evidence": periodicity_metrics(mag, pt)}
    motor_delta = arrays[f"{a}__neural_admitted_contributions"]-arrays[f"{b}__neural_admitted_contributions"]
    correlations = {f"{x}__{y}": cross_correlation(motor_delta[:, CHANNEL_INDEX[x]], motor_delta[:, CHANNEL_INDEX[y]], NEURAL_DT_MS)
                    for i, x in enumerate(ADMITTED) for y in ADMITTED[i+1:]}
    milestones = _milestones(arrays); reported = summary.get("causal_milestones", {})
    milestone_check = {key: {"recomputed_ms": value, "reported_ms": reported.get(key),
                             "agrees_within_one_sample": (value is None and reported.get(key) is None) or
                             (value is not None and reported.get(key) is not None and abs(value-reported[key]) <= (NEURAL_DT_MS if key in {"D1_first_mapped_motor_activity_ms","D2_first_observer_divergence_ms","D3_first_decoder_or_admitted_divergence_ms","D7_first_tibial_sensory_divergence_ms","D8_first_delivered_sensory_drive_divergence_ms","D9_first_downstream_cns_divergence_ms","D10_first_later_motor_divergence_ms"} else PHYSICS_DT_MS)+1e-9)}
                       for key, value in milestones.items() if key.startswith("D") and key != "D0_pre_intervention_equivalent"}
    consistency = {}
    for condition in CONDITIONS:
        expected = summary.get("per_condition", {}).get(condition, {}); observed = body[condition]
        checks = {"body_path_length": math.isclose(observed["total_3d_path_length"], expected.get("body_path_length", math.nan), rel_tol=1e-10, abs_tol=1e-12),
                  "net_displacement": np.allclose(observed["net_displacement_vector"], expected.get("net_body_displacement", []), rtol=1e-10, atol=1e-12),
                  "minimum_body_height": math.isclose(observed["minimum_body_height"], expected.get("minimum_body_height", math.nan), rel_tol=1e-10, abs_tol=1e-12),
                  "minimum_body_up_z": math.isclose(observed["body_up_z"]["minimum"], expected.get("minimum_body_up_z", math.nan), rel_tol=1e-10, abs_tol=1e-12),
                  "first_fall_time_ms": observed["first_fall_time_ms"] == expected.get("first_fall_time_ms"),
                  "first_rollover_time_ms": observed["first_rollover_time_ms"] == expected.get("first_rollover_time_ms"),
                  "survived_through_500ms": bool(arrays[f"{condition}__physics_finite"][-1]) and observed["survived_through_500ms"]}
        consistency[condition] = {"checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
                                  "movement_category_inputs": {"net_displacement_vector": observed["net_displacement_vector"], "total_3d_path_length": observed["total_3d_path_length"]}}
    return {"schema": SCHEMA, "status": "COMPLETE", "classification": ["POSTRUN_ANALYSIS_COMPLETE", "NEURAL_PHYSICAL_DIVERGENCE_CHARACTERIZED", "SENSORIMOTOR_FEEDBACK_STRUCTURE_CHARACTERIZED"],
            "scope": {"exploratory_descriptive": True, "duration_ms": 500, "walking_classifier": None, "gait_classifier": None, "biological_function_inference": None},
            "thresholds": {"meaningful": "32 * float64 epsilon * max(1, maximum absolute signal scale); fixed before canonical inspection", "periodicity_candidate": "at least 2 cycles, 4 centered crossings, 4 extrema, and >=0.5 FFT non-DC power fraction; descriptive only"},
            "body": body, "joints": {"all_42": joints, "admitted_neural_joints": admitted,
            "baseline_only_joint_names": [n for n in JOINT_NAMES if n not in ADMITTED]}, "per_leg": legs,
            "neural_motor": neural, "sensory": sensory, "inter_interface_cross_correlation": correlations,
            "contact_support": {"available": True, "analysis_performed": False, "limitation": "The raw archive contains 36x3 force vectors but no recorded geom/leg identity mapping; no support or per-leg contact state is inferred."},
            "causal_milestones": milestones, "causal_milestone_consistency": milestone_check,
            "summary_consistency": consistency, "physics_transitions": 0, "neural_transitions": 0}


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def run(*, raw_path: Path = RAW_PATH, manifest_path: Path = MANIFEST_PATH,
        summary_path: Path = SUMMARY_PATH, output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    if not output_available(output_dir):
        raise FileExistsError("refusing to overwrite COMPLETE M7E output")
    arrays, source_manifest, summary, validation = validate_evidence(raw_path, manifest_path, summary_path)
    analysis = analyze_arrays(arrays, summary)
    analysis["provenance"] = {"input_path": str(raw_path.resolve()), "input_byte_size": validation["raw_byte_size"],
        "input_sha256": validation["raw_sha256"], "m7d_source_commit": source_manifest.get("source_commit"),
        "analyzer_source_commit": _git_commit(), "numpy_version": np.__version__, "analysis_schema": SCHEMA}
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_path, output_manifest = output_dir/"m7e_analysis.json", output_dir/"m7e_manifest.json"
    _write_json(analysis_path, analysis)
    manifest = {"schema": SCHEMA, "status": "COMPLETE", "analysis": {"path": str(analysis_path.resolve()),
        "byte_size": analysis_path.stat().st_size, "sha256": _sha256(analysis_path)}, "source": analysis["provenance"],
        "physics_transitions": 0, "neural_transitions": 0}
    _write_json(output_manifest, manifest)
    return analysis


def preflight() -> dict[str, Any]:
    if not output_available(): raise FileExistsError("refusing to overwrite COMPLETE M7E output")
    _, _, _, validation = validate_evidence()
    return {"status": "PASS", "validation": validation, "output_directory": str(OUTPUT_DIR.resolve()),
            "physics_transitions": 0, "neural_transitions": 0, "analysis_run": False}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--windows-preflight", action="store_true"); modes.add_argument("--analyze-windows", action="store_true")
    args = parser.parse_args(argv)
    if args.windows_preflight:
        preflight()
        print("M7E WINDOWS PREFLIGHT PASS — CANONICAL M7D RAW VERIFIED —\nTELEMETRY SCHEMA VERIFIED — READ-ONLY ANALYZER READY —\nZERO PHYSICS TRANSITIONS — ZERO NEURAL TRANSITIONS —\nANALYSIS NOT RUN")
    else:
        run(); print(f"M7E analysis complete: {ANALYSIS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
