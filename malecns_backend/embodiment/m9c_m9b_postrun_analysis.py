"""Strictly read-only analysis of the immutable canonical M9B archive.

Importing this module performs no I/O and constructs no scientific runtime.  The
only entry point, :func:`analyze`, reads numeric telemetry and exclusively
creates a new M9C namespace.  It never imports a Windows execution adapter.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Mapping

import numpy as np

from . import m9b_external_perturbation as m9b

SCHEMA = "M9C-M9B-READ-ONLY-POSTRUN-ANALYSIS.1"
HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE / "interface_output/m9b_external_perturbation"
OUTPUT_DIR = HERE / "interface_output/m9c_m9b_postrun_analysis"
LEGS = ("LF", "LM", "LH", "RF", "RM", "RH")
JOINTS = tuple(f"joint_{leg}{suffix}" for leg in LEGS for suffix in
               ("Coxa", "Coxa_roll", "Coxa_yaw", "Femur", "Femur_roll", "Tibia", "Tarsus1"))
PHYSICS_TRANSITIONS = 0
NEURAL_TRANSITIONS = 0

# Complete array contract emitted by CompactTelemetry plus the M8/M9B extended
# recorder.  The canonical model dimensions are independently captured by the
# four state-zero model snapshots in the immutable M9B manifest: nq=94 and
# nv=93.  They differ because MuJoCo represents the free-root orientation with
# four qpos quaternion coordinates but only three angular velocity DOFs.
M9B_RECORDED_SHAPES = {
    "physics_time_ms": (15001,),
    "physics_qpos": (15001, 94),
    "physics_qvel": (15001, 93),
    "physics_joint_position": (15001, 42),
    "physics_action": (15001, 42),
    "physics_ctrl": (15001, 48),
    "physics_body_position": (15001, 3),
    "physics_body_orientation": (15001, 4),
    "physics_contact_forces": (15001, 36, 3),
    "physics_finite": (15001,),
    "physics_tarsal_contact": (15001, 6),
    "physics_tarsus5_world_position": (15001, 6, 3),
    "physics_body_up_vector": (15001, 3),
    "physics_fall_rollover": (15001, 2),
    "physics_external_force": (15000, 3),
    "neural_time_ms": (3000,),
    "neural_sensory_encoded": (3000, 6),
    "neural_delivered_drive_count": (3000,),
    "neural_aggregate_spikes": (3000,),
    "neural_observer_outputs": (3000, 11),
    "neural_decoder_outputs": (3000, 11),
    "neural_admitted_contributions": (3000, 11),
    "neural_motor_pre_zero": (3000, 11),
    "neural_motor_post_zero": (3000, 11),
}


def _identity(path: Path) -> dict[str, Any]:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"path": path.name, "byte_size": path.stat().st_size, "sha256": h.hexdigest()}


def _require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(f"M9C fail-closed: {message}")


def validate_provenance(source_dir: Path = SOURCE_DIR) -> dict[str, Any]:
    """Validate all four source artifacts without loading raw telemetry."""
    paths = {name: source_dir / name for name in
             ("m9b_raw.npz", "m9b_report.json", "m9b_manifest.json", "m9b_preregistration.json")}
    _require(all(path.is_file() for path in paths.values()), "canonical artifact missing")
    manifest = json.loads(paths["m9b_manifest.json"].read_text(encoding="utf-8"))
    report = json.loads(paths["m9b_report.json"].read_text(encoding="utf-8"))
    prereg = json.loads(paths["m9b_preregistration.json"].read_text(encoding="utf-8"))
    identities = {name: _identity(path) for name, path in paths.items()}
    raw, rep = manifest.get("raw", {}), manifest.get("report", {})
    p = prereg.get("perturbation", {})
    expected_motor = [{"name": n, "action_index": i, "coordinate_sign": s}
                      for n, i, s in m9b.MOTOR_INTERFACES]
    checks = [manifest.get("schema") == m9b.SCHEMA, report.get("schema") == m9b.SCHEMA,
              prereg.get("schema") == m9b.SCHEMA, manifest.get("status") == "COMPLETE",
              report.get("status") == "COMPLETE_UNCLASSIFIED", report.get("classification") is None,
              manifest.get("protocol") == prereg,
              raw == {k: identities["m9b_raw.npz"][k] for k in ("byte_size", "sha256")},
              rep == {k: identities["m9b_report.json"][k] for k in ("byte_size", "sha256")},
              prereg.get("design", {}).get("conditions") == list(m9b.CONDITIONS),
              prereg.get("calibration", {}).get("selected_force_magnitude_native") == 1.024,
              p.get("direction_xyz") == [0.0, 1.0, 0.0], p.get("frame") == "world",
              p.get("application_body_source") == "Thorax",
              p.get("application_point") == "authoritative body center of mass",
              p.get("torque_xyz") == [0.0, 0.0, 0.0],
              p.get("start_transition_inclusive") == 5000,
              p.get("stop_transition_exclusive") == 5200,
              p.get("transition_indices") == "5000-5199",
              prereg.get("physics_dt_ms") == .1, prereg.get("neural_dt_ms") == .5,
              prereg.get("physics_transitions_per_condition") == 15000,
              prereg.get("physics_states_per_condition") == 15001,
              prereg.get("neural_updates_per_condition") == 3000,
              prereg.get("admitted_motor_interfaces") == expected_motor,
              prereg.get("admitted_sensory_interfaces") == list(m9b.SENSORY_INTERFACES)]
    _require(all(checks), "canonical provenance or protocol mismatch")
    return {"manifest": manifest, "report": report, "preregistration": prereg,
            "identities": identities}


def factorial(arrays: Mapping[str, np.ndarray], field: str) -> dict[str, np.ndarray]:
    """Return the two perturbation contrasts and their difference-in-differences."""
    values = {c: np.asarray(arrays[f"{c}__{field}"]) for c in m9b.CONDITIONS}
    _require(len({x.shape for x in values.values()}) == 1, f"shape mismatch for {field}")
    if any(value.dtype == np.bool_ for value in values.values()):
        values = {condition: value.astype(np.int8) for condition, value in values.items()}
    da, db = values["A_P"] - values["A_C"], values["B_P"] - values["B_C"]
    return {"delta_A": da, "delta_B": db, "interaction": da - db}


def first_divergence(value: np.ndarray, times: np.ndarray, *, start_ms: float = 500.0) -> float | None:
    value, times = np.asarray(value), np.asarray(times)
    mask = np.any(value != 0, axis=tuple(range(1, value.ndim))) if value.ndim > 1 else value != 0
    found = np.flatnonzero(mask & (times >= start_ms))
    return None if not found.size else float(times[found[0]])


def quaternion_shortest_arc(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Shortest unsigned orientation separation in radians; invariant to q/-q."""
    left, right = np.asarray(left, float), np.asarray(right, float)
    ln, rn = np.linalg.norm(left, axis=-1), np.linalg.norm(right, axis=-1)
    _require(bool(np.all(ln > 0) and np.all(rn > 0)), "zero quaternion")
    dot = np.sum(left * right, axis=-1) / (ln * rn)
    return 2 * np.arccos(np.clip(np.abs(dot), 0.0, 1.0))


