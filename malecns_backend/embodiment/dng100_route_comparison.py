"""Rhythm Step R4: structural comparison of routes into the E1/E2/I1 core.

Preregistered in docs/evidence/dng100-route-comparison-v1/protocol.json. Structure only, on R1's
signed network matrix (dng100_rate_model); hops and intermediates from R2. No simulation.
"""
import argparse
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.stats import rankdata

from ..cache import load_cache
from . import dng100_recruitment_map as r2
from .dng100_rate_model import CELLS, Model, dense
from .dng100_size_audit import jsonable

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-route-comparison-v1/protocol.json'
PROTOCOL_SHA256 = '7c173a3550eb8c851c9cdd9e0d8b0337eb5a29c9749ceef8ebe2a695689f79a8'
SCHEMA = 'dng100-route-comparison-result-v1'
TEXT_SOURCES = {**r2.TEXT_SOURCES,
                'dng100_recruitment_map_py_lf_sha256': 'malecns_backend/embodiment/dng100_recruitment_map.py',
                'dng100_engaged_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_engaged_rhythm.py'}
BINARY_SOURCES = {**r2.BINARY_SOURCES,
                  'r2_result_json_sha256': 'docs/evidence/dng100-recruitment-map-v1/run/result.json',
                  'r3_result_json_sha256': 'docs/evidence/dng100-engaged-rhythm-v1/run/result.json'}
R2_RESULT = 'docs/evidence/dng100-recruitment-map-v1/run/result.json'
R3_RESULT = 'docs/evidence/dng100-engaged-rhythm-v1/run/result.json'
CORE = ('E1', 'E2', 'I1')
CONTROLS = [92, 278, 754, 763, 820, 1052, 1087, 1599, 2659, 4164, 4685, 9205, 9762, 11053, 21341, 26520, 39896,
            128032, 129181, 130496]
EXPECTED_RHYTHMIC = [1087, 129181, 130496]
RHYTHMIC_SCORE = .5
METRICS = ('direct_E1', 'direct_E2', 'direct_I1', 'twohop_E1', 'twohop_E2', 'twohop_I1', 'i1_share', 'core_focus',
           'out_degree', 'out_weight', 'direct_mn', 'core_hops')
ALPHA = .05/len(METRICS)
NAN_ALLOWED = {'i1_share', 'core_focus'}
INF_ALLOWED = {'core_hops'}


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


# ---- groups ------------------------------------------------------------------------------------

def rhythmic_group(r3_result, controls=CONTROLS):
    """R1's control DNs with R3 R1SIZE control score >= 0.5 (dense indices, sorted)."""
    c = r3_result['arms']['R1SIZE']['controls']
    out = []
    for d in controls:
        s = c[str(d)]['score']
        if isinstance(s, (int, float)) and not math.isnan(s) and s >= RHYTHMIC_SCORE:
            out.append(d)
    return sorted(out)


# ---- metrics ----------------------------------------------------------------------------------

def metrics(W, s, core, mn_local, dist=None):
    """The 12 preregistered metrics for local source s; core = {name: local index}."""
    W = W.tocsr()
    n = W.shape[0]
    col = np.asarray(W[:, s].todense()).ravel()
    out = {}
    for c, j in core.items():
        out[f'direct_{c}'] = float(col[j])
    mid = col.copy()
    mid[s] = 0.
    for c, j in core.items():
        row = np.asarray(W[j].todense()).ravel()
        m = mid.copy()
        m[j] = 0.
        out[f'twohop_{c}'] = float(row @ m)
    Wp = W.multiply(W > 0).tocsr()
    midp = np.where(mid > 0, mid, 0.)
    exc2 = np.asarray(Wp @ midp).ravel() - Wp.diagonal()*midp   # exclude k == j
    exc2[s] = 0.
    core_exc = {c: float(exc2[j]) for c, j in core.items()}
    tot_core = sum(core_exc.values())
    out['i1_share'] = core_exc['I1']/tot_core if tot_core > 0 else math.nan
    tot_all = float(exc2.sum())
    out['core_focus'] = tot_core/tot_all if tot_all > 0 else math.nan
    out_col = col.copy()
    out_col[s] = 0.
    out['out_degree'] = int(np.count_nonzero(out_col))
    out['out_weight'] = float(np.abs(out_col).sum())
    out['direct_mn'] = float(sum(col[m] for m in mn_local))
    d = r2.hops(W, s) if dist is None else dist
    hops = [float(d[j]) for j in core.values()]
    out['core_hops'] = math.inf if any(math.isinf(h) for h in hops) else float(np.mean(hops))
    assert n == W.shape[1]
    return out


