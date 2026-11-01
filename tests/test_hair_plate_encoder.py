"""Synthetic checks for the hair-plate encoder; a toy MuJoCo body, no FlyGym, CNS or physics run."""
import numpy as np
import pytest

from malecns_backend.embodiment import hair_plate_encoder as h

mujoco = pytest.importorskip('mujoco')


def toy():
    legs = ''.join(f'''
      <body name="{leg}Coxa" pos="0 {0.1 if leg[0] == 'L' else -0.1} 0">
        <joint name="joint_{leg}Coxa" type="hinge" axis="0 1 0"/>
        <joint name="joint_{leg}Coxa_roll" type="hinge" axis="0 0 1"/>
        <joint name="joint_{leg}Coxa_yaw" type="hinge" axis="1 0 0"/>
        <geom type="sphere" size=".01" mass=".001"/>
        <body name="{leg}Femur" pos="0 0 -1"><geom type="sphere" size=".01" mass=".001"/></body>
      </body>''' for leg in h.LEGS)
    xml = f'''<mujoco><worldbody><body name="Thorax"><freejoint/><geom type="sphere" size=".1"/>
      <body name="Head" pos="1 0 0"><geom type="sphere" size=".05"/></body>{legs}</body></worldbody></mujoco>'''
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_kinematics(model, data)
    return model, data


def test_rate_is_one_sided_tonic_and_saturates():
    assert h.rate(.1, .2, .6) == 0 and h.rate(.4, .2, .6) == pytest.approx(60) and h.rate(.9, .2, .6) == 120
    with pytest.raises(ValueError):
        h.rate(0, .5, .5)


def test_forward_component_uses_thorax_frame_and_coxa_axis():
    model, data = toy()
    frames = h.BodyFrames(model)
    assert frames.anterior_fraction(data) == pytest.approx(1)
    assert frames.forward(data, 'LM') == pytest.approx(0, abs=1e-9)  # pointing straight down
    data.qpos[frames.qpos['LM']['Coxa']] = -0.5  # rotate about +y: tip moves toward -x? check sign by geometry
    mujoco.mj_kinematics(model, data)
    assert frames.forward(data, 'LM') == pytest.approx(np.sin(0.5), abs=1e-6)
    # rotating the whole thorax does not change the body-frame measure
    data.qpos[3:7] = [np.cos(.3), 0, 0, np.sin(.3)]
    mujoco.mj_kinematics(model, data)
    assert frames.forward(data, 'LM') == pytest.approx(np.sin(0.5), abs=1e-6)


def test_recorded_forward_restores_state_and_axis_directions():
    model, data = toy()
    frames = h.BodyFrames(model)
    kin = {f'joint_{leg}{j}': np.zeros(3) for leg in h.LEGS for j in h.COXA_JOINTS}
    kin['joint_LFCoxa'] = np.array([0, -.5, -1.])
    before = data.qpos.copy()
    rec = h.recorded_forward(model, data, frames, kin)
    assert np.allclose(data.qpos, before)
    assert rec['LF'][0] == pytest.approx(0, abs=1e-9) and rec['LF'][2] == pytest.approx(np.sin(1), abs=1e-6)
    axes = h.axis_directions(model, data, frames)
    assert axes['LF']['Coxa'] < 0 and abs(axes['LF']['Coxa_yaw']) < 1e-9


def test_evaluate_ready_and_failures():
    rng = np.random.default_rng(0)
    recorded = {leg: list(rng.uniform(-.2, .6, 45)) for leg in h.LEGS}
    pops = {leg: {1, 2} for leg in h.LEGS}
    counts = {leg: 2 for leg in h.LEGS}
    rest = {leg: 0. for leg in h.LEGS}
    r = h.evaluate(recorded, rest, {}, pops, counts, .9997)
    assert r['status'] == 'ENCODER_READY' and all(.05 <= v <= .15 for v in r['recorded_active_fraction'].values())
    assert h.evaluate(recorded, rest, {}, pops, dict(counts, LF=3), .9997)['status'] == 'NOT_READY'
    assert h.evaluate(recorded, rest, {}, pops, counts, .5)['status'] == 'INCONCLUSIVE'
    flat = dict(recorded, LF=[.1]*45)
    assert h.evaluate(flat, rest, {}, pops, counts, .9997)['status'] == 'NOT_READY'


class Brain:
    def __init__(self): self.calls = []
    def set_external_drive(self, idx, rate): self.calls.append((list(idx), rate))


def test_encoder_applies_per_leg_rates_to_its_populations():
    model, data = toy()
    frames = h.BodyFrames(model)
    tuning = {leg: dict(theta=.1, f_max=.5) for leg in h.LEGS}
    enc = h.HairPlateEncoder(frames, tuning, {leg: {i + 10*k for i in range(2)} for k, leg in enumerate(h.LEGS)})
    data.qpos[frames.qpos['RH']['Coxa']] = -0.7  # sin(0.7) > 0.5 saturation
    mujoco.mj_kinematics(model, data)
    out = enc.encode(data)
    assert out['RH']['rate_hz'] == 120 and out['LF']['rate_hz'] == 0
    b = Brain(); enc.apply(b, out)
    assert b.calls[-1] == ([50, 51], 120) and len(b.calls) == 6
