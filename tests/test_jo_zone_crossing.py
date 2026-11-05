"""Synthetic checks for antennal gravity Step D; no FlyGym, CNS or physics run."""
import copy
import math
from types import SimpleNamespace

import numpy as np
import pytest

from malecns_backend.live import jo_zone_crossing as m
from malecns_backend.live import antennal_gravity_live as live
from malecns_backend.live import coxa_push_response as pr
from malecns_backend.embodiment import antennal_gravity_encoder as ge


def test_arms_order_split_and_gravity():
    assert len(m.ARMS) == 37 and m.ARMS[0] == m.REPRO
    assert m.ARMS[1:7] == ('OFF_LEVEL_19', 'OFF_DOWN20_19', 'G1_LEVEL_19', 'G1_DOWN20_19', 'FLIP_LEVEL_19',
                           'FLIP_DOWN20_19')
    assert m.split('FLIP_DOWN20_24') == ('FLIP', 'DOWN20', 24)
    for bad in ('G1_UP_19', 'G1_LEVEL_13', 'G1_DOWN_20'):
        with pytest.raises(ValueError):
            m.split(bad)
    assert m.tilt_gravity('LEVEL') == list(m.G0)
    g = m.tilt_gravity('DOWN20')
    assert g[0] == pytest.approx(9810*math.sin(math.radians(20))) and g[1] == 0
    assert np.linalg.norm(g) == pytest.approx(9810)
    tilt, pitch, _ = live.body_angles(dict(qpos=[0, 0, 0, 1, 0, 0, 0], gravity=g))
    assert pitch == pytest.approx(20) and tilt == pytest.approx(20)


def _fake_trial(tilt, monkeypatch):
    t = object.__new__(m.Trial)
    t.samples, t.tilt, t.tilt_state, t.tilt_event = [], tilt, 3, None
    monkeypatch.setattr(pr.Trial, 'capture', lambda self, *a: self.samples.append({}))
    model = SimpleNamespace(opt=SimpleNamespace(gravity=np.array(m.G0)))
    physics = SimpleNamespace(model=model, data=SimpleNamespace(time=.0003))
    for _ in range(6):
        t.capture(physics, None, None)
    return t


@pytest.mark.parametrize('tilt', ['LEVEL', 'DOWN20'])
def test_capture_records_and_rotates(tilt, monkeypatch):
    t = _fake_trial(tilt, monkeypatch)
    g = m.tilt_gravity(tilt)
    assert [s['gravity'] for s in t.samples[:4]] == [list(m.G0)]*4
    assert [s['gravity'] for s in t.samples[4:]] == [g]*2
    assert t.tilt_event['state_index'] == 3 and t.tilt_event['gravity'] == g
    assert t.tilt_event['phi_deg'] == (0. if tilt == 'LEVEL' else -20.)


# ---- synthetic arms ----------------------------------------------------------------------

STEPS, EVENT = 40, 10


