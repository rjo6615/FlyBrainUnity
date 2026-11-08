import math

import numpy as np

from malecns_backend.embodiment import lif_driver_rhythm as l1
from malecns_backend.embodiment import dng100_control_rhythm as r5


def L(rate, score, freq=13.):
    return dict(rate_hz=rate, score=score, frequency_hz=freq, feasible_seeds=16, runs=[])


def test_split_keeps_core_out_of_the_mn_score():
    spikes = {1: [10, 20], 2: [], 900: [5, 6, 7]}
    mn, other = l1.split(spikes, [1, 2])
    assert mn == {1: [10, 20], 2: []} and other == {900: [5, 6, 7]}


def test_aggregate_matches_v1_rule():
    runs = [dict(score=.2, frequency_hz=10.), dict(score=math.nan, frequency_hz=math.nan),
            dict(score=.6, frequency_hz=math.nan)]
    a = l1.aggregate(50, runs)
    assert a['feasible_seeds'] == 2 and math.isclose(a['score'], .4) and a['frequency_hz'] == 10.
    empty = l1.aggregate(25, [dict(score=math.nan, frequency_hz=math.nan)])
    assert math.isnan(empty['score']) and empty['feasible_seeds'] == 0


def test_target_class_order():
    p80 = .216
    none = [L(r, math.nan, math.nan) for r in l1.RATES]
    assert l1.target_class(none, {}, p80)[0] == 'NO_MN_OUTPUT'
    low = [L(25, math.nan), L(50, .3), L(100, .2), L(200, .1)]
    cls, det = l1.target_class(low, {}, p80)
    assert cls == 'NOT_RHYTHMIC' and det['best_rate_hz'] == 50
    good = [L(25, .4), L(50, .8), L(100, .7), L(200, .6)]
    sil = dict(SIL_E1=L(50, .1), SIL_E2=L(50, math.nan), SIL_SHAM=L(50, .75))
    assert l1.target_class(good, sil, p80)[0] == 'LIF_RHYTHM_CORE'
    cls, det = l1.target_class(good, dict(sil, SIL_SHAM=L(50, .3)), p80)
    assert cls == 'LIF_RHYTHM_OTHER' and det['checks'] == dict(frequency=True, core=True, sham=False)
    fast = [L(25, .4), L(50, .8, freq=30.), L(100, .7), L(200, .6)]
    assert l1.target_class(fast, sil, p80)[1]['checks']['frequency'] is False
    assert l1.target_class([L(50, .5)], sil, .6)[0] == 'NOT_RHYTHMIC'


def test_verdict_and_expectations():
    c = dict(DNg75_R='NOT_RHYTHMIC', DNa02_L='NO_MN_OUTPUT', DNp09_R='LIF_RHYTHM_CORE')
    assert l1.step_verdict(c) == 'NOT_REPRODUCED_IN_LIF'
    assert l1.expectations(c, 'NOT_REPRODUCED_IN_LIF') == dict(X1=True, X2=True, X3=True)
    c.update(DNa02_L='LIF_RHYTHM_OTHER')
    assert l1.step_verdict(c) == 'PARTIAL'
    c.update(DNg75_R='LIF_RHYTHM_CORE', DNa02_L='LIF_RHYTHM_CORE')
    assert l1.step_verdict(c) == 'REPRODUCED_IN_LIF'
    assert l1.expectations(c, 'REPRODUCED_IN_LIF') == dict(X1=False, X2=False, X3=False)


def test_sham_mapping_and_i2():
    net = np.array([500, 600, 700, 800])
    cands = [0, 2, 3]
    for s in l1.SEEDS:
        assert l1.sham_dense(s, cands, net) == int(net[r5.sham_cell(s, cands)])
        assert l1.sham_dense(s, cands, net) in (500, 700, 800)
    runs = [dict(seed=s, score=.19, mn_spikes={'7': 40}) for s in l1.I2_SEEDS]
    v1res = {'dng100': {'levels': [dict(rate_hz=50, runs=[]), dict(rate_hz=100, runs=runs)]}}
    mine = {s: dict(score=.19, mn_spikes={'7': 40}) for s in l1.I2_SEEDS}
    assert l1.i2_check(mine, v1res) == dict(passed=True, checked=4, mismatches=[])
    mine[3]['mn_spikes'] = {'7': 41}
    assert not l1.i2_check(mine, v1res)['passed']
    runs[0]['score'] = None
    mine = {s: dict(score=(math.nan if s == 1 else .19), mn_spikes={'7': 40}) for s in l1.I2_SEEDS}
    assert l1.i2_check(mine, v1res)['passed']
