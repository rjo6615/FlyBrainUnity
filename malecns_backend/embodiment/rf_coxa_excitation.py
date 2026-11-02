"""Right-front coxa MN excitation V1: wiring, activity, or a consequence of weak hair plates?

Preregistered in docs/evidence/rf-coxa-excitation-v1/protocol.json. Data only: replays the
Step C held-posture arms A_OFF and A_ON with the drive-asymmetry V1 replay, unchanged.
"""
import argparse
import gzip
import json
import math
from pathlib import Path

import numpy as np

from . import coxa_drive_asymmetry as d
from . import hair_plate_encoder as hp
from . import hair_plate_identity as a

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/rf-coxa-excitation-v1/protocol.json'
PROTOCOL_SHA256 = '50f2829fe569f579d1ae1d75d2d2ca8e680fd1f0cf5057efdbe5102f764a40d6'
SCHEMA = 'rf-coxa-excitation-result-v1'
ARMS = ('A_OFF', 'A_ON')


def protocol():
    import hashlib
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


# ---- E1: per-partner attribution ------------------------------------------------

def kernel_sum(delivery_ticks, window, decay):
    """Sum over deliveries d of K(d) = sum_{t=max(d,lo)}^{hi} decay^(t-d)."""
    lo, hi = window
    total = 0.
    for dtick in delivery_ticks:
        if dtick > hi:
            continue
        start = max(dtick, lo)
        total += decay**(start - dtick)*(1. - decay**(hi - start + 1))/(1. - decay)
    return total


def attribute(fired, targets, weights, indptr, indices, pre_sign, config, delay, window):
    """{m: {pre: window-mean excitatory g contributed}} for excitatory presynaptic partners."""
    lo, hi = window
    n_window = hi - lo + 1
    decay = math.exp(-config.dt/config.tau_syn)
    tset = np.fromiter(sorted(targets), np.int64)
    pos = np.flatnonzero(np.isin(indices, tset))
    pres = np.searchsorted(indptr, pos, side='right') - 1
    edges = {}
    for p_, q in zip(pres.tolist(), pos.tolist()):
        s = np.float32(pre_sign[p_]*config.psp_scale*np.float32(1))
        if s > 0:
            edges.setdefault(p_, []).append((int(indices[q]), float(np.float32(weights[q]*s))))
    deliveries = {p_: [] for p_ in edges}
    for tick, f in enumerate(fired):
        dtick = tick + delay
        if dtick >= len(fired):
            break
        for x in f:
            if x in deliveries:
                deliveries[x].append(dtick)
    out = {m: {} for m in targets}
    for p_, rows in edges.items():
        k = kernel_sum(deliveries[p_], window, decay)/n_window
        for m, value in rows:
            out[m][p_] = out[m].get(p_, 0.) + value*k
    return out, {p_: [(m, v) for m, v in rows] for p_, rows in edges.items()}


def split_terms(wpot_x, wpot_y, on_x, on_y):
    """WIRING and ACTIVITY log terms of x over y; they sum to log(on_x/on_y)."""
    if wpot_x == 0 or wpot_y == 0:
        return None, None
    wiring = math.log(wpot_x/wpot_y)
    activity = math.log((on_x/wpot_x)/(on_y/wpot_y)) if on_x > 0 and on_y > 0 else None
    return wiring, activity


def q2_label(wiring, activity, wpot_x):
    if wpot_x == 0:
        return 'WIRING_GAP'
    if wiring is None:
        return 'NOT_DEFINED'
    if activity is None:  # g_other(x) = 0 with wiring present
        return 'ACTIVITY_GAP'
    neg = [(v, k) for k, v in (('WIRING_GAP', wiring), ('ACTIVITY_GAP', activity)) if v < 0]
    if not neg:
        return 'NO_GAP'
    if len(neg) == 2 and abs(abs(neg[0][0]) - abs(neg[1][0])) <= .1*max(abs(neg[0][0]), abs(neg[1][0])):
        return 'MIXED'
    return min(neg)[1]


