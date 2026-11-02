"""Hair-plate relay interneurons V1: causal necessity (left) and sufficiency (right).

Preregistered in docs/evidence/rf-relay-intervention-v1/protocol.json (design:
docs/RF_RELAY_INTERVENTION_V1.md). Five fixed arms in the Step C A_ON context, one fresh
process each. Reuses the Step C Trial unchanged and layers on it the engine's existing
transmission_withheld_indices (silencing) and forced events from a precomputed,
independently seeded train (injection). The CNS random-number stream is never touched.
Engineering interventions on the model only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from . import hair_plate_posture as c
from .tactile_boundary import create_session, native
from ..embodiment import coxa_drive_asymmetry as d
from ..embodiment import hair_plate_encoder as hp
from ..embodiment import hair_plate_identity as a
from ..embodiment import rf_coxa_excitation as rf

ROOT = c.ROOT
PROTOCOL = 'docs/evidence/rf-relay-intervention-v1/protocol.json'
PROTOCOL_SHA256 = '29b756b70380ddfae471ac4f2d93e8db36f0744664746e18307c1014ea6b4d42'
SCHEMA = 'rf-relay-intervention-arm-v1'
ARMS = ('C0', 'L_SIL', 'L_SHAM', 'R_INJ', 'R_SHAM')
SILENCE = {'L_SIL': 'LEFT_RELAY', 'L_SHAM': 'LEFT_SHAM'}
INJECT = {'R_INJ': 'RIGHT_RELAY', 'R_SHAM': 'RIGHT_SHAM'}
RELAY_TYPES = ('IN03A066', 'IN03A075', 'IN03A080')
SHAM_PREFIX = 'IN03A'
TRAIN_SEED = 20261102


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


# ---- set rules (pure) -------------------------------------------------------------

def floored_targets(pre, indptr, indices, counts, min_syn):
    a0, b0 = indptr[pre], indptr[pre + 1]
    return set(indices[a0:b0][counts[a0:b0] >= min_syn].tolist())


def relay_sets(types, side, indptr, indices, counts, pre_sign, min_syn, lf_hair, lf_post, rf_post):
    """LEFT_RELAY and RIGHT_RELAY by the preregistered rules (dense indices, sorted)."""
    lf_hair_targets = set()
    for s in lf_hair:
        lf_hair_targets |= floored_targets(s, indptr, indices, counts, min_syn)
    left, right = [], []
    for i, t in enumerate(types):
        if t not in RELAY_TYPES:
            continue
        out = floored_targets(i, indptr, indices, counts, min_syn)
        excitatory = pre_sign[i] > 0
        if side.get(i) == 'left' and i in lf_hair_targets and excitatory and out & lf_post:
            left.append(i)
        if side.get(i) == 'right' and excitatory and out & rf_post:
            right.append(i)
    return sorted(left), sorted(right)


def sham_set(relay, sham_side, types, side, indptr, indices, counts, min_syn, replayed, excluded, rates):
    """Same size as relay; IN03A, given side, no floored edge onto any replayed coxa MN.

    For each relay neuron in dense order, the unused candidate with the closest rate
    (ties: lowest dense index). None if it cannot be filled.
    """
    candidates = [i for i, t in enumerate(types)
                  if str(t).startswith(SHAM_PREFIX) and side.get(i) == sham_side and i not in excluded
                  and not floored_targets(i, indptr, indices, counts, min_syn) & replayed]
    chosen = []
    for r in sorted(relay):
        free = [i for i in candidates if i not in chosen]
        if not free:
            return None
        chosen.append(min(free, key=lambda i: (abs(rates[i] - rates[r]), i)))
    return chosen


def injection_rates(left_relay, right_relay, types, rates):
    """Each injected neuron gets the A_ON window-mean rate of LEFT_RELAY neurons of its type."""
    by_type = {}
    for i in left_relay:
        by_type.setdefault(types[i], []).append(rates[i])
    if any(types[i] not in by_type for i in right_relay):
        return None
    return [float(np.mean(by_type[types[i]])) for i in right_relay]


def trains(rates_hz, ticks, dt, seed=TRAIN_SEED):
    """Per-neuron sorted tick lists: Bernoulli per tick, p = rate * dt / 1000 (the engine's
    forced-event equation), from an independent generator."""
    rng = np.random.default_rng(seed)
    u = rng.random((ticks, len(rates_hz)))
    hits = u < np.asarray(rates_hz, dtype=np.float64)*(dt/1000.)
    return [np.flatnonzero(hits[:, j]).tolist() for j in range(len(rates_hz))]


def train_sha256(train):
    return hashlib.sha256(json.dumps(train, separators=(',', ':')).encode()).hexdigest()


def window_ticks(neural):
    lo, hi = c.WINDOW_MS
    times = [t['time_ms'] for t in neural]
    return min(i for i, t in enumerate(times) if t > lo), max(i for i, t in enumerate(times) if t <= hi)


def window_rates(neural, n):
    lo, hi = window_ticks(neural)
    spikes = np.zeros(n, np.int64)
    for t in range(lo, hi + 1):
        if neural[t]['fired']:
            spikes[neural[t]['fired']] += 1
    return spikes/((c.WINDOW_MS[1] - c.WINDOW_MS[0])/1000.)


def resolve(cache, a_on_path):
    """Resolve the four sets, injection rates and trains from the connectome and saved A_ON."""
    import pandas as pd
    from ..cache import load_cache
    from .. import load_malecns, MaleCNSBrain
    from ..neural import ModelConfig
    a_spec = a.protocol()
    table = pd.read_feather(ROOT/a_spec['sources']['annotations']['path'])
    cdata = load_cache(cache)
    raw_sets, _ = a.sensory_sets(table, cdata.body_id_to_index)
    hair = {leg: raw_sets[hp.leg_key(leg)] for leg in hp.LEGS}
    data = load_malecns()
    if not np.array_equal(np.asarray(cdata.body_ids), np.asarray(data.body_ids)):
        raise RuntimeError('cache and live body ids differ')
    config = ModelConfig.calibrated()
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    pools = d.leg_pools(bodymap, d.protocol())
    _, step_c_coxa = c.mn_sets(bodymap)
    replayed = set().union(*(pools[l]['posterior'] | pools[l]['anterior'] for l in hp.LEGS), *step_c_coxa.values())
    brain = MaleCNSBrain(data)
    indptr = np.asarray(data.row_ptr, dtype=np.int64); indices = np.asarray(data.target_indices, dtype=np.int64)
    counts = np.asarray(data.synapse_counts)
    body = np.asarray(data.body_ids)
    by_body = {int(r['bodyId']): r for _, r in table.iterrows()}
    types = [str(t) for t in data.types]
    side = {}
    for i, t in enumerate(types):
        if t.startswith(SHAM_PREFIX):
            r = by_body.get(int(body[i]))
            side[i] = a.side_of(r) if r is not None else None
    a_on = c.load(a_on_path)
    rates = window_rates(a_on['neural'], data.neuron_count)
    left, right = relay_sets(types, side, indptr, indices, counts, brain.pre_sign, config.min_synapses,
                             hair['LF'], pools['LF']['posterior'], pools['RF']['posterior'])
    forced = set(map(int, a_on['initial']['external_schedule']))
    out = dict(LEFT_RELAY=left, RIGHT_RELAY=right)
    relays = set(left) | set(right)
    out['LEFT_SHAM'] = sham_set(left, 'left', types, side, indptr, indices, counts, config.min_synapses,
                                replayed, relays | forced, rates) if left else None
    out['RIGHT_SHAM'] = sham_set(right, 'right', types, side, indptr, indices, counts, config.min_synapses,
                                 replayed, relays | forced, rates) if right else None
    inj = injection_rates(left, right, types, rates) if left and right else None
    buildable = all(out[k] for k in ('LEFT_RELAY', 'RIGHT_RELAY', 'LEFT_SHAM', 'RIGHT_SHAM')) and inj is not None
    sets = {k: [dict(dense=int(i), body_id=int(body[i]), type=types[i], side=side.get(i),
                     a_on_window_rate_hz=float(rates[i])) for i in (v or [])] for k, v in out.items()}
    resolved = dict(status='BUILDABLE' if buildable else 'PROTOCOL_NOT_BUILDABLE', sets=sets,
                    n_replayed_coxa_mns=len(replayed))
    if buildable:
        train = trains(inj, c.TICKS, config.dt)
        resolved.update(injection_rates_hz=inj, train_seed=TRAIN_SEED, train_ticks=c.TICKS,
                        train_events=[len(x) for x in train], train_sha256=train_sha256(train))
    return resolved


# ---- adapter ----------------------------------------------------------------------

class RelayTrial(c.Trial):
    """Step C A_ON Trial plus one declared intervention; RNG stream and kernel unchanged."""

    def __init__(self, arm, spec):
        super().__init__('A_ON')
        if arm not in ARMS:
            raise ValueError('unknown arm')
        self.relay_arm = arm
        sets = spec['resolved']['sets']
        self.silenced = np.asarray(sorted(x['dense'] for x in sets[SILENCE[arm]]), np.intp) if arm in SILENCE \
            else np.empty(0, np.intp)
        self.schedule_by_tick = {}
        if arm in INJECT:
            r = spec['resolved']
            train = trains(r['injection_rates_hz'], r['train_ticks'], spec['engine']['dt_ms'], r['train_seed'])
            if train_sha256(train) != r['train_sha256']:
                raise RuntimeError('injection train differs from preregistration')
            for x, ticks in zip(sets[INJECT[arm]], train):
                for t in ticks:
                    self.schedule_by_tick.setdefault(t, []).append(int(x['dense']))
        self.injected = set(x['dense'] for x in sets[INJECT[arm]]) if arm in INJECT else set()
        self.pending = None

    def attach(self, brain, channels, *, sensory_sources):
        super().attach(brain, channels, sensory_sources=sensory_sources)
        touched = np.union1d(self.silenced, np.asarray(sorted(self.injected), np.intp))
        if np.intersect1d(touched, self.schedule).size:
            raise RuntimeError('intervention set overlaps the external schedule')
        for channel in channels.values():
            if np.intersect1d(np.asarray(channel['observer'].used), touched).size:
                raise RuntimeError('intervention set overlaps a motor readout')
        self.original_transmission = brain.transmission_withheld_indices.copy()
        brain.transmission_withheld_indices = self.silenced.copy()
        self.initial.update(relay_arm=self.relay_arm, silenced=self.silenced.tolist(), injected=sorted(self.injected),
                            motor_channels={k: sorted(map(int, v['observer'].used)) for k, v in channels.items()})
        return self

    def event_trials(self, candidate_available, parameters):
        forced = super().event_trials(candidate_available, parameters)
        scheduled = self.schedule_by_tick.get(len(self.neural), [])
        applied = [i for i in scheduled if self.available[i]]
        forced[applied] = True
        self.pending = dict(scheduled=scheduled, injected=applied,
                            blocked=[i for i in scheduled if not self.available[i]])
        return forced

    def step(self):
        if not np.array_equal(self.brain.transmission_withheld_indices, self.silenced):
            raise RuntimeError('silenced set changed')
        self.pending = None
        fired = super().step()
        p = self.pending or dict(scheduled=[], injected=[], blocked=[])
        self.neural[-1].update(injected=p['injected'], inject_blocked=p['blocked'],
                               transmission_withheld=list(map(int, self.brain._last_transmission_withheld)))
        return fired

    def detach(self):
        if self.brain is not None and hasattr(self, 'original_transmission'):
            self.brain.transmission_withheld_indices = self.original_transmission.copy()
        super().detach()


def run_arm(arm, progress=print):
    spec = protocol()
    trial = RelayTrial(arm, spec)
    result = dict(schema=SCHEMA, arm=arm, run_status='ERROR', protocol_sha256=PROTOCOL_SHA256)
    session = None
    try:
        session = create_session(trial)
        progress(f'{arm}: fresh live-v3 CNS/physics initialization', flush=True)
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


# ---- evaluation -------------------------------------------------------------------

def q_nec(l_sil_ratio, l_sham_ratio):
    if l_sham_ratio is None or l_sil_ratio is None:
        return 'NOT_DEFINED'
    if l_sham_ratio < .8:
        return 'NONSPECIFIC'
    return 'NECESSARY' if l_sil_ratio <= .5 else 'CONTRIBUTES' if l_sil_ratio <= .8 else 'NOT_NECESSARY'


def q_suf(r_inj_rate, r_sham_increase, c0_rf, c0_lf):
    if r_sham_increase >= 2.:
        return 'NONSPECIFIC'
    if r_inj_rate >= .5*c0_lf:
        return 'RESCUED'
    return 'PARTIAL' if r_inj_rate - c0_rf >= 5. else 'NO_EFFECT'


def rate(neural, ids):
    lo, hi = c.WINDOW_MS
    ids = set(ids)
    count = sum(1 for t in neural if lo < t['time_ms'] <= hi for i in t['fired'] if i in ids)
    return count/len(ids)/((hi - lo)/1000.)


def hair_mean(neural, leg):
    lo, hi = c.WINDOW_MS
    v = [t['hair_rate_hz'][leg] for t in neural if lo < t['time_ms'] <= hi]
    return float(np.mean(v))


def first_divergence(x, y, key):
    return next((i for i, (p, q) in enumerate(zip(x, y)) if p[key] != q[key]), None)


def integrity(arms, a_on, spec):
    r = spec['resolved']
    sets = {k: set(x['dense'] for x in v) for k, v in r['sets'].items()}
    checks = {}
    checks['I1_complete'] = all(x['run_status'] == 'COMPLETE' and len(x['samples']) == c.STEPS + 1
                                and len(x['neural']) == c.TICKS for x in arms.values())
    if not checks['I1_complete']:
        return checks, {}
    c0 = arms['C0']
    checks['I2_common_rng'] = all(
        x['initial']['external_schedule'] == c0['initial']['external_schedule']
        and [t['uniforms_sha256'] for t in x['neural']] == [t['uniforms_sha256'] for t in c0['neural']]
        for x in arms.values())
    checks['I3_c0_reproduces_a_on'] = (
        all(p[k] == q[k] for p, q in zip(c0['neural'], a_on['neural'])
            for k in ('fired', 'uniforms_sha256', 'hair_delivered'))
        and all(p['qpos'] == q['qpos'] for p, q in zip(c0['samples'], a_on['samples']))
        and len(c0['samples']) == len(a_on['samples']) and len(c0['neural']) == len(a_on['neural']))
    train = trains(r['injection_rates_hz'], r['train_ticks'], spec['engine']['dt_ms'], r['train_seed'])
    first, ok4, blocked = {}, True, {}
    for k, x in arms.items():
        silenced = sets[SILENCE[k]] if k in SILENCE else set()
        inj = [y['dense'] for y in r['sets'][INJECT[k]]] if k in INJECT else []
        by_tick = {}
        for j, ticks in zip(inj, train):
            for t in ticks:
                by_tick.setdefault(t, set()).add(j)
        n_blocked, start = 0, None
        for t, rec in enumerate(x['neural']):
            withheld = set(rec['transmission_withheld'])
            if withheld != (set(rec['fired']) & silenced) or len(withheld) != len(rec['transmission_withheld']):
                ok4 = False
            done, miss = set(rec['injected']), set(rec['inject_blocked'])
            if done | miss != by_tick.get(t, set()) or done & miss or not done <= set(rec['fired']):
                ok4 = False
            n_blocked += len(miss)
            if start is None and (withheld or done):
                start = t
        if k != 'C0' and start is None:
            ok4 = False
        first[k], blocked[k] = start, n_blocked
    checks['I4_intervention_verified'] = ok4
    prefix = True
    for k, x in arms.items():
        if k == 'C0':
            continue
        t0 = first[k] if first[k] is not None else 0
        if any(p['fired'] != q['fired'] for p, q in zip(x['neural'][:t0], c0['neural'][:t0])):
            prefix = False
        if any(p['qpos'] != q['qpos'] for p, q in zip(x['samples'][:5*t0 + 1], c0['samples'][:5*t0 + 1])):
            prefix = False
    checks['I5_prefix_identity'] = prefix
    return checks, dict(first_intervention_tick=first, injection_blocked_events=blocked)


def decomposition(arm, leg, best, pools, hair, brain, data, config, spec):
    """Descriptive: V1 replay and V2 attribution of the primary best MN, delivered spikes only."""
    sets = spec['resolved']['sets']
    neural = arm['neural']
    fired = [tuple(i for i in t['fired'] if i not in set(t['transmission_withheld'])) for t in neural]
    recorded_fired = [tuple(t['fired']) for t in neural]
    window = window_ticks(neural)
    indptr = np.asarray(data.row_ptr, dtype=np.int64); indices = np.asarray(data.target_indices, dtype=np.int64)
    m = best[leg]
    pr, means = d.replay(fired, [m], brain.weights, indptr, indices, brain.pre_sign, config,
                         brain.delay_steps, hair[leg], window)
    rec = [[t for t, f in enumerate(recorded_fired) if m in f]]
    status, _ = d.compare_spikes(pr, rec, window)
    contrib, _ = rf.attribute(fired, {m}, brain.weights, indptr, indices, brain.pre_sign, config,
                              brain.delay_steps, window)
    groups = {k: set(x['dense'] for x in v) for k, v in sets.items()}
    by = {k: sum(v for p_, v in contrib[m].items() if p_ in ids) for k, ids in groups.items()}
    return dict(best_mn=m, replay_status=status, g_hair=means['hair'][0], g_other=means['other'][0],
                g_inh=means['inh'][0], g_from_set=by)


def evaluate(arms, a_on, spec, cache):
    checks, audit = integrity(arms, a_on, spec)
    if not all(checks.values()):
        return dict(status='INCONCLUSIVE_INTEGRITY', checks=checks, **audit)
    import pandas as pd
    from ..cache import load_cache
    from .. import load_malecns, MaleCNSBrain
    from ..neural import ModelConfig
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    pools = d.leg_pools(bodymap, d.protocol())
    v1 = json.loads((ROOT/spec['sources']['v1_result']['path']).read_text(encoding='utf-8'))
    best = {leg: int(v1['structural'][leg]['best_mn']) for leg in hp.LEGS}
    pool_rate = {k: {leg: rate(x['neural'], pools[leg]['posterior']) for leg in hp.LEGS} for k, x in arms.items()}
    best_rate = {k: {leg: rate(x['neural'], [best[leg]]) for leg in hp.LEGS} for k, x in arms.items()}
    channels = arms['C0']['initial']['motor_channels']
    channel_rate = {k: {name: rate(x['neural'], ids) for name, ids in channels.items()} for k, x in arms.items()}
    hair_rate = {k: {leg: hair_mean(x['neural'], leg) for leg in hp.LEGS} for k, x in arms.items()}
    c0p = pool_rate['C0']
    ratio = {k: (pool_rate[k]['LF']/c0p['LF'] if c0p['LF'] else None) for k in ('L_SIL', 'L_SHAM')}
    increase = {k: pool_rate[k]['RF'] - c0p['RF'] for k in ('R_INJ', 'R_SHAM')}
    confound = {}
    for k, leg in (('L_SIL', 'LF'), ('L_SHAM', 'LF'), ('R_INJ', 'RF'), ('R_SHAM', 'RF')):
        base = hair_rate['C0'][leg]
        confound[k] = dict(leg=leg, c0_hz=base, arm_hz=hair_rate[k][leg],
                           relative_change=(hair_rate[k][leg] - base)/base if base else None)
    flag = lambda ks: any(confound[k]['relative_change'] is None or abs(confound[k]['relative_change']) > .1 for k in ks)
    labels = dict(
        Q_NEC=dict(label=q_nec(ratio['L_SIL'], ratio['L_SHAM']), ratio=ratio,
                   SENSORY_CONFOUNDED=flag(('L_SIL', 'L_SHAM'))),
        Q_SUF=dict(label=q_suf(pool_rate['R_INJ']['RF'], increase['R_SHAM'], c0p['RF'], c0p['LF']),
                   increase_hz=increase, r_inj_rf_hz=pool_rate['R_INJ']['RF'], rescue_threshold_hz=.5*c0p['LF'],
                   SENSORY_CONFOUNDED=flag(('R_INJ', 'R_SHAM'))))
    posture, divergence = {}, {}
    for k, x in arms.items():
        tilts = [c.tilt_deg(s['qpos']) for s in x['samples'][5201:]]
        posture[k] = dict(tilt_mean_deg=float(np.mean(tilts)), tilt_peak_deg=float(np.max(tilts)),
                          rollover_samples=int(sum(t > 90 for t in tilts)))
        divergence[k] = dict(first_qpos_sample=first_divergence(x['samples'], arms['C0']['samples'], 'qpos'),
                             first_fired_tick=first_divergence(x['neural'], arms['C0']['neural'], 'fired'))
    set_rates = {k: {name: rate(x['neural'], [y['dense'] for y in v]) for name, v in spec['resolved']['sets'].items()}
                 for k, x in arms.items()}
    # descriptive replay/attribution of the primary best MNs
    a_spec = a.protocol()
    table = pd.read_feather(ROOT/a_spec['sources']['annotations']['path'])
    cdata = load_cache(cache)
    raw_sets, _ = a.sensory_sets(table, cdata.body_id_to_index)
    hair = {leg: raw_sets[hp.leg_key(leg)] for leg in hp.LEGS}
    data = load_malecns(); config = ModelConfig.calibrated(); brain = MaleCNSBrain(data)
    decomp = {}
    for k, leg in (('C0', 'LF'), ('C0', 'RF'), ('L_SIL', 'LF'), ('L_SHAM', 'LF'), ('R_INJ', 'RF'), ('R_SHAM', 'RF')):
        decomp[f'{k}_{leg}'] = decomposition(arms[k], leg, best, pools, hair, brain, data, config, spec)
    return dict(status='INTEGRITY_ACCEPTED', checks=checks, **audit, labels=labels,
                pool_rate_hz=pool_rate, best_mn_rate_hz=best_rate, channel_rate_hz=channel_rate,
                hair_rate_hz=hair_rate, sensory_confound=confound, set_rate_hz=set_rates,
                posture=posture, divergence_from_c0=divergence, decomposition=decomp)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resolve', action='store_true', help='print the resolved sets and trains')
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--evaluate', type=Path, help='folder with the five arms')
    parser.add_argument('--step-c-dir', type=Path)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.resolve:
        print(json.dumps(resolve(args.cache, args.step_c_dir/'A_ON.json.gz'), indent=1))
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
    a_on_path = args.step_c_dir/'A_ON.json.gz'
    if d.sha256(a_on_path) != spec['sources']['step_c_a_on']['sha256']:
        raise SystemExit('saved Step C A_ON hash mismatch')
    if resolve(args.cache, a_on_path) != spec['resolved']:
        raise SystemExit('set resolution does not reproduce the preregistration')
    folder = args.evaluate
    arms = {k: c.load(folder/f'{k}.json.gz') for k in ARMS}
    hashes = {k: d.sha256(folder/f'{k}.json.gz') for k in ARMS}
    report = dict(schema='rf-relay-intervention-report-v1', protocol_sha256=PROTOCOL_SHA256, arm_sha256=hashes,
                  evaluation=evaluate(arms, c.load(a_on_path), spec, args.cache),
                  interpretation_limits=spec['interpretation_limits'])
    with args.output.open('xb') as stream:
        stream.write((json.dumps(native(report), indent=1, allow_nan=False) + '\n').encode())
    e = report['evaluation']
    print(json.dumps({k: e.get(k) for k in ('status', 'checks', 'labels', 'pool_rate_hz', 'sensory_confound')}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
