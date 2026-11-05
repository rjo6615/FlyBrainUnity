"""Antennal gravity Step C2: Shapley attribution of the live JO operating point.

Geometry replay only: the recorded qpos of the 36 Step C seed arms are put through
mj_forward in the Step B runtime model, and the change of the JO drive d from stored
state 0 is split exactly over six factors (root orientation, neck, a2, a3, arista,
gravity). No CNS, no physics stepping; the encoder and Step C labels are unchanged.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from . import antennal_gravity_encoder as ge

SCHEMA = 'jo-operating-point-result-v1'
PROTOCOL = 'docs/evidence/jo-operating-point-v1/protocol.json'
PROTOCOL_SHA256 = '1527f2fc3a5bec800fbe14667ed98f65d3fa78bf89554ef97307e0e10fee903f'
REPORT = 'docs/evidence/antennal-gravity-live-v1/run/report.json'
REPORT_SHA256 = '515f66ddf5deb218b8d324dd71d21ac5058d0d640761b93395ae8960db716982'
STEP_B_RESULT = 'docs/evidence/antennal-gravity-encoder-v1/run/result.json'
STEP_B_SHA256 = '35ff3da49662c4e417149078d85e928ecab4fdb7bbb753a13919ef8a11ad710f'

FACTORS = ('ROOT', 'NECK', 'A2', 'A3', 'ARISTA', 'GRAVITY')
N = len(FACTORS)
_TRIPLE = ('_yaw', '', '_roll')
JOINTS = {'NECK': ['joint_Head' + x for x in _TRIPLE],
          'A2': [f'joint_{s}Pedicel{x}' for s in 'LR' for x in _TRIPLE],
          'A3': [f'joint_{s}Funiculus{x}' for s in 'LR' for x in _TRIPLE],
          'ARISTA': [f'joint_{s}Arista{x}' for s in 'LR' for x in _TRIPLE]}
ADDR = {'ROOT': [3, 4, 5, 6], 'NECK': [73, 74, 75], 'A2': [76, 77, 78, 85, 86, 87],
        'A3': [79, 80, 81, 88, 89, 90], 'ARISTA': [82, 83, 84, 91, 92, 93]}
G0 = (0., 0., -9810.)
STRIDE, TILT_STATE, PRE_STATE = 5, 5005, 5005
WIN_STATES = tuple(range(5200, 20001, 50))
TYPES, TILTS, SEEDS = ('OFF', 'G1', 'FLIP'), ('UP', 'DOWN'), (13, 14, 15, 16, 17, 18)
ARMS = tuple(f'{t}_{tilt}_{s}' for s in SEEDS for t in TYPES for tilt in TILTS)
SIDES = ('L', 'R')
J2_TOL, J3_TOL, J4_TOL = 1e-9, 1e-4, 1e-9
DRIFT_MIN, SHARE_MIN, SIGN_FRAC = .01, .5, .9
WEIGHTS = [math.factorial(k)*math.factorial(N - k - 1)/math.factorial(N) for k in range(N)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol():
    if sha(PROTOCOL) != PROTOCOL_SHA256:
        raise RuntimeError('protocol hash mismatch')
    return json.loads(Path(PROTOCOL).read_text(encoding='utf-8'))


# ---- exact Shapley ---------------------------------------------------------------------

def shapley(values):
    """values[mask] (mask bit i = factor i at target) -> phi (N, ...), exact."""
    values = np.asarray(values, float)
    phi = np.zeros((N,) + values.shape[1:])
    for i in range(N):
        bit = 1 << i
        for mask in range(1 << N):
            if not mask & bit:
                phi[i] += WEIGHTS[bin(mask).count('1')]*(values[mask | bit] - values[mask])
    return phi


def resolve(model):
    """Exact joint-name resolution of the factor qpos addresses."""
    import mujoco
    names = {}
    for j in range(model.njnt):
        n = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j)
        if n:
            names.setdefault(n.split('/')[-1], []).append(int(model.jnt_qposadr[j]))
    found = {k: [names.get(n, [None, None])[0] if len(names.get(n, [])) == 1 else None for n in v]
             for k, v in JOINTS.items()}
    free = [int(model.jnt_qposadr[j]) for j in range(model.njnt) if model.jnt_type[j] == mujoco.mjtJoint.mjJNT_FREE]
    found['ROOT'] = [free[0] + 3 + i for i in range(4)] if len(free) == 1 else [None]
    return found, all(found[k] == ADDR[k] for k in ADDR)


class Replay:
    """d per side for a given qpos and gravity, through mj_forward on a separate MjData."""

    def __init__(self, model):
        import mujoco
        self.mujoco, self.model = mujoco, model
        self.data = mujoco.MjData(model)
        self.frames = ge.AntennaFrames(model)
        self.count = 0

    def d(self, qpos, gravity):
        self.model.opt.gravity[:] = gravity
        self.data.qpos[:] = qpos
        self.mujoco.mj_forward(self.model, self.data)
        self.count += 1
        return np.array([self.frames.drive(self.data, s)['d'] for s in SIDES])

    def subsets(self, ref, tgt):
        """v(mask) for all 64 masks; ref/tgt = (qpos, gravity); non-factor qpos at target."""
        (rq, rg), (tq, tg) = ref, tgt
        rq, tq = np.asarray(rq, float), np.asarray(tq, float)
        out = []
        for mask in range(1 << N):
            q = tq.copy()
            for i, f in enumerate(FACTORS[:-1]):
                if not mask & (1 << i):
                    q[ADDR[f]] = rq[ADDR[f]]
            out.append(self.d(q, tg if mask & (1 << (N - 1)) else rg))
        return np.array(out)

    def decompose(self, ref, tgt):
        v = self.subsets(ref, tgt)
        phi, total = shapley(v), v[-1] - v[0]
        return phi, total, float(np.max(np.abs(phi.sum(0) - total)))


# ---- per arm ---------------------------------------------------------------------------

def tick_gravity(arm, k):
    return tuple(arm['tilt_event']['gravity']) if STRIDE*k >= arm['initial']['tilt_state'] else G0


def state(arm, i):
    s = arm['samples'][i]
    return s['qpos'], tuple(s['gravity'])


def joint_deg(qpos, f):
    return [math.degrees(qpos[a]) for a in ADDR[f]]


def analyze_arm(arm, replay, win_states=WIN_STATES, rest=None):
    j2 = 0.
    for k, tick in enumerate(arm['neural'], 1):
        d = replay.d(arm['samples'][STRIDE*k]['qpos'], tick_gravity(arm, k))
        j2 = max(j2, abs(d[0] - tick['jo_d']['L']), abs(d[1] - tick['jo_d']['R']))
    ref = (arm['samples'][0]['qpos'], G0)
    d0 = replay.d(*ref)
    j3 = None if rest is None else float(np.max(np.abs(d0 - np.asarray(rest))))
    phi_pre, tot_pre, e_pre = replay.decompose(ref, state(arm, PRE_STATE))
    phis, tots, errs = zip(*(replay.decompose(ref, state(arm, i)) for i in win_states))
    from ..live import antennal_gravity_live as live

    def desc(idx):
        qs = [arm['samples'][i] for i in idx]
        return dict({f: np.mean([joint_deg(s['qpos'], f) for s in qs], 0).round(4).tolist() for f in ('NECK', 'A2', 'A3')},
                    body_pitch_roll_deg=np.mean([live.body_angles(s)[1:] for s in qs], 0).round(4).tolist(),
                    d=np.mean([replay.d(s['qpos'], tuple(s['gravity'])) for s in qs], 0).round(6).tolist())
    return dict(j2=j2, j3=j3, j4=max(e_pre, max(errs)), d0=d0.tolist(),
                pre=dict(phi=phi_pre.tolist(), total=tot_pre.tolist()),
                win=dict(phi=np.mean(phis, 0).tolist(), total=np.mean(tots, 0).tolist()),
                describe=dict(state0=desc([0]), pre=desc([PRE_STATE]), window=desc(win_states)))


def contrast(up, down, replay, win_states=WIN_STATES):
    """Decomposition of d(DOWN state) - d(UP state), UP state as reference, averaged over states."""
    phis, tots, errs = zip(*(replay.decompose(state(up, i), state(down, i)) for i in win_states))
    return dict(phi=np.mean(phis, 0).tolist(), total=np.mean(tots, 0).tolist(), j4=max(errs))


# ---- labels ----------------------------------------------------------------------------

def label(phi, total):
    """phi (arms, N), total (arms,) for one side and group."""
    phi, total = np.asarray(phi, float), np.asarray(total, float)
    med_total = float(np.median(total))
    stats = dict(median_total=med_total, total_range=[float(total.min()), float(total.max())])
    safe = np.where(total == 0, np.nan, total)
    share = phi/safe[:, None]
    stats['factors'] = {}
    for i, f in enumerate(FACTORS):
        sh = share[:, i]
        stats['factors'][f] = dict(
            median_phi=float(np.median(phi[:, i])), phi_range=[float(phi[:, i].min()), float(phi[:, i].max())],
            median_share=float(np.nanmedian(sh)) if np.isfinite(sh).any() else 0.,
            sign_fraction=float(np.mean(np.sign(phi[:, i]) == np.sign(total))))
    if abs(med_total) < DRIFT_MIN:
        return 'NO_MATERIAL_DRIFT', stats
    ok = [(v['median_share'], f) for f, v in stats['factors'].items()
          if v['median_share'] >= SHARE_MIN and v['sign_fraction'] >= SIGN_FRAC]
    return ('DOMINANT_' + max(ok)[1]) if ok else 'MIXED', stats


def groups(records):
    return {'Q1': [(r, 'pre') for r in records.values()],
            'Q2_UP': [(r, 'win') for n, r in records.items() if n.split('_')[1] == 'UP'],
            'Q2_DOWN': [(r, 'win') for n, r in records.items() if n.split('_')[1] == 'DOWN']}


def labels_from(records):
    labels, stats = {}, {}
    for g, items in groups(records).items():
        for si, side in enumerate(SIDES):
            phi = [[r[key]['phi'][i][si] for i in range(N)] for r, key in items]
            tot = [r[key]['total'][si] for r, key in items]
            labels[f'{g}_{side}'], stats[f'{g}_{side}'] = label(phi, tot)
    return labels, stats


def by_type(records):
    out = {}
    for t in TYPES:
        sub = {n: r for n, r in records.items() if n.startswith(t + '_')}
        out[t] = {g: {side: {f: float(np.median([r[key]['phi'][i][si] for r, key in items]))
                             for i, f in enumerate(FACTORS)} | {'total': float(np.median([r[key]['total'][si] for r, key in items]))}
                      for si, side in enumerate(SIDES)} for g, items in groups(sub).items()}
    return out


def evaluate(records, contrasts, j1, addresses_ok):
    checks = dict(J1_inputs=bool(j1), factor_addresses=bool(addresses_ok),
                  J2_replay=bool(records) and all(r['j2'] <= J2_TOL for r in records.values()),
                  J3_reference=bool(records) and all(r['j3'] is not None and r['j3'] <= J3_TOL for r in records.values()),
                  J4_additivity=bool(records) and all(r['j4'] <= J4_TOL for r in records.values())
                  and all(c['j4'] <= J4_TOL for c in contrasts.values()))
    out = dict(checks=checks, max_errors=dict(
        J2=max((r['j2'] for r in records.values()), default=None),
        J3=max((r['j3'] for r in records.values() if r['j3'] is not None), default=None),
        J4=max([r['j4'] for r in records.values()] + [c['j4'] for c in contrasts.values()], default=None)))
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', **out)
    labels, stats = labels_from(records)
    return dict(status='INTEGRITY_ACCEPTED', labels=labels, statistics=stats, by_type=by_type(records), **out)


# ---- run -------------------------------------------------------------------------------

def load_arm(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return json.load(f)


def run(arms_dir, smoke=False):
    import gc
    import flygym
    from . import _windows_m7d_corrected_spontaneous_adapter as adapter
    report = json.loads(Path(REPORT).read_text(encoding='utf-8'))
    if sha(STEP_B_RESULT) != STEP_B_SHA256:
        raise RuntimeError('Step B result hash mismatch')
    rest = [json.loads(Path(STEP_B_RESULT).read_text(encoding='utf-8'))['rest'][s]['d'] for s in SIDES]
    names = ARMS[:2] if smoke else ARMS
    arm_sha = {n: sha(Path(arms_dir)/f'{n}.json.gz') if (Path(arms_dir)/f'{n}.json.gz').exists() else None
               for n in names}
    j1 = sha(REPORT) == REPORT_SHA256 and all(arm_sha[n] == report['arm_sha256'][n] for n in names)
    sim, physics, *_ = adapter._runtime(flygym, None)
    try:
        model = physics.model.ptr
        found, addresses_ok = resolve(model)
        replay = Replay(model)
        win = WIN_STATES[:2] if smoke else WIN_STATES
        records, contrasts = {}, {}
        for s in (SEEDS[:1] if smoke else SEEDS):
            for t in TYPES[:1] if smoke else TYPES:
                pair = {}
                for tilt in TILTS:
                    n = f'{t}_{tilt}_{s}'
                    arm = load_arm(Path(arms_dir)/f'{n}.json.gz')
                    if smoke:
                        arm['neural'] = arm['neural'][:4]
                    records[n] = analyze_arm(arm, replay, win, rest)
                    pair[tilt] = arm
                    print(json.dumps(dict(arm=n, j2=records[n]['j2'], j3=records[n]['j3'], j4=records[n]['j4'])), flush=True)
                contrasts[f'{t}_{s}'] = contrast(pair['UP'], pair['DOWN'], replay, win)
                del pair, arm
                gc.collect()
    finally:
        sim.close()
    e = evaluate(records, contrasts, j1, addresses_ok)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, smoke=smoke, report_sha256=REPORT_SHA256,
                arm_sha256=arm_sha, resolved_addresses=found, step_b_rest=rest, mj_forward_calls=replay.count,
                evaluation=e, records=records, tilt_contrasts=contrasts,
                interpretation_limits=None if smoke else protocol()['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arms', type=Path, required=True, help='folder with the Step C raw .json.gz arms')
    parser.add_argument('--smoke', action='store_true', help='plumbing only (2 arms, 4 ticks, 2 window states)')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.smoke:
        protocol()
    result = run(args.arms, smoke=args.smoke)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=1)
    print(json.dumps(dict(status=result['evaluation']['status'], checks=result['evaluation']['checks'],
                          labels=result['evaluation'].get('labels')), indent=1))


if __name__ == '__main__':
    main()
