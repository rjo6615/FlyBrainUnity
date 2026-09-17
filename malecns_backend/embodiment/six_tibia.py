"""Auditable, isolated six-tibia interfaces derived from the Milestone 4A map.

This module contains no population-name discovery and no multi-leg controller.
Every anatomical value is read from ``six_leg_map.json`` and body IDs are
resolved against the immutable runtime index in ``interface_map.json``.
"""
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from .mappings import AuditedPopulation, INTERFACE_MAP
from .motor import MotorActivityObserver, MotorDecoder, MotorSafety


SIX_LEG_MAP = Path(__file__).with_name("six_leg_map.json")
LEG_ORDER = ("LF", "LM", "LH", "RF", "RM", "RH")


@dataclass(frozen=True)
class TibiaMotorPopulation:
    name: str
    body_ids: tuple[int, ...]
    dense_indices: tuple[int, ...]
    direction: int
    function: str
    confidence: str
    provenance: str


@dataclass(frozen=True)
class TibiaInterface:
    """One independently selectable interface; never a six-leg command."""
    leg: str
    segment: str
    side: str
    actuator_name: str
    action_index: int
    joint_range_rad: tuple[float, float]
    sensor: AuditedPopulation
    sensory_confidence: str
    motor_populations: tuple[TibiaMotorPopulation, ...]
    motor_confidence: str
    extensor: AuditedPopulation
    flexor: AuditedPopulation
    active_antagonist_supported: bool
    observation_reason: str

    # Compatibility with the validated M3D encoder/decoder classes.
    @property
    def flygym_joint_name(self):
        return self.actuator_name

    @property
    def flygym_joint_index(self):
        return self.action_index


def _audited_population(record, dense_indices):
    return AuditedPopulation(
        name=record["name"], category=record["category"],
        dense_indices=tuple(dense_indices), body_ids=tuple(record["body_ids"]),
        side=record["side"], body_target=f"tibia_{record['segment']}_{record['side']}",
        direction=record["direction"], provenance=record["provenance"],
    )


def load_six_tibia_interfaces(map_path=SIX_LEG_MAP, interface_path=INTERFACE_MAP):
    """Load exactly six tibiae, rejecting any inconsistency with audited IDs.

    Names select records *within the authoritative 4A document* only.  They
    are not synthesized or used to infer anatomy.
    """
    audit = json.loads(Path(map_path).read_text(encoding="utf-8"))
    runtime = json.loads(Path(interface_path).read_text(encoding="utf-8"))
    runtime_by_name = {p["name"]: p for p in runtime["populations"]}
    result = {}
    for leg_record in audit["legs"]:
        tibiae = [j for j in leg_record["joints"]
                  if j["actuator"]["anatomical_joint"] == "tibia"]
        if len(tibiae) != 1:
            raise ValueError(f"expected one audited tibia for {leg_record['leg']}")
        joint = tibiae[0]
        actuator, sensory, motor = joint["actuator"], joint["sensory"], joint["motor"]
        if sensory["status"] != "EXACT" or len(sensory["populations"]) != 1:
            raise ValueError(f"{leg_record['leg']} tibia sensory mapping is not EXACT/unique")

        def resolve(record):
            indexed = runtime_by_name.get(record["name"])
            if indexed is None or tuple(indexed["body_ids"]) != tuple(record["body_ids"]):
                raise ValueError(f"audited body IDs do not resolve exactly: {record['name']}")
            return tuple(indexed["dense_indices"])

        sensor_record = sensory["populations"][0]
        sensor = _audited_population(sensor_record, resolve(sensor_record))
        populations = tuple(
            TibiaMotorPopulation(
                p["name"], tuple(p["body_ids"]), resolve(p), int(p["direction"]),
                p["function"], motor["status"], p["provenance"],
            ) for p in motor["populations"]
        )
        positive = [p for p in populations if p.direction == 1]
        negative = [p for p in populations if p.direction == -1]
        active = bool(positive and negative and len(positive) + len(negative) == len(populations))

        def directional_population(items, canonical):
            # Retain the canonical single population name for exact LM numeric
            # equivalence; supported legs pool neurons sharing an audited sign.
            name = items[0].name if len(items) == 1 else canonical
            ids = tuple(i for p in items for i in p.body_ids)
            indices = tuple(i for p in items for i in p.dense_indices)
            return AuditedPopulation(name, "muscles", indices, ids,
                                     actuator["side"],
                                     f"tibia_{actuator['segment']}_{actuator['side']}",
                                     items[0].direction, "ANNOTATION_DERIVED")

        if not active:
            # Empty placeholders allow inventory/observation without inventing
            # an antagonist interpretation.  Decoder construction rejects it.
            positive = positive or [TibiaMotorPopulation("unresolved extensor", (), (), 1, "", motor["status"], "ANNOTATION_DERIVED")]
            negative = negative or [TibiaMotorPopulation("unresolved flexor", (), (), -1, "", motor["status"], "ANNOTATION_DERIVED")]
        interface = TibiaInterface(
            actuator["leg"], actuator["segment"], actuator["side"],
            actuator["name"], int(actuator["action_index"]),
            tuple(float(x) for x in actuator["position_range_rad"]), sensor,
            sensory["status"], populations, motor["status"],
            directional_population(positive, f"tibia extensors {actuator['segment']} {actuator['side']}"),
            directional_population(negative, f"tibia flexors {actuator['segment']} {actuator['side']}"),
            active,
            "audited +1 and -1 motor roles are explicit" if active else
            "observation-only: 4A does not provide both signed antagonist roles",
        )
        result[interface.leg] = interface
    if tuple(result) != LEG_ORDER:
        raise ValueError(f"expected ordered tibiae {LEG_ORDER}, got {tuple(result)}")
    return result


class IsolatedTibiaDecoder:
    """Independent observer/decoder state for exactly one selected tibia."""
    def __init__(self, interface):
        if not interface.active_antagonist_supported:
            raise ValueError(interface.observation_reason)
        self.interface = interface
        self.observer = MotorActivityObserver({
            population.name: population.dense_indices
            for population in interface.motor_populations
        })
        lo, hi = interface.joint_range_rad
        self.decoder = MotorDecoder(interface, MotorSafety(lo, hi, 0.25, 4.0))

    def reset(self, spike_counts=None):
        self.observer.reset(spike_counts)
        self.decoder.reset()

    def update(self, spike_counts, interval_ms, current_position_rad,
               control_dt_s=0.001, apply_neural_offset=True):
        observed = self.observer.update(spike_counts, interval_ms)
        # Preserve every named population in ``observed``.  The antagonist
        # input is the per-neuron mean for each explicit audited direction,
        # not an unweighted average of differently sized populations.
        directional_rates = {}
        for combined in (self.interface.extensor, self.interface.flexor):
            members = [p for p in self.interface.motor_populations
                       if p.direction == combined.direction]
            count = sum(len(p.dense_indices) for p in members)
            directional_rates[combined.name] = sum(
                observed["filtered_hz"][p.name] * len(p.dense_indices)
                for p in members
            ) / count
        command = self.decoder.decode(directional_rates, current_position_rad,
                                      control_dt_s, apply_neural_offset)
        observed["directional_filtered_hz"] = directional_rates
        return observed, command


class SixTibiaIsolation:
    """Factory enforcing one selected neural interface per fresh validation."""
    def __init__(self, interfaces=None):
        self.interfaces = interfaces or load_six_tibia_interfaces()

    def select(self, leg):
        if leg not in self.interfaces:
            raise KeyError(leg)
        return IsolatedTibiaDecoder(self.interfaces[leg])