def verify_force_integrity(arrays: Mapping[str, np.ndarray]) -> dict[str, Any]:
    expected = np.zeros((15000, 3)); expected[5000:5200, 1] = 1.024
    for condition in m9b.CONDITIONS:
        actual = np.asarray(arrays[f"{condition}__physics_external_force"])
        wanted = expected if condition in m9b.PERTURBED else np.zeros_like(expected)
        _require(actual.shape == wanted.shape and np.array_equal(actual, wanted),
                 f"force schedule mismatch in {condition}")
    _require(np.array_equal(arrays["A_P__physics_external_force"],
                            arrays["B_P__physics_external_force"]), "perturbed forces differ")
    return {"passed": True, "nonzero_transitions_per_perturbed_condition": 200,
            "active_transition_indices": [5000, 5199], "force_xyz_world": [0.0, 1.024, 0.0],
            "application": "Thorax authoritative body center of mass", "torque_xyz": [0.0, 0.0, 0.0],
            "first_potentially_affected_state": 5001, "first_potentially_affected_time_ms": 500.1}


def audit_disabled(arrays: Mapping[str, np.ndarray]) -> dict[str, Any]:
    result = {}
    for c in ("B_P", "B_C"):
        pre = np.asarray(arrays[f"{c}__neural_motor_pre_zero"])
        post = np.asarray(arrays[f"{c}__neural_motor_post_zero"])
        required = ("neural_time_ms", "neural_sensory_encoded", "neural_delivered_drive_count",
                    "neural_aggregate_spikes", "neural_observer_outputs", "neural_decoder_outputs")
        _require(pre.shape == (3000, 11) and post.shape == (3000, 11), f"disabled vector shape in {c}")
        _require(np.array_equal(post, np.zeros_like(post)), f"disabled post-zero nonzero in {c}")
        _require(all(np.asarray(arrays[f"{c}__{x}"]).shape[0] == 3000 for x in required),
                 f"disabled processing cadence in {c}")
        result[c] = {"neural_updates": 3000, "sensory_observer_decoder_recorded": True,
                     "pre_zero_vector_recorded": True, "post_zero_exactly_zero": True,
                     "gate_boundary": "immediately before physical application"}
    return result


