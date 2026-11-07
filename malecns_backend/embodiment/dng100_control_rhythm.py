"""Rhythm Step R5: is R3's control-DN core oscillation real, and does it need E1, E2 and I1?

Preregistered in docs/evidence/dng100-control-rhythm-v1/protocol.json. R3's replicate function,
drives, sizes and summaries are reused unchanged (dng100_engaged_rhythm); R1's model and control
pool rule (dng100_rate_model); R2's intermediates. Fixed drives, no adjustment. Neural only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from ..cache import load_cache
from . import dng100_engaged_rhythm as r3
from . import dng100_recruitment_map as r2
from .dng100_rate_model import CELLS, dense
from .dng100_size_audit import jsonable

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-control-rhythm-v1/protocol.json'
PROTOCOL_SHA256 = '0fabdb48d67f67c53f49ca7aaa9a45dd6733259d4d2c253821597aced4d1fb36'
SCHEMA = 'dng100-control-rhythm-result-v1'
TEXT_SOURCES = {**r3.TEXT_SOURCES,
                'dng100_engaged_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_engaged_rhythm.py',
                'dng100_route_comparison_py_lf_sha256': 'malecns_backend/embodiment/dng100_route_comparison.py'}
BINARY_SOURCES = {**r3.BINARY_SOURCES,
                  'r3_result_json_sha256': 'docs/evidence/dng100-engaged-rhythm-v1/run/result.json',
                  'r4_result_json_sha256': 'docs/evidence/dng100-route-comparison-v1/run/result.json'}
R3_RESULT = 'docs/evidence/dng100-engaged-rhythm-v1/run/result.json'
R4_RESULT = 'docs/evidence/dng100-route-comparison-v1/run/result.json'
DRIVES = dict(r3.DRIVES)
ARMS = ('R1SIZE', 'VNCSIZE')     # R1SIZE primary for this question
PRIMARY = 'R1SIZE'
TARGETS = {'DNg75_R': 129181, 'DNa02_L': 130496, 'DNp09_R': 1087}
PRIMARY_TARGETS = ('DNg75_R', 'DNa02_L')
SEEDS = range(2001, 2065)
CONTROL_SEEDS = range(2001, 2017)
I2_SEEDS = range(1001, 1005)
I2_TARGETS = (129181, 130496)
CORE = r3.CORE
CONDITIONS = ('STIM', 'SIL_E1', 'SIL_E2', 'SIL_I1', 'SIL_SHAM')
SHAM_OFFSET = 7_000_000
NEW_CONTROL_RNG = 20261108
NEW_CONTROL_COUNT = 20


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


# ---- draws ---------------------------------------------------------------------------------------

def new_controls(pool, exclude, count=NEW_CONTROL_COUNT, seed=NEW_CONTROL_RNG):
    """Draw from R1's control pool (sorted dense indices) minus exclude; all if fewer than count remain."""
    rest = sorted(i for i in pool if i not in set(exclude))
    if len(rest) <= count:
        return rest
    return sorted(int(i) for i in np.random.default_rng(seed).choice(rest, count, replace=False))


def sham_candidates(n, excluded):
    """Local indices eligible as sham cells (sorted)."""
    ex = set(int(i) for i in excluded)
    return [i for i in range(n) if i not in ex]


def sham_cell(seed, candidates):
    rng = np.random.default_rng(seed + SHAM_OFFSET)
    return int(candidates[int(rng.integers(len(candidates)))])


def conditions(core_local, sham_cands):
    """[(label, silenced-local-indices-function of seed)] per target, in protocol order."""
    out = [('STIM', lambda s: ())]
    out += [(f'SIL_{c}', (lambda j: (lambda s: (j,)))(core_local[c])) for c in CORE]
    out += [('SIL_SHAM', lambda s: (sham_cell(s, sham_cands),))]
    return out


# ---- verdict -------------------------------------------------------------------------------------

def p80(control_summaries):
    cs = [c['score'] for c in control_summaries.values() if not math.isnan(c['score'])]
    return (float(np.percentile(cs, 80)) if cs else math.nan), cs


def target_verdict(summaries, control_p80):
    """summaries: {condition: condition_summary}. R1's rules for C1-C3 (NaN silenced = abolished)."""
    stim = summaries['STIM']
    if math.isnan(stim['score']):
        return 'INCONCLUSIVE', dict(reason='no STIM replicate with a score')
    checks = dict(
        C1_rhythm=bool(stim['score'] >= .5 and (math.isnan(control_p80) or stim['score'] > control_p80)),
        C2_frequency=bool(not math.isnan(stim['frequency_hz']) and 5 <= stim['frequency_hz'] <= 20),
        C3_core_necessity=all(not (summaries[f'SIL_{c}']['score'] >= .5) for c in CORE),
        C4_sham_preserved=bool(summaries['SIL_SHAM']['score'] >= .5))
    not_needed = [c for c in CORE if summaries[f'SIL_{c}']['score'] >= .5]
    if not checks['C1_rhythm']:
        v = 'RHYTHM_NOT_CONFIRMED'
    elif not checks['C2_frequency']:
        v = 'RHYTHM_OUT_OF_BAND'
    elif not checks['C4_sham_preserved']:
        v = 'SILENCING_NONSPECIFIC'
    elif not checks['C3_core_necessity']:
        v = 'RHYTHM_CORE_INDEPENDENT'
    else:
        v = 'CORE_RHYTHM_CONFIRMED'
    return v, dict(checks=checks, core_cells_not_needed=not_needed)


