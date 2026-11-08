"""LIF return Step L1: do the rate model's rhythm drivers give a front-left rhythm in the live engine?

Preregistered in docs/evidence/lif-driver-rhythm-v1/protocol.json. DNg75_R and DNa02_L (primary)
and DNp09_R (secondary) are driven in the live, calibrated whole-CNS LIF engine (MaleCNSBrain),
untuned, with Stage 1 V1's harness (dng100_rhythm: simulate, score_simulation, best, readout).
At each target's best rate E1, E2 and a sham cell (R5's rule) are silenced. Neural only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from ..cache import load_cache
from ..neural import MaleCNSBrain
from . import dng100_control_rhythm as r5
from . import dng100_engaged_rhythm as r3
from . import dng100_recruitment_map as r2
from . import dng100_rhythm as v1

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/lif-driver-rhythm-v1/protocol.json'
PROTOCOL_SHA256 = '47278c7cf08a5f244cbb212a6f8407230ea4e3a0b9ea97ef697e47781ec52d75'
SCHEMA = 'lif-driver-rhythm-result-v1'
TEXT_SOURCES = {'neural_py_lf_sha256': 'malecns_backend/neural.py',
                'brain_params_lf_sha256': 'fly-brain-main/public/data/brain_params.json',
                'dng100_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_rhythm.py',
                'dng100_control_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_control_rhythm.py',
                'dng100_engaged_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_engaged_rhythm.py',
                'dng100_recruitment_map_py_lf_sha256': 'malecns_backend/embodiment/dng100_recruitment_map.py',
                'dng100_rate_model_py_lf_sha256': 'malecns_backend/embodiment/dng100_rate_model.py'}
BINARY_SOURCES = {'v1_protocol_json_sha256': 'docs/evidence/dng100-rhythm-v1/protocol.json',
                  'v1_result_json_sha256': 'docs/evidence/dng100-rhythm-v1/run/result.json'}
V1_RESULT = 'docs/evidence/dng100-rhythm-v1/run/result.json'
TARGETS = {'DNg75_R': 520300, 'DNa02_L': 523769, 'DNp09_R': 11177}      # body IDs
EXPECTED_DENSE = {'DNg75_R': 129181, 'DNa02_L': 130496, 'DNp09_R': 1087}
PRIMARY = ('DNg75_R', 'DNa02_L')
CORE = {'E1': 800173, 'E2': 800863, 'I1': 801884}                        # body IDs
RATES = (25, 50, 100, 200)
SEEDS = range(1, 17)
I2_RATE = 100
I2_SEEDS = range(1, 5)
SILENCING = ('SIL_E1', 'SIL_E2', 'SIL_SHAM')


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


def dense_of(data, body):
    hit = np.flatnonzero(np.asarray(data.body_ids) == body)
    if len(hit) != 1:
        raise ValueError(f'body {body} not unique')
    return int(hit[0])


# ---- simulation and aggregation (V1's, with core cells watched alongside) ---------------------

def split(spikes, mns):
    """Separate watched spikes into the MN set (scored) and everything else (reported only)."""
    mset = set(int(m) for m in mns)
    return ({m: v for m, v in spikes.items() if m in mset}, {m: v for m, v in spikes.items() if m not in mset})


def core_report(spikes, core, spec, dt_ms):
    start, stop = spec['readout']['analysis_window_ms']
    n_bins = int(spec['stimulus']['duration_ms'])
    out = {}
    for name, d in core.items():
        steps = spikes.get(d, [])
        t = np.asarray(steps)*dt_ms
        n = int(np.count_nonzero((t >= start) & (t < stop)))
        trace = v1.rates(steps, n_bins, dt_ms)[int(start):int(stop)]
        s, period = v1.rhythmicity(trace) if n >= 5 else (math.nan, None)
        out[name] = dict(spikes_in_window=n, mean_hz=n*1000./(stop - start), trace_score=s, period_ms=period)
    return out


def aggregate(rate, runs):
    """V1's condition aggregation, unchanged."""
    feasible = [r for r in runs if not math.isnan(r['score'])]
    freqs = [r['frequency_hz'] for r in feasible if not math.isnan(r['frequency_hz'])]
    return dict(rate_hz=rate, score=float(np.mean([r['score'] for r in feasible])) if feasible else math.nan,
                frequency_hz=float(np.median(freqs)) if freqs else math.nan, feasible_seeds=len(feasible), runs=runs)