def _summary(value: np.ndarray, times: np.ndarray) -> dict[str, Any]:
    """Summarize one scalar series or one component vector series.

    The first axis is always time.  A second axis, when present, is the set of
    components belonging to *one* scientifically identified vector.  Entity or
    channel axes must be selected by :func:`_contrast_summaries` before calling
    this function; accepting higher ranks here would make a peak ambiguous and
    was the cause of the original M9C failure.
    """
    v, t = np.asarray(value), np.asarray(times)
    _require(v.ndim in (1, 2), "summary supports only (T,) scalars or (T,D) vectors")
    _require(t.ndim == 1 and v.shape[0] == t.shape[0], "summary time axis mismatch")
    _require(v.ndim == 1 or v.shape[1] > 0, "summary vector has no components")
    magnitude = np.abs(v) if v.ndim == 1 else np.linalg.norm(v, axis=-1)
    eligible = np.flatnonzero(t >= 500.0)
    _require(bool(eligible.size), "summary contains no post-onset sample")
    peak = int(eligible[np.argmax(magnitude[eligible])])
    samples = {}
    for when in (520.0, 750.0, 1000.0, 1500.0):
        i = int(np.argmin(np.abs(t - when)))
        samples[str(int(when))] = {"value": np.asarray(v[i]).tolist(), "magnitude": float(magnitude[i])}
    peak_value = float(v[peak]) if v.ndim == 1 else v[peak].tolist()
    return {"first_detectable_divergence_ms": first_divergence(v, t),
            "force_offset_520_ms": samples["520"], "at_750_ms": samples["750"],
            "at_1000_ms": samples["1000"], "at_1500_ms": samples["1500"],
            "maximum_magnitude": float(magnitude[peak]), "maximum_time_ms": float(t[peak]),
            "value_at_maximum": peak_value,
            "post_run_descriptive_return_fraction_at_1500_ms":
                (None if magnitude[peak] == 0 else float(1 - magnitude[eligible[-1]] / magnitude[peak])),
            "trajectory_description": "exact signed/component series summarized; inspect values for decay, sign change, oscillation, or persistence"}


