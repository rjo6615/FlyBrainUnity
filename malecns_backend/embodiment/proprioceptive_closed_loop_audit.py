"""Canonical, single-attempt Windows entry point for M5D-5B.

The runner delegates construction and trace capture to the locked M5D-5A and
M5D-4C primitives.  Importing this module never starts the experiment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import traceback

from .proprioceptive_closed_loop import (AUTOMATIC_RETRIES, DURATION_MS, SEED,
    base_report, serialize, verify_provenance)

DEFAULT_OUTPUT = Path(__file__).with_name("interface_output") / "proprioceptive_closed_loop_100ms.json"


def atomic_write(path: Path, report) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(serialize(report)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def run_live(duration_ms: float = DURATION_MS, seed: int = SEED):
    """Execute exactly once through the repository's live Windows adapter."""
    if (duration_ms, seed, AUTOMATIC_RETRIES) != (100.0, 1, 0):
        raise ValueError("M5D-5B protocol is fixed at 100 ms, seed 1, no retries")
    provenance = verify_provenance()
    from ._windows_proprioceptive_closed_loop_adapter import run_canonical_pair
    return run_canonical_pair(provenance=provenance)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration-ms", type=float, default=DURATION_MS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv); report = base_report()
    if args.live:
        try:
            report = run_live(args.duration_ms, args.seed)
        except (ImportError, ModuleNotFoundError) as error:
            report.update(run_status="UNAVAILABLE", classification="LIVE_RUNNER_UNAVAILABLE",
                reason=f"LIVE_RUNNER_UNAVAILABLE: {type(error).__name__}: {error}",
                traceback=traceback.format_exc())
        except Exception as error:
            category = ("PROVENANCE_FAILURE" if "provenance" in str(error).lower() else
                "PHYSICS_FAILURE" if type(error).__name__ == "PhysicsFailure" else
                "LIVE_RUNNER_IMPLEMENTATION_FAILURE")
            report.update(run_status="FAILED", classification=category,
                reason=f"{category}: {type(error).__name__}: {error}",
                traceback=traceback.format_exc())
    atomic_write(args.json, report)
    detail = (report.get("reason") if report["run_status"] in ("UNAVAILABLE", "FAILED")
        else report.get("classification")) or "unspecified failure"
    print(f"M5D-5B {report['run_status']}: {detail}")
    return 0 if report["run_status"] in ("COMPLETE", "NOT_RUN", "UNAVAILABLE") else 1


if __name__ == "__main__":
    raise SystemExit(main())
