"""Rhythm Step R3: R1's rhythm criteria in the engaged regime found by R2.

Preregistered in docs/evidence/dng100-engaged-rhythm-v1/protocol.json. R1's model, readout and
verdict are reused unchanged (dng100_rate_model); cord-only sizes and the network context come from
R2 (dng100_recruitment_map). Fixed drives, no adjustment. Neural only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from ..cache import load_cache
from . import dng100_recruitment_map as r2
from .dng100_rate_model import (CELLS, Model, active, dense, draw, scale, score_rates, simulate, summarize,
                                tibia_phase, verdict, WINDOW)
from .dng100_rhythm import rhythmicity
from .dng100_size_audit import jsonable

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-engaged-rhythm-v1/protocol.json'
PROTOCOL_SHA256 = '51bec0c25f8f06e1b04143037027d4ea1d6a3700a855885fbbf63a9bf9b82cba'
SCHEMA = 'dng100-engaged-rhythm-result-v1'
TEXT_SOURCES = {**r2.TEXT_SOURCES,
                'dng100_recruitment_map_py_lf_sha256': 'malecns_backend/embodiment/dng100_recruitment_map.py'}
BINARY_SOURCES = {**r2.BINARY_SOURCES,
                  'r2_result_json_sha256': 'docs/evidence/dng100-recruitment-map-v1/run/result.json'}
R2_RESULT = 'docs/evidence/dng100-recruitment-map-v1/run/result.json'
DRIVES = {'VNCSIZE': 2000., 'R1SIZE': 16000.}
ARMS = ('VNCSIZE', 'R1SIZE')   # VNCSIZE primary
PRIMARY = 'VNCSIZE'
SEEDS = range(1001, 1065)
CONTROL_SEEDS = range(1001, 1017)
I2_SEEDS = range(1, 5)
CORE = ('E1', 'E2', 'I1')
CONTROLS = [92, 278, 754, 763, 820, 1052, 1087, 1599, 2659, 4164, 4685, 9205, 9762, 11053, 21341, 26520, 39896,
            128032, 129181, 130496]


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


# ---- conditions -------------------------------------------------------------------------------

def conditions(dng100, core, controls):
    """[(label, stimulated dense index, silenced dense indices, seeds)] for one arm (dense indices)."""
    out = [('DNG100', dng100, (), SEEDS)]
    out += [(f'SIL_{c}', dng100, (core[c],), SEEDS) for c in CORE]
    out += [(f'CONTROL_{d}', d, (), CONTROL_SEEDS) for d in controls]
    return out


def replicate(model, sizes, ref, seed, drive, stim, silenced, core_local):
    p = draw(seed, len(model.net))
    a, theta, _ = scale(p, sizes, ref)
    rates = simulate(model.W, a, theta, p['tau'], p['rmax'], stim, drive, list(silenced))
    window = rates[WINDOW[0]:WINDOW[1]]
    act = active(rates)
    score, freq, detail = score_rates(rates, model.mn_local, model.names)
    core = {}
    for c, j in core_local.items():
        on = bool(act[j])
        s, period = rhythmicity(window[:, j]) if on else (math.nan, None)
        core[c] = dict(active=on, mean_hz=float(window[:, j].mean()), max_hz=float(window[:, j].max()),
                       trace_score=s, trace_period_ms=period)
    return dict(seed=seed, status='FEASIBLE', score=score, frequency_hz=freq, active_mns=len(detail),
                recruited=int(act.sum()), engaged=all(core[c]['active'] for c in CORE),
                stim_mean_hz=float(window[:, stim].mean()), core=core,
                tibia_phase=tibia_phase(rates, model.mn_local, model.names), mn_detail=detail)


def condition_summary(runs):
    s = summarize(runs)
    s['engaged_fraction'] = sum(r['engaged'] for r in runs)/len(runs)
    s['median_recruited'] = float(np.median([r['recruited'] for r in runs]))
    for c in CORE:
        ts = [r['core'][c]['trace_score'] for r in runs if r['core'][c]['active']]
        s[f'{c}_trace_score_median'] = float(np.median(ts)) if ts else math.nan
        s[f'{c}_active_fraction'] = sum(r['core'][c]['active'] for r in runs)/len(runs)
    return s


def arm_verdict(dng, controls, silenced):
    """R1's verdict plus the engagement qualifier."""
    v, details = verdict(dng, controls, silenced)
    qualifier = 'CORE_NOT_RELIABLY_ENGAGED' if dng['engaged_fraction'] < .5 else None
    return v, dict(details, qualifier=qualifier)


