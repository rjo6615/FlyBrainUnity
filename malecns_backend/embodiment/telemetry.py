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

    def validate(self):
        def numbers(value):
            if isinstance(value, (tuple, list)):
                return value
            return (value,)
        for key, value in asdict(self).items():
            if key.endswith("count") or key.endswith("increment"):
                if value < 0:
                    raise ValueError(f"negative telemetry count: {key}")
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
