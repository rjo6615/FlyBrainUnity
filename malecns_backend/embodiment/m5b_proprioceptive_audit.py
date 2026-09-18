"""CLI for the read-only M5B-1 proprioceptive dissection."""
from __future__ import annotations

import argparse
from pathlib import Path

from .m5b_proprioceptive_dissection import DEFAULT_OUTPUT, build_dissection, serialized_dissection


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--annotations-only", action="store_true",
                        help="skip MaleCNS decoding and explicitly mark connectivity unavailable")
    args = parser.parse_args(argv)
    graph = None
    print("[M5B-1 1/4] Reading locked M4A/M5A annotations and mappings...", flush=True)
    if not args.annotations_only:
        print("[M5B-1 2/4] Decoding and validating the MaleCNS graph (this may take several minutes)...", flush=True)
        from malecns_backend import load_malecns
        graph = load_malecns()
        print("[M5B-1 2/4] MaleCNS graph ready.", flush=True)
    else:
        print("[M5B-1 2/4] Graph decode skipped by --annotations-only.", flush=True)
    print("[M5B-1 3/4] Computing annotation, overlap, and descriptive connectivity evidence...", flush=True)
    result = build_dissection(graph=graph)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(serialized_dissection(result), encoding="utf-8")
    summary = result["aggregate_summary"]
    print(f"[M5B-1 4/4] Wrote {args.json}", flush=True)
    for key, value in summary.items():
        print(f"{key.upper()}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
