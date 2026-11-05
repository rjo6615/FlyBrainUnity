"""Synthetic checks for antennal gravity Step C; no FlyGym, CNS or physics run."""
import copy
import itertools
import math

import numpy as np
import pytest

from malecns_backend.live import antennal_gravity_live as m
from malecns_backend.live import coxa_push_response as pr
from malecns_backend.embodiment import antennal_gravity_encoder as ge


def test_arms_order_and_split():
    assert len(m.ARMS) == 37 and m.ARMS[0] == m.REPRO
    assert m.ARMS[1:7] == ('OFF_UP_13', 'OFF_DOWN_13', 'G1_UP_13', 'G1_DOWN_13', 'FLIP_UP_13', 'FLIP_DOWN_13')
    assert m.split('FLIP_DOWN_18') == ('FLIP', 'DOWN', 18)
    with pytest.raises(ValueError):
        m.split('G1_UP_7')


def test_gravity_rotation_sign_and_magnitude():
    down, up = m.rotated_gravity(-10), m.rotated_gravity(10)
    assert down[0] > 0 > up[0] and down[1] == up[1] == 0
    assert np.linalg.norm(down) == pytest.approx(9810)
    assert down[0] == pytest.approx(9810*math.sin(math.radians(10)))
    # nose-down body pitch: body x axis gains a component along gravity
    sample = dict(qpos=[0, 0, 0, 1, 0, 0, 0], gravity=down.tolist())
    tilt, pitch, roll = m.body_angles(sample)
    assert tilt == pytest.approx(10) and pitch == pytest.approx(10) and roll == pytest.approx(0, abs=1e-9)
    tilt, pitch, _ = m.body_angles(dict(qpos=[0, 0, 0, 1, 0, 0, 0], gravity=list(m.G0)))
    assert tilt == pytest.approx(0, abs=1e-6) and pitch == pytest.approx(0, abs=1e-9)


def test_sign_flip_exact_p_and_labels():
    base = np.array([1., -2., 3., .5, -1., 2.])
    aligned = [base + .01*k for k in range(6)]
    rho, p = m.sign_flip(m.corr_matrix(aligned))
    assert rho > .99 and p == pytest.approx(2/64)
    assert m.label(rho, p) == 'JO_TILT_PATTERN_CONSISTENT'
    mixed = copy.deepcopy(aligned)
    mixed[5] = -mixed[5]
    rho2, p2 = m.sign_flip(m.corr_matrix(mixed))
    assert 0 < rho2 < rho and 2/64 < p2 <= .25
    assert m.label(rho2, p2) == 'JO_TILT_PATTERN_WEAK'
    assert m.label(.1, .26) == m.label(-.1, .01) == 'NO_CONSISTENT_JO_TILT_PATTERN'
    assert m.label(.1, 1/32) == 'JO_TILT_PATTERN_CONSISTENT' and m.label(.1, .25) == 'JO_TILT_PATTERN_WEAK'
    assert m.pearson([1, 1, 1], [1, 2, 3]) == 0.  # zero variance contributes 0
    # flipping every seed leaves rho unchanged, hence the 2/64 floor
    mat = m.corr_matrix(aligned)
    assert m.rho_of(mat, [-1.]*6) == pytest.approx(m.rho_of(mat))


def test_pools_parse_and_rates():
    bodymap = dict(muscles=[
        dict(name='Tibia flexor MN T1 left', actuator='tibia_T1_left', idx=[1, 2]),
        dict(name='Other tibia MN T1 left', actuator='tibia_T1_left', idx=[3]),
        dict(name='Pleural remotor/abductor MN T2 right', actuator='coxa_abduct_T2_right', idx=[4]),
        dict(name='Wing thing', actuator='wing', idx=[9])])
    g = m.pools(bodymap)
    assert g == {'T1 left tibia': {1, 2, 3}, 'T2 right coxa_abduct': {4}}
    arm = dict(neural=[dict(time_ms=520., fired=[1]), dict(time_ms=520.5, fired=[1, 4]), dict(time_ms=2000., fired=[3]),
                       dict(time_ms=2000.5, fired=[4])])
    r = m.pool_rates(m.counts(arm, *m.WINDOW_MS), g, *m.WINDOW_MS)
    assert r['T1 left tibia'] == pytest.approx(2/3/1.48) and r['T2 right coxa_abduct'] == pytest.approx(1/1.48)


