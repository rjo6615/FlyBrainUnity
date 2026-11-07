import math

import numpy as np
from scipy import sparse

from malecns_backend.embodiment import dng100_balance_test as r7
from malecns_backend.embodiment.dng100_rate_model import simulate


def toy():
    W = np.array([[0, 30, -20, 0, 0],
                  [25, 0, 0, -15, 0],
                  [20, 0, 0, 0, 0],
                  [0, 18, 0, 0, 0],
                  [10, 10, -5, -5, 0]], float)
    return sparse.csr_matrix(W)


def test_scaling_only_touches_s_columns_and_g1_is_identical():
    W = toy()
    s = [2, 3]
    one = r7.scaled(W, s, 1.)
    assert np.array_equal(one.data, W.data) and np.array_equal(one.indices, W.indices)
    half = r7.scaled(W, s, .5).toarray()
    ref = W.toarray()
    assert np.allclose(half[:, [0, 1, 4]], ref[:, [0, 1, 4]]) and np.allclose(half[:, s], .5*ref[:, s])
    assert np.allclose(r7.scaled(W, s, 3.).toarray()[:, s], 3*ref[:, s])


def test_g0_matches_silencing_s_for_other_cells():
    W = toy()
    s = [2, 3]
    n = W.shape[0]
    a, theta, tau, rmax = np.ones(n), np.full(n, 7.5), np.full(n, 20.), np.full(n, 200.)
    zero = simulate(r7.scaled(W, s, 0.), a, theta, tau, rmax, 0, 60., (), duration=200.)
    sil = simulate(W, a, theta, tau, rmax, 0, 60., s, duration=200.)
    keep = [0, 1, 4]
    # equal up to ODE solver tolerance (adaptive steps also see S's own rates), not bitwise
    assert np.allclose(zero[:, keep], sil[:, keep], rtol=1e-4, atol=1e-4)


def S(score, rec=150., e1=1.):
    return dict(score=score, median_recruited=rec, E1_trace_score_median=e1)


def test_removal_and_boost():
    lost = {g: S(.9) for g in r7.LEVELS}
    lost[.5] = S(.05, rec=690., e1=0.)
    lost[.25] = S(.01, rec=700., e1=0.)
    assert r7.removal_class(lost) == ('LOST_BY_IGNITION', .5)
    other = {g: S(.9) for g in r7.LEVELS}
    other[0.] = S(.1, rec=200., e1=.9)
    assert r7.removal_class(other) == ('LOST_OTHER', 0.)
    assert r7.removal_class({g: S(.9) for g in r7.LEVELS}) == ('NOT_LOST', None)
    nanloss = {g: S(.9) for g in r7.LEVELS}
    nanloss[.75] = S(math.nan, rec=650., e1=math.nan)
    assert r7.removal_class(nanloss) == ('LOST_BY_IGNITION', .75)
    dng = {g: S(.02, rec=620.) for g in r7.LEVELS}
    assert r7.boost_holds(dng) == (False, [])
    dng[2.] = S(.6, rec=200.)
    dng[3.] = S(.7, rec=600.)          # ignited: does not count
    assert r7.boost_holds(dng) == (True, [2.])


def test_verdict_and_expectations():
    lost = {g: S(.9) for g in r7.LEVELS}
    lost[.25] = S(.05, rec=690., e1=0.)
    keep = {g: S(.9) for g in r7.LEVELS}
    flat = {g: S(.02, rec=620.) for g in r7.LEVELS}
    boost = dict(flat)
    boost[1.5] = S(.6, rec=150.)
    v, d = r7.verdict({'DNg75_R': lost, 'DNa02_L': lost}, boost)
    assert v == 'BALANCE_SUPPORTED' and r7.expectations(v, d) == dict(X1=True, X2=True, X3=False)
    assert r7.verdict({'DNg75_R': lost, 'DNa02_L': lost}, flat)[0] == 'REMOVAL_ONLY'
    v, d = r7.verdict({'DNg75_R': lost, 'DNa02_L': keep}, boost)
    assert v == 'BOOST_ONLY' and r7.expectations(v, d) == dict(X1=True, X2=False, X3=False)
    assert r7.verdict({'DNg75_R': keep, 'DNa02_L': keep}, flat)[0] == 'NOT_SUPPORTED'
    bad = dict(keep)
    bad[1.] = S(.3)
    assert r7.verdict({'DNg75_R': bad, 'DNa02_L': keep}, flat) == ('INVALID', {})


def test_i2_check():
    runs = [dict(seed=s, score=.95, recruited=185, core={c: dict(active=True) for c in r7.CORE}) for s in r7.I2_SEEDS]
    r6res = {'conditions': {t: {'STIM': {'runs': runs}} for t in r7.DRIVERS}}
    mine = {(t, s): dict(score=.95, recruited=185, core_active={c: True for c in r7.CORE})
            for t in r7.DRIVERS for s in r7.I2_SEEDS}
    assert r7.i2_check(mine, r6res) == dict(passed=True, checked=8, mismatches=[])
    mine[('DNg75_R', 3004)]['recruited'] = 186
    assert not r7.i2_check(mine, r6res)['passed']
