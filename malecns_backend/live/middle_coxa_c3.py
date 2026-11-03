"""Middle-leg coxa C3 confirmation on new seeds (V1).

Preregistered in docs/evidence/middle-coxa-c3-v1/protocol.json (design:
docs/MIDDLE_COXA_C3_CONFIRMATION_V1.md). The C2 context unchanged (Step C A_ON +
SHIFT_SERVO_EQUILIBRIUM at state 5005, H1/H1_FLIP joint_LMCoxa + joint_RMCoxa by hash) on
never-run CNS seeds 4-6, plus REPRO_1, a rerun of C2 arm P0_1 that must match it exactly.
Reuses middle_coxa_displacement; that module and its protocol are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from . import coxa_admission as ca
from . import coxa_hypothesis_loop as loop
from . import hair_plate_posture as c
from . import middle_coxa_displacement as m
from .tactile_boundary import create_session as create_v3_session, native

ROOT = loop.ROOT
PROTOCOL = 'docs/evidence/middle-coxa-c3-v1/protocol.json'
PROTOCOL_SHA256 = 'dd268b80dcb80295e9af87e7dd1bb6df08a4e77a2625e02abf344de716d909e4'
SCHEMA = 'middle-coxa-c3-arm-v1'
LABEL = 'COXA_CONDITIONAL_H1'
CANDIDATES, LEG_OF = m.CANDIDATES, m.LEG_OF
SEEDS = (4, 5, 6)
KINDS = m.KINDS
ARMS = ('REPRO_1',) + tuple(f'{k}_{s}' for s in SEEDS for k in KINDS)
EVENT_STATE, BOUND, BAR = m.EVENT_STATE, m.BOUND, m.BAR
PRE_MS = (400., 500.)


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def split(arm):
    if arm == 'REPRO_1':
        return 'P0', 1
    kind, seed = arm.rsplit('_', 1)
    if kind not in KINDS or int(seed) not in SEEDS:
        raise ValueError('unknown arm')
    return kind, int(seed)


class Trial(m.Trial):
    """The C2 trial (displacement + seed + channel inventory) with this test's arm set."""

    def __init__(self, arm):
        kind, seed = split(arm)
        loop.Trial.__init__(self, arm)
        self.kind, self.seed = kind, seed


def run_arm(arm, progress=print, steps=c.STEPS):
    spec = protocol()
    kind, seed = split(arm)
    defs = None
    if KINDS[kind] is not None:
        defs = m.candidate_defs(KINDS[kind], loop.d2_channels(loop.protocol()))
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
    return 'CONFIRMED' if n == len(SEEDS) else 'PARTIAL' if n else 'NOT_CONFIRMED'


STATUS = {'CONFIRMED': 'CONDITIONAL', 'PARTIAL': 'C2_PASSED_ONLY', 'NOT_CONFIRMED': 'NOT_SUPPORTED'}


def reproduces(a, ref):
    return (len(a['samples']) == len(ref['samples']) and len(a['neural']) == len(ref['neural'])
            and all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                    for x, y in zip(a['samples'], ref['samples']))
            and all(x['fired'] == y['fired'] and x['uniforms_sha256'] == y['uniforms_sha256']
                    and x['hair_delivered'] == y['hair_delivered'] for x, y in zip(a['neural'], ref['neural']))
            and (a['event'] or {}).get('after_sha256') == (ref['event'] or {}).get('after_sha256') is not None)


def mean_in(arm, key, lo, hi):
    w = [t for t in arm['neural'] if lo < t['time_ms'] <= hi]
    return {leg: float(np.mean([t[key][leg] for t in w])) for leg in w[0][key]}


def integrity(arms, c2_p0, spec, v3_names, indices):
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
    checks['I3_reproduction'] = bool(reproduces(arms['REPRO_1'], c2_p0[1]))
    i4, expected = True, set()
    for a in arms.values():
        e = a['event'] or {}
        i4 &= (e.get('state_index') == EVENT_STATE and e.get('operation') == m.OPERATION
               and e.get('after_sha256') == e.get('expected_sha256') is not None
               and [(x['coordinate'], x['delta_rad']) for x in e.get('shifted', [])]
               == [(n, spec['context']['delta_rad'][n]) for n in CANDIDATES])
        expected.add(e.get('expected_sha256'))
    checks['I4_displacement_verified'] = bool(i4 and len(expected) == 1)
    v3_inv = {n: arms['P0_4']['initial']['channels'][n] for n in v3_names}
    v3_idx = {ch['index'] for ch in v3_inv.values()}
    i5, first, offs = True, {}, {}
    for arm in ['REPRO_1'] + [f'P0_{s}' for s in SEEDS]:
        p = arms[arm]
        base = p['samples'][1]['commanded_joints']
        i5 &= set(p['initial']['channels']) == set(v3_names) and not p['hypothesis_channels']
        i5 &= {n: p['initial']['channels'].get(n) for n in v3_names} == v3_inv
        i5 &= all(x['commanded_joints'][i] == base[i] for x in p['samples'][1:] for i in indices.values())
    for s in SEEDS:
        p0 = arms[f'P0_{s}']
        base = p0['samples'][1]['commanded_joints']
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
    new = [arms[f'P0_{s}']['neural'][0]['uniforms_sha256'] for s in SEEDS]
    old = [c2_p0[s]['neural'][0]['uniforms_sha256'] for s in (1, 2, 3)]
    checks['I7_seeds_applied'] = (len(set(new)) == len(SEEDS) and not set(new) & set(old)
                                  and all(arms[f'{k}_{s}']['initial'].get('cns_seed') == s for s in SEEDS for k in KINDS)
                                  and arms['REPRO_1']['initial'].get('cns_seed') == 1)
    return checks, dict(first_command_sample=first, offsets=offs)


