"""Antennal gravity Step C: does JO tilt information reach leg motor neurons? (V1)

Preregistered in docs/evidence/antennal-gravity-live-v1/protocol.json (design:
docs/ANTENNAL_GRAVITY_LIVE_V1.md). 37 fixed arms: REPRO_N0_7 plus {OFF, G1, FLIP} x
{UP, DOWN} x CNS seeds 13-18, one fresh process each, in the push-response N context
(hair-plate Step C A_ON, 20 live-v3 channels, no coxa channel, zero force). The Step B
JO encoder drives the four Step A C/E sets (withheld in OFF); at stored state 5005 the
gravity vector is rotated 10 deg about world y (DOWN = nose-down, UP = nose-up) and held.
The kernel, live-v3, the hair-plate encoder and the Step B encoder are unchanged.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import time

import numpy as np

from . import coxa_hypothesis_loop as loop
from . import coxa_offset_yoke as yk
from . import coxa_push_response as pr
from . import hair_plate_posture as c
from .tactile_boundary import native
from ..embodiment import antennal_gravity_encoder as ge

ROOT = c.ROOT
PROTOCOL = 'docs/evidence/antennal-gravity-live-v1/protocol.json'
PROTOCOL_SHA256 = '05655b4005a48d27f4c8c29adf9baa012322582794d40c9d9172ab749cb8d7ea'
SCHEMA = 'antennal-gravity-live-arm-v1'
ENCODER_RESULT = 'docs/evidence/antennal-gravity-encoder-v1/run/result.json'
ENCODER_RESULT_SHA256 = '35ff3da49662c4e417149078d85e928ecab4fdb7bbb753a13919ef8a11ad710f'
STEP_A_RESULT = 'docs/evidence/antennal-gravity-identity-v1/run/result.json'
STEP_A_SHA256 = '5b735be5682361f4c708254bb7e65772ef08998fb1365329e3e64b3861104f8d'
REPRO_SHA256 = '1a94e5add3a828ba37c86840efda450fcff9cc36d5f52bceeceb53a2977fb9dd'
SEEDS = (13, 14, 15, 16, 17, 18)
TYPES = ('OFF', 'G1', 'FLIP')
TILTS = {'UP': 10., 'DOWN': -10.}
ASSIGN = {'OFF': 'G1', 'G1': 'G1', 'FLIP': 'G1_FLIP'}
REPRO = 'REPRO_N0_7'
ARMS = (REPRO,) + tuple(f'{t}_{d}_{s}' for s in SEEDS for t in TYPES for d in TILTS)
G0 = (0., 0., -9810.)
JO_SIZE = 320
WINDOW_MS = (520., 2000.)
TONIC_MS = (0., 500.)
PREFIX_MS = 500.
SIGN_TICK_AFTER_MS = 500.5
ROLLOVER_DEG = 45.
DN_TYPES = ('DNp73', 'DNp18', 'DNg29', 'pIP1', 'DNbe001')


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def split(arm):
    if arm == REPRO:
        return 'REPRO', None, 7
    t, d, s = arm.split('_')
    if t not in TYPES or d not in TILTS or int(s) not in SEEDS:
        raise ValueError('unknown arm')
    return t, d, int(s)


def block(seed):
    return tuple(f'{t}_{d}_{seed}' for t in TYPES for d in TILTS)


def rotated_gravity(phi_deg):
    """R_y(phi) @ G0; phi < 0 gives gravity a +x component (nose-down tilt)."""
    p = math.radians(phi_deg)
    r = np.array([[math.cos(p), 0., math.sin(p)], [0., 1., 0.], [-math.sin(p), 0., math.cos(p)]])
    return r @ np.asarray(G0)


def encoder_populations():
    if sha(ROOT/ENCODER_RESULT) != ENCODER_RESULT_SHA256:
        raise ValueError('Step B result identity mismatch')
    saved = json.loads((ROOT/ENCODER_RESULT).read_text(encoding='utf-8'))
    if saved['status'] != 'ENCODER_READY':
        raise ValueError('Step B encoder not ready')
    return {k: [int(i) for i in saved['dense_indices'][k]] for k in ge.SETS}


# ---- live adapter ----------------------------------------------------------------------

class Trial(pr.Trial):
    """Push-response N context plus JO input (withheld in OFF) and a declared gravity tilt."""

    def __init__(self, arm, event_state=c.EVENT_STATE):
        t, tilt, seed = split(arm)
        if t == 'REPRO':
            raise ValueError('REPRO is produced by coxa_push_replication unchanged')
        loop.Trial.__init__(self, arm)  # pr.Trial.__init__ only adds its fixed seed check
        self.kind, self.push, self.seed = 'N', '0', seed
        self.jo_type, self.tilt, self.assignment = t, tilt, ASSIGN[t]
        self.jo_deliver = t != 'OFF'
        self.jo_pop = encoder_populations()
        self.tilt_state, self.tilt_event = event_state, None

    def bind(self, sim, physics, obs):
        super().bind(sim, physics, obs)
        self.model_ptr = getattr(physics.model, 'ptr', physics.model)
        if tuple(float(x) for x in self.model_ptr.opt.gravity) != G0:
            raise RuntimeError('unexpected initial gravity')
        self.jo_frames = ge.AntennaFrames(self.model_ptr)
        self.jo_encoder = ge.AntennalGravityEncoder(self.jo_frames, self.jo_pop, self.assignment)

    def capture(self, physics, obs, action):
        super().capture(physics, obs, action)
        model = getattr(physics.model, 'ptr', physics.model)
        self.samples[-1]['gravity'] = [float(x) for x in model.opt.gravity]
        index = len(self.samples) - 1
        if index == self.tilt_state:
            g = rotated_gravity(TILTS[self.tilt])
            model.opt.gravity[:] = g
            self.tilt_event = dict(state_index=index, time_s=float(physics.data.time), phi_deg=TILTS[self.tilt],
                                   gravity=[float(x) for x in model.opt.gravity])

    def attach(self, brain, channels, *, sensory_sources):
        out = super().attach(brain, channels, sensory_sources=sensory_sources)
        self.jo = np.asarray(sorted({int(i) for v in self.jo_pop.values() for i in v}), dtype=np.intp)
        if len(self.jo) != JO_SIZE or np.intersect1d(self.jo, self.schedule).size:
            raise RuntimeError('complete JO set disjoint from the existing schedule required')
        self.schedule = np.union1d(self.schedule, self.jo).astype(np.intp)
        for channel in channels.values():
            if np.intersect1d(np.asarray(channel['observer'].used), self.schedule).size:
                raise RuntimeError('motor readout overlaps externally driven sensory inventory')
        self._jo_set = set(map(int, self.jo))
        self.initial.update(external_schedule=self.schedule.tolist(), jo_neurons=self.jo_pop,
                            jo_type=self.jo_type, jo_assignment=self.assignment, jo_deliver=self.jo_deliver,
                            tilt=self.tilt, tilt_phi_deg=TILTS[self.tilt], tilt_state=self.tilt_state)
        return out

    def step(self):
        brain = self.brain
        proprio = np.flatnonzero(brain.external_drive > 0)
        if (np.setdiff1d(proprio, self.proprio).size
                or not np.all(brain.external_drive[proprio] == 1000. / brain.config.dt)):
            raise RuntimeError('unexpected kernel proprioceptive input boundary')
        data = getattr(self.physics.data, 'ptr', self.physics.data)
        encoded = self.encoder.encode(data)
        self.encoder.apply(brain, encoded)
        jo = self.jo_encoder.encode(data)
        self.jo_encoder.apply(brain, jo)
        self.available = brain.refractory <= 0
        brain.external_drive_withheld_indices = (np.empty(0, dtype=np.intp) if self.jo_deliver else self.jo.copy())
        fired = self.original_step()  # exactly one canonical neural transition
        delivered = [int(i) for i in brain._last_external_delivered]
        brain.external_drive[self.hair] = 0.
        brain.external_drive[self.jo] = 0.
        self.neural.append(dict(time_ms=float(brain.time_ms), uniforms_sha256=self.current_uniforms,
            hair_rate_hz={leg: encoded[leg]['rate_hz'] for leg in c.hp.LEGS},
            hair_forward={leg: encoded[leg]['forward'] for leg in c.hp.LEGS},
            hair_delivered=[i for i in delivered if i in self._hair_set],
            jo_d={'L': jo['C_left']['d'], 'R': jo['C_right']['d']},
            jo_rate_hz={k: jo[k]['rate_hz'] for k in ge.SETS},
            jo_delivered=[i for i in delivered if i in self._jo_set],
            fired=list(map(int, fired)), motor_readout_verified=False))
        return fired


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
                  jo_type=t, jo_assignment=ASSIGN[t], tilt=tilt, tilt_phi_deg=TILTS[tilt],
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


# ---- evaluation helpers (pure) ---------------------------------------------------------

def pools(bodymap):
    """{'<T> <side> <class>': set(ids)} over leg muscles."""
    name = re.compile(r'^(.+) (T[123]) (left|right)$')
    out = {}
    for e in bodymap['muscles']:
        m = name.match(e['name'])
        if not m:
            continue
        cls = e['actuator'][:-len(f'_{m.group(2)}_{m.group(3)}')]
        out.setdefault(f'{m.group(2)} {m.group(3)} {cls}', set()).update(int(i) for i in e['idx'])
    return out


def counts(arm, lo, hi):
    """Spike count per neuron over ticks with lo < time_ms <= hi."""
    out = {}
    for t in arm['neural']:
        if lo < t['time_ms'] <= hi:
            for i in t['fired']:
                out[i] = out.get(i, 0) + 1
    return out


def pool_rates(cnt, groups, lo, hi):
    span = (hi - lo)/1000.
    return {k: sum(cnt.get(i, 0) for i in ids)/len(ids)/span for k, ids in groups.items()}


def axes(qpos):
    w, x, y, z = qpos[3:7]
    n = math.sqrt(w*w + x*x + y*y + z*z)
    w, x, y, z = w/n, x/n, y/n, z/n
    bx = np.array([1 - 2*(y*y + z*z), 2*(x*y + w*z), 2*(x*z - w*y)])
    by = np.array([2*(x*y - w*z), 1 - 2*(x*x + z*z), 2*(y*z + w*x)])
    bz = np.array([2*(x*z + w*y), 2*(y*z - w*x), 1 - 2*(x*x + y*y)])
    return bx, by, bz


def body_angles(sample):
    """Tilt, pitch (+ nose-down) and roll (+ left side down) relative to the recorded gravity, degrees."""
    g = np.asarray(sample['gravity'], float)
    g = g/np.linalg.norm(g)
    bx, by, bz = axes(sample['qpos'])
    clip = lambda v: max(-1., min(1., float(v)))
    return (math.degrees(math.acos(clip(-bz @ g))), math.degrees(math.asin(clip(bx @ g))),
            math.degrees(math.asin(clip(by @ g))))


def pearson(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return 0.
    return float(np.corrcoef(a, b)[0, 1])


def corr_matrix(vectors):
    n = len(vectors)
    m = np.zeros((n, n))
    for i, j in itertools.combinations(range(n), 2):
        m[i, j] = m[j, i] = pearson(vectors[i], vectors[j])
    return m


def rho_of(m, signs=None):
    n = len(m)
    s = np.ones(n) if signs is None else np.asarray(signs, float)
    pairs = list(itertools.combinations(range(n), 2))
    return float(np.mean([s[i]*s[j]*m[i, j] for i, j in pairs]))


def sign_flip(m):
    """Observed rho and exact sign-flip p over all 2**n sign vectors."""
    obs = rho_of(m)
    flips = [rho_of(m, s) for s in itertools.product((1., -1.), repeat=len(m))]
    return obs, float(sum(r >= obs - 1e-12 for r in flips)/len(flips))


def label(rho, p):
    if rho > 0 and p <= 1/32:
        return 'JO_TILT_PATTERN_CONSISTENT'
    if rho > 0 and p <= .25:
        return 'JO_TILT_PATTERN_WEAK'
    return 'NO_CONSISTENT_JO_TILT_PATTERN'


def complete(a):
    return a['run_status'] == 'COMPLETE' and len(a['samples']) == c.STEPS + 1 and len(a['neural']) == c.TICKS


def first_after(arm, t_ms):
    return next(t for t in arm['neural'] if t['time_ms'] > t_ms)


def summarize(arm, groups, dn):
    """Per-arm numbers needed after the seed block is released from memory."""
    win, ton = counts(arm, *WINDOW_MS), counts(arm, *TONIC_MS)
    lo, hi = WINDOW_MS
    ang = [body_angles(s) for s in arm['samples'] if lo < s['time_s']*1000. <= hi]
    return dict(window_counts={k: sum(win.get(i, 0) for i in ids) for k, ids in groups.items()},
                window_rates=pool_rates(win, groups, *WINDOW_MS), tonic_rates=pool_rates(ton, groups, *TONIC_MS),
                dn_rates=pool_rates(win, dn, *WINDOW_MS) if dn else {},
                tilt_max_deg=float(max(a[0] for a in ang)), tilt_mean_deg=float(np.mean([a[0] for a in ang])),
                pitch_mean_deg=float(np.mean([a[1] for a in ang])), roll_mean_deg=float(np.mean([a[2] for a in ang])))


def seed_checks(arms, s, jo_sets):
    """I1, I3-I7 (per seed) on the six arms of one seed."""
    k = {name: arms[name] for name in block(s)}
    out = dict(I1=all(complete(a) for a in k.values()))
    if not out['I1']:
        return out, {}
    ref = k[f'OFF_UP_{s}']
    uni = [t['uniforms_sha256'] for t in ref['neural']]
    out['I3'] = all(a['initial']['external_schedule'] == ref['initial']['external_schedule']
                    and [t['uniforms_sha256'] for t in a['neural']] == uni for a in k.values())
    i4 = all(a['samples'][0]['qpos'] == ref['samples'][0]['qpos'] for a in k.values())
    for t in TYPES:
        i4 &= pr.prefix_equal(k[f'{t}_UP_{s}'], k[f'{t}_DOWN_{s}'], c.EVENT_STATE + 1, PREFIX_MS)
    out['I4'] = bool(i4)
    i5 = True
    for name, a in k.items():
        g = rotated_gravity(TILTS[split(name)[1]]).tolist()
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
                z = ge.zone_rates(x['jo_d'][side], ASSIGN[t])
                i6 &= all(x['jo_rate_hz'][f'{zone}_{sname}'] == hz for zone, hz in z.items())
        first[name] = first_after(a, SIGN_TICK_AFTER_MS)['jo_d']
    for t in TYPES:
        dn, up = first[f'{t}_DOWN_{s}'], first[f'{t}_UP_{s}']
        i6 &= dn['L'] > up['L'] and dn['R'] > up['R']
    out['I6'] = bool(i6)
    out['I7'] = all(a['initial'].get('cns_seed') == s and a.get('cns_seed') == s for a in k.values())
    return out, dict(tick1=uni[0], first_post_tilt_d=first,
                     first_on_off_difference=next((i for i, (x, y) in enumerate(zip(k[f'G1_UP_{s}']['samples'],
                                                   ref['samples'])) if x['qpos'] != y['qpos']), None))


def contrasts(summary, included):
    """Delta per type and S per assignment, per seed, over included pools (sorted)."""
    delta = {t: {s: [summary[f'{t}_DOWN_{s}']['window_rates'][p] - summary[f'{t}_UP_{s}']['window_rates'][p]
                     for p in included] for s in SEEDS} for t in TYPES}
    s_vec = {t: {s: [a - b for a, b in zip(delta[t][s], delta['OFF'][s])] for s in SEEDS} for t in ('G1', 'FLIP')}
    return delta, s_vec


def labels_from(s_vec):
    out = {}
    for t, by_seed in s_vec.items():
        m = corr_matrix([by_seed[s] for s in SEEDS])
        rho, p = sign_flip(m)
        out[t] = dict(label=label(rho, p), rho=rho, p=p, pair_correlations=m.tolist())
    return out


def evaluate(load, repro_ref, repro_ok, groups, dn):
    """load(arm) -> arm record. groups: MN pools; dn: {type: set(dense)}."""
    repro = load(REPRO)
    checks = dict(I1_complete=complete(repro),
                  I2_reproduction=bool(repro_ok) and complete(repro) and yk.reproduces(repro, repro_ref))
    del repro
    gc.collect()
    jo_sets = None
    parts, audits, summary = {}, {}, {}
    for s in SEEDS:
        arms = {k: load(k) for k in block(s)}
        if jo_sets is None:
            jo_sets = {int(i) for v in arms[f'G1_UP_{s}']['initial']['jo_neurons'].values() for i in v}
        parts[s], audits[s] = seed_checks(arms, s, jo_sets)
        if parts[s]['I1']:
            for k, a in arms.items():
                summary[k] = summarize(a, groups, dn)
        del arms
        gc.collect()
    checks['I1_complete'] &= all(p['I1'] for p in parts.values())
    for key, nm in (('I3', 'I3_common_rng'), ('I4', 'I4_prefixes'), ('I5', 'I5_tilt_record'),
                    ('I6', 'I6_jo_delivery'), ('I7', 'I7_seeds')):
        checks[nm] = all(p.get(key, False) for p in parts.values())
    if checks['I7_seeds']:
        tick1 = [audits[s]['tick1'] for s in SEEDS]
        checks['I7_seeds'] = len(set(tick1)) == len(SEEDS)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks)
    body = {k: {m: v[m] for m in ('tilt_max_deg', 'tilt_mean_deg', 'pitch_mean_deg', 'roll_mean_deg')}
            for k, v in summary.items()}
    base = dict(checks=checks, body=body, audit=audits)
    precondition = all(body[f'OFF_{d}_{s}']['tilt_max_deg'] < ROLLOVER_DEG for s in SEEDS for d in TILTS)
    if not precondition:
        return dict(status='INCONCLUSIVE_PHYSICS', **base)
    included = sorted(p for p in groups if any(v['window_counts'][p] > 0 for v in summary.values()))
    delta, s_vec = contrasts(summary, included)
    labels = labels_from(s_vec)
    mean_s = {t: np.mean([s_vec[t][s] for s in SEEDS], axis=0) for t in s_vec}
    per_pool = {t: {p: dict(median=float(np.median([s_vec[t][s][i] for s in SEEDS])),
                            positive_seeds=int(sum(s_vec[t][s][i] > 0 for s in SEEDS)))
                    for i, p in enumerate(included)} for t in s_vec}
    side = {t: {sd: {s: float(np.mean([v for p, v in zip(included, s_vec[t][s]) if f' {sd} ' in p] or [0.]))
                     for s in SEEDS} for sd in ('left', 'right')} for t in s_vec}
    tonic = {t: {s: float(np.mean([summary[f'{t}_UP_{s}']['tonic_rates'][p] for p in included])) for s in SEEDS}
             for t in TYPES}
    dn_contrast = {t: {s: {ty: summary[f'{t}_DOWN_{s}']['dn_rates'][ty] - summary[f'{t}_UP_{s}']['dn_rates'][ty]
                           for ty in dn} for s in SEEDS} for t in TYPES}
    return dict(status='INTEGRITY_ACCEPTED', labels={t: v['label'] for t, v in labels.items()}, statistics=labels,
                included_pools=included, r_GF=pearson(mean_s['G1'], mean_s['FLIP']),
                mean_abs_delta_hz={t: {s: float(np.mean(np.abs(delta[t][s]))) for s in SEEDS} for t in TYPES},
                s_norm_hz={t: {s: float(np.linalg.norm(s_vec[t][s])) for s in SEEDS} for t in s_vec},
                per_pool_s=per_pool, per_side_mean_s_hz=side, per_side_label='left/right JO reconstruction asymmetry; not read as roll sensing',
                tonic_mean_mn_rate_0_500ms_hz=tonic, dn_down_minus_up_hz=dn_contrast, delta_hz=delta, s_hz=s_vec, **base)


def dn_groups(cache):
    from ..cache import load_cache
    if sha(ROOT/STEP_A_RESULT) != STEP_A_SHA256:
        raise ValueError('Step A result identity mismatch')
    saved = json.loads((ROOT/STEP_A_RESULT).read_text(encoding='utf-8'))
    index = {int(k): int(v) for k, v in load_cache(cache).body_id_to_index.items()}
    out = {}
    for pop in saved['populations'].values():
        for d in pop['descending_reached']:
            if d['type'] in DN_TYPES:
                out.setdefault(d['type'], set()).add(index[int(d['body_id'])])
    return out


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
    hashes = {k: sha(folder/f'{k}.json.gz') for k in ARMS}
    repro_ok = sha(args.repro_ref) == REPRO_SHA256
    e = evaluate(lambda k: c.load(folder/f'{k}.json.gz'), c.load(args.repro_ref), repro_ok,
                 pools(bodymap), dn_groups(args.cache))
    report = dict(schema='antennal-gravity-live-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=e, interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(native({k: e.get(k) for k in ('status', 'checks', 'labels', 'r_GF')}), indent=1))
    print(json.dumps(native({t: {k: v[k] for k in ('rho', 'p')} for t, v in (e.get('statistics') or {}).items()}),
                     indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
