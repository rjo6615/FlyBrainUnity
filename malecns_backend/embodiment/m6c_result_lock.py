"""Raw-byte evidence lock for the externally retained canonical M6C result.

This utility is deliberately read-only with respect to the canonical JSON.  It
streams the large file, checks the small set of identity fields, and creates a
lock with exclusive-create semantics.  It never starts an M6C runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .integrated_whole_leg_readiness import CONDITIONS, DURATION_MS, SCHEMA, SEED

CANONICAL = Path(__file__).resolve().parent / "interface_output" / "integrated_whole_leg_readiness.json"
LOCK = Path(__file__).resolve().parent / "interface_output" / "m6c_canonical_result_lock.json"


def raw_identity(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def build_lock(path: Path) -> dict[str, Any]:
    digest, size = raw_identity(path)
    data = json.loads(path.read_bytes())
    conditions = data.get("condition_results", {})
    required = {
        "schema": SCHEMA, "seed": SEED, "duration_ms": DURATION_MS,
        "classification": "INTEGRATED_MULTI_LEG_CAUSALITY_CONFIRMED",
        "run_status": "COMPLETE", "scientific_run_executed": True,
        "m7_readiness": "M7_SPONTANEOUS_LOCOMOTION_EXPERIMENT_READY",
    }
    mismatches = {key: {"expected": value, "observed": data.get(key)}
                  for key, value in required.items() if data.get(key) != value}
    if tuple(conditions) != CONDITIONS:
        mismatches["condition_order"] = {"expected": list(CONDITIONS), "observed": list(conditions)}
    if mismatches:
        raise ValueError(f"canonical identity checks failed: {mismatches}")
    provenance = data.get("provenance", {})
    root = Path(__file__).resolve().parents[2]
    try:
        recorded_path = path.resolve().relative_to(root)
    except ValueError:
        recorded_path = path.resolve()
    return {
        "schema": "M6C-CANONICAL-RESULT-LOCK.0",
        "lock_status": "LOCKED",
        "artifact_kind": "RAW_SCIENTIFIC_EVIDENCE",
        "canonical_path": str(recorded_path).replace("\\", "/"),
        "raw_sha256": digest,
        "byte_size": size,
        **required,
        "condition_count": len(conditions),
        "provenance": {key: provenance.get(key) for key in
                       ("m6a_sha256", "m6b_sha256", "tier_a_sha256")},
        "preservation_policy": "Never rewrite, normalize, regenerate, or overwrite the canonical JSON.",
    }


def write_lock_exclusive(lock: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(destination, flags, 0o444)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(lock, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=CANONICAL)
    parser.add_argument("--lock", type=Path, default=LOCK)
    args = parser.parse_args(argv)
    if not args.canonical.is_file():
        parser.error(f"canonical evidence is not materialized: {args.canonical}")
    write_lock_exclusive(build_lock(args.canonical), args.lock)
    print(f"M6C CANONICAL EVIDENCE LOCKED: {args.lock}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
