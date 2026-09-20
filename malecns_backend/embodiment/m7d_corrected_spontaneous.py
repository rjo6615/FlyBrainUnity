"""M7D corrected-embodiment spontaneous MaleCNS preregistration and CLI.

Importing this module is inert.  Only ``--run-windows`` advances either clock;
``--windows-preflight`` initializes two fresh runtimes and executes zero steps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .integrated_whole_leg_readiness import EQUIVALENCE_FIELDS, EXPECTED_TIER_B, TIER_A

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "interface_output" / "m7d_corrected_spontaneous"
SUMMARY_PATH = OUTPUT_DIR / "m7d_summary.json"
MANIFEST_PATH = OUTPUT_DIR / "m7d_manifest.json"
RAW_PATH = OUTPUT_DIR / "m7d_raw.npz"
B4_DIR = HERE / "interface_output" / "m7c_initial_stability"
B4_SUMMARY = B4_DIR / "m7c_b4_stability_summary.json"
B4_MANIFEST = B4_DIR / "m7c_b4_stability_manifest.json"
B4_RAW = B4_DIR / "m7c_b4_stability_raw.npz"
B4_RAW_SHA256 = "966996caa3504b592c603b349c1ebb905f18e687f2d99f3c0be5d06fe83a4109"
M7_DIR = HERE / "interface_output" / "m7_canonical"
M7_SUMMARY = M7_DIR / "m7_summary.json"
M7_MANIFEST = M7_DIR / "m7_manifest.json"
M7_RAW = M7_DIR / "m7_raw.npz"
SCHEMA = "M7D-CORRECTED-SPONTANEOUS.1"
SEED = 1
DURATION_MS = 500
PHYSICS_DT_MS = .1
NEURAL_DT_MS = .5  # inherited frozen MaleCNS cadence
EXPECTED_PHYSICS_TRANSITIONS = 5000
EXPECTED_PHYSICS_STATES = 5001
EXPECTED_NEURAL_UPDATES = 1000
INIT_POSE = "tripod"
SPAWN_POS = (0.0, 0.0, 0.6045752232266313)
SPAWN_ORIENTATION = (0.0, 0.0, 0.0)
CONDITIONS = ("CORRECTED_SPONTANEOUS_NEURAL_EMBODIMENT", "CORRECTED_ALL_NEURAL_MOTOR_DISABLED")
ADMITTED_MOTOR = TIER_A + EXPECTED_TIER_B
ADMITTED_SENSORY = TIER_A
PROHIBITED_ASSISTANCE = ("gait controller", "tripod controller", "stance controller", "swing controller",
    "balance controller", "reference trajectory", "walking trajectory", "CPG", "phase oscillator",
    "foot placement controller", "adhesion scheduler", "dynamic adhesion", "target movement",
    "navigation target", "reward", "reinforcement learning", "AI policy", "optimizer",
    "scripted descending command", "scripted neural stimulation", "adaptive stabilization",
    "postural controller", "fall recovery", "outcome-dependent parameter changes")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_b4(summary: Path = B4_SUMMARY, manifest: Path = B4_MANIFEST,
              raw: Path = B4_RAW) -> dict[str, Any]:
    """Fail closed on all three canonical B4 artifacts and the required raw hash."""
    if not all(p.is_file() for p in (summary, manifest, raw)):
        raise RuntimeError("canonical B4 summary/manifest/raw evidence is incomplete")
    s, m = (json.loads(p.read_text(encoding="utf-8")) for p in (summary, manifest))
    digest = sha256(raw)
    checks = (s.get("status") == "COMPLETE",
        s.get("classification") == "SUPPORTED_INITIALIZATION_STABLE_100MS",
        s.get("physics_transitions") == 1000, s.get("neural_transitions") == 0,
        m.get("status") == "COMPLETE", m.get("raw", {}).get("sha256") == B4_RAW_SHA256,
        m.get("raw", {}).get("byte_size") == raw.stat().st_size, digest == B4_RAW_SHA256)
    if not all(checks):
        raise RuntimeError("canonical B4 provenance or required raw SHA-256 mismatch")
    return {"summary": {"path": str(summary.resolve()), "sha256": sha256(summary)},
        "manifest": {"path": str(manifest.resolve()), "sha256": sha256(manifest)},
        "raw": {"path": str(raw.resolve()), "byte_size": raw.stat().st_size, "sha256": digest}}


def verify_m7(summary: Path = M7_SUMMARY, manifest: Path = M7_MANIFEST,
              raw: Path = M7_RAW) -> dict[str, Any]:
    """Verify canonical M7's tracked evidence and immutable raw identity."""
    if not all(p.is_file() for p in (summary, manifest, raw)):
        raise RuntimeError("canonical M7 summary/manifest/raw evidence is incomplete")
    s, evidence = (json.loads(p.read_text(encoding="utf-8")) for p in (summary, manifest))
    digest = sha256(raw)
    if (s.get("run_status") != "COMPLETE" or evidence.get("raw_sha256") != digest or
            evidence.get("raw_byte_size") != raw.stat().st_size):
        raise RuntimeError("canonical M7 evidence identity mismatch")
    return {"summary": {"path": str(summary.resolve()), "sha256": sha256(summary)},
        "manifest": {"path": str(manifest.resolve()), "sha256": sha256(manifest)},
        "raw": {"path": str(raw.resolve()), "byte_size": raw.stat().st_size, "sha256": digest}}


