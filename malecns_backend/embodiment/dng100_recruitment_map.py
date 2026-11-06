"""Rhythm Step R2: where does DNg100_L's signal stop in R1's rate model? A descriptive recruitment map.

Preregistered in docs/evidence/dng100-recruitment-map-v1/protocol.json. R1's model is reused unchanged
(dng100_rate_model: network, draws, size scaling, solver); the only difference is a fixed drive ladder
instead of the preprint's drive adjustment. Cord-only sizes come from R1b (dng100_size_audit). Neural
only; no rhythm verdict.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.sparse.csgraph import shortest_path

from ..cache import load_cache
from . import dng100_size_audit as r1b
from .dng100_rate_model import B, CELLS, Model, active, dense, draw, scale, score_rates, simulate, WINDOW

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-recruitment-map-v1/protocol.json'
PROTOCOL_SHA256 = '4b26c10aa9c7dff94f68ed73100bd3ebec90fa32c136c47bf5ed13f32824076f'
SCHEMA = 'dng100-recruitment-map-result-v1'
TEXT_SOURCES = {'dng100_rate_model_py_lf_sha256': 'malecns_backend/embodiment/dng100_rate_model.py',
                'dng100_size_audit_py_lf_sha256': 'malecns_backend/embodiment/dng100_size_audit.py',
                'skeleton_dump_mjs_lf_sha256': 'malecns_backend/embodiment/skeleton_dump.mjs',
                'dng100_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_rhythm.py',
                'neural_py_lf_sha256': 'malecns_backend/neural.py',
                'skel_js_lf_sha256': 'fly-brain-main/src/codec/skel.js',
                'rc_js_lf_sha256': 'fly-brain-main/src/codec/rc.js',
                'bodymap_lf_sha256': 'fly-brain-main/public/data/bodymap.json'}
BINARY_SOURCES = {'skeletons_flys_sha256': 'fly-brain-main/public/data/skeletons.flys',
                  'neuron_size_bin_sha256': 'fly-brain-main/public/data/neuron_size.bin',
                  'r1_result_json_sha256': 'docs/evidence/dng100-rate-model-v1/run/result.json',
                  'r1b_result_json_sha256': 'docs/evidence/dng100-size-audit-v1/run/result.json'}
R1_RESULT = 'docs/evidence/dng100-rate-model-v1/run/result.json'
LADDER = [250.*2**k for k in range(9)]
SEEDS = range(1, 17)
ARMS = ('R1SIZE', 'VNCSIZE')
CORE = ('E1', 'E2', 'I1')
MAJORITY = 8
SATURATED = 0.9
RANGE_MAX = 500
R1B_Z_STAR = 462.
R1B_M_VNC = 507457760.
I2_DRIVES = (250., 500., 1000., 2000.)


def lf_sha(path):
    return hashlib.sha256((ROOT/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def raw_sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def sources():
    return {**{k: lf_sha(p) for k, p in TEXT_SOURCES.items()}, **{k: raw_sha(p) for k, p in BINARY_SOURCES.items()}}


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


# ---- structure ---------------------------------------------------------------------------

def hops(W, src):
    """Unweighted directed distance from local index src over all nonzero-sign edges (W[post, pre])."""
    return shortest_path((W != 0).T.astype(float), indices=src, unweighted=True)


def intermediates(W, src, targets):
    """Two-hop intermediates src -> k -> target, per target (local indices, sorted)."""
    out = np.asarray(W[:, src].todense()).ravel()
    first = set(np.flatnonzero(out).tolist())
    return {t: sorted(k for k in first if W[targets[t], k] != 0) for t in targets}


def input_parts(W, r, j, theta, b=B):
    """Excitatory and inhibitory synaptic input to local cell j at rates r, threshold, margin."""
    row = np.asarray(W[j].todense()).ravel()
    exc = b*float(row[row > 0] @ r[row > 0])
    inh = b*float(row[row < 0] @ r[row < 0])
    return dict(exc=exc, inh=inh, theta=float(theta[j]), margin=exc + inh - float(theta[j]))


def cord_only_sizes(data, net):
    """R1b cord-only sizes for R1's network: f measured for DNs/ANs, f = 1 otherwise; reference m_VNC."""
    voff, pos, seg = r1b.decode()
    sup = np.asarray(data.superclass_ids)
    brain_sc, cord_sc = r1b.brain_cord_sets(data.superclasses)
    vsc = sup[np.repeat(np.arange(len(voff) - 1), np.diff(voff))]
    plane = r1b.neck_plane(pos[np.isin(vsc, brain_sc), 2], pos[np.isin(vsc, cord_sc), 2])
    total, above = r1b.cable_split(voff, pos, seg, plane['z_star'])
    with np.errstate(divide='ignore', invalid='ignore'):
        f = np.where(total > 0, above/total, np.nan)
    from ..neural import ModelConfig, region_scales
    _, regions, med = region_scales(data, ModelConfig())
    size = np.asarray(data.neuron_sizes, float)
    _, _, _, m_vnc = r1b.scaling(size, f, regions == 2, float(med[2]))
    names = np.asarray(data.superclasses, object)[sup[net]]
    dnan = np.isin(names, ['descending_neuron', 'ascending_neuron'])
    f_net = np.where(dnan, f[net], 1.)
    return size[net]*f_net, m_vnc, plane['z_star'], f_net


