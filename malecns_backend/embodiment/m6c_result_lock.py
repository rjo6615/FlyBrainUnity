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

from .integrated_whole_leg_readiness import (
    CONDITIONS, DURATION_MS, EXPECTED_TIER_B, M6A_SHA256, SCHEMA, SEED,
    TIER_A, TIER_A_SHA256,
)

CANONICAL = Path(__file__).resolve().parent / "interface_output" / "integrated_whole_leg_readiness.json"
LOCK = Path(__file__).resolve().parent / "interface_output" / "m6c_canonical_result_lock.final.json"
CANONICAL_SHA256 = "eca51d5ab644f9826eaeeDFC521952c1b9def5ef9cf30d846dfa82df95fbc69b".lower()
M6B_SHA256 = "02a4bbb7ec79ccf0967e9b8499c5a68d0ed8133a56688592ba13cfb2785285a2"


class DuplicateJSONKeyError(ValueError):
    """A JSON object cannot represent canonical identity with repeated keys."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKeyError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def raw_identity(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def build_lock(path: Path, *, expected_sha256: str = CANONICAL_SHA256) -> dict[str, Any]:
    digest, size = raw_identity(path)
    if digest != expected_sha256.lower():
        raise ValueError(f"canonical raw SHA256 mismatch: expected {expected_sha256.lower()}, observed {digest}")
    data = json.loads(path.read_bytes(), object_pairs_hook=_unique_object)
    conditions = data.get("condition_results", {})
    required = {
        "schema": SCHEMA, "seed": SEED, "duration_ms": DURATION_MS,
        "classification": "INTEGRATED_MULTI_LEG_CAUSALITY_CONFIRMED",
        "run_status": "COMPLETE", "scientific_run_executed": True,
        "m7_readiness": "M7_SPONTANEOUS_LOCOMOTION_EXPERIMENT_READY",
    }
    mismatches = {key: {"expected": value, "observed": data.get(key)}
                  for key, value in required.items() if data.get(key) != value}
    if not isinstance(conditions, dict) or set(conditions) != set(CONDITIONS) or len(conditions) != len(CONDITIONS):
        mismatches["condition_membership"] = {
            "expected": sorted(CONDITIONS),
            "observed": sorted(conditions) if isinstance(conditions, dict) else conditions,
        }
    else:
        incomplete = {name: {
            "pre_intervention_equivalence": conditions[name].get("pre_intervention_equivalence"),
            "physics_instability": conditions[name].get("physics_instability"),
        } for name in CONDITIONS if (
            conditions[name].get("pre_intervention_equivalence") is not True
            or conditions[name].get("physics_instability") is not False
        )}
        if incomplete:
            mismatches["condition_completion"] = incomplete
    expected_provenance = {"verified": True, "hash_policy": "raw-bytes",
        "m6a_sha256": M6A_SHA256, "m6b_sha256": M6B_SHA256,
        "tier_a_sha256": TIER_A_SHA256}
    provenance = data.get("provenance", {})
    if any(provenance.get(key) != value for key, value in expected_provenance.items()):
        mismatches["provenance"] = {"expected": expected_provenance, "observed": provenance}
    expected_motor = TIER_A + EXPECTED_TIER_B
    if tuple(data.get("admitted_motor_interfaces", ())) != expected_motor:
        mismatches["admitted_motor_interfaces"] = {"expected": list(expected_motor),
            "observed": data.get("admitted_motor_interfaces")}
    sensory = data.get("sensory_interfaces", ())
    if (not isinstance(sensory, list) or tuple(row.get("actuator") for row in sensory
            if isinstance(row, dict)) != TIER_A):
        mismatches["sensory_interfaces"] = {"expected_actuators": list(TIER_A), "observed": sensory}
    hidden = data.get("hidden_locomotion_audit", {})
    if hidden.get("hidden_locomotion_assistance_executed") is not False:
        mismatches["hidden_locomotion_assistance_executed"] = {
            "expected": False, "observed": hidden.get("hidden_locomotion_assistance_executed")}
    if mismatches:
        raise ValueError(f"canonical identity checks failed: {mismatches}")
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
        "condition_membership": sorted(conditions),
        "serialized_condition_order_is_semantic": False,
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
