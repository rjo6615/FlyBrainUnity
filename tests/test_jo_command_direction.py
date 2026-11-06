"""Synthetic checks for antennal gravity Step D4; no FlyGym, CNS or physics run."""
import copy
import json
import math

import numpy as np
import pytest

from malecns_backend.live import jo_command_direction as m
from malecns_backend.live import jo_command_yoke as cy
from malecns_backend.live import jo_zone_crossing as zc

STEPS, EVENT = 40, 10
A = list(m.ADMITTED)


def test_arms_and_scramble_vector():
    assert len(m.ARMS) == 27 and m.ARMS[0] == 'POST_ONLY__G1_DOWN20_19' and m.ARMS[-1] == 'POST_ONLY__FLIP_DOWN20_22'
    assert m.split('POST_NEG__FLIP_DOWN20_24') == ('POST_NEG', 'FLIP_DOWN20_24')
    assert m.split('POST_ONLY__G1_DOWN20_22') == ('POST_ONLY', 'G1_DOWN20_22')
    for bad in ('POST_NEG__G1_DOWN20_22', 'FULL_ON__G1_DOWN20_19', 'POST_ONLY__OFF_DOWN20_19'):
        with pytest.raises(ValueError):
            m.split(bad)
    assert np.array_equal(m.scramble_draw(), m.SIGN) and (m.SIGN == -1).sum() == 10
    spec = json.loads((m.ROOT/m.PROTOCOL).read_text())
    assert spec['scramble']['sign_by_admitted_order'] == m.SIGN.tolist()
    assert [A[i] for i in spec['scramble']['flipped_positions']] == spec['scramble']['flipped_coordinates']
    assert spec['arms']['total'] == len(m.ARMS) and tuple(spec['admitted']) == m.ADMITTED


def test_schedules():
    n = m.TILT_TRANSITION + 3
    rng = np.random.default_rng(1)
    off = rng.uniform(-.5, .5, size=(n, 42))
    on = off + rng.uniform(-.2, .2, size=(n, 42))
    on[:, list(cy.UNADMITTED)] = off[:, list(cy.UNADMITTED)] + 7.   # must never be taken from ON
    t = m.TILT_TRANSITION
    for cond in m.FALLEN_CONDITIONS:
        x, clipped = m.schedule_for(cond, on, off)
        assert np.array_equal(x[:t], off[:t]) and np.array_equal(x[:, list(cy.UNADMITTED)], off[:, list(cy.UNADMITTED)])
        assert clipped == 0, cond
    assert np.array_equal(m.schedule_for('POST_ONLY', on, off)[0][t:, A], on[t:, A])
    assert np.allclose(m.schedule_for('POST_NEG', on, off)[0][t:, A], 2*off[t:, A] - on[t:, A])
    assert np.allclose(m.schedule_for('POST_HALF', on, off)[0][t:, A], (off[t:, A] + on[t:, A])/2)
    s = m.schedule_for('POST_SCRAMBLE', on, off)[0][t:, A]
    plus, minus = m.SIGN > 0, m.SIGN < 0
    assert np.array_equal(s[:, plus], on[t:, A][:, plus])
    assert np.allclose(s[:, minus], (2*off[t:, A] - on[t:, A])[:, minus])
    # clipping: a reversed change past the joint range is clipped and counted
    on2, off2 = on.copy(), off.copy()
    off2[t:, 3], on2[t:, 3] = 1.2, 1.0      # reversed: 1.4 > 1.30
    x, clipped = m.schedule_for('POST_NEG', on2, off2)
    assert clipped == 3 and np.all(x[t:, 3] == m.JOINT_MAX)
    assert m.schedule_for('POST_SCRAMBLE', on2, off2)[1] == 3   # coordinate 3 has sign -1
    with pytest.raises(ValueError):
        m.schedule_for('PRE_ONLY', on, off)


# ---- synthetic arms -------------------------------------------------------------------------