def protocol() -> dict[str, Any]:
    return {"schema": SCHEMA, "status": "NOT_RUN", "scientific_run_executed": False,
        "seed": SEED, "duration_ms": DURATION_MS, "physics_dt_ms": PHYSICS_DT_MS,
        "neural_dt_ms": NEURAL_DT_MS, "expected_physics_transitions_per_condition": 5000,
        "expected_physics_states_per_condition": 5001, "expected_neural_updates_per_condition": 1000,
        "conditions": [{"name": c, "fresh_runtime": True} for c in CONDITIONS],
        "physical_initialization": {"flygym": "1.2.1", "mujoco": "3.2.7", "init_pose": INIT_POSE,
            "spawn_pos": list(SPAWN_POS), "spawn_orientation": list(SPAWN_ORIENTATION),
            "control": "position", "adhesion_enabled": False, "settling_transitions": 0,
            "baseline_targets": "exact measured corrected tripod joint state at time zero",
            "calibration_surface": "canonical inherited static m5d2c_calibration_surface"},
        "admitted_motor_interfaces": list(ADMITTED_MOTOR), "admitted_sensory_interfaces": list(ADMITTED_SENSORY),
        "baseline_only_actuator_count": 31, "equivalence_fields": list(EQUIVALENCE_FIELDS),
        "condition_b_intervention": "zero only 11 admitted contributions immediately before physical application",
        "hidden_assistance": {name: False for name in PROHIBITED_ASSISTANCE},
        "causal_milestones": [f"D{i}" for i in range(11)],
        "stability_checkpoints_ms": [7.2, 13.0, 100.0, 500.0],
        "fall_after_intervention_terminates": False, "walking": None, "tripod_gait_classification": None,
        "telemetry": {"numeric_only": True, "allow_pickle": False,
            "physics_states": 5001, "neural_samples": 1000,
            "physics": ["time", "root_xyz", "body_orientation", "body_up_z", "qpos", "qvel", "42_joint_positions", "commanded_targets", "action", "ctrl", "support_contact_summaries", "finite"],
            "neural": ["neural_time", "six_sensory_encoded_values", "delivered_sensory_drive_summary", "aggregate_cns_summary", "11_observer_values", "11_decoder_values", "11_admitted_contributions"]}}


def validate_protocol(value: Mapping[str, Any]) -> None:
    checks = (value.get("seed") == 1, value.get("duration_ms") == 500,
        value.get("physics_dt_ms") == .1, tuple(x["name"] for x in value.get("conditions", ())) == CONDITIONS,
        all(x.get("fresh_runtime") for x in value.get("conditions", ())),
        tuple(value.get("admitted_motor_interfaces", ())) == ADMITTED_MOTOR,
        tuple(value.get("admitted_sensory_interfaces", ())) == ADMITTED_SENSORY,
        value.get("baseline_only_actuator_count") == 31,
        value.get("physical_initialization", {}).get("spawn_pos") == list(SPAWN_POS),
        value.get("physical_initialization", {}).get("init_pose") == "tripod",
        not any(value.get("hidden_assistance", {}).values()), value.get("walking") is None,
        value.get("tripod_gait_classification") is None)
    if not all(checks): raise RuntimeError("M7D frozen protocol mismatch")


def output_available() -> bool:
    if RAW_PATH.exists(): return False
    for path in (SUMMARY_PATH, MANIFEST_PATH):
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") == "COMPLETE": return False
    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--windows-preflight", action="store_true"); modes.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv); validate_protocol(protocol())
    if not output_available(): raise FileExistsError("refusing to overwrite COMPLETE canonical M7D evidence")
    from . import _windows_m7d_corrected_spontaneous_adapter as adapter
    if args.windows_preflight:
        adapter.windows_preflight()
        print("M7D WINDOWS PREFLIGHT PASS — CORRECTED EMBODIMENT FROZEN —\nMATCHED CONDITIONS VERIFIED — ZERO PHYSICS TRANSITIONS —\nZERO NEURAL TRANSITIONS — SCIENCE NOT RUN")
    else: adapter.run_windows()
    return 0


if __name__ == "__main__": raise SystemExit(main())
