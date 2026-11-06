"""Rhythm Step R1: the preprint's DNg100 rate model on our maleCNS front-left network.

Preregistered in docs/evidence/dng100-rate-model-v1/protocol.json. Neural-only reference
model: no live engine, calibration, mapping, body or admission change. The rhythmicity score
and front-left MN set are reused from the Stage 1 V1 module.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy import sparse
from scipy.integrate import solve_ivp

from ..cache import load_cache
from ..neural import ModelConfig, region_scales
from .dng100_rhythm import clean, front_left_mns, rhythmicity

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-rate-model-v1/protocol.json'
PROTOCOL_SHA256 = '3785bbeb11c7bd2255f5ebade21afff9dbff08d32bc9f798f049dbb16b0621dc'
SCHEMA = 'dng100-rate-model-result-v1'
SOURCE_FILES = {'ratenet_js_lf_sha256': 'fly-brain-main/src/ratenet.js',
                'bodymap_lf_sha256': 'fly-brain-main/public/data/bodymap.json',
                'dng100_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_rhythm.py',
                'neural_py_lf_sha256': 'malecns_backend/neural.py'}

FLOOR = 5
B = 0.03
DURATION_MS = 1000.
ONSET_MS = 20.
WINDOW = (250, 1000)            # samples t = 250..999 ms (1-ms grid)
ACTIVE_HZ = 0.01
I_START = 250.
RECRUIT = (5, 500)
MAX_ADJUST = 10
RTOL, ATOL = 2e-6, 5e-9
# ratenet.js NT_SIGN with modulatorySign = 1: unknown, ACh, GABA, Glu, DA, 5HT, OA, histamine
NT_SIGN = {'acetylcholine': 1., 'gaba': -1., 'glutamate': -1., 'dopamine': 1., 'serotonin': 1.,
           'octopamine': 1., 'histamine': -1.}


def lf_sha(path):
    return hashlib.sha256((ROOT/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


# ---- network ----------------------------------------------------------------------

def edges(data):
    rp = np.asarray(data.row_ptr)
    src = np.repeat(np.arange(data.neuron_count), np.diff(rp))
    tgt, w = np.asarray(data.target_indices), np.asarray(data.synapse_counts)
    keep = w >= FLOOR
    return src[keep], tgt[keep], w[keep].astype(np.float64)


def build_network(data, mns=None):
    """Preprint rule on our wiring. Returns sorted dense indices and membership counts."""
    mns = sorted(mns if mns is not None else front_left_mns(data.bodymap))
    src, tgt, _ = edges(data)
    sup = np.asarray(data.superclass_ids)
    is_dn = np.array([s == 'descending_neuron' for s in data.superclasses])[sup]
    mnset = set(mns)
    pre = set(np.unique(src[np.isin(tgt, mns)]).tolist()) - mnset
    local = sorted(i for i in pre if not is_dn[i])
    dns = set(np.unique(src[np.isin(tgt, local) & is_dn[src]]).tolist())
    members = mnset | pre | dns
    nt = np.asarray(data.neurotransmitter_ids)
    # Unknown-transmitter neurons are dropped, except the scored MNs (kept as readout; sign 0, so
    # they send no input). Amendment before any simulation: 21 of the 68 V1 MNs are 'unknown'.
    unknown = {i for i in members - mnset if data.neurotransmitters[nt[i]] == 'unknown'}
    net = sorted(members - unknown)
    return net, dict(mns=len(mns), premotor=len(pre), premotor_dns=len(pre) - len(local),
                     dns_onto_premotor=len(dns), before_filter=len(members), unknown_removed=len(unknown),
                     network=len(net))


def signed_matrix(data, net):
    """W[post, pre] = sign(pre) * synapse count (>= FLOOR) within the network (local indices)."""
    src, tgt, w = edges(data)
    pos = -np.ones(data.neuron_count, np.int64)
    pos[net] = np.arange(len(net))
    keep = (pos[src] >= 0) & (pos[tgt] >= 0)
    nt = np.asarray(data.neurotransmitter_ids)
    sign = np.array([NT_SIGN.get(data.neurotransmitters[nt[i]], 0.) for i in net])
    pre, post = pos[src[keep]], pos[tgt[keep]]
    W = sparse.csr_matrix((sign[pre]*w[keep], (post, pre)), shape=(len(net), len(net)))
    return W, int(keep.sum()), float(w[keep].sum())


def vnc_size_median(data):
    _, _, med = region_scales(data, ModelConfig())
    return float(med[2])


# ---- model --------------------------------------------------------------------------

def trunc_normal(rng, mean, std, n):
    x = rng.normal(mean, std, n)
    while np.any(bad := x <= 0):
        x[bad] = rng.normal(mean, std, int(bad.sum()))
    return x


def draw(seed, n):
    rng = np.random.default_rng(seed)
    return dict(a_star=trunc_normal(rng, 1., .1, n), theta_star=trunc_normal(rng, 7.5, .6, n),
                tau=trunc_normal(rng, 20., 2., n), rmax=trunc_normal(rng, 200., 10., n))


def scale(params, size, size_ref):
    s = np.where(size > 0, size/size_ref, 1.)
    return params['a_star']/s, params['theta_star']*s, s


def rhs(r, W, I, a, theta, tau, rmax, silenced, b=B):
    x = I + b*(W @ r) - theta
    act = np.maximum(rmax*np.tanh(a/rmax*x), 0.)
    act[silenced] = 0.
    return (act - r)/tau


def simulate(W, a, theta, tau, rmax, stim, i_stim, silenced, duration=DURATION_MS, onset=ONSET_MS):
    """Rates on the 1-ms grid t = 0..duration-1 (array [time, neuron])."""
    n = W.shape[0]
    sil = np.zeros(n, bool)
    sil[list(silenced)] = True
    grid = np.arange(int(duration))
    out = np.zeros((len(grid), n))
    r0 = np.zeros(n)
    for lo, hi, current in ((0., onset, 0.), (onset, duration, i_stim)):
        I = np.zeros(n)
        if stim is not None:
            I[stim] = current
        sel = (grid >= lo) & (grid < hi)
        sol = solve_ivp(lambda t, r: rhs(r, W, I, a, theta, tau, rmax, sil), (lo, hi), r0, method='RK45',
                        t_eval=np.append(grid[sel], hi), rtol=RTOL, atol=ATOL)
        if not sol.success:
            raise RuntimeError(sol.message)
        out[sel] = sol.y[:, :-1].T
        r0 = sol.y[:, -1]
    return out


def active(rates):
    return rates[WINDOW[0]:WINDOW[1]].max(axis=0) > ACTIVE_HZ


def adjust(run, i_start=I_START):
    """Preprint rule: double if < 5 recruited, halve if > 500; at most 10 adjustments."""
    current, history = i_start, []
    for k in range(MAX_ADJUST + 1):
        rates = run(current)
        n = int(active(rates).sum())
        history.append(dict(i_stim=current, recruited=n))
        if RECRUIT[0] <= n <= RECRUIT[1]:
            return rates, dict(status='FEASIBLE', i_stim=current, adjustments=k, history=history)
        if k == MAX_ADJUST:
            break
        current = current*2 if n < RECRUIT[0] else current/2
    return rates, dict(status='INFEASIBLE', i_stim=current, adjustments=MAX_ADJUST, history=history)


def score_rates(rates, mn_local, names):
    """V1 score on rate traces: mean over active MNs; NaN if none."""
    window = rates[WINDOW[0]:WINDOW[1]]
    detail, scores, freqs = {}, [], []
    for mn, j in mn_local.items():
        trace = window[:, j]
        if trace.max() <= ACTIVE_HZ:
            continue
        s, period = rhythmicity(trace)
        detail[mn] = dict(muscle=names.get(mn), score=s, period_ms=period, max_hz=float(trace.max()),
                          mean_hz=float(trace.mean()))
        scores.append(s)
        if s > 0 and period:
            freqs.append(1000./period)
    if not scores:
        return math.nan, math.nan, detail
    return float(np.mean(scores)), (float(np.median(freqs)) if freqs else math.nan), detail


def tibia_phase(rates, mn_local, names):
    """Descriptive: lag (ms) of the peak normalized cross-correlation of the Ti flexor vs Ti extensor means."""
    window = rates[WINDOW[0]:WINDOW[1]]
    groups = {}
    for label in ('Ti flexor', 'Ti extensor'):
        cols = [j for mn, j in mn_local.items() if (names.get(mn) or '').startswith(label + ' MN')]
        groups[label] = window[:, cols].mean(axis=1) if cols else None
    f, e = groups['Ti flexor'], groups['Ti extensor']
    if f is None or e is None or f.std() == 0 or e.std() == 0:
        return None
    f, e = (f - f.mean())/f.std(), (e - e.mean())/e.std()
    lags = np.arange(-100, 101)
    cc = [float(np.mean(f[max(0, -l):len(f) - max(0, l)]*e[max(0, l):len(e) - max(0, -l)])) for l in lags]
    k = int(np.argmax(cc))
    return dict(peak_lag_ms=int(lags[k]), peak_corr=cc[k], corr_at_zero=cc[100])


# ---- verdict ------------------------------------------------------------------------

def summarize(runs):
    feasible = [r for r in runs if r['status'] == 'FEASIBLE' and not math.isnan(r['score'])]
    freqs = [r['frequency_hz'] for r in feasible if not math.isnan(r['frequency_hz'])]
    return dict(score=float(np.mean([r['score'] for r in feasible])) if feasible else math.nan,
                frequency_hz=float(np.median(freqs)) if freqs else math.nan, feasible=len(feasible),
                replicates=len(runs),
                fraction_ge_half=(sum(r['score'] >= .5 for r in feasible)/len(feasible)) if feasible else math.nan)


def verdict(dng, controls, silenced):
    if math.isnan(dng['score']):
        return 'INCONCLUSIVE', dict(reason='no feasible DNG100 replicate')
    cs = [c['score'] for c in controls.values() if not math.isnan(c['score'])]
    p80 = float(np.percentile(cs, 80)) if cs else math.nan
    checks = dict(C1_rhythm=dng['score'] >= .5 and (math.isnan(p80) or dng['score'] > p80),
                  C2_frequency=not math.isnan(dng['frequency_hz']) and 5 <= dng['frequency_hz'] <= 20,
                  C3_necessity=all(not (s['score'] >= .5) for s in silenced.values()))
    if not checks['C1_rhythm']:
        v = 'RATE_RHYTHM_NOT_REPRODUCED'
    elif checks['C2_frequency'] and checks['C3_necessity']:
        v = 'RATE_RHYTHM_REPRODUCED'
    else:
        v = 'RATE_RHYTHM_PARTIAL'
    return v, dict(checks=checks, control_p80=p80, control_scores=cs)


# ---- run ----------------------------------------------------------------------------

class Model:
    def __init__(self, data):
        self.data = data
        self.net, self.counts = build_network(data)
        self.pos = {g: k for k, g in enumerate(self.net)}
        self.W, self.edges, self.synapses = signed_matrix(data, self.net)
        self.size_ref = vnc_size_median(data)
        self.size = np.asarray(data.neuron_sizes, np.float64)[self.net]
        mns = front_left_mns(data.bodymap)
        self.mn_local = {m: self.pos[m] for m in mns if m in self.pos}
        self.names = {int(i): e['name'] for e in data.bodymap['muscles'] if e['name'].endswith(' T1 left')
                      for i in e['idx']}

    def local(self, idx):
        return self.pos[idx]

    def replicate(self, seed, stim=None, silenced=(), duration=DURATION_MS, adjust_drive=True):
        p = draw(seed, len(self.net))
        a, theta, _ = scale(p, self.size, self.size_ref)
        sil = [self.local(s) for s in silenced]
        st = None if stim is None else self.local(stim)
        run = lambda i: simulate(self.W, a, theta, p['tau'], p['rmax'], st, i, sil, duration=duration)
        if st is None:
            rates = run(0.)
            info = dict(status='FEASIBLE', i_stim=0., adjustments=0,
                        history=[dict(i_stim=0., recruited=int(active(rates).sum()))])
        elif adjust_drive:
            rates, info = adjust(run)
        else:
            rates = run(I_START)
            info = dict(status='FEASIBLE', i_stim=I_START, adjustments=0, history=[])
        score, freq, detail = score_rates(rates, self.mn_local, self.names)
        if info['status'] != 'FEASIBLE':
            score, freq = math.nan, math.nan
        return dict(seed=seed, score=score, frequency_hz=freq, active_mns=len(detail),
                    recruited=info['history'][-1]['recruited'] if info['history'] else None,
                    tibia_phase=tibia_phase(rates, self.mn_local, self.names), mn_detail=detail, **info)


def run(cache, progress=print):
    spec = protocol()
    sources = {k: lf_sha(p) for k, p in SOURCE_FILES.items()}
    if sources != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=sources)
    data = load_cache(cache)
    m = Model(data)
    body = [int(data.body_ids[i]) for i in m.net]
    body_sha = hashlib.sha256(json.dumps(sorted(body)).encode()).hexdigest()
    if body_sha != spec['network']['body_ids_sha256']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='network mismatch', body_ids_sha256=body_sha)
    ids = {k: dense(data, b) for k, b in spec['cells'].items()}
    controls = control_dns(data, m.net, ids)
    if controls != spec['controls']['dense_indices']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='control draw mismatch', controls=controls)
    started = time.time()

    def note(text):
        progress(f'[{time.time()-started:7.0f}s] {text}', flush=True)

    def condition(label, seeds, stim, silenced=()):
        runs = [m.replicate(s, stim, silenced) for s in seeds]
        out = dict(summary=summarize(runs), runs=runs)
        note(f"{label}: score {out['summary']['score']} freq {out['summary']['frequency_hz']} "
             f"feasible {out['summary']['feasible']}/{len(runs)}")
        return out

    c = spec['conditions']
    dng_seeds = range(1, c['dng100_seeds'] + 1)
    dng = condition('DNG100', dng_seeds, ids['DNg100_L'])
    silenced = {k: condition(f'SIL_{k}', dng_seeds, ids['DNg100_L'], [ids[cell]])
                for k, cell in (('E1', 'E1'), ('E2', 'E2'), ('I1', 'I1'))}
    ctl = {str(d): condition(f'CONTROL {data.instances[d]}', range(1, c['control_seeds'] + 1), d)
           for d in controls}
    baseline = condition('BASELINE', range(1, c['baseline_seeds'] + 1), None)
    v, details = verdict(dng['summary'], {k: x['summary'] for k, x in ctl.items()},
                         {k: x['summary'] for k, x in silenced.items()})
    s = m.size/m.size_ref
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict=v, **details,
                expectations=dict(P1=details.get('checks', {}).get('C1_rhythm'),
                                  P2=(not (silenced['I1']['summary']['score'] >= .5)),
                                  P3=details.get('checks', {}).get('C2_frequency')),
                network=dict(counts=m.counts, edges=m.edges, synapses=m.synapses, size_ref=m.size_ref,
                             size_ratio_over_20=int((s > 20).sum()), body_ids_sha256=body_sha,
                             front_left_mns_in_network=len(m.mn_local)),
                cells={k: dict(dense_index=i, body_id=int(data.body_ids[i])) for k, i in ids.items()},
                dng100=dng, silenced=silenced, controls=ctl, baseline=baseline, sources=sources,
                runtime_s=round(time.time()-started, 1), interpretation_limits=spec['interpretation_limits'])


CELLS = {'DNg100_L': 10045, 'DNg100_R': 10056, 'E1': 800173, 'E2': 800863, 'I1': 801884}


def dense(data, body_id):
    hit = np.flatnonzero(np.asarray(data.body_ids) == body_id)
    if len(hit) != 1:
        raise ValueError(f'body {body_id} not unique')
    return int(hit[0])


def control_dns(data, net, ids, count=20, seed=20261107):
    nt = np.asarray(data.neurotransmitter_ids)
    sup = np.asarray(data.superclass_ids)
    exclude = {ids['DNg100_L'], ids['DNg100_R']}
    pool = sorted(i for i in net if data.superclasses[sup[i]] == 'descending_neuron'
                  and data.neurotransmitters[nt[i]] == 'acetylcholine' and i not in exclude)
    return sorted(int(i) for i in np.random.default_rng(seed).choice(pool, count, replace=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--time-replicate', action='store_true',
                        help='plumbing: one DNg100 replicate with seed 0 (not a protocol seed); prints wall time only')
    parser.add_argument('--describe', action='store_true', help='print network counts, body-ID hash, controls')
    args = parser.parse_args(argv)
    if args.time_replicate or args.describe:
        data = load_cache(args.cache)
        t0 = time.time()
        m = Model(data)
        t1 = time.time()
        if args.describe:
            ids = {k: dense(data, b) for k, b in CELLS.items()}
            body = sorted(int(data.body_ids[i]) for i in m.net)
            print(json.dumps(clean(dict(counts=m.counts, edges=m.edges, synapses=m.synapses, size_ref=m.size_ref,
                                        mns_in_network=len(m.mn_local),
                                        body_ids_sha256=hashlib.sha256(json.dumps(body).encode()).hexdigest(),
                                        in_network={k: i in m.pos for k, i in ids.items()},
                                        controls=control_dns(data, m.net, {'DNg100_L': ids['DNg100_L'],
                                                                           'DNg100_R': ids['DNg100_R']}),
                                        sources={k: lf_sha(p) for k, p in SOURCE_FILES.items()})), indent=1))
        if args.time_replicate:
            t2 = time.time()
            info = m.replicate(0, dense(data, CELLS['DNg100_L']))
            print(json.dumps(dict(build_s=round(t1 - t0, 1), replicate_s=round(time.time() - t2, 1),
                                  simulations=len(info['history']))))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(clean(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(clean({k: result.get(k) for k in ('verdict', 'checks', 'control_p80', 'expectations',
                                                         'runtime_s')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
