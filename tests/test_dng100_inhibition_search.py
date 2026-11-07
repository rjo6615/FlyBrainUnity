import math

import numpy as np
from scipy import sparse

from malecns_backend.embodiment import dng100_inhibition_search as r6


def toy(direct_loops=True):
    # 0 E1, 1 E2, 2 I1, 3 k_strong, 4 k_weak, 5 excluded (DN), 6 relay x, 7 k_t2, 8 excitatory, 9 inhib not touching E
    n = 10
    W = np.zeros((n, n))
    if direct_loops:
        W[3, 0], W[0, 3] = 20, -15      # E1 -> k3, k3 -| E1 : strength 15
        W[4, 1], W[1, 4] = 6, -30       # E2 -> k4, k4 -| E2 : strength 6
    W[5, 0], W[0, 5] = 10, -10          # excluded loop
    W[2, 0], W[0, 2] = 10, -10          # I1 loop (excluded)
    W[6, 0] = 8                          # E1 -> x6
    W[7, 6], W[1, 7] = 5, -9             # x6 -> k7, k7 -| E2 (one-relay loop)
    W[8, 0], W[0, 8] = 10, 10            # excitatory partner: not a candidate
    W[9, 6] = 4                          # inhibitory cell not inhibiting E
    sign = np.array([1, 1, -1, -1, -1, -1, 1, -1, 1, -1], float)
    return sparse.csr_matrix(W), sign


def test_candidates_tiers_exclusions_cap():
    W, sign = toy()
    key = np.arange(10)
    out, counts = r6.candidates(W, sign, [0, 1], 2, {5}, key, t2_threshold=2)
    assert [c['local'] for c in out] == [3, 4] and [c['strength'] for c in out] == [15., 6.]
    assert counts == dict(t1=2, t2=0, t2_used=False)
    out, counts = r6.candidates(W, sign, [0, 1], 2, {5}, key)       # T1 (2) < 5 -> T2 used
    assert [(c['local'], c['tier']) for c in out] == [(3, 'T1'), (4, 'T1'), (7, 'T2')]
    assert counts['t2_used'] and counts['t2'] == 1
    out, _ = r6.candidates(W, sign, [0, 1], 2, {5}, key, cap=1)
    assert [c['local'] for c in out] == [3]
    W2, _ = toy(direct_loops=False)
    out, counts = r6.candidates(W2, sign, [0, 1], 2, {5}, key)
    assert [c['local'] for c in out] == [7] and counts['t1'] == 0


def S(score, e1_act=1., e1_tr=.1):
    return dict(score=score, E1_active_fraction=e1_act, E1_trace_score_median=e1_tr)


def test_classify_and_valid():
    assert r6.classify(S(.8)) == 'NOT_NEEDED'
    assert r6.classify(S(.1)) == 'NEEDED_OSCILLATION'
    assert r6.classify(S(math.nan, e1_act=.2, e1_tr=math.nan)) == 'NEEDED_CORE_OFF'
    assert r6.classify(S(.2, e1_tr=.9)) == 'NEEDED_OTHER'
    assert r6.valid(S(.9), S(.6)) and not r6.valid(S(.9), S(.4))


def test_verdict_order():
    def pt(valid=True, classes=None, group='NOT_NEEDED'):
        return dict(valid=valid, classes=classes or {'SIL_1': 'NOT_NEEDED', 'SIL_2': 'NOT_NEEDED'}, group=group)
    osc = {'SIL_1': 'NEEDED_OSCILLATION', 'SIL_2': 'NOT_NEEDED'}
    assert r6.verdict({'a': pt(classes=osc), 'b': pt(classes=osc)}) == ('SHARED_INHIBITORY_PARTNER', ['SIL_1'])
    assert r6.verdict({'a': pt(classes=osc), 'b': pt()})[0] == 'TARGET_SPECIFIC_PARTNER'
    assert r6.verdict({'a': pt(classes=osc), 'b': pt(valid=False, classes=osc)})[0] == 'TARGET_SPECIFIC_PARTNER'
    assert r6.verdict({'a': pt(group='NEEDED_OSCILLATION'), 'b': pt()})[0] == 'REDUNDANT_INHIBITION'
    assert r6.verdict({'a': pt(group='NEEDED_CORE_OFF'), 'b': pt()})[0] == 'GROUP_SILENCES_CORE'
    assert r6.verdict({'a': pt(), 'b': pt()})[0] == 'NO_PARTNER_IN_SET'
    assert r6.verdict({'a': pt(valid=False), 'b': pt(valid=False)})[0] == 'INCONCLUSIVE'
    per = {'a': pt(group='NEEDED_OSCILLATION'), 'b': pt(group='NEEDED_OSCILLATION')}
    assert r6.expectations(dict(t1=7), 'SHARED_INHIBITORY_PARTNER', per) == dict(X1=True, X2=True, X3=True)
    assert r6.expectations(dict(t1=2), 'NO_PARTNER_IN_SET', {'a': pt(), 'b': per['b']}) == \
        dict(X1=False, X2=False, X3=False)


def test_i2_check():
    runs = [dict(seed=s, score=.9, recruited=180, core={c: dict(active=True) for c in r6.CORE}) for s in r6.I2_SEEDS]
    r5res = {'arms': {'R1SIZE': {'targets': {t: {'conditions': {'STIM': {'runs': runs}}} for t in r6.TARGETS}}}}
    mine = {(t, s): dict(score=.9, recruited=180, core_active={c: True for c in r6.CORE})
            for t in r6.TARGETS for s in r6.I2_SEEDS}
    assert r6.i2_check(mine, r5res) == dict(passed=True, checked=8, mismatches=[])
    mine[('DNa02_L', 2002)]['score'] = .91
    assert not r6.i2_check(mine, r5res)['passed']
