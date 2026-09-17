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
        self.wall_finished = None
        self.instrumentation_wall_s = 0.0
        self.neural_wall_s = 0.0
        self.physics_wall_s = 0.0
        self.initial_angle_rad = None
        self.last_command_rad = None
        self.first_times_s = {
            "sensory_spike": None, "downstream_spike": None,
            "extensor_spike": None, "flexor_spike": None,
            "decoded_motor_signal": None, "actuator_target_update": None,
            "physical_tibia_response": None,
        }
        self.observer.reset(self.brain.spike_counts)

    def step(self, sensory_enabled=True, motor_enabled=True,
             apply_neural_motor=True):
        if self.wall_started is None:
            self.wall_started = time.perf_counter()
        before = self.body.observe()
        if self.initial_angle_rad is None:
            self.initial_angle_rad = before.frame.tibia_angle_rad
            self.last_command_rad = before.frame.tibia_angle_rad
        encoded = self.encoder.encode(before.frame)
        if sensory_enabled:
            encoded.apply(self.brain)
        else:
            self.brain.clear_external_drive()
        sensor_before = int(self.brain.spike_counts[encoded.indices].sum())
        cns_before = int(self.brain.spike_counts.sum())
        diagnostic_started = time.perf_counter()
        sensor_set = set(int(x) for x in encoded.indices)
        extensor_set = set(int(x) for x in self.pathway.extensor.dense_indices)
        flexor_set = set(int(x) for x in self.pathway.flexor.dense_indices)
        self.instrumentation_wall_s += time.perf_counter() - diagnostic_started
        for _ in range(self.timing.neural_steps_per_control):
            neural_started = time.perf_counter()
            fired = self.brain.step()
            self.neural_wall_s += time.perf_counter() - neural_started
            diagnostic_started = time.perf_counter()
            fired_set = set(int(x) for x in fired)
            event_time_s = self.brain.time_ms / 1000.0
            for key, happened in (
                ("sensory_spike", bool(fired_set & sensor_set)),
                ("downstream_spike", bool(fired_set - sensor_set)),
                ("extensor_spike", bool(fired_set & extensor_set)),
                ("flexor_spike", bool(fired_set & flexor_set)),
            ):
                if happened and self.first_times_s[key] is None:
                    self.first_times_s[key] = event_time_s
            self.instrumentation_wall_s += time.perf_counter() - diagnostic_started
        motor = self.observer.update(self.brain.spike_counts, self.timing.motor_interval_ms)
        rates, increments = motor["filtered_hz"], motor["increments"]
        command = self.decoder.decode(rates, before.frame.tibia_angle_rad,
                                      self.timing.control_dt_ms / 1000,
                                      apply_neural_offset=apply_neural_motor)
        prior_command_rad = self.last_command_rad
        diagnostic_started = time.perf_counter()
        if command.antagonist_signal != 0 and self.first_times_s["decoded_motor_signal"] is None:
            self.first_times_s["decoded_motor_signal"] = self.brain.time_ms / 1000.0
        if (command.target_position_rad != self.last_command_rad and
                self.first_times_s["actuator_target_update"] is None):
            self.first_times_s["actuator_target_update"] = self.brain.time_ms / 1000.0
        self.last_command_rad = command.target_position_rad
        self.instrumentation_wall_s += time.perf_counter() - diagnostic_started
        physics_started = time.perf_counter()
        after = self.body.step(command, self.timing.physics_steps_per_control) if motor_enabled else before
        self.physics_wall_s += time.perf_counter() - physics_started
        diagnostic_started = time.perf_counter()
        if (abs(after.frame.tibia_angle_rad - self.initial_angle_rad) > 1e-12 and
                self.first_times_s["physical_tibia_response"] is None):
            self.first_times_s["physical_tibia_response"] = after.frame.time_s
        self.instrumentation_wall_s += time.perf_counter() - diagnostic_started
        self.control_steps += 1
        if self.telemetry is not None:
            diagnostic_started = time.perf_counter()
            motor_neurons = {
                self.pathway.extensor.name: {
                    "body_ids": list(self.pathway.extensor.body_ids),
                    **motor["neurons"][self.pathway.extensor.name],
                },
                self.pathway.flexor.name: {
                    "body_ids": list(self.pathway.flexor.body_ids),
                    **motor["neurons"][self.pathway.flexor.name],
                },
            }
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
                self.control_steps, round(self.brain.time_ms / self.timing.neural_dt_ms),
                self.body.physics_steps, before.frame.tibia_angle_rad,
                after.joint_velocity_rad_s, command.target_position_rad,
                (after.frame.tibia_angle_rad if after.actuator_position_rad is None
                 else after.actuator_position_rad),
                float(encoded.rates_hz.min()), int(np.count_nonzero(encoded.rates_hz)),
                float(encoded.rates_hz.sum()),
                int(self.brain.spike_counts[encoded.indices].sum()),
                int(np.count_nonzero(self.brain.spike_counts[encoded.indices])),
                int(self.brain.spike_counts.sum()) - cns_before,
                int(np.count_nonzero(self.brain.spike_counts)), motor_neurons,
                command.extensor_activation, command.flexor_activation,
                command.antagonist_signal, command.raw_decoder_output_rad,
                command.magnitude_clamped_output_rad,
                command.range_clamped_position_rad, command.slew_clamped_position_rad,
                prior_command_rad,
            ))
            self.instrumentation_wall_s += time.perf_counter() - diagnostic_started
        return {"before": before, "after": after, "encoded": encoded,
                "motor": motor, "command": command,
                "decoded_neural_offset_rad": command.raw_decoder_output_rad,
                "applied_neural_offset_rad": (command.raw_decoder_output_rad
                                               if apply_neural_motor else 0.0),
                "base_actuator_target_rad": before.frame.tibia_angle_rad,
                "sensory_spike_increment": int(
                    self.brain.spike_counts[encoded.indices].sum()) - sensor_before,
                "cns_spike_increment": int(self.brain.spike_counts.sum()) - cns_before}

    def run(self, duration_ms, **step_options):
        count = duration_ms / self.timing.control_dt_ms
        if not math.isclose(count, round(count), abs_tol=1e-9):
            raise ValueError("duration must be a multiple of control_dt")
        rows = [self.step(**step_options) for _ in range(round(count))]
        self.wall_finished = time.perf_counter()
        return rows

    def performance(self):
        wall = (0.0 if self.wall_started is None else
                (self.wall_finished or time.perf_counter()) - self.wall_started)
        simulated = self.control_steps * self.timing.control_dt_ms / 1000
        return {
            "wall_clock_s": wall, "simulated_s": simulated,
            "real_time_factor": simulated / wall if wall else 0.0,
            "neural_steps_per_s": self.control_steps * self.timing.neural_steps_per_control / wall if wall else 0.0,
            "physics_steps_per_s": self.control_steps * self.timing.physics_steps_per_control / wall if wall else 0.0,
            "neural_steps": self.control_steps * self.timing.neural_steps_per_control,
            "physics_steps": self.control_steps * self.timing.physics_steps_per_control,
            "control_steps": self.control_steps,
            "average_neural_step_s": self.neural_wall_s / (self.control_steps * self.timing.neural_steps_per_control)
                                     if self.control_steps else 0.0,
            "neural_wall_clock_s": self.neural_wall_s,
            "physics_wall_clock_s": self.physics_wall_s,
            "diagnostic_overhead_s": self.instrumentation_wall_s,
            "instrumentation_wall_clock_s": self.instrumentation_wall_s,
        }
