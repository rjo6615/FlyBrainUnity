"""Right-front coxa drive asymmetry V1: where does RF hair-plate -> coxa MN drive get lost?

Preregistered in docs/evidence/coxa-drive-asymmetry-v1/protocol.json. Data only: the
connectome, the engine's own weight rule and the spikes recorded in Step C arm A_ON.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from . import hair_plate_encoder as hp
from . import hair_plate_identity as a

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/coxa-drive-asymmetry-v1/protocol.json'
PROTOCOL_SHA256 = '217014751fdaab86e80d358963992d8d3f5de8b76d90c0784929ddc2f261d462'
SCHEMA = 'coxa-drive-asymmetry-result-v1'
FACTORS = ('SOURCE_COUNT', 'SYNAPSES_PER_SOURCE', 'FLOOR_LOSS', 'SIZE_SCALING', 'TRANSMITTER_SIGN')
ENGINE = ('FLOOR_LOSS', 'SIZE_SCALING')


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


# ---- engine weight rule -----------------------------------------------------------

def edges_into(data, targets):
    """(pre, post, position) of every CSR edge whose target is in targets, in CSR order."""
    indptr = np.asarray(data.row_ptr, dtype=np.int64)
    post = np.asarray(data.target_indices, dtype=np.int64)
    pos = np.flatnonzero(np.isin(post, np.fromiter(sorted(targets), np.int64)))
    pre = np.searchsorted(indptr, pos, side='right') - 1
    return pre, post[pos], pos


def rule_weights(data, config, pre, post, pos):
    """MaleCNSBrain's weight and sign rule, recomputed for the given edges only."""
    from ..neural import region_scales
    counts = np.asarray(data.synapse_counts, dtype=np.float32)[pos]
    scale, _, _ = region_scales(data, config)
    sensory = np.fromiter(('sensory' in data.superclasses[x] for x in data.superclass_ids), bool, data.neuron_count)
    valid = counts >= config.min_synapses
    if config.sensory_mask:
        valid &= ~sensory[post]
    w = np.where(valid, counts * scale[post], 0).astype(np.float32)
    sign = np.asarray(data.nt_signs, np.float32).copy()
    if config.neuromodulation:
        sign[np.fromiter((str(t).startswith('OA-') for t in data.types), bool, data.neuron_count)] = 0
    if config.inhibitory_gain != 1:
        w[sign[pre] < 0] *= config.inhibitory_gain
    return counts, scale, w, sign


def g_star(config):
    return (config.e_exc - config.v_rest)*(config.v_threshold - config.v_rest)/(config.e_exc - config.v_threshold)


def mean_field(w_eff, rate_hz, config):
    """Discrete steady-state mean conductance of the engine's deliver/decay update."""
    return w_eff*rate_hz*config.dt/1000./(1. - math.exp(-config.dt/config.tau_syn))


# ---- Part S ---------------------------------------------------------------------

def pool_terms(counts, scale_post, weights, sign_pre, floor):
    """N_s-free pool sums R, F, S, G over the given edges."""
    counts = np.asarray(counts, np.float64)
    keep = counts >= floor
    return dict(R=float(counts.sum()), F=float(counts[keep].sum()),
                S=float((counts*np.asarray(scale_post, np.float64))[keep].sum()),
                G=float((np.asarray(weights, np.float64)*np.asarray(sign_pre, np.float64)).sum()))


def factors(x, y):
    """Log-ratios of x over y for the five identity factors; they sum to log(G_x/G_y)."""
    def parts(t):
        return dict(SOURCE_COUNT=t['N_s'], SYNAPSES_PER_SOURCE=t['R']/t['N_s'], FLOOR_LOSS=t['F']/t['R'],
                    SIZE_SCALING=t['S']/t['F'], TRANSMITTER_SIGN=t['G']/t['S'])
    px, py = parts(x), parts(y)
    out = {k: math.log(px[k]/py[k]) for k in FACTORS}
    total = math.log(x['G']/y['G'])
    if abs(sum(out.values()) - total) > 1e-9:
        raise RuntimeError('factor identity does not sum')
    return out, total


def largest_loss(logs):
    neg = sorted((v, k) for k, v in logs.items() if v < 0)
    if not neg:
        return 'NO_DEFICIT'
    if len(neg) > 1 and abs(neg[1][0]) >= .9*abs(neg[0][0]):
        return 'MIXED'
    return neg[0][1]


