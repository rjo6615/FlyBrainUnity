"""Synthetic checks for antennal gravity Step D4 v2; no FlyGym, CNS or physics run."""
import copy
import json
import math

import numpy as np
import pytest

from malecns_backend.live import jo_command_direction_v2 as m
from malecns_backend.live import jo_command_yoke as cy
from malecns_backend.live import jo_zone_crossing as zc

STEPS, EVENT = 40, 10
A = list(m.ADMITTED)
OUTSIDE = {10: -1.75, 12: 1.9, 17: -1.56, 31: -1.8, 33: 1.85}   # outside the v1 default range


def test_arms_and_protocol():
    assert len(m.ARMS) == 15 and m.ARMS[0] == 'POST_NEG__G1_DOWN20_19' and m.ARMS[-1] == 'POST_SCRAMBLE__FLIP_DOWN20_24'
    assert m.split('POST_HALF__FLIP_DOWN20_23') == ('POST_HALF', 'FLIP_DOWN20_23')
    for bad in ('POST_ONLY__G1_DOWN20_19', 'POST_NEG__G1_DOWN20_20', 'POST_NEG__OFF_DOWN20_19'):
        with pytest.raises(ValueError):
            m.split(bad)
    spec = json.loads((m.ROOT/m.PROTOCOL).read_text())
    assert spec['arms']['total'] == len(m.ARMS) and tuple(spec['admitted']) == m.ADMITTED
    assert spec['scramble']['sign_by_admitted_order'] == m.SIGN.tolist() == m.v1.scramble_draw().tolist()
    assert spec['declared_live_range_rad'] == [m.LIVE_MIN, m.LIVE_MAX]
    assert set(spec['sources']['v1_post_only_arms']) == {f'POST_ONLY__{s}' for s in m.FALLEN}
    assert set(spec['sources']['archives']) == set(m.FALLEN) | {cy.off_of(s) for s in m.FALLEN}


def outside_schedules(n):
    rng = np.random.default_rng(1)
    off = rng.uniform(-.5, .5, size=(n, 42))
    for i, v in OUTSIDE.items():
        off[:, i] = v
    on = off + rng.uniform(-.2, .2, size=(n, 42))
    on[:, list(cy.UNADMITTED)] = off[:, list(cy.UNADMITTED)] + 7.   # must never be taken from ON
    return on, off


def test_schedules_outside_default_range():
    n, t = m.TILT_TRANSITION + 3, m.TILT_TRANSITION
    on, off = outside_schedules(n)
    for cond in m.CONDITIONS:
        x, clipped = m.schedule_for(cond, on, off)
        assert clipped == 0, cond   # v1 clipped these coordinates; v2 must not
        assert np.array_equal(x[:t], off[:t]) and np.array_equal(x[:, list(cy.UNADMITTED)], off[:, list(cy.UNADMITTED)])
    assert np.allclose(m.schedule_for('POST_NEG', on, off)[0][t:, A], 2*off[t:, A] - on[t:, A])
    assert np.allclose(m.schedule_for('POST_HALF', on, off)[0][t:, A], (off[t:, A] + on[t:, A])/2)
    s = m.schedule_for('POST_SCRAMBLE', on, off)[0][t:, A]
    plus, minus = m.SIGN > 0, m.SIGN < 0
    assert np.array_equal(s[:, plus], on[t:, A][:, plus])
    assert np.allclose(s[:, minus], (2*off[t:, A] - on[t:, A])[:, minus])
    # the v1 rule would have clipped them: the defect this version removes
    assert m.v1.schedule_for('POST_HALF', on, off)[1] > 0
    # per-coordinate clipping still works when a range is finite
    tight = dict(m.RANGES)
    tight[12] = (-1., 1.)
    x, clipped = m.schedule_for('POST_HALF', on, off, tight)
    assert clipped == 3 and np.all(x[t:, 12] == 1.)
    with pytest.raises(ValueError):
        m.schedule_for('POST_ONLY', on, off)


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