def _contrast_summaries(arrays: Mapping[str, np.ndarray], field: str, times: np.ndarray,
                        names: tuple[str, ...] | None = None) -> dict[str, Any]:
    """Summarize factorial contrasts without discarding channel/entity identity.

    ``(T,)`` and unnamed ``(T,D)`` inputs describe one scalar or vector.
    Named ``(T,N)`` inputs describe N scalar channels.  Named ``(T,N,D)``
    inputs describe N vector entities.  Named data are always reported per
    identity; the explicitly labelled aggregate is descriptive only.
    """
    contrasts = factorial(arrays, field)
    out = {}
    for label, value in contrasts.items():
        value = np.asarray(value)
        if names is None:
            _require(value.ndim in (1, 2), f"unsupported unnamed rank for {field}")
            item = {"vector_or_signed_summary": _summary(value, times)}
        else:
            _require(value.ndim in (2, 3), f"unsupported named rank for {field}")
            _require(value.shape[1] == len(names), f"identity count mismatch for {field}")
            key = "channels" if value.ndim == 2 else "entities"
            identified = {name: _summary(value[:, i], times) for i, name in enumerate(names)}
            item = {
                key: identified,
                "aggregate_l2_summary": _summary(
                    np.linalg.norm(value.reshape(value.shape[0], -1), axis=1), times),
                "aggregate_l2_definition": (
                    "Euclidean root-sum-square across all named channels"
                    if value.ndim == 2 else
                    "Euclidean root-sum-square across all named entities and vector components"),
            }
            ranked = sorted(names, key=lambda n: identified[n]["maximum_magnitude"], reverse=True)
            item[f"largest_{key}_by_peak_magnitude"] = ranked
        out[label] = item
    return out


def classify(interaction_detected: bool, admitted_interaction_detected: bool) -> dict[str, Any]:
    supported = []
    if not interaction_detected and not admitted_interaction_detected:
        supported.append(m9b.CLASSIFICATIONS[0])
    if admitted_interaction_detected:
        supported.append(m9b.CLASSIFICATIONS[1])
    if interaction_detected:
        supported.append(m9b.CLASSIFICATIONS[2])
    primary = (m9b.CLASSIFICATIONS[2] if interaction_detected else
               m9b.CLASSIFICATIONS[1] if admitted_interaction_detected else m9b.CLASSIFICATIONS[0])
    return {"primary": primary, "supported": supported,
            "rule": "interaction is primary; causal motor alteration requires changed admitted contribution; otherwise no detectable effect"}


def _load_raw(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name].copy() for name in archive.files}


def _clock_accumulation_tolerance(expected: np.ndarray, dt_ms: float) -> np.ndarray:
    """Bound binary64 error from the recorder's repeated clock advancement.

    MuJoCo advances its seconds-valued binary64 clock once per transition and
    the recorder then multiplies that value by 1000.  Each addition contributes
    at most half an ULP (round-to-nearest); the final ULP covers construction of
    the independently vectorized nominal reference.  This is a derived IEEE-754
    bound, not a fitted ``allclose`` tolerance.
    """
    # Convert the nominal millisecond values to the seconds scale on which the
    # accumulation actually occurs, then return the error bound in milliseconds.
    seconds = expected / 1000.0
    dt_seconds = dt_ms / 1000.0
    addition_ulp = np.spacing(np.maximum(np.abs(seconds), abs(dt_seconds)))
    return 1000.0 * (0.5 * np.cumsum(addition_ulp) +
                     np.spacing(np.maximum(np.abs(seconds), abs(dt_seconds))))


def _validate_clock(time: np.ndarray, *, sample_count: int, dt_ms: float,
                    first_index: int, label: str,
                    tolerance: np.ndarray | None = None) -> np.ndarray:
    """Validate sample-index cadence under the frozen binary64 recorder model."""
    time = np.asarray(time)
    _require(time.dtype == np.dtype("float64"), f"{label} dtype")
    _require(time.shape == (sample_count,), f"{label} sample count")
    _require(bool(np.all(np.isfinite(time))), f"{label} nonfinite timestamp")
    _require(bool(np.all(np.diff(time) > 0)), f"{label} timestamps not strictly monotonic")
    indices = np.arange(first_index, first_index + sample_count, dtype=np.float64)
    expected = indices * dt_ms
    if tolerance is None:
        tolerance = _clock_accumulation_tolerance(expected, dt_ms)
    _require(tolerance.shape == time.shape, f"{label} tolerance shape")
    delta = np.abs(time - expected)
    _require(bool(delta[0] <= tolerance[0]), f"{label} origin")
    _require(bool(delta[-1] <= tolerance[-1]), f"{label} endpoint")
    _require(bool(np.all(delta <= tolerance)), f"{label} index cadence")

    # Adjacent subtraction exposes the rounding errors at both endpoints.  The
    # per-index accumulated bounds therefore also bound any represented step.
    step_tolerance = tolerance[:-1] + tolerance[1:] + np.spacing(dt_ms)
    _require(bool(np.all(np.abs(np.diff(time) - dt_ms) <= step_tolerance)),
             f"{label} dt")
    return tolerance