# ---- one simulation -----------------------------------------------------------------------

def one(model, sizes, ref, seed, drive, ctx):
    p = draw(seed, len(model.net))
    a, theta, _ = scale(p, sizes, ref)
    rates = simulate(model.W, a, theta, p['tau'], p['rmax'], ctx['stim'], drive, [])
    window = rates[WINDOW[0]:WINDOW[1]]
    act = active(rates)
    dist = ctx['dist']
    layers = {('unreachable' if np.isinf(k) else str(int(k))): int(act[dist == k].sum()) for k in np.unique(dist)}
    last = rates[-1]
    core = {}
    for name in CORE:
        j = ctx['core'][name]
        parts = input_parts(model.W, last, j, theta)
        row = np.asarray(model.W[j].todense()).ravel()
        contrib = B*row*last
        pre = [k for k in np.flatnonzero(row) if act[k]]
        top = sorted(pre, key=lambda k: -abs(contrib[k]))[:5]
        core[name] = dict(active=bool(act[j]), max_hz=float(window[:, j].max()), mean_hz=float(window[:, j].mean()),
                          **parts, active_presynaptic=len(pre),
                          top_active_inputs={str(model.net[k]): float(contrib[k]) for k in top})
    score, freq, detail = score_rates(rates, model.mn_local, model.names)
    s = ctx['stim']
    deepest = max((int(k) for k in np.unique(dist[act]) if np.isfinite(k)), default=None)
    return dict(seed=seed, drive=drive, recruited=int(act.sum()), dng100_mean_hz=float(window[:, s].mean()),
                dng100_frac_rmax=float(window[:, s].mean()/p['rmax'][s]), layers=layers, deepest_layer=deepest,
                classes={c: int(act[idx].sum()) for c, idx in ctx['classes'].items()},
                active_mns=len(detail), core=core,
                intermediates={str(model.net[k]): float(window[:, k].max()) for k in ctx['mids']},
                rhythm_score_reported_only=score, rhythm_frequency_reported_only=freq)


# ---- labels ---------------------------------------------------------------------------------

def cell_label(sims, name, ladder=LADDER):
    """sims: list of simulation dicts for one arm."""
    for d in ladder:
        if sum(s['core'][name]['active'] for s in sims if s['drive'] == d) >= MAJORITY:
            return f'ENGAGED_AT_{int(d)}', d
    top = [s for s in sims if s['drive'] == ladder[-1]]
    sat = sum(s['dng100_frac_rmax'] >= SATURATED for s in top) >= MAJORITY
    return ('NOT_ENGAGED_DNG100_SATURATED' if sat else 'NOT_ENGAGED_UNSATURATED'), None


def arm_label(sims, ladder=LADDER):
    cells = {c: cell_label(sims, c, ladder) for c in CORE}
    engaged = [d for _, d in cells.values() if d is not None]
    detail = dict(cells={c: lab for c, (lab, _) in cells.items()})
    if not engaged:
        return 'CORE_NOT_REACHED', detail
    if len(engaged) < len(CORE):
        return 'CORE_PARTIAL', detail
    d = max(engaged)
    med = float(np.median([s['recruited'] for s in sims if s['drive'] == d]))
    detail.update(highest_engaging_drive=d, median_recruited_there=med)
    return ('CORE_REACHED_IN_PREPRINT_RANGE' if med <= RANGE_MAX else 'CORE_REACHED_BEYOND_RANGE'), detail


