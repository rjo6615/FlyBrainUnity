"""M8 10-second extension of the frozen M7D corrected embodiment protocol.

The module is inert on import.  The canonical command performs a zero-step
preflight before creating either condition and refuses to overwrite evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import m7d_corrected_spontaneous as m7d

HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "interface_output" / "m8_extended_spontaneous"
RAW_PATH = OUTPUT_DIR / "m8_raw.npz"
MANIFEST_PATH = OUTPUT_DIR / "m8_manifest.json"
ANALYSIS_PATH = OUTPUT_DIR / "m8_analysis.json"
REPORT_PATH = OUTPUT_DIR / "M8_POSTRUN_REPORT.md"
REPLAY_MANIFEST_PATH = OUTPUT_DIR / "m8_replay_manifest.json"
SCHEMA = "M8-EXTENDED-SPONTANEOUS.1"
DURATION_MS = 10_000
PHYSICS_DT_MS, NEURAL_DT_MS = m7d.PHYSICS_DT_MS, m7d.NEURAL_DT_MS
EXPECTED_PHYSICS_TRANSITIONS = 100_000
EXPECTED_PHYSICS_STATES = 100_001
EXPECTED_NEURAL_UPDATES = 20_000
SEED, INIT_POSE, SPAWN_POS = m7d.SEED, m7d.INIT_POSE, m7d.SPAWN_POS
CONDITIONS, ADMITTED_MOTOR, ADMITTED_SENSORY = m7d.CONDITIONS, m7d.ADMITTED_MOTOR, m7d.ADMITTED_SENSORY


def protocol() -> dict[str, Any]:
    frozen = m7d.protocol()
    return {"schema": SCHEMA, "status": "NOT_RUN", "scientific_run_executed": False,
        "derived_from": {"schema": m7d.SCHEMA, "configuration": "exact except duration and telemetry"},
        "seed": SEED, "duration_ms": DURATION_MS, "physics_dt_ms": PHYSICS_DT_MS,
        "neural_dt_ms": NEURAL_DT_MS, "expected_physics_transitions_per_condition": EXPECTED_PHYSICS_TRANSITIONS,
        "expected_physics_states_per_condition": EXPECTED_PHYSICS_STATES,
        "expected_neural_updates_per_condition": EXPECTED_NEURAL_UPDATES,
        "conditions": frozen["conditions"], "physical_initialization": frozen["physical_initialization"],
        "admitted_motor_interfaces": list(ADMITTED_MOTOR),
        "admitted_sensory_interfaces": list(ADMITTED_SENSORY),
        "baseline_only_actuator_count": frozen["baseline_only_actuator_count"],
        "condition_b_intervention": frozen["condition_b_intervention"],
        "hidden_assistance": frozen["hidden_assistance"], "walking": None,
        "tripod_gait_classification": None, "fall_after_intervention_terminates": False,
        "telemetry": {"physics_cadence_ms": .1, "neural_cadence_ms": .5,
            "large_diagnostic_cadence_ms": 5., "numeric_npz_allow_pickle": False,
            "authoritative_contact_identity": "resolved from compiled MuJoCo geom/body IDs or fail closed",
            "foot_positions": "MuJoCo body x_pos for six Tarsus5 bodies",
            "replay": "physics state at full 0.1-ms cadence; neural arrays at 0.5-ms cadence"}}


def validate_protocol(value: Mapping[str, Any]) -> None:
    checks = (value.get("duration_ms") == 10_000, value.get("seed") == m7d.SEED,
        value.get("physics_dt_ms") == m7d.PHYSICS_DT_MS,
        value.get("neural_dt_ms") == m7d.NEURAL_DT_MS,
        tuple(x["name"] for x in value.get("conditions", ())) == CONDITIONS,
        tuple(value.get("admitted_motor_interfaces", ())) == ADMITTED_MOTOR,
        tuple(value.get("admitted_sensory_interfaces", ())) == ADMITTED_SENSORY,
        value.get("physical_initialization") == m7d.protocol()["physical_initialization"],
        not any(value.get("hidden_assistance", {}).values()), value.get("walking") is None)
    if not all(checks):
        raise RuntimeError("M8 protocol deviates from M7D beyond preregistered duration/telemetry changes")


def output_available() -> bool:
    return not any(p.exists() for p in (RAW_PATH, MANIFEST_PATH, ANALYSIS_PATH, REPORT_PATH, REPLAY_MANIFEST_PATH))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--windows-preflight", action="store_true")
    modes.add_argument("--run-windows", action="store_true")
    args = parser.parse_args(argv); validate_protocol(protocol())
    if not output_available(): raise FileExistsError("refusing to overwrite any M8 artifact")
    from . import _windows_m8_extended_spontaneous_adapter as adapter
    if args.windows_preflight:
        report = adapter.windows_preflight()
        print(json.dumps(report, indent=2, sort_keys=True))
        print("M8 PREFLIGHT PASS — ZERO PHYSICS/NEURAL TRANSITIONS — CANONICAL RUN NOT EXECUTED")
    else:
        adapter.run_windows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
