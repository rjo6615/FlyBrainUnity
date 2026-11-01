"""Synthetic checks for the Step A hair-plate identity test; no real connectome."""
from types import SimpleNamespace

import numpy as np
import pandas as pd

from malecns_backend.embodiment import hair_plate_identity as h
from malecns_backend.embodiment.posture_sense_inventory import adjacency


def spec():
    return h.protocol()


def test_sensory_sets_use_declared_nerves_and_sides():
    table = pd.DataFrame(dict(bodyId=[10, 11, 12, 13, 14], type=['SNpp45', 'SNpp45', 'SNpp45', 'SNpp52', 'SNpp45'],
        entryNerve=['VProN', 'ProLN', 'MesoLN', 'MesoLN', 'MetaLN'], rootSide=['L', 'L', None, 'R', None],
        somaSide=[None, None, 'R', None, None]))
    sets, excluded = h.sensory_sets(table, {10: 0, 11: 1, 12: 2, 13: 3, 14: 4})
    assert sets == {('T1', 'left'): {0}, ('T2', 'right'): {2}}
    assert {e['body_id'] for e in excluded} == {11, 14}


def world(swap=False):
    """S(0) -> remotor M(5) direct 20; S -> promotor M(6) direct 8; S -> inhibitory k(2) 10 -> promotor 9;
    S -> excitatory k(3) 7 -> remotor 6."""
    edges = [(0, 5, 20), (0, 6, 8), (0, 2, 10), (0, 3, 7), (2, 6, 9), (3, 5, 6)]
    if swap:
        edges = [(0, 5, 8), (0, 6, 20), (0, 2, 10), (0, 3, 7), (2, 5, 9), (3, 6, 6)]
    edges.sort()
    n = 7
    row_ptr = [0]*(n + 1)
    for pre, _, _ in edges:
        row_ptr[pre + 1] += 1
    data = SimpleNamespace(row_ptr=list(np.cumsum(row_ptr)), target_indices=[e[1] for e in edges],
                           synapse_counts=[e[2] for e in edges])
    signs = np.array([1, 0, -1, 1, 0, 0, 0], float)
    inter = np.array([0, 0, 1, 1, 0, 0, 0], float)
    pools = {'Pleural remotor/abductor MN': {5}, 'Tergopleural/Pleural promotor MN': {6}}
    return adjacency(data, 6), signs, inter, pools


def test_leg_result_matches_published_pattern():
    adj, signs, inter, pools = world()
    r = h.leg_result(adj, signs, inter, {0}, pools, spec())
    assert r['posterior_direct'] == 20 and r['anterior_direct'] == 8
    assert r['top_population'] == 'Pleural remotor/abductor MN'
    assert r['net_two_hop']['anterior'] == -90 and r['net_two_hop']['posterior'] == 42
    assert r['match']


def test_reversed_wiring_fails():
    adj, signs, inter, pools = world(swap=True)
    r = h.leg_result(adj, signs, inter, {0}, pools, spec())
    assert not r['match'] and not r['checks']['i_posterior_exceeds_anterior']


def test_verdict_rules():
    m = lambda ok: dict(match=ok)
    legs = {('T1', 'left'): m(True), ('T1', 'right'): m(True), ('T2', 'left'): m(True),
            ('T2', 'right'): m(True), ('T3', 'left'): m(True), ('T3', 'right'): m(False)}
    assert h.verdict(legs) == 'MATCH_ALL'
    legs[('T2', 'left')] = m(False)
    assert h.verdict(legs) == 'FRONT_ONLY'
    legs[('T1', 'left')] = m(False)
    assert h.verdict(legs) == 'NO_MATCH'