@pytest.fixture
def small(monkeypatch):
    monkeypatch.setattr(m.c, 'STEPS', STEPS)
    monkeypatch.setattr(m.c, 'TICKS', STEPS//5)
    monkeypatch.setattr(m.c, 'EVENT_STATE', EVENT)
    monkeypatch.setattr(m, 'TILT_TRANSITION', EVENT)


def quat(deg):
    a = math.radians(deg)
    return [0, 0, 0, math.cos(a/2), 0, math.sin(a/2), 0]


def samples(cmds, fall_at=None, wobble=False):
    g = zc.tilt_gravity('DOWN20')
    out = []
    for i in range(STEPS + 1):
        tilt = 60. if fall_at is not None and i >= fall_at else 0.
        if i > EVENT:
            body = quat(-(tilt + 20.))
        else:
            body = quat(.5 if wobble and i >= 3 else 0.)
        out.append(dict(qpos=body, commanded_joints=None if i == 0 else list(cmds[i - 1]), adhesion_zero=None if i == 0 else True,
                        gravity=list(zc.G0) if i <= EVENT else g, applied_body_wrenches=[], external_applied_max=0.,
                        generalized_applied_max=0))
    return out


def archives():
    rng = np.random.default_rng(0)
    out = {}
    servo = rng.uniform(-.5, .5, size=(STEPS, len(cy.UNADMITTED)))
    offs = {}
    for seed in range(19, 25):
        off = rng.uniform(-.5, .5, size=(STEPS, 42))
        off[:, list(cy.UNADMITTED)] = servo
        offs[seed] = off
        out[f'OFF_DOWN20_{seed}'] = dict(samples=samples(off))
    for s in m.FALLEN + m.UPRIGHT:
        on = offs[int(s.rsplit('_', 1)[1])] + rng.uniform(-.2, .2, size=(STEPS, 42))
        on[:, list(cy.UNADMITTED)] = servo
        out[s] = dict(samples=samples(on, fall_at=25 if s in m.FALLEN else None,
                                      wobble=s in m.UPRIGHT and s.startswith('G1')))
    return out


def arms_for(arch, falls):
    """falls(cond, source) -> bool."""
    arms = {}
    for name in m.ARMS:
        cond, s = m.split(name)
        on, off = m.yk.schedule(arch[s]), m.yk.schedule(arch[cy.off_of(s)])
        x, _ = m.schedule_for(cond, on, off)
        arms[name] = dict(run_status='COMPLETE', samples=samples(x, 30 if falls(cond, s) else None),
                          neural=[{}]*(STEPS//5), source=s, cns_seed=int(s.rsplit('_', 1)[1]))
    return arms


def pattern(cond, s):
    if s in m.UPRIGHT:
        return s == 'G1_DOWN20_22'
    return cond in ('POST_ONLY', 'POST_SCRAMBLE') or (cond == 'POST_NEG' and s.startswith('FLIP'))


def run_eval(arms, arch, d3=None, ok=True):
    d3 = d3 or {f'POST_ONLY__{s}': copy.deepcopy(arms[f'POST_ONLY__{s}']) for s in m.FALLEN}
    return m.evaluate(lambda k: copy.deepcopy(arms[k]), lambda k: arch[k], lambda k: d3[k], ok)


def test_evaluate_accepts(small):
    arch = archives()
    e = run_eval(arms_for(arch, pattern), arch)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['labels']['G1_DOWN20_19'] == dict(direction='DIRECTION_SPECIFIC', pattern='PATTERN_NONSPECIFIC',
                                               half_dose='HALF_DOSE_STAYS_UP')
    assert e['consistency']['FLIP']['direction'] == 'DIRECTION_NONSPECIFIC'
    assert e['consistency']['G1']['direction'] == 'DIRECTION_SPECIFIC'
    assert e['upright_degenerate'] == {s: s.startswith('FLIP') for s in m.UPRIGHT}
    assert e['upright']['G1'] == dict(non_degenerate=['G1_DOWN20_20', 'G1_DOWN20_22', 'G1_DOWN20_23'], degenerate=[],
                                      falls=['G1_DOWN20_22'])
    assert e['upright']['FLIP']['non_degenerate'] == []
    assert e['expectations'] == dict(E1='NOT_HELD', E2='HELD', E3='NOT_HELD')
    assert e['diagnostics']['G1_DOWN20_19']['POST_NEG']['clipped_values'] == 0
    assert e['diagnostics']['G1_DOWN20_19']['POST_ONLY']['max_step_at_tilt_rad'] > 0
    assert set(e['mean_abs_delta_post_rad']) == set(m.FALLEN + m.UPRIGHT)


def test_expectations_held(small):
    arch = archives()
    e = run_eval(arms_for(arch, lambda cond, s: s in m.FALLEN and cond in ('POST_ONLY', 'POST_SCRAMBLE')), arch)
    assert e['expectations'] == dict(E1='HELD', E2='HELD', E3='HELD')


def test_integrity_failures(small):
    arch = archives()
    good = arms_for(arch, pattern)
    assert run_eval(good, arch, ok=False)['checks']['Z5_sources'] is False
    d3_bad = {f'POST_ONLY__{s}': copy.deepcopy(good[f'POST_ONLY__{s}']) for s in m.FALLEN}
    d3_bad['POST_ONLY__G1_DOWN20_21']['samples'][33]['qpos'] = quat(5.)
    e = run_eval(good, arch, d3=d3_bad)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and e['checks']['Z2_reproduction'] is False and 'labels' not in e
    for mutate, key in (
            (lambda a: a['POST_NEG__G1_DOWN20_21'].update(run_status='ERROR'), 'Z1_complete'),
            (lambda a: a['POST_HALF__FLIP_DOWN20_23']['samples'][EVENT + 3]['commanded_joints'].__setitem__(3, 9.), 'Z3_yoke_audit'),
            (lambda a: a['POST_ONLY__G1_DOWN20_20']['samples'][5].update(adhesion_zero=False), 'Z3_yoke_audit'),
            (lambda a: a['POST_SCRAMBLE__G1_DOWN20_19']['samples'][EVENT + 1].update(gravity=list(zc.G0)), 'Z4_gravity'),
            (lambda a: a['POST_ONLY__FLIP_DOWN20_22']['samples'][3].update(external_applied_max=1.), 'Z4_gravity'),
            (lambda a: a['POST_NEG__FLIP_DOWN20_24'].update(cns_seed=7), 'Z5_sources')):
        arms = copy.deepcopy(good)
        mutate(arms)
        e = run_eval(arms, arch)
        assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and e['checks'][key] is False and 'labels' not in e, key


def test_degenerate_rule(small):
    arch = archives()
    assert m.degenerate(arch['FLIP_DOWN20_19'], arch['OFF_DOWN20_19'])
    assert not m.degenerate(arch['G1_DOWN20_20'], arch['OFF_DOWN20_20'])
    # a fallen ON archive diverges only after the tilt -> degenerate by the rule
    assert m.degenerate(arch['G1_DOWN20_19'], arch['OFF_DOWN20_19'])
