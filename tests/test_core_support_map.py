import math
from types import SimpleNamespace

import numpy as np

from malecns_backend.embodiment import core_support_map as f2
from malecns_backend.embodiment import engine_fidelity_audit as f1
from malecns_backend.neural import MaleCNSBrain

NTS = ['unknown', 'acetylcholine', 'gaba', 'glutamate', 'dopamine', 'serotonin', 'octopamine', 'histamine']
SUPER = ['ol_intrinsic', 'cb_intrinsic', 'vnc_sensory', 'vnc_intrinsic', 'descending_neuron', 'ascending_neuron',
         'unknown', 'visual_projection', 'cb_sensory']


def toy():
    sizes = [1, 3, 9, 27, 2, 6, 18, 54, 4, 12, 36, 108, 5, 7]
    sup = [0, 7, 1, 1, 1, 4, 5, 3, 2, 3, 3, 3, 6, 8]
    nt = [1, 1, 2, 1, 1, 1, 1, 3, 1, 1, 2, 1, 1, 1]
    signs = [1, 1, -1, 1, 1, 1, 1, -1, 1, 1, -1, 1, 1, 1]
    types = ['L1', 'v', 'c', 'c', 'c', 'DN', 'AN', 'IN', 's', 'IN', 'IN', 'MN', 'u', 's2']
    edges = {0: [(9, 6), (2, 40)], 1: [(9, 50), (11, 100)], 2: [(9, 35), (10, 30)], 3: [(5, 60)],
             5: [(9, 70), (10, 8)], 6: [(3, 20)], 7: [(11, 7), (9, 9)], 8: [(9, 20), (10, 100)],
             9: [(10, 12), (11, 8), (6, 9), (8, 9)], 10: [(11, 9)], 12: [(9, 10)], 13: [(10, 30)]}
    indptr, indices, counts = [0], [], []
    for i in range(len(sizes)):
        for t, c in edges.get(i, []):
            indices.append(t)
            counts.append(c)
        indptr.append(len(indices))
    return SimpleNamespace(neuron_count=len(sizes), row_ptr=np.array(indptr), target_indices=np.array(indices),
                           synapse_counts=np.array(counts, np.uint16), neuron_sizes=np.array(sizes, np.float32),
                           superclasses=SUPER, superclass_ids=np.array(sup), neurotransmitter_ids=np.array(nt),
                           neurotransmitters=NTS, nt_signs=np.array(signs, np.float32), types=types,
                           classes=['other'], class_ids=np.zeros(len(sizes), int), instances=types,
                           body_ids=np.arange(100, 100 + len(sizes)))


NET = [7, 9, 10, 11]


def test_groups_partition_the_rest():
    assert [f2.group_of(s) for s in SUPER] == ['OPTIC', 'BRAIN', 'SENSORY', 'VNC', 'DN', 'AN', 'OTHER', 'OPTIC',
                                               'SENSORY']
    d = toy()
    grp = f2.group_ids(d, NET)
    sizes = f2.group_sizes(grp)
    assert sizes['NETWORK'] == 4 and sum(sizes.values()) == d.neuron_count
    assert sizes == dict(NETWORK=4, OPTIC=2, BRAIN=3, VNC=0, AN=1, DN=1, SENSORY=2, OTHER=1)


