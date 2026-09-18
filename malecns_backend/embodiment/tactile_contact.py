"""M5D-2 modeled distal-contact transduction (contact only, never load).

The association of the populations with claw contact is annotation-backed.
Everything from a FlyGym force vector to a firing rate is deliberately marked
as modeled engineering and must not be interpreted as a measured response.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping

import numpy as np

from .m5d_tarsal_contact_load import LEGS, build_audit
from .mappings import INTERFACE_MAP

SEGMENTS = ("Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5")
DISTAL_SEGMENT = "Tarsus5"
DISTAL_OFFSET = 5


@dataclass(frozen=True)
class TactilePopulation:
    leg: str
    name: str
    body_ids: tuple[int, ...]
    dense_indices: tuple[int, ...]


def load_tactile_populations(interface_path=INTERFACE_MAP) -> dict[str, TactilePopulation]:
    """Resolve the six locked M5D-1 populations without name inference."""
    sources = [p for p in build_audit()["biological_populations"]
               if p["mechanism"] == "contact"]
    indexed = {p["name"]: p for p in json.loads(Path(interface_path).read_text())["populations"]}
    result = {}
    for source in sources:
        runtime = indexed[source["population_name"]]
        ids = tuple(source["body_ids"])
        if tuple(runtime["body_ids"]) != ids:
            raise ValueError(f"body-ID mismatch for {source['population_name']}")
        result[source["leg"]] = TactilePopulation(
            source["leg"], source["population_name"], ids,
            tuple(runtime["dense_indices"]),
        )
    if tuple(result) != LEGS:
        raise ValueError(f"expected ordered tactile populations {LEGS}, got {tuple(result)}")
    return result


@dataclass(frozen=True)
class TactileContactConfig:
    """MODELED_ENGINEERING_PARAMETER values, not biological measurements.

    The epsilon threshold is provisional until a live calibration demonstrates
    the runtime's zero/nonzero separation.  A linear, onset-only 20 ms pulse is
    intentionally simple and capped at 120 Hz.
    """
    engineering_threshold: float = 1e-12
    transient_duration_ms: float = 20.0
    maximum_modeled_rate_hz: float = 120.0
    seed: int = 1
    enabled: bool = True

    def __post_init__(self):
        if self.engineering_threshold < 0:
            raise ValueError("engineering_threshold must be nonnegative")
        if self.transient_duration_ms <= 0 or self.maximum_modeled_rate_hz < 0:
            raise ValueError("transient duration must be positive and rate nonnegative")


@dataclass(frozen=True)
class TactileContactFrame:
    leg: str
    time_ms: float
    all_segment_vectors: tuple[tuple[float, float, float], ...]
    raw_force_vector: tuple[float, float, float]
    force_magnitude: float
    threshold: float
    contact: bool
    onset_time_ms: float | None
    modeled_rate_hz: float
    population_name: str
    population_size: int
    generated_dense_indices: tuple[int, ...]

    @property
    def generated_tactile_spike_count(self):
        return len(self.generated_dense_indices)


def distal_contact_vectors(contact_forces) -> dict[str, np.ndarray]:
    """Validate `(36, 3)` telemetry and select only each Tarsus5 row."""
    raw = np.asarray(contact_forces, dtype=np.float64)
    if raw.shape != (36, 3):
        raise ValueError(f"contact_forces must have shape (36, 3), got {raw.shape}")
    return {leg: raw[i * 6 + DISTAL_OFFSET].copy() for i, leg in enumerate(LEGS)}


class TactileContactEncoder:
    """Stateful onset encoder with isolated deterministic population RNGs."""
    def __init__(self, populations: Mapping[str, TactilePopulation] | None = None,
                 config: TactileContactConfig | None = None):
        self.populations = dict(populations or load_tactile_populations())
        self.config = config or TactileContactConfig()
        if tuple(self.populations) != LEGS:
            raise ValueError("exactly six ordered tactile populations are required")
        # SeedSequence spawning makes streams stable and independent by leg;
        # neither construction nor disabled operation touches a brain/tibia RNG.
        children = np.random.SeedSequence(self.config.seed).spawn(len(LEGS))
        self.rng = {leg: np.random.default_rng(child) for leg, child in zip(LEGS, children)}
        self.reset()

    def reset(self):
        self._contact = {leg: False for leg in LEGS}
        self._onset = {leg: None for leg in LEGS}

    def encode(self, contact_forces, time_ms: float, dt_ms: float) -> dict[str, TactileContactFrame]:
        if dt_ms <= 0:
            raise ValueError("dt_ms must be positive")
        raw = np.asarray(contact_forces, dtype=np.float64)
        selected = distal_contact_vectors(raw)
        frames = {}
        for position, leg in enumerate(LEGS):
            vector = selected[leg]
            magnitude = float(np.linalg.norm(vector))
            contact = bool(magnitude > self.config.engineering_threshold)
            if contact and not self._contact[leg]:
                self._onset[leg] = float(time_ms)
            elif not contact:
                self._onset[leg] = None
            self._contact[leg] = contact
            elapsed = (float(time_ms) - self._onset[leg]
                       if contact and self._onset[leg] is not None else np.inf)
            envelope = max(0.0, 1.0 - elapsed / self.config.transient_duration_ms)
            rate = (self.config.maximum_modeled_rate_hz * envelope
                    if self.config.enabled else 0.0)
            population = self.populations[leg]
            # One independent Bernoulli candidate per complete annotated population.
            probability = min(1.0, rate * dt_ms / 1000.0)
            mask = self.rng[leg].random(len(population.dense_indices)) < probability if rate else np.zeros(len(population.dense_indices), bool)
            generated = tuple(int(x) for x in np.asarray(population.dense_indices)[mask])
            frames[leg] = TactileContactFrame(
                leg, float(time_ms), tuple(tuple(float(x) for x in row) for row in raw[position*6:(position+1)*6]),
                tuple(float(x) for x in vector), magnitude,
                self.config.engineering_threshold, contact, self._onset[leg], rate,
                population.name, len(population.body_ids), generated,
            )
        return frames

    @staticmethod
    def apply_external_drive(brain, frames: Mapping[str, TactileContactFrame], dt_ms: float):
        """Deliver generated candidates solely through the normal drive API.

        A rate of ``1000/dt`` makes each already-sampled candidate certain at
        the runtime boundary.  It does not access any neural-state attribute.
        """
        indices = tuple(i for leg in LEGS for i in frames[leg].generated_dense_indices)
        if indices:
            brain.set_external_drive(indices, 1000.0 / dt_ms)
        return indices


def calibration_statistics(samples: Mapping[str, list[float]]) -> dict:
    result = {}
    for leg in LEGS:
        values = np.asarray(samples[leg], dtype=np.float64)
        if not values.size:
            raise ValueError(f"no calibration observations for {leg}")
        result[leg] = {
            "count": int(values.size), "min": float(values.min()), "max": float(values.max()),
            "mean": float(values.mean()), "median": float(np.median(values)),
            "percentiles": {str(p): float(np.percentile(values, p)) for p in (1, 5, 25, 50, 75, 95, 99)},
            "exact_zero_fraction": float(np.mean(values == 0)),
            "nonzero_fraction": float(np.mean(values != 0)),
        }
    return result
