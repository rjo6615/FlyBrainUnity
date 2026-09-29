"""Annotation-backed Live Fly v2 motor inventory (17 motor, 6 sensory).

The six femur-roll interfaces are motor-only.  Proprioception remains limited
to the six historical tibia channels; these additions are not locally closed
loop.
"""
from __future__ import annotations

import copy
import math
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .integrated_whole_leg_readiness import EXPECTED_TIER_B, TIER_A

HISTORICAL_MOTOR = TIER_A + EXPECTED_TIER_B
NEW_ACTION_INDICES = frozenset((4, 11, 18, 25, 32, 39))

_CHANNEL_ROWS = (
    ("joint_LFFemur_roll", 4, "Fe reductor MN T1 left", (804941, 805598, 812111, 814163)),
    ("joint_LMFemur_roll", 11, "Fe reductor MN T2 left", (804025, 820764, 1050607195)),
    ("joint_LHFemur_roll", 18, "Fe reductor MN T3 left", (800578, 820350)),
    ("joint_RFFemur_roll", 25, "Fe reductor MN T1 right", (803830, 806898, 811652, 813566, 817595, 835074)),
    ("joint_RMFemur_roll", 32, "Fe reductor MN T2 right", (821769, 823132, 905145)),
    ("joint_RHFemur_roll", 39, "Fe reductor MN T3 right", (801693, 902962)),
)

SUPPLEMENTAL_MOTOR_CHANNELS = MappingProxyType({name: MappingProxyType({
    "actuator": name, "action_index": index, "population_name": population,
    "body_ids": body_ids, "coordinate_sign": 1,
    "decoder_mode": "unidirectional_positive",
}) for name, index, population, body_ids in _CHANNEL_ROWS})
V2_MOTOR = HISTORICAL_MOTOR + tuple(SUPPLEMENTAL_MOTOR_CHANNELS)


def derive_v2(protocol: Mapping[str, Any], records: Sequence[Mapping[str, Any]],
              table: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive v2 metadata without mutating any canonical v1 object."""
    value = copy.deepcopy(dict(protocol))
    record_copy = copy.deepcopy(list(records))
    rows = copy.deepcopy(list(table))
    for row in rows:
        definition = SUPPLEMENTAL_MOTOR_CHANNELS.get(row.get("actuator"))
        if definition is None:
            continue
        if row.get("action_index") != definition["action_index"]:
            raise RuntimeError("v2 actuator/action identity mismatch")
        row.update({
            "neural_motor_admission": True,
            "neural_sensory_admission": False,
            "coordinate_sign": 1,
            "coordinate_sign_status": "ANNOTATION_AND_LOCAL_MECHANICAL_VALIDATION",
            "motor_status": "ANNOTATION_BACKED_FE_REDUCTOR",
            "validation_source": "MALECNS_FE_REDUCTOR_AND_LOCAL_FLYGYM_MECHANICS",
            "reason": "annotation-backed Fe reductor motor-only admission",
            "handling": "baseline_plus_neural_contribution",
        })
    value["admitted_motor_interfaces"] = list(V2_MOTOR)
    # Deliberately retain the canonical six-tibia sensory inventory verbatim.
    value["admitted_sensory_interfaces"] = list(protocol["admitted_sensory_interfaces"])
    value["motor_output_count"] = 17
    value["sensory_proprioceptive_input_count"] = 6
    validate_v2(value, rows)
    return value, record_copy, rows


def validate_v2(protocol: Mapping[str, Any], table: Sequence[Mapping[str, Any]]) -> None:
    """Fail closed on v2 metadata and preservation of historical admission."""
    if len(table) != 42 or [row.get("action_index") for row in table] != list(range(42)):
        raise RuntimeError("v2 admission table must be the ordered 42-actuator model")
    motor = {row["action_index"] for row in table if row.get("neural_motor_admission")}
    sensory = {row["action_index"] for row in table if row.get("neural_sensory_admission")}
    expected_sensory = {row["action_index"] for row in table if row.get("actuator") in TIER_A}
    historical = {row["action_index"] for row in table
                  if row.get("actuator") in HISTORICAL_MOTOR and row.get("neural_motor_admission")}
    expected_historical = {row["action_index"] for row in table
                           if row.get("actuator") in HISTORICAL_MOTOR}
    checks = (len(motor) == 17, len(sensory) == 6 and sensory == expected_sensory,
              historical == expected_historical and len(historical) == 11,
              motor - historical == NEW_ACTION_INDICES,
              tuple(protocol.get("admitted_motor_interfaces", ())) == V2_MOTOR,
              tuple(protocol.get("admitted_sensory_interfaces", ())) == TIER_A,
              all(table[index]["actuator"] == definition["actuator"] and
                  table[index]["coordinate_sign"] == 1
                  for definition in SUPPLEMENTAL_MOTOR_CHANNELS.values()
                  for index in (definition["action_index"],)))
    if not all(checks):
        raise RuntimeError("Live Fly v2 admission contract mismatch")


def assert_v2_physical_admission(vector: Sequence[float],
                                 table: Sequence[Mapping[str, Any]]) -> None:
    """Reject every nonzero output not authorized by validated v2 metadata."""
    validate_v2({"admitted_motor_interfaces": V2_MOTOR,
                 "admitted_sensory_interfaces": TIER_A}, table)
    if len(vector) != 42:
        raise RuntimeError("v2 action-vector shape failure")
    for row, value in zip(table, vector):
        if not math.isfinite(float(value)) or (not row["neural_motor_admission"] and value != 0.0):
            raise RuntimeError(f"unauthorized v2 neural contribution: {row['actuator']}")


def gate_contributions(values: Mapping[str, float], condition: str,
                       admitted: Sequence[str]) -> dict[str, float]:
    """Use the existing enabled/disabled condition boundary for all 17 channels."""
    from .m7d_corrected_spontaneous import CONDITIONS

    if condition not in CONDITIONS or tuple(values) != tuple(admitted) or tuple(admitted) != V2_MOTOR:
        raise RuntimeError("v2 contribution inventory or condition mismatch")
    return {name: float(values[name]) if condition == CONDITIONS[0] else 0.0
            for name in admitted}