def expectations(arms):
    p, s = arms['VNCSIZE'], arms['R1SIZE']
    e1 = p['dng100']['E1_trace_score_median']
    return dict(X1=p['verdict'] == 'RATE_RHYTHM_NOT_REPRODUCED' and p['dng100']['score'] < .1,
                X2=s['verdict'] == 'RATE_RHYTHM_NOT_REPRODUCED',
                X3=None if math.isnan(e1) else bool(e1 < .5))


# ---- I2: reproduce R2 -------------------------------------------------------------------------------

def same(a, b):
    if a is None or (isinstance(a, float) and math.isnan(a)):
        return b is None or (isinstance(b, float) and math.isnan(b))
    return a == b


def i2_check(mine, r2_sims):
    """mine: {(arm, seed): dict(recruited, core_active, score)}; r2_sims: R2 result 'simulations'."""
    bad, checked = [], 0
    for arm, drive in DRIVES.items():
        rec = {s['seed']: s for s in r2_sims[arm] if s['drive'] == drive}
        for seed in I2_SEEDS:
            got, ref = mine[(arm, seed)], rec[seed]
            want = dict(recruited=ref['recruited'], core_active={c: ref['core'][c]['active'] for c in CORE},
                        score=ref['rhythm_score_reported_only'])
            checked += 1
            if not (got['recruited'] == want['recruited'] and got['core_active'] == want['core_active']
                    and same(got['score'], want['score'])):
                bad.append(dict(arm=arm, seed=seed, got=got, r2=want))
    return dict(passed=not bad and checked == len(DRIVES)*len(I2_SEEDS), checked=checked, mismatches=bad)


# ---- run --------------------------------------------------------------------------------------------

def setup(data):
    model = Model(data)
    ctx = r2.context(data, model)
    vnc_size, m_vnc, z_star, _ = r2.cord_only_sizes(data, np.asarray(model.net))
    return model, ctx, dict(R1SIZE=(model.size, model.size_ref), VNCSIZE=(vnc_size, m_vnc)), z_star, m_vnc


