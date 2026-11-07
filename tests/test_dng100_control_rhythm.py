import math

from malecns_backend.embodiment import dng100_control_rhythm as r5


def test_constants_and_conditions():
    assert r5.DRIVES == {'VNCSIZE': 2000., 'R1SIZE': 16000.} and r5.PRIMARY == 'R1SIZE'
    assert sorted(r5.TARGETS.values()) == [1087, 129181, 130496]
    assert len(r5.SEEDS) == 64 and min(r5.SEEDS) == 2001 and len(r5.CONTROL_SEEDS) == 16
    core = {'E1': 11, 'E2': 12, 'I1': 13}
    c = r5.conditions(core, [3, 4, 5])
    assert [x[0] for x in c] == list(r5.CONDITIONS)
    assert c[0][1](2001) == () and c[1][1](2001) == (11,) and c[3][1](7) == (13,)
    sham = c[4][1](2001)
    assert len(sham) == 1 and sham[0] in (3, 4, 5) and c[4][1](2001) == sham
    total = len(r5.ARMS)*(20*len(r5.CONTROL_SEEDS) + len(r5.TARGETS)*len(r5.CONDITIONS)*len(r5.SEEDS))
    assert total == 2560


def test_draws():
    cands = r5.sham_candidates(10, [0, 2, 4, 6, 8])
    assert cands == [1, 3, 5, 7, 9]
    assert all(r5.sham_cell(s, cands) in cands for s in range(2001, 2065))
    assert r5.sham_cell(2001, cands) == r5.sham_cell(2001, cands)
    pool = list(range(100))
    ctl = r5.new_controls(pool, range(0, 100, 2))
    assert len(ctl) == 20 and all(x % 2 for x in ctl) and ctl == sorted(ctl)
    assert ctl == r5.new_controls(pool, range(0, 100, 2))
    assert r5.new_controls(list(range(10)), [0]) == list(range(1, 10))


def summ(score, freq=13.):
    return dict(score=score, frequency_hz=freq)


def test_verdict_order():
    good = dict(STIM=summ(.9), SIL_E1=summ(.1), SIL_E2=summ(math.nan), SIL_I1=summ(.2), SIL_SHAM=summ(.8))
    assert r5.target_verdict(good, .3)[0] == 'CORE_RHYTHM_CONFIRMED'
    assert r5.target_verdict(dict(good, STIM=summ(.9)), .95)[0] == 'RHYTHM_NOT_CONFIRMED'
    assert r5.target_verdict(dict(good, STIM=summ(.9, 30.)), .3)[0] == 'RHYTHM_OUT_OF_BAND'
    assert r5.target_verdict(dict(good, SIL_SHAM=summ(.1)), .3)[0] == 'SILENCING_NONSPECIFIC'
    v, d = r5.target_verdict(dict(good, SIL_E2=summ(.7)), .3)
    assert v == 'RHYTHM_CORE_INDEPENDENT' and d['core_cells_not_needed'] == ['E2']
    assert r5.target_verdict(dict(good, STIM=summ(math.nan)), .3)[0] == 'INCONCLUSIVE'
    assert r5.p80({'a': summ(.1), 'b': summ(math.nan), 'c': summ(.5)})[1] == [.1, .5]


def test_headline_and_expectations():
    def arms(r1, vnc, p80=.2):
        return {'R1SIZE': dict(control_p80=p80, targets={t: dict(verdict=r1[i]) for i, t in enumerate(r5.TARGETS)}),
                'VNCSIZE': dict(control_p80=.1, targets={t: dict(verdict=vnc) for t in r5.TARGETS})}
    a = arms(['CORE_RHYTHM_CONFIRMED', 'CORE_RHYTHM_CONFIRMED', 'RHYTHM_NOT_CONFIRMED'], 'RHYTHM_NOT_CONFIRMED')
    assert r5.headline_verdict(a) == 'OBSERVATION_CONFIRMED'
    assert r5.expectations('OBSERVATION_CONFIRMED', a) == dict(X1=True, X2=True, X3=True)
    b = arms(['CORE_RHYTHM_CONFIRMED', 'RHYTHM_CORE_INDEPENDENT', 'CORE_RHYTHM_CONFIRMED'], 'RHYTHM_OUT_OF_BAND', .6)
    assert r5.headline_verdict(b) == 'OBSERVATION_NOT_CONFIRMED'
    assert r5.expectations('OBSERVATION_NOT_CONFIRMED', b) == dict(X1=False, X2=False, X3=False)


def test_i2_check():
    runs = lambda d: [dict(seed=s, score=(math.nan if s == 1001 else .9), recruited=150 + d % 7,
                           core={c: dict(active=True) for c in r5.CORE}) for s in r5.I2_SEEDS]
    r3res = {'arms': {a: {'conditions': {f'CONTROL_{d}': {'runs': runs(d)} for d in r5.I2_TARGETS}}
                      for a in r5.DRIVES}}
    mine = {(a, d, s): dict(score=(math.nan if s == 1001 else .9), recruited=150 + d % 7,
                            core_active={c: True for c in r5.CORE})
            for a in r5.DRIVES for d in r5.I2_TARGETS for s in r5.I2_SEEDS}
    assert r5.i2_check(mine, r3res) == dict(passed=True, checked=16, mismatches=[])
    mine[('VNCSIZE', 130496, 1003)]['recruited'] += 1
    out = r5.i2_check(mine, r3res)
    assert not out['passed'] and out['mismatches'][0]['seed'] == 1003