# ---- synthetic arms for integrity and evaluation -------------------------------------

STEPS, EVENT = 40, 10  # 0.1 ms states; ticks every 5 states


@pytest.fixture
def small(monkeypatch):
    monkeypatch.setattr(m.c, 'STEPS', STEPS)
    monkeypatch.setattr(m.c, 'TICKS', STEPS//5)
    monkeypatch.setattr(m.c, 'EVENT_STATE', EVENT)
    monkeypatch.setattr(m, 'PREFIX_MS', EVENT*.1 - .5)
    monkeypatch.setattr(m, 'SIGN_TICK_AFTER_MS', EVENT*.1)
    monkeypatch.setattr(m, 'WINDOW_MS', (EVENT*.1 + .5, STEPS*.1))
    monkeypatch.setattr(m, 'TONIC_MS', (0., EVENT*.1))


JO = {'C_left': [100], 'C_right': [101], 'E_left': [102], 'E_right': [103]}


def make_arm(name, pattern):
    t, tilt, s = m.split(name)
    g = m.rotated_gravity(m.TILTS[tilt]).tolist()
    samples = []
    for i in range(STEPS + 1):
        after = i > EVENT
        q = [0, 0, 0, 1, 0, 0, 0] if not after else [0, 0, 0, 1, 0, 0, .001*m.TILTS[tilt]]
        samples.append(dict(time_s=i*1e-4, qpos=q, commanded_joints=[0.]*42, gravity=g if after else list(m.G0),
                            applied_body_wrenches=[], external_applied_max=0., generalized_applied_max=0))
    neural = []
    for k in range(1, STEPS//5 + 1):
        tm = k*.5
        d = -.14 + (.17 if tilt == 'DOWN' else -.17)*(tm > EVENT*.1)
        rates = {f'{z}_{sn}': hz for sd, sn in (('L', 'left'), ('R', 'right'))
                 for z, hz in ge.zone_rates(d, m.ASSIGN[t]).items()}
        fired = list(pattern(t, tilt, s, tm))
        neural.append(dict(time_ms=tm, uniforms_sha256=f'u{s}-{k}', fired=fired, jo_d={'L': d, 'R': d},
                           jo_rate_hz=rates, jo_delivered=[] if t == 'OFF' else [100 + k % 4], hair_delivered=[]))
    return dict(arm=name, run_status='COMPLETE', cns_seed=s, samples=samples, neural=neural,
                initial=dict(external_schedule=[1, 2, 100], cns_seed=s, jo_neurons=JO, jo_deliver=t != 'OFF',
                             jo_assignment=m.ASSIGN[t], force_body=dict(id=1, frame='world', point='body COM',
                                                                         torque=[0., 0., 0.])),
                event=dict(operation='OBSERVE_ONLY', after_sha256='x', original_sha256='x', state_index=EVENT),
                tilt_event=dict(state_index=EVENT, gravity=g))


GROUPS = {f'T{k} left x': {k} for k in range(1, 7)}


def pattern_consistent(t, tilt, s, tm):
    """After the tilt, G1 DOWN fires pool 1 extra and FLIP DOWN pool 2 extra, in every seed."""
    out = [5] if tm > EVENT*.1 else []
    if tm > EVENT*.1 + .5 and tilt == 'DOWN':
        out += {'OFF': [], 'G1': [1, 3], 'FLIP': [2]}[t]
    if tm > EVENT*.1 + .5 and tilt == 'UP' and t != 'OFF' and s % 2:
        out += [4]
    return out


def build(pattern):
    arms = {n: make_arm(n, pattern) for n in m.ARMS[1:]}
    repro = dict(run_status='COMPLETE', samples=[dict(qpos=[0], commanded_joints=[0])]*(STEPS + 1),
                 neural=[dict(fired=[], uniforms_sha256='r', hair_delivered=[])]*(STEPS//5))
    arms[m.REPRO] = repro
    return arms


def run_eval(arms, repro_ok=True):
    return m.evaluate(lambda k: copy.deepcopy(arms[k]), arms[m.REPRO], repro_ok, GROUPS, {'DNp73': {6}})


def test_evaluate_accepts_and_labels_consistent_pattern(small):
    e = run_eval(build(pattern_consistent))
    assert e['status'] == 'INTEGRITY_ACCEPTED', e.get('checks')
    assert e['labels'] == {'G1': 'JO_TILT_PATTERN_CONSISTENT', 'FLIP': 'JO_TILT_PATTERN_CONSISTENT'}
    assert e['included_pools'] == sorted(['T1 left x', 'T2 left x', 'T3 left x', 'T4 left x', 'T5 left x'])
    assert np.isfinite(e['r_GF'])


def test_integrity_failures(small):
    good = build(pattern_consistent)
    assert run_eval(good, repro_ok=False)['status'] == 'INCONCLUSIVE_INTEGRITY'
    for mutate, key in (
            (lambda a: a['G1_UP_14']['neural'][3].update(uniforms_sha256='zz'), 'I3_common_rng'),
            (lambda a: a['G1_UP_14']['samples'][3].update(qpos=[9]*7), 'I4_prefixes'),
            (lambda a: a['FLIP_DOWN_15']['samples'][-1].update(gravity=list(m.G0)), 'I5_tilt_record'),
            (lambda a: a['OFF_DOWN_16']['neural'][2].update(jo_delivered=[100]), 'I6_jo_delivery'),
            (lambda a: a['G1_DOWN_17']['neural'][-1]['jo_rate_hz'].update(C_left=1.), 'I6_jo_delivery'),
            (lambda a: a['G1_UP_18']['initial'].update(cns_seed=7), 'I7_seeds')):
        arms = copy.deepcopy(good)
        mutate(arms)
        e = run_eval(arms)
        assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and e['checks'][key] is False, key
    arms = copy.deepcopy(good)
    arms['OFF_UP_13']['neural'][0]['uniforms_sha256'] = arms['OFF_UP_14']['neural'][0]['uniforms_sha256']
    for n in m.block(13):
        arms[n]['neural'][0]['uniforms_sha256'] = arms['OFF_UP_14']['neural'][0]['uniforms_sha256']
    assert run_eval(arms)['checks']['I7_seeds'] is False


def test_sign_sanity_and_rollover(small):
    arms = build(pattern_consistent)
    for x in arms['G1_DOWN_13']['neural']:
        if x['time_ms'] > EVENT*.1:
            x['jo_d'] = {'L': -.5, 'R': -.5}
            x['jo_rate_hz'] = {f'{z}_{sn}': hz for sn in ('left', 'right') for z, hz in ge.zone_rates(-.5, 'G1').items()}
    assert run_eval(arms)['checks']['I6_jo_delivery'] is False
    arms = build(pattern_consistent)
    s = math.sin(math.radians(25))
    for x in arms['OFF_UP_15']['samples'][EVENT + 1:]:
        x['qpos'] = [0, 0, 0, math.cos(math.radians(25)), s, 0, 0]  # 50 deg roll: beyond the 45 deg bar
    e = run_eval(arms)
    assert e['status'] == 'INCONCLUSIVE_PHYSICS'


def test_no_jo_effect_gives_no_consistent_label(small):
    rng = np.random.default_rng(0)
    noise = {(t, tilt, s): rng.permutation([1, 2, 3, 4])[:int(rng.integers(1, 4))]
             for t in m.TYPES for tilt in m.TILTS for s in m.SEEDS}

    def pattern(t, tilt, s, tm):
        return list(noise[(t, tilt, s)]) if tm > EVENT*.1 + .5 and tm < EVENT*.1 + 1.6 else []
    e = run_eval(build(pattern))
    assert e['status'] == 'INTEGRITY_ACCEPTED'
    for t in ('G1', 'FLIP'):
        st = e['statistics'][t]
        assert e['labels'][t] == m.label(st['rho'], st['p'])
        assert st['p'] >= 2/64


def test_rotated_gravity_is_what_capture_would_write():
    gravity = np.array(m.G0)
    g = m.rotated_gravity(-10)
    gravity[:] = g
    assert [float(x) for x in gravity] == g.tolist()
