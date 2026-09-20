"""Read-only, fail-closed inspection of the canonical M7 first 10 ms.

This module intentionally has no dependency on the M7 scientific runner (or
any FlyGym/neural module).  Loading is always performed with pickle disabled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

CANONICAL_SHA256 = "155ef633a319711d44fc471c1f46c24cec0b36ea6e7326556c5b987e912fed47"
CONDITIONS = ("SPONTANEOUS_NEURAL_EMBODIMENT", "ALL_NEURAL_MOTOR_DISABLED")
FALL_HEIGHT_FRACTION = 0.5
ROLLOVER_UP_Z_MAX = 0.0
REQUIRED = ("physics_time_ms", "physics_qpos", "physics_qvel",
            "physics_joint_position", "physics_action", "physics_ctrl",
            "physics_body_position", "physics_body_orientation",
            "physics_contact_forces")
HERE = Path(__file__).resolve().parent
DEFAULT_RAW = HERE / "interface_output" / "m7_canonical" / "m7_raw.npz"
DEFAULT_OUTPUT = HERE / "interface_output" / "m7c_initial_stability" / "m7c_canonical_first10ms.json"


class EvidenceError(RuntimeError):
    """Evidence is absent, malformed, or not the frozen canonical archive."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _up_z(quaternion: np.ndarray) -> np.ndarray:
    """World Z component of body-local up for MuJoCo w,x,y,z quaternions."""
    q = np.asarray(quaternion, dtype=np.float64)
    if q.ndim != 2 or q.shape[1] != 4 or not np.all(np.isfinite(q)):
        raise EvidenceError("body orientation must be finite (samples,4)")
    norm = np.linalg.norm(q, axis=1)
    if np.any(norm == 0):
        raise EvidenceError("zero-norm body orientation")
    q = q / norm[:, None]
    return 1.0 - 2.0 * (q[:, 1] ** 2 + q[:, 2] ** 2)


def _array(archive: Mapping[str, np.ndarray], condition: str, field: str) -> np.ndarray:
    key = f"{condition}__{field}"
    if key not in archive:
        raise EvidenceError(f"missing telemetry: {key}")
    value = np.asarray(archive[key])
    if value.dtype == object or not np.issubdtype(value.dtype, np.number):
        raise EvidenceError(f"non-numeric telemetry: {key}")
    if not np.all(np.isfinite(value)):
        raise EvidenceError(f"non-finite telemetry: {key}")
    return value


def analyze(raw: Path) -> dict[str, Any]:
    before = raw.stat()
    actual = sha256(raw)
    if actual != CANONICAL_SHA256:
        raise EvidenceError(f"canonical SHA-256 mismatch: {actual}")
    # Security/scientific invariant: never permit object unpickling from evidence.
    with np.load(raw, allow_pickle=False) as archive:
        trajectories: dict[str, Any] = {}
        selected: dict[str, dict[str, np.ndarray]] = {}
        for condition in CONDITIONS:
            values = {field: _array(archive, condition, field) for field in REQUIRED}
            time = values["physics_time_ms"]
            if time.ndim != 1 or time.size < 2 or time[0] != 0 or np.any(np.diff(time) <= 0):
                raise EvidenceError(f"malformed physics clock: {condition}")
            lengths = {v.shape[0] for v in values.values()}
            if lengths != {time.size}:
                raise EvidenceError(f"inconsistent physics sample counts: {condition}")
            mask = time <= 10.0 + np.spacing(10.0)
            if not np.any(mask) or time[mask][-1] < 10.0 - 1e-9:
                raise EvidenceError(f"telemetry does not cover 0--10 ms: {condition}")
            values = {k: v[mask] for k, v in values.items()}; selected[condition] = values
            pos, quat = values["physics_body_position"], values["physics_body_orientation"]
            if pos.ndim != 2 or pos.shape[1] != 3:
                raise EvidenceError("body position must be (samples,3)")
            up = _up_z(quat); threshold = float(pos[0, 2] * FALL_HEIGHT_FRACTION)
            fall = pos[:, 2] < threshold; roll = up <= ROLLOVER_UP_Z_MAX
            rows = []
            for i in range(time[mask].size):
                forces = values["physics_contact_forces"][i]
                rows.append({"sample_index": i, "physics_time_ms": float(values["physics_time_ms"][i]),
                    "body_xyz": pos[i].tolist(), "body_orientation_quaternion_wxyz": quat[i].tolist(),
                    "body_up_z": float(up[i]), "body_height": float(pos[i, 2]),
                    "qpos": values["physics_qpos"][i].tolist(), "qvel": values["physics_qvel"][i].tolist(),
                    "joint_positions_42": values["physics_joint_position"][i].tolist(),
                    "action": values["physics_action"][i].tolist(), "ctrl": values["physics_ctrl"][i].tolist(),
                    "contact_force_telemetry": forces.tolist(),
                    "nonzero_contact_entries": int(np.count_nonzero(forces)),
                    "fall": {"height_threshold": threshold, "height_below_threshold": bool(fall[i])},
                    "rollover": {"up_z_threshold": ROLLOVER_UP_Z_MAX, "body_up_z_at_or_below_threshold": bool(roll[i])}})
            first = lambda x: (int(np.flatnonzero(x)[0]) if np.any(x) else None)
            fi, ri = first(fall), first(roll)
            trajectories[condition] = {"initial_height": float(pos[0, 2]), "fall_height_threshold": threshold,
                "first_fall_sample_index": fi, "first_fall_time_ms": None if fi is None else float(values["physics_time_ms"][fi]),
                "first_rollover_sample_index": ri, "first_rollover_time_ms": None if ri is None else float(values["physics_time_ms"][ri]),
                "samples": rows}
        equality = {}
        for field in REQUIRED:
            a, b = selected[CONDITIONS[0]][field], selected[CONDITIONS[1]][field]
            equality[field] = {"array_equal": bool(np.array_equal(a, b)),
                "max_abs_difference": float(np.max(np.abs(a - b))) if a.size else 0.0}
        if not all(item["array_equal"] for item in equality.values()):
            raise EvidenceError("canonical conditions differ within first 10 ms")
    after = raw.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or sha256(raw) != actual:
        raise EvidenceError("canonical archive changed during analysis")
    return {"schema": "M7C-A-CANONICAL-FIRST10MS.1", "source_raw_sha256": actual,
        "source_read_only": True, "np_load_allow_pickle": False, "window_ms": [0.0, 10.0],
        "condition_equality": equality, "trajectories": trajectories,
        "physics_transitions_executed": 0, "neural_transitions_executed": 0}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv); report = analyze(args.raw)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(args.json)


if __name__ == "__main__":
    main()
