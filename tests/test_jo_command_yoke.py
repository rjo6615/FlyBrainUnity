"""Synthetic checks for antennal gravity Step D3; no FlyGym, CNS or physics run."""
import copy
import math

import numpy as np
import pytest

from malecns_backend.live import jo_command_yoke as m
from malecns_backend.live import jo_zone_crossing as zc

STEPS, EVENT = 40, 10


def test_arms_groups_and_masks():
    assert len(m.ARMS) == 45 and m.ARMS[0] == 'FULL_ON__G1_DOWN20_19' and m.ARMS[-1] == 'POST_ONLY__FLIP_DOWN20_24'
    assert len(m.ADMITTED) == 20 and len(m.UNADMITTED) == 22
    assert m.split('NO_HIND__FLIP_DOWN20_23') == ('NO_HIND', 'FLIP_DOWN20_23')
    assert m.off_of('G1_DOWN20_21') == 'OFF_DOWN20_21'
    for bad in ('NO_HIND__G1_DOWN20_20', 'ALL__G1_DOWN20_19'):
        with pytest.raises(ValueError):
            m.split(bad)
    assert set(np.flatnonzero(m.on_mask('FULL_ON', 0))) == set(m.ADMITTED)
    assert set(np.flatnonzero(m.on_mask('ONLY_FRONT', 7))) == set(m.GROUPS['FRONT'])
    assert set(np.flatnonzero(m.on_mask('NO_MIDDLE', 7))) == set(m.ADMITTED) - set(m.GROUPS['MIDDLE'])
    assert set(np.flatnonzero(m.on_mask('PRE_ONLY', 5004))) == set(m.ADMITTED)
    assert not m.on_mask('PRE_ONLY', 5005).any()
    assert not m.on_mask('POST_ONLY', 5004).any()
    assert set(np.flatnonzero(m.on_mask('POST_ONLY', 5005))) == set(m.ADMITTED)


def test_mix_never_takes_unadmitted_from_on():
    on, off = np.full((5006, 42), 1.), np.zeros((5006, 42))
    for cond in m.CONDITIONS:
        x = m.mix(cond, on, off)
        assert not x[:, list(m.UNADMITTED)].any(), cond
    x = m.mix('PRE_ONLY', on, off)
    assert x[5004, 3] == 1. and x[5005, 3] == 0.
    assert m.mix('ONLY_HIND', on, off)[0, 17] == 1. and m.mix('ONLY_HIND', on, off)[0, 3] == 0.


def test_labels_and_consistency():
    assert m.group_label(True, False) == 'SUFFICIENT_AND_NECESSARY'
    assert m.group_label(True, True) == 'SUFFICIENT_NOT_NECESSARY'
    assert m.group_label(False, False) == 'NECESSARY_NOT_SUFFICIENT'
    assert m.group_label(False, True) == 'NEITHER'
    falls = lambda f: dict(falls=f, t_fall_ms=None, peak_tilt_deg=0.)
    out = {k: falls(False) for k in m.CONDITIONS}
    out.update(ONLY_FRONT=falls(True), NO_MIDDLE=falls(True), NO_HIND=falls(True), POST_ONLY=falls(True))
    lab = m.source_labels(out)
    assert lab['groups'] == dict(FRONT='SUFFICIENT_AND_NECESSARY', MIDDLE='NEITHER', HIND='NEITHER')
    assert lab['timing'] == dict(PRE_TILT_SUFFICIENT=False, POST_TILT_SUFFICIENT=True)
    labels = {s: copy.deepcopy(lab) for s in m.SOURCES}
    outcomes = {s: out for s in m.SOURCES}
    labels['G1_DOWN20_21']['groups']['HIND'] = 'NECESSARY_NOT_SUFFICIENT'
    cons = m.consistency(labels)
    assert cons['G1']['groups']['HIND'] == 'MIXED' and cons['FLIP']['groups']['FRONT'] == 'SUFFICIENT_AND_NECESSARY'
    assert cons['G1']['timing']['POST_TILT_SUFFICIENT'] is True
    assert m.expectations(labels, outcomes) == dict(E1_FLIP='HELD', E2_G1='NOT_HELD')


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
        # body pitched by `tilt` relative to the tilted gravity: rotate about y by tilt + 20 deg after the event
        body = quat(-(tilt + 20.)) if i > EVENT else quat(0.)
        out.append(dict(qpos=body, commanded_joints=None if i == 0 else list(cmds[i - 1]), adhesion_zero=None if i == 0 else True,
                        gravity=list(zc.G0) if i <= EVENT else g, applied_body_wrenches=[], external_applied_max=0.,
                        generalized_applied_max=0))
    return out


