"""Synthetic checks for coxa hypothesis D1/D2; no CNS, physics or real geometry."""
import types

import pytest

from malecns_backend.embodiment import coxa_hypothesis as h
from malecns_backend.embodiment._windows_m8_live_condition import _resolve_supplemental_channels

NAMED = {'Tergopleural/Pleural promotor': [1, 0, 0], 'Pleural remotor/abductor': [-.7071, .7071, 0],
         'Sternal adductor': [0, -1, 0], 'Sternal anterior rotator': [1, 0, 0],
         'Sternal posterior rotator': [-1, 0, 0]}


def bodymap(legs=('T1 left',)):
    muscles = []
    for k, leg in enumerate(legs):
        seg, side = leg.split()
        o = 10*k
        muscles += [
            dict(name=f'Tergopleural/Pleural promotor MN {seg} {side}', actuator=f'coxa_{seg}_{side}', idx=[o+1, o+2]),
            dict(name=f'Pleural remotor/abductor MN {seg} {side}', actuator=f'coxa_{seg}_{side}', idx=[o+3]),
            dict(name=f'Pleural remotor/abductor MN {seg} {side}', actuator=f'coxa_abduct_{seg}_{side}', idx=[o+3]),
            dict(name=f'Sternal adductor MN {seg} {side}', actuator=f'coxa_abduct_{seg}_{side}', idx=[o+4]),
            dict(name=f'Sternal posterior rotator MN {seg} {side}', actuator=f'coxa_twist_{seg}_{side}', idx=[o+5]),
            dict(name=f'Ti flexor MN {seg} {side}', actuator=f'tibia_{seg}_{side}', idx=[o+9])]
    return dict(muscles=muscles)


ALL = ('T1 left', 'T2 left', 'T3 left', 'T1 right', 'T2 right', 'T3 right')
VEC = {'Coxa': [-1., 0, 0], 'Coxa_roll': [0, 1., 0], 'Coxa_yaw': [0, 0, 1.]}


def world():
    pools = h.coxa_pools(bodymap(ALL))
    ids = {n: [1000 + i for i in sorted(p['dense'])] for leg in h.LEGS for n, p in pools[leg].items()}
    vectors = {leg: dict(VEC) for leg in h.LEGS}
    ranges = {leg: dict(Coxa=1., Coxa_roll=.1, Coxa_yaw=.2) for leg in h.LEGS}
    audited = {n: tuple(v) for n, v in ids.items()}
    return pools, ids, vectors, ranges, audited


def test_pools_parse_and_dedupe():
    p = h.coxa_pools(bodymap())['LF']
    assert sorted(p) == ['Pleural remotor/abductor MN T1 left', 'Sternal adductor MN T1 left',
                         'Sternal posterior rotator MN T1 left', 'Tergopleural/Pleural promotor MN T1 left']
    assert p['Pleural remotor/abductor MN T1 left']['labels'] == {'coxa', 'coxa_abduct'}
    assert p['Pleural remotor/abductor MN T1 left']['dense'] == {3}
    bad = bodymap(); bad['muscles'][0]['name'] = 'Tergopleural/Pleural promotor MN T2 left'
    with pytest.raises(ValueError):
        h.coxa_pools(bad)


def test_action_index_matches_42_order():
    assert h.action_index('LF', 'Coxa') == 0 and h.action_index('LM', 'Coxa_yaw') == 9
    assert h.action_index('RF', 'Coxa_roll') == 22 and h.action_index('RH', 'Coxa_yaw') == 37


def test_assignment_rule_ties_signs_and_restriction():
    pools, _, vectors, _, _ = world()
    a1 = h.assign(pools, vectors, NAMED, restrict=False)['LF']
    assert a1['Tergopleural/Pleural promotor MN T1 left'][('joint')] == 'Coxa'
    assert a1['Tergopleural/Pleural promotor MN T1 left']['sign'] == -1
    assert a1['Pleural remotor/abductor MN T1 left']['joint'] == 'Coxa'  # tie -> lower DoF index
    assert a1['Sternal adductor MN T1 left']['joint'] == 'Coxa_roll' and a1['Sternal adductor MN T1 left']['sign'] == -1
    assert a1['Sternal posterior rotator MN T1 left']['joint'] == 'Coxa' and a1['Sternal posterior rotator MN T1 left']['sign'] == 1
    a2 = h.assign(pools, vectors, NAMED, restrict=True)['LF']
    assert a2['Sternal posterior rotator MN T1 left']['candidates'] == ['Coxa_yaw']
    assert a2['Sternal posterior rotator MN T1 left']['status'] == 'UNASSIGNED'


def test_channels_modes_flip_and_kernel_resolver():
    pools, ids, vectors, _, _ = world()
    defs = h.channels(h.assign(pools, vectors, NAMED, restrict=False), ids)
    lf = defs['joint_LFCoxa']
    assert lf['decoder_mode'] == 'antagonist_pair' and lf['action_index'] == 0
    assert set(lf['negative_populations']) == {'Tergopleural/Pleural promotor MN T1 left'}
    roll = defs['joint_LFCoxa_roll']
    assert roll['decoder_mode'] == 'unidirectional_positive' and roll['coordinate_sign'] == -1
    assert h.flipped(defs)['joint_LFCoxa_roll']['coordinate_sign'] == 1
    data = types.SimpleNamespace(body_id_to_index={b: b - 1000 for v in ids.values() for b in v})
    table = {f'joint_{leg}{j}': dict(action_index=h.action_index(leg, j)) for leg in h.LEGS for j in h.COXA_JOINTS}
    assert set(_resolve_supplemental_channels(defs, data, table, ())) == set(defs)


def test_evaluate_ready_and_failures():
    pools, ids, vectors, ranges, audited = world()
    e = h.evaluate(vectors, ranges, pools, ids, audited, NAMED, 1.)
    assert e['status'] == 'D1_D2_READY' and not e['h2_identical_to_h1']
    assert e['D1c_swing_cross_check']['LF']['match']
    assert h.evaluate(vectors, ranges, pools, ids, audited, NAMED, .5)['status'] == 'INCONCLUSIVE'
    bad = {leg: dict(VEC, Coxa=[1., 0, 0]) for leg in h.LEGS}
    assert h.evaluate(bad, ranges, pools, ids, audited, NAMED, 1.)['status'] == 'NOT_READY'
    wrong = dict(audited); wrong[next(iter(wrong))] = (1,)
    assert h.evaluate(vectors, ranges, pools, ids, wrong, NAMED, 1.)['status'] == 'NOT_READY'

    def refuse(d):
        raise ValueError('x')
    assert h.evaluate(vectors, ranges, pools, ids, audited, NAMED, 1., refuse)['status'] == 'NOT_READY'


def test_swing_split():
    a = {leg: {} for leg in h.LEGS}
    a['LF'] = {'p': dict(pool='Tergopleural/Pleural promotor', joint='Coxa'),
               'r': dict(pool='Sternal posterior rotator', joint='Coxa_roll')}
    out = h.swing_check(a, {leg: dict(Coxa=1., Coxa_roll=0, Coxa_yaw=0) for leg in h.LEGS})
    assert out['LF']['h1_swing_joint'] == 'SPLIT' and not out['LF']['match']
