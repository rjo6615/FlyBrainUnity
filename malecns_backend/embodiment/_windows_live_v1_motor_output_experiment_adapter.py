"""Future Windows execution boundary for Experiment 3.

No runtime imports occur here.  Execution is intentionally unavailable until
prospective authorization and a passive runtime observation hook are reviewed.
"""
from __future__ import annotations

from typing import Any

from . import live_v1_motor_output_experiment as experiment


def enabled_gate(values: dict[str, float], admitted: tuple[str, ...]) -> dict[str, float]:
    expected = tuple(row[0] for row in experiment.MOTOR_CHANNELS)
    if tuple(admitted) != expected or tuple(values) != expected:
        raise RuntimeError("Live Fly v1 channel identity/order mismatch")
    return {name: float(values[name]) for name in admitted}


def matched_control_gate(values: dict[str, float], admitted: tuple[str, ...]) -> dict[str, float]:
    """Existing matched control: zero only the final 11 contributions."""
    enabled_gate(values, admitted)
    return {name: 0.0 for name in admitted}


def execute(*_args: Any, **_kwargs: Any) -> None:
    """Fail before importing or constructing either scientific runtime."""
    experiment.assert_execution_authorized()
    raise AssertionError("unreachable")
