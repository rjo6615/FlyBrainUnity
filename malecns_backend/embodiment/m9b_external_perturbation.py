"""M9B preregistration: frozen MaleCNS embodiment under calibrated force.

Importing this module is a zero-transition operation.  The four-condition
factorial was selected before observation because the M8 runner already admits
orthogonal motor gating and a transition-indexed external-force hook without
changing the embodiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import m7d_corrected_spontaneous as m7d

HERE = Path(__file__).resolve().parent
CALIBRATION_DIR = HERE / "interface_output/m9a_3_matched_control_calibration_attempt_3"
CALIBRATION_FILES = {
    "m9a_3_attempt_3_manifest.json": (2680, "4b39440d1322379064f4655bf86a83f5be33f160ed40c32779f59bd505423226"),
    "m9a_3_attempt_3_report.json": (5996715, "05a8c63766fd5e74ec5b241a3977e8215356a676845281a9fccad5d9dfa61d22"),
    "m9a_3_attempt_3_preregistration.json": (5495, "1adca0c26dd2e70eb5c2ea697bf01be22ccb9d7ce64f198af8bcc1d436bda366"),
}
# The three JSON files are Git-managed text.  Their frozen identities are the
# LF bytes stored in Git and must survive checkout newline materialization.
# Scientific NPZ results remain exact-byte locked below.  Keep this
# classification exhaustive and fail closed rather than inferring from suffix.
CANONICAL_LF_TEXT_ARTIFACTS = frozenset({
    "m9a_3_attempt_3_manifest.json",
    "m9a_3_attempt_3_report.json",
    "m9a_3_attempt_3_preregistration.json",
})
EXACT_BYTE_BINARY_ARTIFACTS = frozenset()
OUTPUT_DIR = HERE / "interface_output/m9b_external_perturbation"
RAW_PATH = OUTPUT_DIR / "m9b_raw.npz"
REPORT_PATH = OUTPUT_DIR / "m9b_report.json"
MANIFEST_PATH = OUTPUT_DIR / "m9b_manifest.json"
PREREGISTRATION_PATH = OUTPUT_DIR / "m9b_preregistration.json"
SCHEMA = "M9B-MALECNS-CALIBRATED-EXTERNAL-PERTURBATION.1"
CALIBRATION_SCHEMA = "M9A-3-MATCHED-CONTROL-PHYSICS-ONLY-CALIBRATION.3"
CONDITIONS = ("A_P", "A_C", "B_P", "B_C")
PERTURBED = frozenset(("A_P", "B_P"))
MOTOR_ENABLED = frozenset(("A_P", "A_C"))
MAGNITUDE_NATIVE = 1.024
DIRECTION = (0.0, 1.0, 0.0)
START_TRANSITION, STOP_TRANSITION = 5000, 5200
DURATION_MS, PHYSICS_DT_MS, NEURAL_DT_MS = 1500.0, 0.1, 0.5
PHYSICS_TRANSITIONS, PHYSICS_STATES, NEURAL_UPDATES = 15000, 15001, 3000
MOTOR_INTERFACES = (
    ("joint_LFTibia", 5, 1), ("joint_LMTibia", 12, 1), ("joint_LHTibia", 19, 1),
    ("joint_RFTibia", 26, 1), ("joint_RMTibia", 33, 1), ("joint_RHTibia", 40, 1),
    ("joint_LFFemur", 3, -1), ("joint_LMFemur", 10, -1), ("joint_LHFemur", 17, -1),
    ("joint_RMFemur", 31, -1), ("joint_RHFemur", 38, -1),
)
SENSORY_INTERFACES = tuple(f"joint_{leg}Tibia" for leg in ("LF", "LM", "LH", "RF", "RM", "RH"))
CLASSIFICATIONS = (
    "M9B_COMPLETE_NO_DETECTABLE_NEURAL_MOTOR_EFFECT_UNDER_PERTURBATION",
    "M9B_NEURAL_MOTOR_CAUSALLY_ALTERS_TRAJECTORY_UNDER_PERTURBATION",
    "M9B_PERTURBATION_RESPONSE_DEPENDS_ON_NEURAL_MOTOR_ENABLEMENT",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_provenance_bytes(name: str, raw: bytes) -> bytes:
    """Apply the explicitly classified representation policy for an artifact."""
    if name in EXACT_BYTE_BINARY_ARTIFACTS:
        return raw
    if name in CANONICAL_LF_TEXT_ARTIFACTS:
        # Replace CRLF first: replacing CR first would manufacture CRCRLF.
        return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    raise RuntimeError(f"unclassified M9A Attempt-3 provenance artifact: {name}")


def _exact_file_identity(path: Path, size: int, digest: str) -> bool:
    """Verify an immutable binary without interpreting or normalizing it."""
    return path.is_file() and path.stat().st_size == size and _sha256(path) == digest


def verify_m9a_provenance(directory: Path = CALIBRATION_DIR, *,
                          immutable_directory: Path | None = None) -> dict[str, Any]:
    """Verify canonical text, immutable NPZ inputs, and selection semantics.

    ``immutable_directory`` exists so tests can copy and mutate only the small
    text artifacts without symlinks or duplicate NPZ files.  Production omits
    it, so every artifact is necessarily verified in the one canonical tree.
    """
    raw_directory = directory if immutable_directory is None else immutable_directory
    classified = CANONICAL_LF_TEXT_ARTIFACTS | EXACT_BYTE_BINARY_ARTIFACTS
    if classified != set(CALIBRATION_FILES) or CANONICAL_LF_TEXT_ARTIFACTS & EXACT_BYTE_BINARY_ARTIFACTS:
        raise RuntimeError("M9A Attempt-3 provenance artifact classification is not exhaustive")
    evidence = {}
    for name, (size, digest) in CALIBRATION_FILES.items():
        path = directory / name
        canonical = _canonical_provenance_bytes(name, path.read_bytes()) if path.is_file() else b""
        if not path.is_file() or len(canonical) != size or hashlib.sha256(canonical).hexdigest() != digest:
            raise RuntimeError(f"M9A Attempt-3 canonical provenance mismatch: {name}")
        evidence[name] = {"byte_size": size, "sha256": digest}
    manifest = json.loads((directory / "m9a_3_attempt_3_manifest.json").read_text(encoding="utf-8"))
    report = json.loads((directory / "m9a_3_attempt_3_report.json").read_text(encoding="utf-8"))
    prereg = json.loads((directory / "m9a_3_attempt_3_preregistration.json").read_text(encoding="utf-8"))
    raw_entries = manifest.get("raw", ())
    raw_names = [str(x["path"]).replace("\\", "/").rsplit("/", 1)[-1] for x in raw_entries]
    raw_ok = len(raw_entries) == 8 and all(
        _exact_file_identity(raw_directory / name, x["byte_size"], x["sha256"])
        for x, name in zip(raw_entries, raw_names))
    manifest_report = manifest.get("report", {})
    perturb = prereg.get("perturbation", {})
    checks = (manifest.get("schema") == CALIBRATION_SCHEMA, manifest.get("status") == "COMPLETE",
              report.get("schema") == CALIBRATION_SCHEMA, report.get("status") == "COMPLETE",
              manifest_report.get("byte_size") == CALIBRATION_FILES["m9a_3_attempt_3_report.json"][0],
              manifest_report.get("sha256") == CALIBRATION_FILES["m9a_3_attempt_3_report.json"][1],
              report.get("selected_force_magnitude_native") == MAGNITUDE_NATIVE,
              report.get("protocol", {}).get("selection_rule_preregistered", {}).get("choice", "").startswith("lowest qualifying"),
              perturb.get("direction_xyz") == list(DIRECTION), perturb.get("frame") == "world",
              perturb.get("application_body_source") == "Thorax",
              perturb.get("application_point") == "body center of mass",
              perturb.get("torque_xyz") == [0.0, 0.0, 0.0],
              perturb.get("start_ms_inclusive") == 500.0, perturb.get("stop_ms_exclusive") == 520.0,
              prereg.get("physics", {}).get("dt_ms") == PHYSICS_DT_MS, raw_ok)
    if not all(checks):
        raise RuntimeError("M9A Attempt-3 scientific provenance is incompatible with M9B")
    return evidence


def force_at_transition(condition: str, transition: int) -> tuple[float, float, float]:
    if condition not in CONDITIONS or not isinstance(transition, int):
        raise ValueError("canonical condition and integer transition required")
    active = condition in PERTURBED and START_TRANSITION <= transition < STOP_TRANSITION
    return tuple(MAGNITUDE_NATIVE * component if active else 0.0 for component in DIRECTION)


def gate_contributions(values: Mapping[str, float], condition: str,
                       admitted: Sequence[str]) -> dict[str, float]:
    if condition not in CONDITIONS or tuple(values) != tuple(admitted) or tuple(admitted) != m7d.ADMITTED_MOTOR:
        raise RuntimeError("M9B motor inventory or condition mismatch")
    return {name: float(values[name]) if condition in MOTOR_ENABLED else 0.0 for name in admitted}


def protocol() -> dict[str, Any]:
    inherited = m7d.protocol()
    return {"schema": SCHEMA, "status": "NOT_RUN", "scientific_run_executed": False,
        "design": {"type": "preregistered_2x2_factorial", "conditions": list(CONDITIONS),
            "factors": ["neural_motor_enabled", "external_force_present"],
            "rationale": "orthogonal frozen interventions are supported without changing embodiment semantics; enables perturbation-specific difference-in-differences"},
        "seed": m7d.SEED, "duration_ms": DURATION_MS, "physics_dt_ms": PHYSICS_DT_MS,
        "neural_dt_ms": NEURAL_DT_MS, "physics_transitions_per_condition": PHYSICS_TRANSITIONS,
        "physics_states_per_condition": PHYSICS_STATES, "neural_updates_per_condition": NEURAL_UPDATES,
        "calibration": {"schema": CALIBRATION_SCHEMA, "attempt": 3, "status": "COMPLETE",
            "selected_force_magnitude_native": MAGNITUDE_NATIVE, "selection": "preregistered lowest qualifying candidate"},
        "perturbation": {"direction_xyz": list(DIRECTION), "frame": "world",
            "application_body_source": "Thorax", "application_point": "authoritative body center of mass",
            "torque_xyz": [0.0, 0.0, 0.0], "start_transition_inclusive": START_TRANSITION,
            "stop_transition_exclusive": STOP_TRANSITION, "transition_indices": "5000-5199",
            "outgoing_transition_count": 200, "integer_index_scheduling": True},
        "physical_initialization": inherited["physical_initialization"],
        "admitted_motor_interfaces": [{"name": n, "action_index": i, "coordinate_sign": s} for n, i, s in MOTOR_INTERFACES],
        "admitted_sensory_interfaces": list(SENSORY_INTERFACES),
        "disabled_control": {"zero_point": "immediately before physical application",
            "pre_zero_decoder_computed": True, "brain_active": True, "sensory_active": True,
            "neural_updates_active": True, "observer_active": True, "decoder_active": True},
        "baseline": {"interval_ms": [0, 500], "record_each_condition_independently": True,
            "exact_equivalence_required_only_at_state_zero": True, "pre_force_physical_equality_required": False},
        "telemetry": {"physics_cadence_ms": PHYSICS_DT_MS, "neural_cadence_ms": NEURAL_DT_MS,
            "physics": ["timestamps", "root_position", "root_quaternion", "body_up_vector", "root_linear_velocity",
                "root_angular_velocity", "42_joint_positions", "42_actuator_commands", "11_neural_contribution_pre_application",
                "six_authoritative_contact_flags", "six_distal_tarsus_positions", "external_force_vector", "fall_rollover"],
            "neural": ["timestamps", "aggregate_cns_state_and_spikes", "six_tibial_proprioceptive_encoded_signals",
                "delivered_sensory_drive", "mapped_motor_population_activity", "11_motor_observer_states",
                "11_decoder_outputs", "disabled_pre_zero_motor_vector", "disabled_post_zero_motor_vector"],
            "channel_identity_provenance": True, "causal_milestone_ordering": True},
        "analyses": ["force_onset_offset_integrity", "first_physical_effect", "root_position_orientation_velocity",
            "distal_tarsus_trajectories", "contact_pattern_evolution", "fall_rollover", "post_force_980ms",
            "proprioceptive_encoding_and_delivered_drive", "CNS_activity", "motor_observer_decoder_and_output",
            "A_P_minus_A_C", "B_P_minus_B_C", "difference_in_differences", "analogous_valid_sensory_CNS_motor_contrasts"],
        "classifications": list(CLASSIFICATIONS),
        "claim_boundary": "descriptive trajectories and conservative causal contrasts only; post-500ms A/B divergence alone is not perturbation attribution",
        "hidden_assistance": inherited["hidden_assistance"], "contact_is_neural_input": False,
        "decoder_semantics": "exact frozen M7D/M8 filter, gain, saturation, slew, and bounds; no retuning"}


def validate_protocol(value: Mapping[str, Any]) -> None:
    verify_m9a_provenance()
    expected_names = tuple(x["name"] for x in value.get("admitted_motor_interfaces", ()))
    expected_rows = tuple((x["name"], x["action_index"], x["coordinate_sign"]) for x in value.get("admitted_motor_interfaces", ()))
    checks = (value == protocol(), expected_names == m7d.ADMITTED_MOTOR, expected_rows == MOTOR_INTERFACES,
              tuple(value.get("admitted_sensory_interfaces", ())) == SENSORY_INTERFACES,
              value.get("physical_initialization") == m7d.protocol()["physical_initialization"],
              not any(value.get("hidden_assistance", {}).values()), not value.get("contact_is_neural_input"))
    if not all(checks): raise RuntimeError("M9B frozen protocol mismatch")


def output_available() -> bool:
    return not any(path.exists() for path in (RAW_PATH, REPORT_PATH, MANIFEST_PATH))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--windows-preflight", action="store_true")
    modes.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv); validate_protocol(protocol())
    if not output_available(): raise FileExistsError("canonical M9B output namespace is not clean")
    from . import _windows_m9b_external_perturbation_adapter as adapter
    result = adapter.windows_preflight() if args.windows_preflight else adapter.run_windows()
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
