"""Antennal gravity Step D4: direction of the post-tilt command change (V1).

Preregistered in docs/evidence/jo-command-direction-v1/protocol.json (design:
docs/JO_COMMAND_DIRECTION_V1.md). 27 fixed arms on the D3 open-loop yoke path: for each of
the 5 fallen Step D ON DOWN20 sources, POST_ONLY / POST_NEG / POST_HALF / POST_SCRAMBLE; and
POST_ONLY for the 7 ON DOWN20 sources that stayed up. Before the tilt every coordinate comes
from the OFF archive; after it the 20 admitted coordinates follow the declared transform of
Delta = ON - OFF. jo_command_yoke, coxa_offset_yoke, jo_zone_crossing and the kernel are
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
from . import jo_command_yoke as cy
from . import jo_zone_crossing as zc
from .tactile_boundary import native

ROOT = c.ROOT
PROTOCOL = 'docs/evidence/jo-command-direction-v1/protocol.json'
PROTOCOL_SHA256 = 'a7e804f2180f97b2ae0d0a1a5c023203d2b44d2b6d7baa5b793900e7fe901392'
SCHEMA = 'jo-command-direction-arm-v1'
REPORTS = {'docs/evidence/jo-zone-crossing-v1/run/report.json':
           'e64811f7253478b0f2d91031d5b63d9acc8ea2c86ed4878959c49d9e3a80f571',
           'docs/evidence/jo-command-yoke-v1/run/report.json':
           '5abd8a9aaa8b5f81097460fbe0ef44d0068bbea98fe0006febaec102926b5c0e'}
FALLEN = ('G1_DOWN20_19', 'G1_DOWN20_21', 'G1_DOWN20_24', 'FLIP_DOWN20_23', 'FLIP_DOWN20_24')
UPRIGHT = ('G1_DOWN20_20', 'G1_DOWN20_22', 'G1_DOWN20_23', 'FLIP_DOWN20_19', 'FLIP_DOWN20_20',
           'FLIP_DOWN20_21', 'FLIP_DOWN20_22')
FALLEN_CONDITIONS = ('POST_ONLY', 'POST_NEG', 'POST_HALF', 'POST_SCRAMBLE')
ARMS = tuple(f'{k}__{s}' for s in FALLEN for k in FALLEN_CONDITIONS) + tuple(f'POST_ONLY__{s}' for s in UPRIGHT)
ADMITTED = cy.ADMITTED
JOINT_MIN, JOINT_MAX = -1.35, 1.30
SIGN = np.array([-1, -1, 1, 1, 1, 1, 1, -1, -1, -1, -1, 1, -1, 1, -1, -1, 1, -1, 1, 1])
TILT_TRANSITION = c.EVENT_STATE    # transition 5005 is the first under tilted gravity


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    spec = json.loads(raw)
    if (tuple(spec['admitted']) != ADMITTED or spec['scramble']['sign_by_admitted_order'] != SIGN.tolist()
            or spec['joint_range_rad'] != [JOINT_MIN, JOINT_MAX]):
        raise ValueError('constants differ from the protocol')
    return spec


def split(arm):
    cond, source = arm.split('__')
    if not ((source in FALLEN and cond in FALLEN_CONDITIONS) or (source in UPRIGHT and cond == 'POST_ONLY')):
        raise ValueError('unknown arm')
    return cond, source


def scramble_draw():
    """Reproduces the preregistered sign vector."""
    flipped = set(np.random.default_rng(20261106).permutation(20)[:10].tolist())
    return np.array([-1 if i in flipped else 1 for i in range(20)])


def schedule_for(cond, on_schedule, off_schedule):
    """Declared applied schedule (n x 42) and the number of clipped values."""
    on_s, off_s = np.asarray(on_schedule, float), np.asarray(off_schedule, float)
    if on_s.shape != off_s.shape or on_s.shape[1] != 42:
        raise ValueError('matched 42-coordinate schedules required')
    out = off_s.copy()
    a = list(ADMITTED)
    on_a, off_a = on_s[TILT_TRANSITION:, a], off_s[TILT_TRANSITION:, a]
    if cond == 'POST_ONLY':
        raw = new = on_a
    elif cond == 'POST_NEG':
        raw = off_a - (on_a - off_a)
        new = np.clip(raw, JOINT_MIN, JOINT_MAX)
    elif cond == 'POST_HALF':
        raw = off_a + .5*(on_a - off_a)
        new = np.clip(raw, JOINT_MIN, JOINT_MAX)
    elif cond == 'POST_SCRAMBLE':
        neg = off_a - (on_a - off_a)
        raw = np.where(SIGN > 0, on_a, neg)
        new = np.where(SIGN > 0, on_a, np.clip(neg, JOINT_MIN, JOINT_MAX))
    else:
        raise ValueError('unknown condition')
    out[TILT_TRANSITION:, a] = new
    return out, int(np.count_nonzero(raw != new))


class Trial(cy.Trial):
    """D3 yoke trial (same apply/capture/detach) for a D4 arm name."""

    def __init__(self, arm, actions, event_state=c.EVENT_STATE):
        _, source = split(arm)
        zc.Trial.__init__(self, cy.off_of(source), event_state)
        self.yoke_arm, self.actions = arm, np.asarray(actions, dtype=float)
        self.sim = self.original_sim_step = None
        self.applied = None


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

def degenerate(on, off):
    first = cy.first_qpos_difference(on, off)
    return first is None or first > c.EVENT_STATE


def source_labels(out):
    """out: {condition: outcome} for one fallen source."""
    return dict(direction='DIRECTION_NONSPECIFIC' if out['POST_NEG']['falls'] else 'DIRECTION_SPECIFIC',
                pattern='PATTERN_NONSPECIFIC' if out['POST_SCRAMBLE']['falls'] else 'PATTERN_SPECIFIC',
                half_dose='HALF_DOSE_FALLS' if out['POST_HALF']['falls'] else 'HALF_DOSE_STAYS_UP')


def consistency(labels):
    out = {}
    for t in ('G1', 'FLIP'):
        src = [s for s in FALLEN if s.startswith(t + '_')]
        out[t] = {k: (labels[src[0]][k] if len({labels[s][k] for s in src}) == 1 else 'MIXED')
                  for k in ('direction', 'pattern', 'half_dose')}
    return out


def upright_summary(outcomes, degen):
    out = {}
    for t in ('G1', 'FLIP'):
        src = [s for s in UPRIGHT if s.startswith(t + '_')]
        counted = [s for s in src if not degen[s]]
        out[t] = dict(non_degenerate=counted, degenerate=[s for s in src if degen[s]],
                      falls=[s for s in counted if outcomes[s]['POST_ONLY']['falls']])
    return out


def expectations(outcomes, upright):
    neg_up = sum(not outcomes[s]['POST_NEG']['falls'] for s in FALLEN)
    half_up = all(not outcomes[s]['POST_HALF']['falls'] for s in FALLEN)
    upright_falls = sum(len(v['falls']) for v in upright.values())
    held = lambda ok: 'HELD' if ok else 'NOT_HELD'
    return dict(E1=held(neg_up >= 4), E2=held(half_up), E3=held(upright_falls == 0))


def evaluate(load, load_archive, load_d3, hashes_ok):
    """load(arm) -> D4 arm; load_archive(name) -> Step D archive; load_d3(name) -> D3 arm;
    hashes_ok: Z5 file identity."""
    checks = dict(Z1_complete=True, Z2_reproduction=True, Z3_yoke_audit=True, Z4_gravity=True,
                  Z5_sources=bool(hashes_ok))
    outcomes, diagnostics, mean_abs_delta, degen = {}, {}, {}, {}
    a_idx = list(ADMITTED)
    for source in FALLEN + UPRIGHT:
        on, off = load_archive(source), load_archive(cy.off_of(source))
        on_s, off_s = yk.schedule(on), yk.schedule(off)
        mean_abs_delta[source] = float(np.abs(on_s[TILT_TRANSITION:, a_idx] - off_s[TILT_TRANSITION:, a_idx]).mean())
        if source in UPRIGHT:
            degen[source] = degenerate(on, off)
        outcomes[source], diagnostics[source] = {}, {}
        for cond in (FALLEN_CONDITIONS if source in FALLEN else ('POST_ONLY',)):
            name = f'{cond}__{source}'
            a = load(name)
            expected, clipped = schedule_for(cond, on_s, off_s)
            checks['Z1_complete'] &= (a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1
                                      and len(a['neural']) == c.TICKS)
            checks['Z3_yoke_audit'] &= cy.yoke_audit(a, expected)
            checks['Z4_gravity'] &= cy.gravity_ok(a)
            checks['Z5_sources'] &= (a.get('source') == source and a.get('cns_seed') == int(source.rsplit('_', 1)[1]))
            if source in FALLEN and cond == 'POST_ONLY':
                ref = load_d3(name)
                checks['Z2_reproduction'] &= (len(a['samples']) == len(ref['samples']) and
                                              all(x['qpos'] == y['qpos'] for x, y in zip(a['samples'], ref['samples'])))
                del ref
            outcomes[source][cond] = cy.outcome(a)
            steps = np.abs(np.diff(expected, axis=0))
            diagnostics[source][cond] = dict(
                clipped_values=clipped, max_step_rad=float(steps.max()),
                max_step_at_tilt_rad=float(steps[TILT_TRANSITION - 1].max()))
            del a
            gc.collect()
        del on, off
        gc.collect()
    checks = {k: bool(v) for k, v in checks.items()}
    base = dict(checks=checks, outcomes=outcomes, diagnostics=diagnostics, mean_abs_delta_post_rad=mean_abs_delta,
                upright_degenerate=degen)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', **base)
    labels = {s: source_labels(outcomes[s]) for s in FALLEN}
    upright = upright_summary(outcomes, degen)
    return dict(status='INTEGRITY_ACCEPTED', labels=labels, consistency=consistency(labels), upright=upright,
                expectations=expectations(outcomes, upright), **base)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--archives', type=Path, required=True, help='folder with the Step D raw arms')
    parser.add_argument('--d3', type=Path, help='folder with the D3 raw arms (evaluation only)')
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = protocol()
    if any(live.sha(ROOT/k) != v for k, v in REPORTS.items()):
        raise ValueError('Step D or D3 report identity mismatch')
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
    if args.d3 is None or args.evaluate is None:
        raise ValueError('--evaluate and --d3 are required for evaluation')
    archives, d3 = spec['sources']['archives'], spec['sources']['d3_post_only_arms']
    hashes_ok = (all(live.sha(args.archives/f'{k}.json.gz') == v for k, v in archives.items())
                 and all(live.sha(args.d3/f'{k}.json.gz') == v for k, v in d3.items()))
    hashes = {k: live.sha(args.evaluate/f'{k}.json.gz') for k in ARMS}
    e = evaluate(lambda k: c.load(args.evaluate/f'{k}.json.gz'), lambda k: c.load(args.archives/f'{k}.json.gz'),
                 lambda k: c.load(args.d3/f'{k}.json.gz'), hashes_ok)
    report = dict(schema='jo-command-direction-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=e, interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'labels', 'consistency', 'upright',
                                                   'expectations')}), indent=1))
    print(json.dumps(native({s: {k: (v['falls'], v['t_fall_ms']) for k, v in o.items()}
                             for s, o in e['outcomes'].items()}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
