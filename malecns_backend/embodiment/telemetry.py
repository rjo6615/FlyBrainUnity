"""Bounded, selected-population JSONL telemetry."""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class TelemetrySample:
    simulation_time_s: float
    physics_time_s: float
    neural_time_ms: float
    tibia_angle_rad: float
    encoded_rate_mean_hz: float
    encoded_rate_max_hz: float
    sensory_spike_count: int
    total_cns_spike_count: int
    extensor_spike_increment: int
    flexor_spike_increment: int
    extensor_filtered_hz: float
    flexor_filtered_hz: float
    actuator_target_rad: float
    contact_force_n: float
    body_position_m: tuple[float, float, float]
    body_orientation: tuple[float, ...]
    control_step: int
    neural_step: int
    physics_step: int
    input_tibia_angle_rad: float
    joint_velocity_rad_s: float
    commanded_joint_position_rad: float
    actuator_position_rad: float
    encoded_rate_min_hz: float
    encoded_nonzero_neurons: int
    encoded_total_rate_hz: float
    cumulative_sensory_spikes: int
    distinct_sensory_neurons: int
    cns_spike_increment: int
    distinct_cns_neurons: int
    motor_neurons: dict
    extensor_activation: float
    flexor_activation: float
    antagonist_signal: float
    raw_motor_output_rad: float
    magnitude_clamped_output_rad: float
    range_clamped_position_rad: float
    slew_clamped_position_rad: float
    prior_actuator_command_rad: float

    def validate(self):
        def numbers(value):
            if isinstance(value, (tuple, list)):
                return value
            return (value,)
        for key, value in asdict(self).items():
            if key.endswith("count") or key.endswith("increment"):
                if value < 0:
                    raise ValueError(f"negative telemetry count: {key}")
            elif isinstance(value, dict):
                continue
            elif not all(math.isfinite(float(x)) for x in numbers(value)):
                raise ValueError(f"nonfinite telemetry: {key}")


class JSONLTelemetry:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8")

    def write(self, sample):
        sample.validate()
        self._file.write(json.dumps(asdict(sample), separators=(",", ":")) + "\n")
        self._file.flush()

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
