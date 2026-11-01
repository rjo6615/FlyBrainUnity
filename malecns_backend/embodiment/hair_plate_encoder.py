"""Modeled CxHP8-like (SNpp45) coxa forward-limit encoder, Step B (static validation only).

Preregistered in docs/evidence/hair-plate-encoder-v1/protocol.json. Tuning comes from
recorded real-fly walking kinematics shipped with FlyGym, never from simulation outcomes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import pickle

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/hair-plate-encoder-v1/protocol.json'
PROTOCOL_SHA256 = '224090d82632d16f62134914d9f53d8c7379ffd525159eaae49a0ba4653c6d5d'
SCHEMA = 'hair-plate-encoder-result-v1'
LEGS = ('LF', 'LM', 'LH', 'RF', 'RM', 'RH')
SEGMENT = {'F': 'T1', 'M': 'T2', 'H': 'T3'}
SIDE = {'L': 'left', 'R': 'right'}
COXA_JOINTS = ('Coxa', 'Coxa_roll', 'Coxa_yaw')
MAX_RATE_HZ = 120.


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def leg_key(leg):
    return SEGMENT[leg[1]], SIDE[leg[0]]


def rate(f, theta, f_max):
    """Tonic one-sided limit tuning in Hz."""
    if not theta < f_max:
        raise ValueError('threshold must be below saturation')
    return float(MAX_RATE_HZ * np.clip((f - theta)/(f_max - theta), 0., 1.))


class BodyFrames:
    """Exact Thorax/Head/Coxa/Femur body and coxa joint addresses in a MuJoCo model."""

    def __init__(self, model):
        import mujoco
        self.mujoco = mujoco
        names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(model.nbody)]
        joints = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(model.njnt)]

        def unique(pool, suffix):
            hits = [i for i, n in enumerate(pool) if n and n.split('/')[-1] == suffix]
            if len(hits) != 1:
                raise ValueError('exact unique model element required: ' + suffix)
            return hits[0]
        self.thorax, self.head = unique(names, 'Thorax'), unique(names, 'Head')
        self.coxa = {leg: unique(names, leg + 'Coxa') for leg in LEGS}
        self.femur = {leg: unique(names, leg + 'Femur') for leg in LEGS}
        self.qpos = {leg: {j: int(model.jnt_qposadr[unique(joints, f'joint_{leg}{j}')]) for j in COXA_JOINTS}
                     for leg in LEGS}

    def anterior_fraction(self, data):
        r = np.asarray(data.xmat[self.thorax]).reshape(3, 3)
        v = r.T @ (np.asarray(data.xpos[self.head]) - np.asarray(data.xpos[self.thorax]))
        return float(v[0]/np.linalg.norm(v))

    def forward(self, data, leg):
        r = np.asarray(data.xmat[self.thorax]).reshape(3, 3)
        v = r.T @ (np.asarray(data.xpos[self.femur[leg]]) - np.asarray(data.xpos[self.coxa[leg]]))
        return float(v[0]/np.linalg.norm(v))


def recorded_forward(model, data, frames, kinematics):
    """f per leg over recorded poses; restores qpos afterwards."""
    saved = np.array(data.qpos, copy=True)
    out = {}
    try:
        for leg in LEGS:
            series = [np.asarray(kinematics[f'joint_{leg}{j}'], float) for j in COXA_JOINTS]
            values = []
            for k in range(len(series[0])):
                data.qpos[:] = saved
                for j, s in zip(COXA_JOINTS, series):
                    data.qpos[frames.qpos[leg][j]] = s[k]
                frames.mujoco.mj_kinematics(model, data)
                values.append(frames.forward(data, leg))
            out[leg] = values
    finally:
        data.qpos[:] = saved
        frames.mujoco.mj_kinematics(model, data)
    return out


def axis_directions(model, data, frames, step=.1):
    saved = np.array(data.qpos, copy=True)
    out = {}
    try:
        for leg in LEGS:
            frames.mujoco.mj_kinematics(model, data)
            base = frames.forward(data, leg)
            out[leg] = {}
            for j in COXA_JOINTS:
                data.qpos[:] = saved
                data.qpos[frames.qpos[leg][j]] += step
                frames.mujoco.mj_kinematics(model, data)
                out[leg][j] = frames.forward(data, leg) - base
    finally:
        data.qpos[:] = saved
        frames.mujoco.mj_kinematics(model, data)
    return out


def tuning_from(recorded):
    return {leg: dict(theta=float(np.percentile(v, 90)), f_max=float(np.max(v))) for leg, v in recorded.items()}


class HairPlateEncoder:
    """Physics-measured coxa forwardness -> SNpp45 Poisson rates (MODELED_TRANSDUCTION)."""
    provenance = 'MODELED_TRANSDUCTION'

    def __init__(self, frames, tuning, populations):
        if set(tuning) != set(LEGS) or set(populations) != set(LEGS):
            raise ValueError('all six legs required')
        self.frames, self.tuning = frames, tuning
        self.populations = {leg: np.asarray(sorted(populations[leg]), dtype=np.intp) for leg in LEGS}

    def encode(self, data):
        out = {}
        for leg in LEGS:
            f = self.frames.forward(data, leg)
            t = self.tuning[leg]
            out[leg] = dict(forward=f, rate_hz=rate(f, t['theta'], t['f_max']))
        return out

    def apply(self, brain, encoded):
        for leg in LEGS:
            brain.set_external_drive(self.populations[leg], encoded[leg]['rate_hz'])


def populations_from_annotations(cache):
    """Exactly Step A's SNpp45 sets, keyed by leg name."""
    import pandas as pd
    from ..cache import load_cache
    from . import hair_plate_identity as a
    a.protocol()
    src = a.protocol()['sources']['annotations']
    table = pd.read_feather(ROOT/src['path'])
    sets, _ = a.sensory_sets(table, load_cache(cache).body_id_to_index)
    return {leg: sets[leg_key(leg)] for leg in LEGS}


