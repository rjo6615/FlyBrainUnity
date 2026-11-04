"""Push response and offset yoke on six new seeds: replication and noise estimate (V1).

Preregistered in docs/evidence/coxa-push-replication-v1/protocol.json (design:
docs/COXA_PUSH_REPLICATION_V1.md). 55 fixed arms: REPRO_N0_1 plus {N, C, Y} x {0, F, B} x
never-used CNS seeds 7-12, one fresh process each. The N/C arms are the push-response arms
and the Y arms the offset-yoke arms (coxa 0/7/14/28 yoked to this run's own C0_s); both
modules are reused by import and not edited. Their seed sets are fixed, so this module only
adds seed-generic Trial constructors and the replication evaluator.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from . import coxa_admission as ca
from . import coxa_hypothesis_loop as loop
from . import coxa_offset_yoke as yk
from . import coxa_push_response as pr
from . import hair_plate_posture as c
from . import tactile_recovery_metrics as metrics
from .tactile_boundary import native

ROOT = pr.ROOT
PROTOCOL = 'docs/evidence/coxa-push-replication-v1/protocol.json'
PROTOCOL_SHA256 = '01a6ea1cb14d64daa0f4789701d4326874f2c9d38e1fd07397e869b2463c9404'
SCHEMA = 'coxa-push-replication-arm-v1'
SEEDS = (7, 8, 9, 10, 11, 12)
OLD_SEEDS = pr.SEEDS
SETS = ('N', 'C', 'Y')
REPRO = 'REPRO_N0_1'
ARMS = (REPRO,) + tuple(f'{k}{p}_{s}' for s in SEEDS for k in SETS for p in pr.PUSHES)
INDICES = yk.INDICES


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    yk.protocol()  # also locks the push-response protocol and the H1 action indices
    return json.loads(raw)


def split(arm):
    if arm == REPRO:
        return 'N', '0', 1
    head, seed = arm.rsplit('_', 1)
    if len(head) != 2 or head[0] not in SETS or head[1] not in pr.PUSHES or int(seed) not in SEEDS:
        raise ValueError('unknown arm')
    return head[0], head[1], int(seed)


def block(seed):
    return tuple(f'{k}{p}_{seed}' for k in SETS for p in pr.PUSHES)


# ---- adapter (seed-generic constructors; behaviour inherited unchanged) ---------------

class PushTrial(pr.Trial):
    def __init__(self, arm):
        kind, push, seed = split(arm)
        loop.Trial.__init__(self, arm)  # pr.Trial.__init__ only adds its fixed seed check
        self.kind, self.push, self.seed = kind, push, seed


class YokeTrial(yk.Trial):
    def __init__(self, arm, actions):
        _, push, seed = split(arm)
        loop.Trial.__init__(self, arm)
        self.kind, self.push, self.seed = 'Y', push, seed
        self.yoke_arm, self.actions = arm, actions
        self.sim = self.original_sim_step = None
        self.proposed = self.applied = None


def smoke_schedule(source):
    values = np.asarray([s['commanded_joints'] for s in source['samples'][1:]], dtype=float)
    if values.ndim != 2 or values.shape[1] != 42 or not np.isfinite(values).all():
        raise ValueError('finite archived action schedule required')
    return values


def run_arm(arm, source=None, source_sha256=None, progress=print, steps=c.STEPS):
    spec = protocol()
    kind, push, seed = split(arm)
    defs = None
    if kind == 'C':
        defs = pr.candidate_defs('H1', loop.d2_channels(loop.protocol()))
        if ca.defs_sha256(defs) != pr.protocol()['candidates']['H1']['sha256']:
            raise RuntimeError('candidate definitions differ from preregistration')
    if kind == 'Y':
        actions = yk.schedule(source) if steps == c.STEPS else smoke_schedule(source)
        trial = YokeTrial(arm, actions)
    else:
        trial = PushTrial(arm)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256, cns_seed=seed, push=push,
                  hypothesis_channels=sorted(defs) if defs else [], label=pr.LABEL if defs else None,
                  definitions_sha256=ca.defs_sha256(defs) if defs else None)
    if kind == 'Y':
        result.update(source_arm=f'C0_{seed}', source_sha256=source_sha256, yoke_indices=INDICES)
    session = None
    try:
        session = pr.create_session(trial, 'H1' if defs else None, defs)
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


# ---- evaluation (pure on arm records; one seed block in memory at a time) -------------

def complete(a):
    return a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1 and len(a['neural']) == c.TICKS


def seed_checks(arms, s, v3_names, def_sha, c0_sha):
    """Integrity for one seed block of 9 arms (I1, I3-I7 parts)."""
    out = dict(I1=all(complete(a) for a in arms.values()))
    if not out['I1']:
        return out
    n0 = arms[f'N0_{s}']
    uni = [t['uniforms_sha256'] for t in n0['neural']]
    out['I3'] = all(a['initial']['external_schedule'] == n0['initial']['external_schedule']
                    and [t['uniforms_sha256'] for t in a['neural']] == uni for a in arms.values())
    out['I4'] = all(pr.force_ok(a, split(k)[1]) for k, a in arms.items())
    v3_inv = {n: n0['initial']['channels'][n] for n in v3_names}
    v3_idx = {ch['index'] for ch in v3_inv.values()}
    idx = list(INDICES.values())
    outside = [i for i in range(42) if i not in v3_idx and i not in idx]
    i5 = i6 = i7 = True
    for p in pr.PUSHES:
        n, cc, y = arms[f'N{p}_{s}'], arms[f'C{p}_{s}'], arms[f'Y{p}_{s}']
        base = n['samples'][1]['commanded_joints']
        i5 &= (set(n['initial']['channels']) == set(v3_names) and not n['hypothesis_channels']
               and {k: n['initial']['channels'][k] for k in v3_names} == v3_inv
               and all(x['commanded_joints'][i] == base[i] for x in n['samples'][1:] for i in idx))
        i5 &= ({k: cc['initial']['channels'].get(k) for k in v3_names} == v3_inv
               and set(cc['initial']['channels']) == set(v3_names) | set(pr.CANDIDATES)
               and cc['hypothesis_channels'] == sorted(pr.CANDIDATES) and cc['label'] == pr.LABEL
               and cc['definitions_sha256'] == def_sha
               and all(x['commanded_joints'][i] == z['commanded_joints'][i]
                       for x, z in zip(cc['samples'][1:], n['samples'][1:]) for i in outside)
               and all(abs(v) <= loop.BOUND + loop.EPS for vs in ca.offsets(cc, base, INDICES).values() for v in vs))
        i6 &= (y.get('source_sha256') == c0_sha and yk.yoke_audit(y, arms[f'C0_{s}'])
               and y['initial']['channels'] == v3_inv and y['hypothesis_channels'] == [] and y['label'] is None)
        kf = loop.first_command_change(cc, idx, base)
        kf = len(cc['samples']) if kf is None else kf
        t_k = cc['samples'][kf]['time_s']*1000. if kf < len(cc['samples']) else math.inf
        i7 &= (all(x['qpos'] == z['qpos'] and x['commanded_joints'] == z['commanded_joints']
                   for x, z in zip(cc['samples'][:kf], n['samples'][:kf]))
               and all(x['fired'] == z['fired'] for x, z in zip(cc['neural'], n['neural']) if x['time_ms'] < t_k))
        if p != '0':
            for k in SETS:
                i7 &= pr.prefix_equal(arms[f'{k}{p}_{s}'], arms[f'{k}0_{s}'], pr.START + 1, pr.START*pr.DT*1000.)
    i6 &= yk.reproduces(arms[f'Y0_{s}'], arms[f'C0_{s}'])
    i7 &= all(a['initial'].get('cns_seed') == s for a in arms.values())
    out.update(I5=bool(i5), I6=bool(i6), I7=bool(i7))
    return out


def seed_measures(arms, s):
    traces = {k: metrics.trace(a, [x['supports'] for x in a['samples']]) for k, a in arms.items()}
    d_int, responses = {}, {}
    for k in arms:
        kind, push, _ = split(k)
        if push == '0':
            continue
        ctrl = traces[f'{kind}0_{s}']
        d_int[k] = pr.deviation_integral(traces[k], ctrl)
        responses[k] = metrics.response(traces[k], ctrl, start=pr.START, stop=pr.STOP)
    names = sorted(INDICES, key=INDICES.get)
    base_all, base_win = yk.coxa(arms[f'C0_{s}']), yk.coxa(arms[f'C0_{s}'], slice(pr.FIRST_CLEARED, None))
    modulation = {}
    for p in ('F', 'B'):
        a = arms[f'C{p}_{s}']
        diff = np.abs(yk.coxa(a, slice(pr.FIRST_CLEARED, None)) - base_win)
        modulation[f'C{p}_{s}'] = dict(cleared_mean_abs_rad={n: float(v) for n, v in zip(names, diff.mean(axis=0))},
                                       differing_transitions={n: int(v) for n, v in zip(names, (yk.coxa(a) != base_all).sum(axis=0))})
    tilt = {k: dict(mean=float(np.mean([c.tilt_deg(x['qpos']) for x in a['samples']])),
                    peak=float(np.max([c.tilt_deg(x['qpos']) for x in a['samples']]))) for k, a in arms.items()}
    return dict(deviation_integral_mm_s=d_int, responses=responses, c_arm_loop_modulation=modulation, tilt_deg=tilt,
                pulse={f'N{p}_{s}': responses[f'N{p}_{s}']['resolved_perturbation'] for p in ('F', 'B')},
                tick1=arms[f'N0_{s}']['neural'][0]['uniforms_sha256'])


def q1(r):
    if all(x >= pr.AMPLIFY for x in r):
        return 'AMPLIFICATION_REPLICATES'
    return 'AMPLIFICATION_DIRECTIONAL' if all(x > 1. for x in r) else 'AMPLIFICATION_NOT_REPLICATED'


def q2b(e):
    if all(x < 1. for x in e):
        return 'FREE_COMMANDS_INCREASE_D'
    return 'FREE_COMMANDS_DECREASE_D' if all(x > 1. for x in e) else 'NO_CONSISTENT_SIGN'


def ratios(d, seeds, p):
    return dict(R=[d[f'C{p}_{s}']/d[f'N{p}_{s}'] for s in seeds], E=[d[f'Y{p}_{s}']/d[f'C{p}_{s}'] for s in seeds],
                R_Y=[d[f'Y{p}_{s}']/d[f'N{p}_{s}'] for s in seeds])


def spread(values):
    logs = np.log(np.asarray(values, dtype=float))
    return dict(n=len(values), median=float(np.median(values)), min=float(np.min(values)), max=float(np.max(values)),
                log_mean=float(np.mean(logs)), log_sd=float(np.std(logs, ddof=1)))


def evaluate(load, repro_ref, repro_ok, old_d, old_tick1, v3_names, def_sha, c0_sha):
    """load(arm) -> arm record; old_d: seeds 1-3 D values (N/C/Y pushed arms) from the verified reports."""
    repro = load(REPRO)
    checks = dict(I1_complete=complete(repro), I2_reproduction=bool(repro_ok) and complete(repro)
                  and yk.reproduces(repro, repro_ref))
    del repro
    parts, measures = [], {}
    for s in SEEDS:
        arms = {k: load(k) for k in block(s)}
        part = seed_checks(arms, s, v3_names, def_sha, c0_sha[s])
        parts.append(part)
        if all(part.values()):
            measures[s] = seed_measures(arms, s)
        del arms
        gc.collect()
    checks['I1_complete'] &= all(p['I1'] for p in parts)
    for key, name in (('I3', 'I3_common_rng'), ('I4', 'I4_exact_force'), ('I5', 'I5_channels_bounds'),
                      ('I6', 'I6_yoke'), ('I7', 'I7_prefixes_seeds')):
        checks[name] = all(p.get(key, False) for p in parts)
    if all(checks.values()):
        tick1 = [measures[s]['tick1'] for s in SEEDS]
        checks['I7_prefixes_seeds'] = len(set(tick1)) == len(SEEDS) and not set(tick1) & set(old_tick1)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks)
    d_int = {k: v for m in measures.values() for k, v in m['deviation_integral_mm_s'].items()}
    pulse = {k: v for m in measures.values() for k, v in m['pulse'].items()}
    base = dict(checks=checks, pulse_resolved=pulse, deviation_integral_mm_s=d_int,
                responses={k: v for m in measures.values() for k, v in m['responses'].items()},
                c_arm_loop_modulation={k: v for m in measures.values() for k, v in m['c_arm_loop_modulation'].items()},
                tilt_deg={k: v for m in measures.values() for k, v in m['tilt_deg'].items()})
    if not all(pulse.values()):
        return dict(status='INCONCLUSIVE_PULSE', **base)
    labels, new, pooled = {}, {}, {}
    for p in ('F', 'B'):
        r = ratios(d_int, SEEDS, p)
        labels[p] = dict(Q1=q1(r['R']), Q2a=yk.label(r['R_Y'], r['E']), Q2b=q2b(r['E']))
        new[p] = r
        old = ratios(old_d, OLD_SEEDS, p)
        pooled[p] = {m: spread(old[m] + r[m]) for m in ('R', 'E', 'R_Y')}
        dn = [old_d[f'N{p}_{s}'] for s in OLD_SEEDS] + [d_int[f'N{p}_{s}'] for s in SEEDS]
        pooled[p]['D_N'] = dict(mean=float(np.mean(dn)), sd=float(np.std(dn, ddof=1)))
        pooled[p]['old_seed_ratios'] = old
    return dict(status='INTEGRITY_ACCEPTED', labels=labels, ratios=new, pooled_seeds_1_3_and_7_12=pooled, **base)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--source', type=Path, help='C0_s archive for a Y arm')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--repro-ref', type=Path, help='push-response N0_1 raw arm')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = protocol()
    if args.arm:
        kind = split(args.arm)[0]
        source = digest = None
        if kind == 'Y':
            if args.source is None:
                raise SystemExit('a Y arm requires --source C0_s')
            digest, source = loop.sha(args.source), c.load(args.source)
            if args.smoke_steps is None and (source.get('arm') != f'C0_{split(args.arm)[2]}' or source['run_status'] != 'COMPLETE'):
                raise SystemExit('Y source must be this run\'s COMPLETE C0_s')
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/(f'{args.arm}.json.gz' if args.smoke_steps is None else f'smoke_{args.arm}.json.gz')
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm, source, digest, steps=args.smoke_steps or c.STEPS)
        out = c.save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=out)))
        return 0 if result['run_status'] in ('COMPLETE', 'SMOKE') else 1
    from ..embodiment import live_v3_motor_interface as v3
    src = spec['sources']
    reports_ok = (loop.sha(ROOT/src['push_response_report']) == src['push_response_report_sha256']
                  and loop.sha(ROOT/src['offset_yoke_report']) == src['offset_yoke_report_sha256'])
    if not reports_ok:
        raise SystemExit('earlier report identity mismatch')
    old_d = {**json.loads((ROOT/src['push_response_report']).read_text())['evaluation']['deviation_integral_mm_s'],
             **json.loads((ROOT/src['offset_yoke_report']).read_text())['evaluation']['deviation_integral_mm_s']}
    repro_ok = loop.sha(args.repro_ref) == src['repro_reference']['sha256']
    folder = args.evaluate
    hashes = {k: loop.sha(folder/f'{k}.json.gz') for k in ARMS}
    e = evaluate(lambda k: c.load(folder/f'{k}.json.gz'), c.load(args.repro_ref), repro_ok, old_d,
                 list(src['old_seed_tick1_uniforms'].values()), tuple(v3.V3_MOTOR),
                 pr.protocol()['candidates']['H1']['sha256'], {s: hashes[f'C0_{s}'] for s in SEEDS})
    report = dict(schema='coxa-push-replication-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=e, interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'pulse_resolved', 'labels', 'ratios')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
