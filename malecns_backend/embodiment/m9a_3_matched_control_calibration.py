"""Frozen M9A-3 matched-control, physics-only perturbation protocol.

Importing this module is inert.  In particular, it neither imports a neural
runtime nor constructs or advances physics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import m7d_corrected_spontaneous as m7d

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "interface_output" / "m9a_3_matched_control_calibration"
REPORT_PATH = OUTPUT_DIR / "m9a_3_report.json"
MANIFEST_PATH = OUTPUT_DIR / "m9a_3_manifest.json"
PREREGISTRATION_PATH = OUTPUT_DIR / "m9a_3_preregistration.json"
SCHEMA = "M9A-3-MATCHED-CONTROL-PHYSICS-ONLY-CALIBRATION.1"

CANDIDATE_FORCE_NATIVE = (0.256, 0.512, 1.024, 2.048)
DIRECTION = (0.0, 1.0, 0.0)
APPLICATION_BODY_SOURCE = "Thorax"
START_MS, STOP_MS, OBSERVE_MS = 500.0, 520.0, 1500.0
DT_MS, TRANSITIONS, STATES = m7d.PHYSICS_DT_MS, 15_000, 15_001

# Values are intentionally duplicated here rather than trusted from mutable
# manifests. Text/source evidence has canonical-LF identities; binary evidence
# is verified as exact bytes. Every entry must be explicitly classified below.
HISTORICAL = {
    "m9a/candidate_0.0001_raw.npz": (3075886, "71b4c0150cb1296ffcffdab1bc600d725995f302cc1da25dd53fee88a701de41"),
    "m9a/candidate_0.0002_raw.npz": (3075658, "1bebe255c785ea6468a5e6bad2f4a86dca3575247ca0aecc9108942ad9b0a241"),
    "m9a/candidate_0.0004_raw.npz": (3076169, "f97e3d3f67dd70835592ab27458e237bc4b2ac331c61cee5ac12b8c602077075"),
    "m9a/candidate_0.0008_raw.npz": (3076391, "12bd71526456f844f66ac64fc58e84c7799a776432c1eec31b3aab763e4d45b7"),
    "m9a/m9a_preregistration.json": (5386, "7babc0d657bd74c8f1de596644ac4422a317f3a9f74729eb588fd0c76fe54408"),
    "m9a_2/candidate_0.002000_raw.npz": (3076871, "1c840a69a7f9b065b5957c4e8e338da80046ef4dec0ab068aedd7fef406069ad"),
    "m9a_2/candidate_0.008000_raw.npz": (3077824, "d60a40669c7f4c4df3a97b1725c31b917560bf9e9c2b4f3fb8d9929b62ecf80b"),
    "m9a_2/candidate_0.032000_raw.npz": (3080754, "aace3bfc4b79c50ef3f7b74a7111a1654edf751c5085e2fe8e4d53746de74cd1"),
    "m9a_2/candidate_0.128000_raw.npz": (3086369, "3b6f6f4027fda98608875543b5f0d4ca9efe3e7c75f3b7028a769ec2bbe0411e"),
    "m9a_2/m9a_2_preregistration.json": (4877, "b724b8941a3055141d2203663c9940f01acf4a93e3e2ba387470370f3083d116"),
    "forensics/README.md": (1235, "8ce08f4ae2770d6ad8de0cb9dc8870e08caa7227cb9b661b6680ffa0d55569a4"),
    "forensics/m9a_2_postrun_forensics.py": (12776, "53a13908044fcbee0d6ec609a5fb401d51973266a3817ae1d8f27dd50a98eef5"),
}

CANONICAL_LF_TEXT_EVIDENCE = frozenset({
    "m9a/m9a_preregistration.json",
    "m9a_2/m9a_2_preregistration.json",
    "forensics/README.md",
    "forensics/m9a_2_postrun_forensics.py",
})

EXACT_BYTE_BINARY_EVIDENCE = frozenset({
    "m9a/candidate_0.0001_raw.npz",
    "m9a/candidate_0.0002_raw.npz",
    "m9a/candidate_0.0004_raw.npz",
    "m9a/candidate_0.0008_raw.npz",
    "m9a_2/candidate_0.002000_raw.npz",
    "m9a_2/candidate_0.008000_raw.npz",
    "m9a_2/candidate_0.032000_raw.npz",
    "m9a_2/candidate_0.128000_raw.npz",
})

assert CANONICAL_LF_TEXT_EVIDENCE | EXACT_BYTE_BINARY_EVIDENCE == set(HISTORICAL)
assert not CANONICAL_LF_TEXT_EVIDENCE & EXACT_BYTE_BINARY_EVIDENCE


def _historical_path(key: str) -> Path:
    prefix, name = key.split("/", 1)
    if prefix == "m9a": return HERE / "interface_output/m9a_perturbation_calibration" / name
    if prefix == "m9a_2": return HERE / "interface_output/m9a_2_perturbation_calibration" / name
    return (HERE / "interface_output/m9a_2_postrun_forensics" / name
            if name == "README.md" else HERE / name)


def _canonical_historical_bytes(key: str, raw: bytes) -> bytes:
    """Return the explicit byte representation frozen for historical evidence."""
    if key in EXACT_BYTE_BINARY_EVIDENCE:
        return raw
    if key not in CANONICAL_LF_TEXT_EVIDENCE:
        raise RuntimeError(f"unclassified historical evidence: {key}")
    canonical = raw.replace(b"\r\n", b"\n")
    if b"\r" in canonical:
        raise RuntimeError(f"invalid historical line endings: {key}")
    return canonical


def _verify_historical_file(key: str, path: Path, size: int, digest: str) -> None:
    canonical = _canonical_historical_bytes(key, path.read_bytes())
    if len(canonical) != size or hashlib.sha256(canonical).hexdigest() != digest:
        raise RuntimeError(f"immutable historical evidence mismatch: {key}")


def verify_historical_evidence() -> None:
    for key, (size, digest) in HISTORICAL.items():
        _verify_historical_file(key, _historical_path(key), size, digest)


def force_at(time_ms: float, magnitude: float, condition: str) -> tuple[float, float, float]:
    if condition not in ("P", "C"): raise ValueError("condition must be P or C")
    active = condition == "P" and START_MS <= time_ms < STOP_MS
    return tuple(magnitude * x if active else 0.0 for x in DIRECTION)


def protocol() -> dict[str, Any]:
    inherited = m7d.protocol()
    return {
        "schema": SCHEMA, "status": "NOT_RUN", "experiment_namespace": "M9A-3",
        "claim_boundary": "physical perturbation calibration only; not balance, neural stabilization, reflexes, gait, biological function, MaleCNS, or M9B",
        "male_cns": {"constructed": False, "neural_transitions": 0},
        "physics": {"flygym": "1.2.1", "mujoco": "3.2.7", "dt_ms": DT_MS,
                    "transitions_per_condition": TRANSITIONS, "states_per_condition": STATES,
                    "observation_duration_ms": OBSERVE_MS},
        "physical_initialization": inherited["physical_initialization"],
        "fixed_actuation": {"joint_count": 42, "commands": "frozen corrected M7D/B4 baseline copied at every transition",
                            "adhesion": [0, 0, 0, 0, 0, 0]},
        "matched_pair": {"conditions": ["P", "C"], "fresh_identical_runtime_per_condition": True,
                         "exact_pre_force_equivalence_required": True,
                         "comparison": "timestamp-aligned P minus C; never own-pre-state displacement"},
        "perturbation": {"mechanism": "MuJoCo data.xfrc_applied direct Cartesian force",
            "application_body_source": APPLICATION_BODY_SOURCE,
            "compiled_identity_resolution": "unique exact terminal slash-delimited component",
            "application_point": "body center of mass", "torque_xyz": [0.0, 0.0, 0.0],
            "frame": "world", "direction_xyz": list(DIRECTION),
            "start_ms_inclusive": START_MS, "stop_ms_exclusive": STOP_MS,
            "candidate_force_magnitudes_native": list(CANDIDATE_FORCE_NATIVE),
            "ladder_rationale": "factor-two geometric escalation above 0.128; under local proportional extrapolation, its 0.000411825-mm maximum P-vs-0.0001 position signal predicts approximately 0.000824, 0.001647, 0.003295, and 0.006589 mm; outcomes cannot alter the ladder"},
        "disturbance_metrics": ["root_position_vector_and_euclidean", "root_linear_velocity_vector_and_euclidean",
            "quaternion_shortest_arc_angle_deg", "body_up_angle_deg", "angular_velocity_vector_and_euclidean",
            "authoritative_six_leg_contact_xor", "per_leg_distal_tarsus_euclidean", "first_physical_divergence_ms"],
        "selection_rule_preregistered": {
            "choice": "lowest qualifying magnitude in frozen order; fail closed if none",
            "measurable": {"post_500ms_any_continuous_divergence_at_least": 1e-9},
            "meaningful_posture_any_of": {"authoritative_contact_pattern_divergence": True,
                "maximum_root_position_divergence_mm_at_least": 0.005,
                "maximum_orientation_divergence_deg_at_least": 0.25,
                "maximum_any_distal_tarsus_divergence_mm_at_least": 0.01},
            "safety": {"finite_both": True, "no_fall_launch_or_rollover_through_ms": 750.0,
                "maximum_root_position_divergence_mm": 0.5, "maximum_orientation_divergence_deg": 30.0,
                "maximum_root_linear_velocity_divergence": 5.0,
                "absolute_root_displacement_from_initial_mm_each_condition": 1.5,
                "absolute_tilt_deg_each_condition": 60.0, "absolute_root_linear_speed_each_condition": 10.0,
                "minimum_post_force_observation_ms": 980.0},
            "passive_return_required": False,
            "return_rationale": "the future causal question is whether enabled neural feedback changes recovery; requiring >=25% passive return would select on an irrelevant property and can exclude a safe useful disturbance"},
        "telemetry": ["complete_physical_timestamps", "root_pose", "root_linear_and_angular_velocity",
            "six_authoritative_contacts", "six_distal_tarsus_positions", "applied_external_force",
            "fixed_actuator_commands_and_sha256", "body_id_name_and_source", "environment_and_model_provenance"],
        "explicit_absences": {name: False for name in ("sensory_encoding", "mapped_motor_decoding", "gait_or_cpg",
            "stabilization_controller", "reward_rl_ai", "reference_trajectory", "adaptive_force_tuning", "hidden_assistance")},
    }


def validate_protocol(value: Mapping[str, Any]) -> None:
    verify_historical_evidence()
    if (value != protocol() or tuple(value["perturbation"]["candidate_force_magnitudes_native"]) != CANDIDATE_FORCE_NATIVE
            or value["physical_initialization"] != m7d.protocol()["physical_initialization"]):
        raise RuntimeError("M9A-3 frozen protocol mismatch")


def choose_candidate(rows: Sequence[Mapping[str, Any]]) -> float:
    if tuple(float(r["magnitude_native"]) for r in rows) != CANDIDATE_FORCE_NATIVE:
        raise RuntimeError("results do not match frozen ladder")
    for r in rows:
        meaningful = (r["contact_pattern_diverged"] or r["max_root_position_divergence_mm"] >= .005
            or r["max_orientation_divergence_deg"] >= .25 or r["max_distal_tarsus_divergence_mm"] >= .01)
        safe = (r["finite_both"] and not r["catastrophic_through_750ms"]
            and r["max_root_position_divergence_mm"] <= .5 and r["max_orientation_divergence_deg"] <= 30
            and r["max_root_linear_velocity_divergence"] <= 5
            and r["max_absolute_root_displacement_mm"] <= 1.5 and r["max_absolute_tilt_deg"] <= 60
            and r["max_absolute_root_linear_speed"] <= 10 and r["post_force_observation_ms"] >= 980)
        if r["max_continuous_divergence"] >= 1e-9 and meaningful and safe: return float(r["magnitude_native"])
    raise RuntimeError("no preregistered candidate qualifies")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--windows-preflight", action="store_true")
    modes.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv); validate_protocol(protocol())
    from . import _windows_m9a_3_matched_control_adapter as adapter
    result = adapter.windows_preflight() if args.windows_preflight else adapter.run_windows()
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
