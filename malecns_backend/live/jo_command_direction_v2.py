"""Antennal gravity Step D4 v2: direction of the post-tilt command change, live joint ranges.

Preregistered in docs/evidence/jo-command-direction-v2/protocol.json (design:
docs/JO_COMMAND_DIRECTION_V2.md). 15 fixed arms on the D3 open-loop yoke path: POST_NEG,
POST_HALF and POST_SCRAMBLE for each of the 5 fallen Step D ON DOWN20 sources. Identical to
D4 v1 except that each admitted coordinate is clipped to its own declared live decoder range
(recorded from the live session in every arm, Z6) instead of the default MotorSafety range.
POST_ONLY and the upright controls are reused from v1. The v1 module, jo_command_yoke,
coxa_offset_yoke, jo_zone_crossing and the kernel are unchanged.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
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
from . import jo_command_direction as v1
from . import jo_command_yoke as cy
from .tactile_boundary import native

ROOT = c.ROOT
PROTOCOL = 'docs/evidence/jo-command-direction-v2/protocol.json'
PROTOCOL_SHA256 = '5b77fd9e411a369a7d452fdb7b203ccdcc744c24b2a9f7c2be7fd41961ab4095'
SCHEMA = 'jo-command-direction-arm-v2'
REPORTS = {'docs/evidence/jo-zone-crossing-v1/run/report.json':
           'e64811f7253478b0f2d91031d5b63d9acc8ea2c86ed4878959c49d9e3a80f571',
           'docs/evidence/jo-command-yoke-v1/run/report.json':
           '5abd8a9aaa8b5f81097460fbe0ef44d0068bbea98fe0006febaec102926b5c0e',
           'docs/evidence/jo-command-direction-v1/run/report.json':
           '8dc55e706dc5f6f16f569fa8fac211d3f4bfc03d9a989bec7f142698cbf54918'}
V1_REPORT = 'docs/evidence/jo-command-direction-v1/run/report.json'
FALLEN = v1.FALLEN
CONDITIONS = ('POST_NEG', 'POST_HALF', 'POST_SCRAMBLE')
ARMS = tuple(f'{k}__{s}' for s in FALLEN for k in CONDITIONS)
ADMITTED = v1.ADMITTED
SIGN = v1.SIGN
LIVE_MIN, LIVE_MAX = -1e6, 1e6
RANGES = {i: (LIVE_MIN, LIVE_MAX) for i in ADMITTED}
TILT_TRANSITION = v1.TILT_TRANSITION
LIVE_STEP_RAD = 4. * .0005     # largest live change between consecutive neural updates


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    spec = json.loads(raw)
    if (tuple(spec['admitted']) != ADMITTED or spec['scramble']['sign_by_admitted_order'] != SIGN.tolist()
            or spec['declared_live_range_rad'] != [LIVE_MIN, LIVE_MAX]
            or tuple(spec['arms']['conditions']) != CONDITIONS or tuple(spec['arms']['fallen_sources']) != FALLEN):
        raise ValueError('constants differ from the protocol')
    return spec


def split(arm):
    cond, source = arm.split('__')
    if source not in FALLEN or cond not in CONDITIONS:
        raise ValueError('unknown arm')
    return cond, source


def schedule_for(cond, on_schedule, off_schedule, ranges=None):
    """Declared applied schedule (n x 42) and the number of clipped values (per-coordinate ranges)."""
    ranges = RANGES if ranges is None else ranges
    on_s, off_s = np.asarray(on_schedule, float), np.asarray(off_schedule, float)
    if on_s.shape != off_s.shape or on_s.shape[1] != 42:
        raise ValueError('matched 42-coordinate schedules required')
    a = list(ADMITTED)
    lo = np.array([ranges[i][0] for i in a])
    hi = np.array([ranges[i][1] for i in a])
    out = off_s.copy()
    on_a, off_a = on_s[TILT_TRANSITION:, a], off_s[TILT_TRANSITION:, a]
    neg = off_a - (on_a - off_a)
    if cond == 'POST_NEG':
        raw = neg
    elif cond == 'POST_HALF':
        raw = off_a + .5*(on_a - off_a)
    elif cond == 'POST_SCRAMBLE':
        raw = np.where(SIGN > 0, on_a, neg)
    else:
        raise ValueError('unknown condition')
    new = np.clip(raw, lo, hi)
    out[TILT_TRANSITION:, a] = new
    return out, int(np.count_nonzero(raw != new))


class Trial(v1.Trial):
    """D4 v1 / D3 yoke trial plus a record of the live channel ranges and compiled actuator limits."""

    def __init__(self, arm, actions, event_state=c.EVENT_STATE):
        _, source = split(arm)
        cy.zc.Trial.__init__(self, cy.off_of(source), event_state)
        self.yoke_arm, self.actions = arm, np.asarray(actions, dtype=float)
        self.sim = self.original_sim_step = None
        self.applied = None
        self.actuator_limits = self.channel_ranges = None

    def bind(self, sim, physics, obs):
        super().bind(sim, physics, obs)
        m = self.model_ptr
        rows = []
        for i in range(42):
            j = int(m.actuator_trnid[i, 0])
            rows.append(dict(actuator=i, actuator_name=str(m.actuator(i).name), joint=j, joint_name=str(m.joint(j).name),
                             jnt_limited=bool(m.jnt_limited[j]), jnt_range=[float(x) for x in m.jnt_range[j]],
                             ctrllimited=bool(m.actuator_ctrllimited[i]),
                             ctrlrange=[float(x) for x in m.actuator_ctrlrange[i]]))
        self.actuator_limits = rows

    def attach(self, brain, channels, *, sensory_sources):
        out = super().attach(brain, channels, sensory_sources=sensory_sources)
        self.channel_ranges = {name: dict(index=int(ch['index']), safety=asdict(ch['pipeline'].safety))
                               for name, ch in channels.items()}
        return out


def load_archives(folder, source, spec):
    out = {}
    for name in (source, cy.off_of(source)):
        path = Path(folder)/f'{name}.json.gz'
        if live.sha(path) != spec['sources']['archives'][name]:
            raise RuntimeError(f'archive {name} differs from preregistration')
        out[name] = c.load(path)
    return out[source], out[cy.off_of(source)]


def run_arm(arm, folder, progress=print, steps=c.STEPS):
    spec = protocol()
    cond, source = split(arm)
    on, off = load_archives(folder, source, spec)
    actions, clipped = schedule_for(cond, yk.schedule(on), yk.schedule(off))
    del on, off
    gc.collect()
    trial = Trial(arm, actions)
    seed = trial.seed
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256, condition=cond,
                  source=source, off_source=cy.off_of(source), cns_seed=seed, clipped_values=clipped,
                  archive_sha256={k: spec['sources']['archives'][k] for k in (source, cy.off_of(source))},
                  not_claimed=spec['not_claimed'])
    session = None
    try:
        session = pr.create_session(trial, None, None)
        progress(f'{arm}: fresh CNS/physics initialization; all 42 coordinates yoked ({cond}, live ranges)', flush=True)
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
                      tilt_event=trial.tilt_event, actuator_limits=trial.actuator_limits,
                      channel_ranges=trial.channel_ranges)
    return result


# ---- evaluation (pure on arm records) ------------------------------------------------

def live_range_ok(arm, expected):
    """Z6: one live channel per admitted coordinate, declared range, applied values inside it and ctrlrange."""
    ch, act = arm.get('channel_ranges'), arm.get('actuator_limits')
    if not ch or not act or len(act) != 42:
        return False
    by_index = {}
    for v in ch.values():
        by_index.setdefault(int(v['index']), []).append(v['safety'])
    for i in ADMITTED:
        if len(by_index.get(i, [])) != 1:
            return False
        s = by_index[i][0]
        if [s['joint_min_rad'], s['joint_max_rad']] != list(RANGES[i]):
            return False
        col = expected[:, i]
        if col.min() < s['joint_min_rad'] or col.max() > s['joint_max_rad']:
            return False
        a = act[i]
        if a['actuator'] != i:
            return False
        if a['ctrllimited'] and (col.min() < a['ctrlrange'][0] or col.max() > a['ctrlrange'][1]):
            return False
    return True


def preflight(smoke):
    """Preflight read of the discarded smoke: exit status, yoke audit (rows run), Z6 ranges."""
    n = len(smoke['samples']) - 1
    expected = np.asarray([r['commanded_joints'] for r in smoke['samples'][1:]], float) if n else None
    audit = n > 0 and all(r['adhesion_zero'] is True for r in smoke['samples'][1:])
    return dict(status=smoke['run_status'], audited_rows=n, adhesion_zero=bool(audit),
                live_range_ok=bool(n and live_range_ok(smoke, expected)))


def excursion(on_s, off_s, expected):
    """Per admitted coordinate: largest distance beyond [min(ON,OFF), max(ON,OFF)] after the tilt."""
    a = list(ADMITTED)
    x = expected[TILT_TRANSITION:, a]
    lo = np.minimum(on_s[TILT_TRANSITION:, a], off_s[TILT_TRANSITION:, a])
    hi = np.maximum(on_s[TILT_TRANSITION:, a], off_s[TILT_TRANSITION:, a])
    return {int(i): float(v) for i, v in zip(a, np.maximum(0., np.maximum(lo - x, x - hi)).max(axis=0))}


def expectations(outcomes):
    neg_up = sum(not outcomes[s]['POST_NEG']['falls'] for s in FALLEN)
    half_up = all(not outcomes[s]['POST_HALF']['falls'] for s in FALLEN)
    held = lambda ok: 'HELD' if ok else 'NOT_HELD'
    return dict(E1=held(neg_up >= 4), E2=held(half_up))


def evaluate(load, load_archive, load_v1, v1_outcomes, hashes_ok):
    """load(arm) -> v2 arm; load_archive(name) -> Step D archive; load_v1(name) -> v1 POST_ONLY arm;
    v1_outcomes: the v1 report's outcomes; hashes_ok: Z5 file identity."""
    checks = dict(Z1_complete=True, Z2_pretilt_anchor=True, Z3_yoke_audit=True, Z4_gravity=True,
                  Z5_sources=bool(hashes_ok), Z6_live_range=True, Z7_no_clip=True)
    outcomes, diagnostics = {}, {}
    for source in FALLEN:
        on, off = load_archive(source), load_archive(cy.off_of(source))
        on_s, off_s = yk.schedule(on), yk.schedule(off)
        del on, off
        ref = load_v1(f'POST_ONLY__{source}')
        ref_q = [s['qpos'] for s in ref['samples'][:TILT_TRANSITION + 1]]
        del ref
        outcomes[source], diagnostics[source] = {}, {}
        for cond in CONDITIONS:
            name = f'{cond}__{source}'
            a = load(name)
            expected, clipped = schedule_for(cond, on_s, off_s)
            checks['Z1_complete'] &= (a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1
                                      and len(a['neural']) == c.TICKS)
            checks['Z2_pretilt_anchor'] &= (len(a['samples']) > TILT_TRANSITION and
                                            [s['qpos'] for s in a['samples'][:TILT_TRANSITION + 1]] == ref_q)
            checks['Z3_yoke_audit'] &= cy.yoke_audit(a, expected)
            checks['Z4_gravity'] &= cy.gravity_ok(a)
            checks['Z5_sources'] &= (a.get('source') == source and a.get('cns_seed') == int(source.rsplit('_', 1)[1]))
            checks['Z6_live_range'] &= live_range_ok(a, expected)
            checks['Z7_no_clip'] &= (clipped == 0 and a.get('clipped_values') == 0)
            outcomes[source][cond] = cy.outcome(a)
            steps = np.abs(np.diff(expected, axis=0))
            diagnostics[source][cond] = dict(
                clipped_values=clipped, max_step_at_tilt_rad=float(steps[TILT_TRANSITION - 1].max()),
                transitions_over_live_step=int(np.count_nonzero(steps[TILT_TRANSITION - 1:].max(axis=1) > LIVE_STEP_RAD)),
                max_abs_command_rad=float(np.abs(expected[:, list(ADMITTED)]).max()),
                excursion_beyond_on_off_rad=excursion(on_s, off_s, expected))
            del a
            gc.collect()
    checks = {k: bool(v) for k, v in checks.items()}
    v1_vs_v2 = {s: {k: dict(v1=v1_outcomes[s][k], v2=outcomes[s][k]) for k in CONDITIONS} for s in FALLEN}
    base = dict(checks=checks, outcomes=outcomes, diagnostics=diagnostics, v1_vs_v2=v1_vs_v2,
                v1_post_only={s: v1_outcomes[s]['POST_ONLY'] for s in FALLEN})
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', **base)
    labelled = [s for s in FALLEN if v1_outcomes[s]['POST_ONLY']['falls']]
    if len(labelled) != len(FALLEN):
        return dict(status='INCONCLUSIVE_PREREQUISITE', **base)
    labels = {s: v1.source_labels(outcomes[s]) for s in FALLEN}
    return dict(status='INTEGRITY_ACCEPTED', labels=labels, consistency=v1.consistency(labels),
                expectations=expectations(outcomes), **base)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--archives', type=Path, required=True, help='folder with the Step D raw arms')
    parser.add_argument('--v1', type=Path, help='folder with the D4 v1 raw arms (evaluation only)')
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--preflight', type=Path, help='read a smoke arm for the preflight only')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    spec = protocol()
    if any(live.sha(ROOT/k) != v for k, v in REPORTS.items()):
        raise ValueError('Step D, D3 or D4 v1 report identity mismatch')
    if args.preflight:
        print(json.dumps(preflight(c.load(args.preflight))))
        return 0
    if args.output is None:
        raise ValueError('--output is required')
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
    if args.v1 is None or args.evaluate is None:
        raise ValueError('--evaluate and --v1 are required for evaluation')
    archives, v1_arms = spec['sources']['archives'], spec['sources']['v1_post_only_arms']
    hashes_ok = (all(live.sha(args.archives/f'{k}.json.gz') == v for k, v in archives.items())
                 and all(live.sha(args.v1/f'{k}.json.gz') == v for k, v in v1_arms.items()))
    v1_outcomes = json.loads((ROOT/V1_REPORT).read_text(encoding='utf-8'))['evaluation']['outcomes']
    hashes = {k: live.sha(args.evaluate/f'{k}.json.gz') for k in ARMS}
    e = evaluate(lambda k: c.load(args.evaluate/f'{k}.json.gz'), lambda k: c.load(args.archives/f'{k}.json.gz'),
                 lambda k: c.load(args.v1/f'{k}.json.gz'), v1_outcomes, hashes_ok)
    report = dict(schema='jo-command-direction-report-v2', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=e, interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'labels', 'consistency', 'expectations')}),
                     indent=1))
    print(json.dumps(native({s: {k: (v['falls'], v['t_fall_ms'], round(v['peak_tilt_deg'], 1)) for k, v in o.items()}
                             for s, o in e['outcomes'].items()}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
