import math

import numpy as np
from scipy import sparse

from malecns_backend.embodiment import dng100_recruitment_map as rm
from malecns_backend.embodiment.dng100_rate_model import B, rhs

LADDER = [1., 2., 4.]


def test_input_parts_equal_the_model_rhs_input():
    rng = np.random.default_rng(0)
    W = sparse.csr_matrix(rng.integers(-20, 20, (6, 6)).astype(float))
    r = rng.uniform(0, 50, 6)
    theta = rng.uniform(5, 30, 6)
    a, tau, rmax = np.ones(6), np.full(6, 20.), np.full(6, 200.)
    for j in range(6):
        parts = rm.input_parts(W, r, j, theta)
        # rhs at r with zero external drive: (rmax*tanh(a/rmax*x))^+ - r over tau, with x = b W r - theta
        x = B*(W @ r) - theta
        assert math.isclose(parts['margin'], x[j], rel_tol=1e-12, abs_tol=1e-12)
        assert parts['exc'] >= 0 >= parts['inh']
        got = rhs(r, W, np.zeros(6), a, theta, tau, rmax, np.zeros(6, bool))[j]
        assert math.isclose(got, (max(200*math.tanh(parts['margin']/200), 0) - r[j])/20, rel_tol=1e-12, abs_tol=1e-12)


def test_hops_and_intermediates():
    # 0 -> 1 -> 3, 0 -> 2 -> 3 (inhibitory), 0 -> 2 -> 4; W[post, pre]
    W = sparse.lil_matrix((6, 6))
    W[1, 0], W[2, 0], W[3, 1], W[3, 2], W[4, 2] = 5, 7, 9, -6, 8
    W = W.tocsr()
    d = rm.hops(W, 0)
    assert list(d[:5]) == [0, 1, 1, 2, 2] and np.isinf(d[5])
    assert rm.intermediates(W, 0, {'a': 3, 'b': 4}) == {'a': [1, 2], 'b': [2]}


def sim(drive, seed, active, frac=.5, recruited=10):
    return dict(drive=drive, seed=seed, recruited=recruited, dng100_frac_rmax=frac,
                core={c: dict(active=active.get(c, False), margin=-1.) for c in rm.CORE},
                intermediates={'7': 0.}, deepest_layer=2)


def test_cell_and_arm_labels():
    seeds = range(16)
    sims = [sim(d, s, {'E1': d >= 2 and s < 8, 'E2': d >= 4 and s < 8, 'I1': d >= 4 and s < 7},
                recruited=600 if d == 4 else 10) for d in LADDER for s in seeds]
    assert rm.cell_label(sims, 'E1', LADDER) == ('ENGAGED_AT_2', 2.)
    assert rm.cell_label(sims, 'E2', LADDER) == ('ENGAGED_AT_4', 4.)
    assert rm.cell_label(sims, 'I1', LADDER)[1] is None  # 7 of 16 is not a majority
    lab, det = rm.arm_label(sims, LADDER)
    assert lab == 'CORE_PARTIAL' and det['cells']['I1'] == 'NOT_ENGAGED_UNSATURATED'
    sat = [dict(x, dng100_frac_rmax=.95) for x in sims]
    assert rm.cell_label(sat, 'I1', LADDER)[0] == 'NOT_ENGAGED_DNG100_SATURATED'
    all3 = [sim(d, s, {c: d >= 4 for c in rm.CORE}, recruited=600 if d == 4 else 10) for d in LADDER for s in seeds]
    assert rm.arm_label(all3, LADDER)[0] == 'CORE_REACHED_BEYOND_RANGE'
    all3 = [sim(d, s, {c: d >= 4 for c in rm.CORE}, recruited=500) for d in LADDER for s in seeds]
    assert rm.arm_label(all3, LADDER)[0] == 'CORE_REACHED_IN_PREPRINT_RANGE'
    none = [sim(d, s, {}) for d in LADDER for s in seeds]
    assert rm.arm_label(none, LADDER)[0] == 'CORE_NOT_REACHED'
    stop = rm.stopping_point(none, {'E1': ['7'], 'E2': ['7'], 'I1': []}, LADDER)
    assert stop['E1'] == dict(median_margin=-1., active_intermediates=[], silent_intermediates=['7'],
                              median_deepest_layer=2.)


def test_i2_check_and_expectations():
    sims = [dict(seed=1, drive=250., recruited=1), dict(seed=1, drive=500., recruited=3)]
    ok = rm.i2_check(sims, [dict(seed=1, history=[dict(i_stim=250., recruited=1), dict(i_stim=125., recruited=0)]),
                            dict(seed=40, history=[dict(i_stim=250., recruited=9)])])
    assert ok == dict(passed=True, checked=1, mismatches=[])
    bad = rm.i2_check(sims, [dict(seed=1, history=[dict(i_stim=500., recruited=2)])])
    assert not bad['passed'] and bad['mismatches'][0]['r2'] == 3
    lab = lambda e1, e2, i1: {'E1': e1, 'E2': e2, 'I1': i1}
    labels = {'R1SIZE': ('CORE_REACHED_BEYOND_RANGE', dict(cells=lab('ENGAGED_AT_4000', 'ENGAGED_AT_8000',
                                                                     'NOT_ENGAGED_DNG100_SATURATED'))),
              'VNCSIZE': ('CORE_PARTIAL', dict(cells=lab('ENGAGED_AT_2000', 'ENGAGED_AT_8000',
                                                         'NOT_ENGAGED_UNSATURATED')))}
    x = rm.expectations(labels)
    assert x['X1'] and x['X2'] and x['X3'] and x['X3_vacuous_cells'] == ['I1']
    labels['VNCSIZE'][1]['cells']['E2'] = 'NOT_ENGAGED_UNSATURATED'
    assert not rm.expectations(labels)['X3']