def evaluate(arms, c2_p0, spec, v3_names, indices, bodymap=None):
    checks, audit = integrity(arms, c2_p0, spec, v3_names, indices)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks, first_command_sample=audit.get('first_command_sample'))
    lo, hi = c.WINDOW_MS
    hair = {k: mean_in(a, 'hair_rate_hz', lo, hi) for k, a in arms.items()}
    forward = {k: mean_in(a, 'hair_forward', lo, hi) for k, a in arms.items()}
    pre_f = {k: mean_in(a, 'hair_forward', *PRE_MS) for k, a in arms.items()}
    context = {s: {LEG_OF[n]: hair[f'P0_{s}'][LEG_OF[n]] for n in CANDIDATES} for s in SEEDS}
    base = dict(checks=checks, p0_hair_rate_hz=context, hair_rate_hz=hair, forward_window=forward,
                first_command_sample=audit['first_command_sample'])
    if not all(v >= m.CONTEXT_MIN_HZ for row in context.values() for v in row.values()):
        return dict(status='INCONCLUSIVE_CONTEXT', **base)
    tilt = {k: [c.tilt_deg(x['qpos']) for x in a['samples']] for k, a in arms.items()}
    rollover = any(t > 90 for v in tilt.values() for t in v)
    labels, status, per_seed, flags, pre = {}, {}, {}, {}, {}
    for name in CANDIDATES:
        leg = LEG_OF[name]
        rows, passes = {}, []
        for s in SEEDS:
            f0 = forward[f'P0_{s}'][leg]
            dc, dfl = forward[f'PC_{s}'][leg] - f0, forward[f'PF_{s}'][leg] - f0
            ok = bool(dc <= -BAR and dfl >= BAR)
            passes.append(ok)
            rows[s] = dict(d_pc=dc, d_pf=dfl, passed=ok, hair_p0=hair[f'P0_{s}'][leg],
                           hair_pc=hair[f'PC_{s}'][leg], hair_pf=hair[f'PF_{s}'][leg],
                           pre_d_pc=pre_f[f'PC_{s}'][leg] - pre_f[f'P0_{s}'][leg],
                           pre_d_pf=pre_f[f'PF_{s}'][leg] - pre_f[f'P0_{s}'][leg])
        near = {}
        for arm, off in audit['offsets'].items():
            w = ca.in_window(arms[arm])
            vals = [abs(x) for x, inside in zip(off[name], w) if inside]
            near[arm] = float(np.mean([v >= BOUND - m.NEAR_BOUND for v in vals]))
            win = [x for x, inside in zip(off[name], w) if inside]
            pre.setdefault(arm, {})[name] = dict(before_event=float(np.mean(off[name][:EVENT_STATE])),
                                                 window=float(np.mean(win)))
        no_drive = all(all(x == 0 for x in audit['offsets'][f'PC_{s}'][name]) for s in SEEDS)
        labels[name], per_seed[name] = label(passes), rows
        status[name] = STATUS[labels[name]]
        flags[name] = dict(BOUND_LIMITED=any(v > m.BOUND_FRACTION for v in near.values()), near_bound_fraction=near,
                           ROLLOVER=rollover, NO_DRIVE=no_drive)
    out = dict(status='INTEGRITY_ACCEPTED', labels=labels, coordinate_status=status, label_tag=LABEL,
               per_seed=per_seed, flags=flags, offsets_before_vs_window_rad=pre, **base,
               tilt_deg={k: dict(mean=float(np.mean(v)), peak=float(np.max(v))) for k, v in tilt.items()},
               first_physical_divergence_vs_P0={
                   k: next((i for i, (x, y) in enumerate(zip(a['samples'], arms[f'P0_{split(k)[1]}']['samples']))
                            if x['qpos'] != y['qpos']), None) for k, a in arms.items() if k[:2] in ('PC', 'PF')})
    if bodymap is not None:
        _, per_leg = c.mn_sets(bodymap)
        out['coxa_mn_rates_per_leg_hz'] = {k: {leg: c.rate(a, ids) for leg, ids in per_leg.items()} for k, a in arms.items()}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--c2-dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
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
    for key in ('c2_protocol', 'c2_report'):
        if loop.sha(ROOT/spec['sources'][key]['path']) != spec['sources'][key]['sha256']:
            raise SystemExit(f'{key} identity mismatch')
    c2_p0 = {}
    for s in (1, 2, 3):
        raw = args.c2_dir/f'P0_{s}.json.gz'
        if loop.sha(raw) != spec['sources']['c2_p0_raw'][str(s)]:
            raise SystemExit(f'C2 P0_{s} raw identity mismatch')
        c2_p0[s] = c.load(raw)
    saved = loop.d2_channels(loop.protocol())
    if any(ca.defs_sha256(m.candidate_defs(k, saved)) != spec['candidates'][k]['sha256'] for k in ('H1', 'H1_FLIP')):
        raise SystemExit('candidate definitions differ from preregistration')
    indices = {n: d['action_index'] for n, d in m.candidate_defs('H1', saved).items()}
    folder = args.evaluate
    arms = {k: c.load(folder/f'{k}.json.gz') for k in ARMS}
    hashes = {k: loop.sha(folder/f'{k}.json.gz') for k in ARMS}
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    report = dict(schema='middle-coxa-c3-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=evaluate(arms, c2_p0, spec, tuple(v3.V3_MOTOR), indices, bodymap),
                  interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    e = report['evaluation']
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'p0_hair_rate_hz', 'labels', 'coordinate_status',
                                                   'per_seed', 'flags')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