def q1_label(frac_lf, frac_lh):
    lf, lh = frac_lf >= .5, frac_lh >= .5
    return 'HAIR_EVOKED' if lf and lh else 'BASELINE' if not lf and not lh else 'MIXED_LEGS'


def q3_label(off_rf, off_lf, on_rf, on_lf):
    if off_rf < .67*off_lf:
        return 'PRE_EXISTING_ASYMMETRY'
    if on_rf < .33*on_lf:
        return 'CONSEQUENCE_OF_HAIR_PLATES'
    return 'NOT_DETERMINED'


def leg_quantities(contrib, own_hair, m):
    other = {p_: v for p_, v in contrib[m].items() if p_ not in own_hair}
    return other, sum(other.values()), sum(v for p_, v in contrib[m].items() if p_ in own_hair)


def labels(best, g_other, wpot):
    """best: {leg: mn}; g_other: {arm: {mn: value}}; wpot: {mn: value}."""
    on, off = g_other['A_ON'], g_other['A_OFF']
    frac = {leg: ((on[best[leg]] - off[best[leg]])/on[best[leg]] if on[best[leg]] else 0.) for leg in ('LF', 'LH')}
    out = dict(Q1=dict(label=q1_label(frac['LF'], frac['LH']), hair_evoked_fraction=frac))
    for key, ref in (('Q2', 'LF'), ('Q2b', 'LH')):
        x, y = best['RF'], best[ref]
        wiring, activity = split_terms(wpot[x], wpot[y], on[x], on[y])
        out[key] = dict(label=q2_label(wiring, activity, wpot[x]), wiring=wiring, activity=activity,
                        total=(math.log(on[x]/on[y]) if on[x] > 0 and on[y] > 0 else None))
    out['Q3'] = dict(label=q3_label(off[best['RF']], off[best['LF']], on[best['RF']], on[best['LF']]),
                     off_ratio=off[best['RF']]/off[best['LF']] if off[best['LF']] else None,
                     on_ratio=on[best['RF']]/on[best['LF']] if on[best['LF']] else None)
    return out


# ---- run ------------------------------------------------------------------------

