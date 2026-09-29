"""Continuous headless execution over the validated ScientificSession."""
from __future__ import annotations

from dataclasses import dataclass
import sys
import time
from typing import Any, Callable, Mapping, TextIO

from malecns_backend.embodiment.scientific_session import ScientificSession


class LatestLiveTelemetry:
    """Bounded passive view of the newest Live Fly neural and physics telemetry."""

    def __init__(self) -> None:
        self.latest_neural: Mapping[str, Any] | None = None
        self.latest_physics: Mapping[str, Any] | None = None
        self.neural_records = 0
        self.physics_records = 0

    def __call__(self, record: Mapping[str, Any]) -> None:
        # The scientific kernel supplies recursively read-only telemetry.
        # Keep only the newest record of each kind: memory usage never grows
        # with Live Fly runtime.
        if "neural_transition_index" in record:
            self.latest_neural = record
            self.neural_records += 1
            return
        if "physics_transition_index" in record:
            self.latest_physics = record
            self.physics_records += 1
            return
        raise RuntimeError("unrecognized Live Fly telemetry record")

    def status_text(self) -> str:
        record = self.latest_neural
        if record is None:
            return "motors=[waiting] sensory_events=0"

        contributions = record.get("final_contribution_rad", {})
        active = [
            f"{str(name).removeprefix('joint_')}={float(value):+.4f}"
            for name, value in contributions.items()
            if float(value) != 0.0
        ]
        delivered = record.get("delivered_external_sensory_events", ())
        motor_text = ",".join(active) if active else "none"
        return f"motors=[{motor_text}] sensory_events={len(delivered)}"


@dataclass(frozen=True)
class RunSummary:
    simulation_seconds: float
    initialization_wall_seconds: float
    execution_wall_seconds: float
    real_time_factor: float
    physics_transitions: int
    neural_transitions: int
    shutdown_reason: str

    @property
    def wall_seconds(self) -> float:
        """Backward-compatible name for execution (not initialization) wall time."""
        return self.execution_wall_seconds


def create_live_session(
        *, telemetry_observer: Callable[[Mapping[str, Any]], None] | None = None
        ) -> ScientificSession:
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
        continuous=True, telemetry_observer=telemetry_observer,
    )


def create_live_v2_session(*, telemetry_observer=None, runtime_factory=None) -> ScientificSession:
    """Build continuous Live Fly v2 with 17 motor and six sensory channels."""
    from malecns_backend.embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
    from malecns_backend.embodiment import _windows_m8_live_condition as kernel
    from malecns_backend.embodiment import live_v2_motor_interface as v2
    from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d

    v1_protocol, records, v1_table = adapter._protocol()
    protocol, records, table = v2.derive_v2(v1_protocol, records, v1_table)
    return kernel.create_scientific_session(
        protocol=protocol, condition=m7d.CONDITIONS[0], condition_number=1,
        progress=lambda *_: "", cached_admission_assertion=v2.assert_v2_physical_admission,
        cached_records=records, cached_table=table, condition_names=m7d.CONDITIONS,
        contribution_gate=v2.gate_contributions, compact_telemetry=False,
        runtime_factory=runtime_factory or adapter._runtime, proprioception_only=True,
        fixed_initial_baseline=True, m8_extended_telemetry=False, continuous=True,
        motor_channel_names=v2.V2_MOTOR,
        supplemental_motor_channels=v2.SUPPLEMENTAL_MOTOR_CHANNELS,
        telemetry_observer=telemetry_observer,
    )


def run(*, session_factory: Callable[[], ScientificSession] = create_live_session,
        telemetry_interval: float = 1.0, max_transitions: int | None = None,
        clock: Callable[[], float] = time.monotonic,
        output: TextIO = sys.stdout, pose_publisher=None,
        live_telemetry: LatestLiveTelemetry | None = None) -> RunSummary:
    """Run until interrupted; ``max_transitions`` exists only for tests."""
    if telemetry_interval <= 0:
        raise ValueError("telemetry_interval must be positive")
    if max_transitions is not None and max_transitions < 0:
        raise ValueError("max_transitions must be nonnegative")

    session = session_factory()
    initialization_started = clock()
    run_started = last_report = initialization_started
    initialization_wall = 0.0
    sim_seconds = 0.0
    initial_sim_seconds = 0.0
    physics = neural = 0
    reason = "test transition limit" if max_transitions == 0 else "completed"
    pending_error: BaseException | None = None
    try:
        initial = session.initialize()
        initialized = clock()
        initialization_wall = max(0.0, initialized - initialization_started)
        run_started = last_report = initialized
        sim_seconds = initial.time_ms / 1000.0
        initial_sim_seconds = sim_seconds
        print(f"LIVE initialized init_wall={initialization_wall:.3f}s sim={sim_seconds:.3f}s",
              file=output, flush=True)
        if pose_publisher is not None:
            pose_publisher.publish(initial, now=initialized)
        while max_transitions is None or physics < max_transitions:
            state = session.step(lightweight=True)
            sim_seconds = state.time_ms / 1000.0
            physics = state.physics_transitions
            neural = state.neural_transitions
            now = clock()
            if pose_publisher is not None and pose_publisher.due(now):
                pose_publisher.publish(session.snapshot(), now=now)
            if now - last_report >= telemetry_interval:
                wall = now - run_started
                rtf = (sim_seconds - initial_sim_seconds) / wall if wall else 0.0
                x, y, z = state.root_position_xyz
                telemetry_text = (
                    f" {live_telemetry.status_text()}"
                    if live_telemetry is not None else ""
                )
                print(f"LIVE sim={sim_seconds:.3f}s run_wall={wall:.3f}s RTF={rtf:.2f}x "
                      f"physics={physics} neural={neural} root=({x:.4f},{y:.4f},{z:.4f}) "
                      f"finite={state.finite}{telemetry_text}",
                      file=output, flush=True)
                last_report = now
        reason = "test transition limit"
    except KeyboardInterrupt:
        reason = "KeyboardInterrupt"
    except BaseException as exc:
        reason = f"exception:{type(exc).__name__}"
        pending_error = exc
    finally:
        session.close()
        wall = max(0.0, clock() - run_started)
        rtf = (sim_seconds - initial_sim_seconds) / wall if wall else 0.0
        print(f"LIVE final init_wall={initialization_wall:.3f}s run_wall={wall:.3f}s "
              f"sim={sim_seconds:.3f}s RTF={rtf:.2f}x "
              f"physics={physics} neural={neural} reason={reason}", file=output, flush=True)
    if pending_error is not None:
        raise pending_error
    return RunSummary(sim_seconds, initialization_wall, wall, rtf, physics, neural, reason)
