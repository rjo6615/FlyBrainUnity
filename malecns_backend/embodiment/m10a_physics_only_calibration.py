"""M10A preregistration for physics-only perturbation-range calibration.

Importing and preflighting this module execute no physics or neural transition.
The scientific runner is deliberately isolated in a physics-only adapter and is
not invoked unless the future ``--run-windows`` mode is explicitly requested.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import m7d_corrected_spontaneous as m7d

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "interface_output" / "m10a_physics_only_calibration"
PREREGISTRATION_PATH = OUTPUT_DIR / "m10a_preregistration.json"
REPORT_PATH = OUTPUT_DIR / "m10a_report.json"
MANIFEST_PATH = OUTPUT_DIR / "m10a_manifest.json"
SCHEMA = "M10A-PHYSICS-ONLY-PERTURBATION-RANGE-CALIBRATION.1"

ANCHOR_FORCE_NATIVE = 1.024
# Half-octave spacing preserves M9A's geometric-escalation convention while
# resolving levels between its factor-two candidates. Values are generated,
# not independently chosen decimal forces.
LADDER_HALF_OCTAVE_INDICES = tuple(range(-4, 5))
CANDIDATE_FORCE_NATIVE = tuple(
    ANCHOR_FORCE_NATIVE * 2.0 ** (index / 2.0)
    for index in LADDER_HALF_OCTAVE_INDICES
)
CONTROL_FORCE_NATIVE = 0.0
DIRECTION = (0.0, 1.0, 0.0)
APPLICATION_BODY_SOURCE = "Thorax"
APPLICATION_POINT = "authoritative body center of mass"
START_MS, STOP_MS, DURATION_MS = 500.0, 520.0, 1500.0
DT_MS = m7d.PHYSICS_DT_MS
START_TRANSITION, STOP_TRANSITION = 5000, 5200
TRANSITIONS, STATES = 15_000, 15_001
TARGET_NONZERO_COUNT = 4
NO_SELECTION = "NO_PREREGISTERED_FORCE_SERIES_QUALIFIES"
ANCHOR_FAILURE = "M9_ANCHOR_FAILED_MECHANICAL_INTEGRITY_GATE"

PHYSICAL_METRIC_KEYS = frozenset({
    "magnitude_native", "finite", "catastrophic_through_750ms",
    "max_absolute_root_displacement_mm", "max_absolute_tilt_deg",
    "post_force_observation_ms", "max_continuous_divergence",
    "max_root_position_divergence_mm", "max_orientation_divergence_deg",
    "max_distal_tarsus_divergence_mm", "contact_pattern_diverged",
    "peak_linear_velocity", "peak_angular_velocity",
    "post_perturbation_trajectory_deviation_mm",
})


def force_at_transition(magnitude: float, transition: int) -> tuple[float, float, float]:
    """Return world-frame force for an outgoing physics transition."""
    if magnitude not in (CONTROL_FORCE_NATIVE, *CANDIDATE_FORCE_NATIVE):
        raise ValueError("magnitude is not in the preregistered ladder")
    if not isinstance(transition, int) or transition < 0 or transition >= TRANSITIONS:
        raise ValueError("transition is outside the preregistered duration")
    active = magnitude != 0.0 and START_TRANSITION <= transition < STOP_TRANSITION
    return tuple(magnitude * component if active else 0.0 for component in DIRECTION)


def protocol() -> dict[str, Any]:
    initialization = m7d.protocol()["physical_initialization"]
    return {
        "schema": SCHEMA,
        "status": "NOT_RUN",
        "scientific_run_executed": False,
        "claim_boundary": "physics-only calibration of physical disturbance and mechanical response; no biological or neural-function inference",
        "source_commit": "recorded by the future canonical runner before transitions",
        "physical_initialization": initialization,
        "initialization_identity": "exact frozen corrected M7D/B4 static initialization used by canonical M9",
        "physics": {"flygym": "1.2.1", "mujoco": "3.2.7", "dt_ms": DT_MS,
                    "duration_ms": DURATION_MS, "transitions_per_condition": TRANSITIONS,
                    "states_per_condition": STATES, "post_force_observation_ms": DURATION_MS - STOP_MS},
        "conditions": {"zero_force_control": CONTROL_FORCE_NATIVE,
            "fresh_identical_runtime_per_condition": True,
            "same_initialization_duration_geometry_and_fixed_actuation": True,
            "comparison": "each nonzero candidate minus the single zero-force control at matched timestamps"},
        "perturbation": {"anchor_force_native": ANCHOR_FORCE_NATIVE,
            "ladder_construction": "anchor * 2^(k/2), integer k=-4..4; half-octave refinement of M9A geometric escalation",
            "half_octave_indices": list(LADDER_HALF_OCTAVE_INDICES),
            "candidate_force_magnitudes_native": list(CANDIDATE_FORCE_NATIVE),
            "direction_xyz": list(DIRECTION), "frame": "world",
            "application_body_source": APPLICATION_BODY_SOURCE,
            "application_point": APPLICATION_POINT, "torque_xyz": [0.0, 0.0, 0.0],
            "start_ms_inclusive": START_MS, "stop_ms_exclusive": STOP_MS,
            "start_transition_inclusive": START_TRANSITION,
            "stop_transition_exclusive": STOP_TRANSITION,
            "transition_indices": "5000-5199", "first_possible_affected_state_ms": 500.1,
            "only_force_magnitude_varies": True},
        "fixed_actuation": {"joint_count": 42,
            "commands": "frozen corrected baseline copied at every transition",
            "adhesion": [0, 0, 0, 0, 0, 0]},
        "physical_observables": ["timestamps", "thorax_com_position", "root_orientation_wxyz",
            "body_up_vector", "root_linear_velocity", "root_angular_velocity", "height",
            "42_joint_positions", "six_authoritative_contact_flags_observation_only",
            "six_distal_tarsus_positions", "applied_external_force"],
        "derived_physical_metrics": ["timestamp_aligned_com_displacement_vs_zero_control",
            "quaternion_shortest_arc_orientation_deviation_vs_zero_control",
            "peak_linear_velocity", "peak_angular_velocity",
            "post_perturbation_trajectory_deviation_vs_zero_control",
            "contact_pattern_difference_vs_zero_control", "mechanical_integrity_gate_results"],
        "mechanical_integrity_gates": {"provenance": "numeric limits inherited unchanged from M9A-3 Attempt-3 safety rules",
            "finite": True, "catastrophic_through_ms": 750.0,
            "catastrophic_definition": "height <= 50% initial height, body_up_z <= 0, or absolute root displacement > 1.5 mm",
            "maximum_absolute_root_displacement_mm": 1.5,
            "maximum_absolute_tilt_deg": 60.0,
            "minimum_post_force_observation_ms": 980.0},
        "measurement_gate": {"maximum_continuous_candidate_vs_control_divergence_at_least": 1e-9,
            "provenance": "inherited unchanged from M9A-3 Attempt-3 measurable threshold"},
        "response_score": {"definition": "max(position_mm/0.005, orientation_deg/0.25, distal_tarsus_mm/0.01, 1 if contact differs else 0)",
            "normalizers": "M9A-3 Attempt-3 preregistered meaningful-disturbance thresholds"},
        "selection_rule_preregistered": {
            "target_nonzero_count": TARGET_NONZERO_COUNT,
            "eligibility": "measurement gate and every mechanical integrity gate",
            "anchor": "1.024 must be selected; fail closed if it is ineligible",
            "algorithm": ["sort eligible candidates by (response score, magnitude)",
                "select the lowest-score candidate, the 1.024 anchor, and highest-score candidate",
                "until four are selected, add the unselected candidate maximizing its minimum absolute log2 response-score distance to selected candidates",
                "break equal-distance ties by lower magnitude; return selected magnitudes in ascending magnitude order"],
            "failure": "fail closed unless at least four eligible candidates and four distinct response scores exist"},
        "contact_semantics": "physical observation only; never encoded or delivered",
        "execution_absence": {"male_cns_constructed": False, "neural_transitions": 0,
            "sensory_encoding_or_delivery_count": 0, "neural_motor_decode_or_application_count": 0,
            "controllers": False, "reward_or_rl": False, "gait_or_reference_controller": False,
            "contact_used_as_sensory_input": False},
        "future_artifacts": {"raw": "m10a_raw.npz", "report": REPORT_PATH.name,
            "manifest": MANIFEST_PATH.name, "raw_sha256_in_manifest": True,
            "selected_force_series_in_report": True},
    }


def validate_protocol(value: Mapping[str, Any]) -> None:
    expected = protocol()
    checks = (value == expected,
        tuple(value["physical_initialization"][key] for key in ("spawn_pos", "spawn_orientation")) ==
        (list(m7d.SPAWN_POS), list(m7d.SPAWN_ORIENTATION)),
        value["perturbation"]["anchor_force_native"] in value["perturbation"]["candidate_force_magnitudes_native"],
        not any(value["execution_absence"][key] for key in ("male_cns_constructed", "controllers", "reward_or_rl", "gait_or_reference_controller")))
    if not all(checks):
        raise RuntimeError("M10A preregistered protocol mismatch")


def _eligible(row: Mapping[str, Any]) -> bool:
    if not set(row).issubset(PHYSICAL_METRIC_KEYS):
        raise RuntimeError("selection input contains a nonphysical or unregistered metric")
    required = PHYSICAL_METRIC_KEYS
    if not required.issubset(row):
        raise RuntimeError(f"selection input lacks physical metrics: {sorted(required - set(row))}")
    return (bool(row["finite"]) and not bool(row["catastrophic_through_750ms"])
        and float(row["max_absolute_root_displacement_mm"]) <= 1.5
        and float(row["max_absolute_tilt_deg"]) <= 60.0
        and float(row["post_force_observation_ms"]) >= 980.0
        and float(row["max_continuous_divergence"]) >= 1e-9)


def response_score(row: Mapping[str, Any]) -> float:
    """Reduce only preregistered physical deviations to a coverage coordinate."""
    return max(float(row["max_root_position_divergence_mm"]) / 0.005,
        float(row["max_orientation_divergence_deg"]) / 0.25,
        float(row["max_distal_tarsus_divergence_mm"]) / 0.01,
        1.0 if bool(row["contact_pattern_diverged"]) else 0.0)


def select_force_series(rows: Sequence[Mapping[str, Any]]) -> tuple[float, ...] | str:
    """Apply the frozen physical-only, deterministic response-coverage rule."""
    import math
    if tuple(float(row.get("magnitude_native", -1)) for row in rows) != CANDIDATE_FORCE_NATIVE:
        raise RuntimeError("results do not match the ordered preregistered ladder")
    eligible = [(response_score(row), float(row["magnitude_native"])) for row in rows if _eligible(row)]
    anchor = next(row for row in rows if row["magnitude_native"] == ANCHOR_FORCE_NATIVE)
    if not _eligible(anchor):
        return ANCHOR_FAILURE
    eligible.sort()
    if len(eligible) < TARGET_NONZERO_COUNT or len({score for score, _ in eligible}) < TARGET_NONZERO_COUNT:
        return NO_SELECTION
    selected = {eligible[0][1], ANCHOR_FORCE_NATIVE, eligible[-1][1]}
    while len(selected) < TARGET_NONZERO_COUNT:
        choices = []
        for score, magnitude in eligible:
            if magnitude in selected or score <= 0:
                continue
            distance = min(abs(math.log2(score) - math.log2(other_score))
                for other_score, other_magnitude in eligible if other_magnitude in selected and other_score > 0)
            choices.append((distance, -magnitude, magnitude))
        if not choices:
            return NO_SELECTION
        selected.add(max(choices)[2])
    return tuple(sorted(selected))


def preflight() -> dict[str, Any]:
    """Validate the frozen document and empty namespace without a runtime."""
    value = protocol()
    validate_protocol(value)
    allowed = {PREREGISTRATION_PATH.resolve()}
    existing = {path.resolve() for path in OUTPUT_DIR.iterdir()} if OUTPUT_DIR.exists() else set()
    if existing - allowed:
        raise FileExistsError("M10A namespace contains scientific execution evidence")
    return {"schema": SCHEMA, "status": "PREFLIGHT_PASS", "protocol": value,
        "physics_runtime_constructed": False, "physics_transitions": 0,
        "male_cns_constructed": False, "neural_transitions": 0,
        "sensory_encoding_or_delivery_count": 0,
        "neural_motor_decode_or_application_count": 0,
        "canonical_calibration_executed": False}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight:
        result = preflight()
    else:
        from . import _windows_m10a_physics_only_adapter as adapter
        result = adapter.run_windows()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
