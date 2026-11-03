"""Synthetic checks for the released-posture coxa test: release variant, T_roll, labels, integrity."""
import copy
import math
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.live import coxa_release_posture as rp
from malecns_backend.live import hair_plate_posture as c

V3 = ('a', 'b')
IDX = {'joint_LFCoxa': 0, 'joint_LHCoxa': 14}
UP = [0, 0, 0, 1, 0, 0, 0]
DOWN = [0, 0, 0, 0, 1, 0, 0]  # 180 deg tilt
R22_IDS = [0, 1, 2, 7, 14]
K_IDS = [1, 2, 7]
SPEC = dict(release=dict(R22=dict(actuator_ids=R22_IDS), K=dict(actuator_ids=K_IDS)),
            candidates=dict(H1=dict(sha256='h1'), H1_FLIP=dict(sha256='hf')))


def test_released_rows_and_write(monkeypatch):
    rows = [dict(coordinate=n, actuator_id=i) for n, i in
            (('joint_LFCoxa', 0), ('joint_LFCoxa_roll', 1), ('joint_LHCoxa', 14), ('joint_RFCoxa', 21))]
    assert [r['actuator_id'] for r in rp.released_rows(rows, rp.KEEP)] == [1, 21]
    with pytest.raises(ValueError):
        rp.released_rows(rows, ('joint_XX',))
    monkeypatch.setattr(rp.mechanical, 'partition', lambda inv: ([], rows))
    model = SimpleNamespace(actuator_gainprm=np.ones((30, 3)), actuator_biasprm=np.ones((30, 3)))
    rp.write_rows_except(model, None, rp.KEEP)
    zeroed = sorted(set(np.flatnonzero(~model.actuator_gainprm.any(axis=1))))
    assert zeroed == [1, 21] and model.actuator_biasprm[0].all() and model.actuator_biasprm[14].all()


def samples_rolling(at_sample):
    out = [dict(time_s=i*1e-4, qpos=UP, commanded_joints=[0.]*42) for i in range(c.STEPS + 1)]
    if at_sample is not None:
        for s in out[at_sample:]:
            s['qpos'] = DOWN
    return out


def test_t_roll_and_censoring():
    assert rp.t_roll(samples_rolling(8000)) == (pytest.approx(800.), False)
    assert rp.t_roll(samples_rolling(None)) == (2000., True)
    early = samples_rolling(100)  # tilt before the release does not count
    for s in early[rp.EVENT_STATE + 1:]:
        s['qpos'] = UP
    assert rp.t_roll(early) == (2000., True)


def test_labels():
    assert rp.consistent([20, 25, 40]) == 'DELAYS' and rp.consistent([-20, -30, -21]) == 'HASTENS'
    assert rp.consistent([20, 19.9, 40]) is None
    assert rp.q_sign(None, [0, 0, 0]) == 'NOT_EVALUATED'
    assert rp.q_sign('DELAYS', [0, 30, 0]) == 'SIGN_SPECIFIC' and rp.q_sign('DELAYS', [25, 30, 0]) == 'SIGN_INDEPENDENT'
    roll = {f'{k}_{s}': 800. for s in rp.SEEDS for k in rp.KINDS}
    over = dict.fromkeys(roll, True)
    lab = rp.labels(roll, over)
    assert lab['Q_ASSIST']['label'] == 'NO_CONSISTENT_ASSIST_EFFECT' and lab['Q_NEURAL']['label'] == 'NO_CONSISTENT_LOOP_EFFECT'
    assert lab['Q_SIGN']['label'] == 'NOT_EVALUATED' and lab['Q_RESCUE']['label'] == 'NO_RESCUE'
    for s in rp.SEEDS:
        roll[f'KC_{s}'] = 2000.; over[f'KC_{s}'] = False
    lab = rp.labels(roll, over)
    assert lab['Q_NEURAL']['label'] == 'LOOP_DELAYS' and lab['Q_SIGN']['label'] == 'SIGN_SPECIFIC'
    assert lab['Q_RESCUE']['label'] == 'RESCUE'