def run(cache, raw_dir):
    spec = protocol()
    d.protocol()  # V1 hash lock
    import pandas as pd
    from ..cache import load_cache
    from .. import MaleCNSBrain, load_malecns
    from ..neural import ModelConfig
    src = spec['sources']
    integrity = dict(v1_result_hash=d.sha256(ROOT/src['v1_result']['path']) == src['v1_result']['sha256'],
                     step_c_report_hash=d.sha256(ROOT/src['step_c_report']['path']) == src['step_c_report']['sha256'])
    report = json.loads((ROOT/src['step_c_report']['path']).read_text(encoding='utf-8'))
    paths = {arm: Path(raw_dir)/f'{arm}.json.gz' for arm in ARMS}
    for arm in ARMS:
        integrity[f'{arm}_hash'] = d.sha256(paths[arm]) == src['arms'][arm] == report['arm_sha256'][arm]
    v1 = json.loads((ROOT/src['v1_result']['path']).read_text(encoding='utf-8'))
    best = {leg: int(v1['structural'][leg]['best_mn']) for leg in hp.LEGS}
    a_spec = a.protocol()
    table = pd.read_feather(ROOT/a_spec['sources']['annotations']['path'])
    cdata = load_cache(cache)
    raw_sets, _ = a.sensory_sets(table, cdata.body_id_to_index)
    sets = {leg: raw_sets[hp.leg_key(leg)] for leg in hp.LEGS}
    data = load_malecns()
    integrity['body_ids_identical'] = bool(np.array_equal(np.asarray(cdata.body_ids), np.asarray(data.body_ids)))
    config = ModelConfig.calibrated()
    bodymap = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text(encoding='utf-8'))
    pools = d.leg_pools(bodymap, d.protocol())
    leg_of = {m: leg for leg in hp.LEGS for m in pools[leg]['posterior']}
    targets = set(leg_of)
    brain = MaleCNSBrain(data)
    pre, post, pos = d.edges_into(data, targets)
    _, _, w_rule, sign_rule = d.rule_weights(data, config, pre, post, pos)
    integrity['engine_weights_equal'] = bool(np.array_equal(w_rule, brain.weights[pos]))
    integrity['engine_signs_equal'] = bool(np.array_equal(sign_rule[pre], brain.pre_sign[pre]))
    indptr = np.asarray(data.row_ptr, dtype=np.int64); indices = np.asarray(data.target_indices, dtype=np.int64)
    counts = np.asarray(data.synapse_counts)
    # downstream of own-leg hair plates: floored direct edge from any own-leg SNpp45
    downstream = {}
    for leg in hp.LEGS:
        ds = set()
        for s in sets[leg]:
            a0, b0 = indptr[s], indptr[s + 1]
            ds.update(indices[a0:b0][counts[a0:b0] >= config.min_synapses].tolist())
        downstream[leg] = ds
    body = np.asarray(data.body_ids)
    by_body = {int(r['bodyId']): r for _, r in table.iterrows()}
    arms, contrib, replay_status, rates, sum_ok = {}, {}, {}, {}, True
    mns = sorted(targets)
    for arm in ARMS:
        raw = json.load(gzip.open(paths[arm], 'rt', encoding='utf-8'))
        arms[arm] = raw
        fired = [tuple(int(x) for x in t['fired']) for t in raw['neural']]
        lo_ms, hi_ms = spec['targets']['window_ms']
        times = [t['time_ms'] for t in raw['neural']]
        window = (min(i for i, t in enumerate(times) if t > lo_ms), max(i for i, t in enumerate(times) if t <= hi_ms))
        hair_all = set().union(*map(set, raw['initial']['hair_plate_neurons'].values()))
        schedule = set(map(int, raw['initial']['external_schedule']))
        integrity[f'{arm}_targets_not_forced'] = not (targets & (hair_all | schedule))
        integrity[f'{arm}_complete'] = raw['run_status'] == 'COMPLETE' and len(raw['neural']) == 4000
        predicted, split = [None]*len(mns), {k: [0.]*len(mns) for k in ('hair', 'other')}
        groups = {}
        for i, m in enumerate(mns):
            groups.setdefault(leg_of[m], []).append(i)
        for leg, idx in groups.items():
            pr, means = d.replay(fired, [mns[i] for i in idx], brain.weights, indptr, indices, brain.pre_sign,
                                 config, brain.delay_steps, sets[leg], window)
            for j, i in enumerate(idx):
                predicted[i] = pr[j]; split['hair'][i] = means['hair'][j]; split['other'][i] = means['other'][j]
        position = {m: i for i, m in enumerate(mns)}
        recorded = [[] for _ in mns]
        for tick, f in enumerate(fired):
            for x in f:
                if x in position:
                    recorded[position[x]].append(tick)
        replay_status[arm], _ = d.compare_spikes(predicted, recorded, window)
        c_, _ = attribute(fired, targets, brain.weights, indptr, indices, brain.pre_sign, config, brain.delay_steps, window)
        contrib[arm] = c_
        for i, m in enumerate(mns):
            ref = split['hair'][i] + split['other'][i]
            got = sum(c_[m].values())
            if abs(got - ref) > max(1e-6*abs(ref), 1e-9):
                sum_ok = False
        spikes = np.zeros(data.neuron_count, np.int64)
        for tick in range(window[0], window[1] + 1):
            if fired[tick]:
                spikes[list(fired[tick])] += 1
        rates[arm] = spikes/((hi_ms - lo_ms)/1000.)
    integrity['E1_sum_check'] = sum_ok
    integrity['replay_ok'] = all(s != 'INCONCLUSIVE_REPLAY' for s in replay_status.values())
    integrity['schedule_identical'] = arms['A_OFF']['initial']['external_schedule'] == arms['A_ON']['initial']['external_schedule']
    integrity['uniforms_identical'] = all(x['uniforms_sha256'] == y['uniforms_sha256']
                                          for x, y in zip(arms['A_OFF']['neural'], arms['A_ON']['neural']))
    del arms
    # E2-E4 per target
    _, edge_values = attribute([()], targets, brain.weights, indptr, indices, brain.pre_sign, config, brain.delay_steps, (0, 0))
    wpot, g_other, per_target = {}, {arm: {} for arm in ARMS}, {}
    def describe(p_):
        r = by_body.get(int(body[p_]), {})
        return dict(type=str(data.types[p_]), superclass=str(data.superclasses[data.superclass_ids[p_]]),
                    side=a.side_of(r) or 'unknown' if len(r) else 'unknown')
    for m in mns:
        leg = leg_of[m]
        own = sets[leg]
        wpot[m] = sum(v for p_, rows in edge_values.items() if p_ not in own for mm, v in rows if mm == m)
        entry = dict(leg=leg, W_pot=wpot[m], arms={})
        for arm in ARMS:
            other, g_o, g_h = leg_quantities(contrib[arm], own, m)
            g_other[arm][m] = g_o
            groups = {}
            for p_, v in other.items():
                info = describe(p_)
                for key in ('superclass', 'side'):
                    groups.setdefault(key, {}).setdefault(info[key], 0.)
                    groups[key][info[key]] += v
                ds = 'downstream_of_own_hair_plates' if p_ in downstream[leg] else 'not_downstream'
                groups.setdefault('downstream', {}).setdefault(ds, 0.)
                groups['downstream'][ds] += v
            top = sorted(other.items(), key=lambda kv: -kv[1])[:15]
            entry['arms'][arm] = dict(g_hair=g_h, g_other=g_o, rate_hz=float(rates[arm][m]), by=groups,
                                      top_partners=[dict(dense=p_, body_id=int(body[p_]), g=v, rate_hz=float(rates[arm][p_]),
                                                         downstream=p_ in downstream[leg], **describe(p_)) for p_, v in top])
        per_target[str(m)] = entry
    lab = labels(best, g_other, wpot) if all(integrity.values()) else {}
    # E5 type table, RF vs LF best MNs
    types = {}
    for leg in ('RF', 'LF'):
        m = best[leg]
        for p_, rows in edge_values.items():
            if p_ in sets[leg]:
                continue
            for mm, v in rows:
                if mm == m:
                    t = str(data.types[p_])
                    row = types.setdefault(t, dict(weight_RF=0., weight_LF=0.))
                    row[f'weight_{leg}'] += v
    sides = {}
    for i, t in enumerate(data.types):
        if str(t) in types:
            r = by_body.get(int(body[i]), {})
            s = a.side_of(r) if len(r) else None
            sides.setdefault(str(t), {}).setdefault(s or 'unknown', []).append(i)
    for t, row in types.items():
        for arm in ARMS:
            for s, ids in sides.get(t, {}).items():
                row[f'rate_{arm}_{s}'] = float(np.mean(rates[arm][ids]))
    # pool-level (descriptive)
    pool = {}
    for leg in hp.LEGS:
        ids = sorted(pools[leg]['posterior'])
        pool[leg] = dict(W_pot=sum(wpot[m] for m in ids), **{f'g_other_{arm}': sum(g_other[arm][m] for m in ids) for arm in ARMS})
    pool_labels = labels({leg: leg for leg in hp.LEGS},
                         {arm: {leg: pool[leg][f'g_other_{arm}'] for leg in hp.LEGS} for arm in ARMS},
                         {leg: pool[leg]['W_pot'] for leg in hp.LEGS})
    status = 'INTEGRITY_ACCEPTED' if all(integrity.values()) else 'INCONCLUSIVE_INTEGRITY'
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, status=status, integrity=integrity,
                replay_status=replay_status, labels=lab, best_mn=best, per_target=per_target,
                type_table=dict(sorted(types.items(), key=lambda kv: -(kv[1]['weight_RF'] + kv[1]['weight_LF']))),
                pool=pool, pool_labels_descriptive=pool_labels, interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--step-c-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run(args.cache, args.step_c_dir)
        stream.write((json.dumps(result, indent=1, allow_nan=False, default=str) + '\n').encode())
    print(json.dumps(dict(status=result['status'], replay=result['replay_status'], integrity=result['integrity'],
                          labels={k: v['label'] for k, v in result['labels'].items()}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
