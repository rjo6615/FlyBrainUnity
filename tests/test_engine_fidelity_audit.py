from types import SimpleNamespace

import numpy as np

from malecns_backend.embodiment import engine_fidelity_audit as f1
from malecns_backend.neural import MaleCNSBrain, ModelConfig, region_scales

NTS = ['unknown', 'acetylcholine', 'gaba', 'glutamate', 'dopamine', 'serotonin', 'octopamine', 'histamine']


def toy():
    sizes = [1, 3, 9, 27, 2, 6, 18, 54, 4, 12, 36, 108, 0]
    sup = [0]*4 + [1]*4 + [3]*5
    sup[8] = 2                                                     # a sensory cell
    nt = [1, 1, 2, 1, 1, 6, 1, 3, 1, 1, 2, 1, 0]
    signs = [1, 1, -1, 1, 1, 1, 1, -1, 1, 1, -1, 1, .4]
    types = ['L1', 'v', 'v', 'v', 'KC', 'OA-VUMa1', 'c', 'c', 's', 'IN', 'IN', 'MN', 'x']
    edges = {0: [(9, 6), (10, 40)], 1: [(9, 5), (11, 100)], 2: [(9, 35), (10, 30)], 5: [(10, 60)],
             7: [(11, 7), (9, 5)], 8: [(9, 20), (10, 100), (11, 80)], 9: [(10, 12), (11, 8), (8, 9)], 10: [(11, 9)]}
    indptr, indices, counts = [0], [], []
    for i in range(len(sizes)):
        for t, c in edges.get(i, []):
            indices.append(t)
            counts.append(c)
        indptr.append(len(indices))
    return SimpleNamespace(neuron_count=len(sizes), row_ptr=np.array(indptr), target_indices=np.array(indices),
                           synapse_counts=np.array(counts, np.uint16), neuron_sizes=np.array(sizes, np.float32),
                           superclasses=['ol_intrinsic', 'cb_intrinsic', 'vnc_sensory', 'vnc_intrinsic'],
                           superclass_ids=np.array(sup), neurotransmitter_ids=np.array(nt), neurotransmitters=NTS,
                           nt_signs=np.array(signs, np.float32), types=types, classes=['other', 'Kenyon_Cell'],
                           class_ids=np.array([0]*4 + [1] + [0]*8), instances=types,
                           body_ids=np.arange(100, 113))


NET = [1, 2, 7, 9, 10, 11]


def test_independent_factor_matches_engine():
    d, p = toy(), ModelConfig.calibrated()
    mine, region, med = f1.independent_factor(d, p)
    scale, r, m = region_scales(d, p)
    assert np.array_equal(mine, scale) and np.array_equal(region, r) and np.array_equal(med, m)


def test_a3_detects_a_wrong_weight():
    d, p = toy(), ModelConfig.calibrated()
    E, b = f1.Edges(d), MaleCNSBrain(d, p)
    assert f1.a3_weights(d, b, p, E, [9, 10, 11])['passed']
    b.weights[np.flatnonzero(b.weights)[0]] *= 1.5
    out = f1.a3_weights(d, b, p, E, [9, 10, 11])
    assert not out['passed'] and out['mismatches'] == 1


def test_a4_rule():
    d, p = toy(), ModelConfig.calibrated()
    sign = np.array(MaleCNSBrain(d, p).pre_sign)
    out = f1.a4_signs(d, sign, [1, 2, 5, 7, 10, 12])
    assert out['passed'] and out['counts'] == dict(oa_type=1, negative=3, positive=1, unknown=1, other=0)
    sign[2] = .3
    bad = f1.a4_signs(d, sign, [1, 2])
    assert not bad['passed'] and bad['first_mismatches'][0]['dense'] == 2


def test_a5_a7():
    d, p = toy(), ModelConfig.calibrated()
    E, b = f1.Edges(d), MaleCNSBrain(d, p)
    assert f1.a5_sizes(d, p, NET)['passed']
    out = f1.a7_mask(d, b, p, E, NET)
    assert out['passed'] and out['removed_whole_graph'] == 1 and out['removed_in_network'] == 0
    k = np.flatnonzero(b.weights)[0]
    b.weights[k] = 0
    assert not f1.a7_mask(d, b, p, E, NET)['passed']