def headline_verdict(arms):
    p = arms[PRIMARY]['targets']
    ok = all(p[t]['verdict'] == 'CORE_RHYTHM_CONFIRMED' for t in PRIMARY_TARGETS)
    return 'OBSERVATION_CONFIRMED' if ok else 'OBSERVATION_NOT_CONFIRMED'


def expectations(headline, arms):
    return dict(X1=headline == 'OBSERVATION_CONFIRMED',
                X2=all(arms['VNCSIZE']['targets'][t]['verdict'] == 'RHYTHM_NOT_CONFIRMED' for t in TARGETS),
                X3=None if math.isnan(arms['R1SIZE']['control_p80']) else bool(arms['R1SIZE']['control_p80'] < .5))


def i2_check(mine, r3_result):
    """mine: {(arm, dense, seed): dict(score, recruited, core_active)} vs R3's stored control runs."""
    bad, checked = [], 0
    for arm in DRIVES:
        for d in I2_TARGETS:
            runs = {r['seed']: r for r in r3_result['arms'][arm]['conditions'][f'CONTROL_{d}']['runs']}
            for s in I2_SEEDS:
                ref = runs[s]
                want = dict(score=ref['score'], recruited=ref['recruited'],
                            core_active={c: ref['core'][c]['active'] for c in CORE})
                got = mine[(arm, d, s)]
                checked += 1
                if not (r3.same(got['score'], want['score']) and got['recruited'] == want['recruited']
                        and got['core_active'] == want['core_active']):
                    bad.append(dict(arm=arm, dn=d, seed=s, got=got, r3=want))
    return dict(passed=not bad and checked == len(DRIVES)*len(I2_TARGETS)*len(I2_SEEDS), checked=checked,
                mismatches=bad)


# ---- run -------------------------------------------------------------------------------------------

def pool_and_classes(data, model):
    """R1's control pool (network ACh DNs except DNg100_L/R, as dng100_rate_model.control_dns) and
    local indices of network DNs and ANs."""
    nt = np.asarray(data.neurotransmitter_ids)
    sup = np.asarray(data.superclass_ids)
    ids = {k: dense(data, b) for k, b in CELLS.items()}
    exclude = {ids['DNg100_L'], ids['DNg100_R']}
    pool = sorted(i for i in model.net if data.superclasses[sup[i]] == 'descending_neuron'
                  and data.neurotransmitters[nt[i]] == 'acetylcholine' and i not in exclude)
    names = np.asarray(data.superclasses, object)[sup[np.asarray(model.net)]]
    dnan = np.flatnonzero(np.isin(names, ['descending_neuron', 'ascending_neuron']))
    return pool, dnan


def name_of(data, i):
    try:
        return str(data.instances[i]) if len(data.instances) == data.neuron_count else None
    except Exception:
        return None


def slim(run):
    return {k: v for k, v in run.items() if k != 'mn_detail'} | dict(
        mn_detail=run['mn_detail'] if run['score'] == run['score'] and run['score'] >= .5 else None)


