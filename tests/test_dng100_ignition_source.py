import math

import numpy as np
from scipy import sparse

from malecns_backend.embodiment import dng100_ignition_source as r8


def test_partners():
    W = np.zeros((6, 6))
    W[1, 0], W[3, 0], W[4, 0], W[0, 0] = 5, -7, 9, 3   # self-loop on the source is not a partner
    W[2, 1] = 4
    assert r8.partners(sparse.csr_matrix(W), 0) == [1, 3, 4]
    assert r8.partners(sparse.csr_matrix(W), 1) == [2]
    assert r8.partners(sparse.csr_matrix(W), 5) == []


def S(rec, score=.02, e1=0.):
    return dict(median_recruited=rec, score=score, E1_trace_score_median=e1)


def test_verdict_order_and_unmasked():
    ign, low = S(620), S(150)
    singles = {'SIL_1': S(610), 'SIL_2': S(140, score=.8, e1=.9), 'SIL_3': S(200, score=.6, e1=.2)}
    v, prev = r8.arm_verdict(ign, ign, low, singles)
    assert v == 'SINGLE_IGNITION_SOURCE' and prev == ['SIL_2', 'SIL_3']
    assert r8.unmasked(prev, singles) == ('RHYTHM_UNMASKED', ['SIL_2'])
    assert r8.unmasked(['SIL_3'], singles) == ('NO_RHYTHM_UNMASKED', [])
    assert r8.unmasked([], singles) == ('NOT_APPLICABLE', [])
    allign = {k: S(600) for k in singles}
    assert r8.arm_verdict(ign, ign, low, allign) == ('DISTRIBUTED_IGNITION', [])
    assert r8.arm_verdict(ign, ign, ign, allign) == ('IGNITION_NOT_VIA_PARTNERS', [])
    assert r8.arm_verdict(low, ign, low, allign)[0] == 'INVALID'
    assert r8.arm_verdict(ign, low, low, allign)[0] == 'INVALID'
    assert r8.ignited(S(500)) and not r8.ignited(S(499.5))
    assert r8.unmasked(['SIL_x'], {'SIL_x': S(100, score=.9, e1=math.nan)})[0] == 'NO_RHYTHM_UNMASKED'


def test_expectations():
    arms = {'R1SIZE': dict(verdict='DISTRIBUTED_IGNITION', secondary='NOT_APPLICABLE'),
            'VNCSIZE': dict(verdict='SINGLE_IGNITION_SOURCE', secondary='NO_RHYTHM_UNMASKED')}
    assert r8.expectations(arms) == dict(X1=True, X2=False, X3=True)
    arms['R1SIZE'].update(verdict='SINGLE_IGNITION_SOURCE', secondary='RHYTHM_UNMASKED')
    assert r8.expectations(arms) == dict(X1=False, X2=False, X3=False)


def test_i2_check():
    def runs(seeds):
        return [dict(seed=s, score=.03, recruited=620, core={c: dict(active=True) for c in r8.CORE}) for s in seeds]
    r7res = {'conditions': {'DNg100_L': {'1.0': {'runs': runs(r8.I2['R1SIZE'])}}}}
    r3res = {'arms': {'VNCSIZE': {'conditions': {'DNG100': {'runs': runs(r8.I2['VNCSIZE'])}}}}}
    mine = {(a, s): dict(score=.03, recruited=620, core_active={c: True for c in r8.CORE})
            for a, seeds in r8.I2.items() for s in seeds}
    assert r8.i2_check(mine, r7res, r3res) == dict(passed=True, checked=8, mismatches=[])
    mine[('VNCSIZE', 1002)]['core_active']['I1'] = False
    assert not r8.i2_check(mine, r7res, r3res)['passed']
