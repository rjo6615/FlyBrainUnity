"""Rhythm Step R9: can relay 13964's two roles be separated by grading its output?

Preregistered in docs/evidence/dng100-graded-relay-v1/protocol.json. While DNg100_L is stimulated
(R1SIZE, drive 16,000), the outgoing weights of relay 13964 (R8's single ignition source) are
scaled by g in 0..1, either all of them (WHOLE) or all but its synapse onto E1 (SPARE_E1). R3's
replicate function is reused unchanged on a model copy carrying the scaled W. This is a declared
model probe confined to that copy, not a live-engine change. Neural only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from ..cache import load_cache
from . import dng100_balance_test as r7
from . import dng100_control_rhythm as r5
from . import dng100_engaged_rhythm as r3
from . import dng100_ignition_source as r8
from . import dng100_recruitment_map as r2
from .dng100_rate_model import CELLS, dense
from .dng100_size_audit import jsonable

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-graded-relay-v1/protocol.json'
PROTOCOL_SHA256 = 'de66566bb90188e3675f40fe7bae46ff168b3e9e2e7bac805d87247157862399'
SCHEMA = 'dng100-graded-relay-result-v1'
TEXT_SOURCES = {**r8.TEXT_SOURCES,
                'dng100_ignition_source_py_lf_sha256': 'malecns_backend/embodiment/dng100_ignition_source.py'}
BINARY_SOURCES = {**r8.BINARY_SOURCES,
                  'r8_result_json_sha256': 'docs/evidence/dng100-ignition-source-v1/run/result.json'}
R7_RESULT = r8.R7_RESULT
R8_RESULT = 'docs/evidence/dng100-ignition-source-v1/run/result.json'
ARM = 'R1SIZE'
DRIVE = 16000.
DNG100 = 'DNg100_L'          # body ID CELLS['DNg100_L'] (10045)
RELAY_BODY = 13964           # R8's single ignition source (dense 3694, resolved at run time)
WIRING = dict(weight_from_dng100=52., targets=68, weight_onto_E1=8., total_out=1086.)
LEVELS = tuple(round(i/10, 1) for i in range(11))
MODES = ('WHOLE', 'SPARE_E1')
SEEDS = range(6001, 6033)
I2_R7 = range(4001, 4005)
I2_R8 = range(5001, 5005)
CORE = r3.CORE
IGNITED = r2.RANGE_MAX       # 500


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

def relay_scaled(W, col, g, spare_rows=()):
    """Copy of CSR W[post, pre] with column col's entries multiplied by g, except rows in spare_rows.
    Structure is preserved, so g = 1 is bitwise identical to W."""
    out = W.tocsr().copy()
    rows = np.repeat(np.arange(out.shape[0]), np.diff(out.indptr))
    mask = (out.indices == col) & ~np.isin(rows, list(spare_rows))
    out.data = np.where(mask, out.data*g, out.data)
    return out


def mode_W(W, k, e1, mode, g):
    if mode == 'WHOLE':
        return r7.scaled(W, [k], g)
    if mode == 'SPARE_E1':
        return relay_scaled(W, k, g, (e1,))
    raise ValueError(mode)


def wiring(W, k, st, e1, core_local):
    col = np.asarray(W.tocsc()[:, k].todense()).ravel()
    targets = [int(j) for j in np.flatnonzero(col) if j != k]
    core_targets = sorted(c for c, j in core_local.items() if col[j] != 0)
    got = dict(weight_from_dng100=float(W[k, st]), targets=len(targets), weight_onto_E1=float(col[e1]),
               total_out=float(col[targets].sum()))
    return dict(**got, all_excitatory=bool((col[targets] > 0).all()), core_targets=core_targets,
                passed=bool(got == WIRING and (col[targets] > 0).all() and core_targets == ['E1']))


# ---- criteria ------------------------------------------------------------------------------------

def labels(s):
    e1 = s['E1_trace_score_median']
    return dict(ignited=bool(s['median_recruited'] >= IGNITED), engaged=bool(s['E1_active_fraction'] >= .5),
                rhythmic=bool(s['score'] >= .5 and e1 == e1 and e1 >= .5))


def mode_class(by_level):
    """by_level: {g: condition_summary}. First matching class and the levels that earn it."""
    lab = {g: labels(s) for g, s in by_level.items()}
    window = [g for g in sorted(lab) if not lab[g]['ignited'] and lab[g]['rhythmic']]
    if window:
        return 'RHYTHM_WINDOW', window
    sep = [g for g in sorted(lab) if not lab[g]['ignited'] and lab[g]['engaged']]
    if sep:
        return 'SEPARABLE_NO_RHYTHM', sep
    return 'NOT_SEPARABLE', []


def valid(modes):
    return bool(labels(modes['WHOLE'][1.])['ignited'] and labels(modes['SPARE_E1'][1.])['ignited']
                and not labels(modes['WHOLE'][0.])['ignited'])


def step_verdict(classes):
    for v in ('RHYTHM_WINDOW', 'SEPARABLE_NO_RHYTHM'):
        if v in classes.values():
            return v
    return 'NOT_SEPARABLE'


def transition(by_level):
    off = [g for g in sorted(by_level) if not labels(by_level[g])['ignited']]
    lv = sorted(by_level)
    return dict(highest_not_ignited=max(off) if off else None, not_ignited_levels=off,
                contiguous_from_zero=bool(off == lv[:len(off)]))


def expectations(classes):
    return dict(X1=classes['WHOLE'] == 'NOT_SEPARABLE', X2=classes['SPARE_E1'] == 'NOT_SEPARABLE',
                X3='RHYTHM_WINDOW' not in classes.values())


def key(x):
    return dict(score=x['score'], recruited=x['recruited'], core_active={c: x['core'][c]['active'] for c in CORE})


def i2_check(mine, r7_result, r8_result):
    refs = {'R7': {r['seed']: r for r in r7_result['conditions'][DNG100]['1.0']['runs']},
            'R8': {r['seed']: r for r in r8_result['conditions'][ARM]['SIL_3694']['runs']}}
    bad, checked = [], 0
    for src, seeds in (('R7', I2_R7), ('R8', I2_R8)):
        for s in seeds:
            want, got = key(refs[src][s]), mine[(src, s)]
            checked += 1
            if not (r3.same(got['score'], want['score']) and got['recruited'] == want['recruited']
                    and got['core_active'] == want['core_active']):
                bad.append(dict(source=src, seed=s, got=got, ref=want))
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
    size, ref = sizes[ARM]
    st = model.pos[dense(data, CELLS[DNG100])]
    relay_dense = dense(data, RELAY_BODY)
    k = model.pos[relay_dense]
    e1 = core_local['E1']
    watch = {**core_local, 'RELAY': k}   # RELAY adds 13964's own trace to each run; it gates nothing
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in model.net)).encode()).hexdigest()
    wire = wiring(model.W, k, st, e1, core_local)
    i1 = dict(r1_network_body_ids_sha256=body_sha, relay_dense=relay_dense, relay_local=k, wiring=wire,
              passed=bool(body_sha == spec['integrity']['r1_network_body_ids_sha256'] and wire['passed']
                          and relay_dense == 3694 and z_star == r2.R1B_Z_STAR and m_vnc == r2.R1B_M_VNC))
    if not i1['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I1 failed',
                    integrity=dict(I1=i1), sources=src)
    started = time.time()
    m1 = r7.with_W(model, mode_W(model.W, k, e1, 'WHOLE', 1.))
    mine = {}
    for s in I2_R7:
        mine[('R7', s)] = key(r3.replicate(m1, size, ref, s, DRIVE, st, (), core_local))
    for s in I2_R8:
        mine[('R8', s)] = key(r3.replicate(model, size, ref, s, DRIVE, st, (k,), core_local))
    i2 = i2_check(mine, json.loads((ROOT/R7_RESULT).read_bytes()), json.loads((ROOT/R8_RESULT).read_bytes()))
    progress(f'[{time.time()-started:6.0f}s] I2: {i2["passed"]} ({i2["checked"]} checked)', flush=True)
    if not i2['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I2 failed',
                    integrity=dict(I1=i1, I2=i2), sources=src)
    results, total = {}, 0
    for mode in MODES:
        results[mode] = {}
        for g in LEVELS:
            mg = r7.with_W(model, mode_W(model.W, k, e1, mode, g))
            runs = [r5.slim(r3.replicate(mg, size, ref, s, DRIVE, st, (), watch)) for s in SEEDS]
            total += len(runs)
            results[mode][g] = dict(summary=r3.condition_summary(runs), runs=runs)
            sm = results[mode][g]['summary']
            progress(f'[{time.time()-started:6.0f}s] {mode} g={g}: score {sm["score"]:.3f} '
                     f'recruited {sm["median_recruited"]}', flush=True)
    i4 = total == len(MODES)*len(LEVELS)*len(SEEDS)
    summ = {m: {g: v['summary'] for g, v in r.items()} for m, r in results.items()}
    ok = i4 and valid(summ)
    cls = {m: mode_class(summ[m]) for m in MODES}
    classes = {m: c[0] for m, c in cls.items()}
    v = ('INVALID' if not valid(summ) else step_verdict(classes)) if i4 else 'INCONCLUSIVE'

    def mean(m, g, f):
        return float(np.mean([f(r) for r in results[m][g]['runs']]))

    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict=v, valid=valid(summ) if i4 else None,
                modes={m: dict(cls=cls[m][0], levels=cls[m][1], transition=transition(summ[m])) for m in MODES},
                expectations=expectations(classes) if ok else None,
                curves={m: {str(g): dict(score=s['score'], frequency_hz=s['frequency_hz'],
                                         median_recruited=s['median_recruited'], **labels(s),
                                         **{f'{c}_trace_score_median': s[f'{c}_trace_score_median'] for c in CORE},
                                         **{f'{c}_active_fraction': s[f'{c}_active_fraction'] for c in CORE},
                                         **{f'{c}_mean_hz': mean(m, g, lambda r, c=c: r['core'][c]['mean_hz'])
                                            for c in (*CORE, 'RELAY')},
                                         DNg100_L_mean_hz=mean(m, g, lambda r: r['stim_mean_hz']))
                            for g, s in by.items()} for m, by in summ.items()},
                conditions={m: {str(g): v for g, v in r.items()} for m, r in results.items()},
                relay=dict(body_id=RELAY_BODY, dense=relay_dense, wiring=wire),
                integrity=dict(I1=i1, I2=i2, I4=dict(passed=i4, simulations=total)),
                sources=src, runtime_s=round(time.time() - started, 1),
                interpretation_limits=spec['interpretation_limits'])


def headline(r):
    out = {k: r.get(k) for k in ('verdict', 'valid', 'modes', 'expectations', 'reason', 'runtime_s')}
    if 'curves' in r:
        out['curves'] = {m: {g: (round(c['score'], 3) if c['score'] == c['score'] else None, c['median_recruited'],
                                 c['E1_active_fraction']) for g, c in by.items()} for m, by in r['curves'].items()}
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