# ---- statistics --------------------------------------------------------------------------------

def perm_test(values, rhythmic_mask):
    """Exact two-sided permutation test of the rank sum of the rhythmic group (mid-ranks).

    NaN values are excluded; if any rhythmic value is NaN the metric cannot separate (p NaN)."""
    v = np.asarray(values, float)
    r = np.asarray(rhythmic_mask, bool)
    if np.any(np.isnan(v[r])):
        return dict(p=math.nan, n=int((~np.isnan(v)).sum()), assignments=0, rank_sum=math.nan)
    keep = ~np.isnan(v)
    v, r = v[keep], r[keep]
    ranks = rankdata(v)
    k, n = int(r.sum()), len(v)
    expect = k*(n + 1)/2
    obs = abs(ranks[r].sum() - expect)
    sums = np.array([ranks[list(c)].sum() for c in combinations(range(n), k)])
    p = float(np.mean(np.abs(sums - expect) >= obs - 1e-9))
    return dict(p=p, n=n, assignments=len(sums), rank_sum=float(ranks[r].sum()))


def placement(dng, rhythmic_vals, nonrhythmic_vals):
    """'nonrhythmic_side' if DNg100's value is strictly outside the rhythmic range toward the
    nonrhythmic median; otherwise 'not_nonrhythmic_side'."""
    rv = np.asarray(rhythmic_vals, float)
    nv = np.asarray([x for x in nonrhythmic_vals if not math.isnan(x)], float)
    if math.isnan(dng) or len(nv) == 0:
        return 'not_nonrhythmic_side'
    rm, nm = float(np.median(rv)), float(np.median(nv))
    if nm < rm and dng < rv.min():
        return 'nonrhythmic_side'
    if nm > rm and dng > rv.max():
        return 'nonrhythmic_side'
    return 'not_nonrhythmic_side'


def evaluate(table, rhythmic, controls=CONTROLS, dng100='DNG100'):
    """table: {label: {metric: value}} with str(control) labels and dng100. Returns per-metric and verdict."""
    mask = [c in rhythmic for c in controls]
    per = {}
    for m in METRICS:
        vals = [table[str(c)][m] for c in controls]
        t = perm_test(vals, mask)
        sep = bool(not math.isnan(t['p']) and t['p'] <= ALPHA)
        rv = [v for v, k in zip(vals, mask) if k]
        nv = [v for v, k in zip(vals, mask) if not k]
        per[m] = dict(t, separates=sep, rhythmic=rv, nonrhythmic_median=float(np.nanmedian(nv)),
                      rhythmic_median=float(np.median(rv)) if not any(math.isnan(x) for x in rv) else math.nan,
                      dng100=table[dng100][m],
                      placement=placement(table[dng100][m], rv, nv) if sep else None)
    seps = [m for m in METRICS if per[m]['separates']]
    if not seps:
        v = 'NO_SIGNATURE'
    elif any(per[m]['placement'] == 'nonrhythmic_side' for m in seps):
        v = 'SIGNATURE_DNG100_DIFFERS'
    else:
        v = 'SIGNATURE_DNG100_LIKE_RHYTHMIC'
    return v, per, seps


def expectations(verdict_, table, rhythmic):
    rh = [table[str(c)] for c in rhythmic]
    d = table['DNG100']
    x3 = None if math.isnan(d['i1_share']) or any(math.isnan(r['i1_share']) for r in rh) else \
        bool(d['i1_share'] > max(r['i1_share'] for r in rh))
    return dict(X1=verdict_ == 'NO_SIGNATURE', X2=bool(d['out_degree'] > max(r['out_degree'] for r in rh)), X3=x3)


def complete(table):
    bad = []
    for label, row in table.items():
        for m in METRICS:
            v = row.get(m)
            if v is None:
                bad.append((label, m, 'missing'))
            elif isinstance(v, float) and math.isnan(v) and m not in NAN_ALLOWED:
                bad.append((label, m, 'nan'))
            elif isinstance(v, float) and math.isinf(v) and m not in INF_ALLOWED:
                bad.append((label, m, 'inf'))
    return dict(passed=not bad and len(table) == 21, rows=len(table), problems=bad)


# ---- run ---------------------------------------------------------------------------------------

def name_of(data, i):
    inst = data.instances
    try:
        return str(inst[i]) if len(inst) == data.neuron_count else None
    except Exception:
        return None