def structural(data, config, sets, pools, rate_hz, floor):
    """Per-leg pool terms, per-MN W_m and mean-field drive for the posterior pool."""
    legs = {}
    for leg, sources in sets.items():
        post_ids = pools[leg]['posterior']
        pre, post, pos = edges_into(data, post_ids)
        own = np.isin(pre, np.fromiter(sorted(sources), np.int64))
        pre, post, pos = pre[own], post[own], pos[own]
        counts, scale, w, sign = rule_weights(data, config, pre, post, pos)
        terms = pool_terms(counts, scale[post], w, sign[pre], floor)
        terms['N_s'] = len(sources)
        per_mn = {}
        for m in sorted(post_ids):
            sel = post == m
            W = float((w[sel].astype(np.float64)*sign[pre[sel]]).sum()*config.psp_scale)
            per_mn[m] = dict(W=W, g=mean_field(W, rate_hz, config), raw=float(counts[sel].sum()),
                             floored=float(counts[sel][counts[sel] >= floor].sum()), scale=float(scale[m]),
                             sources=int(len(set(pre[sel][counts[sel] >= floor].tolist()))))
        best = max(sorted(per_mn), key=lambda m: per_mn[m]['W']) if per_mn else None
        legs[leg] = dict(terms=terms, per_mn={str(k): v for k, v in per_mn.items()}, best_mn=best,
                         best_g=per_mn[best]['g'] if best is not None else 0.,
                         concentration=(per_mn[best]['W']/config.psp_scale/terms['G']) if terms['G'] else None)
    return legs


def inventory(data, table, sets, pools, floor):
    """S1: per SNpp45 neuron totals and own-pool outputs, plus annotation status fields."""
    indptr = np.asarray(data.row_ptr, dtype=np.int64)
    targets = np.asarray(data.target_indices, dtype=np.int64)
    counts = np.asarray(data.synapse_counts, dtype=np.float64)
    body = np.asarray(data.body_ids)
    by_body = {int(r['bodyId']): r for _, r in table.iterrows()}
    out = {}
    for leg, sources in sets.items():
        pool = np.fromiter(sorted(pools[leg]['posterior']), np.int64)
        rows = []
        for s in sorted(sources):
            c, t = counts[indptr[s]:indptr[s+1]], targets[indptr[s]:indptr[s+1]]
            mine = np.isin(t, pool)
            r = by_body.get(int(body[s]), {})
            rows.append(dict(dense=int(s), body_id=int(body[s]), total_raw=float(c.sum()),
                             total_floored=float(c[c >= floor].sum()), partners_floored=int((c >= floor).sum()),
                             pool_raw=float(c[mine].sum()), pool_floored=float(c[mine & (c >= floor)].sum()),
                             status=str(r.get('status')), status_label=str(r.get('statusLabel'))))
        out[leg] = rows
    return out


# ---- Part M: exact replay ---------------------------------------------------------