@pytest.fixture
def small(monkeypatch):
    monkeypatch.setattr(m.c, 'STEPS', STEPS)
    monkeypatch.setattr(m.c, 'TICKS', STEPS//5)
    monkeypatch.setattr(m.c, 'EVENT_STATE', EVENT)
    monkeypatch.setattr(live, 'PREFIX_MS', EVENT*.1 - .5)
    monkeypatch.setattr(live, 'SIGN_TICK_AFTER_MS', EVENT*.1)
    monkeypatch.setattr(live, 'WINDOW_MS', (EVENT*.1 + .5, STEPS*.1))
    monkeypatch.setattr(live, 'TONIC_MS', (0., EVENT*.1))


JO = {'C_left': [100], 'C_right': [101], 'E_left': [102], 'E_right': [103]}


def make_arm(name, pattern, d_level=-.18, d_down=.17):
    t, tilt, s = m.split(name)
    g = m.tilt_gravity(tilt)
    samples = []
    for i in range(STEPS + 1):
        after = i > EVENT
        q = [0, 0, 0, 1, 0, 0, .001*(tilt == 'DOWN20')] if after else [0, 0, 0, 1, 0, 0, 0]
        samples.append(dict(time_s=i*1e-4, qpos=q, commanded_joints=[0.]*42, gravity=g if after else list(m.G0),
                            applied_body_wrenches=[], external_applied_max=0., generalized_applied_max=0))
    neural = []
    for k in range(1, STEPS//5 + 1):
        tm = k*.5
        d = d_down if (tilt == 'DOWN20' and tm > EVENT*.1) else d_level
        rates = {f'{z}_{sn}': hz for sn in ('left', 'right') for z, hz in ge.zone_rates(d, m.ASSIGN[t]).items()}
        neural.append(dict(time_ms=tm, uniforms_sha256=f'u{s}-{k}', fired=list(pattern(t, tilt, s, tm)),
                           jo_d={'L': d, 'R': d}, jo_rate_hz=rates,
                           jo_delivered=[] if t == 'OFF' else [100 + k % 4], hair_delivered=[]))
    return dict(arm=name, run_status='COMPLETE', cns_seed=s, samples=samples, neural=neural,
                initial=dict(external_schedule=[1, 2, 100], cns_seed=s, jo_neurons=JO, jo_deliver=t != 'OFF',
                             jo_assignment=m.ASSIGN[t], force_body=dict(id=1, frame='world', point='body COM',
                                                                         torque=[0., 0., 0.])),
                event=dict(operation='OBSERVE_ONLY', after_sha256='x', original_sha256='x', state_index=EVENT),
                tilt_event=dict(state_index=EVENT, gravity=g))


GROUPS = {f'T{k} left x': {k} for k in range(1, 7)}
DN = {'DNp73': {7}, 'DNbe001': {8}}


def pattern_opposed(t, tilt, s, tm):
    """After the tilt, G1 and FLIP move pools and DNs in opposite directions in every seed."""
    out = [5] if tm > EVENT*.1 else []
    late = tm > EVENT*.1 + .5
    if late and t == 'G1':
        out += [1, 3, 7, 8] if tilt == 'LEVEL' else [2]
    if late and t == 'FLIP':
        out += [2] if tilt == 'LEVEL' else [1, 3, 7, 8]
    if late and t != 'OFF' and tilt == 'LEVEL' and s % 2:
        out += [4]
    return out


def build(pattern, **kw):
    arms = {n: make_arm(n, pattern, **kw) for n in m.ARMS[1:]}
    arms[m.REPRO] = dict(run_status='COMPLETE', samples=[dict(qpos=[0], commanded_joints=[0])]*(STEPS + 1),
                         neural=[dict(fired=[], uniforms_sha256='r', hair_delivered=[])]*(STEPS//5))
    return arms


def run_eval(arms, repro_ok=True):
    return m.evaluate(lambda k: copy.deepcopy(arms[k]), arms[m.REPRO], repro_ok, GROUPS, DN)


def test_evaluate_accepts_labels_and_predictions(small):
    e = run_eval(build(pattern_opposed))
    assert e['status'] == 'INTEGRITY_ACCEPTED', e.get('checks')
    assert e['O1'] is True
    assert e['labels'] == {'G1': 'JO_TILT_PATTERN_CONSISTENT', 'FLIP': 'JO_TILT_PATTERN_CONSISTENT'}
    assert e['r_GF'] < 0
    assert e['predictions'] == dict(P1='HELD', P2='HELD', P3='HELD', P4='HELD')
    assert e['window_d']['OFF_DOWN20_19']['L'] == pytest.approx(.17)


def test_operating_point_failure(small):
    e = run_eval(build(pattern_opposed, d_down=.04))
    assert e['status'] == 'INCONCLUSIVE_OPERATING_POINT' and 'labels' not in e
    e = run_eval(build(pattern_opposed, d_level=-.04))
    assert e['status'] == 'INCONCLUSIVE_OPERATING_POINT'


def test_integrity_failures(small):
    good = build(pattern_opposed)
    assert run_eval(good, repro_ok=False)['status'] == 'INCONCLUSIVE_INTEGRITY'
    for mutate, key in (
            (lambda a: a['G1_LEVEL_20']['neural'][3].update(uniforms_sha256='zz'), 'I3_common_rng'),
            (lambda a: a['G1_DOWN20_20']['samples'][3].update(qpos=[9]*7), 'I4_prefixes'),
            (lambda a: a['FLIP_LEVEL_21']['samples'][-1].update(gravity=m.tilt_gravity('DOWN20')), 'I5_tilt_record'),
            (lambda a: a['FLIP_DOWN20_21']['samples'][-1].update(gravity=list(m.G0)), 'I5_tilt_record'),
            (lambda a: a['OFF_DOWN20_22']['neural'][2].update(jo_delivered=[100]), 'I6_jo_delivery'),
            (lambda a: a['G1_DOWN20_23']['neural'][-1]['jo_rate_hz'].update(C_left=1.), 'I6_jo_delivery'),
            (lambda a: a['G1_LEVEL_24']['initial'].update(cns_seed=7), 'I7_seeds')):
        arms = copy.deepcopy(good)
        mutate(arms)
        e = run_eval(arms)
        assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and e['checks'][key] is False, key


def test_rollover_precondition(small):
    arms = build(pattern_opposed)
    s = math.sin(math.radians(25))
    for x in arms['OFF_LEVEL_21']['samples'][EVENT + 1:]:
        x['qpos'] = [0, 0, 0, math.cos(math.radians(25)), s, 0, 0]
    assert run_eval(arms)['status'] == 'INCONCLUSIVE_PHYSICS'


def test_prediction_rules():
    lab = {'G1': 'JO_TILT_PATTERN_CONSISTENT', 'FLIP': 'JO_TILT_PATTERN_WEAK'}
    dn = {t: {s: {'DNp73': v, 'DNbe001': v} for s in m.SEEDS} for t, v in (('G1', -3.), ('FLIP', 2.))}
    p = m.predictions(lab, .1, dn)
    assert p == dict(P1='HELD', P2='NOT_HELD', P3='NOT_HELD', P4='HELD')
    dn['FLIP'][22]['DNbe001'] = 0.
    assert m.predictions(lab, -.1, dn)['P4'] == 'NOT_HELD'
    dn['FLIP'][22]['DNbe001'] = -1.
    assert m.predictions(lab, -.1, dn) == dict(P1='HELD', P2='NOT_HELD', P3='HELD', P4='NOT_HELD')
