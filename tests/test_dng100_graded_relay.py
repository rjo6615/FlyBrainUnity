import math

import numpy as np
from scipy import sparse

from malecns_backend.embodiment import dng100_graded_relay as r9
from malecns_backend.embodiment.dng100_rate_model import simulate


def toy():
    W = np.array([[0, 30, 12, 0, 0],
                  [25, 0, 8, -15, 0],
                  [20, 0, 0, 0, 0],
                  [0, 18, 6, 0, 0],
                  [10, 10, 4, -5, 0]], float)
    return sparse.csr_matrix(W)


def test_spare_scales_exactly_declared_entries_and_g1_identical():
    W, k, e1 = toy(), 2, 1
    ref = W.toarray()
    for mode in r9.MODES:
        one = r9.mode_W(W, k, e1, mode, 1.)
        assert np.array_equal(one.data, W.data) and np.array_equal(one.indices, W.indices)
        assert np.array_equal(one.indptr, W.indptr)
    half = r9.mode_W(W, k, e1, 'SPARE_E1', .5).toarray()
    want = ref.copy()
    want[[0, 3, 4], k] *= .5
    assert np.array_equal(half, want)
    whole = r9.mode_W(W, k, e1, 'WHOLE', .3).toarray()
    want = ref.copy()
    want[:, k] *= .3
    assert np.allclose(whole, want)
    zero = r9.mode_W(W, k, e1, 'SPARE_E1', 0.).toarray()
    assert zero[e1, k] == 8 and not zero[[0, 3, 4], k].any() and np.array_equal(zero[:, [0, 1, 3, 4]],
                                                                                   ref[:, [0, 1, 3, 4]])


def test_whole_g0_matches_silencing_relay():
    W, k = toy(), 2
    n = W.shape[0]
    a, theta, tau, rmax = np.ones(n), np.full(n, 7.5), np.full(n, 20.), np.full(n, 200.)
    zero = simulate(r9.mode_W(W, k, 1, 'WHOLE', 0.), a, theta, tau, rmax, 0, 60., (), duration=200.)
    sil = simulate(W, a, theta, tau, rmax, 0, 60., [k], duration=200.)
    keep = [0, 1, 3, 4]
    assert np.allclose(zero[:, keep], sil[:, keep], rtol=1e-4, atol=1e-4)


def S(rec, e1_active=1., score=.02, e1=.1):
    return dict(median_recruited=rec, E1_active_fraction=e1_active, score=score, E1_trace_score_median=e1)


def test_labels_classes_validity_and_verdict():
    assert r9.labels(S(500)) == dict(ignited=True, engaged=True, rhythmic=False)
    assert r9.labels(S(499.5, e1_active=.4, score=.6, e1=.5)) == dict(ignited=False, engaged=False, rhythmic=True)
    assert not r9.labels(S(100, score=.9, e1=math.nan))['rhythmic']
    ign = {g: S(620) for g in r9.LEVELS}
    silent = {**ign, **{0.: S(160, e1_active=1/16), .1: S(170, e1_active=0.)}}
    assert r9.mode_class(silent) == ('NOT_SEPARABLE', [])
    sep = {**silent, **{.2: S(300, e1_active=.7)}}
    assert r9.mode_class(sep) == ('SEPARABLE_NO_RHYTHM', [.2])
    win = {**sep, **{.3: S(250, score=.7, e1=.8), .1: S(240, e1_active=0., score=.8, e1=.9)}}
    assert r9.mode_class(win) == ('RHYTHM_WINDOW', [.1, .3])
    assert r9.valid(dict(WHOLE=silent, SPARE_E1=ign))
    assert not r9.valid(dict(WHOLE=ign, SPARE_E1=ign))
    assert not r9.valid(dict(WHOLE=silent, SPARE_E1={**ign, **{1.: S(400)}}))
    assert r9.step_verdict(dict(WHOLE='NOT_SEPARABLE', SPARE_E1='SEPARABLE_NO_RHYTHM')) == 'SEPARABLE_NO_RHYTHM'
    assert r9.step_verdict(dict(WHOLE='RHYTHM_WINDOW', SPARE_E1='SEPARABLE_NO_RHYTHM')) == 'RHYTHM_WINDOW'
    assert r9.step_verdict(dict(WHOLE='NOT_SEPARABLE', SPARE_E1='NOT_SEPARABLE')) == 'NOT_SEPARABLE'
    assert r9.transition(silent) == dict(highest_not_ignited=.1, not_ignited_levels=[0., .1], contiguous_from_zero=True)
    gap = {**ign, **{0.: S(100), .5: S(100)}}
    assert r9.transition(gap)['contiguous_from_zero'] is False
    assert r9.transition(ign) == dict(highest_not_ignited=None, not_ignited_levels=[], contiguous_from_zero=True)
    assert r9.expectations(dict(WHOLE='NOT_SEPARABLE', SPARE_E1='SEPARABLE_NO_RHYTHM')) == dict(
        X1=True, X2=False, X3=True)


def test_wiring_and_i2_check():
    W = toy()
    core = {'E1': 1, 'E2': 3, 'I1': 4}
    w = r9.wiring(W, 2, 0, 1, core)
    assert w['targets'] == 4 and w['weight_onto_E1'] == 8 and w['total_out'] == 30 and w['all_excitatory']
    assert w['core_targets'] == ['E1', 'E2', 'I1'] and not w['passed']

    def runs(seeds):
        return [dict(seed=s, score=.03, recruited=620, core={c: dict(active=True) for c in r9.CORE}) for s in seeds]
    r7res = {'conditions': {'DNg100_L': {'1.0': {'runs': runs(r9.I2_R7)}}}}
    r8res = {'conditions': {'R1SIZE': {'SIL_3694': {'runs': runs(r9.I2_R8)}}}}
    mine = {(src, s): dict(score=.03, recruited=620, core_active={c: True for c in r9.CORE})
            for src, seeds in (('R7', r9.I2_R7), ('R8', r9.I2_R8)) for s in seeds}
    assert r9.i2_check(mine, r7res, r8res) == dict(passed=True, checked=8, mismatches=[])
    mine[('R8', 5003)]['recruited'] = 161
    assert not r9.i2_check(mine, r7res, r8res)['passed']
