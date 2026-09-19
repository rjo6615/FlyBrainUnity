"""Fail-closed M6B-P3 Coxa-yaw anatomical sign calibration helpers.

This module contains geometry only.  It deliberately has no dependency on the
MaleCNS runtime, spike data, the M6B condition runner, or locomotor outcomes.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

EPSILON_RAD = 0.0001
ROTATIONAL_TOLERANCE = 1e-10


def transform_local_axis(local_axis: Sequence[float], body_xmat: Sequence[float]) -> list[float]:
    """Transform MuJoCo's body-local ``jnt_axis`` into world coordinates.

    ``data.xmat[model.jnt_bodyid[jid]]`` is the row-major rotation from the
    joint's owning body frame to world.  Translation is intentionally absent
    because an axis is a direction.
    """
    axis = np.asarray(local_axis, dtype=float).reshape(3)
    rotation = np.asarray(body_xmat, dtype=float).reshape(3, 3)
    world = rotation @ axis
    norm = float(np.linalg.norm(world))
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("joint axis is unavailable or zero")
    return (world / norm).tolist()


def signed_rotational_metric(axis: Sequence[float], neutral_vector: Sequence[float],
                             perturbed_vector: Sequence[float]) -> float:
    """Return the oriented sine-like rotation of a leg vector about ``axis``."""
    a = np.asarray(axis, dtype=float); v0 = np.asarray(neutral_vector, dtype=float)
    v1 = np.asarray(perturbed_vector, dtype=float)
    if any(x.shape != (3,) for x in (a, v0, v1)):
        raise ValueError("axis and vectors must be three-dimensional")
    denominator = np.linalg.norm(a) * np.linalg.norm(v0) * np.linalg.norm(v1)
    if not math.isfinite(float(denominator)) or denominator == 0:
        raise ValueError("rotational geometry is degenerate")
    return float(np.dot(a, np.cross(v0, v1)) / denominator)


def assess_coordinate_sign(metric_plus: float | None, metric_minus: float | None,
                           annotation_direction: str | None,
                           *, bilateral_only: bool = False,
                           tolerance: float = ROTATIONAL_TOLERANCE) -> tuple[str, int | None, str]:
    """Join independent annotation semantics to kinematics, or fail closed.

    A metric establishes what positive q does, but does not itself establish
    what an annotated muscle name means.  Only an unambiguous anatomical
    direction may bridge those facts; symmetry is never such a bridge.
    """
    if bilateral_only:
        return "SIGN_UNRESOLVED", None, "bilateral symmetry cannot establish an independent sign"
    if annotation_direction is None:
        return "SIGN_UNRESOLVED", None, "annotation action direction unavailable"
    if annotation_direction not in {"positive_axis_rotation", "negative_axis_rotation"}:
        return "SIGN_UNRESOLVED", None, "annotation-to-anatomical rotation correspondence ambiguous"
    if metric_plus is None or metric_minus is None:
        return "SIGN_UNRESOLVED", None, "rotational geometry unavailable"
    if abs(metric_plus) <= tolerance or abs(metric_minus) <= tolerance:
        return "SIGN_UNRESOLVED", None, "rotational metric approximately zero"
    if metric_plus * metric_minus >= 0 or not math.isclose(
            abs(metric_plus), abs(metric_minus), rel_tol=1e-3, abs_tol=tolerance):
        return "SIGN_UNRESOLVED", None, "+epsilon/-epsilon evidence inconsistent"
    annotation_factor = 1 if annotation_direction == "positive_axis_rotation" else -1
    sign = annotation_factor * (1 if metric_plus > 0 else -1)
    return "RESOLVED", sign, "annotation direction and independent rotational geometry agree"


def annotation_evidence(interface: Mapping[str, Any]) -> dict[str, Any]:
    """Extract, without strengthening, M6A's Coxa-yaw annotation claims."""
    populations = [dict(x) for x in interface.get("directional_motor_populations", ())]
    names = [str(x.get("population", "")) for x in populations]
    return {
        "populations": populations,
        "directional_terms": names,
        "antagonist_pair_present": ({x.get("annotation_direction") for x in populations} >= {-1, 1}),
        "annotation_positive_action": next((x.get("population") for x in populations
                                             if x.get("annotation_direction") == 1), None),
        # Population labels identify anterior/posterior rotators, but the
        # locked M6A evidence does not define either label as a handed rotation
        # about the NMF joint axis.  Do not silently invent that missing link.
        "anatomical_axis_rotation": None,
        "directionality_origin": "M6A explicit signed antagonist assignment; axis handedness not established",
    }


__all__ = ["EPSILON_RAD", "ROTATIONAL_TOLERANCE", "annotation_evidence",
           "assess_coordinate_sign", "signed_rotational_metric", "transform_local_axis"]
