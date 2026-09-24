"""Phase-2 headless runtime tests; no real or canonical experiment is run."""
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from malecns_backend.embodiment.scientific_session import ScientificSession
from malecns_backend.live import headless


class FakeSession:
    def __init__(self, failure=None):
        self.transitions = 0
        self.close_calls = 0
        self.failure = failure

    def initialize(self):
        return SimpleNamespace(time_ms=0.0)

    def step(self, *, lightweight=False):
        assert lightweight is True
        self.transitions += 1
        if self.failure is not None and self.transitions == 2:
            raise self.failure
        return SimpleNamespace(
            time_ms=self.transitions * 0.1,
            root_position_xyz=(0.0, 0.0, -100.0),  # deliberately "fallen"
            finite=True, physics_transitions=self.transitions,
            neural_transitions=self.transitions // 5,
        )

    def close(self):
        self.close_calls += 1


def ticking_clock():
    import itertools
    values = itertools.count()
    return lambda: next(values) * 0.25


def test_bounded_testing_run_uses_session_step_counts_cadence_and_no_fall_policy():
    session = FakeSession()
    output = StringIO()
    summary = headless.run(session_factory=lambda: session, max_transitions=11,
                           telemetry_interval=1.0, clock=lambda: 0.0, output=output)
    assert session.transitions == summary.physics_transitions == 11
    assert summary.neural_transitions == 2
    assert summary.shutdown_reason == "test transition limit"
    assert session.close_calls == 1
    assert not hasattr(headless.run, "trajectory")


def test_telemetry_clock_only_changes_reporting_not_stepping():
    quiet = FakeSession(); noisy = FakeSession()
    headless.run(session_factory=lambda: quiet, max_transitions=10,
                 telemetry_interval=100, clock=lambda: 0.0, output=StringIO())
    headless.run(session_factory=lambda: noisy, max_transitions=10,
                 telemetry_interval=.01, clock=ticking_clock(), output=StringIO())
    assert quiet.transitions == noisy.transitions == 10


@pytest.mark.parametrize("failure, reason", [
    (KeyboardInterrupt(), "KeyboardInterrupt"),
    (RuntimeError("boom"), "exception:RuntimeError"),
])
def test_interrupt_and_exception_cleanup(failure, reason):
    session = FakeSession(failure)
    output = StringIO()
    if isinstance(failure, KeyboardInterrupt):
        result = headless.run(session_factory=lambda: session, clock=lambda: 0.0,
                              output=output)
        assert result.shutdown_reason == reason
    else:
        with pytest.raises(RuntimeError, match="boom"):
            headless.run(session_factory=lambda: session, clock=lambda: 0.0,
                         output=output)
    assert session.close_calls == 1
    assert f"reason={reason}" in output.getvalue()


def test_factory_is_scientific_session_and_configuration_stays_unassisted(monkeypatch):
    captured = {}
    sentinel = ScientificSession(lambda: iter(()))
    monkeypatch.setattr(
        "malecns_backend.embodiment._windows_m7d_corrected_spontaneous_adapter._protocol",
        lambda: ({}, [], []),
    )
    def create(**kwargs):
        captured.update(kwargs)
        return sentinel
    monkeypatch.setattr(
        "malecns_backend.embodiment._windows_m8_live_condition.create_scientific_session", create)
    assert headless.create_live_session() is sentinel
    assert captured["continuous"] is True
    assert captured["proprioception_only"] is True
    assert captured["fixed_initial_baseline"] is True
    assert captured["compact_telemetry"] is False
    assert captured["m8_extended_telemetry"] is False
    assert "external_force_by_transition" not in captured


def test_continuous_kernel_has_no_history_or_canonical_writer():
    source = Path("malecns_backend/embodiment/_windows_m8_live_condition.py").read_text()
    assert "elif not pause_at_states:" in source
    live_source = Path("malecns_backend/live/headless.py").read_text()
    forbidden = ("interface_output", "StreamingAssets", "external_force", "recovery",
                 "controller", "socket", "trajectory.append")
    assert not any(term in live_source for term in forbidden)