def stopping_point(sims, ctx_mids_by_cell, ladder=LADDER):
    top = [s for s in sims if s['drive'] == ladder[-1]]
    out = {}
    for name in CORE:
        if cell_label(sims, name, ladder)[1] is not None:
            continue
        mids = ctx_mids_by_cell[name]
        on = [m for m in mids if sum(s['intermediates'][m] > 0.01 for s in top) >= MAJORITY]
        layers = [s['deepest_layer'] for s in top if s['deepest_layer'] is not None]
        out[name] = dict(median_margin=float(np.median([s['core'][name]['margin'] for s in top])),
                         active_intermediates=on, silent_intermediates=[m for m in mids if m not in on],
                         median_deepest_layer=float(np.median(layers)) if layers else None)
    return out


def summary(sims, ladder=LADDER):
    rows = []
    for d in ladder:
        at = [s for s in sims if s['drive'] == d]
        rows.append(dict(drive=d, median_recruited=float(np.median([s['recruited'] for s in at])),
                         median_dng100_hz=float(np.median([s['dng100_mean_hz'] for s in at])),
                         median_active_mns=float(np.median([s['active_mns'] for s in at])),
                         core_active_seeds={c: int(sum(s['core'][c]['active'] for s in at)) for c in CORE},
                         core_median_margin={c: float(np.median([s['core'][c]['margin'] for s in at])) for c in CORE}))
    return rows


def i2_check(sims, r1_runs):
    """R1SIZE recruited counts must equal R1's recorded history at the shared drives (seeds 1-16)."""
    got = {(s['seed'], s['drive']): s['recruited'] for s in sims}
    bad, checked = [], 0
    for run in r1_runs:
        if run['seed'] not in SEEDS:
            continue
        for h in run['history']:
            if h['i_stim'] in I2_DRIVES:
                checked += 1
                if got.get((run['seed'], h['i_stim'])) != h['recruited']:
                    bad.append(dict(seed=run['seed'], drive=h['i_stim'], r1=h['recruited'],
                                    r2=got.get((run['seed'], h['i_stim']))))
    return dict(passed=not bad and checked > 0, checked=checked, mismatches=bad)


def expectations(labels):
    r1, vnc = labels['R1SIZE'], labels['VNCSIZE']
    d = lambda lab: math.inf if not lab.startswith('ENGAGED_AT_') else float(lab.split('_')[-1])
    e1 = d(r1[1]['cells']['E1'])
    x3 = {c: d(vnc[1]['cells'][c]) <= d(r1[1]['cells'][c]) for c in CORE}
    vacuous = [c for c in CORE if math.isinf(d(vnc[1]['cells'][c])) and math.isinf(d(r1[1]['cells'][c]))]
    return dict(X1=bool(math.isfinite(e1) and e1 >= 4000), X2=r1[0] == 'CORE_REACHED_BEYOND_RANGE',
                X3=all(x3.values()), X3_per_cell=x3, X3_vacuous_cells=vacuous)


# ---- run --------------------------------------------------------------------------------------

def context(data, model):
    ids = {k: dense(data, b) for k, b in CELLS.items()}
    stim = model.pos[ids['DNg100_L']]
    core = {c: model.pos[ids[c]] for c in CORE}
    dist = hops(model.W, stim)
    mids_by_cell = intermediates(model.W, stim, core)
    mids = sorted(set().union(*map(set, mids_by_cell.values())))
    sup = np.asarray(data.superclass_ids)
    names = np.asarray(data.superclasses, object)[sup[model.net]]
    mn = np.zeros(len(model.net), bool)
    mn[list(model.mn_local.values())] = True
    cls = dict(dn=names == 'descending_neuron', an=names == 'ascending_neuron', mn=mn,
               cord=np.array([str(x).startswith('vnc_') for x in names]) & ~mn)
    cls['other'] = ~(cls['dn'] | cls['an'] | cls['mn'] | cls['cord'])
    return dict(stim=stim, core=core, dist=dist, mids=mids,
                mids_by_cell={c: [str(model.net[k]) for k in v] for c, v in mids_by_cell.items()},
                classes={k: np.flatnonzero(v) for k, v in cls.items()})