def make_arm(kind, seed, roll_at=8000):
    base = [0.]*42
    cmd = list(base)
    if rp.KINDS[kind] is not None:
        cmd[0] = cmd[14] = .1 if kind == 'KC' else -.1
    samples = samples_rolling(roll_at)
    for i, s in enumerate(samples):
        s['commanded_joints'] = base if i < 1000 else cmd
    samples[0]['commanded_joints'] = None
    neural = [dict(time_ms=(k + 1)*.5, uniforms_sha256=f'{seed}-{k}', fired=[], hair_delivered=[],
                   hair_forward=dict.fromkeys(('LF', 'LM', 'LH', 'RF', 'RM', 'RH'), .5),
                   hair_rate_hz=dict.fromkeys(('LF', 'LM', 'LH', 'RF', 'RM', 'RH'), 120.)) for k in range(c.TICKS)]
    channels = {'a': dict(index=5), 'b': dict(index=6)}
    hyp = rp.KINDS[kind] is not None
    if hyp:
        channels.update({n: dict(index=i) for n, i in IDX.items()})
    group = 'R22' if kind == 'R22' else 'K'
    event = dict(state_index=rp.EVENT_STATE, operation=rp.OPERATION[kind], after_sha256=group, neutral_sha256=group,
                 released_actuator_ids=SPEC['release'][group]['actuator_ids'],
                 kept_coordinates=[] if group == 'R22' else sorted(rp.KEEP))
    return dict(run_status='COMPLETE', samples=samples, neural=neural, event=event,
                hypothesis_channels=sorted(IDX) if hyp else [], label=rp.LABEL if hyp else None,
                definitions_sha256={'KC': 'h1', 'KF': 'hf'}.get(kind),
                initial=dict(external_schedule=[1, 2], channels=channels, cns_seed=seed))


def world(**over):
    arms = {f'{k}_{s}': make_arm(k, s) for s in rp.SEEDS for k in rp.KINDS}
    arms.update(over)
    return arms, copy.deepcopy(arms['R22_1'])


def test_accepts_and_labels_consistent_world():
    arms, r_on = world(**{f'KC_{s}': make_arm('KC', s, roll_at=9000) for s in rp.SEEDS})
    e = rp.evaluate(arms, r_on, SPEC, V3, IDX)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['labels']['Q_NEURAL']['label'] == 'LOOP_DELAYS' and e['labels']['Q_SIGN']['label'] == 'SIGN_SPECIFIC'
    assert e['labels']['Q_ASSIST']['label'] == 'NO_CONSISTENT_ASSIST_EFFECT'
    assert e['t_roll_ms']['KC_2'] == pytest.approx(900.)


@pytest.mark.parametrize('fault', ['incomplete', 'rng', 'step_c', 'release_ids', 'neutral', 'hash', 'bound',
                                   'r22_prefix', 'seed', 'command_in_k'])
def test_integrity_faults(fault):
    arms, r_on = world()
    if fault == 'incomplete': arms['KF_2']['run_status'] = 'ERROR'
    if fault == 'rng': arms['KC_3']['neural'][7]['uniforms_sha256'] = 'x'
    if fault == 'step_c': r_on['samples'][9]['qpos'] = DOWN
    if fault == 'release_ids': arms['K_2']['event']['released_actuator_ids'] = R22_IDS
    if fault == 'neutral': arms['KF_1']['event']['after_sha256'] = 'other'
    if fault == 'hash': arms['KC_1']['definitions_sha256'] = 'hf'
    if fault == 'bound':
        arms['KC_2'] = make_arm('KC', 2)
        for s in arms['KC_2']['samples'][2000:]:
            s['commanded_joints'] = [.3 if i in (0, 14) else 0. for i in range(42)]
    if fault == 'r22_prefix': arms['R22_3']['samples'][4000]['qpos'] = DOWN
    if fault == 'seed':
        for k in rp.KINDS:
            arms[f'{k}_2']['neural'][0]['uniforms_sha256'] = '1-0'
    if fault == 'command_in_k':
        arms['K_1']['samples'][3000]['commanded_joints'] = [.1] + [0.]*41
    e = rp.evaluate(arms, r_on, SPEC, V3, IDX)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'labels' not in e


def test_protocol_lock_and_release_sets():
    spec = rp.protocol()
    assert spec['arms']['order'] == list(rp.ARMS)
    r22, k = spec['release']['R22']['actuator_ids'], spec['release']['K']['actuator_ids']
    assert len(r22) == 22 and len(k) == 20 and sorted(set(r22) - set(k)) == [0, 14]
    assert spec['candidates']['label'] == rp.LABEL
