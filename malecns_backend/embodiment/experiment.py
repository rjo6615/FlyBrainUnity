"""Bounded real MaleCNS ↔ FlyGym experiment (never substitutes a fake body)."""
from pathlib import Path

from malecns_backend import MaleCNSBrain, load_malecns
from .body import FlyGymBody
from .loop import EmbodimentLoop
from .mappings import load_selected_pathway
from .motor import MotorActivityObserver, MotorDecoder
from .sensory import SensoryEncoder
from .telemetry import JSONLTelemetry


def run_real_experiment(duration_ms=10, seed=1,
                        telemetry_path=Path("malecns_backend/embodiment/closed_loop.jsonl")):
    """Run Test 4 with the real connectome and real body for a bounded interval.

    This routine contains no tonic drive, behavior choice, gait, root motion,
    or direct sensory-to-motor route. A fresh invocation gives a reproducible
    initial brain/body state when the installed FlyGym version is deterministic.
    """
    pathway = load_selected_pathway()
    brain = MaleCNSBrain(load_malecns()); brain.reset(seed)
    body = FlyGymBody(selected_joint_index=pathway.flygym_joint_index)
    observer = MotorActivityObserver({pathway.extensor.name:pathway.extensor.dense_indices,
                                      pathway.flexor.name:pathway.flexor.dense_indices})
    with JSONLTelemetry(telemetry_path) as telemetry:
        loop = EmbodimentLoop(brain, body, SensoryEncoder(pathway), observer,
                              MotorDecoder(pathway), pathway, telemetry=telemetry)
        initial = body.observe()
        rows = loop.run(duration_ms)
        final = body.observe()
    motor_spikes = sum(r["motor"]["increments"][pathway.extensor.name] +
                       r["motor"]["increments"][pathway.flexor.name] for r in rows)
    command_change = max((abs(r["command"].target_position_rad-r["before"].frame.tibia_angle_rad)
                          for r in rows), default=0.0)
    body_change = abs(final.frame.tibia_angle_rad-initial.frame.tibia_angle_rad)
    sensor_spikes = int(brain.spike_counts[list(pathway.sensor.dense_indices)].sum())
    nonsensory_spikes = int(brain.spike_counts.sum()) - sensor_spikes
    if motor_spikes and body_change > 1e-8:
        outcome = "A. SENSORIMOTOR PROPAGATION OBSERVED"
    elif nonsensory_spikes > 0:
        outcome = "B. NEURAL PROPAGATION WITHOUT MEANINGFUL BODY RESPONSE"
    else:
        outcome = "C. NO RELEVANT PROPAGATION"
    result = {"scientific_outcome":outcome, "sensory_spikes":sensor_spikes,
              "nonsensory_spikes":nonsensory_spikes, "motor_spikes":motor_spikes,
              "command_change_rad":command_change, "joint_change_rad":body_change,
              "neural_health":brain.diagnostics(), "performance":loop.performance(),
              "telemetry":str(telemetry_path)}
    body.close()
    return result
