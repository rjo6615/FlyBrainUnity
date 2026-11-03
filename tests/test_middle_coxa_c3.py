"""Synthetic checks for the middle-leg coxa C3 confirmation: arm set, REPRO, labels, integrity, context."""
import copy

import pytest

from malecns_backend.live import middle_coxa_c3 as t3
from malecns_backend.live import middle_coxa_displacement as m
from malecns_backend.live import hair_plate_posture as c

V3 = ('a', 'b')
IDX = {'joint_LMCoxa': 7, 'joint_RMCoxa': 28}
UP = [0, 0, 0, 1, 0, 0, 0]
LEGS = ('LF', 'LM', 'LH', 'RF', 'RM', 'RH')
SPEC = dict(context=dict(delta_rad=dict(m.DELTA)), candidates=dict(H1=dict(sha256='h1'), H1_FLIP=dict(sha256='hf')))


def make_arm(kind, seed, d_lm=0., d_rm=0., hair=120., pre=0.):
    base = [0.]*42
    cmd = list(base)
    if m.KINDS[kind] is not None:
        cmd[7] = cmd[28] = .1 if kind == 'PC' else -.1
    samples = [dict(time_s=i*1e-4, qpos=UP, commanded_joints=base if i < 6000 else cmd) for i in range(c.STEPS + 1)]
    samples[0]['commanded_joints'] = None
    neural = []
    for k in range(c.TICKS):
        t = (k + 1)*.5
        fwd = dict.fromkeys(LEGS, .2)
        if t > 500.5:
            fwd['LM'] += d_lm; fwd['RM'] += d_rm
        elif t > 400.:
            fwd['LM'] += pre
        neural.append(dict(time_ms=t, uniforms_sha256=f'{seed}-{k}', fired=[], hair_delivered=[],
                           hair_forward=fwd, hair_rate_hz=dict.fromkeys(LEGS, hair)))
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
    arms = {'REPRO_1': make_arm('P0', 1)}
    for s in t3.SEEDS:
        arms[f'P0_{s}'] = make_arm('P0', s)
        arms[f'PC_{s}'] = make_arm('PC', s, d_lm=-.05, d_rm=-.03, pre=-.001)
        arms[f'PF_{s}'] = make_arm('PF', s, d_lm=.04, d_rm=.01)
    arms.update(over)
    c2 = {s: make_arm('P0', s) for s in (1, 2, 3)}
    return arms, c2


def test_arm_set_and_split():
    assert t3.ARMS[0] == 'REPRO_1' and len(t3.ARMS) == 10
    assert t3.split('REPRO_1') == ('P0', 1) and t3.split('PF_6') == ('PF', 6)
    with pytest.raises(ValueError):
        t3.split('P0_1')


def test_labels_status_and_pre_measure():
    arms, c2 = world(PF_5=make_arm('PF', 5, d_lm=.04, d_rm=.03))
    e = t3.evaluate(arms, c2, SPEC, V3, IDX)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['labels'] == {'joint_LMCoxa': 'CONFIRMED', 'joint_RMCoxa': 'PARTIAL'}
    assert e['coordinate_status'] == {'joint_LMCoxa': 'CONDITIONAL', 'joint_RMCoxa': 'C2_PASSED_ONLY'}
    assert e['per_seed']['joint_LMCoxa'][4]['pre_d_pc'] == pytest.approx(-.001)
    pre = e['offsets_before_vs_window_rad']['PC_4']['joint_LMCoxa']
    assert pre['before_event'] == 0. and 0.09 < pre['window'] <= .1
    assert t3.label([False]*3) == 'NOT_CONFIRMED' and t3.STATUS['NOT_CONFIRMED'] == 'NOT_SUPPORTED'


def test_context_precondition():
    arms, c2 = world(P0_6=make_arm('P0', 6, hair=10.))
    assert t3.evaluate(arms, c2, SPEC, V3, IDX)['status'] == 'INCONCLUSIVE_CONTEXT'


@pytest.mark.parametrize('fault', ['incomplete', 'rng', 'repro_qpos', 'repro_event', 'operation', 'delta', 'hash',
                                   'bound', 'p0_command', 'prefix', 'old_seed', 'repro_seed'])
def test_integrity_faults(fault):
    arms, c2 = world()
    if fault == 'incomplete': arms['PF_5']['run_status'] = 'ERROR'
    if fault == 'rng': arms['PC_6']['neural'][9]['uniforms_sha256'] = 'x'
    if fault == 'repro_qpos': arms['REPRO_1']['samples'][15000]['qpos'] = [0, 0, 1, 1, 0, 0, 0]
    if fault == 'repro_event': c2[1]['event']['after_sha256'] = 'y'
    if fault == 'operation': arms['PC_4']['event']['operation'] = 'OBSERVE_ONLY'
    if fault == 'delta': arms['P0_5']['event']['shifted'][0]['delta_rad'] = -.3
    if fault == 'hash': arms['PC_5']['definitions_sha256'] = 'hf'
    if fault == 'bound':
        for s in arms['PC_4']['samples'][7000:]:
            s['commanded_joints'] = [.3 if i == 28 else 0. for i in range(42)]
    if fault == 'p0_command': arms['REPRO_1']['samples'][3000]['commanded_joints'] = [0.]*7 + [.1] + [0.]*34
    if fault == 'prefix': arms['PF_6']['samples'][10]['qpos'] = [0, 0, 1, 1, 0, 0, 0]
    if fault == 'old_seed':
        for k in m.KINDS:
            for t in arms[f'{k}_4']['neural']:
                t['uniforms_sha256'] = t['uniforms_sha256'].replace('4-', '2-', 1)
    if fault == 'repro_seed': arms['REPRO_1']['initial']['cns_seed'] = 4
    e = t3.evaluate(arms, c2, SPEC, V3, IDX)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'labels' not in e


def test_protocol_lock():
    spec = t3.protocol()
    assert spec['arms']['order'] == list(t3.ARMS) and spec['arms']['seeds'] == list(t3.SEEDS)
    assert spec['context']['delta_rad'] == m.DELTA
    assert spec['candidates']['H1']['sha256'] == m.protocol()['candidates']['H1']['sha256']
