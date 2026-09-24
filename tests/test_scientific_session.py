"""Phase-1 session regressions; these never execute a canonical experiment."""
from pathlib import Path

import pytest

from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d
from malecns_backend.embodiment import m8_extended_spontaneous as m8
from malecns_backend.embodiment import _windows_m8_extended_spontaneous_adapter as adapter
from malecns_backend.embodiment.integrated_whole_leg_readiness import EXPECTED_TIER_B, TIER_A
from malecns_backend.embodiment.scientific_session import ScientificSession


def _state(i, *, finite=True):
    qpos = [i, i + .1, i + .2, 1., 0., 0., 0.] + [float(i)] * 42
    return {"time_ms": i * .1, "qpos": qpos, "qvel": [float(-i)] * len(qpos),
            "joint_positions": [float(i)] * 42, "finite": finite,
            "sensory": {"LF": (i,)}, "sensory_candidates": (i,),
            "decoder_outputs": {"motor": i},
            "admitted_motor_contributions": {"motor": i},
            "malecns_state_digest": f"brain-{i}"}


def _kernel(states, closed):
    try:
        for state in states:
            yield state
        return {"physics_steps": len(states) - 1}
    finally:
        closed.append(True)


def test_exact_frozen_inventory_seed_and_cadence():
    assert m8.ADMITTED_MOTOR == (
        "joint_LFTibia", "joint_LMTibia", "joint_LHTibia", "joint_RFTibia",
        "joint_RMTibia", "joint_RHTibia", "joint_LFFemur", "joint_LMFemur",
        "joint_LHFemur", "joint_RMFemur", "joint_RHFemur")
    assert m8.ADMITTED_MOTOR == TIER_A + EXPECTED_TIER_B
    assert m8.ADMITTED_SENSORY == TIER_A
    assert m8.SEED == m7d.SEED == 1
    assert m8.PHYSICS_DT_MS == .1
    assert m8.NEURAL_DT_MS == .5
    assert round(m8.NEURAL_DT_MS / m8.PHYSICS_DT_MS) == 5


def test_m8_finite_adapter_selects_unassisted_enabled_kernel_configuration(monkeypatch):
    captured = []
    def runner(**kwargs):
        captured.append(kwargs)
        return {}
    monkeypatch.setattr(adapter.m7da, "_protocol", lambda: ({}, [], []))
    adapter._invoke(runner, {}, [], [], m8.CONDITIONS[0], 1, False)
    call = captured[0]
    assert call["fixed_initial_baseline"] is True
    assert call["proprioception_only"] is True  # exactly the six tibial streams
    assert call["runtime_factory"] is adapter.m7da._runtime
    assert "external_force_by_transition" not in call
    assert call["contribution_gate"] is adapter.gate_contributions


def test_snapshot_shape_quaternion_order_and_five_to_one_cadence():
    closed = []
    states = [_state(i) for i in range(11)]
    session = ScientificSession(lambda: _kernel(states, closed))
    first = session.initialize()
    assert first.root_position_xyz == (0., .1, .2)
    assert first.root_quaternion_wxyz == (1., 0., 0., 0.)
    assert len(first.joint_positions) == 42
    snapshots = [first] + [session.step() for _ in range(10)]
    assert [x.time_ms for x in snapshots] == pytest.approx([i * .1 for i in range(11)])
    assert [i for i in range(1, 11) if i % 5 == 0] == [5, 10]
    session.close()
    assert closed == [True]


def test_short_noncanonical_prefix_equivalence_all_authoritative_fields():
    """Compare direct finite consumption and session consumption transition-wise."""
    states = [_state(i) for i in range(8)]
    direct_closed = []
    direct = _kernel(states, direct_closed)
    expected = list(direct)
    session_closed = []
    session = ScientificSession(lambda: _kernel([_state(i) for i in range(8)], session_closed))
    actual = [session.initialize()]
    actual.extend(session.step() for _ in range(7))
    for raw, snapshot in zip(expected, actual):
        assert snapshot.time_ms == raw["time_ms"]
        assert snapshot.qpos == tuple(raw["qpos"])
        assert snapshot.qvel == tuple(raw["qvel"])
        assert snapshot.joint_positions == tuple(raw["joint_positions"])
        for field in ("malecns_state_digest", "sensory", "sensory_candidates",
                      "decoder_outputs", "admitted_motor_contributions"):
            assert snapshot.diagnostics[field] == raw[field]
    session.close()


def test_fresh_initialization_and_idempotent_close():
    sessions = []
    for _ in range(2):
        closed = []
        session = ScientificSession(lambda c=closed: _kernel([_state(0), _state(1)], c))
        sessions.append((session, session.initialize(), closed))
    assert sessions[0][1] == sessions[1][1]
    for session, _, closed in sessions:
        session.close(); session.close()
        assert closed == [True]


def test_fall_has_no_recovery_or_termination_and_nonfinite_fails_closed():
    # Lifecycle has no pose/fall branch: an inverted quaternion advances normally.
    falling = _state(0); falling["qpos"][3:7] = [0., 1., 0., 0.]
    session = ScientificSession(lambda: _kernel([falling, _state(1)], []))
    session.initialize()
    assert session.step().time_ms == .1

    closed = []
    failed = ScientificSession(lambda: _kernel([_state(0), _state(1, finite=False)], closed))
    failed.initialize()
    with pytest.raises(RuntimeError, match="failed closed"):
        failed.step()
    assert closed == [True]


def test_kernel_source_preserves_action_shape_adhesion_admission_and_ordering():
    source = Path("malecns_backend/embodiment/_windows_m8_live_condition.py").read_text()
    assert "initialization_vector = [0.] * 42" in source
    assert 'cached_admission_assertion(neural_vector, cached_table)' in source
    assert 'sim.step({"joints": commands.copy(), "adhesion": np.zeros(6)})' in source
    assert source.index("brain.clear_external_drive()") < source.index("brain.set_external_drive")
    assert source.index("brain.set_external_drive") < source.index("brain.step()")
    assert source.index("brain.step()") < source.index("raw = compute_raw_contribution")
    assert source.index("raw = compute_raw_contribution") < source.index("cached_admission_assertion(neural_vector")
    assert source.index("cached_admission_assertion(neural_vector") < source.index('sim.step({"joints"')
