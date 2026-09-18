"""CLI for the deterministic, read-only M5B-2 broad-coxa audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from .m5b_multi_axis_coxa import DEFAULT_OUTPUT, build_multi_axis_audit, serialized_audit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="fail if the committed artifact is stale")
    args = parser.parse_args(argv)
    text = serialized_audit(build_multi_axis_audit())
    if args.check:
        if not args.json.exists() or args.json.read_text(encoding="utf-8") != text:
            print(f"stale M5B-2 artifact: {args.json}")
            return 1
        print(f"M5B-2 artifact is current: {args.json}")
        return 0
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(text, encoding="utf-8")
    print(f"Wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
