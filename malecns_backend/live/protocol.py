"""Versioned, output-only Live Fly pose wire protocol."""
from __future__ import annotations

import json
import math
from typing import Any, Mapping, Sequence

PROTOCOL = "live_fly_pose"
VERSION = 1
JOINT_COUNT = 42

# M4A/M5A authoritative action-index order, also used by ScientificSession.
JOINT_NAMES = (
    "joint_LFCoxa", "joint_LFCoxa_roll", "joint_LFCoxa_yaw", "joint_LFFemur",
    "joint_LFFemur_roll", "joint_LFTibia", "joint_LFTarsus1", "joint_LMCoxa",
    "joint_LMCoxa_roll", "joint_LMCoxa_yaw", "joint_LMFemur", "joint_LMFemur_roll",
    "joint_LMTibia", "joint_LMTarsus1", "joint_LHCoxa", "joint_LHCoxa_roll",
    "joint_LHCoxa_yaw", "joint_LHFemur", "joint_LHFemur_roll", "joint_LHTibia",
    "joint_LHTarsus1", "joint_RFCoxa", "joint_RFCoxa_roll", "joint_RFCoxa_yaw",
    "joint_RFFemur", "joint_RFFemur_roll", "joint_RFTibia", "joint_RFTarsus1",
    "joint_RMCoxa", "joint_RMCoxa_roll", "joint_RMCoxa_yaw", "joint_RMFemur",
    "joint_RMFemur_roll", "joint_RMTibia", "joint_RMTarsus1", "joint_RHCoxa",
    "joint_RHCoxa_roll", "joint_RHCoxa_yaw", "joint_RHFemur", "joint_RHFemur_roll",
    "joint_RHTibia", "joint_RHTarsus1",
)


class ProtocolError(ValueError):
    """A message does not satisfy the Live Fly v1 schema."""


def hello(session_id: str) -> dict[str, Any]:
    return {
        "type": "hello", "protocol": PROTOCOL, "version": VERSION,
        "session_id": session_id, "joint_count": JOINT_COUNT,
        "joint_names": list(JOINT_NAMES), "physics_dt_seconds": .0001,
        "neural_dt_seconds": .0005, "root_quaternion_order": "wxyz",
        "source_length_unit": "millimetres",
        "coordinate_convention": "FlyGym right-handed Z-up; unconverted MuJoCo coordinates",
        "rig/model identity": "FlyGym NeuroMechFly, validated MaleCNS 42-leg-joint action order",
    }


def pose(session_id: str, sequence: int, sim_time_seconds: float,
         root_position: Sequence[float], root_quaternion_wxyz: Sequence[float],
         joint_positions: Sequence[float], **diagnostics: Any) -> dict[str, Any]:
    message = {
        "type": "pose", "protocol": PROTOCOL, "version": VERSION,
        "session_id": session_id, "sequence": sequence,
        "sim_time_seconds": sim_time_seconds,
        "root_position": list(root_position),
        "root_quaternion_wxyz": list(root_quaternion_wxyz),
        "joint_positions": list(joint_positions),
    }
    message.update(diagnostics)
    validate_pose(message)
    return message


def _common(message: Mapping[str, Any], kind: str) -> None:
    if message.get("type") != kind or message.get("protocol") != PROTOCOL or message.get("version") != VERSION:
        raise ProtocolError(f"not a {PROTOCOL} v{VERSION} {kind} message")
    if not isinstance(message.get("session_id"), str) or not message["session_id"]:
        raise ProtocolError("session_id must be a nonempty string")


def validate_hello(message: Mapping[str, Any]) -> None:
    _common(message, "hello")
    if message.get("joint_count") != JOINT_COUNT or tuple(message.get("joint_names", ())) != JOINT_NAMES:
        raise ProtocolError("hello must contain the authoritative 42-joint order")
    if message.get("root_quaternion_order") != "wxyz":
        raise ProtocolError("root quaternion order must be wxyz")


def validate_pose(message: Mapping[str, Any]) -> None:
    _common(message, "pose")
    if not isinstance(message.get("sequence"), int) or message["sequence"] < 0:
        raise ProtocolError("sequence must be a nonnegative integer")
    vectors = (("root_position", 3), ("root_quaternion_wxyz", 4),
               ("joint_positions", JOINT_COUNT))
    for name, length in vectors:
        value = message.get(name)
        if not isinstance(value, (list, tuple)) or len(value) != length:
            raise ProtocolError(f"{name} must contain exactly {length} values")
        if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in value):
            raise ProtocolError(f"{name} values must be finite numbers")
    if not isinstance(message.get("sim_time_seconds"), (int, float)) or not math.isfinite(message["sim_time_seconds"]):
        raise ProtocolError("sim_time_seconds must be finite")


def encode(message: Mapping[str, Any]) -> bytes:
    if message.get("type") == "hello":
        validate_hello(message)
    elif message.get("type") == "pose":
        validate_pose(message)
    else:
        raise ProtocolError("unknown message type")
    return (json.dumps(message, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def decode(line: bytes | str) -> dict[str, Any]:
    try:
        message = json.loads(line.decode("utf-8") if isinstance(line, bytes) else line)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid UTF-8 JSON") from exc
    if not isinstance(message, dict):
        raise ProtocolError("message must be a JSON object")
    return message
