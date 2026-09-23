"""Frozen M10B protocol, inert preflight, and explicit execution entry point.

Import and ``--preflight`` only read and hash frozen files.  The Windows
runtime is imported only after the explicit ``--run-windows`` switch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import m7d_corrected_spontaneous as m7d
from . import m9b_external_perturbation as m9b

HERE = Path(__file__).resolve().parent
M10A_DIR = HERE / "interface_output" / "m10a_physics_only_calibration"
M10A_SOURCE_COMMIT = "aa76c684343d088913eabe636d7a76dcc6e11e3b"
M10A_ARTIFACTS = {
    "m10a_raw.npz": "3058b21a4776ee8743b1ed5ea3233ed5e03e81eeafacf174b0d19ab06533af5c",
    "m10a_manifest.json": "86d4e0833b31adb8e836bf072c03c0cf39b413c5c3d4a34861a1f4766801253f",
    "m10a_report.json": "e08b5f127a18a9b1f51feca41cb140a6b8d787254bea106056a7c87ab30667b8",
}
FORCES = (0.256, 1.024, 2.896309375740099, 4.096)
CONDITIONS = (
    ("A_C", True, 0.0), ("B_C", False, 0.0),
    ("A_F0256", True, FORCES[0]), ("B_F0256", False, FORCES[0]),
    ("A_F1024", True, FORCES[1]), ("B_F1024", False, FORCES[1]),
    ("A_F2896", True, FORCES[2]), ("B_F2896", False, FORCES[2]),
    ("A_F4096", True, FORCES[3]), ("B_F4096", False, FORCES[3]),
)
PERTURBATION = {"direction_xyz": [0.0, 1.0, 0.0], "frame": "world",
    "application_body_source": "Thorax", "application_point": "authoritative body center of mass",
    "torque_xyz": [0.0, 0.0, 0.0], "start_ms_inclusive": 500.0,
    "stop_ms_exclusive": 520.0, "start_transition_inclusive": 5000,
    "stop_transition_exclusive": 5200, "transition_indices": "5000-5199",
    "first_possible_affected_state_ms": 500.1, "only_magnitude_varies": True}
WINDOWS = {
    "pre_perturbation": {"start_ms_inclusive": 0.0, "stop_ms_exclusive": 500.0},
    "direct_force": {"start_ms_inclusive": 500.0, "stop_ms_exclusive": 520.0},
    "early_post_force": {"start_ms_inclusive": 520.0, "stop_ms_exclusive": 557.0},
    "later_post_force": {"start_ms_inclusive": 557.0, "stop_ms_inclusive": 1500.0},
}
PRIMARY_THRESHOLDS = {"thorax_com_deviation_mm": 0.005,
                      "root_orientation_shortest_arc_deg": 0.25}
LABELS = ("ATTENUATING", "AMPLIFYING", "DIRECTIONALLY_MIXED",
          "NO_RESOLVED_DIRECTIONAL_EFFECT")
OUTPUT_DIR = HERE / "interface_output" / "m10b_perturbation_scaling"
PREREGISTRATION_PATH = OUTPUT_DIR / "m10b_preregistration.json"
FUTURE_OUTPUT_IDENTIFIERS = {
    "raw": "interface_output/m10b_perturbation_scaling/m10b_raw.npz",
    "report": "interface_output/m10b_perturbation_scaling/m10b_report.json",
    "manifest": "interface_output/m10b_perturbation_scaling/m10b_manifest.json",
}


def resolve_future_output(identifier: str, root: Path = HERE) -> Path:
    """Resolve a frozen repository-relative artifact identifier at runtime."""
    if identifier not in FUTURE_OUTPUT_IDENTIFIERS.values():
        raise ValueError("unknown M10B output identifier")
    return root / Path(identifier)


RAW_PATH = resolve_future_output(FUTURE_OUTPUT_IDENTIFIERS["raw"])
REPORT_PATH = resolve_future_output(FUTURE_OUTPUT_IDENTIFIERS["report"])
MANIFEST_PATH = resolve_future_output(FUTURE_OUTPUT_IDENTIFIERS["manifest"])
PREFLIGHT_PATH = OUTPUT_DIR / "m10b_preflight.json"
SCHEMA = "M10B-PREREGISTERED-PERTURBATION-SCALING-NEURAL-CAUSAL.1"
PREREGISTRATION_SHA256 = "a267647093d616f394374761da58ae495f12a6df6fe12e004abbcb1cb1b2d5a9"
PHYSICS_TRANSITIONS_PER_CONDITION = 15000
NEURAL_UPDATES_PER_CONDITION = 3000
TOTAL_PHYSICS_TRANSITIONS = 150000
TOTAL_NEURAL_UPDATES = 30000

RAW_SCHEMA = {
    "physics_time_ms": [15001], "root_thorax_position": [15001, 3],
    "root_orientation_wxyz": [15001, 4], "root_linear_velocity": [15001, 3],
    "root_angular_velocity": [15001, 3], "height": [15001],
    "joint_positions": [15001, 42], "distal_tarsus_positions": [15001, 6, 3],
    "physical_contact_observations": [15001, 6], "applied_external_force": [15000, 3],
    "tibial_proprioceptive_physical_inputs": [3000, 6], "modeled_sensory_encoding": [3000, 6],
    "delivered_sensory_cns_state": [3000, 6], "mapped_motor_population_state": [3000, 11],
    "decoder_state_output": [3000, 11], "admitted_neural_motor_pre_intervention": [3000, 11],
    "admitted_neural_motor_physical_contribution": [15000, 11],
    "physical_command_after_intervention": [15000, 42], "neural_time_ms": [3000],
    "condition_identity": [], "force_magnitude": [], "motor_enabled": [],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_m10a(directory: Path = M10A_DIR) -> dict[str, str]:
    """Require all canonical M10A inputs and their exact-byte identities."""
    verified = {}
    for name, expected in M10A_ARTIFACTS.items():
        path = directory / name
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"M10B fail-closed before transitions: frozen M10A mismatch: {name}")
        verified[name] = expected
    return verified


def verify_preregistration(path: Path = PREREGISTRATION_PATH) -> str:
    """Verify immutable scientific bytes after only CRLF-to-LF normalization."""
    if not path.is_file():
        raise RuntimeError("M10B fail-closed before transitions: frozen preregistration mismatch")
    physical = path.read_bytes()
    canonical = physical.replace(b"\r\n", b"\n")
    # A lone CR is not a Windows line ending and is therefore substantive.
    if b"\r" in canonical or hashlib.sha256(canonical).hexdigest() != PREREGISTRATION_SHA256:
        raise RuntimeError("M10B fail-closed before transitions: frozen preregistration mismatch")
    try:
        validate_protocol(json.loads(canonical.decode("utf-8")))
    except (UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("M10B fail-closed before transitions: invalid preregistration") from exc
    return PREREGISTRATION_SHA256


def force_at_transition(condition: str, transition: int) -> tuple[float, float, float]:
    rows = {name: magnitude for name, _, magnitude in CONDITIONS}
    if condition not in rows or not isinstance(transition, int) or not 0 <= transition < 15000:
        raise ValueError("canonical condition and transition required")
    magnitude = rows[condition]
    active = magnitude != 0 and 5000 <= transition < 5200
    return (0.0, magnitude if active else 0.0, 0.0)


def difference_in_differences(a_force: Any, a_control: Any,
                              b_force: Any, b_control: Any) -> Any:
    """Primary estimator: (A_F - A_C) - (B_F - B_C)."""
    return (a_force - a_control) - (b_force - b_control)


def gate_contributions(values: Mapping[str, float], motor_enabled: bool) -> dict[str, float]:
    """Apply the frozen M9B intervention immediately before physical apply."""
    if tuple(values) != m7d.ADMITTED_MOTOR:
        raise RuntimeError("M10B admitted motor inventory mismatch")
    return {name: float(value) if motor_enabled else 0.0 for name, value in values.items()}


def classify_direction(early_effect: float, later_effect: float, threshold: float) -> str:
    """Classify two preregistered post-force windows without floating-sign fishing."""
    if not all(math.isfinite(x) for x in (early_effect, later_effect, threshold)) or threshold <= 0:
        raise ValueError("finite effects and a positive preregistered threshold required")
    signs = {1 if value >= threshold else -1 if value <= -threshold else 0
             for value in (early_effect, later_effect)} - {0}
    if signs == {-1}: return "ATTENUATING"
    if signs == {1}: return "AMPLIFYING"
    if signs == {-1, 1}: return "DIRECTIONALLY_MIXED"
    return "NO_RESOLVED_DIRECTIONAL_EFFECT"


def scaling_summary(forces: Sequence[float], signed_effects: Sequence[float]) -> dict[str, Any]:
    """Four-point descriptive analysis; deliberately no fit, ratio, or correlation."""
    if tuple(forces) != FORCES or len(signed_effects) != 4 or not all(math.isfinite(x) for x in signed_effects):
        raise ValueError("ordered frozen forces and four finite effects required")
    values = tuple(float(x) for x in signed_effects)
    absolute = tuple(abs(x) for x in values)
    return {"signed_effects": list(values), "absolute_effects": list(absolute),
        "adjacent_signed_changes": [values[i + 1] - values[i] for i in range(3)],
        "adjacent_absolute_changes": [absolute[i + 1] - absolute[i] for i in range(3)],
        "resolved_sign_consistent": all(x > 0 for x in values) or all(x < 0 for x in values),
        "sign_changes": [values[i] * values[i + 1] < 0 for i in range(3)],
        "absolute_effect_monotonic_nondecreasing": all(absolute[i] <= absolute[i + 1] for i in range(3))}


def protocol() -> dict[str, Any]:
    return {"schema": SCHEMA, "status": "NOT_RUN", "canonical_experiment_executed": False,
        "scientific_question": "whether the preregistered physical perturbation-response effect attributable to neural-motor enablement changes systematically across four frozen magnitudes",
        "m10a": {"source_commit": M10A_SOURCE_COMMIT, "artifacts": M10A_ARTIFACTS,
                   "selected_force_series": list(FORCES), "read_only": True},
        "timing": {"flygym": "1.2.1", "mujoco": "3.2.7", "physics_dt_ms": 0.1,
            "neural_dt_ms": 0.5, "duration_ms": 1500.0, "physics_transitions": 15000,
            "physics_states": 15001, "neural_updates": 3000},
        "physical_initialization": m7d.protocol()["physical_initialization"],
        "conditions": [{"name": n, "motor_enabled": e, "force_magnitude": f,
                        "fresh_identical_deterministic_initialization": True} for n, e, f in CONDITIONS],
        "shared_controls": ["A_C", "B_C"], "perturbation": PERTURBATION,
        "interfaces": {"sensory": list(m9b.SENSORY_INTERFACES),
            "motor": [{"name": n, "action_index": i, "coordinate_sign": s} for n, i, s in m9b.MOTOR_INTERFACES],
            "provenance": "canonical M9B unchanged", "contact_is_neural_input": False},
        "disabled_intervention": {"male_cns_runs": True, "sensory_encoding_and_delivery_runs": True,
            "observer_runtime_runs": True, "decoder_runs": True, "zero_boundary": "immediately before physical application",
            "exact_11_channel_physical_contribution_zero_required": True},
        "primary_estimator": "delta_delta_F(t) = (A_F(t) - A_C(t)) - (B_F(t) - B_C(t))",
        "analysis_windows": WINDOWS,
        "window_rationale": "557 ms is the frozen M9C approximate first admitted-motor boundary; it separates post-force observations before versus from that modeled-chain milestone without asserting biological timing",
        "primary_metrics": ["thorax_com_deviation_mm", "root_orientation_shortest_arc_deg"],
        "supporting_metrics": ["root_linear_velocity", "root_angular_velocity", "height",
            "distal_tarsus_trajectory_deviation", "physical_contact_pattern_difference_observation_only"],
        "metric_reduction": "for each primary metric and window, maximum timestamp-aligned nonnegative condition-vs-shared-control deviation; directional effect is enabled minus disabled",
        "directional_resolution": {"thresholds": PRIMARY_THRESHOLDS, "comparison": "inclusive: <= -threshold attenuating; >= threshold amplifying",
            "post_force_windows_used": ["early_post_force", "later_post_force"],
            "opposite_resolved_window_signs": "DIRECTIONALLY_MIXED",
            "no_resolved_window_or_only_unresolved_opposition": "NO_RESOLVED_DIRECTIONAL_EFFECT",
            "labels": list(LABELS), "threshold_provenance": "M9A meaningful-disturbance conventions fixed before M10B"},
        "scaling_analysis": {"per_metric_and_window": ["signed directional effect at each force",
            "absolute effect at each force", "adjacent signed and absolute changes", "resolved sign consistency and adjacent sign changes",
            "absolute-effect monotonic nondecreasing indicator"], "curve_fit": False, "correlation": False,
            "normalization_or_ratio": False, "order": list(FORCES)},
        "raw_schema_per_condition": RAW_SCHEMA,
        "future_outputs": {**FUTURE_OUTPUT_IDENTIFIERS,
            "exclusive_creation_required": True, "m9_and_m10a_namespaces_read_only": True},
        "future_manifest_required": ["source_commit", "M10A source commit and exact artifact identities",
            "selected force series", "M9 interface provenance", "MaleCNS and connectome provenance",
            "physical initialization identity", "FlyGym MuJoCo and NumPy versions", "physics and neural timesteps",
            "duration and perturbation geometry", "condition matrix", "11 motor and six sensory channel identities",
            "frozen decoder filter gain saturation slew and bounds", "random seeds and deterministic state",
            "raw artifact SHA-256", "transition counts per condition", "force integrity",
            "disabled-motor exact-zero integrity", "absence of controllers reward RL and reference trajectory",
            "contact observation-only semantics"],
        "integrity_before_transitions": ["M10A exact hashes", "M9 interface identity", "frozen initialization",
            "versions and timing", "condition matrix", "force schedule", "clean exclusive M10B outputs"],
        "execution_absences": {"controllers": False, "reward": False, "rl": False,
            "reference_trajectory": False, "gait_logic": False, "contact_sensory_input": False}}


def validate_protocol(value: Mapping[str, Any]) -> None:
    # The already-frozen document contains the original Linux checkout root.
    # Translate only those three exact legacy serialization values to their
    # repository-relative identities; all runtime paths are resolved separately.
    comparable = dict(value)
    outputs = dict(comparable.get("future_outputs", {}))
    legacy_root = "/workspace/FlyBrainUnity/malecns_backend/embodiment/"
    for key, identifier in FUTURE_OUTPUT_IDENTIFIERS.items():
        if outputs.get(key) == legacy_root + identifier:
            outputs[key] = identifier
    comparable["future_outputs"] = outputs
    if (comparable != protocol() or tuple(value["m10a"]["selected_force_series"]) != FORCES
            or tuple(value["interfaces"]["sensory"]) != m9b.SENSORY_INTERFACES
            or value["physical_initialization"] != m7d.protocol()["physical_initialization"]):
        raise RuntimeError("M10B frozen preregistration mismatch")


def outputs_available() -> bool:
    return not any(path.exists() for path in (RAW_PATH, REPORT_PATH, MANIFEST_PATH))


def preflight(m10a_dir: Path = M10A_DIR) -> dict[str, Any]:
    """Perform read-only integrity checks and report explicit zero counters."""
    value = protocol()
    preregistration_sha256 = verify_preregistration()
    verified = verify_m10a(m10a_dir)
    if not outputs_available():
        raise FileExistsError("M10B future output namespace is not exclusively available")
    return {"schema": SCHEMA, "status": "PREFLIGHT_PASS", "canonical_experiment_executed": False,
        "physics_runtime_constructed": False, "male_cns_constructed": False,
        "physics_transitions": 0, "neural_transitions": 0,
        "sensory_encoding_or_delivery_count": 0, "neural_motor_decode_or_application_count": 0,
        "verified_m10a_artifact_hashes": verified, "frozen_force_series": list(FORCES),
        "frozen_preregistration_sha256": preregistration_sha256,
        "condition_matrix": value["conditions"], "perturbation": PERTURBATION,
        "interfaces": value["interfaces"], "analysis_windows": WINDOWS,
        "primary_metrics": value["primary_metrics"], "directional_resolution": value["directional_resolution"],
        "scaling_analysis": value["scaling_analysis"], "future_outputs": value["future_outputs"]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight:
        result = preflight()
    else:
        # Deliberately late: importing this module or preflighting cannot even
        # import the physics execution boundary.
        from . import _windows_m10b_perturbation_scaling_adapter as adapter
        result = adapter.run_windows()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
