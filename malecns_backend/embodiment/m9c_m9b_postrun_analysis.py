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
    v, t = np.asarray(value), np.asarray(times)
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
    contrasts = factorial(arrays, field)
    out = {}
    for label, value in contrasts.items():
        item = {"vector_or_signed_summary": _summary(value, times)}
        if names is not None:
            item["channels"] = {name: _summary(value[:, i], times) for i, name in enumerate(names)}
            ranked = sorted(names, key=lambda n: item["channels"][n]["maximum_magnitude"], reverse=True)
            item["largest_channels_by_peak_magnitude"] = ranked
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


def _validate_arrays(a: Mapping[str, np.ndarray]) -> None:
    expected_keys = {f"{c}__{name}" for c in m9b.CONDITIONS for name in M9B_RECORDED_SHAPES}
    _require(set(a) == expected_keys, "recorded array inventory mismatch")
    for c in m9b.CONDITIONS:
        for name, shape in M9B_RECORDED_SHAPES.items():
            _require(f"{c}__{name}" in a and np.asarray(a[f"{c}__{name}"]).shape == shape,
                     f"missing or malformed {c} {name}")
    pt = np.arange(15001) * .1
    nt = np.arange(3000) * .5
    for c in m9b.CONDITIONS:
        _require(np.array_equal(a[f"{c}__physics_time_ms"], pt), f"physics cadence {c}")
        _require(np.array_equal(a[f"{c}__neural_time_ms"], nt), f"neural cadence {c}")
    state_fields = ("physics_body_position", "physics_body_orientation", "physics_joint_position")
    _require(all(np.array_equal(a[f"A_P__{x}"][0], a[f"{c}__{x}"][0])
                 for x in state_fields for c in m9b.CONDITIONS), "state-zero inequality")


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
    output_dir.mkdir(parents=False, exist_ok=False)
    try:
        for name, value in (("m9c_analysis.json", result), ("m9c_report.json", report)):
            with (output_dir / name).open("x", encoding="utf-8") as stream:
                json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")
        manifest = {"schema": SCHEMA, "status": "COMPLETE", "read_only": True,
            "physics_transitions": 0, "neural_transitions": 0,
            "source_m9b_artifacts": provenance["identities"], "analyzer_source_commit": result["analyzer_source_commit"],
            "outputs": {name: _identity(output_dir / name) for name in ("m9c_analysis.json", "m9c_report.json")}}
        with (output_dir / "m9c_manifest.json").open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")
    except BaseException:
        # Never leave a namespace that could be mistaken for a completed analysis.
        for path in output_dir.glob("*"): path.unlink()
        output_dir.rmdir()
        raise
    return result


if __name__ == "__main__":
    raise SystemExit("Import and call analyze() explicitly after review; no execution CLI is provided.")
