"""Fixed, numeric compact-telemetry schema for the frozen M7 runner.

This module is deliberately independent of FlyGym.  It can therefore exercise
the exact serializer contract without constructing or advancing a simulation.
"""
from __future__ import annotations

from dataclasses import dataclass
import io
from typing import Any, Mapping

import numpy as np


PHYSICS_TRANSITIONS = 50_000
PHYSICS_STATE_SAMPLES = PHYSICS_TRANSITIONS + 1
NEURAL_SAMPLES = 10_000
SENSORY_CHANNELS = 6
ADMITTED_MOTOR_CHANNELS = 11


class TelemetrySchemaError(RuntimeError):
    """An observed telemetry value did not match its declared schema."""

    run_status = "ABORTED_IMPLEMENTATION_TELEMETRY_SCHEMA_FAILURE"

    def __init__(self, field: str, expected_shape: tuple[int, ...],
                 observed_shape: tuple[Any, ...], sample_index: int,
                 simulation_time_ms: float):
        self.field = field
        self.expected_shape = expected_shape
        self.observed_shape = observed_shape
        self.sample_index = sample_index
        self.simulation_time_ms = simulation_time_ms
        super().__init__(f"telemetry schema failure: field={field}, expected_shape={expected_shape}, "
                         f"observed_shape={observed_shape}, sample_index={sample_index}, "
                         f"simulation_time_ms={simulation_time_ms}")

    def details(self) -> dict[str, Any]:
        return {"field": self.field, "expected_shape": list(self.expected_shape),
                "observed_shape": list(self.observed_shape),
                "sample_index": self.sample_index,
                "simulation_time_ms": self.simulation_time_ms}


@dataclass(frozen=True)
class Field:
    sample_shape: tuple[int, ...]
    dtype: np.dtype
    cadence: str
    meaning: str


def build_schema(*, qpos_shape: tuple[int, ...], qvel_shape: tuple[int, ...],
                 ctrl_shape: tuple[int, ...], contact_forces_shape: tuple[int, ...],
                 joint_shape: tuple[int, ...] = (42,), action_shape: tuple[int, ...] = (42,)) -> dict[str, Field]:
    """Declare every array written to M7's compact NPZ payload."""
    f64, i64, boolean = np.dtype("float64"), np.dtype("int64"), np.dtype("bool")
    return {
        "physics_time_ms": Field((), f64, "physics", "simulation time"),
        "physics_qpos": Field(qpos_shape, f64, "physics", "MuJoCo generalized position"),
        "physics_qvel": Field(qvel_shape, f64, "physics", "MuJoCo generalized velocity"),
        "physics_joint_position": Field(joint_shape, f64, "physics", "42 measured actuator coordinates"),
        "physics_action": Field(action_shape, f64, "physics", "42 commanded actuator coordinates"),
        "physics_ctrl": Field(ctrl_shape, f64, "physics", "MuJoCo actuator control"),
        "physics_body_position": Field((3,), f64, "physics", "body Cartesian position"),
        "physics_body_orientation": Field((4,), f64, "physics", "body orientation quaternion"),
        "physics_contact_forces": Field(contact_forces_shape, f64, "physics", "FlyGym contact-force observation"),
        "physics_finite": Field((), boolean, "physics", "finite-state validity flag"),
        "neural_time_ms": Field((), f64, "neural", "simulation time at neural update"),
        "neural_sensory_encoded": Field((SENSORY_CHANNELS,), f64, "neural",
            "per-interface peak encoded rate in LF, LM, LH, RF, RM, RH order"),
        "neural_delivered_drive_count": Field((), i64, "neural", "number of delivered external-drive indices"),
        "neural_aggregate_spikes": Field((), i64, "neural", "aggregate CNS spike count"),
        "neural_observer_outputs": Field((ADMITTED_MOTOR_CHANNELS,), f64, "neural", "observer peak rates"),
        "neural_decoder_outputs": Field((ADMITTED_MOTOR_CHANNELS,), f64, "neural", "raw decoder contributions"),
        "neural_admitted_contributions": Field((ADMITTED_MOTOR_CHANNELS,), f64, "neural", "gated admitted contributions"),
    }