def test_swaps_change_only_the_declared_rule():
    d = toy()
    E, live = f1.Edges(d), MaleCNSBrain(d)
    w, s = np.array(live.weights), np.array(live.pre_sign)
    for name in f1.FIELDS:
        b = f1.build(d, name, E, NET)
        a = f1.swap_audit(name, b, w, s, d, E, NET)
        assert a['passed'], (name, a)
    assert f1.swap_audit('S0_LIVE', f1.build(d, 'S0_LIVE', E, NET), w, s, d, E, NET)['changed_weights'] == 0
    b = f1.build(d, 'S2_MINSYN5', E, NET)
    assert f1.swap_audit('S2_MINSYN5', b, w, s, d, E, NET)['changed_weights'] > 0
    b.weights[0] += 1
    assert not f1.swap_audit('S2_MINSYN5', b, w, s, d, E, NET)['passed']
    b = f1.build(d, 'S3_INHGAIN1', E, NET)
    assert not f1.swap_audit('S2_MINSYN5', b, w, s, d, E, NET)['passed']


def R(seed, e1, e2):
    return dict(seed=seed, core=dict(E1=dict(mean_hz=e1), E2=dict(mean_hz=e2), I1=dict(mean_hz=0.)))


def test_engagement_needs_both_cells_in_the_same_seeds():
    on = [R(s, 12., 11.) for s in range(5)] + [R(s, 0., 0.) for s in range(5, 8)]
    assert f1.cell_engaged(on) == (True, 5)
    assert f1.cell_engaged([R(s, 12., 9.) for s in range(8)]) == (False, 0)
    assert f1.cell_engaged(on[1:] + [R(9, 0., 0.)])[0] is False


def E(live=False, **kw):
    out = {c: dict(a=False, b=False) for c in f1.FIELDS}
    out['S0_LIVE'] = dict(a=live, b=False)
    for c, dn in kw.items():
        out[c][dn] = True
    return out


def test_part_b_labels():
    assert f1.part_b_label(E(), gate_ok=False)[0] == 'INCONCLUSIVE'
    assert f1.part_b_label(E(), audits_ok=False)[0] == 'INCONCLUSIVE'
    assert f1.part_b_label(E())[0] == 'NOT_THESE_RULES'
    assert f1.part_b_label(E(S5_ALL='a'))[0] == 'COMBINATION_ONLY'
    label, det = f1.part_b_label(E(S1_ISOLATED='b', S5_ALL='a'))
    assert label == 'SINGLE_RULE_ENGAGES' and det['engaging_single_rules'] == ['S1_ISOLATED']
    label, det = f1.part_b_label(E(live=True, S1_ISOLATED='a'))        # 'a' already on in LIVE: does not count
    assert label == 'NOT_THESE_RULES' and det['already_engaged_in_live'] == ['a']
    all_on = {c: dict(a=True) for c in f1.FIELDS}
    assert f1.part_b_label(all_on)[0] == 'INCONCLUSIVE'


def test_gate_s0():
    l1res = dict(targets={t: dict(levels=[dict(rate_hz=r, runs=[dict(seed=s, score=None, mn_spikes={'1': r})
                                                               for s in f1.SEEDS]) for r in f1.RATES])
                          for t in f1.GATED_DNS})
    table = {t: {str(r): [dict(seed=s, score=float('nan'), mn_spikes={'1': r}) for s in f1.SEEDS] for r in f1.RATES}
             for t in f1.GATED_DNS}
    assert f1.gate_s0(table, l1res)['passed']
    table['DNa02_L']['200'][3]['mn_spikes'] = {'1': 7}
    out = f1.gate_s0(table, l1res)
    assert not out['passed'] and out['mismatches'] == [dict(dn='DNa02_L', rate=200, seed=4)]


def test_part_c_shape_and_terms():
    d = toy()
    E, b = f1.Edges(d), MaleCNSBrain(d)
    out = f1.part_c(d, b, E, NET + [8], dict(D=8), dict(C=11, X=10))
    cell = out['C']
    assert cell['dns']['D']['direct_lif_psp_mv'] > 0 and cell['dns']['D']['direct_rate_term'] > 0
    top = cell['dns']['D']['top_2hop_lif'][0]                                     # 8 -> 10 (100 syn) -> 11, inhibitory
    assert top['body_id'] == 110 and top['score'] < 0
    assert cell['floor_edges']['dropped_by_6_kept_by_5'] == 0 and out['X']['input_load_mv']['exc_outside'] > 0


def test_a1():
    p = ModelConfig.calibrated()
    params = {k: getattr(p, v) for k, v in f1.PARAM_KEYS.items()}
    assert f1.a1_config(params, p, p)['passed']
    assert not f1.a1_config(dict(params, wSyn=.6), p, p)['passed']
