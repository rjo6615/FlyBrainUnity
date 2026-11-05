"""Synthetic checks for the antennal gravity encoder; toy MuJoCo body, no FlyGym, CNS or physics run."""
import numpy as np
import pytest

from malecns_backend.embodiment import antennal_gravity_encoder as e

mujoco = pytest.importorskip('mujoco')


def toy(tilt=0.):
    """Head at +x; a3 hangs straight down (inertial centre at -z); arista lever lateral (+-y)."""
    ant = ''.join(f'''
      <body name="{s}Funiculus" pos=".1 {0.05 if s == 'L' else -0.05} 0">
        <inertial pos="{tilt} 0 -.1" mass=".001" diaginertia="1e-6 1e-6 1e-6"/>
        <body name="{s}Arista" pos="0 {0.05 if s == 'L' else -0.05} 0">
          <inertial pos="0 0 0" mass=".001" diaginertia="1e-6 1e-6 1e-6"/>
        </body>
      </body>''' for s in 'LR')
    xml = f'''<mujoco><worldbody><body name="Thorax"><freejoint/><geom type="sphere" size=".1"/>
      <body name="Head" pos="1 0 0"><geom type="sphere" size=".05"/>{ant}</body></body></worldbody></mujoco>'''
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data, e.AntennaFrames(model)


def test_level_drive_zero_and_tangent_anterior_on_both_sides():
    model, data, f = toy()
    for s in 'LR':
        r = f.drive(data, s)
        assert r['d'] == pytest.approx(0, abs=1e-9)
        assert r['t_dot_x_head'] == pytest.approx(1)  # sign convention: tangent points anterior
    assert f.anterior_fraction(data) == pytest.approx(1)


def test_nose_down_pitch_pulls_arista_anteriorly_and_mirror_holds():
    model, data, f = toy()
    pitch, head_z = e.imposed_series(model, data, f, (0, 1, 0))
    i = e.GRID_DEG.index(10)
    assert head_z[i] < 0  # +pitch about world y is nose-down
    assert pitch['L'][i] == pytest.approx(np.sin(np.radians(10)))
    assert np.allclose(pitch['L'], pitch['R'])
    assert e._monotonic(pitch['L']) and e._slope(pitch['L']) == pytest.approx(1, abs=.01)
    assert np.allclose(data.qpos[3:7], [1, 0, 0, 0])  # restored


def test_roll_is_blind_for_vertical_axis_and_tilted_axis_gives_opposite_sides():
    model, data, f = toy()
    roll, _ = e.imposed_series(model, data, f, (1, 0, 0))
    assert np.allclose(roll['L'], 0, atol=1e-9) and np.allclose(roll['R'], 0, atol=1e-9)
    model, data, f = toy(tilt=.05)  # a3 tilted anteriorly: level d != 0, still mirror-equal
    assert f.drive(data, 'L')['d'] == pytest.approx(f.drive(data, 'R')['d'])
    assert f.drive(data, 'L')['d'] != pytest.approx(0, abs=1e-3)


def test_zone_rates_one_sided_and_flip():
    assert e.zone_rates(.5, 'G1') == {'C': 60., 'E': 0.}
    assert e.zone_rates(-.25, 'G1') == {'C': 0., 'E': 30.}
    assert e.zone_rates(-.25, 'G1_FLIP') == {'E': 0., 'C': 30.}
    assert e.zone_rates(1., 'G1')['C'] == e.MAX_RATE_HZ


def _inputs():
    rest = {s: dict(d=-.1, r_perp_norm=.05, t_dot_x_head=.9, n_head=[0, 0, -1], t_head=[1, 0, 0]) for s in 'LR'}
    grid = [np.sin(np.radians(g)) - .1 for g in e.GRID_DEG]
    ids = {k: [1, 2] for k in e.SETS}
    return rest, {s: list(grid) for s in 'LR'}, {s: [0.]*len(grid) for s in 'LR'}, ids


def test_evaluate_boundaries():
    rest, pitch, roll, ids = _inputs()
    ok = e.evaluate(rest, pitch, roll, .999, 9.8, ids, ids, True)
    assert ok['status'] == 'ENCODER_READY'
    assert ok['rest_rates_hz']['G1'] == {'C_left': 0., 'E_left': pytest.approx(12.), 'C_right': 0., 'E_right': pytest.approx(12.)}
    bad = {s: dict(rest[s], t_dot_x_head=.69) for s in 'LR'}
    assert e.evaluate(bad, pitch, roll, .999, 9.8, ids, ids, True)['status'] == 'INCONCLUSIVE'
    assert e.evaluate(rest, pitch, roll, .98, 9.8, ids, ids, True)['status'] == 'INCONCLUSIVE'
    assert e.evaluate(rest, pitch, roll, .999, 9.8, ids, dict(ids, C_left=[1]), True)['checks']['B1_identity'] is False
    assert e.evaluate(rest, pitch, roll, .999, 9.8, ids, ids, False)['status'] == 'NOT_READY'
    off = dict(pitch, R=[v + .051 for v in pitch['R']])
    assert e.evaluate(rest, off, roll, .999, 9.8, ids, ids, True)['checks']['B3_mirror'] is False
    edge = dict(pitch, R=[v + .049 for v in pitch['R']])
    assert e.evaluate(rest, edge, roll, .999, 9.8, ids, ids, True)['checks']['B3_mirror'] is True
    flat = {s: [0.]*len(e.GRID_DEG) for s in 'LR'}
    assert e.evaluate(rest, flat, roll, .999, 9.8, ids, ids, True)['checks']['B4_pitch_response'] is False
    big = dict(roll, L=[1.01] + roll['L'][1:])
    assert e.evaluate(rest, pitch, big, .999, 9.8, ids, ids, True)['checks']['B2_bounded'] is False


def test_encoder_interface_drives_every_set():
    model, data, f = toy(tilt=.05)
    enc = e.AntennalGravityEncoder(f, {k: [i] for i, k in enumerate(e.SETS)}, 'G1')
    out = enc.encode(data)
    calls = []

    class Brain:
        def set_external_drive(self, idx, hz):
            calls.append((tuple(idx), hz))
    enc.apply(Brain(), out)
    assert len(calls) == 4 and all(np.isfinite(h) and h >= 0 for _, h in calls)
    assert sum(out[k]['rate_hz'] > 0 for k in e.SETS) == 2  # one zone per side
    with pytest.raises(ValueError):
        e.AntennalGravityEncoder(f, {}, 'G1')
