"""Antennal gravity Step D3: open-loop command yoke of the Step D ON falls (V1).

Preregistered in docs/evidence/jo-command-yoke-v1/protocol.json (design:
docs/JO_COMMAND_YOKE_V1.md). 45 fixed arms: 9 conditions x the 5 fallen Step D ON DOWN20
arms. Each arm runs the Step D OFF_DOWN20 trial of the source's seed, and at every outgoing
transition all 42 commanded coordinates are replaced (coxa_offset_yoke sim.step pattern)
by a declared mix of the source's ON archive and the matched OFF archive. The CNS runs but
its output does not reach the body. jo_zone_crossing, coxa_offset_yoke and the kernel are
unchanged.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from . import antennal_gravity_live as live
from . import coxa_offset_yoke as yk
from . import coxa_push_response as pr
from . import hair_plate_posture as c
from . import jo_zone_crossing as zc
from .tactile_boundary import native

ROOT = c.ROOT
PROTOCOL = 'docs/evidence/jo-command-yoke-v1/protocol.json'
PROTOCOL_SHA256 = '3fbb281de2c0875465d66c06ed9996f9cd42ec5a9f728622ed7bbf0fd609b66d'
SCHEMA = 'jo-command-yoke-arm-v1'
REPORT = 'docs/evidence/jo-zone-crossing-v1/run/report.json'
REPORT_SHA256 = 'e64811f7253478b0f2d91031d5b63d9acc8ea2c86ed4878959c49d9e3a80f571'
SOURCES = ('G1_DOWN20_19', 'G1_DOWN20_21', 'G1_DOWN20_24', 'FLIP_DOWN20_23', 'FLIP_DOWN20_24')
CONDITIONS = ('FULL_ON', 'ONLY_FRONT', 'ONLY_MIDDLE', 'ONLY_HIND', 'NO_FRONT', 'NO_MIDDLE', 'NO_HIND',
              'PRE_ONLY', 'POST_ONLY')
ARMS = tuple(f'{k}__{s}' for s in SOURCES for k in CONDITIONS)
GROUPS = {'FRONT': (3, 4, 5, 6, 24, 25, 26, 27), 'MIDDLE': (10, 11, 12, 31, 32, 33), 'HIND': (17, 18, 19, 38, 39, 40)}
ADMITTED = tuple(sorted(i for g in GROUPS.values() for i in g))
UNADMITTED = tuple(i for i in range(42) if i not in ADMITTED)
TILT_TRANSITION = c.EVENT_STATE    # transition 5005 is the first under tilted gravity
FALL_DEG = 45.
GROUP_LABELS = {(True, False): 'SUFFICIENT_AND_NECESSARY', (True, True): 'SUFFICIENT_NOT_NECESSARY',
                (False, False): 'NECESSARY_NOT_SUFFICIENT', (False, True): 'NEITHER'}


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    spec = json.loads(raw)
    if {k: tuple(v) for k, v in spec['groups'].items() if k in GROUPS} != GROUPS:
        raise ValueError('group indices differ from the protocol')
    return spec


def split(arm):
    cond, source = arm.split('__')
    if cond not in CONDITIONS or source not in SOURCES:
        raise ValueError('unknown arm')
    return cond, source


def off_of(source):
    return f"OFF_DOWN20_{source.rsplit('_', 1)[1]}"


def on_mask(cond, n):
    """Coordinates taken from the ON archive at transition n (others from OFF)."""
    m = np.zeros(42, dtype=bool)
    if cond == 'FULL_ON':
        m[list(ADMITTED)] = True
    elif cond.startswith('ONLY_'):
        m[list(GROUPS[cond[5:]])] = True
    elif cond.startswith('NO_'):
        m[list(ADMITTED)] = True
        m[list(GROUPS[cond[3:]])] = False
    elif cond == 'PRE_ONLY':
        m[list(ADMITTED)] = n < TILT_TRANSITION
    elif cond == 'POST_ONLY':
        m[list(ADMITTED)] = n >= TILT_TRANSITION
    else:
        raise ValueError('unknown condition')
    return m


def mix(cond, on_schedule, off_schedule):
    """Declared applied schedule (n x 42) from the two archived schedules."""
    on_schedule, off_schedule = np.asarray(on_schedule, float), np.asarray(off_schedule, float)
    if on_schedule.shape != off_schedule.shape or on_schedule.shape[1] != 42:
        raise ValueError('matched 42-coordinate schedules required')
    out = off_schedule.copy()
    for n in range(len(out)):
        m = on_mask(cond, n)
        out[n, m] = on_schedule[n, m]
    return out


class Trial(zc.Trial):
    """Step D OFF_DOWN20 trial with all 42 applied coordinates yoked to a declared schedule."""

    def __init__(self, arm, actions, event_state=c.EVENT_STATE):
        _, source = split(arm)
        super().__init__(off_of(source), event_state)
        self.yoke_arm, self.actions = arm, np.asarray(actions, dtype=float)
        self.sim = self.original_sim_step = None
        self.applied = None

    def bind(self, sim, physics, obs):
        super().bind(sim, physics, obs)
        self.sim, self.original_sim_step = sim, sim.step
        sim.step = self.apply

    def apply(self, action):
        index = len(self.samples) - 1
        if not 0 <= index < len(self.actions) or set(action) != {'joints', 'adhesion'}:
            raise ValueError('invalid outgoing transition or action fields')
        adhesion = np.asarray(action['adhesion'], dtype=float)
        if adhesion.shape != (6,) or np.any(adhesion != 0.):
            raise RuntimeError('adhesion must be all zero')
        joints = self.actions[index].copy()
        self.applied = dict(joints=joints, adhesion=adhesion.copy())
        return self.original_sim_step(dict(joints=joints.copy(), adhesion=adhesion.copy()))

    def capture(self, physics, obs, action):
        applied = None if action is None else self.applied
        if action is not None and applied is None:
            raise RuntimeError('missing applied action')
        super().capture(physics, obs, applied)  # the record holds what was applied
        self.samples[-1]['adhesion_zero'] = None if applied is None else bool(np.all(applied['adhesion'] == 0.))

    def detach(self):
        if self.original_sim_step is not None:
            self.sim.step = self.original_sim_step
        super().detach()


def load_archives(folder, source, spec):
    out = {}
    for name in (source, off_of(source)):
        path = Path(folder)/f'{name}.json.gz'
        if live.sha(path) != spec['sources']['archives'][name]:
            raise RuntimeError(f'archive {name} differs from preregistration')
        out[name] = c.load(path)
    return out[source], out[off_of(source)]


def run_arm(arm, folder, progress=print, steps=c.STEPS):
    spec = protocol()
    cond, source = split(arm)
    on, off = load_archives(folder, source, spec)
    actions = mix(cond, yk.schedule(on), yk.schedule(off))
    del on, off
    gc.collect()
    trial = Trial(arm, actions)
    seed = trial.seed
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256, condition=cond,
                  source=source, off_source=off_of(source), cns_seed=seed,
                  archive_sha256={k: spec['sources']['archives'][k] for k in (source, off_of(source))},
                  not_claimed=spec['not_claimed'])
    session = None
    try:
        session = pr.create_session(trial, None, None)
        progress(f'{arm}: fresh CNS/physics initialization; all 42 coordinates yoked ({cond})', flush=True)
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
        result.update(samples=trial.samples, neural=trial.neural, initial=trial.initial, event=trial.event,
                      tilt_event=trial.tilt_event)
    return result


# ---- evaluation (pure on arm records) ------------------------------------------------

def yoke_audit(arm, expected):
    rows = arm['samples']
    if len(rows) != len(expected) + 1 or rows[0]['commanded_joints'] is not None:
        return False
    return all(row['adhesion_zero'] is True and np.array_equal(np.asarray(row['commanded_joints'], float), expected[i])
               for i, row in enumerate(rows[1:]))


def gravity_ok(arm):
    g = zc.tilt_gravity('DOWN20')
    return all((s['gravity'] == list(zc.G0)) if i <= c.EVENT_STATE else (s['gravity'] == g)
               for i, s in enumerate(arm['samples'])) and all(
        not s['applied_body_wrenches'] and s['external_applied_max'] == 0. and s['generalized_applied_max'] == 0
        for s in arm['samples'])


def outcome(arm):
    tilt = np.array([live.body_angles(s)[0] for s in arm['samples']])
    after = tilt[c.EVENT_STATE + 1:]
    hit = np.nonzero(after >= FALL_DEG)[0]
    return dict(falls=bool(hit.size), t_fall_ms=None if not hit.size else float((hit[0] + 1)*.1),
                peak_tilt_deg=float(after.max()))


def first_qpos_difference(a, b):
    return next((i for i, (x, y) in enumerate(zip(a['samples'], b['samples'])) if x['qpos'] != y['qpos']), None)


def group_label(only_falls, no_falls):
    return GROUP_LABELS[(bool(only_falls), bool(no_falls))]


def source_labels(out):
    """out: {condition: outcome} for one source."""
    groups = {g: group_label(out[f'ONLY_{g}']['falls'], out[f'NO_{g}']['falls']) for g in GROUPS}
    timing = dict(PRE_TILT_SUFFICIENT=out['PRE_ONLY']['falls'], POST_TILT_SUFFICIENT=out['POST_ONLY']['falls'])
    return dict(groups=groups, timing=timing)


def consistency(labels):
    """Within each assignment: CONSISTENT value or MIXED, per group and timing label."""
    out = {}
    for t in ('G1', 'FLIP'):
        src = [s for s in SOURCES if s.startswith(t + '_')]
        out[t] = dict(
            groups={g: (labels[src[0]]['groups'][g] if len({labels[s]['groups'][g] for s in src}) == 1 else 'MIXED')
                    for g in GROUPS},
            timing={k: (labels[src[0]]['timing'][k] if len({labels[s]['timing'][k] for s in src}) == 1 else 'MIXED')
                    for k in ('PRE_TILT_SUFFICIENT', 'POST_TILT_SUFFICIENT')})
    return out


def expectations(labels, outcomes):
    flip = [s for s in SOURCES if s.startswith('FLIP_')]
    g1 = [s for s in SOURCES if s.startswith('G1_')]
    e1 = all(labels[s]['groups']['FRONT'] == 'SUFFICIENT_AND_NECESSARY' and outcomes[s]['POST_ONLY']['falls']
             for s in flip)
    e2 = all(outcomes[s]['PRE_ONLY']['falls'] for s in g1)
    return dict(E1_FLIP='HELD' if e1 else 'NOT_HELD', E2_G1='HELD' if e2 else 'NOT_HELD')


def evaluate(load, load_archive, hashes_ok):
    """load(arm) -> yoke arm; load_archive(name) -> Step D archive; hashes_ok: Y5 file identity."""
    checks = dict(Y1_complete=True, Y2_reproduction=True, Y3_yoke_audit=True, Y4_gravity=True,
                  Y5_sources=bool(hashes_ok))
    outcomes, unadmitted_equal, divergence = {}, {}, {}
    for source in SOURCES:
        on, off = load_archive(source), load_archive(off_of(source))
        on_s, off_s = yk.schedule(on), yk.schedule(off)
        unadmitted_equal[source] = bool(np.array_equal(on_s[:, list(UNADMITTED)], off_s[:, list(UNADMITTED)]))
        outcomes[source], divergence[source] = {}, {}
        for cond in CONDITIONS:
            name = f'{cond}__{source}'
            a = load(name)
            checks['Y1_complete'] &= (a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1
                                      and len(a['neural']) == c.TICKS)
            checks['Y3_yoke_audit'] &= yoke_audit(a, mix(cond, on_s, off_s))
            checks['Y4_gravity'] &= gravity_ok(a)
            checks['Y5_sources'] &= (a.get('source') == source and a.get('cns_seed') == int(source.rsplit('_', 1)[1]))
            if cond == 'FULL_ON':
                checks['Y2_reproduction'] &= (len(a['samples']) == len(on['samples']) and
                                              all(x['qpos'] == y['qpos'] for x, y in zip(a['samples'], on['samples'])))
            outcomes[source][cond] = outcome(a)
            divergence[source][cond] = dict(first_qpos_diff_from_off=first_qpos_difference(a, off),
                                            first_qpos_diff_from_on=first_qpos_difference(a, on))
            del a
            gc.collect()
        del on, off
        gc.collect()
    checks = {k: bool(v) for k, v in checks.items()}
    base = dict(checks=checks, outcomes=outcomes, unadmitted_identical_on_off=unadmitted_equal,
                first_qpos_divergence_state=divergence)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', **base)
    labels = {s: source_labels(outcomes[s]) for s in SOURCES}
    return dict(status='INTEGRITY_ACCEPTED', labels=labels, consistency=consistency(labels),
                expectations=expectations(labels, outcomes), **base)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--archives', type=Path, required=True, help='folder with the Step D raw arms')
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = protocol()
    if live.sha(ROOT/REPORT) != REPORT_SHA256:
        raise ValueError('Step D report identity mismatch')
    if args.arm:
        smoke = args.smoke_steps is not None
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/(f'smoke_{args.arm}.json.gz' if smoke else f'{args.arm}.json.gz')
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm, args.archives, steps=args.smoke_steps or c.STEPS)
        out = c.save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=out)))
        return 0 if result['run_status'] in ('COMPLETE', 'SMOKE') else 1
    names = list(spec['sources']['archives'])
    hashes_ok = all(live.sha(args.archives/f'{k}.json.gz') == spec['sources']['archives'][k] for k in names)
    hashes = {k: live.sha(args.evaluate/f'{k}.json.gz') for k in ARMS}
    e = evaluate(lambda k: c.load(args.evaluate/f'{k}.json.gz'), lambda k: c.load(args.archives/f'{k}.json.gz'),
                 hashes_ok)
    report = dict(schema='jo-command-yoke-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=e, interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'labels', 'consistency', 'expectations')}),
                     indent=1))
    print(json.dumps(native({s: {k: (v['falls'], v['t_fall_ms']) for k, v in o.items()}
                             for s, o in e['outcomes'].items()}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