def replay(fired, mns, data_weights, indptr, indices, pre_sign, config, delay, hair_sources, window_ticks):
    """Re-integrate the given MNs from recorded spikes exactly as MaleCNSBrain.step does.

    fired: per tick list of fired dense indices (recorded order). Returns predicted spike
    ticks per MN and window-mean conductances split by source class.
    """
    p = config
    mns = list(mns)
    k_of = {m: i for i, m in enumerate(mns)}
    mset = np.fromiter(mns, np.int64)
    sub = {}
    seen = sorted({int(x) for tick in fired for x in tick})
    for pre in seen:
        a0, b0 = indptr[pre], indptr[pre + 1]
        t = indices[a0:b0]
        hit = np.flatnonzero(np.isin(t, mset))
        if len(hit):
            sub[pre] = (np.fromiter((k_of[int(x)] for x in t[hit]), np.intp, len(hit)), data_weights[a0:b0][hit])
    K = len(mns)
    v = np.full(K, p.v_rest, np.float32)
    g_exc = np.zeros(K, np.float32); g_inh = np.zeros(K, np.float32); refr = np.zeros(K, np.float32)
    zeros = np.zeros(K, np.float32)
    hp_e = np.zeros(K); other_e = np.zeros(K); inh = np.zeros(K)
    sums = dict(hair=np.zeros(K), other=np.zeros(K), inh=np.zeros(K), total_exc=np.zeros(K), total_inh=np.zeros(K))
    n_window = 0
    decay32 = np.float32(math.exp(-p.dt/p.tau_syn)); decay = math.exp(-p.dt/p.tau_syn)
    depression = np.float32(1)
    predicted = [[] for _ in range(K)]
    lo, hi = window_ticks
    for tick in range(len(fired)):
        arriving = fired[tick - delay] if tick >= delay else ()
        for pre in arriving:
            if pre not in sub:
                continue
            s = np.float32(pre_sign[pre] * p.psp_scale * depression)
            if s == 0:
                continue
            ks, ws = sub[pre]
            values = ws * s
            np.add.at(g_exc if s > 0 else g_inh, ks, values)
            v64 = values.astype(np.float64)
            if s > 0:
                np.add.at(hp_e if pre in hair_sources else other_e, ks, v64)
            else:
                np.add.at(inh, ks, v64)
        refractory = refr > 0
        refr[refractory] -= p.dt; v[refractory] = p.v_reset
        integrate = ~refractory
        if p.conductance_based:
            dv = (p.v_rest - v + g_exc*(p.e_exc - v)/(p.e_exc - p.v_rest) + g_inh*(v - p.e_inh)/(p.v_rest - p.e_inh) + zeros)*(p.dt/p.tau_mem)
        else:
            dv = (p.v_rest - v + g_exc + g_inh + zeros)*(p.dt/p.tau_mem)
        v[integrate] += dv[integrate].astype(np.float32)
        threshold = integrate & (v >= p.v_threshold + zeros + zeros)
        for k in np.flatnonzero(threshold):
            predicted[k].append(tick)
        v[threshold] = p.v_reset; refr[threshold] = p.refractory_ms
        if lo <= tick <= hi:
            n_window += 1
            sums['hair'] += hp_e; sums['other'] += other_e; sums['inh'] += inh
            sums['total_exc'] += g_exc; sums['total_inh'] += g_inh
        g_exc *= decay32; g_inh *= decay32
        hp_e *= decay; other_e *= decay; inh *= decay
    means = {k: (v_/max(n_window, 1)).tolist() for k, v_ in sums.items()}
    return predicted, means


def compare_spikes(predicted, recorded, window_ticks):
    lo, hi = window_ticks
    rows, exact, close = [], True, True
    for pr, rc in zip(predicted, recorded):
        pw = [t for t in pr if lo <= t <= hi]; rw = [t for t in rc if lo <= t <= hi]
        same = pw == rw
        matched, used = 0, set()
        for t in rw:
            for c in (t, t - 1, t + 1):
                if c in pw and c not in used:
                    used.add(c); matched += 1
                    break
        exact &= same
        if len(rw) >= 5 and matched < .95*len(rw):
            close = False
        rows.append(dict(recorded=len(rw), predicted=len(pw), matched=matched, exact=same))
    tot_r = sum(r['recorded'] for r in rows); tot_p = sum(r['predicted'] for r in rows)
    if tot_r and abs(tot_p - tot_r) > .05*tot_r:
        close = False
    status = 'REPLAY_EXACT' if exact else 'REPLAY_CLOSE' if close else 'INCONCLUSIVE_REPLAY'
    return status, rows


# ---- labels ---------------------------------------------------------------------

def q1(best_g, gs):
    rf, lf, lh = best_g['RF'], best_g['LF'], best_g['LH']
    if rf >= gs:
        return 'RF_DIRECT_SUFFICIENT'
    if lf >= gs or lh >= gs:
        return 'RF_DIRECT_SUBTHRESHOLD'
    return 'ALL_SUBTHRESHOLD'


def q3(rf_ratio, lf_ratio):
    return 'INHIBITION_CONTRIBUTES' if rf_ratio >= 2*lf_ratio else 'INHIBITION_NOT_DECISIVE'


