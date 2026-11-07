"""Rhythm Step R7: does the E1-E2 rhythm sit on an excitation/inhibition balance?

Preregistered in docs/evidence/dng100-balance-test-v1/protocol.json. The outgoing weights of the
inhibitory set S (I1 plus R6's 31 T1 candidates) are scaled by g while DNg75_R, DNa02_L or DNg100_L
is stimulated (R1SIZE, drive 16,000). R3's replicate function is reused unchanged on a model copy
whose W is the scaled matrix. This is a declared model probe, not a live-engine change. Neural only.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from ..cache import load_cache
from . import dng100_engaged_rhythm as r3
from . import dng100_inhibition_search as r6
from . import dng100_control_rhythm as r5
from . import dng100_recruitment_map as r2
from .dng100_rate_model import CELLS, dense
from .dng100_size_audit import jsonable

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-balance-test-v1/protocol.json'
PROTOCOL_SHA256 = 'f7d6ec976a64b37df72258cedf4ec1357324eb6464fa1649aae757b3a78e899d'
SCHEMA = 'dng100-balance-test-result-v1'
TEXT_SOURCES = {**r6.TEXT_SOURCES,
                'dng100_inhibition_search_py_lf_sha256': 'malecns_backend/embodiment/dng100_inhibition_search.py'}
BINARY_SOURCES = {**r6.BINARY_SOURCES,
                  'r6_result_json_sha256': 'docs/evidence/dng100-inhibition-search-v1/run/result.json'}
R6_RESULT = 'docs/evidence/dng100-inhibition-search-v1/run/result.json'
ARM = 'R1SIZE'
DRIVE = 16000.
LEVELS = (0., .25, .5, .75, 1., 1.5, 2., 3.)
REMOVAL_SCAN = (.75, .5, .25, 0.)
BOOST = (1.5, 2., 3.)
DRIVERS = {'DNg75_R': 129181, 'DNa02_L': 130496}
DNG100 = 'DNg100_L'   # body ID CELLS['DNg100_L'] (10045); dense index resolved at run time
SEEDS = range(4001, 4033)
I2_SEEDS = range(3001, 3005)
CORE = r3.CORE
IGNITED = r2.RANGE_MAX   # 500


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


# ---- intervention ----------------------------------------------------------------------------------

def scaled(W, cols, g):
    """Copy of CSR W[post, pre] with every entry in the columns cols (presynaptic S) multiplied by g.
    Structure is preserved, so g = 1 is bitwise identical to W."""
    out = W.tocsr().copy()
    factor = np.ones(out.shape[1])
    factor[list(cols)] = g
    out.data = out.data*factor[out.indices]
    return out


def with_W(model, W):
    m = copy.copy(model)
    m.W = W
    return m


def stimulated(ids):
    """Dense indices of the stimulated DNs: the two drivers (dense) and DNg100_L (from its body ID)."""
    return {**DRIVERS, DNG100: ids[DNG100]}


# ---- criteria ------------------------------------------------------------------------------------

def ignited(summary):
    return bool(summary['median_recruited'] >= IGNITED)


def removal_class(by_level):
    """by_level: {g: condition_summary}. Scan 0.75 -> 0; first level whose score is not >= 0.5."""
    for g in REMOVAL_SCAN:
        s = by_level[g]
        if not (s['score'] >= .5):
            e1 = s['E1_trace_score_median']
            by_ign = ignited(s) and (math.isnan(e1) or e1 < .5)
            return ('LOST_BY_IGNITION' if by_ign else 'LOST_OTHER'), g
    return 'NOT_LOST', None


def boost_holds(by_level):
    hits = [g for g in BOOST if by_level[g]['score'] >= .5 and not ignited(by_level[g])]
    return bool(hits), hits


def verdict(drivers, dng100):
    """drivers: {name: {g: summary}}; dng100: {g: summary}."""
    if any(not (d[1.]['score'] >= .5) for d in drivers.values()):
        return 'INVALID', {}
    cls = {k: removal_class(v) for k, v in drivers.items()}
    a = all(c[0] == 'LOST_BY_IGNITION' for c in cls.values())
    b, hits = boost_holds(dng100)
    v = 'BALANCE_SUPPORTED' if a and b else 'REMOVAL_ONLY' if a else 'BOOST_ONLY' if b else 'NOT_SUPPORTED'
    return v, dict(removal={k: dict(cls=c[0], loss_level=c[1]) for k, c in cls.items()}, a_holds=a,
                   b_holds=b, boost_levels_with_rhythm=hits)


def expectations(v, details):
    if not details:
        return None
    rem = details['removal']
    return dict(X1=rem['DNg75_R']['cls'] == 'LOST_BY_IGNITION', X2=rem['DNa02_L']['cls'] == 'LOST_BY_IGNITION',
                X3=not details['b_holds'])


def i2_check(mine, r6_result):
    bad, checked = [], 0
    for t in DRIVERS:
        runs = {r['seed']: r for r in r6_result['conditions'][t]['STIM']['runs']}
        for s in I2_SEEDS:
            ref = runs[s]
            want = dict(score=ref['score'], recruited=ref['recruited'],
                        core_active={c: ref['core'][c]['active'] for c in CORE})
            got = mine[(t, s)]
            checked += 1
            if not (r3.same(got['score'], want['score']) and got['recruited'] == want['recruited']
                    and got['core_active'] == want['core_active']):
                bad.append(dict(target=t, seed=s, got=got, r6=want))
    return dict(passed=not bad and checked == len(DRIVERS)*len(I2_SEEDS), checked=checked, mismatches=bad)


# ---- run --------------------------------------------------------------------------------------------

def run(cache, progress=print):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    data = load_cache(cache)
    model, ctx, sizes, z_star, m_vnc = r3.setup(data)
    core_local = ctx['core']
    size, ref = sizes[ARM]
    r6res = json.loads((ROOT/R6_RESULT).read_bytes())
    ids = {k: dense(data, b) for k, b in CELLS.items()}
    s_dense = sorted([int(c['dense']) for c in r6res['candidates']] + [ids['I1']])
    sign = r6.network_signs(data, model.net)
    s_local = [model.pos[d] for d in s_dense]
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in model.net)).encode()).hexdigest()
    i1 = dict(r1_network_body_ids_sha256=body_sha, s_size=len(s_dense), s_dense=s_dense,
              passed=bool(body_sha == spec['integrity']['r1_network_body_ids_sha256'] and len(s_dense) == 32
                          and len(set(s_dense)) == 32 and all(sign[j] < 0 for j in s_local)
                          and z_star == r2.R1B_Z_STAR and m_vnc == r2.R1B_M_VNC
                          and all(d in model.pos for d in stimulated(ids).values())))
    if not i1['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I1 failed',
                    integrity=dict(I1=i1), sources=src)
    started = time.time()
    m1 = with_W(model, scaled(model.W, s_local, 1.))
    mine = {}
    for t, d in DRIVERS.items():
        for s in I2_SEEDS:
            x = r3.replicate(m1, size, ref, s, DRIVE, model.pos[d], (), core_local)
            mine[(t, s)] = dict(score=x['score'], recruited=x['recruited'],
                                core_active={c: x['core'][c]['active'] for c in CORE})
    i2 = i2_check(mine, r6res)
    progress(f'[{time.time()-started:6.0f}s] I2 R6 reproduction via g = 1: {i2["passed"]} ({i2["checked"]} checked)',
             flush=True)
    if not i2['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I2 failed',
                    integrity=dict(I1=i1, I2=i2), sources=src)
    results, total = {}, 0
    for name, d in stimulated(ids).items():
        results[name] = {}
        for g in LEVELS:
            mg = with_W(model, scaled(model.W, s_local, g))
            runs = [r5.slim(r3.replicate(mg, size, ref, s, DRIVE, model.pos[d], (), core_local)) for s in SEEDS]
            total += len(runs)
            results[name][g] = dict(summary=r3.condition_summary(runs), runs=runs)
            sm = results[name][g]['summary']
            progress(f'[{time.time()-started:6.0f}s] {name} g={g}: score {sm["score"]:.3f} '
                     f'recruited {sm["median_recruited"]}', flush=True)
    i4 = total == 3*len(LEVELS)*len(SEEDS)
    summ = {n: {g: v['summary'] for g, v in r.items()} for n, r in results.items()}
    v, details = verdict({k: summ[k] for k in DRIVERS}, summ[DNG100]) if i4 else ('INCONCLUSIVE', {})
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict=v, details=details,
                expectations=expectations(v, details) if i4 else None,
                curves={n: {str(g): dict(score=s['score'], frequency_hz=s['frequency_hz'],
                                         median_recruited=s['median_recruited'], ignited=ignited(s),
                                         **{f'{c}_trace_score_median': s[f'{c}_trace_score_median'] for c in CORE},
                                         **{f'{c}_active_fraction': s[f'{c}_active_fraction'] for c in CORE},
                                         **{f'{c}_mean_hz': float(np.mean([r['core'][c]['mean_hz']
                                                                           for r in results[n][g]['runs']]))
                                            for c in CORE})
                            for g, s in by.items()} for n, by in summ.items()},
                conditions={n: {str(g): v for g, v in r.items()} for n, r in results.items()},
                inhibitory_set=dict(dense=s_dense, body_ids=[int(data.body_ids[d]) for d in s_dense]),
                integrity=dict(I1=i1, I2=i2, I4=dict(passed=i4, simulations=total)),
                sources=src, runtime_s=round(time.time() - started, 1),
                interpretation_limits=spec['interpretation_limits'])


def headline(r):
    out = {k: r.get(k) for k in ('verdict', 'details', 'expectations', 'reason', 'runtime_s')}
    if 'curves' in r:
        out['curves'] = {n: {g: (round(c['score'], 3) if c['score'] == c['score'] else None, c['median_recruited'])
                             for g, c in by.items()} for n, by in r['curves'].items()}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--time-one', action='store_true',
                        help='plumbing: one unscaled R1SIZE DNg100_L simulation, seed 0 (not a protocol seed); '
                             'wall time only')
    args = parser.parse_args(argv)
    if args.time_one:
        data = load_cache(args.cache)
        model, ctx, sizes, _, _ = r3.setup(data)
        t = time.time()
        r3.replicate(model, *sizes[ARM], 0, DRIVE, model.pos[dense(data, CELLS[DNG100])], (), ctx['core'])
        print(json.dumps(dict(one_simulation_s=round(time.time() - t, 2), sources=sources()), indent=1))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(jsonable(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(jsonable(headline(result)), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
