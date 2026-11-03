"""Synthetic checks for the middle-leg coxa displacement test: bias shift, labels, integrity, context."""
import copy
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.live import middle_coxa_displacement as m
from malecns_backend.live import hair_plate_posture as c

V3 = ('a', 'b')
IDX = {'joint_LMCoxa': 7, 'joint_RMCoxa': 28}
UP = [0, 0, 0, 1, 0, 0, 0]
LEGS = ('LF', 'LM', 'LH', 'RF', 'RM', 'RH')
SPEC = dict(displacement=dict(delta_rad=dict(m.DELTA)), candidates=dict(H1=dict(sha256='h1'), H1_FLIP=dict(sha256='hf')))


def test_shift_rows_and_expected_record(monkeypatch):
    gain = np.zeros((30, 3)); bias = np.zeros((30, 3))
    gain[7, 0], gain[28, 0] = 20., 30.
    bias[7, 1], bias[28, 1] = -20., -30.
    arrays = dict(actuator_gainprm=gain, actuator_biasprm=bias)
    monkeypatch.setattr(m.mechanical, 'validate_binding', lambda inv, rec: None)
    monkeypatch.setattr(m.mechanical, 'array_values', lambda rec, name: arrays[name])
    inv = dict(rows=[dict(coordinate='joint_LMCoxa', actuator_id=7), dict(coordinate='joint_RMCoxa', actuator_id=28)])
    rows = m.shift_rows(inv, None)
    assert [(n, a) for n, a, _, _ in rows] == [('joint_LMCoxa', 7), ('joint_RMCoxa', 28)]
    assert rows[0][3] == pytest.approx(20.*m.DELTA['joint_LMCoxa']) and rows[0][3] < 0  # equilibrium moves forward
    model = SimpleNamespace(actuator_biasprm=bias.copy())
    m.write_shift(model, rows)
    changed = np.argwhere(model.actuator_biasprm != bias)
    assert changed.tolist() == [[7, 0], [28, 0]]
    # equilibrium of kp*ctrl + b0 - kp*q is ctrl + b0/kp = ctrl + Delta
    assert model.actuator_biasprm[28, 0]/30. == pytest.approx(m.DELTA['joint_RMCoxa'])
    bias[7, 1] = -19.
    with pytest.raises(ValueError):
        m.shift_rows(inv, None)


def make_arm(kind, seed, d_lm=0., d_rm=0., hair=120.):
    base = [0.]*42
    cmd = list(base)
    if m.KINDS[kind] is not None:
        cmd[7] = cmd[28] = .1 if kind == 'PC' else -.1
    samples = [dict(time_s=i*1e-4, qpos=UP, commanded_joints=base if i < 6000 else cmd) for i in range(c.STEPS + 1)]
    samples[0]['commanded_joints'] = None
    fwd = dict.fromkeys(LEGS, .2); fwd['LM'] += d_lm; fwd['RM'] += d_rm
    neural = [dict(time_ms=(k + 1)*.5, uniforms_sha256=f'{seed}-{k}', fired=[], hair_delivered=[],
                   hair_forward=dict(fwd), hair_rate_hz=dict.fromkeys(LEGS, hair)) for k in range(c.TICKS)]
    channels = {'a': dict(index=5), 'b': dict(index=6)}
    hyp = m.KINDS[kind] is not None
    if hyp:
        channels.update({n: dict(index=i) for n, i in IDX.items()})
    event = dict(state_index=m.EVENT_STATE, operation=m.OPERATION, after_sha256='x', expected_sha256='x',
                 shifted=[dict(coordinate=n, delta_rad=m.DELTA[n]) for n in m.CANDIDATES])
    return dict(run_status='COMPLETE', samples=samples, neural=neural, event=event,
                hypothesis_channels=sorted(IDX) if hyp else [], definitions_sha256={'PC': 'h1', 'PF': 'hf'}.get(kind),
                initial=dict(external_schedule=[1, 2], channels=channels, cns_seed=seed))


def world(**over):
    arms = {}
    for s in m.SEEDS:
        arms[f'P0_{s}'] = make_arm('P0', s)
        arms[f'PC_{s}'] = make_arm('PC', s, d_lm=-.05, d_rm=-.03)
        arms[f'PF_{s}'] = make_arm('PF', s, d_lm=.04, d_rm=.01)
    arms.update(over)
    c0 = {s: copy.deepcopy(arms[f'P0_{s}']) for s in m.SEEDS}
    return arms, c0


def test_labels_and_flags():
    arms, c0 = world(PF_2=make_arm('PF', 2, d_lm=.04, d_rm=.03))
    e = m.evaluate(arms, c0, SPEC, V3, IDX)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['labels'] == {'joint_LMCoxa': 'C2_PASSED', 'joint_RMCoxa': 'C2_PARTIAL'}
    assert e['per_seed']['joint_RMCoxa'][2]['passed'] and not e['per_seed']['joint_RMCoxa'][1]['passed']
    assert not e['flags']['joint_LMCoxa']['NO_DRIVE'] and not e['flags']['joint_LMCoxa']['ROLLOVER']
    assert m.label([False]*3) == 'C2_NOT_SUPPORTED'


def test_context_precondition():
    arms, c0 = world(P0_3=make_arm('P0', 3, hair=29.))
    c0[3] = copy.deepcopy(arms['P0_3'])
    e = m.evaluate(arms, c0, SPEC, V3, IDX)
    assert e['status'] == 'INCONCLUSIVE_CONTEXT' and 'labels' not in e


@pytest.mark.parametrize('fault', ['incomplete', 'rng', 'c0_prefix', 'operation', 'delta', 'expected', 'hash',
                                   'bound', 'p0_command', 'prefix', 'seed'])
def test_integrity_faults(fault):
    arms, c0 = world()
    if fault == 'incomplete': arms['PF_2']['run_status'] = 'ERROR'
    if fault == 'rng': arms['PC_3']['neural'][9]['uniforms_sha256'] = 'x'
    if fault == 'c0_prefix': c0[2]['samples'][100]['qpos'] = [0, 0, 1, 1, 0, 0, 0]
    if fault == 'operation': arms['PC_1']['event']['operation'] = 'OBSERVE_ONLY'
    if fault == 'delta': arms['P0_2']['event']['shifted'][1]['delta_rad'] = -.3
    if fault == 'expected': arms['PF_1']['event']['after_sha256'] = 'y'
    if fault == 'hash': arms['PC_2']['definitions_sha256'] = 'hf'
    if fault == 'bound':
        for s in arms['PC_1']['samples'][7000:]:
            s['commanded_joints'] = [.3 if i == 7 else 0. for i in range(42)]
    if fault == 'p0_command': arms['P0_1']['samples'][3000]['commanded_joints'] = [0.]*7 + [.1] + [0.]*34
    if fault == 'prefix': arms['PC_2']['samples'][10]['qpos'] = [0, 0, 1, 1, 0, 0, 0]
    if fault == 'seed':
        for k in m.KINDS:
            arms[f'{k}_3']['neural'][0]['uniforms_sha256'] = '1-0'
    e = m.evaluate(arms, c0, SPEC, V3, IDX)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'labels' not in e


def test_protocol_lock():
    spec = m.protocol()
    assert spec['arms']['order'] == list(m.ARMS)
    assert spec['displacement']['delta_rad'] == m.DELTA
    assert spec['candidates']['H1']['action_index'] == IDX
