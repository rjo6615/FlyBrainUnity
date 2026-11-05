"""Synthetic checks for antennal gravity Step C2; a tiny MJCF model, no FlyGym, CNS or physics run."""
import itertools
import math

import numpy as np
import pytest

from malecns_backend.embodiment import jo_operating_point as m


def test_shapley_exact_on_known_function():
    a, b = np.array([.3, -.2, .5, .1, 0., .7]), .4
    vals = []
    for mask in range(64):
        x = np.array([(mask >> i) & 1 for i in range(6)], float)
        vals.append(a @ x + b*x[0]*x[1])
    phi = m.shapley(vals)
    expect = a.copy()
    expect[:2] += b/2
    assert np.allclose(phi, expect, atol=1e-12)
    rng = np.random.default_rng(1)
    v = rng.normal(size=(64, 2))
    assert np.allclose(m.shapley(v).sum(0), v[-1] - v[0], atol=1e-12)
    assert sum(m.WEIGHTS[k]*math.comb(5, k) for k in range(6)) == pytest.approx(1)


def _phi(shares, total, n=18):
    return [[s*total for s in shares]]*n, [total]*n


def test_label_rules():
    phi, tot = _phi([.6, .2, .1, .1, 0, 0], -.05)
    lab, st = m.label(phi, tot)
    assert lab == 'DOMINANT_ROOT' and st['factors']['ROOT']['median_share'] == pytest.approx(.6)
    assert m.label(*_phi([.6, .2, .1, .1, 0, 0], .009))[0] == 'NO_MATERIAL_DRIFT'
    assert m.label(*_phi([.4, .3, .3, 0, 0, 0], .05))[0] == 'MIXED'
    assert m.label(*_phi([.5, .5, 0, 0, 0, 0], .05))[0] in ('DOMINANT_ROOT', 'DOMINANT_NECK')
    assert m.label(*_phi([1.4, -.9, .5, 0, 0, 0], .05))[0] == 'DOMINANT_ROOT'
    assert m.label(*_phi([.3, .2, .1, .9, -.5, 0], .05))[0] == 'DOMINANT_A3'
    # sign consistency: 2 of 18 arms with the wrong sign (88.9 %) fails, 1 of 10 (90 %) passes
    phi, tot = _phi([.8, .2, 0, 0, 0, 0], .05)
    phi = [list(p) for p in phi]
    for k in (0, 1):
        phi[k] = [-.01, .06, 0, 0, 0, 0]
    assert m.label(phi, tot)[0] == 'MIXED'
    phi, tot = _phi([.8, .2, 0, 0, 0, 0], .05, n=10)
    phi = [list(p) for p in phi]
    phi[0] = [-.01, .06, 0, 0, 0, 0]
    assert m.label(phi, tot)[0] == 'DOMINANT_ROOT'


def _rec(j2=0., j3=0., j4=0.):
    z = [[0., 0.]]*6
    return dict(j2=j2, j3=j3, j4=j4, pre=dict(phi=z, total=[0., 0.]), win=dict(phi=z, total=[0., 0.]))


def test_evaluate_integrity():
    recs = {n: _rec() for n in m.ARMS}
    cons = {f'{t}_{s}': dict(j4=0.) for t in m.TYPES for s in m.SEEDS}
    e = m.evaluate(recs, cons, True, True)
    assert e['status'] == 'INTEGRITY_ACCEPTED' and e['labels']['Q1_L'] == 'NO_MATERIAL_DRIFT'
    assert set(e['labels']) == {f'{g}_{s}' for g in ('Q1', 'Q2_UP', 'Q2_DOWN') for s in 'LR'}
    for args, key in (((recs, cons, False, True), 'J1_inputs'), ((recs, cons, True, False), 'factor_addresses'),
                      (({**recs, 'G1_UP_13': _rec(j2=2e-9)}, cons, True, True), 'J2_replay'),
                      (({**recs, 'G1_UP_13': _rec(j3=None)}, cons, True, True), 'J3_reference'),
                      (({**recs, 'G1_UP_13': _rec(j3=2e-4)}, cons, True, True), 'J3_reference'),
                      ((recs, {**cons, 'OFF_13': dict(j4=1e-8)}, True, True), 'J4_additivity')):
        e = m.evaluate(*args)
        assert e['status'] == 'INCONCLUSIVE_INTEGRITY' and e['checks'][key] is False and 'labels' not in e


def test_groups_split_up_down():
    recs = {n: _rec() for n in m.ARMS}
    g = m.groups(recs)
    assert len(g['Q1']) == 36 and len(g['Q2_UP']) == len(g['Q2_DOWN']) == 18


