"""Live Fly v3 motor inventory (20 motor, 6 tibia sensory channels).

v3 derives from the validated v2 admission table and adds exactly three
previously validated antagonist motor channels.  No new sensory interface is
introduced and v1/v2 objects are never mutated.
"""
from __future__ import annotations

import copy
import math
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .integrated_whole_leg_readiness import TIER_A
from . import live_v2_motor_interface as v2


NEW_ACTION_INDICES = frozenset((6, 24, 27))

_CANDIDATE_ROWS = (
    (
        "joint_RFFemur",
        24,
        -1,
        (
            ("Sternotrochanter MN T1 right", (801079, 803698)),
            ("Tergotr. MN T1 right", (804866, 817347, 909521, 924716)),
            ("Tr extensor MN T1 right", (818842, 838321)),
        ),
        (
            ("Acc. tr flexor MN T1 right", (807873, 1050306082, 1050349786)),
            ("Tr flexor MN T1 right", (816648, 817640, 818719, 820130, 820668, 903010, 914655)),
        ),
    ),
    (
        "joint_LFTarsus1",
        6,
        -1,
        (
            ("Ta levator MN T1 left", (810541, 1050111955)),
        ),
        (
            ("Ta depressor MN T1 left", (817655, 819278, 1050403926, 1050660827, 1051062549)),
        ),
    ),
    (
        "joint_RFTarsus1",
        27,
        -1,
        (
            ("Ta levator MN T1 right", (817210, 820110, 820896)),
        ),
        (
            ("Ta depressor MN T1 right", (825721, 1050248133, 1050380236, 1050815462)),
        ),
    ),
)


def _population_map(rows: Sequence[tuple[str, Sequence[int]]]) -> Mapping[str, tuple[int, ...]]:
    return MappingProxyType({name: tuple(int(x) for x in body_ids) for name, body_ids in rows})


CANDIDATE_MOTOR_CHANNELS = MappingProxyType({
    name: MappingProxyType({
        "actuator": name,
        "action_index": index,
        "coordinate_sign": sign,
        "decoder_mode": "antagonist_pair",
        "positive_populations": _population_map(positive),
        "negative_populations": _population_map(negative),
    })
    for name, index, sign, positive, negative in _CANDIDATE_ROWS
})

# The kernel must receive all non-historical channel definitions, including the
# six v2 one-sided Femur_roll channels.
SUPPLEMENTAL_MOTOR_CHANNELS = MappingProxyType({
    **dict(v2.SUPPLEMENTAL_MOTOR_CHANNELS),
    **dict(CANDIDATE_MOTOR_CHANNELS),
})

V3_MOTOR = v2.V2_MOTOR + tuple(CANDIDATE_MOTOR_CHANNELS)


def derive_v3(protocol: Mapping[str, Any], records: Sequence[Mapping[str, Any]],
              table: Sequence[Mapping[str, Any]]
              ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive v3 from already-derived v2 metadata without mutating inputs."""
    value = copy.deepcopy(dict(protocol))
    record_copy = copy.deepcopy(list(records))
    rows = copy.deepcopy(list(table))

    # Require the input to be an intact v2 projection before extending it.
    v2.validate_v2(value, rows)

    for row in rows:
        definition = CANDIDATE_MOTOR_CHANNELS.get(row.get("actuator"))
        if definition is None:
            continue
        if row.get("action_index") != definition["action_index"]:
            raise RuntimeError("v3 actuator/action identity mismatch")
        row.update({
            "neural_motor_admission": True,
            "neural_sensory_admission": False,
            "coordinate_sign": int(definition["coordinate_sign"]),
            "coordinate_sign_status": "VALIDATED_CANDIDATE_MECHANICS",
            "motor_status": "VALIDATED_ANTAGONIST_CANDIDATE",
            "validation_source": "CANDIDATE_MOTOR_CHANNEL_VALIDATION",
            "reason": "validated antagonist candidate motor-only admission",
            "handling": "baseline_plus_neural_contribution",
        })

    value["admitted_motor_interfaces"] = list(V3_MOTOR)
    value["motor_output_count"] = 20
    value["sensory_proprioceptive_input_count"] = 6
    validate_v3(value, rows)
    return value, record_copy, rows


def validate_v3(protocol: Mapping[str, Any], table: Sequence[Mapping[str, Any]]) -> None:
    """Fail closed on the exact 20-motor/6-sensory v3 admission contract."""
    if len(table) != 42 or [row.get("action_index") for row in table] != list(range(42)):
        raise RuntimeError("v3 admission table must be the ordered 42-actuator model")

    motor_rows = [row for row in table if row.get("neural_motor_admission")]
    sensory_rows = [row for row in table if row.get("neural_sensory_admission")]
    motor = {row["action_index"] for row in motor_rows}
    sensory = {row["action_index"] for row in sensory_rows}
    expected_sensory = {row["action_index"] for row in table if row.get("actuator") in TIER_A}
    v2_motor = {row["action_index"] for row in table if row.get("actuator") in v2.V2_MOTOR}

    coxa_admitted = [
        row["actuator"] for row in motor_rows
        if any(token in str(row["actuator"]) for token in ("Coxa", "Coxa_roll", "Coxa_yaw"))
    ]
    tarsus_admitted = {
        row["action_index"] for row in motor_rows if str(row["actuator"]).endswith("Tarsus1")
    }

    checks = (
        len(motor) == 20,
        len(sensory) == 6 and sensory == expected_sensory,
        len(v2_motor) == 17,
        motor - v2_motor == NEW_ACTION_INDICES,
        tuple(protocol.get("admitted_motor_interfaces", ())) == V3_MOTOR,
        tuple(row["actuator"] for row in protocol["sensory_interfaces"]) == TIER_A,
        not coxa_admitted,
        tarsus_admitted == {6, 27},
        all(
            table[int(definition["action_index"])]["actuator"] == name
            and table[int(definition["action_index"])]["coordinate_sign"] == -1
            for name, definition in CANDIDATE_MOTOR_CHANNELS.items()
        ),
    )
    if not all(checks):
        raise RuntimeError("Live Fly v3 admission contract mismatch")


def assert_v3_physical_admission(vector: Sequence[float],
                                 table: Sequence[Mapping[str, Any]]) -> None:
    """Reject every nonzero output not authorized by validated v3 metadata."""
    validate_v3(
        {
            "admitted_motor_interfaces": V3_MOTOR,
            "sensory_interfaces": [{"actuator": name} for name in TIER_A],
        },
        table,
    )
    if len(vector) != 42:
        raise RuntimeError("v3 action-vector shape failure")
    for row, value in zip(table, vector):
        if not math.isfinite(float(value)) or (
            not row["neural_motor_admission"] and value != 0.0
        ):
            raise RuntimeError(f"unauthorized v3 neural contribution: {row['actuator']}")


def gate_contributions(values: Mapping[str, float], condition: str,
                       admitted: Sequence[str]) -> dict[str, float]:
    """Use the existing enabled/disabled condition boundary for all 20 channels."""
    from .m7d_corrected_spontaneous import CONDITIONS

    if (
        condition not in CONDITIONS
        or tuple(values) != tuple(admitted)
        or tuple(admitted) != V3_MOTOR
    ):
        raise RuntimeError("v3 contribution inventory or condition mismatch")
    return {
        name: float(values[name]) if condition == CONDITIONS[0] else 0.0
        for name in admitted
    }
