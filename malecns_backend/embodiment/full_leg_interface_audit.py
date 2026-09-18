"""Command-line entry point for the deterministic M5A interface audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from .full_leg_interface import DEFAULT_OUTPUT, build_audit, enumerate_live_actuators, serialized_audit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--live", action="store_true", help="require read-only introspection of an installed FlyGym model")
    args = parser.parse_args(argv)
    live = enumerate_live_actuators() if args.live else None
    audit = build_audit(live)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(serialized_audit(audit), encoding="utf-8")
    print(f"{'ACTUATOR':<22} {'SENSOR':<10} {'MOTOR':<10} {'CONFIDENCE':<30} {'TIER':<6} ELIGIBLE")
    for item in audit["actuator_records"]:
        print(f"{item['actuator_name']:<22} {item['sensory_confidence']:<10} {item['motor_confidence']:<10} {item['overall_interface_confidence']:<30} {item['activation_tier']:<6} {str(item['activation_eligible']).upper()}")
    summary = audit["summary"]
    for label, key in (("TOTAL ACTUATORS", "total_actuators"), *( (f"TIER {i}", f"tier_{i}") for i in range(1, 5)), ("ACTIVATION ELIGIBLE", "activation_eligible"), ("SENSORY MAPPED", "sensory_mapped"), ("MOTOR MAPPED", "motor_mapped"), ("BOTH MAPPED", "both_mapped")):
        print(f"{label}: {summary[key]}")
    print("\nSix existing tibia interfaces:")
    for item in audit["six_tibia_regression"]["interfaces"]:
        print(f"  {item['leg']} tibia ({item['actuator']}): {'PASS' if item['passed'] else 'FAIL'}")
    print("SIX-TIBIA REGRESSION: " + ("PASS" if audit["six_tibia_regression"]["passed"] else "FAIL"))
    if args.live:
        print("\nDiscovered physical action DOFs by leg:")
        for leg in ("LF", "LM", "LH", "RF", "RM", "RH"):
            dofs = [item["mujoco_metadata"]["joint_name"] for item in audit["actuator_records"]
                    if item["leg"] == leg]
            print(f"  {leg}: " + ", ".join(dofs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