def test_tick_gravity_rule():
    arm = dict(initial=dict(tilt_state=5005), tilt_event=dict(gravity=[1., 0., -2.]))
    assert m.tick_gravity(arm, 1000) == m.G0 and m.tick_gravity(arm, 1001) == (1., 0., -2.)


# ---- tiny MuJoCo model with the real chain structure ---------------------------------

def _antenna(s):
    tri = ''.join(f'<joint name="joint_{s}{{b}}{x}" type="hinge" axis="{ax}" stiffness="1"/>'
                  for x, ax in (('_yaw', '0 0 1'), ('', '0 1 0'), ('_roll', '1 0 0')))
    y = .1 if s == 'L' else -.1
    return (f'<body name="{s}Pedicel" pos=".2 {y} .05">{tri.format(b="Pedicel")}'
            '<inertial pos="0 0 -.02" mass=".01" diaginertia="1e-5 1e-5 1e-5"/>'
            f'<body name="{s}Funiculus" pos="0 0 -.04">{tri.format(b="Funiculus")}'
            '<inertial pos=".01 0 -.08" mass=".01" diaginertia="1e-5 1e-5 1e-5"/>'
            f'<body name="{s}Arista" pos="0 0 -.06">{tri.format(b="Arista")}'
            f'<inertial pos="0 {y} 0" mass=".001" diaginertia="1e-6 1e-6 1e-6"/></body></body></body>')


XML = ('<mujoco><option gravity="0 0 -9810"/><worldbody><body name="FlyBody"><freejoint/>'
       '<body name="Thorax"><inertial pos="0 0 0" mass="1" diaginertia="1 1 1"/>'
       '<body name="Head" pos=".5 0 0">'
       + ''.join(f'<joint name="joint_Head{x}" type="hinge" axis="{ax}" stiffness="10"/>'
                 for x, ax in (('_yaw', '0 0 1'), ('', '0 1 0'), ('_roll', '1 0 0')))
       + '<inertial pos="0 0 0" mass=".1" diaginertia=".01 .01 .01"/>'
       + _antenna('L') + _antenna('R') + '</body></body></body></worldbody></mujoco>')

TINY_ADDR = {'ROOT': [3, 4, 5, 6], 'NECK': [7, 8, 9], 'A2': [10, 11, 12, 19, 20, 21],
             'A3': [13, 14, 15, 22, 23, 24], 'ARISTA': [16, 17, 18, 25, 26, 27]}


@pytest.fixture
def tiny(monkeypatch):
    mujoco = pytest.importorskip('mujoco')
    monkeypatch.setattr(m, 'ADDR', TINY_ADDR)
    model = mujoco.MjModel.from_xml_string(XML)
    return model, m.Replay(model)


def _q(model, root_deg_y=0., extra=None):
    q = np.array(model.qpos0, float)
    h = math.radians(root_deg_y)/2
    q[3:7] = [math.cos(h), 0, math.sin(h), 0]
    for a, v in (extra or {}).items():
        q[a] = v
    return q


def test_resolve_matches_declared_addresses(tiny):
    model, _ = tiny
    found, ok = m.resolve(model)
    assert ok and found['A3'] == TINY_ADDR['A3']


def test_root_only_change_is_all_root(tiny):
    model, rp = tiny
    phi, total, err = rp.decompose((_q(model), m.G0), (_q(model, 10.), m.G0))
    assert err < 1e-12 and abs(total[0]) > 1e-3
    assert np.allclose(phi[0], total) and np.allclose(phi[1:], 0)


def test_joint_only_change_goes_to_that_factor(tiny):
    model, rp = tiny
    phi, total, _ = rp.decompose((_q(model), m.G0), (_q(model, 0., {14: .2, 23: .2}), m.G0))
    assert abs(total[0]) > 1e-3 and np.allclose(phi[3], total) and np.allclose(np.delete(phi, 3, 0), 0)


def test_rotating_body_and_gravity_together_leaves_d(tiny):
    model, rp = tiny
    phi_deg = 10.
    # gravity R_y(-10) applied to (0,0,-9810) and body R_y(-10): relative geometry unchanged
    gv = np.array([[math.cos(math.radians(-phi_deg)), 0, math.sin(math.radians(-phi_deg))], [0, 1, 0],
                   [-math.sin(math.radians(-phi_deg)), 0, math.cos(math.radians(-phi_deg))]]) @ np.array(m.G0)
    phi, total, err = rp.decompose((_q(model), m.G0), (_q(model, -phi_deg), tuple(gv)))
    assert gv[0] > 0  # matches antennal_gravity_live.rotated_gravity(-10) (DOWN)
    assert np.allclose(total, 0, atol=1e-9) and err < 1e-12
    assert phi[0][0] == pytest.approx(-phi[5][0], abs=1e-9) and abs(phi[0][0]) > 1e-3
