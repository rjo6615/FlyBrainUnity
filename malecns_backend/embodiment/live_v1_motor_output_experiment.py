"""Experiment 3: guarded Live Fly v1 motor-output observability assay.

This module is deliberately inert.  Import, default invocation, ``--help``, and
``--validate`` cannot construct either runtime.  Scientific execution remains
unreachable until a separately reviewed authorization artifact is frozen in a
future change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "interface_output" / "live_v1_motor_output_experiment"
DESIGN_PATH = OUTPUT_DIR / "implementation_design.json"
AUTHORIZATION_PATH = OUTPUT_DIR / "prospective_execution_authorization.json"

FROZEN_PRIOR_COMMIT = "ea81974f59ce9a67a382c20d605b385765f10b33"
PRIOR_OBJECT_AVAILABLE_AT_IMPLEMENTATION = False
NEURAL_DT_MS = 0.5
PHYSICS_DT_MS = 0.1
ACTION_COUNT = 42

# Exact Live Fly v1 order used by the existing live runner.  This is an
# inventory, not a newly admitted set of populations.
MOTOR_CHANNELS = (
    ("joint_LFTibia", 5, 1), ("joint_LMTibia", 12, 1),
    ("joint_LHTibia", 19, 1), ("joint_RFTibia", 26, 1),
    ("joint_RMTibia", 33, 1), ("joint_RHTibia", 40, 1),
    ("joint_LFFemur", 3, -1), ("joint_LMFemur", 10, -1),
    ("joint_LHFemur", 17, -1), ("joint_RMFemur", 31, -1),
    ("joint_RHFemur", 38, -1),
)
CONDITIONS = ("live_v1_enabled", "matched_control_final_11_zeroed")
CLASSIFICATIONS = {
    "activity": ("OBSERVED_ACTIVE", "OBSERVED_INACTIVE"),
    "decoder": ("DECODER_OUTPUT", "NO_DECODER_OUTPUT"),
    "physics": ("PHYSICALLY_DIVERGENT", "NOT_PHYSICALLY_DIVERGENT"),
}

NEURAL_FIELDS = (
    "neural_transition_index", "neural_time_ms", "per_neuron_spike_increments",
    "per_neuron_filtered_rate_hz", "population_mean_filtered_rate_hz",
    "pooled_positive_rate_hz", "pooled_negative_rate_hz",
    "positive_activation", "negative_activation", "raw_signed_contribution_rad",
    "final_contribution_rad", "range_clamped", "slew_limited",
    "commanded_joint_targets", "encoded_sensory_rates",
    "scheduled_sensory_candidate_events", "delivered_external_sensory_events",
)
PHYSICS_FIELDS = (
    "physics_transition_index", "physics_time_ms", "commanded_joint_targets",
    "measured_joint_positions", "qpos", "qvel", "root_position",
    "root_quaternion", "contact_information",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def design() -> dict[str, Any]:
    """Return the frozen, non-executing implementation contract."""
    return {
        "schema": "LIVE-V1-MOTOR-OUTPUT-EXPERIMENT-DESIGN.1",
        "experiment": "Live Fly v1 11-channel motor-output observability assay",
        "status": "IMPLEMENTED_NOT_AUTHORIZED",
        "prior_work": {"commit": FROZEN_PRIOR_COMMIT,
                       "object_available_at_implementation": False,
                       "ancestry_verified": False},
        "conditions": list(CONDITIONS),
        "motor_channels": [{"joint": n, "action_index": i, "coordinate_sign": s}
                           for n, i, s in MOTOR_CHANNELS],
        "timing": {"neural_dt_ms": NEURAL_DT_MS, "physics_dt_ms": PHYSICS_DT_MS,
                   "physics_per_neural_transition": 5},
        "observation": {"neural_fields": list(NEURAL_FIELDS),
                        "physics_fields": list(PHYSICS_FIELDS),
                        "state_mutation_permitted": False},
        "classifications": CLASSIFICATIONS,
        "execution_authorization": {"required": True, "present": False,
            "artifact": AUTHORIZATION_PATH.name,
            "rule": "must be created prospectively in a separate reviewed change"},
        "prohibitions": ["new intervention", "decoder change", "population change",
            "sensory change", "dynamics change", "physics change", "Unity change",
            "TCP transport change", "scientific interpretation beyond observation"],
    }


def verify_design(path: Path = DESIGN_PATH) -> str:
    """Fail closed unless the committed design is byte/content identical."""
    if not path.is_file():
        raise RuntimeError("Experiment 3 design artifact is missing")
    payload = path.read_bytes()
    # Normalize tuples used by the Python API to their JSON array form.
    if json.loads(payload) != json.loads(canonical_json(design())):
        raise RuntimeError("Experiment 3 design artifact mismatch")
    return hashlib.sha256(payload).hexdigest()


def assert_execution_authorized(path: Path = AUTHORIZATION_PATH) -> None:
    """Unconditionally fail closed in this implementation revision."""
    # Merely placing a file at the prospective path must never authorize a run.
    # A future reviewed change must add a frozen identity and verifier.
    del path
    raise PermissionError("Experiment 3 scientific execution is not authorized")


def validate_neural_record(record: Mapping[str, Any], previous_index: int | None = None) -> None:
    if tuple(record) != NEURAL_FIELDS:
        raise ValueError("neural telemetry field inventory/order mismatch")
    index = record["neural_transition_index"]
    if not isinstance(index, int) or index < 1 or (previous_index is not None and index != previous_index + 1):
        raise ValueError("non-contiguous neural transition index")
    if record["neural_time_ms"] != index * NEURAL_DT_MS:
        raise ValueError("neural timestamp/cadence mismatch")
    if len(record["commanded_joint_targets"]) != ACTION_COUNT:
        raise ValueError("neural target vector is not 42 entries")


def validate_physics_record(record: Mapping[str, Any], previous_index: int | None = None) -> None:
    if tuple(record) != PHYSICS_FIELDS:
        raise ValueError("physics telemetry field inventory/order mismatch")
    index = record["physics_transition_index"]
    if not isinstance(index, int) or index < 1 or (previous_index is not None and index != previous_index + 1):
        raise ValueError("non-contiguous physics transition index")
    if abs(record["physics_time_ms"] - index * PHYSICS_DT_MS) > 1e-12:
        raise ValueError("physics timestamp/cadence mismatch")
    if len(record["commanded_joint_targets"]) != ACTION_COUNT or len(record["measured_joint_positions"]) != ACTION_COUNT:
        raise ValueError("physics joint vector is not 42 entries")


def result_schema() -> dict[str, Any]:
    """Machine-checkable shape of the future report (no invented results)."""
    return {"schema": "LIVE-V1-MOTOR-OUTPUT-RESULT.1", "status": "NOT_RUN",
        "conditions": list(CONDITIONS), "channels": [n for n, _, _ in MOTOR_CHANNELS],
        "channel_metrics": ["first_motor_population_activity_time_ms",
            "first_nonzero_decoder_output_time_ms", "first_physical_divergence_time_ms",
            "spike_increment_distribution", "filtered_rate_distribution",
            "positive_negative_directional_balance", "raw_contribution_distribution",
            "final_contribution_distribution", "nonzero_output_duty_fraction",
            "range_clamp_occupancy", "slew_limit_occupancy",
            "command_to_measured_response_lag_ms", "enabled_control_physical_divergence"],
        "classifications": CLASSIFICATIONS,
        "baseline_only_joint_count": 31, "passive_motion_report": None}


def readiness() -> dict[str, Any]:
    """Validate static contracts only; perform exactly zero transitions."""
    digest = verify_design()
    return {"schema": "LIVE-V1-MOTOR-OUTPUT-READINESS.1",
        "status": "NOT_READY_UNAUTHORIZED", "design_sha256": digest,
        "scientific_execution_authorized": False, "scientific_run_executed": False,
        "neural_transitions": 0, "physics_transitions": 0,
        "channel_count": len(MOTOR_CHANNELS), "action_count": ACTION_COUNT,
        "existing_runtime_hook_added": True,
        "telemetry_contract_implemented": True}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true",
                        help="validate static readiness; performs zero transitions")
    parser.add_argument("--execute", action="store_true",
                        help="reserved; always unauthorized in this revision")
    args = parser.parse_args(argv)
    if args.execute:
        assert_execution_authorized()
    if args.validate:
        print(canonical_json(readiness()), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
