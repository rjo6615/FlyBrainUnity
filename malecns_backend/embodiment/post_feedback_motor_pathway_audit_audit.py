"""Command-line entry point for the read-only M5D-5C audit."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from .post_feedback_motor_pathway_audit import DEFAULT_OUTPUT, analyze, serialize, verify_provenance


def atomic_write(path: Path, report) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(serialize(report)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    artifact, provenance = verify_provenance()
    report = analyze(artifact, provenance)
    atomic_write(args.json, report)
    print(f"M5D-5C {report['run_status']}: {report['classification']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
