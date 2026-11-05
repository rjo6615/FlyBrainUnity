"""Antennal gravity Step D: zone-crossing JO tilt (V1).

Preregistered in docs/evidence/jo-zone-crossing-v1/protocol.json (design:
docs/JO_ZONE_CROSSING_V1.md). 37 fixed arms: REPRO_N0_7 plus {OFF, G1, FLIP} x
{LEVEL, DOWN20} x CNS seeds 19-24, one fresh process each, in the Step C context. LEVEL
keeps gravity unchanged; DOWN20 rotates it 20 deg nose-down after stored state 5005, so the
live JO drive crosses zero. Step C's Trial (bind/step), measures and statistics are reused
unchanged; only the tilt set, seeds, the operating-point condition O1 and the prediction
checks are new.
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
from . import coxa_hypothesis_loop as loop
from . import coxa_offset_yoke as yk
from . import coxa_push_response as pr
from . import hair_plate_posture as c
from .tactile_boundary import native

ROOT = c.ROOT
PROTOCOL = 'docs/evidence/jo-zone-crossing-v1/protocol.json'
PROTOCOL_SHA256 = 'b002e1c86b629ac559e9f509b2d25e004a0ab63bcfb2256c3fa66f2aeca01449'
SCHEMA = 'jo-zone-crossing-arm-v1'
C2_RESULT = 'docs/evidence/jo-operating-point-v1/run/result.json'
C2_SHA256 = '981ee47c9e93290a62b4c9efd85bb0c3b01930dc15055b75303e431ab0690a05'
SEEDS = (19, 20, 21, 22, 23, 24)
TYPES = live.TYPES
TILTS = {'LEVEL': None, 'DOWN20': -20.}
BASE, TILTED = 'LEVEL', 'DOWN20'
ASSIGN = live.ASSIGN
REPRO = live.REPRO
ARMS = (REPRO,) + tuple(f'{t}_{d}_{s}' for s in SEEDS for t in TYPES for d in TILTS)
G0 = live.G0
O1_MARGIN = .05
P4_DN = ('DNp73', 'DNbe001')


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    if live.sha(ROOT/C2_RESULT) != C2_SHA256:
        raise ValueError('Step C2 result identity mismatch')
    live.protocol()  # Step C protocol lock unchanged
    return json.loads(raw)


def split(arm):
    if arm == REPRO:
        return 'REPRO', None, 7
    t, d, s = arm.split('_')
    if t not in TYPES or d not in TILTS or int(s) not in SEEDS:
        raise ValueError('unknown arm')
    return t, d, int(s)


def block(seed):
    return tuple(f'{t}_{d}_{seed}' for t in TYPES for d in TILTS)


def tilt_gravity(tilt):
    """Gravity from state 5006 on: unchanged for LEVEL, R_y(phi) @ G0 otherwise."""
    return list(G0) if TILTS[tilt] is None else live.rotated_gravity(TILTS[tilt]).tolist()


# ---- live adapter ----------------------------------------------------------------------

class Trial(live.Trial):
    """Step C Trial (bind, JO step) with the Step D tilt set."""

    def __init__(self, arm, event_state=c.EVENT_STATE):
        t, tilt, seed = split(arm)
        if t == 'REPRO':
            raise ValueError('REPRO is produced by coxa_push_replication unchanged')
        loop.Trial.__init__(self, arm)
        self.kind, self.push, self.seed = 'N', '0', seed
        self.jo_type, self.tilt, self.assignment = t, tilt, ASSIGN[t]
        self.jo_deliver = t != 'OFF'
        self.jo_pop = live.encoder_populations()
        self.tilt_state, self.tilt_event = event_state, None

    def capture(self, physics, obs, action):
        pr.Trial.capture(self, physics, obs, action)
        model = getattr(physics.model, 'ptr', physics.model)
        self.samples[-1]['gravity'] = [float(x) for x in model.opt.gravity]
        index = len(self.samples) - 1
        if index == self.tilt_state:
            if TILTS[self.tilt] is not None:
                model.opt.gravity[:] = live.rotated_gravity(TILTS[self.tilt])
            self.tilt_event = dict(state_index=index, time_s=float(physics.data.time),
                                   phi_deg=TILTS[self.tilt] or 0., gravity=[float(x) for x in model.opt.gravity])

    def attach(self, brain, channels, *, sensory_sources):
        out = pr.Trial.attach(self, brain, channels, sensory_sources=sensory_sources)
        self.jo = np.asarray(sorted({int(i) for v in self.jo_pop.values() for i in v}), dtype=np.intp)
        if len(self.jo) != live.JO_SIZE or np.intersect1d(self.jo, self.schedule).size:
            raise RuntimeError('complete JO set disjoint from the existing schedule required')
        self.schedule = np.union1d(self.schedule, self.jo).astype(np.intp)
        for channel in channels.values():
            if np.intersect1d(np.asarray(channel['observer'].used), self.schedule).size:
                raise RuntimeError('motor readout overlaps externally driven sensory inventory')
        self._jo_set = set(map(int, self.jo))
        self.initial.update(external_schedule=self.schedule.tolist(), jo_neurons=self.jo_pop,
                            jo_type=self.jo_type, jo_assignment=self.assignment, jo_deliver=self.jo_deliver,
                            tilt=self.tilt, tilt_phi_deg=TILTS[self.tilt] or 0., tilt_state=self.tilt_state)
        return out


def run_arm(arm, progress=print, steps=c.STEPS, event_state=c.EVENT_STATE):
    spec = protocol()
    if arm == REPRO:
        from . import coxa_push_replication as rp
        result = rp.run_arm('N0_7', progress=progress, steps=steps)
        result['saved_as'] = REPRO
        return result
    t, tilt, seed = split(arm)
    trial = Trial(arm, event_state)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256, cns_seed=seed,
                  jo_type=t, jo_assignment=ASSIGN[t], tilt=tilt, tilt_phi_deg=TILTS[tilt] or 0.,
                  not_claimed=spec['not_claimed'])
    session = None
    try:
        session = pr.create_session(trial, None, None)
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
        result['run_status'] = 'COMPLETE' if steps == c.STEPS and event_state == c.EVENT_STATE else 'SMOKE'
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

def window_d(arm, lo=None, hi=None):
    lo, hi = live.WINDOW_MS if lo is None else (lo, hi)
    ticks = [t['jo_d'] for t in arm['neural'] if lo < t['time_ms'] <= hi]
    return {side: float(np.mean([t[side] for t in ticks])) for side in ('L', 'R')}


def seed_checks(arms, s, jo_sets):
    """I1, I3-I7 (per seed) on the six arms of one seed."""
    k = {name: arms[name] for name in block(s)}
    out = dict(I1=all(live.complete(a) for a in k.values()))
    if not out['I1']:
        return out, {}
    ref = k[f'OFF_{BASE}_{s}']
    uni = [t['uniforms_sha256'] for t in ref['neural']]
    out['I3'] = all(a['initial']['external_schedule'] == ref['initial']['external_schedule']
                    and [t['uniforms_sha256'] for t in a['neural']] == uni for a in k.values())
    i4 = all(a['samples'][0]['qpos'] == ref['samples'][0]['qpos'] for a in k.values())
    for t in TYPES:
        i4 &= pr.prefix_equal(k[f'{t}_{BASE}_{s}'], k[f'{t}_{TILTED}_{s}'], c.EVENT_STATE + 1, live.PREFIX_MS)
    out['I4'] = bool(i4)
    i5 = True
    for name, a in k.items():
        g = tilt_gravity(split(name)[1])
        i5 &= all(x['gravity'] == list(G0) for x in a['samples'][:c.EVENT_STATE + 1])
        i5 &= all(x['gravity'] == g for x in a['samples'][c.EVENT_STATE + 1:])
        ev, te = a.get('event') or {}, a.get('tilt_event') or {}
        i5 &= (ev.get('operation') == 'OBSERVE_ONLY' and ev.get('after_sha256') == ev.get('original_sha256')
               and ev.get('state_index') == c.EVENT_STATE and te.get('state_index') == c.EVENT_STATE
               and te.get('gravity') == g)
        i5 &= pr.force_ok(a, '0')
    out['I5'] = bool(i5)
    i6, first = True, {}
    for name, a in k.items():
        t = split(name)[0]
        dlv = [i for x in a['neural'] for i in x['jo_delivered']]
        i6 &= (a['initial']['jo_deliver'] == (t != 'OFF') and a['initial']['jo_assignment'] == ASSIGN[t]
               and (bool(dlv) and set(dlv) <= jo_sets if t != 'OFF' else not dlv))
        for x in a['neural']:
            for side, sname in (('L', 'left'), ('R', 'right')):
                z = live.ge.zone_rates(x['jo_d'][side], ASSIGN[t])
                i6 &= all(x['jo_rate_hz'][f'{zone}_{sname}'] == hz for zone, hz in z.items())
        first[name] = live.first_after(a, live.SIGN_TICK_AFTER_MS)['jo_d']
    for t in TYPES:
        dn, lv = first[f'{t}_{TILTED}_{s}'], first[f'{t}_{BASE}_{s}']
        i6 &= dn['L'] > lv['L'] and dn['R'] > lv['R']
    out['I6'] = bool(i6)
    out['I7'] = all(a['initial'].get('cns_seed') == s and a.get('cns_seed') == s for a in k.values())
    return out, dict(tick1=uni[0], first_post_tilt_d=first,
                     window_d={n: window_d(a) for n, a in k.items()},
                     first_on_off_difference=next((i for i, (x, y) in enumerate(zip(k[f'G1_{BASE}_{s}']['samples'],
                                                   ref['samples'])) if x['qpos'] != y['qpos']), None))


def operating_point(audits):
    """O1 on OFF arms: window d > +margin for DOWN20 and < -margin for LEVEL, both sides."""
    ok = True
    for s in SEEDS:
        wd = audits[s]['window_d']
        ok &= all(wd[f'OFF_{TILTED}_{s}'][side] > O1_MARGIN and wd[f'OFF_{BASE}_{s}'][side] < -O1_MARGIN
                  for side in ('L', 'R'))
    return bool(ok)


def contrasts(summary, included):
    delta = {t: {s: [summary[f'{t}_{TILTED}_{s}']['window_rates'][p] - summary[f'{t}_{BASE}_{s}']['window_rates'][p]
                     for p in included] for s in SEEDS} for t in TYPES}
    s_vec = {t: {s: [a - b for a, b in zip(delta[t][s], delta['OFF'][s])] for s in SEEDS} for t in ('G1', 'FLIP')}
    return delta, s_vec


def labels_from(s_vec):
    out = {}
    for t, by_seed in s_vec.items():
        m = live.corr_matrix([by_seed[s] for s in SEEDS])
        rho, p = live.sign_flip(m)
        out[t] = dict(label=live.label(rho, p), rho=rho, p=p, pair_correlations=m.tolist())
    return out


def predictions(labels, r_gf, dn_contrast):
    p4 = all(dn_contrast['G1'][s][ty] != 0 and dn_contrast['FLIP'][s][ty] != 0
             and np.sign(dn_contrast['G1'][s][ty]) != np.sign(dn_contrast['FLIP'][s][ty])
             for s in SEEDS for ty in P4_DN)
    held = lambda b: 'HELD' if b else 'NOT_HELD'
    return dict(P1=held(labels['G1'] == 'JO_TILT_PATTERN_CONSISTENT'),
                P2=held(labels['FLIP'] == 'JO_TILT_PATTERN_CONSISTENT'),
                P3=held(r_gf < 0), P4=held(p4))


def evaluate(load, repro_ref, repro_ok, groups, dn):
    """load(arm) -> arm record. groups: MN pools; dn: {type: set(dense)}."""
    repro = load(REPRO)
    checks = dict(I1_complete=live.complete(repro),
                  I2_reproduction=bool(repro_ok) and live.complete(repro) and yk.reproduces(repro, repro_ref))
    del repro
    gc.collect()
    jo_sets = None
    parts, audits, summary = {}, {}, {}
    for s in SEEDS:
        arms = {k: load(k) for k in block(s)}
        if jo_sets is None:
            jo_sets = {int(i) for v in arms[f'G1_{BASE}_{s}']['initial']['jo_neurons'].values() for i in v}
        parts[s], audits[s] = seed_checks(arms, s, jo_sets)
        if parts[s]['I1']:
            for k, a in arms.items():
                summary[k] = live.summarize(a, groups, dn)
        del arms
        gc.collect()
    checks['I1_complete'] &= all(p['I1'] for p in parts.values())
    for key, nm in (('I3', 'I3_common_rng'), ('I4', 'I4_prefixes'), ('I5', 'I5_tilt_record'),
                    ('I6', 'I6_jo_delivery'), ('I7', 'I7_seeds')):
        checks[nm] = all(p.get(key, False) for p in parts.values())
    if checks['I7_seeds']:
        checks['I7_seeds'] = len({audits[s]['tick1'] for s in SEEDS}) == len(SEEDS)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks)
    body = {k: {m: v[m] for m in ('tilt_max_deg', 'tilt_mean_deg', 'pitch_mean_deg', 'roll_mean_deg')}
            for k, v in summary.items()}
    wd = {n: d for s in SEEDS for n, d in audits[s]['window_d'].items()}
    base = dict(checks=checks, body=body, window_d=wd, audit=audits)
    if not operating_point(audits):
        return dict(status='INCONCLUSIVE_OPERATING_POINT', O1=False, **base)
    if not all(body[f'OFF_{d}_{s}']['tilt_max_deg'] < live.ROLLOVER_DEG for s in SEEDS for d in TILTS):
        return dict(status='INCONCLUSIVE_PHYSICS', O1=True, **base)
    included = sorted(p for p in groups if any(v['window_counts'][p] > 0 for v in summary.values()))
    delta, s_vec = contrasts(summary, included)
    stats = labels_from(s_vec)
    labels = {t: v['label'] for t, v in stats.items()}
    mean_s = {t: np.mean([s_vec[t][s] for s in SEEDS], axis=0) for t in s_vec}
    r_gf = live.pearson(mean_s['G1'], mean_s['FLIP'])
    per_pool = {t: {p: dict(median=float(np.median([s_vec[t][s][i] for s in SEEDS])),
                            positive_seeds=int(sum(s_vec[t][s][i] > 0 for s in SEEDS)))
                    for i, p in enumerate(included)} for t in s_vec}
    side = {t: {sd: {s: float(np.mean([v for p, v in zip(included, s_vec[t][s]) if f' {sd} ' in p] or [0.]))
                     for s in SEEDS} for sd in ('left', 'right')} for t in s_vec}
    tonic = {t: {s: float(np.mean([summary[f'{t}_{BASE}_{s}']['tonic_rates'][p] for p in included])) for s in SEEDS}
             for t in TYPES}
    dn_contrast = {t: {s: {ty: summary[f'{t}_{TILTED}_{s}']['dn_rates'][ty] - summary[f'{t}_{BASE}_{s}']['dn_rates'][ty]
                           for ty in dn} for s in SEEDS} for t in TYPES}
    return dict(status='INTEGRITY_ACCEPTED', O1=True, labels=labels, statistics=stats,
                predictions=predictions(labels, r_gf, dn_contrast), included_pools=included, r_GF=r_gf,
                mean_abs_delta_hz={t: {s: float(np.mean(np.abs(delta[t][s]))) for s in SEEDS} for t in TYPES},
                s_norm_hz={t: {s: float(np.linalg.norm(s_vec[t][s])) for s in SEEDS} for t in s_vec},
                per_pool_s=per_pool, per_side_mean_s_hz=side,
                per_side_label='left/right JO reconstruction asymmetry; not read as roll sensing',
                tonic_mean_mn_rate_0_500ms_hz=tonic, dn_down20_minus_level_hz=dn_contrast, delta_hz=delta,
                s_hz=s_vec, **base)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--smoke-event', type=int, help='smoke only: tilt state index')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--repro-ref', type=Path, help='coxa-push-replication N0_7 raw arm')
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = protocol()
    if args.arm:
        smoke = args.smoke_steps is not None
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/(f'smoke_{args.arm}.json.gz' if smoke else f'{args.arm}.json.gz')
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm, steps=args.smoke_steps or c.STEPS,
                         event_state=args.smoke_event if smoke and args.smoke_event is not None else c.EVENT_STATE)
        out = c.save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=out)))
        return 0 if result['run_status'] in ('COMPLETE', 'SMOKE') else 1
    bodymap = json.loads((ROOT/spec['sources']['bodymap']).read_text(encoding='utf-8'))
    folder = args.evaluate
    hashes = {k: live.sha(folder/f'{k}.json.gz') for k in ARMS}
    repro_ok = live.sha(args.repro_ref) == live.REPRO_SHA256
    e = evaluate(lambda k: c.load(folder/f'{k}.json.gz'), c.load(args.repro_ref), repro_ok,
                 live.pools(bodymap), live.dn_groups(args.cache))
    report = dict(schema='jo-zone-crossing-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=e, interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'O1', 'labels', 'r_GF', 'predictions')}),
                     indent=1))
    print(json.dumps(native({t: {k: v[k] for k in ('rho', 'p')} for t, v in (e.get('statistics') or {}).items()}),
                     indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
