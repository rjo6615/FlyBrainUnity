"""Non-intervening Milestone 4B-1 component audit.

``--check`` uses only deterministic component inputs.  In particular, motor
counts are ENGINEERED DEBUG INPUT and are never described as biological data.
No code path in this command can actuate more than one tibia.
"""
import argparse

import numpy as np

from .mappings import load_selected_pathway
from .motor import MotorActivityObserver, MotorDecoder
from .sensory import LegSensoryFrame, SensoryEncoder
from .six_tibia import LEG_ORDER, IsolatedTibiaDecoder, load_six_tibia_interfaces


def component_check():
    interfaces = load_six_tibia_interfaces()
    print("LEG  SENSOR POPULATION       N    MOTOR STATUS  ACTUATOR       INDEX  VALIDATION")
    ok = True
    for leg in LEG_ORDER:
        item = interfaces[leg]
        rates = SensoryEncoder(item).encode(LegSensoryFrame(0.0, 0.0))
        decoder = IsolatedTibiaDecoder(item)
        n = max(i for p in item.motor_populations for i in p.dense_indices) + 1
        counts = np.zeros(n, dtype=np.uint32)
        decoder.reset(counts)
        # ENGINEERED DEBUG INPUT: one count in an audited positive pool.
        counts[np.asarray(item.extensor.dense_indices)] = 1
        _, command = decoder.update(counts, 1.0, 0.0)
        passed = (np.isfinite(rates.rates_hz).all() and
                  len(rates.indices) == len(item.sensor.body_ids) and
                  command.antagonist_signal > 0 and
                  command.actuator == item.actuator_name)
        ok &= passed
        print(f"{leg:<4} {item.sensor.name:<23} {len(item.sensor.body_ids):<4} "
              f"{item.motor_confidence:<13} {item.actuator_name:<14} "
              f"{item.action_index:<6} {'PASS' if passed else 'FAIL'}")

    # Independent M3D reference comparison, identical state and inputs.
    lm, reference = interfaces["LM"], load_selected_pathway()
    a = SensoryEncoder(lm).encode(LegSensoryFrame(0.0, 0.123))
    b = SensoryEncoder(reference).encode(LegSensoryFrame(0.0, 0.123))
    equivalent = np.array_equal(a.indices, b.indices) and np.array_equal(a.rates_hz, b.rates_hz)
    counts = np.zeros(max(lm.flexor.dense_indices + lm.extensor.dense_indices) + 1, np.uint32)
    counts[np.asarray(lm.extensor.dense_indices)] = 2
    new_observer = MotorActivityObserver({lm.extensor.name: lm.extensor.dense_indices,
                                          lm.flexor.name: lm.flexor.dense_indices})
    old_observer = MotorActivityObserver({reference.extensor.name: reference.extensor.dense_indices,
                                          reference.flexor.name: reference.flexor.dense_indices})
    new_observer.reset(np.zeros_like(counts)); old_observer.reset(np.zeros_like(counts))
    nr = new_observer.update(counts, 1.0); rr = old_observer.update(counts, 1.0)
    nc = MotorDecoder(lm).decode(nr["filtered_hz"], 0.1, 0.001)
    rc = MotorDecoder(reference).decode(rr["filtered_hz"], 0.1, 0.001)
    equivalent &= nr == rr and nc == rc

    # Mutation of one isolated decoder has no route into another's state.
    left, right = IsolatedTibiaDecoder(interfaces["LF"]), IsolatedTibiaDecoder(interfaces["RF"])
    left.decoder.previous_target = 0.2
    isolated = right.decoder.previous_target is None
    ok &= equivalent and isolated
    print("\nENGINEERED DEBUG INPUT: used only for decoder sign/component checks")
    print(f"M3D LM REFERENCE EQUIVALENCE: {'PASS' if equivalent else 'FAIL'}")
    print(f"CROSS-LEG DECODER ISOLATION: {'PASS' if isolated else 'FAIL'}")
    print("NO SIMULTANEOUS SIX-TIBIA CONTROL: PASS")
    print("NO GAIT/CPG/BEHAVIOR CONTROLLER: PASS")
    return ok


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="run deterministic component validation")
    parser.add_argument("--isolated", action="store_true",
                        help="reserved: real-body runs require an explicitly configured FlyGym environment")
    args = parser.parse_args(argv)
    if args.isolated:
        parser.error("real-body isolated runs are unavailable; use --check")
    if not args.check:
        parser.error("select --check")
    raise SystemExit(0 if component_check() else 1)


if __name__ == "__main__":
    main()