def test_conditions_keep_only_declared_edges_and_audit():
    d = toy()
    E, grp = f1.Edges(d), f2.group_ids(d, NET)
    base = f2.pre_gain_weights(d, MaleCNSBrain(d).config, E)
    live = f2.build(d, 'LIVE', E, grp, base)
    w, s = np.array(live.weights), np.array(live.pre_sign)
    for name in f2.CONDITIONS:
        b = f2.build(d, name, E, grp, base)
        a = f2.lesion_audit(name, b, w, s, E, grp)
        assert a['passed'], (name, a)
    assert np.array_equal(np.asarray(f2.build(d, 'LIVE_VIA_WEIGHTS', E, grp, base).weights), w)
    minus = f2.kept_edges('MINUS_BRAIN', E, grp)
    assert not minus[E.src == 3].any() and minus[E.src == 5].all()                 # 3 is BRAIN, 5 is DN
    only = f2.kept_edges('ONLY_DN', E, grp)
    assert only[(E.src == 5) & (E.tgt == 9)].all() and not only[E.src == 3].any()   # DN -> network kept; BRAIN -> DN not
    b = f2.build(d, 'MINUS_DN', E, grp, base)
    b.weights[np.flatnonzero(f2.kept_edges('MINUS_DN', E, grp) & (w != 0))[0]] += 1
    assert not f2.lesion_audit('MINUS_DN', b, w, s, E, grp)['passed']
    assert np.array_equal(base, f2.pre_gain_weights(d, MaleCNSBrain(d).config, E))   # base never scaled in place


def R(seed, e1, e2, score=.2, sens=0):
    return dict(seed=seed, score=score, mn_spikes={'1': 3}, active_mns=1, active_fraction=.01,
                network_active_fraction=.1, active_neurons=dict(NETWORK=3, SENSORY=sens),
                core=dict(E1=dict(mean_hz=e1, trace_score=math.nan), E2=dict(mean_hz=e2), I1=dict(mean_hz=0.)))


def test_same_runs_normalises_nan():
    a = [R(s, 12., 12., score=math.nan) for s in f2.SEEDS]
    b = [dict(R(s, 12., 12.), score=None, core=dict(E1=dict(mean_hz=12., trace_score=None), E2=dict(mean_hz=12.),
                                                    I1=dict(mean_hz=0.))) for s in f2.SEEDS]
    assert f2.same_runs(a, b)['passed']
    b[2]['mn_spikes'] = {'1': 4}
    assert f2.same_runs(a, b)['mismatches'] == [3]


def E(**on):
    out = {c: False for c in f2.CONDITIONS}
    out.update(LIVE=True, LIVE_VIA_WEIGHTS=True)
    for g in f2.GROUPS:
        out[f'MINUS_{g}'] = True
    out.update(on)
    return out


def test_labels():
    assert f2.label(E(), gates_ok=False)[0] == 'INCONCLUSIVE'
    assert f2.label(E(LIVE=False))[0] == 'INCONCLUSIVE'
    assert f2.label(E())[0] == 'DISTRIBUTED'
    assert f2.label(E(ONLY_AN=True))[0] == 'REDUNDANT'
    lab, det = f2.label(E(MINUS_VNC=False))
    assert lab == 'NEEDED_NOT_SUFFICIENT' and det['needed'] == ['VNC']
    lab, det = f2.label(E(MINUS_VNC=False, ONLY_VNC=True))
    assert lab == 'LOCALISED' and det['localised'] == ['VNC'] and det['nonmonotonic'] == []
    lab, det = f2.label(E(MINUS_VNC=False, ONLY_BRAIN=True))
    assert lab == 'NEEDED_NOT_SUFFICIENT' and det['nonmonotonic'] == [dict(sufficient='BRAIN', needed='VNC')]


def test_expectations_and_sham():
    table = {c: [R(s, 12., 12.) for s in f2.SEEDS] for c in f2.CONDITIONS}
    table['ISOLATED'] = table['ONLY_SENSORY'] = [R(s, 0., 0.) for s in f2.SEEDS]
    sh = f2.sham(table)
    assert sh['minus_equals_live'] and sh['only_equals_isolated'] and sh['sensory_active_in_live'] == 0
    lab, det = f2.label(E(MINUS_VNC=False, ONLY_VNC=True))
    assert f2.expectations(lab, det, sh) == dict(X1=True, X2=True, X3=True)
    table['MINUS_SENSORY'] = [R(s, 12., 12., sens=2) for s in f2.SEEDS]
    assert not f2.sham(table)['minus_equals_live']