def run(cache, progress=print):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    data = load_cache(cache)
    model, ctx, sizes, z_star, m_vnc = r3.setup(data)
    core_local = ctx['core']
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in model.net)).encode()).hexdigest()
    r3res = json.loads((ROOT/R3_RESULT).read_bytes())
    r4res = json.loads((ROOT/R4_RESULT).read_bytes())
    r4_rhythmic = sorted(int(v['dense']) for v in r4res['dns'].values() if v['group'] == 'RHYTHMIC')
    pool, dnan = pool_and_classes(data, model)
    controls = new_controls(pool, list(r3.CONTROLS))
    i1 = dict(r1_network_body_ids_sha256=body_sha, z_star=z_star, m_vnc=m_vnc, r4_rhythmic=r4_rhythmic,
              pool_size=len(pool), new_controls=controls,
              passed=bool(body_sha == spec['integrity']['r1_network_body_ids_sha256'] and z_star == r2.R1B_Z_STAR
                          and m_vnc == r2.R1B_M_VNC and r4_rhythmic == sorted(TARGETS.values())
                          and all(t in model.pos for t in TARGETS.values())
                          and len(controls) == min(NEW_CONTROL_COUNT, len(set(pool) - set(r3.CONTROLS)))
                          and not set(controls) & set(r3.CONTROLS)))
    if not i1['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I1 failed',
                    integrity=dict(I1=i1), sources=src)
    started = time.time()
    mine = {}
    for arm in DRIVES:
        size, ref = sizes[arm]
        for d in I2_TARGETS:
            for s in I2_SEEDS:
                r = r3.replicate(model, size, ref, s, DRIVES[arm], model.pos[d], (), core_local)
                mine[(arm, d, s)] = dict(score=r['score'], recruited=r['recruited'],
                                         core_active={c: r['core'][c]['active'] for c in CORE})
    i2 = i2_check(mine, r3res)
    progress(f'[{time.time()-started:6.0f}s] I2 R3 reproduction: {i2["passed"]} ({i2["checked"]} checked)', flush=True)
    if not i2['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I2 failed',
                    integrity=dict(I1=i1, I2=i2), sources=src)
    mn = set(model.mn_local.values())
    base_ex = set(dnan.tolist()) | mn | set(core_local.values())
    shams = {}
    for t, d in TARGETS.items():
        mids = r2.intermediates(model.W, model.pos[d], core_local)
        shams[t] = sham_candidates(len(model.net), base_ex | set().union(*map(set, mids.values())))
    arms, total = {}, 0
    for arm in ARMS:
        size, ref = sizes[arm]
        ctl = {}
        for d in controls:
            runs = [r3.replicate(model, size, ref, s, DRIVES[arm], model.pos[d], (), core_local)
                    for s in CONTROL_SEEDS]
            total += len(runs)
            ctl[str(d)] = dict(summary=r3.condition_summary(runs), runs=[slim(x) for x in runs])
        cp80, cscores = p80({k: v['summary'] for k, v in ctl.items()})
        progress(f'[{time.time()-started:6.0f}s] {arm} new controls done', flush=True)
        targets = {}
        for t, d in TARGETS.items():
            out = {}
            for label, sil in conditions(core_local, shams[t]):
                runs = []
                for s in SEEDS:
                    silenced = sil(s)
                    x = r3.replicate(model, size, ref, s, DRIVES[arm], model.pos[d], silenced, core_local)
                    x['silenced_local'] = list(silenced)
                    x['silenced_dense'] = [int(model.net[j]) for j in silenced]
                    runs.append(x)
                total += len(runs)
                out[label] = dict(summary=r3.condition_summary(runs), runs=[slim(x) for x in runs])
            summ = {k: v['summary'] for k, v in out.items()}
            v, det = target_verdict(summ, cp80)
            targets[t] = dict(dense=d, body_id=int(data.body_ids[d]), name=name_of(data, d), verdict=v, **det,
                              summaries=summ, conditions=out, sham_candidates=len(shams[t]))
            progress(f'[{time.time()-started:6.0f}s] {arm} {t} done', flush=True)
        arms[arm] = dict(drive=DRIVES[arm], control_p80=cp80, control_scores=cscores, targets=targets,
                         controls={k: dict(v, body_id=int(data.body_ids[int(k)]), name=name_of(data, int(k)))
                                   for k, v in ctl.items()})
    i4 = total == spec['conditions']['total_simulations']
    head = headline_verdict(arms) if i4 else 'INCONCLUSIVE'
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict=head, primary_arm=PRIMARY,
                verdicts={a: {t: arms[a]['targets'][t]['verdict'] for t in TARGETS} for a in ARMS},
                expectations=expectations(head, arms) if i4 else None, arms=arms,
                integrity=dict(I1=i1, I2=i2, I4=dict(passed=i4, simulations=total)),
                sources=src, runtime_s=round(time.time() - started, 1),
                interpretation_limits=spec['interpretation_limits'])


def headline(result):
    out = {k: result.get(k) for k in ('verdict', 'verdicts', 'expectations', 'reason', 'runtime_s')}
    for arm, a in result.get('arms', {}).items():
        out[arm] = dict(control_p80=a['control_p80'],
                        targets={t: dict(checks=v.get('checks'),
                                         scores={c: v['summaries'][c]['score'] for c in CONDITIONS},
                                         freq=v['summaries']['STIM']['frequency_hz'])
                                 for t, v in a['targets'].items()})
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--time-one', action='store_true',
                        help='plumbing: one R1SIZE DNg75_R simulation, seed 0 (not a protocol seed); wall time only')
    args = parser.parse_args(argv)
    if args.time_one:
        data = load_cache(args.cache)
        model, ctx, sizes, z_star, m_vnc = r3.setup(data)
        pool, _ = pool_and_classes(data, model)
        t = time.time()
        r3.replicate(model, *sizes['R1SIZE'], 0, DRIVES['R1SIZE'], model.pos[TARGETS['DNg75_R']], (), ctx['core'])
        print(json.dumps(dict(one_simulation_s=round(time.time() - t, 2), pool_size=len(pool),
                              sources=sources()), indent=1))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(jsonable(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(jsonable(headline(result)), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
