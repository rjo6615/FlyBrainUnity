"""Synthetic checks for the coxa push-response test: force schedule/audit, D integral, labels, integrity."""
import copy

import numpy as np
import pytest

from malecns_backend.live import coxa_push_response as p
from malecns_backend.live import hair_plate_posture as c

V3 = ('a', 'b')
IDX = {'joint_LFCoxa': 0, 'joint_LMCoxa': 7, 'joint_LHCoxa': 14, 'joint_RMCoxa': 28}
LEGS = ('LF', 'LM', 'LH', 'RF', 'RM', 'RH')
BODY = dict(id=3, name='Thorax', frame='world', point='body COM', torque=[0., 0., 0.])
SPEC = dict(candidates=dict(H1=dict(sha256='h1'), H1_FLIP=dict(sha256='hf')))
DEV = {'N': .1, 'C': .08, 'X': .1}  # F-push deviations: C attenuates, X does not


def make_arm(kind, push, seed, dev=None):
    dev = (DEV[kind] if push == 'F' else .1) if dev is None else dev
    sign = p.PUSHES[push]
    base = [0.]*42
    cmd = list(base)
    if p.SETS[kind] is not None:
        for i in IDX.values():
            cmd[i] = .1 if kind == 'C' else -.1
    samples = []
    for i in range(c.STEPS + 1):
        x = dev*sign if sign and i > p.START else 0.
        v = p.force_at_transition(push, i - 1) if i else (0., 0., 0.)
        samples.append(dict(time_s=i*1e-4, qpos=[x, 0, 1., 1, 0, 0, 0], qvel=[0.]*6, supports=6,
                            commanded_joints=None if i == 0 else (base if i < 1000 else cmd),
                            applied_body_wrenches=[] if not any(v) else [dict(body_id=3, wrench=list(v) + [0., 0., 0.])],
                            external_applied_max=float(max(abs(t) for t in v)), generalized_applied_max=0.))
    neural = [dict(time_ms=(k + 1)*.5, uniforms_sha256=f'{seed}-{k}', fired=[], hair_delivered=[],
                   hair_rate_hz=dict.fromkeys(LEGS, 60.), hair_forward=dict.fromkeys(LEGS, 0.)) for k in range(c.TICKS)]
    channels = {'a': dict(index=5), 'b': dict(index=6)}
    hyp = p.SETS[kind] is not None
    if hyp:
        channels.update({n: dict(index=i) for n, i in IDX.items()})
    return dict(run_status='COMPLETE', samples=samples, neural=neural, event={},
                hypothesis_channels=sorted(IDX) if hyp else [], label=p.LABEL if hyp else None,
                definitions_sha256={'C': 'h1', 'X': 'hf'}.get(kind),
                initial=dict(external_schedule=[1, 2], channels=channels, cns_seed=seed, force_body=dict(BODY)))


def world(**over):
    arms = {a: make_arm(*p.split(a)) for a in p.ARMS}
    arms.update(over)
    c0 = {s: copy.deepcopy(arms[f'N0_{s}']) for s in p.SEEDS}
    return arms, c0


def test_arms_force_schedule_and_audit():
    assert len(p.ARMS) == 27 and p.split('XB_3') == ('X', 'B', 3)
    assert p.force_at_transition('F', 4999) == (0., 0., 0.) and p.force_at_transition('F', 5000) == (1.024, 0., 0.)
    assert p.force_at_transition('B', 5199) == (-1.024, 0., 0.) and p.force_at_transition('B', 5200) == (0., 0., 0.)
    assert p.force_at_transition('0', 5100) == (0., 0., 0.)
    arm = make_arm('N', 'F', 1)
    assert p.force_ok(arm, 'F') and not p.force_ok(arm, 'B') and not p.force_ok(arm, '0')
    assert sum(bool(s['applied_body_wrenches']) for s in arm['samples']) == 200


