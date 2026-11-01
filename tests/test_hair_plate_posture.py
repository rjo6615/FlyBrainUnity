"""Synthetic checks for Step C evaluation; no CNS or physics."""
import copy
import math

import pytest

from malecns_backend.live import hair_plate_posture as c


def test_tilt_from_quaternion():
    assert c.tilt_deg([0, 0, 0, 1, 0, 0, 0]) == pytest.approx(0)
    assert c.tilt_deg([0, 0, 0, math.cos(math.pi/4), math.sin(math.pi/4), 0, 0]) == pytest.approx(90)
    assert c.tilt_deg([0, 0, 0, 0, 1, 0, 0]) == pytest.approx(180)


BODYMAP = dict(muscles=[
    dict(name='Pleural remotor/abductor MN T1 left', actuator='coxa_T1_left', idx=[1]),
    dict(name='Pleural remotor/abductor MN T1 left', actuator='coxa_abduct_T1_left', idx=[1]),
    dict(name='Tergopleural/Pleural promotor MN T1 left', actuator='coxa_T1_left', idx=[2]),
    dict(name='Sternal posterior rotator MN T2 left', actuator='coxa_twist_T2_left', idx=[3]),
    dict(name='Ti flexor MN T1 left', actuator='tibia_T1_left', idx=[9])])


def test_mn_sets_and_window_rate():
    sets, legs = c.mn_sets(BODYMAP)
    assert sets == dict(coxa={1, 2, 3}, posterior={1, 3}, anterior={2}) and legs == {'T1 left': {1, 2}, 'T2 left': {3}}
    arm = dict(neural=[dict(time_ms=500., fired=[1]), dict(time_ms=600., fired=[1, 2]), dict(time_ms=2000., fired=[1])])
    assert c.rate(arm, {1}) == pytest.approx(2/1.48)


def arm(name, *, coxa_spikes=0, post=0, ant=0, release_tail=False, delivered=None):
    samples = [dict(qpos=[0, 0, 0, 1, 0, 0, 0]) for _ in range(c.STEPS + 1)]
    if release_tail:
        for s in samples[c.EVENT_STATE + 1:]:
            s['qpos'] = [0, 0, 0, 0, 1, 0, 0]
    neural = [dict(time_ms=(k + 1)*.5, uniforms_sha256=str(k), fired=[], hair_delivered=[]) for k in range(c.TICKS)]
    t = neural[2000]  # 1000.5 ms, inside the window
    t['fired'] = [3]*post + [2]*ant + [1]*coxa_spikes
    if delivered or (delivered is None and name.endswith('_ON')):
        t['hair_delivered'] = [7]
    release = name.startswith('R_')
    return dict(run_status='COMPLETE', samples=samples, neural=neural, initial=dict(external_schedule=[1, 2]),
                event=dict(state_index=c.EVENT_STATE, operation='ZERO_FULL_SELECTED_ROWS' if release else 'OBSERVE_ONLY',
                           after_sha256='n' if release else 'o', neutral_sha256='n', original_sha256='o'))


def world(**over):
    arms = dict(A_OFF=arm('A_OFF', post=2), A_ON=arm('A_ON', post=20),
                R_OFF=arm('R_OFF', post=2, release_tail=True), R_ON=arm('R_ON', post=2, release_tail=True))
    arms.update(over)
    return arms


def test_posture_sensitive_and_reflex_labels():
    e = c.evaluate(world(), BODYMAP)
    assert e['status'] == 'INTEGRITY_ACCEPTED' and all(e['checks'].values())
    assert e['Q1']['label'] == 'POSTURE_SENSITIVE' and e['Q2']['label'] == 'REFLEX_DIRECTION_CONSISTENT'
    assert e['posture']['R_OFF']['rollover_samples'] == c.STEPS - 5200
    assert e['first_divergence_A_vs_R'] == dict(OFF=c.EVENT_STATE + 1, ON=c.EVENT_STATE + 1)


def test_null_labels_when_on_changes_nothing():
    e = c.evaluate(world(A_ON=arm('A_ON', post=2)), BODYMAP)
    assert e['Q1']['label'] == 'NOT_POSTURE_SENSITIVE' and e['Q2']['label'] == 'NOT_CONSISTENT'


@pytest.mark.parametrize('fault', ['incomplete', 'rng', 'prefix', 'event', 'delivery_off', 'delivery_on'])
def test_integrity_failures_block_labels(fault):
    arms = world()
    if fault == 'incomplete': arms['R_ON']['run_status'] = 'ERROR'
    if fault == 'rng': arms['R_ON']['neural'][5]['uniforms_sha256'] = 'x'
    if fault == 'prefix': arms['R_OFF']['samples'][100]['qpos'] = [9]*7
    if fault == 'event': arms['R_OFF']['event']['after_sha256'] = 'o'
    if fault == 'delivery_off': arms['A_OFF']['neural'][10]['hair_delivered'] = [7]
    if fault == 'delivery_on': arms['A_ON']['neural'][2000]['hair_delivered'] = []
    e = c.evaluate(arms, BODYMAP)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and 'Q1' not in e


def test_protocol_lock_and_arm_order():
    assert c.protocol()['arms']['order'] == list(c.ARMS)
