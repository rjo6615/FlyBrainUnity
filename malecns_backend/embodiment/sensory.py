"""Modeled transduction from a physical T2-left tibia angle to MaleCNS drive."""
from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class LegSensoryFrame:
    """PHYSICS_MEASURED values, before any MaleCNS-specific transformation."""
    time_s: float
    tibia_angle_rad: float

    def validate(self):
        if not math.isfinite(self.time_s) or not math.isfinite(self.tibia_angle_rad):
            raise ValueError("physical sensory values must be finite")


@dataclass(frozen=True)
class EncodedSensoryDrive:
    """MODELED_TRANSDUCTION output for normal stochastic external input."""
    indices: np.ndarray
    rates_hz: np.ndarray
    population_name: str
    normalized_angle: float
    provenance: str = "MODELED_TRANSDUCTION"

    def apply(self, brain):
        # MaleCNSBrain converts each Hz value to a Bernoulli/Poisson-like event
        # probability rate*dt/1000 in its ordinary external-input pathway.
        brain.clear_external_drive()
        brain.set_external_drive(self.indices, self.rates_hz)


class SensoryEncoder:
    """Reference ``popCode`` semantics from fly-brain-main senses.js.

    q is in radians, x=(q-lo)/(hi-lo), preferred positions are (k+.5)/n,
    and r=120 exp(-(x-pref)^2/(2*0.25^2)) Hz. Rates <=5 Hz are omitted.
    There is no additional baseline. The rate-to-spike process lives in
    MaleCNSBrain and is deterministic for a fixed brain RNG seed.
    """
    angle_min_rad = -1.35
    angle_max_rad = 1.30
    width_normalized = 0.25
    maximum_rate_hz = 120.0
    cutoff_hz = 5.0
    baseline_hz = 0.0

    def __init__(self, pathway):
        self.pathway = pathway

    def encode(self, frame):
        frame.validate()
        indices = np.asarray(self.pathway.sensor.dense_indices, dtype=np.intp)
        n = len(indices)
        x = (frame.tibia_angle_rad - self.angle_min_rad) / (self.angle_max_rad - self.angle_min_rad)
        preferred = (np.arange(n, dtype=np.float64) + 0.5) / n
        rates = self.maximum_rate_hz * np.exp(-((x - preferred) ** 2) / (2 * self.width_normalized ** 2))
        rates[rates <= self.cutoff_hz] = 0.0
        rates = np.clip(rates, self.baseline_hz, self.maximum_rate_hz)
        return EncodedSensoryDrive(indices, rates, self.pathway.sensor.name, float(x))
