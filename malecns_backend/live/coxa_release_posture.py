"""Released-posture test with the conditional coxa channels (V1).

Preregistered in docs/evidence/coxa-release-posture-v1/protocol.json (design:
docs/COXA_RELEASE_POSTURE_V1.md). Twelve fixed arms (R22/K/KC/KF x CNS seeds 1-3) on
Step C arm R_ON, one fresh process each. R22 is the Step C release (22 rows); K, KC and KF
release the same rows except joint_LFCoxa and joint_LHCoxa (declared variant
ZERO_SELECTED_ROWS_EXCEPT_2). KC/KF add the CONDITIONAL channels (COXA_CONDITIONAL_H1)
through the D3 hypothesis session path. assistance_native and the kernel are unchanged.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from . import assistance_native as mechanical
from . import coxa_admission as ca
from . import coxa_hypothesis_loop as loop
from . import hair_plate_posture as c
from .tactile_boundary import create_session as create_v3_session, native
from ..embodiment import hair_plate_encoder as hp

ROOT = loop.ROOT
PROTOCOL = 'docs/evidence/coxa-release-posture-v1/protocol.json'
PROTOCOL_SHA256 = '166598304d7d39699336f7490f444664a591d3f2f2e1425d50957fa153a0e260'
SCHEMA = 'coxa-release-posture-arm-v1'
LABEL = 'COXA_CONDITIONAL_H1'
KEEP = ca.CANDIDATES  # joint_LFCoxa, joint_LHCoxa
SEEDS = ca.SEEDS
KINDS = {'R22': None, 'K': None, 'KC': 'H1', 'KF': 'H1_FLIP'}
ARMS = tuple(f'{k}_{s}' for s in SEEDS for k in KINDS)
OPERATION = {'R22': 'ZERO_FULL_SELECTED_ROWS', 'K': 'ZERO_SELECTED_ROWS_EXCEPT_2',
             'KC': 'ZERO_SELECTED_ROWS_EXCEPT_2', 'KF': 'ZERO_SELECTED_ROWS_EXCEPT_2'}
BAR_MS, ROLL_DEG = 20., 90.
EVENT_STATE = c.EVENT_STATE


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def split(arm):
    kind, seed = arm.rsplit('_', 1)
    if kind not in KINDS or int(seed) not in SEEDS:
        raise ValueError('unknown arm')
    return kind, int(seed)


# ---- declared release variant ----------------------------------------------------

def released_rows(selected, keep):
    """Selected rows minus the kept coordinates; refuses an unknown or missing keep."""
    names = [r['coordinate'] for r in selected]
    if not set(keep) <= set(names):
        raise ValueError('kept coordinate not in the selected set')
    return [r for r in selected if r['coordinate'] not in keep]


def neutral_except(original, inv, keep):
    """mechanical.neutral_record with the kept rows left at their original values."""
    mechanical.validate_binding(inv, original)
    expected = copy.deepcopy(original)
    ids = [r['actuator_id'] for r in released_rows(mechanical.partition(inv)[1], keep)]
    for name in mechanical.FIELDS:
        values = mechanical.array_values(original, name).copy()
        values[ids] = 0.
        expected['arrays'][name] = mechanical.isolation.encode_nonfinite(values.tolist())
        expected['identity']['model_arrays'][name] = mechanical.array_identity(values)
    expected['sha256'] = mechanical.digest(expected['identity'])
    return expected


def write_rows_except(model, inv, keep):
    ids = [r['actuator_id'] for r in released_rows(mechanical.partition(inv)[1], keep)]
    for name in mechanical.FIELDS:
        getattr(model, name)[ids] = 0.


# ---- adapter -----------------------------------------------------------------------

class Trial(c.Trial):
    """Step C R_ON trial with a declared CNS seed, release variant and channel inventory."""

    def __init__(self, arm):
        kind, seed = split(arm)
        super().__init__('R_ON')
        self.kind, self.seed, self.relarm = kind, seed, arm

    def bind(self, sim, physics, obs):
        super().bind(sim, physics, obs)
        keep = () if self.kind == 'R22' else KEEP
        self.neutral = mechanical.neutral_record(self.original, self.inventory) if not keep \
            else neutral_except(self.original, self.inventory, keep)
        self.released_ids = sorted(r['actuator_id'] for r in released_rows(mechanical.partition(self.inventory)[1], keep))
        self.kept = sorted(keep)

    def capture(self, physics, obs, action):
        c.context.PassiveRecorder.capture(self, physics, obs, action)
        s = self.samples[-1]
        self.samples[-1] = dict(time_s=s['time_s'], qpos=s['qpos'], qvel=s['qvel'],
                                commanded_joints=s['commanded_joints'], telemetry_forces=s['telemetry_forces'])
        index = len(self.samples) - 1
        if index == EVENT_STATE:
            before = mechanical.model_record(physics.model, physics.data)
            if before != self.original:
                raise RuntimeError('model changed before the declared boundary')
            if self.kind == 'R22':
                mechanical.write_rows(physics.model, self.original, self.inventory, True)
            else:
                write_rows_except(physics.model, self.inventory, KEEP)
            after = mechanical.model_record(physics.model, physics.data)
            if after != self.neutral:
                raise RuntimeError('undeclared mechanical model change')
            self.event = dict(state_index=index, time_s=float(physics.data.time), operation=OPERATION[self.kind],
                              after_sha256=after['sha256'], neutral_sha256=self.neutral['sha256'],
                              original_sha256=self.original['sha256'], released_actuator_ids=self.released_ids,
                              kept_coordinates=self.kept)

    def attach(self, brain, channels, *, sensory_sources):
        fresh = np.random.default_rng(1).bit_generator.state
        if (brain.time_ms != 0. or int(brain.spike_counts.sum()) != 0
                or not brain._rng_states_equal(brain.rng.bit_generator.state, fresh)):
            raise RuntimeError('seed must be applied before the first neural transition')
        brain.rng = np.random.default_rng(self.seed)
        out = super().attach(brain, channels, sensory_sources=sensory_sources)
        self.initial['cns_seed'] = self.seed
        self.initial['channels'] = {name: dict(
            index=int(ch['index']), sign=int(ch['sign']), decoder_mode=str(ch['decoder_mode']),
            bound=float(ch['bound']), positive=list(ch['positive']), negative=list(ch['negative']),
            populations={p: sorted(int(i) for i in ids) for p, ids in ch['populations'].items()})
            for name, ch in channels.items()}
        return out


def run_arm(arm, progress=print):
    spec = protocol()
    kind, seed = split(arm)
    defs = None
    if KINDS[kind] is not None:
        defs = ca.candidate_defs(KINDS[kind], loop.d2_channels(loop.protocol()))
        if ca.defs_sha256(defs) != spec['candidates'][KINDS[kind]]['sha256']:
            raise RuntimeError('candidate definitions differ from preregistration')
    trial = Trial(arm)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256, cns_seed=seed,
                  hypothesis_channels=sorted(defs) if defs else [], label=LABEL if defs else None,
                  definitions_sha256=ca.defs_sha256(defs) if defs else None)
    session = None
    try:
        session = create_v3_session(trial) if defs is None else loop.create_hypothesis_session(trial, KINDS[kind], defs)
        progress(f'{arm}: fresh CNS/physics initialization', flush=True)
        state = session.initialize()
        if state.time_ms != 0.:
            raise RuntimeError('nonzero initial simulation time')
        last = time.monotonic()
        for step in range(1, c.STEPS + 1):
            state = session.step(lightweight=True)
            if state.physics_transitions != step or state.neural_transitions != step // 5:
                raise RuntimeError('authoritative transition count mismatch')
            if time.monotonic() - last >= 30:
                progress(f'{arm}: {step}/{c.STEPS}', flush=True)
                last = time.monotonic()
        result['run_status'] = 'COMPLETE'
    except (Exception, KeyboardInterrupt) as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if session is not None:
            try:
                session.close()
            except Exception as exc:
                result.update(run_status='ERROR', close_error=f'{type(exc).__name__}: {exc}')
        trial.detach()
        result.update(samples=trial.samples, neural=trial.neural, initial=trial.initial, event=trial.event)
    return result


# ---- measures and labels (pure) --------------------------------------------------------

def t_roll(samples):
    """(ms of first post-release sample with tilt > 90 deg, censored flag)."""
    for s in samples[EVENT_STATE + 1:]:
        if c.tilt_deg(s['qpos']) > ROLL_DEG:
            return s['time_s']*1000., False
    return c.WINDOW_MS[1], True


def consistent(diffs, bar=BAR_MS):
    """'DELAYS' / 'HASTENS' if every seed's difference clears the bar in one direction."""
    if all(d >= bar for d in diffs):
        return 'DELAYS'
    if all(d <= -bar for d in diffs):
        return 'HASTENS'
    return None