def archives():
    rng = np.random.default_rng(0)
    out = {}
    servo = rng.normal(size=(STEPS, len(m.UNADMITTED)))   # baseline servos: identical in every archive
    for s in m.SOURCES:
        on = rng.normal(size=(STEPS, 42))
        off = rng.normal(size=(STEPS, 42))
        on[:, list(m.UNADMITTED)] = off[:, list(m.UNADMITTED)] = servo
        out[s] = dict(samples=samples(on, fall_at=25))
        out[m.off_of(s)] = dict(samples=samples(off))
    return out


def arms_for(arch, falls):
    """falls(cond, source) -> bool."""
    arms = {}
    for s in m.SOURCES:
        on, off = m.yk.schedule(arch[s]), m.yk.schedule(arch[m.off_of(s)])
        for cond in m.CONDITIONS:
            x = m.mix(cond, on, off)
            rows = copy.deepcopy(arch[s]['samples']) if cond == 'FULL_ON' else samples(x, 30 if falls(cond, s) else None)
            arms[f'{cond}__{s}'] = dict(run_status='COMPLETE', samples=rows, neural=[{}]*(STEPS//5), source=s,
                                        cns_seed=int(s.rsplit('_', 1)[1]))
    return arms


def pattern(cond, s):
    if s.startswith('FLIP'):
        return cond in ('ONLY_FRONT', 'NO_MIDDLE', 'NO_HIND', 'POST_ONLY')
    return cond in ('ONLY_HIND', 'NO_FRONT', 'NO_MIDDLE', 'PRE_ONLY')


def run_eval(arms, arch, ok=True):
    return m.evaluate(lambda k: copy.deepcopy(arms[k]), lambda k: arch[k], ok)


def test_evaluate_accepts(small):
    arch = archives()
    e = run_eval(arms_for(arch, pattern), arch)
    assert e['status'] == 'INTEGRITY_ACCEPTED', e['checks']
    assert e['outcomes']['FLIP_DOWN20_23']['FULL_ON']['falls'] and e['outcomes']['FLIP_DOWN20_23']['FULL_ON']['t_fall_ms'] == pytest.approx(1.5)
    assert e['consistency']['FLIP']['groups']['FRONT'] == 'SUFFICIENT_AND_NECESSARY'
    assert e['consistency']['G1']['groups']['HIND'] == 'SUFFICIENT_AND_NECESSARY'
    assert e['consistency']['G1']['timing'] == dict(PRE_TILT_SUFFICIENT=True, POST_TILT_SUFFICIENT=False)
    assert e['expectations'] == dict(E1_FLIP='HELD', E2_G1='HELD')
    assert all(e['unadmitted_identical_on_off'].values())


def test_integrity_failures(small):
    arch = archives()
    good = arms_for(arch, pattern)
    assert run_eval(good, arch, ok=False)['checks']['Y5_sources'] is False
    for mutate, key in (
            (lambda a: a['NO_HIND__G1_DOWN20_21'].update(run_status='ERROR'), 'Y1_complete'),
            (lambda a: a['FULL_ON__G1_DOWN20_24']['samples'][33].update(qpos=quat(5.)), 'Y2_reproduction'),
            (lambda a: a['ONLY_FRONT__FLIP_DOWN20_23']['samples'][12]['commanded_joints'].__setitem__(3, 9.), 'Y3_yoke_audit'),
            (lambda a: a['PRE_ONLY__FLIP_DOWN20_24']['samples'][5].update(adhesion_zero=False), 'Y3_yoke_audit'),
            (lambda a: a['POST_ONLY__G1_DOWN20_19']['samples'][EVENT + 1].update(gravity=list(zc.G0)), 'Y4_gravity'),
            (lambda a: a['NO_FRONT__G1_DOWN20_19']['samples'][3].update(external_applied_max=1.), 'Y4_gravity'),
            (lambda a: a['NO_FRONT__G1_DOWN20_21'].update(cns_seed=7), 'Y5_sources')):
        arms = copy.deepcopy(good)
        mutate(arms)
        e = run_eval(arms, arch)
        assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and e['checks'][key] is False and 'labels' not in e, key


def test_outcome_rule(small):
    arch = archives()
    o = m.outcome(dict(samples=samples(np.zeros((STEPS, 42)), fall_at=EVENT + 4)))
    assert o['falls'] and o['t_fall_ms'] == pytest.approx(.4) and o['peak_tilt_deg'] == pytest.approx(60.)
    o = m.outcome(dict(samples=samples(np.zeros((STEPS, 42)))))
    assert not o['falls'] and o['t_fall_ms'] is None and o['peak_tilt_deg'] == pytest.approx(0., abs=1e-9)
    assert m.first_qpos_difference(arch['G1_DOWN20_19'], arch['OFF_DOWN20_19']) == 25