def run(cache, progress=print):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    data = load_cache(cache)
    model = Model(data)
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in model.net)).encode()).hexdigest()
    ctx = context(data, model)
    mid_bodies = sorted(int(data.body_ids[model.net[k]]) for k in ctx['mids'])
    vnc_size, m_vnc, z_star, f_net = cord_only_sizes(data, np.asarray(model.net))
    integrity = dict(r1_network_body_ids_sha256=body_sha, intermediate_body_ids=mid_bodies, z_star=z_star, m_vnc=m_vnc)
    integrity['I1_pass'] = bool(body_sha == spec['integrity']['r1_network_body_ids_sha256']
                                and mid_bodies == spec['integrity']['intermediate_body_ids']
                                and z_star == R1B_Z_STAR and m_vnc == R1B_M_VNC
                                and bool(np.isfinite(vnc_size).all()))
    if not integrity['I1_pass']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I1 failed',
                    integrity=integrity, sources=src)
    started = time.time()
    arms = {'R1SIZE': (model.size, model.size_ref), 'VNCSIZE': (vnc_size, m_vnc)}
    sims = {}
    for arm, (sizes, ref) in arms.items():
        sims[arm] = []
        for d in LADDER:
            for seed in SEEDS:
                sims[arm].append(dict(arm=arm, **one(model, sizes, ref, seed, d, ctx)))
            at = sims[arm][-len(SEEDS):]
            progress(f'[{time.time()-started:6.0f}s] {arm} I={int(d)}: recruited median '
                     f'{np.median([s["recruited"] for s in at])}, DNg100 {np.median([s["dng100_mean_hz"] for s in at]):.1f} Hz, '
                     f'core active {[sum(s["core"][c]["active"] for s in at) for c in CORE]}', flush=True)
    i2 = i2_check(sims['R1SIZE'], json.loads((ROOT/R1_RESULT).read_bytes())['dng100']['runs'])
    i4 = all(len(v) == len(LADDER)*len(SEEDS) for v in sims.values())
    integrity.update(I2=i2, I4_complete=i4)
    labels = {arm: arm_label(v) for arm, v in sims.items()}
    out = dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256,
               verdict='INCONCLUSIVE' if not (i2['passed'] and i4) else 'MAP_RECORDED',
               labels={arm: dict(label=lab, **det) for arm, (lab, det) in labels.items()},
               expectations=expectations(labels),
               stopping_point={arm: stopping_point(v, ctx['mids_by_cell']) for arm, v in sims.items()},
               summary={arm: summary(v) for arm, v in sims.items()},
               structure=dict(hop_layers={('unreachable' if np.isinf(k) else str(int(k))): int((ctx['dist'] == k).sum())
                                          for k in np.unique(ctx['dist'])},
                              intermediates_by_cell=ctx['mids_by_cell'],
                              vncsize_f_dn_an_median=float(np.median(f_net[f_net < 1])) if (f_net < 1).any() else None),
               integrity=integrity, simulations=sims, sources=src, runtime_s=round(time.time() - started, 1),
               interpretation_limits=spec['interpretation_limits'])
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--describe', action='store_true',
                        help='plumbing: hashes, network hash, intermediate body IDs (structure only, no simulation)')
    parser.add_argument('--time-one', action='store_true',
                        help='plumbing: one R1SIZE simulation, seed 0 (not a protocol seed), I=64000; wall time only')
    args = parser.parse_args(argv)
    if args.describe or args.time_one:
        data = load_cache(args.cache)
        model = Model(data)
        ctx = context(data, model)
        if args.describe:
            body = sorted(int(data.body_ids[i]) for i in model.net)
            print(json.dumps(dict(sources=sources(),
                                  r1_network_body_ids_sha256=hashlib.sha256(json.dumps(body).encode()).hexdigest(),
                                  intermediate_body_ids=sorted(int(data.body_ids[model.net[k]]) for k in ctx['mids']),
                                  intermediates_by_cell=ctx['mids_by_cell']), indent=1))
        if args.time_one:
            t = time.time()
            one(model, model.size, model.size_ref, 0, LADDER[-1], ctx)
            print(json.dumps(dict(one_simulation_s=round(time.time() - t, 2))))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(r1b.jsonable(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(r1b.jsonable({k: result.get(k) for k in ('verdict', 'labels', 'expectations', 'stopping_point', 'reason',
                                                         'runtime_s')}), indent=1))
    print(json.dumps(r1b.jsonable(dict(I2=result.get('integrity', {}).get('I2'))), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