def q_sign(direction, flip_diffs, bar=BAR_MS):
    if direction is None:
        return 'NOT_EVALUATED'
    same = [(d >= bar) if direction == 'DELAYS' else (d <= -bar) for d in flip_diffs]
    return 'SIGN_SPECIFIC' if sum(not x for x in same) >= 2 else 'SIGN_INDEPENDENT'


def body_z(qpos):
    w, x, y, z = qpos[3:7]
    return [2*(x*z + w*y), 2*(y*z - w*x), 1 - 2*(x*x + y*y)]


def labels(roll, rollover_any):
    """roll: {arm: ms}; rollover_any: {arm: bool}."""
    d_assist = [roll[f'K_{s}'] - roll[f'R22_{s}'] for s in SEEDS]
    d_loop = [roll[f'KC_{s}'] - roll[f'K_{s}'] for s in SEEDS]
    d_flip = [roll[f'KF_{s}'] - roll[f'K_{s}'] for s in SEEDS]
    a, n = consistent(d_assist), consistent(d_loop)
    rescue = (not any(rollover_any[f'KC_{s}'] for s in SEEDS)) and all(rollover_any[f'K_{s}'] for s in SEEDS)
    return dict(
        Q_ASSIST=dict(label=f'ASSIST_{a}' if a else 'NO_CONSISTENT_ASSIST_EFFECT', diffs_ms=d_assist),
        Q_NEURAL=dict(label=f'LOOP_{n}' if n else 'NO_CONSISTENT_LOOP_EFFECT', diffs_ms=d_loop),
        Q_SIGN=dict(label=q_sign(n, d_flip), flip_diffs_ms=d_flip),
        Q_RESCUE=dict(label='RESCUE' if rescue else 'NO_RESCUE'))