def labels(struct, gs, replay_status, inhibition_ratio):
    terms = {leg: struct[leg]['terms'] for leg in struct}
    vs_lf, total_lf = factors(terms['RF'], terms['LF'])
    vs_lh, total_lh = factors(terms['RF'], terms['LH'])
    out = dict(Q1=q1({leg: struct[leg]['best_g'] for leg in ('RF', 'LF', 'LH')}, gs),
               Q2=dict(label=largest_loss(vs_lf), log_ratios=vs_lf, total=total_lf),
               Q2b=dict(label=largest_loss(vs_lh), log_ratios=vs_lh, total=total_lh),
               engine_share=sum(vs_lf[k] for k in ENGINE)/total_lf if total_lf else None)
    if replay_status != 'INCONCLUSIVE_REPLAY':
        out['Q3'] = dict(label=q3(inhibition_ratio['RF'], inhibition_ratio['LF']), ratios=inhibition_ratio)
    return out


# ---- run ------------------------------------------------------------------------

def leg_pools(bodymap, spec):
    motor = a.motor_sets(bodymap)
    out = {}
    for leg in hp.LEGS:
        pops = motor[hp.leg_key(leg)]
        out[leg] = {side: set().union(*(pops.get(n, set()) for n in spec['sets'][side])) for side in ('posterior', 'anterior')}
    return out