def samples(cmds, fall_at=None):
    g = zc.tilt_gravity('DOWN20')
    out = []
    for i in range(STEPS + 1):
        tilt = 60. if fall_at is not None and i >= fall_at else 0.
        body = quat(-(tilt + 20.)) if i > EVENT else quat(0.)
        out.append(dict(qpos=body, commanded_joints=None if i == 0 else list(cmds[i - 1]), adhesion_zero=None if i == 0 else True,
                        gravity=list(zc.G0) if i <= EVENT else g, applied_body_wrenches=[], external_applied_max=0.,
                        generalized_applied_max=0))
    return out


def live_records(lo=m.LIVE_MIN, hi=m.LIVE_MAX):
    ch = {f'ch{i}': dict(index=i, safety=dict(joint_min_rad=lo, joint_max_rad=hi, max_offset_rad=.25,
                                              max_velocity_rad_s=4.)) for i in A}
    act = [dict(actuator=i, actuator_name=f'a{i}', joint=i + 1, joint_name=f'j{i}', jnt_limited=False,
                jnt_range=[0., 0.], ctrllimited=True, ctrlrange=[-1e6, 1e6]) for i in range(42)]
    return ch, act


def archives():
    rng = np.random.default_rng(0)
    out = {}
    servo = rng.uniform(-.5, .5, size=(STEPS, len(cy.UNADMITTED)))
    offs = {}
    for seed in (19, 21, 23, 24):
        off = rng.uniform(-.5, .5, size=(STEPS, 42))
        for i, v in OUTSIDE.items():
            off[:, i] = v
        off[:, list(cy.UNADMITTED)] = servo
        offs[seed] = off
        out[f'OFF_DOWN20_{seed}'] = dict(samples=samples(off))
    for s in m.FALLEN:
        on = offs[int(s.rsplit('_', 1)[1])] + rng.uniform(-.2, .2, size=(STEPS, 42))
        on[:, list(cy.UNADMITTED)] = servo
        out[s] = dict(samples=samples(on, fall_at=25))
    return out


def v1_post_only(arch):
    return {f'POST_ONLY__{s}': dict(samples=samples(m.yk.schedule(arch[s]), 30)) for s in m.FALLEN}


def v1_outcomes(post_only_falls=True):
    o = dict(falls=True, t_fall_ms=1.0, peak_tilt_deg=150.)
    up = dict(falls=False, t_fall_ms=None, peak_tilt_deg=30.)
    return {s: dict(POST_ONLY=o if post_only_falls else up, POST_NEG=up, POST_HALF=up, POST_SCRAMBLE=o) for s in m.FALLEN}


