"""Headless Milestone 3B engineering audit and experiment entry point."""
import argparse
import importlib.util
import json
import platform
import time

import numpy as np

from malecns_backend.loader import process_memory_bytes
from .mappings import load_selected_pathway
from .motor import MotorActivityObserver, MotorDecoder
from .sensory import LegSensoryFrame, SensoryEncoder


SECTIONS = ("MAPPING", "SENSORY ENCODER", "MOTOR DECODER", "TIMING", "BASELINE",
            "SENSORY-ONLY TEST", "MOTOR-ISOLATION TEST", "CLOSED-LOOP TEST",
            "CAUSAL CONTROL", "NUMERICAL HEALTH", "PERFORMANCE", "SCIENTIFIC PROVENANCE")


def heading(name):
    print(f"\n=== {name} ===")


def component_audit():
    """Fast invariant checks. These are not presented as a body experiment."""
    pathway = load_selected_pathway()
    encoder = SensoryEncoder(pathway)
    drive = encoder.encode(LegSensoryFrame(0.0, 0.0))
    observer = MotorActivityObserver({pathway.extensor.name:pathway.extensor.dense_indices,
                                      pathway.flexor.name:pathway.flexor.dense_indices})
    counts = np.zeros(max(observer.used)+1, np.uint32); observer.reset(counts)
    counts[np.asarray(pathway.extensor.dense_indices)] += 1
    activity = observer.update(counts, 1.0)
    decoder = MotorDecoder(pathway)
    command = decoder.decode(activity["filtered_hz"], 0.0, .001)
    assert np.isfinite(drive.rates_hz).all() and np.max(drive.rates_hz) <= 120
    assert command.actuator == pathway.flygym_joint_name and command.target_position_rad > 0
    return pathway, drive, activity, command


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-real", action="store_true",
                        help="require and run the real bounded FlyGym/MaleCNS experiment")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    pathway, drive, activity, command = component_audit()
    flygym_available = importlib.util.find_spec("flygym") is not None

    heading("MAPPING")
    print(pathway.selection_reason)
    print(json.dumps({"sensor":pathway.sensor.name, "sensor_body_ids":pathway.sensor.body_ids,
          "extensor":pathway.extensor.name, "extensor_body_ids":pathway.extensor.body_ids,
          "flexor":pathway.flexor.name, "flexor_body_ids":pathway.flexor.body_ids,
          "flygym_actuator":pathway.flygym_joint_name, "action_index":pathway.flygym_joint_index}, indent=2))
    heading("SENSORY ENCODER")
    print(f"reference Gaussian population code: {len(drive.indices)} cells, zero-angle max={drive.rates_hz.max():.6f} Hz")
    heading("MOTOR DECODER")
    print(f"ENGINEERED DEBUG INPUT: one count/extensor neuron -> {activity['filtered_hz'][pathway.extensor.name]:.6f} filtered Hz")
    print(f"MODELED MOTOR DECODING target={command.actuator} command={command.target_position_rad:.6f} rad")
    heading("TIMING")
    print("neural=0.5 ms; physics=0.1 ms; control=sensory=motor=1.0 ms; 2 neural and 10 physics steps/control")

    real_status = "NOT RUN"
    block = None
    if args.run_real:
        if not flygym_available:
            block = ("FlyGym/NeuroMechFly and MuJoCo are not installed in this environment "
                     f"(Python {platform.python_version()}); no fake body substitutes for Test 4.")
        else:
            # Import only on explicit request: a real run is intentionally expensive.
            from .experiment import run_real_experiment
            result = run_real_experiment()
            real_status = result["scientific_outcome"]

    for name, text in (
        ("BASELINE", "real NeuroMechFly experiment not run"),
        ("SENSORY-ONLY TEST", "component target/rate invariants passed; real NeuroMechFly experiment not run"),
        ("MOTOR-ISOLATION TEST", "ENGINEERED DEBUG INPUT component isolation passed; real actuator test not run"),
        ("CLOSED-LOOP TEST", f"scientific outcome: {real_status}"),
        ("CAUSAL CONTROL", "not applicable unless a real Test 4 body response is observed"),
        ("NUMERICAL HEALTH", "all component encoder/filter/decoder values finite"),
    ):
        heading(name); print(text)
    heading("PERFORMANCE")
    rss, peak = process_memory_bytes()
    print(json.dumps({"component_wall_clock_s":time.perf_counter()-started,
                      "rss_bytes":rss, "peak_rss_bytes":peak}))
    heading("SCIENTIFIC PROVENANCE")
    print("PHYSICS_MEASURED angle -> MODELED_TRANSDUCTION rates -> CONNECTOME_DERIVED graph ->")
    print("ANNOTATION_DERIVED motor pools -> MODELED_MOTOR_DECODING command; safety clamps are engineering constraints.")
    print("Behavior controller/state machine participated: NO")
    if block:
        print(f"\nREAL NEUROMECHFLY VALIDATION BLOCKED: {block}")
        return 2
    print("\nMALECNS EMBODIMENT COMPONENT INTERFACE VALIDATION PASSED")
    if not args.run_real:
        print("REAL NEUROMECHFLY CLOSED-LOOP EXPERIMENT NOT RUN (use --run-real; this is not outcome A/B/C)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
