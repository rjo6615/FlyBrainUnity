"""Continuous headless execution over the validated ScientificSession."""
from __future__ import annotations

from dataclasses import dataclass
import sys
import time
from typing import Callable, TextIO

from malecns_backend.embodiment.scientific_session import ScientificSession


@dataclass(frozen=True)
class RunSummary:
    simulation_seconds: float
    wall_seconds: float
    real_time_factor: float
    physics_transitions: int
    neural_transitions: int
    shutdown_reason: str


def create_live_session() -> ScientificSession:
    """Build the enabled, unassisted M7D session without artifact writers."""
    from malecns_backend.embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
    from malecns_backend.embodiment import _windows_m8_live_condition as kernel
    from malecns_backend.embodiment import integrated_whole_leg_readiness as m6c
    from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d

    protocol, records, table = adapter._protocol()
    return kernel.create_scientific_session(
        protocol=protocol, condition=m7d.CONDITIONS[0], condition_number=1,
        progress=lambda *_: "", cached_admission_assertion=m6c.assert_physical_admission,
        cached_records=records, cached_table=table, condition_names=m7d.CONDITIONS,
        contribution_gate=adapter.gate_contributions, compact_telemetry=False,
        runtime_factory=adapter._runtime, proprioception_only=True,
        fixed_initial_baseline=True, m8_extended_telemetry=False,
        continuous=True,
    )


def run(*, session_factory: Callable[[], ScientificSession] = create_live_session,
        telemetry_interval: float = 1.0, max_transitions: int | None = None,
        clock: Callable[[], float] = time.monotonic,
        output: TextIO = sys.stdout) -> RunSummary:
    """Run until interrupted; ``max_transitions`` exists only for tests."""
    if telemetry_interval <= 0:
        raise ValueError("telemetry_interval must be positive")
    if max_transitions is not None and max_transitions < 0:
        raise ValueError("max_transitions must be nonnegative")

    session = session_factory()
    started = clock()
    last_report = started
    sim_seconds = 0.0
    initial_sim_seconds = 0.0
    physics = neural = 0
    reason = "test transition limit" if max_transitions == 0 else "completed"
    pending_error: BaseException | None = None
    try:
        initial = session.initialize()
        sim_seconds = initial.time_ms / 1000.0
        initial_sim_seconds = sim_seconds
        print(f"LIVE initialized sim={sim_seconds:.3f}s", file=output, flush=True)
        while max_transitions is None or physics < max_transitions:
            state = session.step(lightweight=True)
            sim_seconds = state.time_ms / 1000.0
            physics = state.physics_transitions
            neural = state.neural_transitions
            now = clock()
            if now - last_report >= telemetry_interval:
                wall = now - started
                rtf = (sim_seconds - initial_sim_seconds) / wall if wall else 0.0
                x, y, z = state.root_position_xyz
                print(f"LIVE sim={sim_seconds:.3f}s wall={wall:.3f}s RTF={rtf:.2f}x "
                      f"physics={physics} neural={neural} root=({x:.4f},{y:.4f},{z:.4f}) "
                      f"finite={state.finite}", file=output, flush=True)
                last_report = now
        reason = "test transition limit"
    except KeyboardInterrupt:
        reason = "KeyboardInterrupt"
    except BaseException as exc:
        reason = f"exception:{type(exc).__name__}"
        pending_error = exc
    finally:
        session.close()
        wall = max(0.0, clock() - started)
        rtf = (sim_seconds - initial_sim_seconds) / wall if wall else 0.0
        print(f"LIVE final sim={sim_seconds:.3f}s wall={wall:.3f}s RTF={rtf:.2f}x "
              f"physics={physics} neural={neural} reason={reason}", file=output, flush=True)
    if pending_error is not None:
        raise pending_error
    return RunSummary(sim_seconds, wall, rtf, physics, neural, reason)