def run(cache, progress=print):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    data = load_cache(cache)
    model, ctx, sizes, z_star, m_vnc = setup(data)
    ids = {k: dense(data, b) for k, b in CELLS.items()}
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in model.net)).encode()).hexdigest()
    i1 = dict(r1_network_body_ids_sha256=body_sha, z_star=z_star, m_vnc=m_vnc,
              controls_in_network=all(c in model.pos for c in CONTROLS),
              passed=bool(body_sha == spec['integrity']['r1_network_body_ids_sha256'] and z_star == r2.R1B_Z_STAR
                          and m_vnc == r2.R1B_M_VNC and all(c in model.pos for c in CONTROLS)
                          and CONTROLS == spec['conditions']['controls_dense_indices']))
    if not i1['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I1 failed',
                    integrity=dict(I1=i1), sources=src)
    started = time.time()
    core_local = ctx['core']
    mine = {}
    for arm in ARMS:
        size, ref = sizes[arm]
        for seed in I2_SEEDS:
            r = replicate(model, size, ref, seed, DRIVES[arm], ctx['stim'], (), core_local)
            mine[(arm, seed)] = dict(recruited=r['recruited'], core_active={c: r['core'][c]['active'] for c in CORE},
                                     score=r['score'])
    i2 = i2_check(mine, json.loads((ROOT/R2_RESULT).read_bytes())['simulations'])
    progress(f'[{time.time()-started:6.0f}s] I2 R2 reproduction: {i2["passed"]} ({i2["checked"]} checked)', flush=True)
    if not i2['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I2 failed',
                    integrity=dict(I1=i1, I2=i2), sources=src)
    arms, total = {}, 0
    for arm in ARMS:
        size, ref = sizes[arm]
        out = {}
        for label, stim, silenced, seeds in conditions(ids['DNg100_L'], ids, CONTROLS):
            runs = [replicate(model, size, ref, s, DRIVES[arm], model.pos[stim], [model.pos[x] for x in silenced],
                              core_local) for s in seeds]
            total += len(runs)
            out[label] = dict(summary=condition_summary(runs), runs=runs)
            sm = out[label]['summary']
            progress(f'[{time.time()-started:6.0f}s] {arm} {label}: score {sm["score"]:.3f} freq {sm["frequency_hz"]} '
                     f'engaged {sm["engaged_fraction"]:.2f} recruited {sm["median_recruited"]}', flush=True)
        ctl = {k[len('CONTROL_'):]: v['summary'] for k, v in out.items() if k.startswith('CONTROL_')}
        sil = {c: out[f'SIL_{c}']['summary'] for c in CORE}
        v, details = arm_verdict(out['DNG100']['summary'], ctl, sil)
        arms[arm] = dict(verdict=v, drive=DRIVES[arm], **details, dng100=out['DNG100']['summary'],
                         silenced=sil, controls=ctl, conditions=out)
    i4 = total == spec['conditions']['total_simulations']
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256,
                verdict=arms[PRIMARY]['verdict'] if i4 else 'INCONCLUSIVE',
                primary_arm=PRIMARY, qualifier=arms[PRIMARY]['qualifier'],
                secondary=dict(arm='R1SIZE', verdict=arms['R1SIZE']['verdict'], qualifier=arms['R1SIZE']['qualifier']),
                expectations=expectations(arms), arms=arms,
                integrity=dict(I1=i1, I2=i2, I4=dict(passed=i4, simulations=total)),
                cells={k: dict(dense_index=i, body_id=int(data.body_ids[i])) for k, i in ids.items()},
                sources=src, runtime_s=round(time.time() - started, 1),
                interpretation_limits=spec['interpretation_limits'])


def headline(result):
    out = {k: result.get(k) for k in ('verdict', 'primary_arm', 'qualifier', 'secondary', 'expectations', 'reason',
                                      'runtime_s')}
    for arm, a in result.get('arms', {}).items():
        out[arm] = dict(verdict=a['verdict'], checks=a.get('checks'), control_p80=a.get('control_p80'),
                        dng100={k: a['dng100'][k] for k in ('score', 'frequency_hz', 'engaged_fraction',
                                                            'E1_trace_score_median', 'E2_trace_score_median',
                                                            'I1_trace_score_median')},
                        silenced={c: a['silenced'][c]['score'] for c in CORE})
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--time-one', action='store_true',
                        help='plumbing: one VNCSIZE DNG100 simulation, seed 0 (not a protocol seed); wall time only')
    args = parser.parse_args(argv)
    if args.time_one:
        data = load_cache(args.cache)
        model, ctx, sizes, z_star, m_vnc = setup(data)
        t = time.time()
        replicate(model, *sizes['VNCSIZE'], 0, DRIVES['VNCSIZE'], ctx['stim'], (), ctx['core'])
        print(json.dumps(dict(one_simulation_s=round(time.time() - t, 2), z_star=z_star, m_vnc=m_vnc,
                              sources=sources()), indent=1))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(jsonable(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(jsonable(headline(result)), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
