"""Middle-leg coxa resistance reflex under an imposed forward displacement (V1, C2 step).

Preregistered in docs/evidence/middle-coxa-displacement-v1/protocol.json (design:
docs/MIDDLE_COXA_DISPLACEMENT_V1.md). Nine fixed arms (P0/PC/PF x CNS seeds 1-3) on Step C
arm A_ON, one fresh process each. At state 5005 the baseline position servos of
joint_LMCoxa and joint_RMCoxa get a declared equilibrium shift (SHIFT_SERVO_EQUILIBRIUM:
biasprm[0] += kp*Delta); PC/PF add only the H1/H1_FLIP channels of those two coordinates
through the D3 hypothesis session path. Nothing here admits or conditions a coordinate.
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

ROOT = loop.ROOT
PROTOCOL = 'docs/evidence/middle-coxa-displacement-v1/protocol.json'
PROTOCOL_SHA256 = '9854e0af9f7b0829cbd21b3544db1edcfcb841150990a97dd81da38cf63f4fab'
SCHEMA = 'middle-coxa-displacement-arm-v1'
CANDIDATES = ('joint_LMCoxa', 'joint_RMCoxa')
LEG_OF = {'joint_LMCoxa': 'LM', 'joint_RMCoxa': 'RM'}
DELTA = {'joint_LMCoxa': -0.24496486703405715, 'joint_RMCoxa': -0.21994650976688868}
SEEDS = ca.SEEDS
KINDS = {'P0': None, 'PC': 'H1', 'PF': 'H1_FLIP'}
ARMS = tuple(f'{k}_{s}' for s in SEEDS for k in KINDS)
OPERATION = 'SHIFT_SERVO_EQUILIBRIUM'
EVENT_STATE = c.EVENT_STATE
BOUND, BAR = loop.BOUND, loop.BAR
NEAR_BOUND, BOUND_FRACTION = ca.NEAR_BOUND, ca.BOUND_FRACTION
CONTEXT_MIN_HZ = 30.


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if PROTOCOL_SHA256 is None or hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def split(arm):
    kind, seed = arm.rsplit('_', 1)
    if kind not in KINDS or int(seed) not in SEEDS:
        raise ValueError('unknown arm')
    return kind, int(seed)


def candidate_defs(d2_arm, saved):
    defs = loop.definitions(d2_arm, saved)
    return {n: defs[n] for n in CANDIDATES}


# ---- declared equilibrium shift ------------------------------------------------------

def shift_rows(inv, original):
    """[(coordinate, actuator_id, kp, new_bias0)] for the two servos; refuses a non-position servo."""
    mechanical.validate_binding(inv, original)
    by_name = {r['coordinate']: r for r in inv['rows']}
    gain = mechanical.array_values(original, 'actuator_gainprm')
    bias = mechanical.array_values(original, 'actuator_biasprm')
    out = []
    for name in CANDIDATES:
        aid = by_name[name]['actuator_id']
        kp = float(gain[aid, 0])
        if not (kp > 0 and bias[aid, 0] == 0. and bias[aid, 1] == -kp):
            raise ValueError(f'{name}: not a plain position servo (kp, biasprm) as declared')
        out.append((name, int(aid), kp, float(bias[aid, 0] + kp*DELTA[name])))
    return out


def shifted_record(original, rows):
    """The original record with exactly biasprm[aid, 0] replaced for the declared rows."""
    expected = copy.deepcopy(original)
    values = mechanical.array_values(original, 'actuator_biasprm').copy()
    for _, aid, _, b0 in rows:
        values[aid, 0] = b0
    expected['arrays']['actuator_biasprm'] = mechanical.isolation.encode_nonfinite(values.tolist())
    expected['identity']['model_arrays']['actuator_biasprm'] = mechanical.array_identity(values)
    expected['sha256'] = mechanical.digest(expected['identity'])
    return expected


def write_shift(model, rows):
    for _, aid, _, b0 in rows:
        model.actuator_biasprm[aid, 0] = b0


# ---- adapter -----------------------------------------------------------------------

class Trial(loop.Trial):
    """D3 trial (Step C A_ON + channel inventory) with a declared seed and equilibrium shift."""

    def __init__(self, arm):
        kind, seed = split(arm)
        super().__init__(arm)
        self.kind, self.seed = kind, seed

    def bind(self, sim, physics, obs):
        super().bind(sim, physics, obs)
        self.rows = shift_rows(self.inventory, self.original)
        self.expected = shifted_record(self.original, self.rows)

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
            write_shift(physics.model, self.rows)
            after = mechanical.model_record(physics.model, physics.data)
            if after != self.expected:
                raise RuntimeError('undeclared mechanical model change')
            self.event = dict(state_index=index, time_s=float(physics.data.time), operation=OPERATION,
                              after_sha256=after['sha256'], expected_sha256=self.expected['sha256'],
                              original_sha256=self.original['sha256'],
                              shifted=[dict(coordinate=n, actuator_id=a, kp=kp, delta_rad=DELTA[n], bias0=b0)
                                       for n, a, kp, b0 in self.rows])

    def attach(self, brain, channels, *, sensory_sources):
        fresh = np.random.default_rng(1).bit_generator.state
        if (brain.time_ms != 0. or int(brain.spike_counts.sum()) != 0
                or not brain._rng_states_equal(brain.rng.bit_generator.state, fresh)):
            raise RuntimeError('seed must be applied before the first neural transition')
        brain.rng = np.random.default_rng(self.seed)
        out = super().attach(brain, channels, sensory_sources=sensory_sources)
        self.initial['cns_seed'] = self.seed
        return out


def run_arm(arm, progress=print, steps=c.STEPS):
    spec = protocol()
    kind, seed = split(arm)
    defs = None
    if KINDS[kind] is not None:
        defs = candidate_defs(KINDS[kind], loop.d2_channels(loop.protocol()))
        if ca.defs_sha256(defs) != spec['candidates'][KINDS[kind]]['sha256']:
            raise RuntimeError('candidate definitions differ from preregistration')
    trial = Trial(arm)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256, cns_seed=seed,
                  hypothesis_channels=sorted(defs) if defs else [],
                  definitions_sha256=ca.defs_sha256(defs) if defs else None)
    session = None
    try:
        session = create_v3_session(trial) if defs is None else loop.create_hypothesis_session(trial, KINDS[kind], defs)
        progress(f'{arm}: fresh CNS/physics initialization', flush=True)
        state = session.initialize()
        if state.time_ms != 0.:
            raise RuntimeError('nonzero initial simulation time')
        last = time.monotonic()
        for step in range(1, steps + 1):
            state = session.step(lightweight=True)
            if state.physics_transitions != step or state.neural_transitions != step // 5:
                raise RuntimeError('authoritative transition count mismatch')
            if time.monotonic() - last >= 30:
                progress(f'{arm}: {step}/{steps}', flush=True)
                last = time.monotonic()
        result['run_status'] = 'COMPLETE' if steps == c.STEPS else 'SMOKE'
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


# ---- evaluation (pure on arm records) ------------------------------------------------

def label(passes):
    n = sum(passes)
    return 'C2_PASSED' if n == len(SEEDS) else 'C2_PARTIAL' if n else 'C2_NOT_SUPPORTED'


def integrity(arms, c0, spec, v3_names, indices):
    checks = {}
    checks['I1_complete'] = all(a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1
                                and len(a['neural']) == c.TICKS for a in arms.values())
    if not checks['I1_complete']:
        return checks, {}
    i2 = True
    for s in SEEDS:
        ref = arms[f'P0_{s}']
        uni = [t['uniforms_sha256'] for t in ref['neural']]
        i2 &= all(arms[f'{k}_{s}']['initial']['external_schedule'] == ref['initial']['external_schedule']
                  and [t['uniforms_sha256'] for t in arms[f'{k}_{s}']['neural']] == uni for k in KINDS)
    checks['I2_common_rng_within_seed'] = bool(i2)
    i3 = True
    for s in SEEDS:
        p, r = arms[f'P0_{s}'], c0[s]
        t_event = p['samples'][EVENT_STATE]['time_s']*1000.
        i3 &= len(r['samples']) == c.STEPS + 1 and len(r['neural']) == c.TICKS
        i3 &= all(x['qpos'] == y['qpos'] for x, y in zip(p['samples'][:EVENT_STATE + 1], r['samples'][:EVENT_STATE + 1]))
        i3 &= all(x['fired'] == y['fired'] and x['uniforms_sha256'] == y['uniforms_sha256']
                  and x['hair_delivered'] == y['hair_delivered']
                  for x, y in zip(p['neural'], r['neural']) if x['time_ms'] <= t_event)
    checks['I3_reproduces_c0_prefix'] = bool(i3)
    i4, expected = True, set()
    for a in arms.values():
        e = a['event'] or {}
        i4 &= (e.get('state_index') == EVENT_STATE and e.get('operation') == OPERATION
               and e.get('after_sha256') == e.get('expected_sha256') is not None
               and [(x['coordinate'], x['delta_rad']) for x in e.get('shifted', [])]
               == [(n, spec['displacement']['delta_rad'][n]) for n in CANDIDATES])
        expected.add(e.get('expected_sha256'))
    checks['I4_displacement_verified'] = bool(i4 and len(expected) == 1)
    v3_inv = {n: arms['P0_1']['initial']['channels'][n] for n in v3_names}
    v3_idx = {ch['index'] for ch in v3_inv.values()}
    i5, first, offs = True, {}, {}
    for s in SEEDS:
        p0 = arms[f'P0_{s}']
        base = p0['samples'][1]['commanded_joints']
        i5 &= set(p0['initial']['channels']) == set(v3_names) and not p0['hypothesis_channels']
        i5 &= all(x['commanded_joints'][i] == base[i] for x in p0['samples'][1:] for i in indices.values())
        i5 &= {n: p0['initial']['channels'].get(n) for n in v3_names} == v3_inv
        for k in ('PC', 'PF'):
            arm = f'{k}_{s}'
            a = arms[arm]
            i5 &= ({n: a['initial']['channels'].get(n) for n in v3_names} == v3_inv
                   and set(a['initial']['channels']) == set(v3_names) | set(CANDIDATES)
                   and a['hypothesis_channels'] == sorted(CANDIDATES)
                   and a['definitions_sha256'] == spec['candidates'][KINDS[k]]['sha256'])
            outside = [i for i in range(42) if i not in v3_idx and i not in indices.values()]
            i5 &= all(x['commanded_joints'][i] == y['commanded_joints'][i]
                      for x, y in zip(a['samples'][1:], p0['samples'][1:]) for i in outside)
            off = ca.offsets(a, base, indices)
            i5 &= all(abs(x) <= BOUND + loop.EPS for v in off.values() for x in v)
            offs[arm] = off
            first[arm] = loop.first_command_change(a, list(indices.values()), base)
    checks['I5_channels_bounds'] = bool(i5)
    i6 = True
    for arm, k in first.items():
        a, p0 = arms[arm], arms[f'P0_{split(arm)[1]}']
        k = len(a['samples']) if k is None else k
        t_k = a['samples'][k]['time_s']*1000. if k < len(a['samples']) else math.inf
        i6 &= all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                  for x, y in zip(a['samples'][:k], p0['samples'][:k]))
        i6 &= all(x['fired'] == y['fired'] for x, y in zip(a['neural'], p0['neural']) if x['time_ms'] < t_k)
    checks['I6_prefix_within_seed'] = bool(i6)
    tick1 = [arms[f'P0_{s}']['neural'][0]['uniforms_sha256'] for s in SEEDS]
    checks['I7_seeds_applied'] = (len(set(tick1)) == len(SEEDS)
                                  and all(arms[f'{k}_{s}']['initial'].get('cns_seed') == s for s in SEEDS for k in KINDS))
    return checks, dict(first_command_sample=first, offsets=offs)


def evaluate(arms, c0, spec, v3_names, indices, bodymap=None):
    checks, audit = integrity(arms, c0, spec, v3_names, indices)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks, first_command_sample=audit.get('first_command_sample'))
    hair = {k: loop.mean_by_leg(a, 'hair_rate_hz') for k, a in arms.items()}
    forward = {k: loop.mean_by_leg(a, 'hair_forward') for k, a in arms.items()}
    context = {s: {LEG_OF[n]: hair[f'P0_{s}'][LEG_OF[n]] for n in CANDIDATES} for s in SEEDS}
    base = dict(checks=checks, p0_hair_rate_hz=context, hair_rate_hz=hair, forward_window=forward,
                first_command_sample=audit['first_command_sample'])
    if not all(v >= CONTEXT_MIN_HZ for row in context.values() for v in row.values()):
        return dict(status='INCONCLUSIVE_CONTEXT', **base)
    tilt = {k: [c.tilt_deg(x['qpos']) for x in a['samples']] for k, a in arms.items()}
    rollover = any(t > 90 for v in tilt.values() for t in v)
    labels, per_seed, flags = {}, {}, {}
    for name in CANDIDATES:
        leg = LEG_OF[name]
        rows, passes = {}, []
        for s in SEEDS:
            f0 = forward[f'P0_{s}'][leg]
            dc, dfl = forward[f'PC_{s}'][leg] - f0, forward[f'PF_{s}'][leg] - f0
            ok = bool(dc <= -BAR and dfl >= BAR)
            passes.append(ok)
            rows[s] = dict(d_pc=dc, d_pf=dfl, passed=ok, hair_p0=hair[f'P0_{s}'][leg],
                           hair_pc=hair[f'PC_{s}'][leg], hair_pf=hair[f'PF_{s}'][leg])
        near = {}
        for arm, off in audit['offsets'].items():
            w = ca.in_window(arms[arm])
            vals = [abs(x) for x, inside in zip(off[name], w) if inside]
            near[arm] = float(np.mean([v >= BOUND - NEAR_BOUND for v in vals]))
        no_drive = all(all(x == 0 for x in audit['offsets'][f'PC_{s}'][name]) for s in SEEDS)
        labels[name], per_seed[name] = label(passes), rows
        flags[name] = dict(BOUND_LIMITED=any(v > BOUND_FRACTION for v in near.values()), near_bound_fraction=near,
                           ROLLOVER=rollover, NO_DRIVE=no_drive)
    out = dict(status='INTEGRITY_ACCEPTED', labels=labels, per_seed=per_seed, flags=flags, **base,
               channel_offsets_rad={arm: {n: dict(mean=float(np.mean(v[EVENT_STATE:])), max_abs=float(np.max(np.abs(v))))
                                          for n, v in off.items()} for arm, off in audit['offsets'].items()},
               tilt_deg={k: dict(mean=float(np.mean(v)), peak=float(np.max(v))) for k, v in tilt.items()},
               first_physical_divergence_vs_P0={
                   k: next((i for i, (x, y) in enumerate(zip(a['samples'], arms[f'P0_{split(k)[1]}']['samples']))
                            if x['qpos'] != y['qpos']), None) for k, a in arms.items() if not k.startswith('P0')})
    if bodymap is not None:
        _, per_leg = c.mn_sets(bodymap)
        out['coxa_mn_rates_per_leg_hz'] = {k: {leg: c.rate(a, ids) for leg, ids in per_leg.items()} for k, a in arms.items()}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hashes', action='store_true', help='print candidate definition hashes')
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--c0-dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    saved = loop.d2_channels(loop.protocol())
    if args.hashes:
        print(json.dumps({k: dict(sha256=ca.defs_sha256(candidate_defs(k, saved)),
                                  action_index={n: d['action_index'] for n, d in candidate_defs(k, saved).items()},
                                  coordinate_sign={n: d['coordinate_sign'] for n, d in candidate_defs(k, saved).items()})
                          for k in ('H1', 'H1_FLIP')}, indent=1))
        return 0
    if args.arm:
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/(f'{args.arm}.json.gz' if args.smoke_steps is None else f'smoke_{args.arm}.json.gz')
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm, steps=args.smoke_steps or c.STEPS)
        digest = c.save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=digest)))
        return 0 if result['run_status'] in ('COMPLETE', 'SMOKE') else 1
    spec = protocol()
    from ..embodiment import live_v3_motor_interface as v3
    c0 = {}
    for s in SEEDS:
        raw = args.c0_dir/f'C0_{s}.json.gz'
        if loop.sha(raw) != spec['sources']['c0'][str(s)]:
            raise SystemExit(f'coxa-admission C0_{s} raw identity mismatch')
        c0[s] = c.load(raw)
    if any(ca.defs_sha256(candidate_defs(k, saved)) != spec['candidates'][k]['sha256'] for k in ('H1', 'H1_FLIP')):
        raise SystemExit('candidate definitions differ from preregistration')
    indices = {n: d['action_index'] for n, d in candidate_defs('H1', saved).items()}
    folder = args.evaluate
    arms = {k: c.load(folder/f'{k}.json.gz') for k in ARMS}
    hashes = {k: loop.sha(folder/f'{k}.json.gz') for k in ARMS}
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    report = dict(schema='middle-coxa-displacement-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=evaluate(arms, c0, spec, tuple(v3.V3_MOTOR), indices, bodymap),
                  interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    e = report['evaluation']
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'p0_hair_rate_hz', 'labels', 'per_seed', 'flags')}),
                     indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
