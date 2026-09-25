"""Guarded executor contract for the frozen three-candidate observation.

Import, ``--help``, and ``--preflight`` never construct a neural or physics
runtime.  The only execution boundary is the explicit ``--execute`` option;
the Windows adapter reuses the authoritative scientific transition kernel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREREGISTRATION_PATH = HERE / "interface_output" / "candidate_motor_channel_future_preregistration.json"
PREREGISTRATION_SHA256 = "16cf491729aae39b8552a79b67993feef5661ee2240317d37c2d385e9e21893d"
OUTPUT_DIR = HERE / "interface_output" / "candidate_motor_channel_experiment"
OUTPUTS = ("execution_manifest.json", "candidate_motor_channel_raw.npz",
           "candidate_motor_channel_report.json", "final_manifest.json")
CANDIDATES = (("joint_RFFemur", 24, -1), ("joint_LFTarsus1", 6, -1),
              ("joint_RFTarsus1", 27, -1))
CONDITIONS = ("ENABLED", "ZEROED")
CURRENT_11_INDICES = (5, 12, 19, 26, 33, 40, 3, 10, 17, 31, 38)
DURATION_MS, SEED = 1000, 1
PHYSICS_DT_MS, NEURAL_DT_MS = 0.1, 0.5
INITIALIZATION_FIELDS = ("initial_qpos", "initial_qvel", "initial_ctrl", "malecns_state_digest",
                         "sensory_state", "decoder_state", "seed", "physics_model_identity",
                         "timestep_configuration")
CLASSIFICATIONS = ("SUPPORTED_AND_ACTIVE", "SUPPORTED_BUT_SILENT",
                   "DECODER_CANCELLATION", "SUPPORTED_LOW_ACTIVITY")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_preregistration_bytes(raw: bytes, expected_sha256: str = PREREGISTRATION_SHA256) -> str:
    actual = sha256_bytes(raw)
    if actual != expected_sha256:
        raise RuntimeError(f"fail closed: preregistration SHA-256 mismatch: {actual}")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("fail closed: preregistration is not valid JSON") from exc
    if value.get("status") != "NOT_RUN":
        raise RuntimeError("fail closed: preregistration status is not NOT_RUN")
    if (value.get("duration_ms"), value.get("seed"), tuple(value.get("conditions", ()))) != (
            DURATION_MS, SEED, CONDITIONS):
        raise RuntimeError("fail closed: frozen duration, seed, or conditions differ")
    frozen = tuple((row.get("joint"), row.get("action_index"), row.get("coordinate_sign"))
                   for row in value.get("candidates", ()))
    if frozen != CANDIDATES:
        raise RuntimeError("fail closed: frozen candidate inventory differs")
    return actual


def verify_preregistration(path: Path = PREREGISTRATION_PATH) -> str:
    path = Path(path)
    if not path.is_file():
        raise RuntimeError("fail closed: preregistration is absent")
    return verify_preregistration_bytes(path.read_bytes())


def authorize_contribution(action_index: int, contribution: float,
                           condition: str) -> tuple[tuple[float, ...], float, float]:
    """Apply the sole intervention and return the complete physical vector."""
    if action_index not in {row[1] for row in CANDIDATES} or condition not in CONDITIONS:
        raise ValueError("exact candidate and condition required")
    before = float(contribution)
    if not math.isfinite(before):
        raise ValueError("candidate contribution must be finite")
    after = before if condition == "ENABLED" else 0.0
    vector = [0.0] * 42
    vector[action_index] = after
    nonzero = tuple(index for index, value in enumerate(vector) if value != 0.0)
    if nonzero not in ((), (action_index,)) or any(vector[index] != 0.0 for index in CURRENT_11_INDICES):
        raise RuntimeError("unauthorized neural motor contribution")
    return tuple(vector), before, after


def require_matched_initialization(enabled: Mapping[str, Any], zeroed: Mapping[str, Any]) -> bool:
    for field in INITIALIZATION_FIELDS:
        if field not in enabled or field not in zeroed:
            raise RuntimeError(f"matched initialization field absent: {field}")
        left = json.dumps(enabled[field], sort_keys=True, separators=(",", ":"), default=str)
        right = json.dumps(zeroed[field], sort_keys=True, separators=(",", ":"), default=str)
        if left != right:
            raise RuntimeError(f"matched initialization differs: {field}")
    return True


def transition_counts(duration_ms: float, physics_dt_ms: float,
                      neural_dt_ms: float) -> tuple[int, int]:
    if duration_ms != DURATION_MS or physics_dt_ms != PHYSICS_DT_MS or neural_dt_ms != NEURAL_DT_MS:
        raise ValueError("only the frozen 1000-ms timestep configuration is permitted")
    physics = int(round(duration_ms / physics_dt_ms))
    neural = int(round(duration_ms / neural_dt_ms))
    if (physics, neural) != (10000, 2000):
        raise RuntimeError("frozen transition accounting mismatch")
    return physics, neural


def require_new_output_directory(path: Path = OUTPUT_DIR) -> Path:
    path = Path(path).resolve()
    prereg = PREREGISTRATION_PATH.resolve()
    if path == prereg or prereg in path.parents or path in prereg.parents:
        raise ValueError("output path may not overlap the preregistration")
    if path.exists() and any(path.iterdir()):
        raise FileExistsError("experiment output directory is occupied; overwrite forbidden")
    return path


def classify(metrics: Mapping[str, float]) -> str:
    """Apply exact, predeclared activity rules without a movement threshold."""
    spikes = int(metrics["total_spike_increments"])
    rate = float(metrics["peak_filtered_rate_hz"])
    contribution = float(metrics["peak_absolute_contribution"])
    antagonist = float(metrics["peak_absolute_raw_antagonist_signal"])
    positive = float(metrics["positive_peak_hz"])
    negative = float(metrics["negative_peak_hz"])
    if contribution != 0.0:
        return "SUPPORTED_AND_ACTIVE"
    if spikes == 0 and rate == 0.0 and antagonist == 0.0:
        return "SUPPORTED_BUT_SILENT"
    if (spikes > 0 or rate > 0.0) and positive > 0.0 and negative > 0.0 and antagonist == 0.0:
        return "DECODER_CANCELLATION"
    return "SUPPORTED_LOW_ACTIVITY"


def preflight(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    digest = verify_preregistration()
    destination = require_new_output_directory(output_dir)
    physics, neural = transition_counts(DURATION_MS, PHYSICS_DT_MS, NEURAL_DT_MS)
    return {"status": "PREFLIGHT_PASS", "preregistration_sha256": digest,
            "scientific_conditions_executed": 0, "runtime_constructed": False,
            "output_directory": str(destination), "physics_transitions_per_condition": physics,
            "neural_transitions_per_condition": neural, "condition_count": 6}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight:
        result = preflight()
    else:
        from . import _windows_candidate_motor_channel_experiment_adapter as adapter
        result = adapter.execute()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