def test_deviation_integral():
    from malecns_backend.live import tactile_recovery_metrics as metrics
    pushed, ctrl = make_arm('N', 'F', 1, dev=.1), make_arm('N', '0', 1)
    tp, tc = (metrics.trace(a, [s['supports'] for s in a['samples']]) for a in (pushed, ctrl))
    assert p.deviation_integral(tp, tc) == pytest.approx(.1*(c.STEPS - p.FIRST_CLEARED)*1e-4)


def test_labels():
    assert p.q_loop([.9, .5, .8]) == 'LOOP_ATTENUATES' and p.q_loop([1.1, 2., 1.5]) == 'LOOP_AMPLIFIES'
    assert p.q_loop([.89, .91, .5]) == 'NO_CONSISTENT_LOOP_EFFECT'
    assert p.q_sign('NO_CONSISTENT_LOOP_EFFECT', [0, 0, 0]) == 'NOT_EVALUATED'
    assert p.q_sign('LOOP_ATTENUATES', [1., .95, .5]) == 'SIGN_SPECIFIC'
    assert p.q_sign('LOOP_ATTENUATES', [.5, .8, 1.]) == 'SIGN_INDEPENDENT'


def test_accepted_world():
    arms, c0 = world()
    e = p.evaluate(arms, c0, SPEC, V3, IDX)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['labels']['F'] == dict(Q_LOOP='LOOP_ATTENUATES', Q_SIGN='SIGN_SPECIFIC')
    assert e['labels']['B'] == dict(Q_LOOP='NO_CONSISTENT_LOOP_EFFECT', Q_SIGN='NOT_EVALUATED')
    assert e['ratios']['F']['loop'] == pytest.approx([.8]*3)
    assert e['fore_aft_deviation']['NB_2']['cleared_mean_along_push_mm'] == pytest.approx(.1)


def test_pulse_precondition():
    arms, c0 = world(NB_2=make_arm('N', 'B', 2, dev=.001))
    assert p.evaluate(arms, c0, SPEC, V3, IDX)['status'] == 'INCONCLUSIVE_PULSE'


@pytest.mark.parametrize('fault', ['incomplete', 'rng', 'c0', 'force', 'force_on_control', 'body', 'hash', 'label',
                                   'bound', 'n_command', 'push_prefix', 'seed'])
def test_integrity_faults(fault):
    arms, c0 = world()
    if fault == 'incomplete': arms['XF_2']['run_status'] = 'ERROR'
    if fault == 'rng': arms['CB_3']['neural'][7]['uniforms_sha256'] = 'x'
    if fault == 'c0': c0[1]['samples'][15000]['qpos'] = [0, 0, 2., 1, 0, 0, 0]
    if fault == 'force': arms['CF_1']['samples'][5100]['applied_body_wrenches'][0]['wrench'][0] = 1.
    if fault == 'force_on_control':
        arms['C0_2']['samples'][5100]['applied_body_wrenches'] = [dict(body_id=3, wrench=[1.024, 0, 0, 0, 0, 0])]
    if fault == 'body': arms['NF_3']['initial']['force_body']['torque'] = [0., 0., 1.]
    if fault == 'hash': arms['CF_2']['definitions_sha256'] = 'hf'
    if fault == 'label': arms['X0_1']['label'] = None
    if fault == 'bound':
        for s in arms['CB_1']['samples'][2000:]:
            s['commanded_joints'] = [.3 if i == 7 else 0. for i in range(42)]
    if fault == 'n_command': arms['NB_1']['samples'][3000]['commanded_joints'] = [.1] + [0.]*41
    if fault == 'push_prefix': arms['XB_2']['samples'][4000]['qpos'] = [0, 0, 2., 1, 0, 0, 0]
    if fault == 'seed':
        for a in p.ARMS:
            if a.endswith('_3'):
                arms[a]['neural'][0]['uniforms_sha256'] = '1-0'
    e = p.evaluate(arms, c0, SPEC, V3, IDX)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'labels' not in e


def test_protocol_lock():
    spec = p.protocol()
    assert spec['arms']['order'] == list(p.ARMS)
    assert spec['disturbance']['directions']['F'] == [p.MAGNITUDE, 0., 0.]
    assert spec['candidates']['H1']['action_index'] == IDX
