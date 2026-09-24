"""Persistent, noncanonical access to the frozen M7D/M8 transition kernel.

This module owns lifecycle only.  Scientific construction and transition
ordering remain in ``_windows_m8_live_condition._scientific_transition_kernel``.
The root quaternion exposed here is MuJoCo's native ``w, x, y, z`` ordering.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Generator, Mapping


def _freeze(value: Any) -> Any:
    """Return a recursively detached, read-only diagnostic value."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if hasattr(value, "tolist"):
        return _freeze(value.tolist())
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value.item() if hasattr(value, "item") else value


@dataclass(frozen=True)
class ScientificSnapshot:
    """A defensive copy of authoritative MuJoCo state at one physics state."""

    time_ms: float
    root_position_xyz: tuple[float, float, float]
    root_quaternion_wxyz: tuple[float, float, float, float]
    joint_positions: tuple[float, ...]
    qpos: tuple[float, ...]
    qvel: tuple[float, ...]
    diagnostics: Mapping[str, Any]


@dataclass(frozen=True)
class ScientificStep:
    """Constant-size state needed by continuous observational runtimes."""

    time_ms: float
    root_position_xyz: tuple[float, float, float]
    finite: bool
    physics_transitions: int
    neural_transitions: int


class ScientificSession:
    """Initialize once, advance incrementally, snapshot, and close once.

    A call to :meth:`step` represents one and only one physics transition.
    Neural work remains inside the kernel and therefore occurs every fifth
    transition, before motor application, exactly as in the finite M8 runner.
    """

    def __init__(self, kernel_factory: Callable[[], Generator[Mapping[str, Any], None, Mapping[str, Any]]]):
        self._factory = kernel_factory
        self._kernel = None
        self._state = None
        self._result = None
        self._initialized = False
        self._closed = False
        self.finished = False

    def initialize(self) -> ScientificSnapshot:
        if self._closed:
            raise RuntimeError("scientific session is closed")
        if self._initialized:
            raise RuntimeError("scientific session is already initialized")
        self._initialized = True
        self._kernel = self._factory()
        try:
            self._advance()
            if self.finished:
                raise RuntimeError("scientific kernel produced no initial state")
            if not self._state.get("finite", False):
                raise RuntimeError("non-finite authoritative state; session failed closed")
            return self.snapshot()
        except BaseException:
            self.close()
            raise

    def _advance(self) -> None:
        try:
            self._state = next(self._kernel)
        except StopIteration as stopped:
            self.finished = True
            self._result = stopped.value

    def step(self, *, lightweight: bool = False) -> ScientificSnapshot | ScientificStep:
        if not self._initialized:
            raise RuntimeError("scientific session is not initialized")
        if self._closed:
            raise RuntimeError("scientific session is closed")
        if self.finished:
            raise StopIteration("scientific session is complete")
        self._advance()
        if self.finished:
            raise StopIteration
        if not self._state.get("finite", False):
            self.close()
            raise RuntimeError("non-finite authoritative state; session failed closed")
        if lightweight:
            qpos = self._state["qpos"]
            return ScientificStep(
                time_ms=float(self._state["time_ms"]),
                root_position_xyz=tuple(float(x) for x in qpos[:3]),
                finite=bool(self._state["finite"]),
                physics_transitions=int(self._state["physics_transition"]),
                neural_transitions=int(self._state["neural_transition_count"]),
            )
        return self.snapshot()

    def snapshot(self) -> ScientificSnapshot:
        if not self._initialized or self._state is None:
            raise RuntimeError("scientific session has no initialized state")
        qpos = tuple(float(x) for x in self._state["qpos"])
        joints = tuple(float(x) for x in self._state["joint_positions"])
        if len(qpos) < 7 or len(joints) != 42:
            raise RuntimeError("invalid authoritative state shape")
        diagnostics = {k: _freeze(v) for k, v in self._state.items()
                       if k not in {"time_ms", "qpos", "qvel", "joint_positions", "brain"}}
        if "brain" in self._state:
            from ._windows_m8_live_condition import _digest
            diagnostics["malecns_state_digest"] = _digest(self._state["brain"])
        return ScientificSnapshot(float(self._state["time_ms"]), qpos[:3], qpos[3:7],
                                  joints, qpos,
                                  tuple(float(x) for x in self._state["qvel"]),
                                  MappingProxyType(diagnostics))

    @property
    def result(self) -> Mapping[str, Any]:
        if not self.finished:
            raise RuntimeError("scientific session has not completed")
        return self._result

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._kernel is not None:
            self._kernel.close()

    def __enter__(self) -> "ScientificSession":
        self.initialize()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