def kinematics(spec):
    import flygym
    from importlib.metadata import version
    k = spec['basis']['kinematics']
    path = Path(flygym.__file__).parent/'data/behavior/single_steps_untethered.pkl'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != k['sha256'] or version('flygym') != '1.2.1':
        raise ValueError('recorded kinematics identity mismatch')
    return pickle.loads(raw)


def evaluate(recorded, rest, axes, populations, step_a_counts, anterior):
    tuning = tuning_from(recorded)
    checks = dict(
        anterior=anterior > .99,
        S1_identity=all(len(populations[leg]) == step_a_counts[leg] for leg in LEGS),
        S2_tuning_defined=all(t['theta'] < t['f_max'] for t in tuning.values()))
    active = {}
    if checks['S2_tuning_defined']:
        for leg in LEGS:
            t = tuning[leg]
            active[leg] = float(np.mean([rate(f, t['theta'], t['f_max']) > 0 for f in recorded[leg]]))
        grid = np.linspace(-1, 1, 201)
        checks['S3_recorded_activity'] = all(.05 <= v <= .15 for v in active.values())
        checks['S4_monotonic'] = all(np.all(np.diff([rate(g, tuning[l]['theta'], tuning[l]['f_max']) for g in grid]) >= 0)
                                     for l in LEGS)
    else:
        checks.update(S3_recorded_activity=False, S4_monotonic=False)
    rest_rates = {leg: rate(rest[leg], tuning[leg]['theta'], tuning[leg]['f_max']) if checks['S2_tuning_defined'] else None
                  for leg in LEGS}
    checks['S5_rest_pose'] = all(r is not None and np.isfinite(r) for r in rest_rates.values())
    if not checks['anterior']:
        status = 'INCONCLUSIVE'
    else:
        status = 'ENCODER_READY' if all(v for k, v in checks.items() if k.startswith('S')) else 'NOT_READY'
    return dict(status=status, checks=checks, tuning=tuning, recorded_active_fraction=active,
                rest_forward=rest, rest_rate_hz=rest_rates, axis_direction_per_0p1rad=axes,
                recorded_forward_range={l: [float(min(v)), float(max(v))] for l, v in recorded.items()})


def run(cache):
    spec = protocol()
    import flygym
    from . import _windows_m7d_corrected_spontaneous_adapter as adapter
    kin = kinematics(spec)
    step_a = json.loads((ROOT/'docs/evidence/hair-plate-identity-v1/run/result.json').read_text(encoding='utf-8'))
    counts = {leg: step_a['legs'][' '.join(leg_key(leg))]['sensory_neurons'] for leg in LEGS}
    populations = populations_from_annotations(cache)
    sim, physics, obs, _, _ = adapter._runtime(flygym, None)
    try:
        model, data = physics.model.ptr, physics.data.ptr
        frames = BodyFrames(model)
        anterior = frames.anterior_fraction(data)
        rest = {leg: frames.forward(data, leg) for leg in LEGS}
        recorded = recorded_forward(model, data, frames, kin)
        axes = axis_directions(model, data, frames)
    finally:
        sim.close()
    result = evaluate(recorded, rest, axes, populations, counts, anterior)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, anterior_fraction=anterior,
                populations={leg: sorted(int(i) for i in populations[leg]) for leg in LEGS},
                recorded_forward=recorded, **result, interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run(args.cache)
        stream.write((json.dumps(result, indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'tuning', 'rest_rate_hz')}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
