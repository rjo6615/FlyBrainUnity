"""Command-line writer and concise report for the M5C inventory."""
from __future__ import annotations

import argparse
from pathlib import Path

from .m5c_leg_sensory_inventory import DEFAULT_OUTPUT, build_inventory, serialized_inventory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print("[M5C 1/3] scanning the complete local population table")
    audit = build_inventory()
    print("[M5C 2/3] comparing source populations with M5A")
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(serialized_inventory(audit), encoding="utf-8")
    print("[M5C 3/3] wrote", args.json)
    print("POPULATION | LEG | BIOLOGICAL STRUCTURE | SENSOR TYPE | BODY COUNT | SOURCE SPECIFICITY | CURRENTLY USED? | CANDIDATE LEVEL")
    for row in audit["interesting_unused"]:
        print(" | ".join(map(str, (row["population_name"], row["leg"], row["biological_structure"],
                                  row["sensory_kind"], row["distinct_body_id_count"],
                                  row["source_classification"], "NO", row["candidate_level"]))))
    print("SUMMARY", audit["aggregate_summary"])


if __name__ == "__main__":
    main()