def _validate_arrays(a: Mapping[str, np.ndarray]) -> None:
    expected_keys = {f"{c}__{name}" for c in m9b.CONDITIONS for name in M9B_RECORDED_SHAPES}
    _require(set(a) == expected_keys, "recorded array inventory mismatch")
    for c in m9b.CONDITIONS:
        for name, shape in M9B_RECORDED_SHAPES.items():
            _require(f"{c}__{name}" in a and np.asarray(a[f"{c}__{name}"]).shape == shape,
                     f"missing or malformed {c} {name}")
    for c in m9b.CONDITIONS:
        pt = np.asarray(a[f"{c}__physics_time_ms"])
        nt = np.asarray(a[f"{c}__neural_time_ms"])
        physics_tolerance = _validate_clock(
            pt, sample_count=15001, dt_ms=.1, first_index=0,
            label=f"physics cadence {c}")
        # Neural updates occur at steps 5, 10, ..., 15000.  The recorder writes
        # the very same ``now_ms`` scalar to neural and physics telemetry on
        # those iterations; it does not own a zero-origin 0.5-ms accumulator.
        sampled_physics = pt[5::5]
        neural_tolerance = physics_tolerance[5::5]
        _validate_clock(nt, sample_count=3000, dt_ms=.5, first_index=1,
                        label=f"neural cadence {c}", tolerance=neural_tolerance)
        _require(bool(np.all(np.abs(nt - sampled_physics) <= 2 * neural_tolerance)),
                 f"neural/physics index correspondence {c}")
    # Separate conditions use the identical deterministic MuJoCo clock.  These
    # are recorded peers, not independently reconstructed decimal references.
    for field in ("physics_time_ms", "neural_time_ms"):
        reference = a[f"A_P__{field}"]
        _require(all(np.array_equal(reference, a[f"{c}__{field}"])
                     for c in m9b.CONDITIONS), f"cross-condition {field}")
    state_fields = ("physics_body_position", "physics_body_orientation", "physics_joint_position")
    _require(all(np.array_equal(a[f"A_P__{x}"][0], a[f"{c}__{x}"][0])
                 for x in state_fields for c in m9b.CONDITIONS), "state-zero inequality")


def _publish(output_dir: Path, result: Mapping[str, Any], report: Mapping[str, Any],
             source_identities: Mapping[str, Any]) -> None:
    """Publish the complete M9C namespace with one atomic directory rename."""
    staging = output_dir.with_name(f".{output_dir.name}.tmp-{os.getpid()}")
    _require(not staging.exists(), "M9C transactional staging namespace already exists")
    staging.mkdir(parents=False, exist_ok=False)
    try:
        for name, value in (("m9c_analysis.json", result), ("m9c_report.json", report)):
            with (staging / name).open("x", encoding="utf-8") as stream:
                json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")
        manifest = {"schema": SCHEMA, "status": "COMPLETE", "read_only": True,
            "physics_transitions": 0, "neural_transitions": 0,
            "source_m9b_artifacts": source_identities,
            "analyzer_source_commit": result["analyzer_source_commit"],
            "outputs": {name: _identity(staging / name)
                        for name in ("m9c_analysis.json", "m9c_report.json")}}
        with (staging / "m9c_manifest.json").open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")
        # The completed directory becomes visible under its final name at once.
        staging.rename(output_dir)
    except BaseException:
        # A staging directory is never a final-looking M9C output namespace.
        if staging.exists():
            shutil.rmtree(staging)
        raise


