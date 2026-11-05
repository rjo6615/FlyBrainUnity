"""Synthetic checks for the JO zone C/E identity evaluation (no connectome)."""
import numpy as np
import pandas as pd
import pytest
from scipy import sparse

from malecns_backend.embodiment import antennal_gravity_identity as ag

# dense layout: C_L 0-9, C_R 10-19, E_L 20-29, E_R 30-39, unclear_R 40-41,
# targets: 50 (C-only), 51 (E-only), 52 (shared), 60 interneuron -> 70 DN, 80 leg MN
N = 100
INDEX = {1000 + i: i for i in range(42)}


def pops():
    p = {}
    for z, s, lo in (('C', 'left', 0), ('C', 'right', 10), ('E', 'left', 20), ('E', 'right', 30)):
        p[(z, s)] = [1000 + i for i in range(lo, lo + 10)]
    p[('unclear', 'right')] = [1040, 1041]
    return p


def graph(shared=0., dn=True):
    m = sparse.lil_matrix((N, N))
    for i in range(0, 20):
        m[i, 50] = 10
        m[i, 52] = shared
    for i in range(20, 40):
        m[i, 51] = 10
        m[i, 52] = shared
    m[40, 51] = 10
    if dn:
        m[50, 70] = 10
        m[51, 70] = 10
    m[50, 80] = 10
    return m.tocsr()


def ev(p=None, adj=None, index=INDEX):
    return ag.evaluate(p or pops(), index, graph() if adj is None else adj, {70: (7000, 'DNtest')},
                       {'T1 left': {80}})


def test_ready():
    e = ev()
    assert e['verdict'] == 'IDENTITY_READY', e['checks']
    assert e['overlap_C_vs_E'] == {'left': 0., 'right': 0.}
    assert e['populations']['C_left']['descending_reached'][0]['body_id'] == 7000
    assert e['populations']['C_left']['leg_mn_two_hop_neurons']['T1 left'] == 10
    assert e['populations']['E_left']['leg_mn_two_hop_neurons']['T1 left'] == 0
    assert e['descriptive']['unclear_right_overlap_with_E_right'] == pytest.approx(10/100)
    assert e['left_right']['C']['count_left_over_right'] == 1.


def test_overlap_boundary():
    # per side, C weights {50:100, 52:10s}, E {51:100, 52:10s}; overlap = 10s/(200+10s)
    assert ev(adj=graph(shared=19.))['checks']['A3_zone_segregation']   # 190/390 < 0.5
    e = ev(adj=graph(shared=21.))                                         # 210/410 > 0.5
    assert not e['checks']['A3_zone_segregation'] and e['verdict'] == 'IDENTITY_PARTIAL'


def test_no_descending():
    e = ev(adj=graph(dn=False))
    assert not e['checks']['A4_descending_reach'] and e['verdict'] == 'IDENTITY_PARTIAL'


def test_identity_and_bilateral_faults():
    idx = dict(INDEX)
    del idx[1000]
    assert ev(index=idx)['verdict'] == 'NOT_READY'
    p = pops()
    p[('C', 'right')] = p[('C', 'right')][:9]
    assert ev(p)['verdict'] == 'NOT_READY'
    p = pops()
    p[('E', 'left')] = p[('E', 'left')] + [1000]
    assert not ev(p)['checks']['A1_identity']


def test_populations_rule():
    t = pd.DataFrame(dict(bodyId=[1, 2, 3, 4, 5, 6], subclass=['wind_gravity']*5 + ['auditory'],
                          type=['JO-CL', 'JO-EV1', 'JO-unclear', 'JO-B3', 'JO-CM', 'JO-CL'],
                          rootSide=['L', 'R', 'R', 'L', None, 'L']))
    assert ag.populations(t) == {('C', 'left'): [1], ('E', 'right'): [2], ('unclear', 'right'): [3],
                                 ('other', 'left'): [4]}


def test_protocol_lock():
    assert ag.protocol()['checks']['A3_zone_segregation'].endswith('< 0.5 on both sides')
