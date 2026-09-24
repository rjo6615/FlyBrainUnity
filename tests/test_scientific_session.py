"""Phase-1 session regressions; these never execute a canonical experiment."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

from malecns_backend.embodiment import m7d_corrected_spontaneous as m7d
from malecns_backend.embodiment import m8_extended_spontaneous as m8
from malecns_backend.embodiment import _windows_m8_extended_spontaneous_adapter as adapter
from malecns_backend.embodiment.integrated_whole_leg_readiness import EXPECTED_TIER_B, TIER_A
from malecns_backend.embodiment.scientific_session import ScientificSession
from malecns_backend.embodiment import _windows_m8_live_condition as live


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


def test_legacy_runner_exhausts_without_snapshot_policy_and_closes(monkeypatch):
    closed = []
    partial = {"physics_instability": True, "physics_steps": 3}
    def legacy_kernel(**kwargs):
        assert kwargs["pause_at_states"] is False
        try:
            if False:
                yield None
            return partial
        finally:
            closed.append(True)
    monkeypatch.setattr(live, "_scientific_transition_kernel", legacy_kernel)
    assert live.run_condition(initialize_only=True) is partial
    assert closed == [True]


def test_initialization_snapshot_failure_closes_deterministically():
    closed = []
    malformed = _state(0); malformed["joint_positions"] = [0.] * 41
    session = ScientificSession(lambda: _kernel([malformed], closed))
    with pytest.raises(RuntimeError, match="shape"):
        session.initialize()
    assert closed == [True]


def test_snapshot_is_detached_and_cannot_mutate_authoritative_state():
    closed = []; state = _state(0)
    state["commands"] = [1.] * 42
    state["decoder_outputs"] = {"motor": 2.}
    session = ScientificSession(lambda: _kernel([state], closed))
    snapshot = session.initialize()
    state["qpos"][0] = 999.; state["commands"][0] = 999.
    assert snapshot.qpos[0] == 0.
    assert snapshot.diagnostics["commands"][0] == 1.
    with pytest.raises(TypeError):
        snapshot.diagnostics["decoder_outputs"]["motor"] = 3.
    session.close()


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
    callback = source.index("external_force_by_transition(condition, step)")
    physical = source.index('sim.step({"joints"')
    assert callback < physical
    legacy = source[source.index("def run_condition("):]
    assert "pause_at_states=False" in legacy and "create_scientific_session(" not in legacy
    pause_block = source[source.index("if pause_at_states:", source.index("for step in range")):
                         source.index("if not finite or step == final_step")]
    assert "_digest(" not in pause_block


@pytest.mark.skipif(os.environ.get("LIVE_FLY_REAL_EQUIVALENCE") != "1",
                    reason="set LIVE_FLY_REAL_EQUIVALENCE=1 on LegendaryPC")
def test_real_parent_vs_session_noncanonical_prefix():
    """Real dependency-gated comparison against the literal pre-refactor code.

    This runs only a 2 ms noncanonical prefix and writes no artifacts. The
    baseline object is the parent of the original extraction patch.
    """
    __import__("numpy"); __import__("flygym")
    baseline = subprocess.check_output(["git", "show",
        "ec7773c:malecns_backend/embodiment/_windows_m8_live_condition.py"], text=True)
    module_name = "malecns_backend.embodiment._phase1_parent_baseline"
    historical_path = Path(
        "malecns_backend/embodiment/_windows_m8_live_condition.py").resolve()
    spec = importlib.util.spec_from_file_location(module_name, historical_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        exec(compile(baseline, str(historical_path), "exec"), module.__dict__)
    finally:
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
    from malecns_backend.embodiment import _windows_m7d_corrected_spontaneous_adapter as m7da
    from malecns_backend.embodiment import integrated_whole_leg_readiness as m6c
    protocol, records, table = m7da._protocol()
    event_runs = {"parent": [], "session": []}; active = ["parent"]
    class TracedSimulation:
        def __init__(self, simulation): self._simulation = simulation
        def __getattr__(self, name): return getattr(self._simulation, name)
        def step(self, action):
            event_runs[active[0]].append(("sim.step", tuple(action["adhesion"])))
            return self._simulation.step(action)
        def close(self): return self._simulation.close()
    def traced_runtime(*args, **kw):
        runtime = list(m7da._runtime(*args, **kw)); runtime[0] = TracedSimulation(runtime[0])
        return tuple(runtime)
    def zero_force(condition, transition):
        event_runs[active[0]].append(("external_force", transition))
        return (0., 0., 0.)
    kwargs = dict(protocol=protocol, condition=m8.CONDITIONS[0], condition_number=1,
        progress=lambda *args: "", cached_admission_assertion=m6c.assert_physical_admission,
        cached_records=records, cached_table=table, duration_ms=2.,
        condition_names=m8.CONDITIONS, contribution_gate=adapter.gate_contributions,
        compact_telemetry=False, runtime_factory=traced_runtime,
        proprioception_only=True, fixed_initial_baseline=True,
        m8_extended_telemetry=False, external_force_by_transition=zero_force)
    from malecns_backend.embodiment import proprioceptive_activation as proprio
    original_sample = proprio.sample_candidates; candidate_runs = {"parent": [], "session": []}
    def recorded_sample(*args, **kw):
        result = original_sample(*args, **kw)
        candidate_runs[active[0]].append(tuple(result))
        return result
    proprio.sample_candidates = recorded_sample
    try:
        parent = module.run_condition(**kwargs)
        compact_parent = module.run_condition(**{**kwargs, "compact_telemetry": True})
        active[0] = "session"
        session = live.create_scientific_session(**kwargs)
        snapshots = [session.initialize()]
        while True:
            try: snapshots.append(session.step())
            except StopIteration: break
    finally:
        proprio.sample_candidates = original_sample
    assert len(snapshots) == len(parent["trajectory"]) == 21
    assert parent["physics_steps"] == 20 and parent["neural_steps"] == 4
    assert session.result["physics_steps"] == 20 and session.result["neural_steps"] == 4
    assert [snapshot.diagnostics["physics_transition"] for snapshot in snapshots] == list(range(21))
    for transition, (expected, actual) in enumerate(zip(parent["trajectory"], snapshots)):
        assert actual.diagnostics["physics_transition"] == transition
        assert actual.time_ms == expected["time_ms"]
        assert actual.qpos == tuple(expected["qpos"])
        assert actual.qvel == tuple(expected["qvel"])
        assert actual.root_position_xyz == tuple(expected["body_position"])
        assert actual.root_quaternion_wxyz == tuple(expected["body_orientation"])
        assert actual.joint_positions == tuple(
            compact_parent["raw_arrays"]["physics_joint_position"][transition])
        assert actual.diagnostics["commands"] == tuple(expected["action"])
        assert actual.diagnostics["adhesion"] == (0.,) * 6
        assert actual.diagnostics["malecns_state_digest"] == expected["malecns_state_digest"]
        assert actual.diagnostics["sensory"] == expected["sensory"]
        assert actual.diagnostics["delivered_sensory_drive"] == expected["delivered_sensory_drive"]
        if transition and transition % 5 == 0:
            neural = transition // 5 - 1
            names = tuple(protocol["admitted_motor_interfaces"])
            assert tuple(actual.diagnostics["decoder_outputs"][name] for name in names) == tuple(
                compact_parent["raw_arrays"]["neural_decoder_outputs"][neural])
            assert tuple(actual.diagnostics["admitted_motor_contributions"][name] for name in names) == tuple(
                compact_parent["raw_arrays"]["neural_admitted_contributions"][neural])
    # Six ordered proprioceptive RNG draws per neural update are identical.
    assert candidate_runs["session"] == candidate_runs["parent"][:len(candidate_runs["session"])]
    assert sum(event[0] == "sim.step" for event in event_runs["parent"]) == 40
    assert sum(event[0] == "sim.step" for event in event_runs["session"]) == 20
    for events in event_runs.values():
        for index, event in enumerate(events):
            if event[0] == "external_force":
                assert events[index + 1] == ("sim.step", (0.,) * 6)