def one(brain, spec, target, rate, seed, mns, core, silenced=()):
    watch = sorted(set(int(m) for m in mns) | set(core.values()))
    spikes = v1.simulate(brain, target, rate, seed, watch, spec['stimulus']['duration_ms'], silenced)
    mn_spikes, other = split(spikes, mns)
    score, freq, detail = v1.score_simulation(mn_spikes, spec, brain.config.dt)
    return dict(seed=seed, score=score, frequency_hz=freq, active_mns=len(detail),
                mn_spikes={str(m): len(v) for m, v in mn_spikes.items() if v},
                mn_detail={str(m): d for m, d in detail.items()}, silenced=[int(s) for s in silenced],
                core=core_report(other, core, spec, brain.config.dt))


# ---- criteria ------------------------------------------------------------------------------------

def target_class(levels, sil, p80):
    """levels: V1-style condition dicts; sil: {label: condition} at the best rate (may be empty)."""
    top = v1.best(levels)
    if top is None:
        return 'NO_MN_OUTPUT', dict(best_rate_hz=None, best_score=None)
    det = dict(best_rate_hz=top['rate_hz'], best_score=top['score'], best_frequency_hz=top['frequency_hz'])
    if not (top['score'] >= .5 and top['score'] > p80):
        return 'NOT_RHYTHMIC', det
    f = top['frequency_hz']
    checks = dict(frequency=bool(not math.isnan(f) and 5 <= f <= 20),
                  core=bool(not (sil['SIL_E1']['score'] >= .5) and not (sil['SIL_E2']['score'] >= .5)),
                  sham=bool(sil['SIL_SHAM']['score'] >= .5))
    det['checks'] = checks
    return ('LIF_RHYTHM_CORE' if all(checks.values()) else 'LIF_RHYTHM_OTHER'), det


def step_verdict(classes):
    p = [classes[t] for t in PRIMARY]
    if all(c == 'LIF_RHYTHM_CORE' for c in p):
        return 'REPRODUCED_IN_LIF'
    if any(c in ('LIF_RHYTHM_CORE', 'LIF_RHYTHM_OTHER') for c in p):
        return 'PARTIAL'
    return 'NOT_REPRODUCED_IN_LIF'


def expectations(classes, verdict):
    quiet = ('NOT_RHYTHMIC', 'NO_MN_OUTPUT')
    return dict(X1=classes['DNg75_R'] in quiet, X2=classes['DNa02_L'] in quiet, X3=verdict == 'NOT_REPRODUCED_IN_LIF')


def i2_check(mine, v1_result):
    ref = {r['seed']: r for l in v1_result['dng100']['levels'] if l['rate_hz'] == I2_RATE for r in l['runs']}
    bad = []
    for s in I2_SEEDS:
        got, want = mine[s], ref[s]
        if not (r3.same(got['score'], want['score']) and got['mn_spikes'] == want['mn_spikes']):
            bad.append(dict(seed=s, got=dict(score=got['score'], mn_spikes=got['mn_spikes']),
                            v1=dict(score=want['score'], mn_spikes=want['mn_spikes'])))
    return dict(passed=not bad and len(mine) == len(I2_SEEDS), checked=len(mine), mismatches=bad)


def sham_lists(data):
    """R5's sham eligibility per target (local indices in R1's network) and the local -> dense map."""
    model, ctx, _, _, _ = r3.setup(data)
    core_local = ctx['core']
    _, dnan = r5.pool_and_classes(data, model)
    base = set(dnan.tolist()) | set(model.mn_local.values()) | set(core_local.values())
    out = {}
    for t, d in EXPECTED_DENSE.items():
        mids = r2.intermediates(model.W, model.pos[d], core_local)
        out[t] = r5.sham_candidates(len(model.net), base | set().union(*map(set, mids.values())))
    return out, np.asarray(model.net)


def sham_dense(seed, candidates, net):
    return int(net[r5.sham_cell(seed, candidates)])


# ---- run --------------------------------------------------------------------------------------------

