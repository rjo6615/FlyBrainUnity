"""Single-attempt M5D-5D Windows runner and post-run telemetry audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import traceback

from .instrumented_proprioceptive_closed_loop import (AUTOMATIC_RETRIES,
    DURATION_MS, SEED, base_report, serialize, verify_provenance)

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE / "interface_output/instrumented_proprioceptive_closed_loop_100ms.json"
DEFAULT_TELEMETRY = BASE / "interface_output/instrumented_proprioceptive_closed_loop_telemetry.npz"


def atomic_write(path: Path, report) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(serialize(report)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def run_live(duration_ms=DURATION_MS, seed=SEED, telemetry_path=DEFAULT_TELEMETRY):
    if (duration_ms, seed, AUTOMATIC_RETRIES) != (100.0, 1, 0):
        raise ValueError("M5D-5D is fixed at 100 ms, seed 1, and zero retries")
    provenance = verify_provenance()
    from ._windows_instrumented_proprioceptive_closed_loop_adapter import run_canonical_pair
    return run_canonical_pair(provenance=provenance, telemetry_path=Path(telemetry_path))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration-ms", type=float, default=DURATION_MS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--telemetry", type=Path, default=DEFAULT_TELEMETRY)
    args = parser.parse_args(argv); report = base_report()
    if args.live:
        try: report = run_live(args.duration_ms, args.seed, args.telemetry)
        except (ImportError, ModuleNotFoundError) as error:
            report.update(run_status="UNAVAILABLE", classification="INSTRUMENTATION_FAILURE",
                reason=f"LIVE_RUNNER_UNAVAILABLE: {type(error).__name__}: {error}")
        except Exception as error:
            category = "PROVENANCE_FAILURE" if "provenance" in str(error).lower() else "INSTRUMENTATION_FAILURE"
            report.update(run_status="FAILED", classification=category,
                reason=f"{category}: {type(error).__name__}: {error}", traceback=traceback.format_exc())
    atomic_write(args.json, report)
    print(f"M5D-5D {report['run_status']}: {report.get('classification') or report.get('reason')}")
    return 0 if report["run_status"] in ("COMPLETE", "NOT_RUN", "UNAVAILABLE") else 1


if __name__ == "__main__": raise SystemExit(main())
