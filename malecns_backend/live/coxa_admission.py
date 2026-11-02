"""Coxa admission question V1, Part B: prospective, isolated confirmation of LF/LH Coxa.

Preregistered in docs/evidence/coxa-admission-v1/protocol.json (design:
docs/COXA_ADMISSION_QUESTION_V1.md). Nine fixed arms (C0/CAND/FLIP x CNS seeds 1-3) on
Step C arm A_ON, one fresh process each. CAND and FLIP add only joint_LFCoxa and
joint_LHCoxa, loaded unchanged from the D2 result through the D3 hypothesis session path.
Seeds are applied by replacing brain.rng at attach, before the first neural transition;
the kernel is not modified. Nothing here admits a coordinate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from . import coxa_hypothesis_loop as loop
from . import hair_plate_posture as c
from .tactile_boundary import create_session as create_v3_session, native
from ..embodiment import hair_plate_encoder as hp

ROOT = loop.ROOT
PROTOCOL = 'docs/evidence/coxa-admission-v1/protocol.json'
PROTOCOL_SHA256 = '3b97fbb85f160b20dbeb43e3a6a650576961437432baa7dfbb0b469a26bc1ed7'
SCHEMA = 'coxa-admission-arm-v1'
CANDIDATES = ('joint_LFCoxa', 'joint_LHCoxa')
LEG_OF = {'joint_LFCoxa': 'LF', 'joint_LHCoxa': 'LH'}
SEEDS = (1, 2, 3)
KINDS = {'C0': None, 'CAND': 'H1', 'FLIP': 'H1_FLIP'}
ARMS = tuple(f'{k}_{s}' for s in SEEDS for k in KINDS)
BOUND, BAR = loop.BOUND, loop.BAR
NEAR_BOUND, BOUND_FRACTION = .01, .5


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


def candidate_defs(d2_arm, saved):
    """The two candidate channels of one D2 arm, in the D3 kernel format."""
    defs = loop.definitions(d2_arm, saved)
    return {n: defs[n] for n in CANDIDATES}


def defs_sha256(defs):
    return hashlib.sha256(json.dumps(native(defs), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class Trial(loop.Trial):
    """D3 trial (Step C A_ON + channel inventory) with a declared CNS seed."""

    def __init__(self, arm):
        kind, seed = split(arm)
        super().__init__(arm)
        self.seed = seed

    def attach(self, brain, channels, *, sensory_sources):
        fresh = np.random.default_rng(1).bit_generator.state
        if (brain.time_ms != 0. or int(brain.spike_counts.sum()) != 0
                or not brain._rng_states_equal(brain.rng.bit_generator.state, fresh)):
            raise RuntimeError('seed must be applied before the first neural transition')
        brain.rng = np.random.default_rng(self.seed)
        out = super().attach(brain, channels, sensory_sources=sensory_sources)
        self.initial['cns_seed'] = self.seed
        return out


def run_arm(arm, progress=print):
    spec = protocol()
    kind, seed = split(arm)
    defs = None
    if KINDS[kind] is not None:
        defs = candidate_defs(KINDS[kind], loop.d2_channels(loop.protocol()))
        if defs_sha256(defs) != spec['candidates'][KINDS[kind]]['sha256']:
            raise RuntimeError('candidate definitions differ from preregistration')
    trial = Trial(arm)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256,
                  cns_seed=seed, hypothesis_channels=sorted(defs) if defs else [],
                  definitions_sha256=defs_sha256(defs) if defs else None)
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


# ---- evaluation (pure on arm records) ------------------------------------------------

def seed_pass(firing, d_cand, d_flip):
    return bool(firing and d_cand <= -BAR and d_flip >= BAR)


def label(passes):
    n = sum(passes)
    return 'CONFIRMED' if n == len(SEEDS) else 'PARTIAL' if n else 'NOT_CONFIRMED'


def offsets(arm, base, indices):
    """{name: per-sample offset of the commanded joint from the C0 baseline}."""
    return {name: [s['commanded_joints'][i] - base[i] for s in arm['samples'][1:]] for name, i in indices.items()}


def in_window(arm):
    lo, hi = c.WINDOW_MS
    return [lo < s['time_s']*1000. <= hi for s in arm['samples'][1:]]


def integrity(arms, step_c, expected_hashes, v3_names, indices):
    checks = {}
    checks['I1_complete'] = all(a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1
                                and len(a['neural']) == c.TICKS for a in arms.values())
    if not checks['I1_complete']:
        return checks, {}
    i2 = True
    for s in SEEDS:
        ref = arms[f'C0_{s}']
        uni = [t['uniforms_sha256'] for t in ref['neural']]
        i2 &= all(arms[f'{k}_{s}']['initial']['external_schedule'] == ref['initial']['external_schedule']
                  and [t['uniforms_sha256'] for t in arms[f'{k}_{s}']['neural']] == uni for k in KINDS)
    checks['I2_common_rng_within_seed'] = bool(i2)
    ref = arms['C0_1']
    checks['I3_reproduces_step_c'] = (
        len(step_c['neural']) == c.TICKS and len(step_c['samples']) == c.STEPS + 1
        and all(x['fired'] == y['fired'] and x['uniforms_sha256'] == y['uniforms_sha256']
                and x['hair_delivered'] == y['hair_delivered'] for x, y in zip(ref['neural'], step_c['neural']))
        and all(x['qpos'] == y['qpos'] for x, y in zip(ref['samples'], step_c['samples'])))
    v3_inv = {n: ref['initial']['channels'][n] for n in v3_names}
    v3_idx = {ch['index'] for ch in v3_inv.values()}
    i4, first, offs = True, {}, {}
    for s in SEEDS:
        c0 = arms[f'C0_{s}']
        base = c0['samples'][1]['commanded_joints']
        i4 &= set(c0['initial']['channels']) == set(v3_names) and not c0['hypothesis_channels']
        i4 &= all(s_['commanded_joints'][i] == base[i] for s_ in c0['samples'][1:] for i in indices.values())
        for k in ('CAND', 'FLIP'):
            arm = f'{k}_{s}'
            a = arms[arm]
            i4 &= ({n: a['initial']['channels'].get(n) for n in v3_names} == v3_inv
                   and set(a['initial']['channels']) == set(v3_names) | set(CANDIDATES)
                   and a['hypothesis_channels'] == sorted(CANDIDATES)
                   and a['definitions_sha256'] == expected_hashes[KINDS[k]])
            outside = [i for i in range(42) if i not in v3_idx and i not in indices.values()]
            i4 &= all(x['commanded_joints'][i] == y['commanded_joints'][i]
                      for x, y in zip(a['samples'][1:], c0['samples'][1:]) for i in outside)
            off = offsets(a, base, indices)
            i4 &= all(abs(x) <= BOUND + loop.EPS for v in off.values() for x in v)
            offs[arm] = off
            first[arm] = loop.first_command_change(a, list(indices.values()), base)
        i4 &= {n: arms[f'C0_{s}']['initial']['channels'][n] for n in v3_names} == v3_inv
    checks['I4_channels_bounds'] = bool(i4)
    i5 = True
    for arm, k in first.items():
        a, c0 = arms[arm], arms[f'C0_{split(arm)[1]}']
        k = len(a['samples']) if k is None else k
        t_k = a['samples'][k]['time_s']*1000. if k < len(a['samples']) else float('inf')
        i5 &= all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                  for x, y in zip(a['samples'][:k], c0['samples'][:k]))
        i5 &= all(x['fired'] == y['fired'] for x, y in zip(a['neural'], c0['neural']) if x['time_ms'] < t_k)
    checks['I5_prefix_within_seed'] = bool(i5)
    tick1 = [arms[f'C0_{s}']['neural'][0]['uniforms_sha256'] for s in SEEDS]
    checks['I6_seeds_applied'] = (len(set(tick1)) == len(SEEDS)
                                  and all(arms[f'{k}_{s}']['initial'].get('cns_seed') == s for s in SEEDS for k in KINDS))
    return checks, dict(first_command_sample=first, offsets=offs)


def evaluate(arms, step_c, expected_hashes, v3_names, indices, bodymap=None):
    checks, audit = integrity(arms, step_c, expected_hashes, v3_names, indices)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks,
                    first_command_sample=audit.get('first_command_sample'))
    per_seed, labels, flags = {}, {}, {}
    hair0, delta = {}, {}
    for s in SEEDS:
        c0 = arms[f'C0_{s}']
        hair0[s] = loop.mean_by_leg(c0, 'hair_rate_hz')
        f0 = loop.mean_by_leg(c0, 'hair_forward')
        delta[s] = {k: {leg: loop.mean_by_leg(arms[f'{k}_{s}'], 'hair_forward')[leg] - f0[leg] for leg in hp.LEGS}
                    for k in ('CAND', 'FLIP')}
    tilt = {k: [c.tilt_deg(x['qpos']) for x in a['samples']] for k, a in arms.items()}
    rollover = any(t > 90 for v in tilt.values() for t in v)
    for name in CANDIDATES:
        leg = LEG_OF[name]
        rows, passes = {}, []
        for s in SEEDS:
            firing = hair0[s][leg] > 0
            ok = seed_pass(firing, delta[s]['CAND'][leg], delta[s]['FLIP'][leg])
            passes.append(ok)
            rows[s] = dict(firing=firing, c0_hair_rate_hz=hair0[s][leg], d_cand=delta[s]['CAND'][leg],
                           d_flip=delta[s]['FLIP'][leg], passed=ok)
        near = {}
        for arm, off in audit['offsets'].items():
            w = in_window(arms[arm])
            vals = [abs(x) for x, inside in zip(off[name], w) if inside]
            near[arm] = float(np.mean([v >= BOUND - NEAR_BOUND for v in vals]))
        per_seed[name] = rows
        labels[name] = label(passes)
        flags[name] = dict(BOUND_LIMITED=any(v > BOUND_FRACTION for v in near.values()), near_bound_fraction=near,
                           ROLLOVER=rollover)
    out = dict(status='INTEGRITY_ACCEPTED', checks=checks, labels=labels, per_seed=per_seed, flags=flags,
               delta_f_all_legs=delta, c0_hair_rate_hz=hair0,
               first_command_sample=audit['first_command_sample'],
               channel_offsets_rad={arm: {n: dict(mean=float(np.mean(v)), max_abs=float(np.max(np.abs(v))))
                                          for n, v in off.items()} for arm, off in audit['offsets'].items()},
               tilt_deg={k: dict(mean=float(np.mean(v)), peak=float(np.max(v))) for k, v in tilt.items()})
    if bodymap is not None:
        sets, per_leg = c.mn_sets(bodymap)
        out['coxa_mn_rates_per_leg_hz'] = {k: {leg: c.rate(a, ids) for leg, ids in per_leg.items()} for k, a in arms.items()}
        out['hair_rate_hz'] = {k: loop.mean_by_leg(a, 'hair_rate_hz') for k, a in arms.items()}
        out['hair_delivered'] = {k: sum(len(t['hair_delivered']) for t in a['neural']) for k, a in arms.items()}
        out['first_physical_divergence_vs_C0'] = {
            k: next((i for i, (x, y) in enumerate(zip(a['samples'], arms[f'C0_{split(k)[1]}']['samples']))
                     if x['qpos'] != y['qpos']), None) for k, a in arms.items() if not k.startswith('C0')}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hashes', action='store_true', help='print candidate definition hashes')
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--step-c-dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    saved = loop.d2_channels(loop.protocol())
    if args.hashes:
        print(json.dumps({k: dict(sha256=defs_sha256(candidate_defs(k, saved)),
                                  action_index={n: d['action_index'] for n, d in candidate_defs(k, saved).items()},
                                  coordinate_sign={n: d['coordinate_sign'] for n, d in candidate_defs(k, saved).items()})
                          for k in ('H1', 'H1_FLIP')}, indent=1))
        return 0
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
    raw = args.step_c_dir/'A_ON.json.gz'
    if loop.sha(raw) != spec['sources']['step_c_a_on']['sha256']:
        raise SystemExit('Step C A_ON raw identity mismatch')
    expected = {k: spec['candidates'][k]['sha256'] for k in ('H1', 'H1_FLIP')}
    if any(defs_sha256(candidate_defs(k, saved)) != h for k, h in expected.items()):
        raise SystemExit('candidate definitions differ from preregistration')
    indices = {n: d['action_index'] for n, d in candidate_defs('H1', saved).items()}
    folder = args.evaluate
    arms = {k: c.load(folder/f'{k}.json.gz') for k in ARMS}
    hashes = {k: loop.sha(folder/f'{k}.json.gz') for k in ARMS}
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    report = dict(schema='coxa-admission-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=evaluate(arms, c.load(raw), expected, tuple(v3.V3_MOTOR), indices, bodymap),
                  interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    e = report['evaluation']
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'labels', 'per_seed', 'flags')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