def run(cache, progress=print):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    v1spec = v1.protocol()
    v1res = json.loads((ROOT/V1_RESULT).read_bytes())
    p80 = float(v1res['control_p80'])
    data = load_cache(cache)
    mns = v1.front_left_mns(data.bodymap)
    targets = {t: dense_of(data, b) for t, b in TARGETS.items()}
    core = {c: dense_of(data, b) for c, b in CORE.items()}
    dng = [i for i, x in enumerate(data.instances) if x == 'DNg100_L']
    shams, net = sham_lists(data)
    i1 = dict(targets=targets, names={t: data.instances[d] for t, d in targets.items()}, core=core, mns=len(mns),
              control_p80=p80, sham_candidates={t: len(v) for t, v in shams.items()},
              passed=bool(targets == EXPECTED_DENSE and mns == v1res['front_left_mns'] and len(mns) == 68
                          and core['E1'] == v1res['core_copies']['E1']['dense_index']
                          and core['E2'] == v1res['core_copies']['E2']['dense_index']
                          and data.instances[targets['DNa02_L']] == 'DNa02_L'
                          and data.instances[targets['DNp09_R']] == 'DNp09_R'
                          and str(data.instances[targets['DNg75_R']]).startswith('DNg75')
                          and str(data.instances[targets['DNg75_R']]).endswith('_R')
                          and len(dng) == 1 and p80 == spec['acceptance']['control_p80']
                          and all(len(v) > 0 for v in shams.values())))
    if not i1['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I1 failed',
                    integrity=dict(I1=i1), sources=src)
    brain = MaleCNSBrain(data)
    started = time.time()

    def note(text):
        progress(f'[{time.time()-started:7.0f}s] {text}', flush=True)

    mine = {s: one(brain, v1spec, dng[0], I2_RATE, s, mns, core) for s in I2_SEEDS}
    i2 = i2_check(mine, v1res)
    note(f'I2 V1 reproduction: {i2["passed"]} ({i2["checked"]} checked)')
    if not i2['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='I2 failed',
                    integrity=dict(I1=i1, I2=i2), sources=src)
    out, total = {}, 0
    for t, d in targets.items():
        levels = []
        for rate in RATES:
            levels.append(aggregate(rate, [one(brain, v1spec, d, rate, s, mns, core) for s in SEEDS]))
            total += len(SEEDS)
            note(f'{t} {rate} Hz: score {levels[-1]["score"]:.3f} feasible {levels[-1]["feasible_seeds"]}')
        top = v1.best(levels)
        sil = {}
        if top is not None:
            plan = {'SIL_E1': lambda s: [core['E1']], 'SIL_E2': lambda s: [core['E2']],
                    'SIL_SHAM': lambda s: [sham_dense(s, shams[t], net)]}
            for label in SILENCING:
                sil[label] = aggregate(top['rate_hz'], [one(brain, v1spec, d, top['rate_hz'], s, mns, core,
                                                            plan[label](s)) for s in SEEDS])
                total += len(SEEDS)
                note(f'{t} {label} at {top["rate_hz"]} Hz: score {sil[label]["score"]:.3f}')
        cls, det = target_class(levels, sil, p80)
        out[t] = dict(dense=d, body_id=TARGETS[t], instance=data.instances[d], cls=cls, **det, levels=levels,
                      silencing=sil)
    feasible_targets = sum(1 for t in out.values() if v1.best(t['levels']) is not None)
    i4 = total == len(targets)*len(RATES)*len(SEEDS) + feasible_targets*len(SILENCING)*len(SEEDS)
    classes = {t: v['cls'] for t, v in out.items()}
    verdict = step_verdict(classes) if i4 else 'INCONCLUSIVE'
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict=verdict, classes=classes,
                expectations=expectations(classes, verdict) if i4 else None, control_p80=p80, targets=out,
                i2_runs={str(s): r for s, r in mine.items()},
                integrity=dict(I1=i1, I2=i2, I4=dict(passed=i4, simulations=total)), sources=src,
                runtime_s=round(time.time() - started, 1), interpretation_limits=spec['interpretation_limits'])


def headline(r):
    out = {k: r.get(k) for k in ('verdict', 'classes', 'expectations', 'reason', 'runtime_s')}
    for t, v in r.get('targets', {}).items():
        out[t] = dict(levels=[(l['rate_hz'], l['score'], l['frequency_hz'], l['feasible_seeds']) for l in v['levels']],
                      silencing={k: s['score'] for k, s in v['silencing'].items()})
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--time-one', action='store_true',
                        help='plumbing: one DNg100_L simulation at 100 Hz, seed 0 (not a protocol seed); wall time only')
    args = parser.parse_args(argv)
    if args.time_one:
        data = load_cache(args.cache)
        brain = MaleCNSBrain(data)
        dng = [i for i, x in enumerate(data.instances) if x == 'DNg100_L'][0]
        t = time.time()
        v1.simulate(brain, dng, 100, 0, v1.front_left_mns(data.bodymap), 3000)
        print(json.dumps(dict(one_simulation_s=round(time.time() - t, 2), sources=sources()), indent=1))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(v1.clean(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(v1.clean(headline(result)), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
