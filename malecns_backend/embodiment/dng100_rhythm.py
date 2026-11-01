"""Stage 1: does our untuned whole-CNS LIF engine reproduce the DNg100 front-leg motor rhythm?

Preregistered in docs/evidence/dng100-rhythm-v1/protocol.json. Neural simulation only:
no body, physics, mapping, sign, gain or admission change.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from scipy.stats import spearmanr

from ..cache import load_cache
from ..neural import MaleCNSBrain

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-rhythm-v1/protocol.json'
PROTOCOL_SHA256 = '3a65a0cefc2dcf57fb2af4d906aa9d44183b5d221b15e51d64b5dc0b26920068'
SCHEMA = 'dng100-rhythm-result-v1'
ENGINE_FILES = {'neural_py_lf_sha256': 'malecns_backend/neural.py',
                'brain_params_lf_sha256': 'fly-brain-main/public/data/brain_params.json'}


def lf_sha(path):
    return hashlib.sha256((ROOT/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


# ---- preprint rhythmicity score -------------------------------------------------

def _raw_score(trace):
    span = trace.max() - trace.min()
    if span <= 0:
        return None
    x = 2*(trace - trace.min())/span - 1
    x = x - x.mean()
    ac = np.correlate(x, x, 'full')[len(x)-1:]
    if ac[0] <= 0:
        return None
    ac = ac/ac[0]
    peaks, props = find_peaks(ac[1:], prominence=.05)
    if not len(peaks):
        return None
    best = int(np.argmax(props['prominences']))
    raw = min(float(ac[1:][peaks].max()), float(props['prominences'].max()))
    return raw, int(peaks[best]) + 1


def rhythmicity(trace, bin_ms=1.):
    """Score in [0,1] and period (ms) of one rate trace; (0, None) without a qualifying peak."""
    found = _raw_score(np.asarray(trace, float))
    if found is None:
        return 0., None
    raw, lag = found
    reference = _raw_score(np.sin(2*np.pi*np.arange(len(trace))/lag))
    if reference is None or reference[0] <= 0:
        return 0., None
    return float(min(1., max(0., raw/reference[0]))), lag*bin_ms


def rates(spike_steps, n_bins, dt_ms, sigma_ms=5., bin_ms=1.):
    counts = np.bincount((np.asarray(spike_steps)*dt_ms/bin_ms).astype(int), minlength=n_bins)[:n_bins].astype(float)
    return gaussian_filter1d(counts, sigma_ms/bin_ms)*(1000./bin_ms)


def score_simulation(spikes_by_mn, spec, dt_ms):
    """spikes_by_mn: {mn: array of step indices}. Returns score (NaN if infeasible), frequency, per-MN detail."""
    r = spec['readout']
    start, stop = r['analysis_window_ms']
    n_bins = int(spec['stimulus']['duration_ms'])
    detail, scores, freqs = {}, [], []
    for mn, steps in sorted(spikes_by_mn.items()):
        t = np.asarray(steps)*dt_ms
        if np.count_nonzero((t >= start) & (t < stop)) < 5:
            continue
        trace = rates(steps, n_bins, dt_ms)[int(start):int(stop)]
        s, period = rhythmicity(trace)
        detail[int(mn)] = dict(score=s, period_ms=period)
        scores.append(s)
        if s > 0 and period:
            freqs.append(1000./period)
    if not scores:
        return math.nan, math.nan, detail
    return float(np.mean(scores)), float(np.median(freqs)) if freqs else math.nan, detail


# ---- network selection ------------------------------------------------------------

def front_left_mns(bodymap):
    return sorted({int(i) for e in bodymap['muscles'] if e['name'].endswith(' T1 left') for i in e['idx']})


def synapses_onto(data, sources, targets):
    targets = set(targets)
    totals = {}
    for s in sources:
        a, b = int(data.row_ptr[s]), int(data.row_ptr[s+1])
        post = np.asarray(data.target_indices[a:b]); w = np.asarray(data.synapse_counts[a:b])
        totals[int(s)] = int(w[np.isin(post, list(targets))].sum())
    return totals


def select_copy(data, cell_type, mns):
    totals = synapses_onto(data, [i for i, t in enumerate(data.types) if t == cell_type], mns)
    best = max(sorted(totals), key=lambda i: totals[i])
    return best, totals


def control_dns(data, exclude, count, seed):
    sup, nt = np.asarray(data.superclass_ids), np.asarray(data.neurotransmitter_ids)
    pool = sorted(i for i in range(data.neuron_count) if data.superclasses[sup[i]] == 'descending_neuron'
                  and data.neurotransmitters[nt[i]] == 'acetylcholine' and i not in exclude)
    return sorted(int(i) for i in np.random.default_rng(seed).choice(pool, count, replace=False))


# ---- simulation -----------------------------------------------------------------

def simulate(brain, target, rate_hz, seed, mns, duration_ms, silenced=()):
    brain.reset(seed)
    brain.clear_external_drive()
    if rate_hz:
        brain.set_external_drive([target], rate_hz)
    brain.transmission_withheld_indices = np.asarray(silenced, dtype=np.intp)
    watch = np.asarray(mns)
    spikes = {int(m): [] for m in mns}
    for step in range(int(round(duration_ms/brain.config.dt))):
        fired = brain.step()
        if len(fired):
            for m in np.intersect1d(fired, watch, assume_unique=False):
                spikes[int(m)].append(step)
    brain.clear_external_drive()
    return spikes


def condition(brain, spec, target, rate, seeds, mns, silenced=()):
    runs = []
    for seed in seeds:
        spikes = simulate(brain, target, rate, seed, mns, spec['stimulus']['duration_ms'], silenced)
        score, freq, detail = score_simulation(spikes, spec, brain.config.dt)
        runs.append(dict(seed=seed, score=score, frequency_hz=freq, active_mns=len(detail),
                         mn_spikes={str(m): len(v) for m, v in spikes.items() if v}))
    feasible = [r for r in runs if not math.isnan(r['score'])]
    freqs = [r['frequency_hz'] for r in feasible if not math.isnan(r['frequency_hz'])]
    return dict(rate_hz=rate, score=float(np.mean([r['score'] for r in feasible])) if feasible else math.nan,
                frequency_hz=float(np.median(freqs)) if freqs else math.nan, feasible_seeds=len(feasible), runs=runs)


def best(levels):
    feasible = [l for l in levels if not math.isnan(l['score'])]
    return max(feasible, key=lambda l: (l['score'], -l['rate_hz'])) if feasible else None


def verdict(dng, controls, silenced, spec):
    top = best(dng)
    if top is None:
        return 'INCONCLUSIVE', {}
    control_scores = [b['score'] for b in (best(c) for c in controls.values()) if b is not None]
    p80 = float(np.percentile(control_scores, 80)) if control_scores else math.nan
    checks = dict(
        C1_rhythm=top['score'] >= .5 and (math.isnan(p80) or top['score'] > p80),
        C2_frequency=not math.isnan(top['frequency_hz']) and 5 <= top['frequency_hz'] <= 20,
        C3_necessity=all(not (s['score'] >= .5) for s in silenced.values()))
    feasible = [l for l in dng if not math.isnan(l['frequency_hz'])]
    rho = spearmanr([l['rate_hz'] for l in feasible], [l['frequency_hz'] for l in feasible])[0] if len(feasible) >= 3 else math.nan
    secondary = dict(C4_drive_scaling_spearman=None if math.isnan(rho) else float(rho), control_p80=p80,
                     control_best_scores=control_scores, dng100_best_rate_hz=top['rate_hz'])
    if not checks['C1_rhythm']:
        result = 'NOT_REPRODUCED'
    elif checks['C2_frequency'] and checks['C3_necessity']:
        result = 'REPRODUCED'
    else:
        result = 'PARTIAL'
    return result, dict(checks=checks, **secondary)


def run(cache, progress=print):
    spec = protocol()
    engine = {k: lf_sha(p) for k, p in ENGINE_FILES.items()}
    if engine != {k: spec['engine'][k] for k in ENGINE_FILES}:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='engine hash mismatch', engine=engine)
    data = load_cache(cache)
    brain = MaleCNSBrain(data)
    mns = front_left_mns(data.bodymap)
    dng = [i for i, x in enumerate(data.instances) if x == 'DNg100_L']
    if len(dng) != 1:
        raise ValueError('exactly one DNg100_L required')
    dng = dng[0]
    stim = spec['stimulus']
    started = time.time()

    def note(text):
        progress(f'[{time.time()-started:7.0f}s] {text}', flush=True)

    baseline = condition(brain, spec, dng, 0, range(1, 17), mns)
    note(f"baseline score {baseline['score']}")
    levels = []
    for rate in stim['rates_hz']:
        levels.append(condition(brain, spec, dng, rate, range(1, 17), mns))
        note(f"DNg100 {rate} Hz score {levels[-1]['score']:.3f} freq {levels[-1]['frequency_hz']}")
    top = best(levels)
    copies = {}
    silenced = {}
    for label, cell in (('E1', 'IN17A001'), ('E2', 'INXXX466')):
        chosen, totals = select_copy(data, cell, mns)
        copies[label] = dict(type=cell, dense_index=chosen, body_id=int(data.body_ids[chosen]),
                             instance=data.instances[chosen], synapses_onto_front_left_mns=totals)
        if top is not None:
            silenced[label] = condition(brain, spec, dng, top['rate_hz'], range(1, 17), mns, silenced=[chosen])
            note(f"{label} silenced score {silenced[label]['score']}")
    controls = {}
    picks = control_dns(data, {dng}, 20, 20261101)
    for k, c in enumerate(picks):
        controls[str(c)] = [condition(brain, spec, c, rate, range(1, 5), mns) for rate in stim['rates_hz']]
        b = best(controls[str(c)])
        note(f"control {k+1}/20 {data.types[c]} best {None if b is None else round(b['score'], 3)}")
    result, details = verdict(levels, controls, silenced, spec)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, engine=engine, verdict=result, **details,
                dng100=dict(dense_index=dng, body_id=int(data.body_ids[dng]), levels=levels),
                front_left_mns=mns, baseline=baseline, core_copies=copies, silenced=silenced,
                controls={c: dict(type=data.types[int(c)], instance=data.instances[int(c)], levels=v) for c, v in controls.items()},
                runtime_s=round(time.time()-started, 1), interpretation_limits=spec['interpretation_limits'])


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, range)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if math.isnan(value) else float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(clean(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(clean({k: result.get(k) for k in ('verdict', 'checks', 'control_p80', 'dng100_best_rate_hz',
                                                         'C4_drive_scaling_spearman', 'runtime_s')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