def _shape(value: Any) -> tuple[Any, ...]:
    """Describe ragged values without ever creating an object array."""
    try:
        return tuple(np.asarray(value).shape)
    except ValueError:
        if isinstance(value, (list, tuple)):
            return (len(value), "ragged")
        return ("unrepresentable",)


class CompactTelemetry:
    """Preallocated telemetry whose assignment is the runtime schema check."""

    def __init__(self, schema: Mapping[str, Field], *, physics_capacity: int,
                 neural_capacity: int):
        self.schema = dict(schema)
        self.capacities = {"physics": physics_capacity, "neural": neural_capacity}
        self.counts = {"physics": 0, "neural": 0}
        self.arrays = {name: np.empty((self.capacities[field.cadence], *field.sample_shape),
                                     dtype=field.dtype)
                       for name, field in self.schema.items()}
        if any(array.dtype == object for array in self.arrays.values()):
            raise TypeError("object dtype is forbidden in compact telemetry")

    def record(self, cadence: str, values: Mapping[str, Any], simulation_time_ms: float) -> None:
        expected = {name for name, field in self.schema.items() if field.cadence == cadence}
        if set(values) != expected:
            raise RuntimeError(f"telemetry field inventory mismatch for {cadence}: "
                               f"expected {sorted(expected)}, observed {sorted(values)}")
        index = self.counts[cadence]
        if index >= self.capacities[cadence]:
            raise TelemetrySchemaError(f"{cadence}_capacity", (), (index + 1,), index, simulation_time_ms)
        for name in sorted(expected):
            field, value = self.schema[name], values[name]
            observed = _shape(value)
            if observed != field.sample_shape:
                raise TelemetrySchemaError(name, field.sample_shape, observed, index, simulation_time_ms)
            try:
                converted = np.asarray(value, dtype=field.dtype)
            except (TypeError, ValueError, OverflowError):
                raise TelemetrySchemaError(name, field.sample_shape, observed, index, simulation_time_ms) from None
            if converted.dtype == object or (np.issubdtype(converted.dtype, np.number) and
                                             not np.all(np.isfinite(converted))):
                raise TelemetrySchemaError(name, field.sample_shape, observed, index, simulation_time_ms)
            self.arrays[name][index] = converted
        self.counts[cadence] += 1

    def export(self) -> dict[str, np.ndarray]:
        return {name: value[:self.counts[field.cadence]].copy()
                for name, (field, value) in ((n, (f, self.arrays[n])) for n, f in self.schema.items())}


def sensory_channel_peaks(values: Any) -> np.ndarray:
    """Preserve the preregistered per-interface peak while removing raggedness."""
    if not isinstance(values, (list, tuple)) or len(values) != SENSORY_CHANNELS:
        raise ValueError("expected exactly six sensory-interface rate vectors")
    channels = []
    for value in values:
        rates = np.asarray(value, dtype=np.float64)
        if rates.ndim != 1 or not rates.size or not np.all(np.isfinite(rates)):
            raise ValueError("each sensory interface must be a nonempty finite rate vector")
        channels.append(float(np.max(rates)))
    return np.asarray(channels, dtype=np.float64)


def roundtrip_minimal(schema: Mapping[str, Field]) -> dict[str, np.ndarray]:
    """Prove NPZ compatibility with one schema-sized sample and no pickle."""
    arrays = {name: np.zeros((1, *field.sample_shape), dtype=field.dtype)
              for name, field in schema.items()}
    stream = io.BytesIO()
    np.savez_compressed(stream, **arrays)
    stream.seek(0)
    with np.load(stream, allow_pickle=False) as loaded:
        result = {name: loaded[name].copy() for name in loaded.files}
    if set(result) != set(arrays) or any(result[n].shape != arrays[n].shape or
                                         result[n].dtype != arrays[n].dtype or
                                         not np.array_equal(result[n], arrays[n]) for n in arrays):
        raise RuntimeError("compact telemetry NPZ round-trip mismatch")
    return result