def arms_for(arch, falls):
    arms = {}
    for name in m.ARMS:
        cond, s = m.split(name)
        x, clipped = m.schedule_for(cond, m.yk.schedule(arch[s]), m.yk.schedule(arch[cy.off_of(s)]))
        ch, act = live_records()
        arms[name] = dict(run_status='COMPLETE', samples=samples(x, 30 if falls(cond, s) else None),
                          neural=[{}]*(STEPS//5), source=s, cns_seed=int(s.rsplit('_', 1)[1]),
                          clipped_values=clipped, channel_ranges=ch, actuator_limits=act)
    return arms


def pattern(cond, s):
    return cond == 'POST_SCRAMBLE' or (cond == 'POST_NEG' and s.startswith('FLIP'))


def run_eval(arms, arch, v1=None, v1o=None, ok=True):
    v1 = v1 or v1_post_only(arch)
    v1o = v1o or v1_outcomes()
    return m.evaluate(lambda k: copy.deepcopy(arms[k]), lambda k: arch[k], lambda k: v1[k], v1o, ok)


def test_evaluate_accepts(small):
    arch = archives()
    e = run_eval(arms_for(arch, pattern), arch)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['labels']['G1_DOWN20_19'] == dict(direction='DIRECTION_SPECIFIC', pattern='PATTERN_NONSPECIFIC',
                                               half_dose='HALF_DOSE_STAYS_UP')
    assert e['consistency']['FLIP']['direction'] == 'DIRECTION_NONSPECIFIC'
    assert e['consistency']['G1']['direction'] == 'DIRECTION_SPECIFIC'
    assert e['expectations'] == dict(E1='NOT_HELD', E2='HELD')
    d = e['diagnostics']['G1_DOWN20_19']['POST_NEG']
    assert d['clipped_values'] == 0 and d['max_abs_command_rad'] > 1.35 and set(d['excursion_beyond_on_off_rad']) == set(A)
    assert e['diagnostics']['G1_DOWN20_19']['POST_HALF']['excursion_beyond_on_off_rad'][12] == 0.
    assert e['v1_vs_v2']['G1_DOWN20_19']['POST_NEG']['v2']['falls'] is False


def test_expectations_held(small):
    arch = archives()
    e = run_eval(arms_for(arch, lambda cond, s: cond == 'POST_SCRAMBLE'), arch)
    assert e['expectations'] == dict(E1='HELD', E2='HELD')


def test_prerequisite(small):
    arch = archives()
    e = run_eval(arms_for(arch, pattern), arch, v1o=v1_outcomes(False))
    assert e['status'] == 'INCONCLUSIVE_PREREQUISITE' and 'labels' not in e


def test_integrity_failures(small):
    arch = archives()
    good = arms_for(arch, pattern)
    assert run_eval(good, arch, ok=False)['checks']['Z5_sources'] is False
    v1_bad = v1_post_only(arch)
    v1_bad['POST_ONLY__G1_DOWN20_21']['samples'][4]['qpos'] = quat(5.)
    e = run_eval(good, arch, v1=v1_bad)
    assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and e['checks']['Z2_pretilt_anchor'] is False and 'labels' not in e
    first = 'ch' + str(A[4])

    def narrow(a):    # the v1 default range recorded live -> declared range mismatch
        a['POST_HALF__G1_DOWN20_24']['channel_ranges'][first]['safety'].update(joint_min_rad=-1.35, joint_max_rad=1.30)

    def duplicate(a):
        a['POST_NEG__G1_DOWN20_19']['channel_ranges']['extra'] = dict(index=A[0], safety=dict(joint_min_rad=-1e6, joint_max_rad=1e6))

    def ctrl(a):
        a['POST_SCRAMBLE__FLIP_DOWN20_23']['actuator_limits'][12].update(ctrlrange=[-1.5, 1.5])

    for mutate, key in (
            (lambda a: a['POST_NEG__G1_DOWN20_21'].update(run_status='ERROR'), 'Z1_complete'),
            (lambda a: a['POST_HALF__FLIP_DOWN20_23']['samples'][EVENT + 3]['commanded_joints'].__setitem__(3, 9.), 'Z3_yoke_audit'),
            (lambda a: a['POST_NEG__G1_DOWN20_24']['samples'][5].update(adhesion_zero=False), 'Z3_yoke_audit'),
            (lambda a: a['POST_SCRAMBLE__G1_DOWN20_19']['samples'][EVENT + 1].update(gravity=list(zc.G0)), 'Z4_gravity'),
            (lambda a: a['POST_NEG__FLIP_DOWN20_24'].update(cns_seed=7), 'Z5_sources'),
            (lambda a: a['POST_HALF__G1_DOWN20_19']['samples'][3].update(qpos=quat(1.)), 'Z2_pretilt_anchor'),
            (narrow, 'Z6_live_range'),
            (duplicate, 'Z6_live_range'),
            (ctrl, 'Z6_live_range'),
            (lambda a: a['POST_NEG__G1_DOWN20_21'].update(channel_ranges=None), 'Z6_live_range'),
            (lambda a: a['POST_HALF__FLIP_DOWN20_24'].update(clipped_values=4), 'Z7_no_clip')):
        arms = copy.deepcopy(good)
        mutate(arms)
        e = run_eval(arms, arch)
        assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and e['checks'][key] is False and 'labels' not in e, key


def test_preflight(small):
    arch = archives()
    a = arms_for(arch, pattern)['POST_NEG__G1_DOWN20_19']
    smoke = dict(a, run_status='SMOKE', samples=a['samples'][:6])
    assert m.preflight(smoke) == dict(status='SMOKE', audited_rows=5, adhesion_zero=True, live_range_ok=True)
    smoke['channel_ranges'] = live_records(-1.35, 1.30)[0]
    assert m.preflight(smoke)['live_range_ok'] is False
