"""Spike-count observation and conservative single-joint motor decoding."""
from dataclasses import dataclass
import math

import numpy as np


class MotorActivityObserver:
    """Observe cumulative counts using the reference 40-ms Euler low-pass.

    For interval Δt: instantaneous_i = Δcount_i*1000/Δt (Hz), then
    filtered_i += (Δt/40)*(instantaneous_i-filtered_i). Population output is
    the arithmetic mean of per-neuron filtered rates.
    """
    def __init__(self, populations, tau_ms=40.0):
        if tau_ms <= 0:
            raise ValueError("tau_ms must be positive")
        self.populations = {name: np.asarray(ix, dtype=np.intp) for name, ix in populations.items()}
        used = sorted(set().union(*(set(x.tolist()) for x in self.populations.values())))
        self.used = np.asarray(used, dtype=np.intp)
        self.tau_ms = float(tau_ms)
        self.last_counts = None
        self.filtered_hz = np.zeros(len(self.used), dtype=np.float64)
        self._positions = {int(index): pos for pos, index in enumerate(self.used)}

    def reset(self, spike_counts=None):
        self.last_counts = None if spike_counts is None else np.asarray(spike_counts, dtype=np.uint32)[self.used].copy()
        self.filtered_hz.fill(0)

    def update(self, spike_counts, interval_ms):
        if interval_ms <= 0 or interval_ms > self.tau_ms:
            raise ValueError("observation interval must be in (0, tau_ms]")
        current = np.asarray(spike_counts, dtype=np.uint32)[self.used]
        if self.last_counts is None:
            increments = current.astype(np.uint64)
        else:
            increments = (current - self.last_counts).astype(np.uint32).astype(np.uint64)
        self.last_counts = current.copy()
        instantaneous = increments.astype(np.float64) * (1000.0 / interval_ms)
        self.filtered_hz += (interval_ms / self.tau_ms) * (instantaneous - self.filtered_hz)
        rates = {}
        inc = {}
        detail = {}
        for name, indices in self.populations.items():
            positions = [self._positions[int(i)] for i in indices]
            rates[name] = float(np.mean(self.filtered_hz[positions])) if positions else 0.0
            inc[name] = int(np.sum(increments[positions])) if positions else 0
            detail[name] = {
                "cumulative_counts": [int(x) for x in current[positions]],
                "increments": [int(x) for x in increments[positions]],
                "instantaneous_hz": [float(x) for x in instantaneous[positions]],
                "filtered_hz": [float(x) for x in self.filtered_hz[positions]],
            }
        return {"increments": inc, "filtered_hz": rates, "neurons": detail}


@dataclass(frozen=True)
class MotorSafety:
    """ENGINEERING constraints; these do not encode a gait or posture."""
    joint_min_rad: float = -1.35
    joint_max_rad: float = 1.30
    max_offset_rad: float = 0.25
    max_velocity_rad_s: float = 4.0


@dataclass(frozen=True)
class MotorCommand:
    actuator: str
    target_position_rad: float
    unclamped_position_rad: float
    extensor_hz: float
    flexor_hz: float
    extensor_activation: float = 0.0
    flexor_activation: float = 0.0
    antagonist_signal: float = 0.0
    raw_decoder_output_rad: float = 0.0
    magnitude_clamped_output_rad: float = 0.0
    range_clamped_position_rad: float = 0.0
    slew_clamped_position_rad: float = 0.0
    provenance: str = "MODELED_MOTOR_DECODING"


class MotorDecoder:
    """Map annotated antagonist activity to only the selected position actuator."""
    half_activation_hz = 17.0

    def __init__(self, pathway, safety=MotorSafety()):
        self.pathway = pathway
        self.safety = safety
        self.previous_target = None

    @classmethod
    def activation(cls, rate_hz):
        if not math.isfinite(rate_hz) or rate_hz < 0:
            raise ValueError("motor rates must be finite and nonnegative")
        return 1.0 - math.exp(-rate_hz * math.log(2.0) / cls.half_activation_hz)

    def reset(self):
        self.previous_target = None

    def decode(self, rates, current_position_rad, control_dt_s, apply_neural_offset=True):
        if not math.isfinite(current_position_rad) or control_dt_s <= 0:
            raise ValueError("invalid physical state or control interval")
        ext = float(rates[self.pathway.extensor.name])
        flex = float(rates[self.pathway.flexor.name])
        # Directions +1/-1 come from the audited bodymap. Magnitude is modeled.
        ext_activation = self.activation(ext)
        flex_activation = self.activation(flex)
        antagonist = ext_activation - flex_activation
        # The activation difference is mathematically in [-1, 1].  Keep the
        # explicit diagnostic stage without introducing a second clamp.
        raw_offset = self.safety.max_offset_rad * antagonist
        offset = raw_offset
        # Actuator decomposition (before safety constraints):
        # candidate = base_target + applied_neural_offset, where base_target is
        # the current measured joint position.  The control condition retains
        # all range/slew/holding semantics and zeros only the latter term.
        applied_offset = offset if apply_neural_offset else 0.0
        raw = current_position_rad + applied_offset
        bounded = min(self.safety.joint_max_rad, max(self.safety.joint_min_rad, raw))
        prior = current_position_rad if self.previous_target is None else self.previous_target
        delta = self.safety.max_velocity_rad_s * control_dt_s
        target = min(prior + delta, max(prior - delta, bounded))
        target = min(self.safety.joint_max_rad, max(self.safety.joint_min_rad, target))
        self.previous_target = target
        return MotorCommand(self.pathway.flygym_joint_name, target, raw, ext, flex,
                            ext_activation, flex_activation, antagonist, raw_offset,
                            offset, bounded, target)
