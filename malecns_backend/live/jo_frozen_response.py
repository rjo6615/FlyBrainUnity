"""Antennal gravity Step D5: does the fly fall because the JO senses the tilt? (V1)

Preregistered in docs/evidence/jo-frozen-response-v1/protocol.json (design:
docs/JO_FROZEN_RESPONSE_V1.md). Closed loop in the Step D context: jo_zone_crossing.Trial
(bind, DOWN20 tilt from stored state 5006, JO step) is reused unchanged except for one
declared probe. In FROZEN arms (G1F, FLIPF) the JO encoder output is held, from the first
encode after gravity is rotated, at the last output computed before it. 61 fixed arms: REPRO
(Step D's G1_DOWN20_19 rerun, exact) plus {OFF, G1, G1F, FLIP, FLIPF} x CNS seeds 25-36, one
fresh process each. Fall = jo_command_yoke.outcome (tilt >= 45 deg after state 5005).
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.stats import binomtest, fisher_exact

from . import antennal_gravity_live as live
from . import coxa_offset_yoke as yk
from . import coxa_push_response as pr
from . import hair_plate_posture as c
from . import jo_command_yoke as jy
from . import jo_zone_crossing as zc
from .tactile_boundary import native

ROOT = c.ROOT
PROTOCOL = 'docs/evidence/jo-frozen-response-v1/protocol.json'
PROTOCOL_SHA256 = 'a1ab56a7bac754aa0da849405a36d61565979de052931e16dff722075e1d2532'
SCHEMA = 'jo-frozen-response-arm-v1'
SEEDS = tuple(range(25, 37))
TILT = 'DOWN20'
TYPES = ('OFF', 'G1', 'G1F', 'FLIP', 'FLIPF')
FROZEN = {'G1F': 'G1', 'FLIPF': 'FLIP'}
SIGHTED = ('G1', 'FLIP')
REPRO = 'REPRO_G1_DOWN20_19'
REPRO_SOURCE = 'G1_DOWN20_19'
REPRO_REF_SHA256 = '7392cc15d3e3e1139090924090c07cdcdc4e1465eb18262a22bbd2fcfa5a3be4'
ARMS = (REPRO,) + tuple(f'{t}_{TILT}_{s}' for s in SEEDS for t in TYPES)
SOURCE_FILES = ('malecns_backend/live/jo_zone_crossing.py', 'malecns_backend/live/antennal_gravity_live.py',
                'malecns_backend/live/jo_command_yoke.py', 'malecns_backend/embodiment/antennal_gravity_encoder.py',
                'malecns_backend/neural.py', 'fly-brain-main/public/data/brain_params.json',
                'docs/evidence/jo-zone-crossing-v1/protocol.json', 'docs/evidence/jo-zone-crossing-v1/run/report.json')
ALPHA = .05
MIN_SIGHTED_FALLS = 5


def lf_sha(path):
    return hashlib.sha256((ROOT/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    spec = json.loads(raw)
    if {p: lf_sha(p) for p in SOURCE_FILES} != spec['sources']['lf_sha256']:
        raise ValueError('source identity mismatch')
    return spec


def split(arm):
    t, d, s = arm.split('_')
    if t not in TYPES or d != TILT:
        raise ValueError('unknown arm')
    return t, int(s)


def block(seed):
    return tuple(f'{t}_{TILT}_{seed}' for t in TYPES)


# ---- live adapter ----------------------------------------------------------------------

class Freeze:
    """Wraps the Step B encoder: live output until gravity is rotated, then the last pre-tilt output."""

    def __init__(self, inner, trial):
        self.inner, self.trial = inner, trial

    def encode(self, data):
        out = self.inner.encode(data)
        self.trial.live_jo = out
        if self.trial.tilt_event is None:
            self.trial.held, self.trial.used_held = out, False
            return out
        if self.trial.held is None:
            raise RuntimeError('no pre-tilt JO output to hold')
        self.trial.used_held = True
        return self.trial.held

    def apply(self, brain, encoded):
        self.inner.apply(brain, encoded)


class Trial(zc.Trial):
    """Step D Trial (DOWN20) with a declared JO type; FROZEN types hold the JO rate after the tilt."""

    def __init__(self, d5_type, seed, event_state=c.EVENT_STATE):
        base = FROZEN.get(d5_type, d5_type)
        zc.loop.Trial.__init__(self, f'{d5_type}_{TILT}_{seed}')
        self.kind, self.push, self.seed = 'N', '0', seed
        self.jo_type, self.tilt, self.assignment = base, TILT, zc.ASSIGN[base]
        self.jo_deliver = base != 'OFF'
        self.jo_pop = live.encoder_populations()
        self.tilt_state, self.tilt_event = event_state, None
        self.d5_type, self.frozen = d5_type, d5_type in FROZEN
        self.held = self.live_jo = None
        self.used_held = False

    def bind(self, sim, physics, obs):
        super().bind(sim, physics, obs)
        self.jo_encoder = (Freeze(self.jo_encoder, self) if self.frozen else Freeze(self.jo_encoder, _Sighted()))
        self._sighted_probe = self.jo_encoder.trial if not self.frozen else None

    def attach(self, brain, channels, *, sensory_sources):
        out = super().attach(brain, channels, sensory_sources=sensory_sources)
        self.initial.update(d5_type=self.d5_type, jo_frozen=self.frozen)
        return out

    def step(self):
        pre_tilt = self.tilt_event is None
        fired = super().step()
        probe = self if self.frozen else self._sighted_probe
        live_jo = probe.live_jo
        self.neural[-1].update(pre_tilt=pre_tilt, jo_held=bool(self.frozen and probe.used_held),
                               jo_live_d={'L': live_jo['C_left']['d'], 'R': live_jo['C_right']['d']})
        return fired


class _Sighted:
    """Sighted arms pass every encode through (tilt_event is never seen), recording the live output."""
    tilt_event = None
    held = live_jo = None
    used_held = False


def run_arm(arm, progress=print, steps=c.STEPS, event_state=c.EVENT_STATE, seed=None):
    spec = protocol()
    if arm == REPRO:
        result = zc.run_arm(REPRO_SOURCE, progress=progress)
        result['saved_as'] = REPRO
        return result
    t, s = split(arm)
    s = s if seed is None else seed
    trial = Trial(t, s, event_state)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256, cns_seed=s,
                  d5_type=t, jo_type=trial.jo_type, jo_frozen=trial.frozen, tilt=TILT,
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
        full = steps == c.STEPS and event_state == c.EVENT_STATE and seed is None
        result['run_status'] = 'COMPLETE' if full else 'SMOKE'
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

def rates_match_encoder(arm, assignment):
    ok = True
    for x in arm['neural']:
        for side, name in (('L', 'left'), ('R', 'right')):
            z = live.ge.zone_rates(x['jo_d'][side], assignment)
            ok &= all(x['jo_rate_hz'][f'{zone}_{name}'] == hz for zone, hz in z.items())
    return bool(ok)


def freeze_audit(frozen, sighted, assignment):
    """Z3: frozen = encoder until the tilt, then the last pre-tilt rates at every tick; sighted = encoder."""
    fn, sn = frozen['neural'], sighted['neural']
    n_pre = sum(1 for x in fn if x['pre_tilt'])
    ok = (n_pre > 0 and all(x['pre_tilt'] for x in fn[:n_pre]) and not any(x['pre_tilt'] for x in fn[n_pre:])
          and n_pre == sum(1 for x in sn if x['pre_tilt'])
          and not any(x['jo_held'] for x in fn[:n_pre]) and all(x['jo_held'] for x in fn[n_pre:])
          and not any(x['jo_held'] for x in sn))
    if not ok:
        return False, n_pre
    held = fn[n_pre - 1]
    ok &= rates_match_encoder(dict(neural=fn[:n_pre]), assignment) and rates_match_encoder(sighted, assignment)
    ok &= all(x['jo_rate_hz'] == held['jo_rate_hz'] and x['jo_d'] == held['jo_d'] for x in fn[n_pre:])
    ok &= all(x['jo_live_d'] == x['jo_d'] for x in sn)
    return bool(ok), n_pre


def matched_prefix(frozen, sighted, n_pre):
    """Z2: qpos/commands equal through state 5005; fired/RNG/JO delivery equal on the pre-tilt ticks."""
    return bool(all(x['qpos'] == y['qpos'] and x['commanded_joints'] == y['commanded_joints']
                    for x, y in zip(frozen['samples'][:c.EVENT_STATE + 1], sighted['samples'][:c.EVENT_STATE + 1]))
                and all(x['fired'] == y['fired'] and x['jo_delivered'] == y['jo_delivered']
                        and x['jo_rate_hz'] == y['jo_rate_hz'] for x, y in zip(frozen['neural'][:n_pre],
                                                                               sighted['neural'][:n_pre])))


def gravity_record_ok(a):
    g = zc.tilt_gravity(TILT)
    ev, te = a.get('event') or {}, a.get('tilt_event') or {}
    return bool(all(x['gravity'] == list(zc.G0) for x in a['samples'][:c.EVENT_STATE + 1])
                and all(x['gravity'] == g for x in a['samples'][c.EVENT_STATE + 1:])
                and ev.get('operation') == 'OBSERVE_ONLY' and ev.get('after_sha256') == ev.get('original_sha256')
                and ev.get('state_index') == c.EVENT_STATE and te.get('state_index') == c.EVENT_STATE
                and te.get('gravity') == g and pr.force_ok(a, '0'))


def delivery_ok(a, t, jo_sets):
    base = FROZEN.get(t, t)
    dlv = [i for x in a['neural'] for i in x['jo_delivered']]
    return bool(a['initial']['jo_deliver'] == (base != 'OFF') and a['initial']['jo_assignment'] == zc.ASSIGN[base]
                and a['initial'].get('d5_type') == t and a['initial'].get('jo_frozen') == (t in FROZEN)
                and (bool(dlv) and set(dlv) <= jo_sets if base != 'OFF' else not dlv))


def first_qpos_difference(a, b):
    return next((i for i, (x, y) in enumerate(zip(a['samples'], b['samples'])) if x['qpos'] != y['qpos']), None)


def post_tilt_jo(a, n_pre):
    post = a['neural'][n_pre:]
    return dict(mean_d={sd: float(np.mean([x['jo_d'][sd] for x in post])) for sd in ('L', 'R')},
                mean_live_d={sd: float(np.mean([x['jo_live_d'][sd] for x in post])) for sd in ('L', 'R')},
                mean_rate_hz={k: float(np.mean([x['jo_rate_hz'][k] for x in post])) for k in live.ge.SETS})


def seed_checks(arms, s, jo_sets):
    out = dict(Z1=all(live.complete(a) for a in arms.values()))
    if not out['Z1']:
        return out, {}
    ref = arms[f'OFF_{TILT}_{s}']
    uni = [t['uniforms_sha256'] for t in ref['neural']]
    out['Z2'] = all(a['initial']['external_schedule'] == ref['initial']['external_schedule']
                    and [t['uniforms_sha256'] for t in a['neural']] == uni
                    and a['samples'][0]['qpos'] == ref['samples'][0]['qpos'] for a in arms.values())
    out['Z3'], audit = True, dict(tick1=uni[0], n_pre_tilt_ticks={}, first_qpos_difference={}, post_tilt_jo={})
    for f, base in FROZEN.items():
        fa, sa = arms[f'{f}_{TILT}_{s}'], arms[f'{base}_{TILT}_{s}']
        ok, n_pre = freeze_audit(fa, sa, zc.ASSIGN[base])
        out['Z3'] &= ok
        out['Z2'] &= matched_prefix(fa, sa, n_pre)
        diff = first_qpos_difference(fa, sa)
        out['Z2'] &= diff is None or diff > c.EVENT_STATE
        audit['n_pre_tilt_ticks'][f] = n_pre
        audit['first_qpos_difference'][f] = diff
        if ok:
            audit['post_tilt_jo'][f] = post_tilt_jo(fa, n_pre)
            audit['post_tilt_jo'][base] = post_tilt_jo(sa, n_pre)
    out['Z2'], out['Z3'] = bool(out['Z2']), bool(out['Z3'])
    out['Z4'] = all(gravity_record_ok(a) for a in arms.values())
    out['Z5'] = all(delivery_ok(a, split(k)[0], jo_sets) for k, a in arms.items())
    out['Z7'] = all(a['initial'].get('cns_seed') == s and a.get('cns_seed') == s for a in arms.values())
    return out, audit


def one_sided(k, n):
    return float(binomtest(k, n, .5, alternative='greater').pvalue) if n else 1.


def q1_label(sighted_falls, n_sighted, off_falls, n_off):
    p = float(fisher_exact([[sighted_falls, n_sighted - sighted_falls], [off_falls, n_off - off_falls]],
                           alternative='greater')[1])
    if p <= ALPHA:
        label = 'JO_FALLS_REPLICATED'
    elif sighted_falls/n_sighted <= off_falls/n_off:
        label = 'JO_FALLS_NOT_REPLICATED'
    else:
        label = 'JO_FALLS_WEAK'
    return label, p


def q2_label(pairs):
    """pairs: [(sighted_falls, frozen_falls)]. b = sighted only, c = frozen only."""
    b = sum(1 for s, f in pairs if s and not f)
    c_ = sum(1 for s, f in pairs if f and not s)
    sighted = sum(1 for s, _ in pairs if s)
    p_b, p_c = one_sided(b, b + c_), one_sided(c_, b + c_)
    if sighted < MIN_SIGHTED_FALLS:
        label = 'UNDERPOWERED'
    elif b > c_ and p_b <= ALPHA:
        label = 'RESPONSE_NEEDED'
    elif c_ > b and p_c <= ALPHA:
        label = 'RESPONSE_PROTECTIVE'
    elif c_ >= b:
        label = 'RESPONSE_NOT_NEEDED'
    else:
        label = 'INDETERMINATE'
    return label, dict(b=b, c=c_, sighted_falls=sighted, frozen_falls=sum(1 for _, f in pairs if f),
                       p_needed=p_b, p_protective=p_c)


def expectations(q1, q2, falls):
    count = lambda t: sum(falls[f'{t}_{TILT}_{s}']['falls'] for s in SEEDS)
    return dict(E1=q1 == 'JO_FALLS_REPLICATED', E2=q2 == 'RESPONSE_NEEDED',
                E3=count('FLIPF') < count('FLIP') and count('G1F') >= count('G1'))


def labels(falls):
    """falls: {arm: jo_command_yoke.outcome}."""
    count = lambda t: sum(falls[f'{t}_{TILT}_{s}']['falls'] for s in SEEDS)
    n = len(SEEDS)
    q1, p1 = q1_label(count('G1') + count('FLIP'), 2*n, count('OFF'), n)
    pairs = {base: [(falls[f'{base}_{TILT}_{s}']['falls'], falls[f'{f}_{TILT}_{s}']['falls']) for s in SEEDS]
             for f, base in FROZEN.items()}
    q2, q2d = q2_label(pairs['G1'] + pairs['FLIP'])
    per_type = {base: dict(zip(('label', 'counts'), q2_label(v))) for base, v in pairs.items()}
    frozen_vs_off = q1_label(count('G1F') + count('FLIPF'), 2*n, count('OFF'), n)
    return dict(Q1=q1, Q1_fisher_p=p1, Q2=q2, Q2_counts=q2d, Q2_per_type_reported=per_type,
                frozen_vs_off_reported=dict(label=frozen_vs_off[0], fisher_p=frozen_vs_off[1]),
                fall_counts={t: count(t) for t in TYPES}, expectations=expectations(q1, q2, falls))


def evaluate(load, repro_ref, repro_ref_ok):
    repro = load(REPRO)
    checks = dict(Z6_reproduction=bool(repro_ref_ok) and live.complete(repro) and yk.reproduces(repro, repro_ref)
                  and all(x['jo_delivered'] == y['jo_delivered'] for x, y in zip(repro['neural'], repro_ref['neural'])),
                  Z7_sources=True)
    repro_outcome = jy.outcome(repro) if live.complete(repro) else None
    del repro
    gc.collect()
    jo_sets, parts, audits, falls = None, {}, {}, {}
    for s in SEEDS:
        arms = {k: load(k) for k in block(s)}
        if jo_sets is None:
            jo_sets = {int(i) for v in arms[f'G1_{TILT}_{s}']['initial']['jo_neurons'].values() for i in v}
        parts[s], audits[s] = seed_checks(arms, s, jo_sets)
        if parts[s]['Z1']:
            falls.update({k: jy.outcome(a) for k, a in arms.items()})
        del arms
        gc.collect()
    names = dict(Z1='Z1_complete', Z2='Z2_matched_until_tilt', Z3='Z3_freeze_audit', Z4='Z4_gravity_forces',
                 Z5='Z5_jo_delivery', Z7='Z7_seeds')
    for key, nm in names.items():
        checks[nm] = all(p.get(key, False) for p in parts.values())
    if checks['Z7_seeds']:
        checks['Z7_seeds'] = len({audits[s]['tick1'] for s in SEEDS}) == len(SEEDS)
    base = dict(checks=checks, repro_outcome=repro_outcome, outcomes=falls, audit=audits)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE', **base)
    return dict(status='INTEGRITY_ACCEPTED', **labels(falls), **base)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--smoke-steps', type=int, help='plumbing smoke only; output is not evidence')
    parser.add_argument('--smoke-seed', type=int, help='smoke only: non-protocol CNS seed')
    parser.add_argument('--evaluate', type=Path)
    parser.add_argument('--repro-ref', type=Path, help="Step D's local raw G1_DOWN20_19 arm")
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    spec = protocol()
    if args.arm:
        smoke = args.smoke_steps is not None
        if smoke and (args.smoke_seed is None or args.smoke_seed in SEEDS or args.arm == REPRO):
            raise ValueError('smoke needs a non-protocol seed and a non-REPRO arm')
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output/(f'smoke_{args.arm}.json.gz' if smoke else f'{args.arm}.json.gz')
        with target.open('xb'):
            pass  # claim the exclusive path before running
        target.unlink()
        result = run_arm(args.arm, steps=args.smoke_steps or c.STEPS, seed=args.smoke_seed if smoke else None)
        out = c.save(target, result)
        print(json.dumps(dict(arm=args.arm, run_status=result['run_status'], error=result.get('error'), sha256=out)))
        return 0 if result['run_status'] in ('COMPLETE', 'SMOKE') else 1
    folder = args.evaluate
    hashes = {k: live.sha(folder/f'{k}.json.gz') for k in ARMS}
    ref_ok = live.sha(args.repro_ref) == REPRO_REF_SHA256
    e = evaluate(lambda k: c.load(folder/f'{k}.json.gz'), c.load(args.repro_ref), ref_ok)
    report = dict(schema='jo-frozen-response-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  repro_ref_sha256=live.sha(args.repro_ref), evaluation=e,
                  interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'Q1', 'Q1_fisher_p', 'Q2', 'Q2_counts',
                                                   'fall_counts', 'expectations', 'repro_outcome')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
