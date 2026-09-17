"""Explicit causal, multi-rate MaleCNS/body scheduler."""
from dataclasses import dataclass
import math
import time

import numpy as np

from .telemetry import TelemetrySample


@dataclass(frozen=True)
class TimingConfig:
    neural_dt_ms: float = 0.5
    physics_dt_ms: float = 0.1
    control_dt_ms: float = 1.0
    sensory_interval_ms: float = 1.0
    motor_interval_ms: float = 1.0

    def __post_init__(self):
        values = (self.neural_dt_ms, self.physics_dt_ms, self.control_dt_ms,
                  self.sensory_interval_ms, self.motor_interval_ms)
        if any(x <= 0 or not math.isfinite(x) for x in values):
            raise ValueError("all timing intervals must be finite and positive")
        for smaller, label in ((self.neural_dt_ms, "neural"), (self.physics_dt_ms, "physics")):
            ratio = self.control_dt_ms / smaller
            if not math.isclose(ratio, round(ratio), abs_tol=1e-9):
                raise ValueError(f"control_dt must contain an integer number of {label} steps")
        if self.sensory_interval_ms != self.control_dt_ms or self.motor_interval_ms != self.control_dt_ms:
            raise ValueError("Milestone 3B samples and decodes exactly once per control interval")

    @property
    def neural_steps_per_control(self):
        return round(self.control_dt_ms / self.neural_dt_ms)

    @property
    def physics_steps_per_control(self):
        return round(self.control_dt_ms / self.physics_dt_ms)


class EmbodimentLoop:
    """Observe -> encode -> neural steps -> decode -> command -> physics.

    The command affects only the *subsequent* physics interval, preventing a
    one-frame look-ahead. Sensory drive is never routed directly to the motor.
    """
    def __init__(self, brain, body, encoder, observer, decoder, pathway,
                 timing=TimingConfig(), telemetry=None):
        if not math.isclose(brain.config.dt, timing.neural_dt_ms, abs_tol=1e-12):
            raise ValueError("MaleCNS neural dt differs from scheduler neural dt")
        if not math.isclose(body.timestep_s * 1000, timing.physics_dt_ms, abs_tol=1e-12):
            raise ValueError("body physics dt differs from scheduler physics dt")
        self.brain, self.body, self.encoder = brain, body, encoder
        self.observer, self.decoder, self.pathway = observer, decoder, pathway
        self.timing, self.telemetry = timing, telemetry
        self.control_steps = 0
        self.wall_started = None
        self.observer.reset(self.brain.spike_counts)

    def step(self, sensory_enabled=True, motor_enabled=True):
        if self.wall_started is None:
            self.wall_started = time.perf_counter()
        before = self.body.observe()
        encoded = self.encoder.encode(before.frame)
        if sensory_enabled:
            encoded.apply(self.brain)
        else:
            self.brain.clear_external_drive()
        sensor_before = int(self.brain.spike_counts[encoded.indices].sum())
        for _ in range(self.timing.neural_steps_per_control):
            self.brain.step()
        motor = self.observer.update(self.brain.spike_counts, self.timing.motor_interval_ms)
        rates, increments = motor["filtered_hz"], motor["increments"]
        command = self.decoder.decode(rates, before.frame.tibia_angle_rad,
                                      self.timing.control_dt_ms / 1000)
        after = self.body.step(command, self.timing.physics_steps_per_control) if motor_enabled else before
        self.control_steps += 1
        if self.telemetry is not None:
            self.telemetry.write(TelemetrySample(
                self.control_steps * self.timing.control_dt_ms / 1000,
                after.frame.time_s, self.brain.time_ms,
                after.frame.tibia_angle_rad, float(encoded.rates_hz.mean()),
                float(encoded.rates_hz.max()),
                int(self.brain.spike_counts[encoded.indices].sum()) - sensor_before,
                int(self.brain.spike_counts.sum()), increments[self.pathway.extensor.name],
                increments[self.pathway.flexor.name], rates[self.pathway.extensor.name],
                rates[self.pathway.flexor.name], command.target_position_rad,
                after.contact_force_n, after.body_position_m, after.body_orientation,
            ))
        return {"before": before, "after": after, "encoded": encoded,
                "motor": motor, "command": command}

    def run(self, duration_ms, **step_options):
        count = duration_ms / self.timing.control_dt_ms
        if not math.isclose(count, round(count), abs_tol=1e-9):
            raise ValueError("duration must be a multiple of control_dt")
        return [self.step(**step_options) for _ in range(round(count))]

    def performance(self):
        wall = 0.0 if self.wall_started is None else time.perf_counter() - self.wall_started
        simulated = self.control_steps * self.timing.control_dt_ms / 1000
        return {
            "wall_clock_s": wall, "simulated_s": simulated,
            "real_time_factor": simulated / wall if wall else 0.0,
            "neural_steps_per_s": self.control_steps * self.timing.neural_steps_per_control / wall if wall else 0.0,
            "physics_steps_per_s": self.control_steps * self.timing.physics_steps_per_control / wall if wall else 0.0,
        }
