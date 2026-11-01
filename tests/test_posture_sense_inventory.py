"""Synthetic checks for the posture-sense inventory; no real connectome."""
from types import SimpleNamespace

import numpy as np
import pandas as pd

from malecns_backend.embodiment import posture_sense_inventory as p


def spec():
    return dict(organs={'hair_plate': "subclass == 'hair plate'", 'haltere': "subclass == 'haltere'"},
                assignment=dict(leg_by_entry_nerve={'ProLN': 'T1', 'MesoLN': 'T2', 'MetaLN': 'T3'}))


def test_organ_rows_assign_leg_from_nerve_and_side_from_root_then_soma():
    table = pd.DataFrame(dict(bodyId=[1, 2, 3, 4], subclass=['hair plate']*3 + ['haltere'],
        entryNerve=['ProLN', 'MetaLN', None, 'DMetaN'], rootSide=['L', None, 'R', None],
        somaSide=[None, 'R', None, None], type=['SNpp1', 'SNpp2', None, 'SApp']))
    rows = p.organ_rows(table, spec())
    assert [(r['leg'], r['side']) for r in rows['hair_plate']] == [('T1', 'left'), ('T3', 'right'), (None, 'right')]
    assert rows['haltere'][0]['leg'] is None and rows['haltere'][0]['side'] is None


def test_motor_pools_group_by_leg_and_joint_class():
    bm = dict(muscles=[dict(name='Ti flexor MN T1 left', actuator='tibia_T1_left', idx=[5]),
                       dict(name='Pleural remotor/abductor MN T1 left', actuator='coxa_abduct_T1_left', idx=[6, 7]),
                       dict(name='GNG133 antenna', actuator='antenna_left', idx=[9])])
    pools = p.motor_pools(bm)
    assert pools == {('T1', 'left'): {'tibia': {5}, 'coxa_abduct': {6, 7}}}


def graph():
    # 0 -> 2 (10 synapses), 0 -> 1 (8), 1 -> 3 (7), 4 -> 3 (3: below floor)
    edges = [(0, 1, 8), (0, 2, 10), (1, 3, 7), (4, 3, 3)]
    row_ptr = [0, 2, 3, 3, 3, 4]
    return SimpleNamespace(row_ptr=row_ptr, target_indices=[e[1] for e in edges], synapse_counts=[e[2] for e in edges])


def test_reach_counts_direct_and_two_hop_above_floor():
    adj = p.adjacency(graph(), 6)
    binary = (adj > 0).astype(float).tocsr()
    assert p.reach(adj, binary, {0}, {2}) == dict(direct_neurons=1, two_hop_neurons=0, direct_synapses=10)
    assert p.reach(adj, binary, {0}, {3}) == dict(direct_neurons=0, two_hop_neurons=1, direct_synapses=0)
    assert p.reach(adj, binary, {4}, {3})['direct_neurons'] == 0
    assert p.reach(adj, binary, set(), {3})['two_hop_neurons'] == 0


def test_classification_rules():
    good = dict(matched_fraction=.95, leg_side_assigned_fraction=.95, any_pool_two_hop_neurons=3)
    assert p.classify('hair_plate', good, 'AVAILABLE_NO_ENCODER', .5) == 'READY_FOR_ENCODER_DESIGN'
    assert p.classify('hair_plate', good, 'AVAILABLE_NO_ENCODER', .4) == 'PARTIAL'
    assert p.classify('campaniform_sensilla', good, 'AVAILABLE_NO_TRANSDUCTION_MODEL', 1) == 'PARTIAL'
    assert p.classify('haltere', dict(good, matched_fraction=.5), 'AVAILABLE_NO_ENCODER', 1) == 'BLOCKED'
    assert p.classify('neck', good, 'UNVERIFIED', 1) == 'PARTIAL'


def test_protocol_lock():
    assert set(p.protocol()['organs']) == {'hair_plate', 'campaniform_sensilla', 'chordotonal_organ',
                                           'wind_gravity_JO', 'haltere', 'neck'}
