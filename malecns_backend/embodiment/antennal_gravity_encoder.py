"""Antennal gravity Step B: kinematic JO zone C/E encoder (static validation only).

Preregistered in docs/evidence/antennal-gravity-encoder-v1/protocol.json. Geometry only:
the drive d is gravity projected on the arista's motion tangent for a3 rotation about its
geometric long axis. No CNS, no physics stepping, no masses, no antenna joint angles.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/antennal-gravity-encoder-v1/protocol.json'
PROTOCOL_SHA256 = '0e97fe33a26857605327e91b9d4527bc1011117e6e7a445db95fc4f8b0b40917'
STEP_A_RESULT = 'docs/evidence/antennal-gravity-identity-v1/run/result.json'
STEP_A_SHA256 = '5b735be5682361f4c708254bb7e65772ef08998fb1365329e3e64b3861104f8d'
SCHEMA = 'antennal-gravity-encoder-result-v1'
SIDES = {'L': 'left', 'R': 'right'}
SETS = ('C_left', 'C_right', 'E_left', 'E_right')
MAX_RATE_HZ = 120.
ANTERIOR_MIN = .99
TANGENT_X_MIN = .7
MIRROR_TOL = .05
GRID_DEG = tuple(range(-30, 31, 5))
ASSIGNMENTS = {'G1': {'plus': 'C', 'minus': 'E'}, 'G1_FLIP': {'plus': 'E', 'minus': 'C'}}
LR_LABEL = 'left/right synapse asymmetry (C 5.31x, E 2.54x), as reconstructed'


def _sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def protocol():
    if _sha(PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads((ROOT/PROTOCOL).read_text(encoding='utf-8'))


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if not n > 0:
        raise ValueError('zero-length vector')
    return v/n


def zone_rates(d, assignment):
    """Per-zone tonic one-sided rate (Hz) for drive d under G1 or G1_FLIP."""
    a = ASSIGNMENTS[assignment]
    return {a['plus']: float(MAX_RATE_HZ*max(d, 0.)), a['minus']: float(MAX_RATE_HZ*max(-d, 0.))}


class AntennaFrames:
    """Exact Thorax/Head/Funiculus/Arista bodies and the root free joint of a MuJoCo model."""

    def __init__(self, model):
        import mujoco
        self.mujoco, self.model = mujoco, model
        names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(model.nbody)]

        def unique(suffix):
            hits = [i for i, n in enumerate(names) if n and n.split('/')[-1] == suffix]
            if len(hits) != 1:
                raise ValueError('exact unique model element required: ' + suffix)
            return hits[0]
        self.thorax, self.head = unique('Thorax'), unique('Head')
        self.funiculus = {s: unique(s + 'Funiculus') for s in SIDES}
        self.arista = {s: unique(s + 'Arista') for s in SIDES}
        free = [j for j in range(model.njnt) if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE]
        if len(free) != 1:
            raise ValueError('exactly one free joint required')
        self.root_q = int(model.jnt_qposadr[free[0]]) + 3

    def gravity(self):
        return np.asarray(self.model.opt.gravity, float)

    def anterior_fraction(self, data):
        r = np.asarray(data.xmat[self.thorax]).reshape(3, 3)
        v = r.T @ (np.asarray(data.xpos[self.head]) - np.asarray(data.xpos[self.thorax]))
        return float(v[0]/np.linalg.norm(v))

    def drive(self, data, side):
        a = np.asarray(data.xpos[self.funiculus[side]], float)
        n = unit(np.asarray(data.xipos[self.funiculus[side]], float) - a)
        p = np.asarray(data.xipos[self.arista[side]], float) - a
        r_perp = p - (p @ n)*n
        head = np.asarray(data.xmat[self.head]).reshape(3, 3)
        t = unit(np.cross(n, r_perp))
        if t @ head[:, 0] < 0:
            t = -t
        d = float(unit(self.gravity()) @ t)
        return dict(d=d, r_perp_norm=float(np.linalg.norm(r_perp)), t_dot_x_head=float(t @ head[:, 0]),
                    n_head=(head.T @ n).tolist(), t_head=(head.T @ t).tolist())


def _quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2,
                     w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2])


def axis_quat(axis, deg):
    h = np.radians(deg)/2
    return np.concatenate([[np.cos(h)], np.sin(h)*unit(axis)])


def imposed_series(model, data, frames, axis, grid=GRID_DEG):
    """d per side and Head x-axis world z under whole-body world rotations; restores qpos."""
    mj = frames.mujoco
    saved = np.array(data.qpos, copy=True)
    q0 = saved[frames.root_q:frames.root_q + 4].copy()
    out = {s: [] for s in SIDES}
    head_x_z = []
    try:
        for deg in grid:
            data.qpos[frames.root_q:frames.root_q + 4] = _quat_mul(axis_quat(axis, deg), q0)
            mj.mj_forward(model, data)
            for s in SIDES:
                out[s].append(frames.drive(data, s)['d'])
            head_x_z.append(float(np.asarray(data.xmat[frames.head]).reshape(3, 3)[2, 0]))
    finally:
        data.qpos[:] = saved
        mj.mj_forward(model, data)
    return out, head_x_z


class AntennalGravityEncoder:
    """Step C-ready encoder: encode(data) -> per-set rates; apply(brain, encoded)."""
    provenance = 'MODELED_TRANSDUCTION'

    def __init__(self, frames, populations, assignment):
        if assignment not in ASSIGNMENTS or set(populations) != set(SETS):
            raise ValueError('G1/G1_FLIP and all four C/E sets required')
        self.frames, self.assignment = frames, assignment
        self.populations = {k: np.asarray(sorted(v), dtype=np.intp) for k, v in populations.items()}

    def encode(self, data):
        out = {}
        for s, side in SIDES.items():
            d = self.frames.drive(data, s)['d']
            for zone, hz in zone_rates(d, self.assignment).items():
                out[f'{zone}_{side}'] = dict(d=d, rate_hz=hz)
        return out

    def apply(self, brain, encoded):
        for k in SETS:
            brain.set_external_drive(self.populations[k], encoded[k]['rate_hz'])


def _monotonic(seq):
    diff = np.diff(np.asarray(seq, float))
    return bool(len(diff) and (np.all(diff > 0) or np.all(diff < 0)))


def _slope(seq, grid=GRID_DEG):
    i = list(grid).index(0)
    return float((seq[i + 1] - seq[i - 1])/np.radians(grid[i + 1] - grid[i - 1]))


def evaluate(rest, pitch, roll, anterior, gravity_norm, body_ids, step_a_ids, matched):
    """rest {side: drive dict}; pitch/roll {side: [d]} over GRID_DEG."""
    b0 = (anterior > ANTERIOR_MIN and gravity_norm > 0 and
          all(rest[s]['r_perp_norm'] > 0 and abs(rest[s]['t_dot_x_head']) >= TANGENT_X_MIN for s in SIDES))
    b1 = matched and all(sorted(body_ids[k]) == sorted(step_a_ids[k]) for k in SETS)
    every = [rest[s]['d'] for s in SIDES] + [v for g in (pitch, roll) for s in SIDES for v in g[s]]
    b2 = all(np.isfinite(v) and abs(v) <= 1 for v in every)
    b3 = all(abs(a - b) <= MIRROR_TOL for a, b in zip(pitch['L'], pitch['R']))
    b4 = all(_monotonic(pitch[s]) for s in SIDES)
    checks = dict(B0_frame=b0, B1_identity=b1, B2_bounded=b2, B3_mirror=b3, B4_pitch_response=b4)
    status = 'INCONCLUSIVE' if not b0 else 'ENCODER_READY' if all(checks.values()) else 'NOT_READY'
    rest_rates = {a: {f'{z}_{SIDES[s]}': hz for s in SIDES for z, hz in zone_rates(rest[s]['d'], a).items()}
                  for a in ASSIGNMENTS}
    return dict(
        status=status, checks=checks, rest=rest, rest_rates_hz=rest_rates, rest_rates_label=LR_LABEL,
        pitch_d=pitch, roll_d=roll, grid_deg=list(GRID_DEG),
        slope_per_rad=dict(pitch={s: _slope(pitch[s]) for s in SIDES}, roll={s: _slope(roll[s]) for s in SIDES}),
        roll_left_minus_right=[a - b for a, b in zip(roll['L'], roll['R'])],
        counts={k: len(body_ids[k]) for k in SETS})


def populations_and_step_a():
    """Step A's population rule over its hash-locked annotations, and Step A's recorded sets."""
    import pandas as pd
    from . import antennal_gravity_identity as a
    spec = a.protocol()
    src = spec['sources']['annotations']
    if a.sha(src['path']) != src['sha256'] or _sha(STEP_A_RESULT) != STEP_A_SHA256:
        raise ValueError('Step A source identity mismatch')
    pops = a.populations(pd.read_feather(ROOT/src['path']))
    body_ids = {f'{z}_{s}': pops.get((z, s), []) for z in a.ZONES for s in SIDES.values()}
    step_a = json.loads((ROOT/STEP_A_RESULT).read_text(encoding='utf-8'))['body_ids']
    return body_ids, step_a


def run(cache):
    spec = protocol()
    import flygym
    from ..cache import load_cache
    from . import _windows_m7d_corrected_spontaneous_adapter as adapter
    body_ids, step_a = populations_and_step_a()
    index = {int(k): int(v) for k, v in load_cache(cache).body_id_to_index.items()}
    matched = all(index.get(b) is not None for k in SETS for b in body_ids[k])
    dense = {k: sorted(int(index[b]) for b in body_ids[k] if index.get(b) is not None) for k in SETS}
    sim, physics, obs, _, _ = adapter._runtime(flygym, None)
    try:
        model, data = physics.model.ptr, physics.data.ptr
        frames = AntennaFrames(model)
        anterior = frames.anterior_fraction(data)
        rest = {s: frames.drive(data, s) for s in SIDES}
        pitch, pitch_head = imposed_series(model, data, frames, (0, 1, 0))
        roll, _ = imposed_series(model, data, frames, (1, 0, 0))
        gravity = frames.gravity().tolist()
        AntennalGravityEncoder(frames, dense, 'G1').encode(data)  # interface smoke on the live state
    finally:
        sim.close()
    result = evaluate(rest, pitch, roll, anterior, float(np.linalg.norm(gravity)), body_ids, step_a, matched)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, anterior_fraction=anterior, gravity=gravity,
                pitch_head_x_world_z=pitch_head, dense_indices=dense, body_ids=body_ids, **result,
                left_right_rule=spec['left_right_rule'], interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run(args.cache)
        stream.write((json.dumps(result, indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'counts', 'rest_rates_hz', 'slope_per_rad')},
                     indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