def integrity(arms, step_c_r_on, spec, v3_names, indices):
    checks = {}
    checks['I1_complete'] = all(a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1
                                and len(a['neural']) == c.TICKS for a in arms.values())
    if not checks['I1_complete']:
        return checks, {}
    i2 = True
    for s in SEEDS:
        ref = arms[f'K_{s}']
        uni = [t['uniforms_sha256'] for t in ref['neural']]
        i2 &= all(arms[f'{k}_{s}']['initial']['external_schedule'] == ref['initial']['external_schedule']
                  and [t['uniforms_sha256'] for t in arms[f'{k}_{s}']['neural']] == uni for k in KINDS)
    checks['I2_common_rng_within_seed'] = bool(i2)
    r = arms['R22_1']
    checks['I3_reproduces_step_c_r_on'] = (
        len(step_c_r_on['neural']) == c.TICKS and len(step_c_r_on['samples']) == c.STEPS + 1
        and all(x['fired'] == y['fired'] and x['uniforms_sha256'] == y['uniforms_sha256']
                and x['hair_delivered'] == y['hair_delivered'] for x, y in zip(r['neural'], step_c_r_on['neural']))
        and all(x['qpos'] == y['qpos'] for x, y in zip(r['samples'], step_c_r_on['samples'])))
    rel = spec['release']
    i4 = True
    neutral = {}
    for arm, a in arms.items():
        kind, _ = split(arm)
        e = a['event'] or {}
        group = 'R22' if kind == 'R22' else 'K'
        i4 &= (e.get('state_index') == EVENT_STATE and e.get('operation') == OPERATION[kind]
               and e.get('after_sha256') == e.get('neutral_sha256')
               and e.get('released_actuator_ids') == rel[group]['actuator_ids']
               and e.get('kept_coordinates') == ([] if group == 'R22' else sorted(KEEP)))
        neutral.setdefault(group, set()).add(e.get('neutral_sha256'))
    i4 &= all(len(v) == 1 for v in neutral.values()) and neutral.get('R22') != neutral.get('K')
    checks['I4_release_verified'] = bool(i4)
    v3_inv = {n: arms['K_1']['initial']['channels'][n] for n in v3_names}
    v3_idx = {ch['index'] for ch in v3_inv.values()}
    i5, first, offs = True, {}, {}
    for s in SEEDS:
        k0 = arms[f'K_{s}']
        base = k0['samples'][1]['commanded_joints']
        for kind in KINDS:
            a = arms[f'{kind}_{s}']
            i5 &= {n: a['initial']['channels'].get(n) for n in v3_names} == v3_inv
            if KINDS[kind] is None:
                i5 &= set(a['initial']['channels']) == set(v3_names) and not a['hypothesis_channels']
                i5 &= all(x['commanded_joints'][i] == base[i] for x in a['samples'][1:] for i in indices.values())
                continue
            i5 &= (set(a['initial']['channels']) == set(v3_names) | set(KEEP)
                   and a['hypothesis_channels'] == sorted(KEEP) and a['label'] == LABEL
                   and a['definitions_sha256'] == spec['candidates'][KINDS[kind]]['sha256'])
            outside = [i for i in range(42) if i not in v3_idx and i not in indices.values()]
            i5 &= all(x['commanded_joints'][i] == y['commanded_joints'][i]
                      for x, y in zip(a['samples'][1:], k0['samples'][1:]) for i in outside)
            off = ca.offsets(a, base, indices)
            i5 &= all(abs(x) <= loop.BOUND + loop.EPS for v in off.values() for x in v)
            offs[f'{kind}_{s}'] = off
            first[f'{kind}_{s}'] = loop.first_command_change(a, list(indices.values()), base)
    checks['I5_channels_bounds'] = bool(i5)
    i6 = True
    for s in SEEDS:
        k0, r22 = arms[f'K_{s}'], arms[f'R22_{s}']
        t_event = k0['samples'][EVENT_STATE]['time_s']*1000.
        i6 &= all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                  for x, y in zip(r22['samples'][:EVENT_STATE + 1], k0['samples'][:EVENT_STATE + 1]))
        i6 &= all(x['fired'] == y['fired'] for x, y in zip(r22['neural'], k0['neural']) if x['time_ms'] <= t_event)
        for kind in ('KC', 'KF'):
            a, k = arms[f'{kind}_{s}'], first[f'{kind}_{s}']
            k = len(a['samples']) if k is None else k
            t_k = a['samples'][k]['time_s']*1000. if k < len(a['samples']) else math.inf
            i6 &= all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                      for x, y in zip(a['samples'][:k], k0['samples'][:k]))
            i6 &= all(x['fired'] == y['fired'] for x, y in zip(a['neural'], k0['neural']) if x['time_ms'] < t_k)
    checks['I6_prefix_within_seed'] = bool(i6)
    tick1 = [arms[f'K_{s}']['neural'][0]['uniforms_sha256'] for s in SEEDS]
    checks['I7_seeds_applied'] = (len(set(tick1)) == len(SEEDS)
                                  and all(arms[f'{k}_{s}']['initial'].get('cns_seed') == s for s in SEEDS for k in KINDS))
    return checks, dict(first_command_sample=first, offsets=offs)