def run(cache, raw_path):
    spec = protocol()
    import pandas as pd
    from ..cache import load_cache
    from .. import MaleCNSBrain, load_malecns
    from ..neural import ModelConfig
    from ..live import hair_plate_posture as c
    integrity = {}
    step_a_path = ROOT/spec['sources']['step_a_result']['path']
    integrity['step_a_result_hash'] = sha256(step_a_path) == spec['sources']['step_a_result']['sha256']
    integrity['step_c_raw_hash'] = sha256(raw_path) == spec['sources']['step_c_a_on_raw']['sha256']
    a_spec = a.protocol()
    table = pd.read_feather(ROOT/a_spec['sources']['annotations']['path'])
    integrity['annotation_hash'] = sha256(ROOT/a_spec['sources']['annotations']['path']) == a_spec['sources']['annotations']['sha256']
    cdata = load_cache(cache)
    raw_sets, _ = a.sensory_sets(table, cdata.body_id_to_index)
    sets = {leg: raw_sets[hp.leg_key(leg)] for leg in hp.LEGS}
    data = load_malecns()
    integrity['body_ids_identical'] = bool(np.array_equal(np.asarray(cdata.body_ids), np.asarray(data.body_ids)))
    config = ModelConfig.calibrated()
    floor = config.min_synapses
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    integrity['bodymap_identical'] = cdata.bodymap == bodymap
    pools = leg_pools(bodymap, spec)
    # Step A reproduction: floored direct counts per population.
    step_a = json.loads(step_a_path.read_text(encoding='utf-8'))
    from .posture_sense_inventory import adjacency
    adj = adjacency(cdata, floor)
    motor = a.motor_sets(cdata.bodymap)
    repro = True
    for leg in hp.LEGS:
        seg, side = hp.leg_key(leg)
        s = sorted(sets[leg])
        direct = {n: int(adj[s][:, sorted(ids)].sum()) for n, ids in sorted(motor[(seg, side)].items())}
        repro &= direct == step_a['legs'][f'{seg} {side}']['direct']
    integrity['step_a_direct_reproduced'] = bool(repro)
    # Engine audit on every edge into the replayed MNs.
    _, step_c_coxa = c.mn_sets(bodymap)
    replayed = set().union(*(pools[l]['posterior'] | pools[l]['anterior'] for l in hp.LEGS), *step_c_coxa.values())
    brain = MaleCNSBrain(data)
    pre, post, pos = edges_into(data, replayed)
    _, _, w_rule, sign_rule = rule_weights(data, config, pre, post, pos)
    integrity['engine_weights_equal'] = bool(np.array_equal(w_rule, brain.weights[pos]))
    integrity['engine_signs_equal'] = bool(np.array_equal(sign_rule[pre], brain.pre_sign[pre]))
    struct = structural(data, config, sets, pools, hp.MAX_RATE_HZ, floor)
    gs = g_star(config)
    inv = inventory(data, table, sets, pools, floor)
    # Part M.
    arm = json.load(gzip.open(raw_path, 'rt', encoding='utf-8'))
    schedule = set(map(int, arm['initial']['external_schedule']))
    hair_all = set().union(*map(set, arm['initial']['hair_plate_neurons'].values()))
    integrity['mns_not_forced'] = not (replayed & (schedule | hair_all))
    integrity['raw_complete'] = arm['run_status'] == 'COMPLETE' and len(arm['neural']) == 4000
    fired = [tuple(int(x) for x in t['fired']) for t in arm['neural']]
    lo_ms, hi_ms = spec['measured']['window_ms']
    times = [t['time_ms'] for t in arm['neural']]
    window = (min(i for i, t in enumerate(times) if t > lo_ms), max(i for i, t in enumerate(times) if t <= hi_ms))
    mns = sorted(replayed)
    hair_by_mn = {}
    for leg in hp.LEGS:
        for m in pools[leg]['posterior'] | pools[leg]['anterior'] | step_c_coxa.get(' '.join(hp.leg_key(leg)), set()):
            hair_by_mn.setdefault(m, set()).update(sets[leg])
    # MNs are replayed in groups sharing one own-leg hair-plate set; recorded spikes drive
    # every presynaptic neuron, so groups are independent.
    predicted, means = [None]*len(mns), {}
    groups = {}
    for i, m in enumerate(mns):
        groups.setdefault(frozenset(hair_by_mn.get(m, set())), []).append(i)
    indptr = np.asarray(data.row_ptr, dtype=np.int64); indices = np.asarray(data.target_indices, dtype=np.int64)
    split = {k: [0.]*len(mns) for k in ('hair', 'other', 'inh', 'total_exc', 'total_inh')}
    for hair, idx in groups.items():
        pr, mn_means = replay(fired, [mns[i] for i in idx], brain.weights, indptr, indices, brain.pre_sign,
                              config, brain.delay_steps, hair, window)
        for j, i in enumerate(idx):
            predicted[i] = pr[j]
            for k in split:
                split[k][i] = mn_means[k][j]
    position = {m: i for i, m in enumerate(mns)}
    recorded = [[] for _ in mns]
    for tick, f in enumerate(fired):
        for x in f:
            if x in position:
                recorded[position[x]].append(tick)
    status, rows = compare_spikes(predicted, recorded, window)
    span_s = (hi_ms - lo_ms)/1000.
    measured = {}
    for i, m in enumerate(mns):
        measured[str(m)] = dict(rate_hz=rows[i]['recorded']/span_s, predicted_hz=rows[i]['predicted']/span_s,
                                exact=rows[i]['exact'], matched=rows[i]['matched'],
                                **{f'g_{k}': split[k][i] for k in split})
    ratio = {}
    for leg in ('RF', 'LF', 'LH'):
        m = struct[leg]['best_mn']
        e = measured[str(m)]
        ratio[leg] = abs(e['g_total_inh'])/e['g_total_exc'] if e['g_total_exc'] else float('inf')
    per_leg_rates = {}
    for leg in hp.LEGS:
        key = ' '.join(hp.leg_key(leg))
        for name, ids in (('posterior', pools[leg]['posterior']), ('anterior', pools[leg]['anterior']),
                          ('step_c_coxa', step_c_coxa.get(key, set()))):
            per_leg_rates.setdefault(leg, {})[name] = (float(np.mean([measured[str(x)]['rate_hz'] for x in ids]))
                                                      if ids else None)
    structural_ok = all(v for k, v in integrity.items())
    if not structural_ok:
        verdict, lab = 'INCONCLUSIVE_INTEGRITY', {}
    else:
        verdict = 'INTEGRITY_ACCEPTED' if status != 'INCONCLUSIVE_REPLAY' else 'INCONCLUSIVE_REPLAY'
        lab = labels(struct, gs, status, ratio)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, status=verdict, integrity=integrity,
                replay_status=status, labels=lab, g_star=gs, rate_hz=hp.MAX_RATE_HZ, window_ticks=list(window),
                structural=struct,
                inventory=inv, per_leg_rates=per_leg_rates, inhibition_ratio=ratio, measured=measured,
                interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--step-c-raw', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run(args.cache, args.step_c_raw)
        stream.write((json.dumps(result, indent=1, allow_nan=False, default=str) + '\n').encode())
    print(json.dumps(dict(status=result['status'], replay=result['replay_status'], integrity=result['integrity'],
                          labels={k: (v['label'] if isinstance(v, dict) else v) for k, v in result['labels'].items()}),
                     indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
