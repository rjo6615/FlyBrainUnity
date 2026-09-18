"""Canonical command-line entry point for the M5D-4E diagnostic."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import traceback

from .sensory_feedback_boundary import DURATION_MS, SEED, analyze, base_report, verify_provenance

DEFAULT_OUTPUT = Path(__file__).with_name("interface_output") / "sensory_feedback_boundary_100ms.json"


def atomic_write(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run_live(duration_ms=DURATION_MS, seed=SEED):
    if (duration_ms, seed) != (DURATION_MS, SEED):
        raise ValueError("M5D-4E protocol is fixed at 100.0 ms and seed 1")
    verify_provenance()
    # Invoke the exact locked M5D-4D runner.  Temporarily replace only its
    # post-run reducer so the same two complete condition traces are audited.
    from . import tactile_motor_closed_loop_audit as locked
    original_m5d4d_analyze = locked.analyze

    def reduce_traces(enabled, disabled):
        return analyze(enabled, disabled,
            _m5d4d_analyze=original_m5d4d_analyze)

    try:
        locked.analyze = reduce_traces
        return locked.run_live(duration_ms, seed)
    finally:
        locked.analyze = original_m5d4d_analyze


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--duration-ms", type=float, default=DURATION_MS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv); report = base_report()
    try:
        report["provenance"] = verify_provenance()
    except Exception as error:
        report.update(run_status="FAILED", classification="PROVENANCE_FAILURE",
            reason=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
    else:
        try:
            if args.live:
                report = run_live(args.duration_ms, args.seed)
        except (ImportError, ModuleNotFoundError) as error:
            report.update(run_status="UNAVAILABLE", reason=f"{type(error).__name__}: {error}")
        except Exception as error:
            report.update(run_status="FAILED", classification="DIAGNOSTIC_IMPLEMENTATION_FAILURE",
                reason=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
    atomic_write(args.json, report)
    print(f"M5D-4E {report['run_status']}: {report['classification']}")
    return 0 if report["run_status"] in ("COMPLETE", "NOT_RUN", "UNAVAILABLE") else 1


if __name__ == "__main__": raise SystemExit(main())
