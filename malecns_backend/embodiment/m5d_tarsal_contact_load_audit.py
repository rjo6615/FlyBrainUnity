"""CLI for the read-only M5D audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from .m5d_tarsal_contact_load import DEFAULT_OUTPUT, build_audit, serialized_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="construct and reset FlyGym; never step it")
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    audit = build_audit(live=args.live)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(serialized_audit(audit), encoding="utf-8")
    print(f"M5D wrote {args.json}")
    print(audit["summary"])


if __name__ == "__main__":
    main()