def evaluate(arms, step_c_r_on, spec, v3_names, indices, bodymap=None):
    checks, audit = integrity(arms, step_c_r_on, spec, v3_names, indices)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks)
    roll, censored, over_any, tilt, direction = {}, {}, {}, {}, {}
    lo, hi = c.WINDOW_MS
    for arm, a in arms.items():
        roll[arm], censored[arm] = t_roll(a['samples'])
        tilts = [c.tilt_deg(x['qpos']) for x in a['samples']]
        post = tilts[EVENT_STATE + 1:]
        over_any[arm] = any(t > ROLL_DEG for t in post)
        w = [t for x, t in zip(a['samples'], tilts) if lo < x['time_s']*1000. <= hi]
        tilt[arm] = dict(mean=float(np.mean(w)), peak=float(np.max(w)), rollover_samples=int(sum(t > ROLL_DEG for t in w)))
        if not censored[arm]:
            k = next(i for i, x in enumerate(a['samples']) if i > EVENT_STATE and c.tilt_deg(x['qpos']) > ROLL_DEG)
            direction[arm] = body_z(a['samples'][k]['qpos'])
    out = dict(status='INTEGRITY_ACCEPTED', checks=checks, labels=labels(roll, over_any),
               t_roll_ms=roll, censored=censored, tilt_deg=tilt, rollover_body_z=direction,
               first_command_sample=audit['first_command_sample'])
    after = {}
    for arm, off in audit['offsets'].items():
        post = {n: v[EVENT_STATE:] for n, v in off.items()}
        after[arm] = {n: dict(mean=float(np.mean(v)), max_abs=float(np.max(np.abs(v))),
                              near_bound_fraction=float(np.mean([abs(x) >= loop.BOUND - ca.NEAR_BOUND for x in v])))
                      for n, v in post.items()}
    out['offsets_after_release_rad'] = after
    out['forward_window'] = {k: {leg: v for leg, v in loop.mean_by_leg(a, 'hair_forward').items() if leg in ('LF', 'LH')}
                             for k, a in arms.items()}
    out['hair_rate_hz'] = {k: loop.mean_by_leg(a, 'hair_rate_hz') for k, a in arms.items()}
    out['first_physical_divergence_vs_K'] = {
        k: next((i for i, (x, y) in enumerate(zip(a['samples'], arms[f'K_{split(k)[1]}']['samples'])) if x['qpos'] != y['qpos']), None)
        for k, a in arms.items() if not k.startswith('K_')}
    if bodymap is not None:
        _, per_leg = c.mn_sets(bodymap)
        out['coxa_mn_rates_per_leg_hz'] = {k: {leg: c.rate(a, ids) for leg, ids in per_leg.items()} for k, a in arms.items()}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--step-c-dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.arm:
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/f'{args.arm}.json.gz'
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm)
        digest = c.save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=digest)))
        return 0 if result['run_status'] == 'COMPLETE' else 1
    spec = protocol()
    from ..embodiment import live_v3_motor_interface as v3
    raw = args.step_c_dir/'R_ON.json.gz'
    if loop.sha(raw) != spec['sources']['step_c_r_on']['sha256']:
        raise SystemExit('Step C R_ON raw identity mismatch')
    saved = loop.d2_channels(loop.protocol())
    if any(ca.defs_sha256(ca.candidate_defs(k, saved)) != spec['candidates'][k]['sha256'] for k in ('H1', 'H1_FLIP')):
        raise SystemExit('candidate definitions differ from preregistration')
    indices = {n: d['action_index'] for n, d in ca.candidate_defs('H1', saved).items()}
    folder = args.evaluate
    arms = {k: c.load(folder/f'{k}.json.gz') for k in ARMS}
    hashes = {k: loop.sha(folder/f'{k}.json.gz') for k in ARMS}
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    report = dict(schema='coxa-release-posture-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=evaluate(arms, c.load(raw), spec, tuple(v3.V3_MOTOR), indices, bodymap),
                  interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    e = report['evaluation']
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'labels', 't_roll_ms', 'censored', 'tilt_deg')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
