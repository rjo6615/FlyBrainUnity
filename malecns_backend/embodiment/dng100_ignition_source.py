"""Rhythm Step R8: which of DNg100_L's direct partners does the network ignition need?

Preregistered in docs/evidence/dng100-ignition-source-v1/protocol.json. Each direct postsynaptic
partner of DNg100_L in R1's network is silenced (singly, and all together) while DNg100_L is
stimulated, in R1SIZE (16,000) and VNCSIZE (2,000). R3's replicate function and R5's sham rule are
reused unchanged. No weight changes. Neural only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from ..cache import load_cache
from . import dng100_balance_test as r7
from . import dng100_control_rhythm as r5
from . import dng100_engaged_rhythm as r3
from . import dng100_recruitment_map as r2
from .dng100_rate_model import CELLS, dense
from .dng100_size_audit import jsonable

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-ignition-source-v1/protocol.json'
PROTOCOL_SHA256 = '528d96a27dedab3513ca2ddb1dbbfe5db6d6280d235c13b9793e2c7cb9adb72e'
SCHEMA = 'dng100-ignition-source-result-v1'
TEXT_SOURCES = {**r7.TEXT_SOURCES,
                'dng100_balance_test_py_lf_sha256': 'malecns_backend/embodiment/dng100_balance_test.py'}
BINARY_SOURCES = {**r7.BINARY_SOURCES,
                  'r7_result_json_sha256': 'docs/evidence/dng100-balance-test-v1/run/result.json'}
R3_RESULT = 'docs/evidence/dng100-engaged-rhythm-v1/run/result.json'
R7_RESULT = 'docs/evidence/dng100-balance-test-v1/run/result.json'
DRIVES = {'R1SIZE': 16000., 'VNCSIZE': 2000.}
ARMS = ('R1SIZE', 'VNCSIZE')
PRIMARY = 'R1SIZE'
SEEDS = range(5001, 5017)
I2 = {'R1SIZE': range(4001, 4005), 'VNCSIZE': range(1001, 1005)}
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


# ---- partners and criteria --------------------------------------------------------------------

def partners(W, s):
    """Local indices j != s with W[j, s] != 0, ascending (dense order, since R1's net is sorted)."""
    col = np.asarray(W.tocsc()[:, s].todense()).ravel()
    return [int(j) for j in np.flatnonzero(col) if j != s]


def ignited(summary):
    return bool(summary['median_recruited'] >= IGNITED)


def arm_verdict(stim, sham, group, singles):
    """singles: {label: summary}. Returns verdict and the preventing labels."""
    if not (ignited(stim) and ignited(sham)):
        return 'INVALID', []
    prevent = [k for k, s in singles.items() if not ignited(s)]
    if prevent:
        return 'SINGLE_IGNITION_SOURCE', prevent
    if not ignited(group):
        return 'DISTRIBUTED_IGNITION', []
    return 'IGNITION_NOT_VIA_PARTNERS', []


def unmasked(prevent, singles):
    """Secondary: among ignition-preventing silencings, score >= 0.5 and median E1 trace >= 0.5."""
    if not prevent:
        return 'NOT_APPLICABLE', []
    hits = [k for k in prevent if singles[k]['score'] >= .5
            and not math.isnan(singles[k]['E1_trace_score_median']) and singles[k]['E1_trace_score_median'] >= .5]
    return ('RHYTHM_UNMASKED' if hits else 'NO_RHYTHM_UNMASKED'), hits


def expectations(arms):
    return dict(X1=arms['R1SIZE']['verdict'] == 'DISTRIBUTED_IGNITION',
                X2=arms['VNCSIZE']['verdict'] == 'DISTRIBUTED_IGNITION',
                X3=arms['R1SIZE']['secondary'] in ('NO_RHYTHM_UNMASKED', 'NOT_APPLICABLE'))


def i2_check(mine, r7_result, r3_result):
    refs = {'R1SIZE': {r['seed']: r for r in r7_result['conditions']['DNg100_L']['1.0']['runs']},
            'VNCSIZE': {r['seed']: r for r in r3_result['arms']['VNCSIZE']['conditions']['DNG100']['runs']}}
    bad, checked = [], 0
    for arm, seeds in I2.items():
        for s in seeds:
            ref = refs[arm][s]
            want = dict(score=ref['score'], recruited=ref['recruited'],
                        core_active={c: ref['core'][c]['active'] for c in CORE})
            got = mine[(arm, s)]
            checked += 1
            if not (r3.same(got['score'], want['score']) and got['recruited'] == want['recruited']
                    and got['core_active'] == want['core_active']):
                bad.append(dict(arm=arm, seed=s, got=got, ref=want))
    return dict(passed=not bad and checked == 8, checked=checked, mismatches=bad)


# ---- run --------------------------------------------------------------------------------------------

def run(cache, progress=print):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    data = load_cache(cache)
    model, ctx, sizes, z_star, m_vnc = r3.setup(data)
    core_local = ctx['core']
    ids = {k: dense(data, b) for k, b in CELLS.items()}
    st = model.pos[ids['DNg100_L']]
    P = partners(model.W, st)
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in model.net)).encode()).hexdigest()
    i1 = dict(r1_network_body_ids_sha256=body_sha, dng100_dense=ids['DNg100_L'], partners=len(P),
              passed=bool(body_sha == spec['integrity']['r1_network_body_ids_sha256'] and len(P) > 0
                          and z_star == r2.R1B_Z_STAR and m_vnc == r2.R1B_M_VNC))
    if not i1['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I1 failed',
                    integrity=dict(I1=i1), sources=src)
    started = time.time()
    mine = {}
    for arm, seeds in I2.items():
        size, ref = sizes[arm]
        for s in seeds:
            x = r3.replicate(model, size, ref, s, DRIVES[arm], st, (), core_local)
            mine[(arm, s)] = dict(score=x['score'], recruited=x['recruited'],
                                  core_active={c: x['core'][c]['active'] for c in CORE})
    i2 = i2_check(mine, json.loads((ROOT/R7_RESULT).read_bytes()), json.loads((ROOT/R3_RESULT).read_bytes()))
    progress(f'[{time.time()-started:6.0f}s] I2: {i2["passed"]} ({i2["checked"]} checked); {len(P)} partners',
             flush=True)
    if not i2['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I2 failed',
                    integrity=dict(I1=i1, I2=i2), sources=src)
    _, dnan = r5.pool_and_classes(data, model)
    mids = r2.intermediates(model.W, st, core_local)
    mid_set = set().union(*map(set, mids.values()))
    excluded = set(dnan.tolist()) | set(model.mn_local.values()) | set(core_local.values()) | mid_set | set(P)
    sham_c = r5.sham_candidates(len(model.net), excluded)
    nt = np.asarray(data.neurotransmitter_ids)
    W = model.W.tocsc()
    info = []
    for j in P:
        d = int(model.net[j])
        info.append(dict(local=j, dense=d, label=f'SIL_{d}', body_id=int(data.body_ids[d]), name=r5.name_of(data, d),
                         transmitter=data.neurotransmitters[nt[d]], weight_from_dng100=float(model.W[j, st]),
                         out_degree=int(W[:, j].count_nonzero() - (1 if model.W[j, j] != 0 else 0)),
                         two_hop_intermediate=j in mid_set))
    plan = [('STIM', lambda s: ()), ('SIL_SHAM', lambda s: (r5.sham_cell(s, sham_c),)), ('SIL_GROUP', lambda s: tuple(P))]
    plan += [(c['label'], (lambda j: (lambda s: (j,)))(c['local'])) for c in info]
    arms, conds, total = {}, {}, 0
    for arm in ARMS:
        size, ref = sizes[arm]
        out = {}
        for label, sil in plan:
            runs = []
            for s in SEEDS:
                silenced = sil(s)
                x = r3.replicate(model, size, ref, s, DRIVES[arm], st, silenced, core_local)
                if label == 'SIL_SHAM':
                    x['silenced_dense'] = [int(model.net[j]) for j in silenced]
                runs.append(r5.slim(x))
            total += len(runs)
            out[label] = dict(summary=r3.condition_summary(runs), runs=runs)
        summ = {k: v['summary'] for k, v in out.items()}
        singles = {c['label']: summ[c['label']] for c in info}
        v, prevent = arm_verdict(summ['STIM'], summ['SIL_SHAM'], summ['SIL_GROUP'], singles)
        sec, hits = unmasked(prevent, singles)
        arms[arm] = dict(verdict=v, drive=DRIVES[arm], preventing=prevent, secondary=sec, unmasked=hits,
                         stim=summ['STIM'], sham=summ['SIL_SHAM'], group=summ['SIL_GROUP'],
                         singles={k: dict(median_recruited=s['median_recruited'], ignited=ignited(s), score=s['score'],
                                          frequency_hz=s['frequency_hz'],
                                          E1_trace_score_median=s['E1_trace_score_median'],
                                          E1_active_fraction=s['E1_active_fraction'])
                                  for k, s in singles.items()})
        conds[arm] = out
        progress(f'[{time.time()-started:6.0f}s] {arm} done: {v} ({len(prevent)} preventing); {sec}', flush=True)
    i4 = total == len(ARMS)*(len(P) + 3)*len(SEEDS)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256,
                verdict=arms[PRIMARY]['verdict'] if i4 else 'INCONCLUSIVE', primary_arm=PRIMARY,
                secondary=arms[PRIMARY]['secondary'] if i4 else None,
                vncsize=dict(verdict=arms['VNCSIZE']['verdict'], secondary=arms['VNCSIZE']['secondary']),
                expectations=expectations(arms) if i4 else None, partners=info, arms=arms, conditions=conds,
                integrity=dict(I1=i1, I2=i2, I4=dict(passed=i4, simulations=total)),
                sources=src, runtime_s=round(time.time() - started, 1),
                interpretation_limits=spec['interpretation_limits'])


def headline(r):
    out = {k: r.get(k) for k in ('verdict', 'secondary', 'vncsize', 'expectations', 'reason', 'runtime_s')}
    for arm, a in r.get('arms', {}).items():
        out[arm] = dict(stim=a['stim']['median_recruited'], sham=a['sham']['median_recruited'],
                        group=a['group']['median_recruited'], preventing=a['preventing'], unmasked=a['unmasked'])
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--time-one', action='store_true',
                        help='plumbing: one R1SIZE DNg100_L simulation, seed 0 (not a protocol seed); wall time only; '
                             'no partner is listed')
    args = parser.parse_args(argv)
    if args.time_one:
        data = load_cache(args.cache)
        model, ctx, sizes, _, _ = r3.setup(data)
        t = time.time()
        r3.replicate(model, *sizes['R1SIZE'], 0, DRIVES['R1SIZE'], model.pos[dense(data, CELLS['DNg100_L'])], (),
                     ctx['core'])
        print(json.dumps(dict(one_simulation_s=round(time.time() - t, 2), sources=sources()), indent=1))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(jsonable(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(jsonable(headline(result)), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