def analyze(source_dir: Path = SOURCE_DIR, output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    """Analyze canonical evidence and exclusively publish three JSON artifacts."""
    _require(not output_dir.exists(), "M9C output namespace already exists")
    provenance = validate_provenance(source_dir)
    arrays = _load_raw(source_dir / "m9b_raw.npz")
    _validate_arrays(arrays)
    force = verify_force_integrity(arrays)
    disabled = audit_disabled(arrays)
    pt, nt = arrays["A_P__physics_time_ms"], arrays["A_P__neural_time_ms"]
    # qvel's first six coordinates are authoritative root linear/angular velocities.
    physical = {"root_position_xyz": _contrast_summaries(arrays, "physics_body_position", pt),
        "body_up_vector_xyz": _contrast_summaries(arrays, "physics_body_up_vector", pt),
        "joints": _contrast_summaries(arrays, "physics_joint_position", pt, JOINTS),
        "distal_tarsi_xyz": _contrast_summaries(arrays, "physics_tarsus5_world_position", pt, LEGS),
        "contacts_signed": _contrast_summaries(arrays, "physics_tarsal_contact", pt, LEGS),
        "fall_rollover_signed": _contrast_summaries(arrays, "physics_fall_rollover", pt,
                                                     ("fall", "rollover"))}
    # Replace qvel summary with explicit root slices after checking the available dimensionality.
    qvel = {c: arrays[f"{c}__physics_qvel"] for c in m9b.CONDITIONS}
    _require(all(v.ndim == 2 and v.shape[0] == 15001 and v.shape[1] >= 6 for v in qvel.values()), "qvel shape")
    for key, sl in (("root_linear_velocity_xyz", slice(0, 3)), ("root_angular_velocity_xyz", slice(3, 6))):
        temp = {f"{c}__x": qvel[c][:, sl] for c in m9b.CONDITIONS}
        physical[key] = _contrast_summaries(temp, "x", pt)
    orientations = {}
    for label, p, c in (("delta_A", "A_P", "A_C"), ("delta_B", "B_P", "B_C")):
        orientations[label] = _summary(quaternion_shortest_arc(arrays[f"{p}__physics_body_orientation"],
                                                                arrays[f"{c}__physics_body_orientation"]), pt)
    orientations["interaction"] = _summary(
        quaternion_shortest_arc(arrays["A_P__physics_body_orientation"], arrays["A_C__physics_body_orientation"])
        - quaternion_shortest_arc(arrays["B_P__physics_body_orientation"], arrays["B_C__physics_body_orientation"]), pt)
    physical["shortest_arc_orientation_radians"] = orientations
    contact_details = {"contact_state_at_perturbation_onset": {
        c: {leg: bool(arrays[f"{c}__physics_tarsal_contact"][5000, i]) for i, leg in enumerate(LEGS)}
        for c in m9b.CONDITIONS}}
    for label, left, right in (("delta_A", "A_P", "A_C"), ("delta_B", "B_P", "B_C")):
        different = arrays[f"{left}__physics_tarsal_contact"] != arrays[f"{right}__physics_tarsal_contact"]
        contact_details[label] = {leg: {"first_difference_ms": first_divergence(different[:, i], pt),
            "total_difference_duration_ms": float(np.count_nonzero(different[:, i] & (pt >= 500)) * .1)}
            for i, leg in enumerate(LEGS)}
    contact_details["interpretation_boundary"] = "authoritative physical contact; not a neural sensory input"
    physical["contact_analysis"] = contact_details
    neural_fields = (("tibial_proprioception", "neural_sensory_encoded", m9b.SENSORY_INTERFACES),
        ("delivered_sensory_drive_count", "neural_delivered_drive_count", None),
        ("aggregate_cns_spikes", "neural_aggregate_spikes", None),
        ("mapped_motor_observers", "neural_observer_outputs", tuple(n for n, _, _ in m9b.MOTOR_INTERFACES)),
        ("decoder_outputs", "neural_decoder_outputs", tuple(n for n, _, _ in m9b.MOTOR_INTERFACES)),
        ("admitted_physical_motor_contributions", "neural_admitted_contributions", tuple(n for n, _, _ in m9b.MOTOR_INTERFACES)))
    neural = {label: _contrast_summaries(arrays, field, nt, names) for label, field, names in neural_fields}
    milestone_fields = [("physical_trajectory_divergence_ms", factorial(arrays, "physics_body_position"), pt),
        ("modeled_proprioceptive_encoding_divergence_ms", factorial(arrays, "neural_sensory_encoded"), nt),
        ("delivered_sensory_drive_divergence_ms", factorial(arrays, "neural_delivered_drive_count"), nt),
        ("aggregate_cns_spike_divergence_ms", factorial(arrays, "neural_aggregate_spikes"), nt),
        ("mapped_motor_observer_divergence_ms", factorial(arrays, "neural_observer_outputs"), nt),
        ("decoder_output_divergence_ms", factorial(arrays, "neural_decoder_outputs"), nt),
        ("admitted_motor_contribution_divergence_ms", factorial(arrays, "neural_admitted_contributions"), nt)]
    milestones = {label: {contrast: first_divergence(value, times) for contrast, value in values.items()}
                  for label, values, times in milestone_fields}
    milestones["external_force_application_ms"] = {"delta_A": 500.0, "delta_B": 500.0, "interaction": None}
    milestones["first_potential_physical_effect_ms"] = {"delta_A": 500.1, "delta_B": 500.1, "interaction": 500.1}
    milestones["subsequent_physical_divergence_after_changed_motor_ms"] = {}
    milestones["later_sensory_cns_motor_divergence_ms"] = {}
    for contrast in ("delta_A", "delta_B", "interaction"):
        motor_time = milestones["admitted_motor_contribution_divergence_ms"][contrast]
        position = factorial(arrays, "physics_body_position")[contrast]
        milestones["subsequent_physical_divergence_after_changed_motor_ms"][contrast] = (
            None if motor_time is None else first_divergence(position, pt, start_ms=motor_time + .1))
        later = [milestones[key][contrast] for key in
                 ("modeled_proprioceptive_encoding_divergence_ms", "aggregate_cns_spike_divergence_ms",
                  "mapped_motor_observer_divergence_ms", "decoder_output_divergence_ms")
                 if milestones[key][contrast] is not None and
                 (motor_time is None or milestones[key][contrast] > motor_time)]
        milestones["later_sensory_cns_motor_divergence_ms"][contrast] = min(later) if later else None
    interaction = any(milestones[k]["interaction"] is not None for k in
                      ("physical_trajectory_divergence_ms", "mapped_motor_observer_divergence_ms", "decoder_output_divergence_ms"))
    admitted = (milestones["admitted_motor_contribution_divergence_ms"]["interaction"] is not None and
                milestones["subsequent_physical_divergence_after_changed_motor_ms"]["interaction"] is not None)
    result = {"schema": SCHEMA, "status": "COMPLETE", "read_only": True,
        "physics_transitions": 0, "neural_transitions": 0,
        "source_m9b_artifacts": provenance["identities"], "source_m9b_commit": provenance["manifest"].get("source_commit"),
        "analyzer_source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "state_zero_equivalent": True, "pre_force_ab_trajectory_equality_required": False,
        "force_integrity": force, "disabled_control_audit": disabled, "physical_response": physical,
        "neural_sensorimotor_response": neural, "causal_milestones": milestones,
        "classification": classify(interaction, admitted),
        "limitations": ["Exact numeric inequality defines detectable divergence; no post-hoc threshold was selected.",
          "Aggregate CNS state and mapped population activity were not separately recorded; aggregate spikes and observer states are reported without substitution.",
          "Contact is authoritative physical telemetry, not a neural sensory input in this embodiment.",
          "Temporal ordering alone does not establish biological function.",
          "No result is labeled balance, stabilization, righting, reflex, natural recovery, gait, or CPG.",
          "Return fractions are post-run descriptive metrics, not preregistered selection criteria."]}
    report = {"schema": SCHEMA, "status": "COMPLETE", "read_only": True,
              "physics_transitions": 0, "neural_transitions": 0,
              "classification": result["classification"], "causal_milestones": milestones,
              "limitations": result["limitations"]}
    _publish(output_dir, result, report, provenance["identities"])
    return result


if __name__ == "__main__":
    raise SystemExit("Import and call analyze() explicitly after review; no execution CLI is provided.")
