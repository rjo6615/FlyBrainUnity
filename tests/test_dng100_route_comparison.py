import math

import numpy as np
from scipy import sparse

from malecns_backend.embodiment import dng100_route_comparison as r4


def toy():
    # cells: 0 source, 1 E1, 2 E2, 3 I1, 4 mid (exc), 5 mid (inh), 6 MN, 7 other
    W = np.zeros((8, 8))
    W[1, 0] = 6         # direct s -> E1
    W[4, 0] = 10        # s -> mid4
    W[5, 0] = 5         # s -> mid5
    W[6, 0] = 7         # s -> MN
    W[1, 4] = 2         # mid4 -> E1
    W[3, 4] = 3         # mid4 -> I1
    W[2, 5] = -4        # mid5 -| E2
    W[7, 4] = 5         # mid4 -> other
    W[1, 1] = 9         # self-loop on E1 (excluded from two-hop)
    return sparse.csr_matrix(W)


def test_metrics_toy():
    m = r4.metrics(toy(), 0, {'E1': 1, 'E2': 2, 'I1': 3}, [6])
    assert m['direct_E1'] == 6 and m['direct_E2'] == 0 and m['direct_I1'] == 0
    assert m['twohop_E1'] == 20 and m['twohop_E2'] == -20 and m['twohop_I1'] == 30
    assert math.isclose(m['i1_share'], 30/50)
    # exc two-hop into all: E1 20, I1 30, other 50 (MN/E1 direct excluded) -> 50/100
    assert math.isclose(m['core_focus'], .5)
    assert m['out_degree'] == 4 and m['out_weight'] == 28 and m['direct_mn'] == 7
    assert m['core_hops'] == (1 + 2 + 2)/3
    assert set(m) == set(r4.METRICS)


def test_perm_test():
    mask = [False]*17 + [True]*3
    t = r4.perm_test(list(range(20)), mask)
    assert t['assignments'] == 1140 and math.isclose(t['p'], 2/1140)
    second = list(range(20))
    second[16], second[17] = second[17], second[16]   # rank sum 56
    assert math.isclose(r4.perm_test(second, mask)['p'], 4/1140)
    assert math.isclose(r4.perm_test([0.]*20, mask)['p'], 1.)
    assert math.isnan(r4.perm_test([math.nan]*19 + [1.], mask)['p'])
    nan_ctrl = [math.nan] + list(range(1, 20))
    assert r4.perm_test(nan_ctrl, mask)['assignments'] == 969   # C(19, 3)


def test_placement_and_verdict():
    assert r4.placement(6., [5, 6, 7], [1, 1, 2]) == 'not_nonrhythmic_side'
    assert r4.placement(9., [5, 6, 7], [1, 1, 2]) == 'not_nonrhythmic_side'
    assert r4.placement(4., [5, 6, 7], [1, 1, 2]) == 'nonrhythmic_side'
    assert r4.placement(8., [1, 2, 3], [5, 6]) == 'nonrhythmic_side'
    assert r4.placement(math.nan, [1, 2, 3], [5, 6]) == 'not_nonrhythmic_side'
    controls = list(range(20))
    rhythmic = [17, 18, 19]

    def table(dng):
        t = {str(c): {m: float(c) for m in r4.METRICS} for c in controls}
        t['DNG100'] = {m: dng for m in r4.METRICS}
        return t
    v, per, seps = r4.evaluate(table(0.), rhythmic, controls)
    assert v == 'SIGNATURE_DNG100_DIFFERS' and seps == list(r4.METRICS)
    assert r4.evaluate(table(18.), rhythmic, controls)[0] == 'SIGNATURE_DNG100_LIKE_RHYTHMIC'
    flat = {str(c): {m: 1. for m in r4.METRICS} for c in controls}
    flat['DNG100'] = {m: 1. for m in r4.METRICS}
    assert r4.evaluate(flat, rhythmic, controls)[0] == 'NO_SIGNATURE'


def test_group_expectations_and_completeness():
    r3 = {'arms': {'R1SIZE': {'controls': {str(c): {'score': (.97 if c in (1087, 129181) else
                                                              .52 if c == 130496 else .1)}
                                           for c in r4.CONTROLS}}}}
    assert r4.rhythmic_group(r3) == r4.EXPECTED_RHYTHMIC
    r3['arms']['R1SIZE']['controls']['92']['score'] = float('nan')
    assert r4.rhythmic_group(r3) == r4.EXPECTED_RHYTHMIC
    row = lambda deg, i1: {**{m: 1. for m in r4.METRICS}, 'out_degree': deg, 'i1_share': i1}
    t = {'DNG100': row(50, .9), **{str(c): row(10, .2) for c in r4.EXPECTED_RHYTHMIC}}
    assert r4.expectations('NO_SIGNATURE', t, r4.EXPECTED_RHYTHMIC) == dict(X1=True, X2=True, X3=True)
    t['DNG100']['i1_share'] = math.nan
    assert r4.expectations('SIGNATURE_DNG100_DIFFERS', t, r4.EXPECTED_RHYTHMIC)['X3'] is None
    full = {str(i): {**{m: 1. for m in r4.METRICS}, 'core_hops': math.inf, 'i1_share': math.nan} for i in range(21)}
    assert r4.complete(full)['passed']
    full['3']['out_weight'] = math.nan
    assert not r4.complete(full)['passed']
