import math

from malecns_backend.embodiment import dng100_engaged_rhythm as r3


def test_conditions_builder():
    core = {'E1': 11, 'E2': 12, 'I1': 13}
    c = r3.conditions(5, core, [7, 8])
    assert [x[0] for x in c] == ['DNG100', 'SIL_E1', 'SIL_E2', 'SIL_I1', 'CONTROL_7', 'CONTROL_8']
    assert c[0] == ('DNG100', 5, (), r3.SEEDS) and c[2] == ('SIL_E2', 5, (12,), r3.SEEDS)
    assert c[4] == ('CONTROL_7', 7, (), r3.CONTROL_SEEDS)
    assert len(r3.SEEDS) == 64 and min(r3.SEEDS) == 1001 and len(r3.CONTROL_SEEDS) == 16
    full = r3.conditions(5, core, r3.CONTROLS)
    assert sum(len(x[3]) for x in full)*len(r3.ARMS) == 1152
    assert r3.DRIVES == {'VNCSIZE': 2000., 'R1SIZE': 16000.} and r3.PRIMARY == 'VNCSIZE'


def run(score, engaged=True, e1=(True, .2)):
    core = {c: dict(active=engaged, trace_score=.1) for c in r3.CORE}
    core['E1'] = dict(active=e1[0], trace_score=e1[1])
    return dict(status='FEASIBLE', score=score, frequency_hz=10., recruited=600, engaged=engaged, core=core)


def test_condition_summary_and_verdict_with_qualifier():
    dng = r3.condition_summary([run(.8), run(.6), run(.7, engaged=False), run(.9, engaged=False, e1=(False, 0))])
    assert math.isclose(dng['score'], .75) and dng['engaged_fraction'] == .5 and dng['E1_trace_score_median'] == .2
    ctl = {str(i): r3.condition_summary([run(.1)]) for i in range(5)}
    sil = {c: r3.condition_summary([run(.2)]) for c in r3.CORE}
    v, d = r3.arm_verdict(dng, ctl, sil)
    assert v == 'RATE_RHYTHM_REPRODUCED' and d['qualifier'] is None
    low = r3.condition_summary([run(.8, engaged=False), run(.8, engaged=False), run(.8)])
    assert r3.arm_verdict(low, ctl, sil)[1]['qualifier'] == 'CORE_NOT_RELIABLY_ENGAGED'
    flat = r3.condition_summary([run(.02)])
    assert r3.arm_verdict(flat, ctl, sil)[0] == 'RATE_RHYTHM_NOT_REPRODUCED'


def test_expectations():
    arms = {'VNCSIZE': dict(verdict='RATE_RHYTHM_NOT_REPRODUCED', dng100=dict(score=.05, E1_trace_score_median=.1)),
            'R1SIZE': dict(verdict='RATE_RHYTHM_NOT_REPRODUCED', dng100=dict(score=.2, E1_trace_score_median=.9))}
    assert r3.expectations(arms) == dict(X1=True, X2=True, X3=True)
    arms['VNCSIZE']['dng100'].update(score=.15, E1_trace_score_median=math.nan)
    assert r3.expectations(arms) == dict(X1=False, X2=True, X3=None)


def test_i2_check():
    r2 = {arm: [dict(seed=s, drive=d, recruited=600 + s, rhythm_score_reported_only=(None if s == 1 else .01),
                     core={c: dict(active=True) for c in r3.CORE}) for s in r3.I2_SEEDS]
          for arm, d in r3.DRIVES.items()}
    mine = {(arm, s): dict(recruited=600 + s, core_active={c: True for c in r3.CORE},
                           score=(math.nan if s == 1 else .01)) for arm in r3.DRIVES for s in r3.I2_SEEDS}
    assert r3.i2_check(mine, r2) == dict(passed=True, checked=8, mismatches=[])
    mine[('R1SIZE', 3)]['score'] = .010001
    out = r3.i2_check(mine, r2)
    assert not out['passed'] and out['mismatches'][0]['seed'] == 3
