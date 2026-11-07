"""Rhythm Step R6: which inhibitory cells (other than I1) does the E1-E2 rhythm need?

Preregistered in docs/evidence/dng100-inhibition-search-v1/protocol.json. Stage A lists short-loop
inhibitory partners of E1/E2 by a declared rule on R1's signed matrix; Stage B silences them
(singly and as a group) while DNg75_R or DNa02_L is stimulated, in R1SIZE at drive 16,000.
R3's replicate function and R5's sham rule are reused unchanged. Neural only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from ..cache import load_cache
from . import dng100_control_rhythm as r5
from . import dng100_engaged_rhythm as r3
from . import dng100_recruitment_map as r2
from .dng100_rate_model import CELLS, NT_SIGN, dense
from .dng100_size_audit import jsonable

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-inhibition-search-v1/protocol.json'
PROTOCOL_SHA256 = '2d82fcd19617a902d98908f9103eb237005ef7ece879baede54b1e5b77daf2a6'
SCHEMA = 'dng100-inhibition-search-result-v1'
TEXT_SOURCES = {**r5.TEXT_SOURCES,
                'dng100_control_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_control_rhythm.py'}
BINARY_SOURCES = {**r5.BINARY_SOURCES,
                  'r5_result_json_sha256': 'docs/evidence/dng100-control-rhythm-v1/run/result.json'}
R5_RESULT = 'docs/evidence/dng100-control-rhythm-v1/run/result.json'
ARM = 'R1SIZE'
DRIVE = 16000.
TARGETS = {'DNg75_R': 129181, 'DNa02_L': 130496}
SEEDS = range(3001, 3033)
I2_SEEDS = range(2001, 2005)
CORE = r3.CORE
CAP = 40
T2_THRESHOLD = 5
EXPECTED_TRANSMITTERS = {'E1': 'acetylcholine', 'E2': 'acetylcholine', 'I1': 'glutamate'}
CLASSES = ('NEEDED_OSCILLATION', 'NEEDED_CORE_OFF', 'NEEDED_OTHER', 'NOT_NEEDED')


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


# ---- Stage A: candidates -----------------------------------------------------------------------

def candidates(W, sign, E, i1, excluded, order_key, cap=CAP, t2_threshold=T2_THRESHOLD):
    """Short-loop inhibitory partners of the excitatory cells E (local indices).

    W[post, pre] signed; sign per local cell; excluded local indices (DN/AN/MN/core/I1);
    order_key[local] breaks ties (dense index). Returns ranked [dict(local, tier, strength, ...)]."""
    W = W.tocsr()
    n = W.shape[0]
    ex = set(int(x) for x in excluded) | {int(i1)} | set(int(e) for e in E)
    inhib = [k for k in range(n) if sign[k] < 0 and k not in ex]
    from_E = np.zeros(n)   # max_e W[k, e] (E excites k)
    for e in E:
        col = np.asarray(W[:, e].todense()).ravel()
        from_E = np.maximum(from_E, np.where(col > 0, col, 0.))
    to_E = np.zeros(n)     # max_e' |W[e', k]| for W < 0 (k inhibits E)
    for e in E:
        row = np.asarray(W[e].todense()).ravel()
        to_E = np.maximum(to_E, np.where(row < 0, -row, 0.))
    t1 = [dict(local=k, tier='T1', strength=float(min(from_E[k], to_E[k])), from_E=float(from_E[k]),
               to_E=float(to_E[k])) for k in inhib if from_E[k] > 0 and to_E[k] > 0]
    rank = lambda c: (-c['strength'], order_key[c['local']])
    t1.sort(key=rank)
    out = t1[:cap]
    t2 = []
    if len(t1) < t2_threshold:
        relay = from_E > 0                     # x excited by E
        in1 = {c['local'] for c in t1}
        for k in inhib:
            if k in in1 or to_E[k] <= 0:
                continue
            row = np.asarray(W[k].todense()).ravel()
            if np.any((row > 0) & relay):      # some x with W[x, e] > 0 and W[k, x] > 0
                t2.append(dict(local=k, tier='T2', strength=float(to_E[k]), from_E=0., to_E=float(to_E[k])))
        t2.sort(key=rank)
        out = out + t2[:cap - len(out)]
    return out, dict(t1=len(t1), t2=len(t2), t2_used=len(t1) < t2_threshold)


# ---- classes and verdict ------------------------------------------------------------------------

def classify(summary):
    s = summary['score']
    if s >= .5:
        return 'NOT_NEEDED'
    if not (summary['E1_active_fraction'] >= .5):
        return 'NEEDED_CORE_OFF'
    e1 = summary['E1_trace_score_median']
    if not math.isnan(e1) and e1 < .5:
        return 'NEEDED_OSCILLATION'
    return 'NEEDED_OTHER'


def valid(stim, sham):
    return bool(stim['score'] >= .5 and sham['score'] >= .5)


def verdict(per_target):
    """per_target: {target: dict(valid, classes={label: class}, group=class)}."""
    vt = {t: v for t, v in per_target.items() if v['valid']}
    if not vt:
        return 'INCONCLUSIVE', []
    labels = sorted(set().union(*[set(v['classes']) for v in vt.values()]))
    hits = {lab: [t for t, v in vt.items() if v['classes'].get(lab) == 'NEEDED_OSCILLATION'] for lab in labels}
    shared = [lab for lab, ts in hits.items() if len(vt) == len(per_target) and len(ts) == len(per_target)]
    if shared:
        return 'SHARED_INHIBITORY_PARTNER', shared
    single = [lab for lab, ts in hits.items() if ts]
    if single:
        return 'TARGET_SPECIFIC_PARTNER', single
    if any(v['group'] == 'NEEDED_OSCILLATION' for v in vt.values()):
        return 'REDUNDANT_INHIBITION', []
    if any(v['group'] == 'NEEDED_CORE_OFF' for v in vt.values()):
        return 'GROUP_SILENCES_CORE', []
    return 'NO_PARTNER_IN_SET', []


def expectations(counts, v, per_target):
    return dict(X1=bool(counts['t1'] >= T2_THRESHOLD), X2=v == 'SHARED_INHIBITORY_PARTNER',
                X3=all(p['group'] == 'NEEDED_OSCILLATION' for p in per_target.values()))


def i2_check(mine, r5_result):
    bad, checked = [], 0
    for t in TARGETS:
        runs = {r['seed']: r for r in r5_result['arms'][ARM]['targets'][t]['conditions']['STIM']['runs']}
        for s in I2_SEEDS:
            ref = runs[s]
            want = dict(score=ref['score'], recruited=ref['recruited'],
                        core_active={c: ref['core'][c]['active'] for c in CORE})
            got = mine[(t, s)]
            checked += 1
            if not (r3.same(got['score'], want['score']) and got['recruited'] == want['recruited']
                    and got['core_active'] == want['core_active']):
                bad.append(dict(target=t, seed=s, got=got, r5=want))
    return dict(passed=not bad and checked == len(TARGETS)*len(I2_SEEDS), checked=checked, mismatches=bad)


# ---- run --------------------------------------------------------------------------------------------

def network_signs(data, net):
    nt = np.asarray(data.neurotransmitter_ids)
    return np.array([NT_SIGN.get(data.neurotransmitters[nt[i]], 0.) for i in net])


def run(cache, progress=print):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    data = load_cache(cache)
    model, ctx, sizes, z_star, m_vnc = r3.setup(data)
    core_local = ctx['core']
    size, ref = sizes[ARM]
    ids = {k: dense(data, b) for k, b in CELLS.items()}
    nt = np.asarray(data.neurotransmitter_ids)
    tx = {c: data.neurotransmitters[nt[ids[c]]] for c in CORE}
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in model.net)).encode()).hexdigest()
    _, dnan = r5.pool_and_classes(data, model)
    mn = set(model.mn_local.values())
    excluded = set(dnan.tolist()) | mn | set(core_local.values())
    sign = network_signs(data, model.net)
    cands, counts = candidates(model.W, sign, [core_local['E1'], core_local['E2']], core_local['I1'], excluded,
                               np.asarray(model.net))
    cl = [c['local'] for c in cands]
    i1 = dict(r1_network_body_ids_sha256=body_sha, transmitters=tx, candidates=len(cl), counts=counts,
              passed=bool(body_sha == spec['integrity']['r1_network_body_ids_sha256'] and tx == EXPECTED_TRANSMITTERS
                          and z_star == r2.R1B_Z_STAR and m_vnc == r2.R1B_M_VNC
                          and len(cl) <= CAP and not set(cl) & (excluded | {core_local['I1']})))
    if not i1['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I1 failed',
                    integrity=dict(I1=i1), sources=src)
    started = time.time()
    r5res = json.loads((ROOT/R5_RESULT).read_bytes())
    mine = {}
    for t, d in TARGETS.items():
        for s in I2_SEEDS:
            x = r3.replicate(model, size, ref, s, DRIVE, model.pos[d], (), core_local)
            mine[(t, s)] = dict(score=x['score'], recruited=x['recruited'],
                                core_active={c: x['core'][c]['active'] for c in CORE})
    i2 = i2_check(mine, r5res)
    progress(f'[{time.time()-started:6.0f}s] I2 R5 reproduction: {i2["passed"]} ({i2["checked"]} checked); '
             f'{len(cl)} candidates (T1 {counts["t1"]}, T2 used {counts["t2_used"]})', flush=True)
    if not i2['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I2 failed',
                    integrity=dict(I1=i1, I2=i2), sources=src)
    info = []
    for c in cands:
        dd = int(model.net[c['local']])
        info.append(dict(c, dense=dd, label=f'SIL_{dd}', body_id=int(data.body_ids[dd]),
                         name=r5.name_of(data, dd), transmitter=data.neurotransmitters[nt[dd]]))
    per_target, conds_out, total = {}, {}, 0
    for t, d in TARGETS.items():
        st = model.pos[d]
        mids = r2.intermediates(model.W, st, core_local)
        mid_set = set().union(*map(set, mids.values()))
        sham_c = r5.sham_candidates(len(model.net), excluded | mid_set | set(cl) | {core_local['I1']})
        plan = [('STIM', lambda s: ()), ('SIL_SHAM', lambda s: (r5.sham_cell(s, sham_c),)),
                ('SIL_GROUP', lambda s: tuple(cl))]
        plan += [(c['label'], (lambda j: (lambda s: (j,)))(c['local'])) for c in info]
        out = {}
        for label, sil in plan:
            runs = []
            for s in SEEDS:
                silenced = sil(s)
                x = r3.replicate(model, size, ref, s, DRIVE, st, silenced, core_local)
                if label == 'SIL_SHAM':
                    x['silenced_dense'] = [int(model.net[j]) for j in silenced]
                runs.append(r5.slim(x))
            total += len(runs)
            out[label] = dict(summary=r3.condition_summary(runs), runs=runs)
        summ = {k: v['summary'] for k, v in out.items()}
        ok = valid(summ['STIM'], summ['SIL_SHAM'])
        per_target[t] = dict(valid=ok, stim=summ['STIM'], sham=summ['SIL_SHAM'],
                             group=classify(summ['SIL_GROUP']),
                             classes={c['label']: classify(summ[c['label']]) for c in info},
                             is_intermediate={c['label']: c['local'] in mid_set for c in info})
        conds_out[t] = out
        progress(f'[{time.time()-started:6.0f}s] {t} done (valid {ok})', flush=True)
    expected_total = len(TARGETS)*(len(cl) + 3)*len(SEEDS)
    i4 = total == expected_total
    v, partners = verdict(per_target) if i4 else ('INCONCLUSIVE', [])
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict=v, partners=partners,
                expectations=expectations(counts, v, per_target) if i4 else None,
                candidates=info, candidate_counts=counts, targets=per_target, conditions=conds_out,
                integrity=dict(I1=i1, I2=i2, I4=dict(passed=i4, simulations=total, expected=expected_total)),
                sources=src, runtime_s=round(time.time() - started, 1),
                interpretation_limits=spec['interpretation_limits'])


def headline(r):
    out = {k: r.get(k) for k in ('verdict', 'partners', 'expectations', 'candidate_counts', 'reason', 'runtime_s')}
    if 'targets' in r:
        out['targets'] = {t: dict(valid=v['valid'], stim=v['stim']['score'], sham=v['sham']['score'], group=v['group'],
                                  needed={k: c for k, c in v['classes'].items() if c != 'NOT_NEEDED'})
                          for t, v in r['targets'].items()}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--time-one', action='store_true',
                        help='plumbing: one R1SIZE DNg75_R simulation, seed 0 (not a protocol seed); wall time only; '
                             'no candidate is computed')
    args = parser.parse_args(argv)
    if args.time_one:
        data = load_cache(args.cache)
        model, ctx, sizes, _, _ = r3.setup(data)
        t = time.time()
        r3.replicate(model, *sizes[ARM], 0, DRIVE, model.pos[TARGETS['DNg75_R']], (), ctx['core'])
        print(json.dumps(dict(one_simulation_s=round(time.time() - t, 2), sources=sources()), indent=1))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(jsonable(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(jsonable(headline(result)), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
