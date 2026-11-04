"""Open-loop coxa offset yoke: is the push amplification reflex or posture? (V1).

Preregistered in docs/evidence/coxa-offset-yoke-v1/protocol.json (design:
docs/COXA_OFFSET_YOKE_V1.md). Nine fixed arms (Y{0,F,B} x CNS seeds 1-3) in the
push-response context, N configuration (no hypothesis channel). At every outgoing
transition the four H1 coxa actions (0/7/14/28) are replaced by the same-seed
push-response C0_s archive (sample n+1), as in tibia_command_dissection.selected_action;
the other 38 coordinates are applied as proposed. coxa_push_response, the tibia module and
the kernel are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from . import coxa_hypothesis_loop as loop
from . import coxa_push_response as pr
from . import hair_plate_posture as c
from . import tactile_recovery_metrics as metrics
from .tactile_boundary import native

ROOT = pr.ROOT
PROTOCOL = 'docs/evidence/coxa-offset-yoke-v1/protocol.json'
PROTOCOL_SHA256 = '309cade6d121d83e470ff2227e6036c6f6f06ef9332c74955325171d76de2609'
SCHEMA = 'coxa-offset-yoke-arm-v1'
INDICES = {'joint_LFCoxa': 0, 'joint_LMCoxa': 7, 'joint_LHCoxa': 14, 'joint_RMCoxa': 28}
SELECTED = np.asarray(sorted(INDICES.values()), dtype=int)
SEEDS = pr.SEEDS
ARMS = tuple(f'Y{p}_{s}' for s in SEEDS for p in pr.PUSHES)
REFERENCES = tuple(f'{k}{p}_{s}' for s in SEEDS for k in 'NC' for p in pr.PUSHES)
LOW, HIGH = .90, 1.10


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    spec = json.loads(raw)
    if spec['yoke']['indices'] != INDICES or pr.protocol()['candidates']['H1']['action_index'] != INDICES:
        raise ValueError('yoke indices differ from the push-response H1 action indices')
    return spec


def split(arm):
    head, seed = arm.rsplit('_', 1)
    if len(head) != 2 or head[0] != 'Y' or head[1] not in pr.PUSHES or int(seed) not in SEEDS:
        raise ValueError('unknown arm')
    return head[0], head[1], int(seed)


def schedule(source):
    """Archived outgoing actions: transition n applied source samples[n+1]['commanded_joints']."""
    values = np.asarray([s['commanded_joints'] for s in source['samples'][1:]], dtype=float)
    if values.shape != (c.STEPS, 42) or not np.isfinite(values).all():
        raise ValueError('complete finite archived action schedule required')
    return values


def selected_action(proposed, archived):
    proposed = np.asarray(proposed, dtype=float)
    archived = np.asarray(archived, dtype=float)
    if proposed.shape != (42,) or archived.shape != (42,) or not np.isfinite(proposed).all() or not np.isfinite(archived).all():
        raise ValueError('finite 42-coordinate proposed and archived actions required')
    applied = proposed.copy()
    applied[SELECTED] = archived[SELECTED]
    return applied


# ---- adapter -----------------------------------------------------------------------

class Trial(pr.Trial):
    """Push-response N trial with the four coxa actions yoked to an archive at sim.step."""

    def __init__(self, arm, actions):
        _, push, seed = split(arm)
        super().__init__(f'N{push}_{seed}')
        self.yoke_arm, self.actions = arm, actions
        self.sim = self.original_sim_step = None
        self.proposed = self.applied = None

    def bind(self, sim, physics, obs):
        super().bind(sim, physics, obs)
        self.sim, self.original_sim_step = sim, sim.step
        sim.step = self.apply

    def apply(self, action):
        index = len(self.samples) - 1
        if not 0 <= index < len(self.actions) or set(action) != {'joints', 'adhesion'}:
            raise ValueError('invalid outgoing transition or action fields')
        joints = selected_action(action['joints'], self.actions[index])
        self.proposed = np.asarray(action['joints'], dtype=float).tolist()
        self.applied = dict(joints=joints, adhesion=np.asarray(action['adhesion']).copy())
        return self.original_sim_step(dict(joints=joints.copy(), adhesion=self.applied['adhesion'].copy()))

    def capture(self, physics, obs, action):
        applied = None if action is None else self.applied
        if action is not None and applied is None:
            raise RuntimeError('missing applied action')
        super().capture(physics, obs, applied)  # the record holds what was applied
        self.samples[-1]['proposed_joints'] = None if action is None else self.proposed

    def detach(self):
        if self.original_sim_step is not None:
            self.sim.step = self.original_sim_step
        super().detach()


def run_arm(arm, source, source_sha256, progress=print, steps=c.STEPS):
    spec = protocol()
    _, push, seed = split(arm)
    if source_sha256 != spec['sources']['reference_arms'][f'C0_{seed}']:
        raise RuntimeError('yoke source differs from preregistration')
    trial = Trial(arm, schedule(source))
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256, cns_seed=seed, push=push,
                  source_arm=f'C0_{seed}', source_sha256=source_sha256, yoke_indices=INDICES,
                  hypothesis_channels=[], label=None)
    session = None
    try:
        session = pr.create_session(trial, None, None)
        progress(f'{arm}: fresh CNS/physics initialization; coxa 0/7/14/28 yoked to C0_{seed}', flush=True)
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

def yoke_audit(arm, source):
    rows, expected = arm['samples'], schedule(source)
    good = len(rows) == len(expected) + 1 and rows[0].get('proposed_joints') is None
    for i, row in enumerate(rows[1:]):
        if not good or row.get('proposed_joints') is None:
            return False
        good &= np.array_equal(np.asarray(row['commanded_joints'], dtype=float),
                               selected_action(row['proposed_joints'], expected[i]))
    return bool(good)


def reproduces(a, b):
    return (len(a['samples']) == len(b['samples']) and len(a['neural']) == len(b['neural'])
            and all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                    for x, y in zip(a['samples'], b['samples']))
            and all(x['fired'] == y['fired'] and x['uniforms_sha256'] == y['uniforms_sha256']
                    and x['hair_delivered'] == y['hair_delivered'] for x, y in zip(a['neural'], b['neural'])))


def integrity(arms, refs, sources_ok, v3_names):
    checks = dict(I1_complete=all(a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1
                                  and len(a['neural']) == c.TICKS for a in arms.values()),
                  I2_sources_verified=bool(sources_ok))
    if not all(checks.values()):
        return checks
    checks['I3_reproduces_c0'] = all(reproduces(arms[f'Y0_{s}'], refs[f'C0_{s}']) for s in SEEDS)
    i4 = i5 = i6 = i7 = True
    for arm, a in arms.items():
        _, push, s = split(arm)
        n = refs[f'N0_{s}']
        i4 &= (a['initial']['external_schedule'] == n['initial']['external_schedule']
               and [t['uniforms_sha256'] for t in a['neural']] == [t['uniforms_sha256'] for t in n['neural']])
        i5 &= (yoke_audit(a, refs[f'C0_{s}']) and set(a['initial']['channels']) == set(v3_names)
               and a['initial']['channels'] == {k: n['initial']['channels'][k] for k in v3_names}
               and a['hypothesis_channels'] == [] and a['label'] is None)
        i6 &= pr.force_ok(a, push)
        i7 &= a['initial'].get('cns_seed') == s
        if push != '0':
            i7 &= pr.prefix_equal(a, arms[f'Y0_{s}'], pr.START + 1, pr.START*pr.DT*1000.)
    checks.update(I4_common_rng=bool(i4), I5_yoke_audit=bool(i5), I6_exact_force=bool(i6),
                  I7_prefixes_seeds=bool(i7))
    return checks


def label(r_y, e):
    if not all(r >= HIGH for r in r_y):
        return 'OFFSETS_DO_NOT_REPRODUCE'
    return 'OFFSETS_REPRODUCE' if all(LOW <= x <= HIGH for x in e) else 'OFFSETS_PARTLY_REPRODUCE'


def coxa(arm, rows=slice(1, None)):
    return np.asarray([s['commanded_joints'] for s in arm['samples'][rows]], dtype=float)[:, SELECTED]


def evaluate(arms, refs, sources_ok, v3_names):
    checks = integrity(arms, refs, sources_ok, v3_names)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks)
    every = {**refs, **arms}
    traces = {k: metrics.trace(a, [x['supports'] for x in a['samples']]) for k, a in every.items()}
    d_int, responses, fore_aft = {}, {}, {}
    for k in every:
        kind, push, s = k[0], k[1], int(k.rsplit('_', 1)[1])
        if push == '0':
            continue
        ctrl = traces[f'{kind}0_{s}']
        d_int[k] = pr.deviation_integral(traces[k], ctrl)
        if kind == 'Y':
            responses[k] = metrics.response(traces[k], ctrl, start=pr.START, stop=pr.STOP)
            dx = (traces[k]['position'][:, 0] - ctrl['position'][:, 0])*pr.PUSHES[push]
            fore_aft[k] = dict(peak_along_push_mm=float(np.max(dx[pr.START:])), min_along_push_mm=float(np.min(dx[pr.START:])),
                               cleared_mean_along_push_mm=float(np.mean(dx[pr.FIRST_CLEARED:])))
    labels, ratios = {}, {}
    for p in ('F', 'B'):
        r_y = [d_int[f'Y{p}_{s}']/d_int[f'N{p}_{s}'] for s in SEEDS]
        e = [d_int[f'Y{p}_{s}']/d_int[f'C{p}_{s}'] for s in SEEDS]
        labels[p], ratios[p] = label(r_y, e), dict(R_Y=r_y, E=e)
    names = sorted(INDICES, key=INDICES.get)
    modulation, removed = {}, {}
    for s in SEEDS:
        base_all, base_win = coxa(refs[f'C0_{s}']), coxa(refs[f'C0_{s}'], slice(pr.FIRST_CLEARED, None))
        for p in ('F', 'B'):
            arm = refs[f'C{p}_{s}']
            diff = np.abs(coxa(arm, slice(pr.FIRST_CLEARED, None)) - base_win)
            modulation[f'C{p}_{s}'] = dict(
                cleared_mean_abs_rad={n: float(v) for n, v in zip(names, diff.mean(axis=0))},
                differing_transitions={n: int(v) for n, v in zip(names, (coxa(arm) != base_all).sum(axis=0))})
    for k, a in arms.items():
        prop = np.asarray([s['proposed_joints'] for s in a['samples'][1:]], dtype=float)[:, SELECTED]
        removed[k] = {n: float(v) for n, v in zip(names, np.abs(coxa(a) - prop).mean(axis=0))}
    tilt = {k: dict(mean=float(np.mean([c.tilt_deg(x['qpos']) for x in a['samples']])),
                    peak=float(np.max([c.tilt_deg(x['qpos']) for x in a['samples']]))) for k, a in arms.items()}
    return dict(status='INTEGRITY_ACCEPTED', labels=labels, ratios=ratios, checks=checks, deviation_integral_mm_s=d_int,
                responses=responses, fore_aft_deviation=fore_aft, tilt_deg=tilt, c_arm_loop_modulation=modulation,
                y_arm_applied_minus_proposed_mean_abs_rad=removed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--ref-dir', type=Path, required=True, help='push-response raw arms (N*, C*)')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = protocol()
    expected = spec['sources']['reference_arms']
    if args.arm:
        seed = split(args.arm)[2]
        raw = args.ref_dir/f'C0_{seed}.json.gz'
        digest = loop.sha(raw)
        if digest != expected[f'C0_{seed}']:
            raise SystemExit(f'push-response C0_{seed} raw identity mismatch')
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/(f'{args.arm}.json.gz' if args.smoke_steps is None else f'smoke_{args.arm}.json.gz')
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm, c.load(raw), digest, steps=args.smoke_steps or c.STEPS)
        out = c.save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=out)))
        return 0 if result['run_status'] in ('COMPLETE', 'SMOKE') else 1
    from ..embodiment import live_v3_motor_interface as v3
    report_ok = loop.sha(ROOT/spec['sources']['push_response_report']) == spec['sources']['push_response_report_sha256']
    ref_hashes = {k: loop.sha(args.ref_dir/f'{k}.json.gz') for k in REFERENCES}
    sources_ok = report_ok and ref_hashes == expected
    refs = {k: c.load(args.ref_dir/f'{k}.json.gz') for k in REFERENCES}
    arms = {k: c.load(args.evaluate/f'{k}.json.gz') for k in ARMS}
    report = dict(schema='coxa-offset-yoke-report-v1', protocol_sha256=PROTOCOL_SHA256,
                  arm_sha256={k: loop.sha(args.evaluate/f'{k}.json.gz') for k in ARMS}, reference_sha256=ref_hashes,
                  evaluation=evaluate(arms, refs, sources_ok, tuple(v3.V3_MOTOR)),
                  interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    e = report['evaluation']
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'labels', 'ratios', 'deviation_integral_mm_s')}),
                     indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