def run(cache, progress=print):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    started = time.time()
    data = load_cache(cache)
    model = Model(data)
    ids = {k: dense(data, b) for k, b in CELLS.items()}
    core = {c: model.pos[ids[c]] for c in CORE}
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in model.net)).encode()).hexdigest()
    r3res = json.loads((ROOT/R3_RESULT).read_bytes())
    rhythmic = rhythmic_group(r3res)
    i1 = dict(r1_network_body_ids_sha256=body_sha, rhythmic=rhythmic,
              controls_in_network=all(c in model.pos for c in CONTROLS),
              passed=bool(body_sha == spec['integrity']['r1_network_body_ids_sha256']
                          and all(c in model.pos for c in CONTROLS)
                          and CONTROLS == spec['groups']['controls_dense_indices']
                          and rhythmic == EXPECTED_RHYTHMIC == spec['groups']['expected_rhythmic']))
    if not i1['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I1 failed',
                    integrity=dict(I1=i1), sources=src)
    stim = model.pos[ids['DNg100_L']]
    mids = r2.intermediates(model.W, stim, core)
    mine = {c: [str(model.net[k]) for k in v] for c, v in mids.items()}
    ref = json.loads((ROOT/R2_RESULT).read_bytes())['structure']['intermediates_by_cell']
    i2 = dict(passed=mine == ref, mine=mine, r2=ref)
    if not i2['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I2 failed',
                    integrity=dict(I1=i1, I2=i2), sources=src)
    vnc_size, m_vnc, _, _ = r2.cord_only_sizes(data, np.asarray(model.net))
    mn = list(model.mn_local.values())
    table, info = {}, {}
    for label, d in [('DNG100', ids['DNg100_L'])] + [(str(c), c) for c in CONTROLS]:
        j = model.pos[d]
        table[label] = metrics(model.W, j, core, mn)
        im = r2.intermediates(model.W, j, core)
        nt = data.neurotransmitters[int(np.asarray(data.neurotransmitter_ids)[d])]
        s_r1 = float(model.size[j]/model.size_ref)
        s_vnc = float(vnc_size[j]/m_vnc)
        info[label] = dict(dense=int(d), body_id=int(data.body_ids[d]), name=name_of(data, d), transmitter=nt,
                           group='DNG100' if label == 'DNG100' else ('RHYTHMIC' if d in rhythmic else 'NONRHYTHMIC'),
                           intermediates={c: [int(model.net[k]) for k in v] for c, v in im.items()},
                           s_R1=s_r1, s_VNC=s_vnc, rho=s_r1/s_vnc if s_vnc > 0 else math.inf)
    i4 = complete(table)
    if not i4['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I4 failed',
                    integrity=dict(I1=i1, I2=i2, I4=i4), table=table, sources=src)
    verdict_, per, seps = evaluate(table, rhythmic)
    rh_mids = {str(c): set().union(*map(set, info[str(c)]['intermediates'].values())) for c in rhythmic}
    dng_mids = set().union(*map(set, info['DNG100']['intermediates'].values()))
    overlap = dict(shared_by_all_rhythmic=sorted(set.intersection(*rh_mids.values())),
                   rhythmic_vs_dng100={k: sorted(v & dng_mids) for k, v in rh_mids.items()},
                   rhythmic_that_are_dng100_intermediates=sorted(c for c in rhythmic if c in dng_mids))
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict=verdict_, separating_metrics=seps,
                alpha=ALPHA, per_metric=per, expectations=expectations(verdict_, table, rhythmic),
                table=table, dns=info, overlap=overlap,
                integrity=dict(I1=i1, I2=dict(passed=True, checked=sum(map(len, ref.values()))), I4=i4),
                sources=src, runtime_s=round(time.time() - started, 1),
                interpretation_limits=spec['interpretation_limits'])


def headline(r):
    keys = ('verdict', 'separating_metrics', 'expectations', 'runtime_s', 'reason')
    out = {k: r[k] for k in keys if k in r}
    if 'per_metric' in r:
        out['p'] = {m: v['p'] for m, v in r['per_metric'].items()}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--load-check', action='store_true',
                        help='plumbing: load the network and print sizes and counts only (no metric values)')
    args = parser.parse_args(argv)
    if args.load_check:
        data = load_cache(args.cache)
        model = Model(data)
        print(json.dumps(dict(network=len(model.net), mns=len(model.mn_local),
                              instances_per_neuron=len(data.instances) == data.neuron_count,
                              controls_in_network=all(c in model.pos for c in CONTROLS), sources=sources()), indent=1))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(jsonable(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(jsonable(headline(result)), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
