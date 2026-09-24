"""M11 motor-channel-dissection protocol, preflight, and guarded runner.

Importing it, testing its pure helpers, and running ``--preflight`` construct
neither the MaleCNS nor a physics runtime.  Canonical execution is reachable
only through the explicit ``--execute-canonical`` switch and a late import.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
M10B_DIR = HERE / "interface_output" / "m10b_perturbation_scaling"
M10C_DIR = HERE / "interface_output" / "m10c_m10b_analysis"
OUTPUT_DIR = HERE / "interface_output" / "m11_motor_channel_dissection"
PREREGISTRATION_PATH = OUTPUT_DIR / "m11a_preregistration.json"

UPSTREAM_ARTIFACTS = {
    "m10b_raw.npz": {"directory": "m10b", "sha256": "85e98715ac3d8b219c86ef338187828e787ee8f300bacad9d318809e23208cde", "byte_size": 57652701},
    "m10b_report.json": {"directory": "m10b", "sha256": "fdc3cc8aef9f02a85dc10f671a4ff86d9592354c8ea60d9a5f179b2c0c81acfc", "byte_size": 5785},
    "m10b_manifest.json": {"directory": "m10b", "sha256": "62b1f4a3e5f5773de594a3d965b0227e0dec9cc52fb09658c0a3d92ecc7f0ad7", "byte_size": 26684},
    "m10b_preregistration.json": {"directory": "m10b", "sha256": "a267647093d616f394374761da58ae495f12a6df6fe12e004abbcb1cb1b2d5a9", "byte_size": 10924},
    "m10c_analysis.json": {"directory": "m10c", "sha256": "31d7dd5445ecd6bc17542f455d5196a087934f3251d5c36915424b737e595740", "byte_size": 30426},
    "m10c_manifest.json": {"directory": "m10c", "sha256": "d5cb32c04da9b285247b35ad44b252997bc0a38c3f5fd9657a49857635f10454", "byte_size": 2588},
}

PROVENANCE_AMENDMENT = {
    "type": "PRE-EXECUTION provenance correction",
    "previous_preregistration_sha256": "758668128d0fbc89e95da787a9f3088a453cb751d7c25a174c90d04cc746e3bd",
    "reason": "m10c_manifest.json was recorded using the LF-normalized Git blob identity rather than the canonical generated M10C artifact raw-byte identity",
    "scientific_conditions_executed_before_correction": 0,
    "physics_transitions_before_correction": 0,
    "neural_transitions_before_correction": 0,
    "scientific_design_changed": False,
}

MOTOR_CHANNELS = (
    ("joint_LFTibia", 5, 1), ("joint_LMTibia", 12, 1),
    ("joint_LHTibia", 19, 1), ("joint_RFTibia", 26, 1),
    ("joint_RMTibia", 33, 1), ("joint_RHTibia", 40, 1),
    ("joint_LFFemur", 3, -1), ("joint_LMFemur", 10, -1),
    ("joint_LHFemur", 17, -1), ("joint_RMFemur", 31, -1),
    ("joint_RHFemur", 38, -1),
)
CONDITIONS = (("full_11_enabled", ()), ("all_11_disabled", tuple(x[0] for x in MOTOR_CHANNELS))) + tuple(
    (f"leave_one_out__{name}", (name,)) for name, _, _ in MOTOR_CHANNELS)
PERTURBATION = {
    "direction_xyz": [0.0, 1.0, 0.0], "magnitude": 1.024,
    "frame": "world", "application_body_source": "Thorax",
    "application_point": "authoritative body center of mass",
    "torque_xyz": [0.0, 0.0, 0.0], "start_ms_inclusive": 500.0,
    "stop_ms_exclusive": 520.0, "start_transition_inclusive": 5000,
    "stop_transition_exclusive": 5200,
}
TIMING = {"duration_ms": 1500.0, "physics_dt_ms": 0.1, "neural_dt_ms": 0.5,
          "physics_transitions_per_condition": 15000, "neural_transitions_per_condition": 3000}
WINDOWS = {
    "pre": {"start_ms_inclusive": 0.0, "stop_ms_exclusive": 500.0},
    "direct_force": {"start_ms_inclusive": 500.0, "stop_ms_exclusive": 520.0},
    "early_post_force": {"start_ms_inclusive": 520.0, "stop_ms_exclusive": 557.0},
    "later_post_force": {"start_ms_inclusive": 557.0, "stop_ms_inclusive": 1500.0},
}
THRESHOLDS = {"thorax_com_deviation_mm": 0.005, "root_orientation_shortest_arc_deg": 0.25}
CLASSIFICATIONS = ("ABLATION_REDUCES_AMPLIFICATION", "ABLATION_INCREASES_AMPLIFICATION",
                   "UNRESOLVED_AT_INHERITED_THRESHOLD")
FUTURE_OUTPUTS = {"raw": "m11_raw.npz", "report": "m11_report.json", "manifest": "m11_manifest.json"}
PREREGISTRATION_SHA256 = "aa8f0b57c1126d6f4bb5b477849e81be2dbd9c86ba6d180698810c7aedfe6fd5"
PREREGISTRATION_BYTE_SIZE = 10003
SCHEMA = "M11B-CANONICAL-MOTOR-CHANNEL-DISSECTION.1"
TOTAL_PHYSICS_TRANSITIONS = 195000
TOTAL_NEURAL_TRANSITIONS = 39000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_upstream(m10b_dir: Path = M10B_DIR, m10c_dir: Path = M10C_DIR) -> dict[str, dict[str, Any]]:
    """Verify every immutable upstream artifact by raw SHA-256 and byte size."""
    verified = {}
    for name, identity in UPSTREAM_ARTIFACTS.items():
        path = (m10b_dir if identity["directory"] == "m10b" else m10c_dir) / name
        if (not path.is_file() or path.stat().st_size != identity["byte_size"]
                or _sha256(path) != identity["sha256"]):
            raise RuntimeError(f"M11 fail-closed before transitions: frozen upstream mismatch: {name}")
        verified[name] = {"sha256": identity["sha256"], "byte_size": identity["byte_size"]}
    return verified


def intervene(decoded: Mapping[str, float], ablated: Sequence[str]) -> dict[str, float]:
    """Zero only selected decoded contributions at the final application boundary."""
    names = tuple(x[0] for x in MOTOR_CHANNELS)
    if tuple(decoded) != names or len(ablated) != len(set(ablated)) or not set(ablated) <= set(names):
        raise ValueError("exact ordered motor inventory and valid unique ablations required")
    if not all(math.isfinite(float(value)) for value in decoded.values()):
        raise ValueError("decoded contributions must be finite")
    selected = set(ablated)
    return {name: 0.0 if name in selected else float(value) for name, value in decoded.items()}


def ablation_effect(ablated_deviation: float, full_enabled_deviation: float) -> float:
    """Signed estimand: ablated minus full-enabled M10-style deviation."""
    if not all(math.isfinite(float(x)) for x in (ablated_deviation, full_enabled_deviation)):
        raise ValueError("finite deviations required")
    return float(ablated_deviation) - float(full_enabled_deviation)


def classify(effect: float, threshold: float) -> str:
    """Classify an ablation effect using inclusive inherited thresholds."""
    if not math.isfinite(effect) or not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("finite effect and positive threshold required")
    if effect <= -threshold:
        return CLASSIFICATIONS[0]
    if effect >= threshold:
        return CLASSIFICATIONS[1]
    return CLASSIFICATIONS[2]


def force_at_transition(transition: int) -> tuple[float, float, float]:
    if not isinstance(transition, int) or not 0 <= transition < 15000:
        raise ValueError("physics transition must be in [0, 15000)")
    return (0.0, 1.024 if 5000 <= transition < 5200 else 0.0, 0.0)


def protocol() -> dict[str, Any]:
    return {
        "schema": "M11A-PREREGISTERED-MOTOR-CHANNEL-DISSECTION.1", "status": "NOT_RUN",
        "provenance_amendment": PROVENANCE_AMENDMENT,
        "scientific_question": "Which admitted motor channels are causally responsible for the later post-perturbation amplification observed in M10, and is that effect distributed across the admitted motor interface or concentrated in particular channels?",
        "scope": "M11 tests causal physical contributions of individual admitted motor channels within the modeled MaleCNS -> decoder -> admitted motor -> MuJoCo chain.",
        "stage_design": {"stage_1": "exactly 13 conditions at force 1.024", "stage_2": "only after Stage 1 is frozen and analyzed, cross-force work requires a separate preregistration", "automatic_four_force_expansion": False},
        "upstream_artifacts": UPSTREAM_ARTIFACTS,
        "motor_channels": [{"name": n, "action_index": i, "coordinate_sign": s} for n, i, s in MOTOR_CHANNELS],
        "conditions": [{"name": n, "ablated_channels": list(a), "fresh_identical_deterministic_initialization": True} for n, a in CONDITIONS],
        "intervention": {"boundary": "decoded physical motor contribution immediately before physical application", "ablated_value": 0.0, "only_listed_channels_changed": True, "MaleCNS_active": True, "sensory_encoding_active": True, "neural_updates_active": True, "motor_observation_active": True, "decoder_active": True},
        "inherited_configuration": {"source": "exact M10B initialization, neural runtime, sensory mapping, decoder, physics, timing, and perturbation implementation; no recalibration", "timing": TIMING, "perturbation": PERTURBATION, "contact_is_neural_input": False},
        "analysis": {"primary_window": "later_post_force", "windows": WINDOWS, "metrics": list(THRESHOLDS), "thresholds": THRESHOLDS, "metric_reduction": "for each condition and metric/window, maximum timestamp-aligned nonnegative perturbation-versus-matched-control deviation, exactly as M10", "estimand": "E_channel_metric = D_leave_one_out_channel_metric - D_full_11_enabled_metric", "sign_semantics": {"positive": "ablation increased the M10-style physical deviation", "negative": "ablation decreased the M10-style physical deviation", "zero": "ablation did not change the M10-style physical deviation"}, "classification": {"inclusive_rules": {CLASSIFICATIONS[0]: "effect <= -threshold", CLASSIFICATIONS[1]: "effect >= threshold", CLASSIFICATIONS[2]: "-threshold < effect < threshold"}, "per_channel_per_primary_metric": True, "ranking_or_composite": False}},
        "secondary_descriptive_only": ["tibia versus femur", "left versus right", "fore versus mid versus hind", "temporal emergence across direct, early, and later windows"],
        "integrity": {"preflight_scientific_transitions": 0, "fail_closed": True, "no_automatic_retries": True, "raw_data_every_condition": True, "verify_upstream_before_and_after_execution": True, "exact_condition_motor_intervention_and_force_validation": True, "no_completed_output_overwrite": True},
        "future_outputs": {"directory": "interface_output/m11_motor_channel_dissection", **FUTURE_OUTPUTS, "exclusive_creation_required": True, "M10_namespaces_read_only": True},
        "interpretation_prohibitions": ["balance", "stabilization", "righting", "reflex", "recovery", "natural locomotion", "biological motor function", "biological timing", "biological necessity or sufficiency of corresponding real neurons"],
        "boundary_note": "557 ms is the inherited approximate admitted-motor boundary, not a biological latency.",
    }


def verify_preregistration(path: Path = PREREGISTRATION_PATH) -> str:
    if (not path.is_file() or path.stat().st_size != PREREGISTRATION_BYTE_SIZE
            or _sha256(path) != PREREGISTRATION_SHA256):
        raise RuntimeError("M11 fail-closed before transitions: preregistration mismatch")
    if json.loads(path.read_text(encoding="utf-8")) != protocol():
        raise RuntimeError("M11 fail-closed before transitions: preregistration content mismatch")
    return PREREGISTRATION_SHA256


def outputs_available(output_dir: Path = OUTPUT_DIR) -> bool:
    return not any((output_dir / name).exists() for name in FUTURE_OUTPUTS.values())


def preflight(m10b_dir: Path = M10B_DIR, m10c_dir: Path = M10C_DIR,
              output_dir: Path | None = None) -> dict[str, Any]:
    """Read and hash only; deliberately reject before constructing runtimes."""
    output_dir = OUTPUT_DIR if output_dir is None else output_dir
    preregistration = verify_preregistration()
    verified = verify_upstream(m10b_dir, m10c_dir)
    if not outputs_available(output_dir):
        raise FileExistsError("M11 future output namespace is occupied; overwrite forbidden")
    return {"status": "PREFLIGHT_PASS", "scientific_conditions_executed": 0,
            "physics_runtime_constructed": False, "MaleCNS_constructed": False,
            "physics_transitions": 0, "neural_transitions": 0,
            "preregistration_sha256": preregistration, "verified_upstream": verified,
            "condition_inventory": [x[0] for x in CONDITIONS]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true",
                       help="read-only validation; performs zero scientific transitions")
    modes.add_argument("--execute-canonical", action="store_true",
                       help="explicitly execute and transactionally publish canonical M11B")
    args = parser.parse_args(argv)
    if args.preflight:
        result = preflight()
    else:
        # Physics dependencies and execution code are unreachable from import,
        # --help, default invocation, and --preflight.
        from . import _windows_m11_motor_channel_dissection_adapter as adapter
        result = adapter.execute_canonical()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
