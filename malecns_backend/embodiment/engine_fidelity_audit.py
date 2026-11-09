"""Engine fidelity audit Step F1: why does descending drive not reach the locomotor core?

Preregistered in docs/evidence/engine-fidelity-audit-v1/protocol.json. Neural only. Part A checks the
live LIF engine against its own references (defects). Part B swaps single declared rules toward the
rate model in model copies, as a diagnostic that is never adopted. Part C describes how both models
weight the inputs to E1, E2 and I1. The live engine is not changed.
"""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from ..cache import load_cache
from ..neural import MaleCNSBrain, ModelConfig, region_scales
from . import dng100_engaged_rhythm as r3
from . import dng100_rate_model as r1
from . import dng100_rhythm as v1
from . import lif_driver_rhythm as l1

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/engine-fidelity-audit-v1/protocol.json'
PROTOCOL_SHA256 = 'ebb68ffc3318e9d1f8fde02a30c981313176cc209e8894cb6900e866672237f0'
SCHEMA = 'engine-fidelity-audit-result-v1'
TEXT_SOURCES = {'neural_py_lf_sha256': 'malecns_backend/neural.py',
                'lif_js_lf_sha256': 'fly-brain-main/src/lif.js',
                'ratenet_js_lf_sha256': 'fly-brain-main/src/ratenet.js',
                'brain_params_lf_sha256': 'fly-brain-main/public/data/brain_params.json',
                'lif_driver_rhythm_py_lf_sha256': 'malecns_backend/embodiment/lif_driver_rhythm.py',
                'dng100_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_rhythm.py',
                'dng100_rate_model_py_lf_sha256': 'malecns_backend/embodiment/dng100_rate_model.py',
                'parity_test_lf_sha256': 'tests/test_calibrated_neural_parity.py',
                'parity_js_lf_sha256': 'tests/js/calibrated_lif_audit.mjs'}
BINARY_SOURCES = {'l1_protocol_json_sha256': 'docs/evidence/lif-driver-rhythm-v1/protocol.json',
                  'l1_result_json_sha256': 'docs/evidence/lif-driver-rhythm-v1/run/result.json',
                  'v1_protocol_json_sha256': 'docs/evidence/dng100-rhythm-v1/protocol.json',
                  'v1_result_json_sha256': 'docs/evidence/dng100-rhythm-v1/run/result.json'}
L1_RESULT = 'docs/evidence/lif-driver-rhythm-v1/run/result.json'
V1_RESULT = 'docs/evidence/dng100-rhythm-v1/run/result.json'
PARAM_KEYS = {'coba': 'conductance_based', 'wSyn': 'psp_scale', 'sizeAlpha': 'size_alpha',
              'kcThreshold': 'kc_threshold_offset', 'inhGain': 'inhibitory_gain', 'eInh': 'e_inh',
              'minSyn': 'min_synapses', 'adaptInc': 'adaptation_increment', 'tRef': 'refractory_ms',
              'laminaBias': 'lamina_bias', 'neuromod': 'neuromodulation'}
DNS = {'DNg100_L': 10045, 'DNg75_R': 520300, 'DNa02_L': 523769}             # body IDs
EXPECTED_DNS = {'DNg100_L': 36, 'DNg75_R': 129181, 'DNa02_L': 130496}
CORE = {'E1': 800173, 'E2': 800863, 'I1': 801884}                           # body IDs
EXPECTED_CORE = {'E1': 142920, 'E2': 143429, 'I1': 144200}
NET_SHA = 'cdcfcd231484a46c2a668d17932d95b2147ab16e7dd5c7f87857490590b12eed'
RATES = (100, 200)
SEEDS = range(1, 9)
GATED_DNS = ('DNg75_R', 'DNa02_L')
ENGAGED_HZ = 10.
ENGAGED_SEEDS = 5
FIELDS = {'S0_LIVE': {}, 'S1_ISOLATED': {}, 'S2_MINSYN5': {'min_synapses': 5},
          'S3_INHGAIN1': {'inhibitory_gain': 1.}, 'S4_BINARYSIGN': {'graded_sign': False},
          'S5_ALL': {'min_synapses': 5, 'inhibitory_gain': 1., 'graded_sign': False}}
ISOLATED = ('S1_ISOLATED', 'S5_ALL')
SINGLE = ('S1_ISOLATED', 'S2_MINSYN5', 'S3_INHGAIN1', 'S4_BINARYSIGN')
NEGATIVE = ('gaba', 'glutamate', 'histamine')
POSITIVE = ('acetylcholine', 'dopamine', 'serotonin')
BINARY = {'acetylcholine': 1., 'gaba': -1., 'glutamate': -1., 'dopamine': 1., 'serotonin': 1., 'octopamine': 1.,
          'histamine': -1.}
A_STAR, THETA_STAR = 1., 7.5                                                 # the preprint's means


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


class Edges:
    """Flat edge list of the whole graph (src, tgt, synapse count as float32)."""
    def __init__(self, data):
        rp = np.asarray(data.row_ptr)
        self.src = np.repeat(np.arange(data.neuron_count, dtype=np.int32), np.diff(rp))
        self.tgt = np.asarray(data.target_indices, np.int32)
        self.count = np.asarray(data.synapse_counts, np.float32)


def sensory_mask(data):
    table = np.array(['sensory' in n for n in data.superclasses], bool)
    return table[np.asarray(data.superclass_ids)]


def member_mask(n, net):
    m = np.zeros(n, bool)
    m[np.asarray(net, np.intp)] = True
    return m


# ---- Part A: the engine's documented rules, re-implemented independently -------------------------

def region_of(name):
    if name.startswith(('ol_', 'visual_projection', 'visual_centrifugal')):
        return 0
    if name.startswith(('vnc_', 'descending', 'ascending', 'sensory_ascending', 'sensory_descending', 'efferent_')):
        return 2
    return 1


def independent_factor(data, p):
    """Size factor by the documented rule: (size / region's upper-middle median) ** -alpha, clipped and capped."""
    table = np.array([region_of(n) for n in data.superclasses], np.uint8)
    region = table[np.asarray(data.superclass_ids)]
    size = np.array(data.neuron_sizes, np.float32)
    med = []
    for r in range(3):
        v = np.sort(size[(region == r) & (size > 0)])
        med.append(v[len(v)//2] if len(v) else 1.)
    med = np.asarray(med, np.float32)
    ratio = np.where(size > 0, size/med[region], 1)
    ratio = np.clip(ratio, 1/p.max_size_scale, p.max_size_scale)
    return np.minimum(p.boost_cap, ratio**-p.size_alpha).astype(np.float32), region, med


def independent_signs(data, p):
    sign = np.array(data.nt_signs, np.float32)
    if p.neuromodulation:
        sign[np.array([str(t).startswith('OA-') for t in data.types], bool)] = 0
    return sign


def binary_signs(data, p):
    """The transmitter-table sign (S4, S5): names, not ids, so a table-order error would be caught."""
    nt = np.asarray(data.neurotransmitter_ids)
    table = np.array([BINARY.get(str(n).lower(), 0.) for n in data.neurotransmitters], np.float32)
    sign = table[nt]
    if p.neuromodulation:
        sign[np.array([str(t).startswith('OA-') for t in data.types], bool)] = 0
    return sign


def expected_weights(data, p, E, sign, factor=None):
    """Whole-graph weights by the documented rule."""
    factor = independent_factor(data, p)[0] if factor is None else factor
    sensory = sensory_mask(data)
    w = np.where((E.count >= p.min_synapses) & ~sensory[E.tgt], E.count*factor[E.tgt], 0).astype(np.float32)
    neg = sign[E.src] < 0
    if p.inhibitory_gain != 1:
        w[neg] = w[neg]*np.float32(p.inhibitory_gain)
    return w


def a1_config(params, config, built):
    bad = {k: (v, getattr(config, f)) for k, f in PARAM_KEYS.items() for v in [params[k]] if getattr(config, f) != v}
    return dict(passed=not bad and built == config, mismatches=bad, keys=len(PARAM_KEYS))


def a2_parity():
    done = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/test_calibrated_neural_parity.py'], cwd=ROOT,
                          capture_output=True, text=True)
    return dict(passed=done.returncode == 0, returncode=done.returncode, tail=done.stdout.strip().splitlines()[-1:])


def a3_weights(data, brain, p, E, targets):
    keep = np.isin(E.tgt, np.asarray(targets, np.int32))
    want = expected_weights(data, p, E, independent_signs(data, p))[keep]
    got = np.asarray(brain.weights)[keep]
    wrong = np.flatnonzero(want != got)
    return dict(passed=len(wrong) == 0, edges=int(keep.sum()), mismatches=int(len(wrong)),
                nonzero=int(np.count_nonzero(got)))


def a4_signs(data, pre_sign, net):
    """Known transmitters only: the data's graded signs are documented for neurons without a consensus call."""
    nt = np.asarray(data.neurotransmitter_ids)
    bad, counts = [], dict(oa_type=0, negative=0, positive=0, unknown=0, other=0)
    magnitude = []
    for i in net:
        name, s = str(data.neurotransmitters[nt[i]]).lower(), float(pre_sign[i])
        if str(data.types[i]).startswith('OA-'):
            counts['oa_type'] += 1
            ok = s == 0
        elif name in NEGATIVE:
            counts['negative'] += 1
            ok = s < 0
            magnitude.append(abs(s))
        elif name in POSITIVE:
            counts['positive'] += 1
            ok = s > 0
            magnitude.append(abs(s))
        else:
            counts['unknown' if name == 'unknown' else 'other'] += 1
            ok = True
        if not ok:
            bad.append(dict(dense=int(i), body_id=int(data.body_ids[i]), transmitter=name, sign=s))
    m = np.asarray(magnitude, float)
    return dict(passed=not bad, counts=counts, mismatches=len(bad), first_mismatches=bad[:20],
                known_magnitude=dict(n=len(m), at_one=int(np.count_nonzero(m == 1)), min=float(m.min()) if len(m) else None))


def a5_sizes(data, p, net):
    factor, region, med = independent_factor(data, p)
    scale, engine_region, engine_med = region_scales(data, p)
    idx = np.asarray(net, np.intp)
    names = np.array(list(data.superclasses))[np.asarray(data.superclass_ids)]
    expect_vnc = np.char.find(names, 'descending') >= 0
    expect_vnc |= np.char.find(names, 'ascending') >= 0
    expect_vnc |= np.char.startswith(names, 'vnc_') | np.char.startswith(names, 'efferent_')
    outside = np.flatnonzero(expect_vnc & (engine_region != 2))
    net_other = idx[engine_region[idx] != 2]
    checks = dict(factor=bool(np.array_equal(factor[idx], scale[idx])), medians=bool(np.array_equal(med, engine_med)),
                  regions=bool(np.array_equal(region, engine_region)), vnc_in_region_2=len(outside) == 0)
    return dict(passed=all(checks.values()), checks=checks, medians=[float(x) for x in engine_med],
                vnc_outside_region_2=int(len(outside)), network_neurons_not_region_2=int(len(net_other)),
                network_not_region_2_superclasses=sorted(set(str(names[i]) for i in net_other)))


def a6_identities(data, dns, core, mns, l1_mns):
    return dict(passed=bool(dns == EXPECTED_DNS and core == EXPECTED_CORE and sorted(mns) == sorted(l1_mns) and len(mns) == 68),
                dns=dns, core=core, mns=len(mns))


def a7_mask(data, brain, p, E, net):
    sensory, weights = sensory_mask(data), np.asarray(brain.weights)
    onto = sensory[E.tgt]
    eligible = E.count >= p.min_synapses
    inside = member_mask(data.neuron_count, net)
    in_net = inside[E.src] & inside[E.tgt]
    checks = dict(sensory_targets_zero=bool(np.all(weights[onto] == 0)),
                  others_nonzero=bool(np.all(weights[eligible & ~onto] != 0)))
    return dict(passed=all(checks.values()), checks=checks, removed_whole_graph=int((eligible & onto).sum()),
                removed_in_network=int((eligible & onto & in_net).sum()))


def part_a_label(checks):
    return 'NO_DEFECT_FOUND' if all(c['passed'] for c in checks.values()) else 'DEFECT_FOUND'


# ---- Part B: declared rule swaps in model copies ---------------------------------------------------

def config_for(name):
    return replace(ModelConfig.calibrated(), **FIELDS[name])


def isolated_weights(data, p, E, net):
    """Pre-gain weights (the constructor applies the inhibitory gain), edges outside the network zeroed."""
    scale = region_scales(data, p)[0]
    sensory = sensory_mask(data)
    w = np.where((E.count >= p.min_synapses) & ~sensory[E.tgt], E.count*scale[E.tgt], 0).astype(np.float32)
    inside = member_mask(data.neuron_count, net)
    w[~(inside[E.src] & inside[E.tgt])] = 0
    return w


def build(data, name, E, net):
    p = config_for(name)
    if name in ISOLATED:
        return MaleCNSBrain(data, p, effective_weights=isolated_weights(data, p, E, net))
    return MaleCNSBrain(data, p)


def swap_audit(name, brain, live_w, live_sign, data, E, net):
    """Z3: this config differs from LIVE only in its declared rule."""
    p, base = brain.config, ModelConfig.calibrated()
    fields = {k for k, v in asdict(p).items() if asdict(base)[k] != v}
    w, sign = np.asarray(brain.weights), np.asarray(brain.pre_sign)
    changed = w != live_w
    inside = member_mask(data.neuron_count, net)
    in_net = inside[E.src] & inside[E.tgt]
    sensory = sensory_mask(data)
    if name == 'S0_LIVE':
        ok = not changed.any() and np.array_equal(sign, live_sign)
    elif name == 'S1_ISOLATED':
        ok = np.array_equal(sign, live_sign) and np.array_equal(w[in_net], live_w[in_net]) and not w[~in_net].any()
    elif name == 'S2_MINSYN5':
        ok = np.array_equal(sign, live_sign) and np.array_equal(changed, (E.count == 5) & ~sensory[E.tgt])
    elif name == 'S3_INHGAIN1':
        ok = np.array_equal(sign, live_sign) and np.array_equal(changed, (live_w != 0) & (live_sign[E.src] < 0))
    elif name == 'S4_BINARYSIGN':
        ok = (np.array_equal(sign, binary_signs(data, p))
              and np.array_equal(changed, (live_w != 0) & ((live_sign[E.src] < 0) != (sign[E.src] < 0))))
    else:
        factor = region_scales(data, p)[0]
        want = np.where(in_net & (E.count >= 5) & ~sensory[E.tgt], E.count*factor[E.tgt], 0).astype(np.float32)
        ok = np.array_equal(sign, binary_signs(data, p)) and np.array_equal(w, want)
    return dict(passed=bool(ok and fields == set(FIELDS[name])), config_fields=sorted(fields),
                changed_weights=int(changed.sum()), changed_signs=int(np.count_nonzero(sign != live_sign)))


def cell_engaged(runs, bar=ENGAGED_HZ, need=ENGAGED_SEEDS):
    n = sum(r['core']['E1']['mean_hz'] >= bar and r['core']['E2']['mean_hz'] >= bar for r in runs)
    return n >= need, n


def gate_s0(table, l1res):
    bad, checked = [], 0
    for t in GATED_DNS:
        stored = {l['rate_hz']: {r['seed']: r for r in l['runs']} for l in l1res['targets'][t]['levels']}
        for rate in RATES:
            for run in table[t][str(rate)]:
                want = stored[rate][run['seed']]
                checked += 1
                if not (r3.same(run['score'], want['score']) and run['mn_spikes'] == want['mn_spikes']):
                    bad.append(dict(dn=t, rate=rate, seed=run['seed']))
    return dict(passed=not bad and checked == len(GATED_DNS)*len(RATES)*len(SEEDS), checked=checked, mismatches=bad)


def dn_engaged(by_config):
    """{config: {dn: {rate: runs}}} -> {config: {dn: True/False}}."""
    return {c: {d: any(cell_engaged(runs)[0] for runs in rates.values()) for d, rates in dns.items()}
            for c, dns in by_config.items()}


def part_b_label(engaged, gate_ok=True, audits_ok=True):
    """A DN the live engine already engages cannot show that a swap is what engages it."""
    if not gate_ok or not audits_ok:
        return 'INCONCLUSIVE', dict(reason='gate or swap audit failed')
    open_dns = [d for d, on in engaged['S0_LIVE'].items() if not on]
    detail = dict(already_engaged_in_live=[d for d, on in engaged['S0_LIVE'].items() if on], open_dns=open_dns)
    if not open_dns:
        return 'INCONCLUSIVE', dict(detail, reason='every DN already engaged in LIVE')
    single = sorted(c for c in SINGLE if any(engaged[c][d] for d in open_dns))
    detail['engaging_single_rules'] = single
    if single:
        return 'SINGLE_RULE_ENGAGES', detail
    if any(engaged['S5_ALL'][d] for d in open_dns):
        return 'COMBINATION_ONLY', detail
    return 'NOT_THESE_RULES', detail


# ---- Part C: description ------------------------------------------------------------------------------

def part_c(data, brain, E, net, dns, core):
    p = brain.config
    scale = region_scales(data, p)[0]
    ref = r1.vnc_size_median(data)
    size = np.asarray(data.neuron_sizes, float)
    s = np.where(size > 0, size/ref, 1.)
    inside = member_mask(data.neuron_count, net)
    known_sign = binary_signs(replace_oa_free(data), p)
    w, sign = np.asarray(brain.weights, float), np.asarray(brain.pre_sign, float)
    eff = w*sign[E.src]*p.psp_scale
    rate_gate = (E.count >= 5) & inside[E.src] & inside[E.tgt]
    rate_w = np.where(rate_gate, r1.B*known_sign[E.src]*E.count/(THETA_STAR*s[E.tgt]**2)*A_STAR, 0.)
    row = np.asarray(data.row_ptr)

    def describe(k):
        return dict(body_id=int(data.body_ids[k]), instance=str(data.instances[k]))

    out = {}
    for cname, c in core.items():
        into = np.flatnonzero(E.tgt == c)
        src = E.src[into]
        live_in, rate_in = dict(zip(src.tolist(), eff[into].tolist())), dict(zip(src.tolist(), rate_w[into].tolist()))
        net_src = inside[src]
        e = eff[into]
        cell = dict(body_id=int(data.body_ids[c]), lif_size_factor=float(scale[c]), size_ratio_s=float(s[c]),
                    rate_gain=A_STAR/float(s[c]), rate_threshold=THETA_STAR*float(s[c]),
                    floor_edges=dict(dropped_by_6_kept_by_5=int((E.count[into] == 5).sum()),
                                     of_which_in_network=int(((E.count[into] == 5) & net_src).sum())),
                    input_load_mv=dict(exc_in_network=float(e[net_src & (e > 0)].sum()),
                                       inh_in_network=float(e[net_src & (e < 0)].sum()),
                                       exc_outside=float(e[~net_src & (e > 0)].sum()),
                                       inh_outside=float(e[~net_src & (e < 0)].sum())),
                    dns={})
        for dname, d in dns.items():
            first = np.arange(row[d], row[d + 1])
            live_top, rate_top = [], []
            direct_live, direct_rate = 0., 0.
            for k in first:
                m = int(E.tgt[k])
                if m == c:
                    direct_live, direct_rate = float(eff[k]), float(rate_w[k])
                elif m in live_in:
                    if eff[k] and live_in[m]:
                        live_top.append((float(eff[k])*live_in[m], m))
                    if rate_w[k] and rate_in[m]:
                        rate_top.append((float(rate_w[k])*rate_in[m], m))
            top = lambda xs: [dict(describe(m), score=v) for v, m in sorted(xs, key=lambda x: -abs(x[0]))[:5]]
            cell['dns'][dname] = dict(direct_lif_psp_mv=direct_live, direct_rate_term=direct_rate,
                                      top_2hop_lif=top(live_top), top_2hop_rate=top(rate_top))
        out[cname] = cell
    return out


def replace_oa_free(data):
    """Part C's rate-model sign has no OA rule; a view of data with no OA-type names."""
    class View:
        neurotransmitter_ids = data.neurotransmitter_ids
        neurotransmitters = data.neurotransmitters
        types = [''] * data.neuron_count
    return View


# ---- run -------------------------------------------------------------------------------------------------

def run_cell(brain, spec, d, rate, seed, mns, core, net=None):
    r = l1.one(brain, spec, d, rate, seed, mns, core)
    r.pop('mn_detail')
    counts = np.asarray(brain.spike_counts)
    part = counts if net is None else counts[np.asarray(net, np.intp)]
    r['active_fraction'] = float(np.count_nonzero(part)/len(part))
    return r


def dense_of(data, body):
    return l1.dense_of(data, body)


def summary(by_config):
    out = {}
    for c, dns in by_config.items():
        out[c] = {}
        for d, rates in dns.items():
            out[c][d] = {}
            for rate, runs in rates.items():
                on, n = cell_engaged(runs)
                out[c][d][rate] = dict(engaged=on, engaged_seeds=n,
                                       median_hz={k: float(np.median([r['core'][k]['mean_hz'] for r in runs])) for k in CORE},
                                       median_active_mns=float(np.median([r['active_mns'] for r in runs])),
                                       median_active_fraction=float(np.median([r['active_fraction'] for r in runs])))
    return out


def run(cache, progress=print):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, status='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    meta = json.loads((Path(cache)/'metadata.json').read_text())
    fp = hashlib.sha256(json.dumps(meta['source'], sort_keys=True).encode()).hexdigest()
    if fp != spec['sources']['cache_source_fingerprints_sha256']:
        return dict(schema=SCHEMA, status='INCONCLUSIVE', reason='cache fingerprint mismatch', sources=src)
    v1spec = v1.protocol()
    l1res = json.loads((ROOT/L1_RESULT).read_bytes())
    v1res = json.loads((ROOT/V1_RESULT).read_bytes())
    data = load_cache(cache)
    mns = v1.front_left_mns(data.bodymap)
    net = r1.build_network(data, mns)[0]
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in net)).encode()).hexdigest()
    if body_sha != NET_SHA:
        return dict(schema=SCHEMA, status='INCONCLUSIVE', reason='network membership mismatch', sources=src)
    dns = {k: dense_of(data, b) for k, b in DNS.items()}
    core = {k: dense_of(data, b) for k, b in CORE.items()}
    started = time.time()

    def note(text):
        progress(f'[{time.time()-started:7.0f}s] {text}', flush=True)

    E = Edges(data)
    live = MaleCNSBrain(data)
    p = ModelConfig.calibrated()
    params = json.loads((ROOT/'fly-brain-main/public/data/brain_params.json').read_text())
    checks = dict(A1=a1_config(params, p, live.config), A2=a2_parity(),
                  A3=a3_weights(data, live, p, E, list(core.values()) + list(mns)),
                  A4=a4_signs(data, live.pre_sign, net), A5=a5_sizes(data, p, net),
                  A6=a6_identities(data, dns, core, mns, v1res['front_left_mns']),
                  A7=a7_mask(data, live, p, E, net))
    a_label = part_a_label(checks)
    note(f'Part A: {a_label}')
    c = part_c(data, live, E, net, dns, core)
    note('Part C done')
    live_w, live_sign = np.array(live.weights), np.array(live.pre_sign)
    del live
    by_config, audits, total = {}, {}, 0
    for name in FIELDS:
        brain = build(data, name, E, net)
        audits[name] = swap_audit(name, brain, live_w, live_sign, data, E, net)
        note(f'{name} audit: {audits[name]["passed"]} changed weights {audits[name]["changed_weights"]}')
        by_config[name] = {}
        scope = net if name in ISOLATED else None
        for dn, d in dns.items():
            by_config[name][dn] = {}
            for rate in RATES:
                by_config[name][dn][str(rate)] = [run_cell(brain, v1spec, d, rate, s, mns, core, scope) for s in SEEDS]
                total += len(SEEDS)
            note(f'{name} {dn} done')
        del brain
        if name == 'S0_LIVE':
            gate = gate_s0(by_config['S0_LIVE'], l1res)
            note(f'S0 gate: {gate["passed"]}')
            if not gate['passed']:
                break
    complete = total == len(FIELDS)*len(DNS)*len(RATES)*len(SEEDS) and v1spec['stimulus']['duration_ms'] == 3000
    audits_ok = all(a['passed'] for a in audits.values())
    if complete:
        b_label, detail = part_b_label(dn_engaged(by_config), gate['passed'], audits_ok)
    else:
        b_label, detail = 'INCONCLUSIVE', dict(reason='incomplete')
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, part_a=a_label, part_b=b_label, part_b_detail=detail,
                expectations=dict(XA=a_label == 'NO_DEFECT_FOUND', XB=b_label == 'NOT_THESE_RULES'),
                checks=checks, part_c=c, cells=summary(by_config), runs=by_config,
                integrity=dict(Z1=dict(passed=True, network_body_ids_sha256=body_sha, cache_fingerprints_sha256=fp),
                               Z2=gate, Z3=dict(passed=audits_ok, audits=audits),
                               Z4=dict(passed=complete, simulations=total)),
                sources=src, runtime_s=round(time.time() - started, 1), interpretation_limits=spec['interpretation_limits'])


def headline(r):
    return {k: r.get(k) for k in ('status', 'reason', 'part_a', 'part_b', 'part_b_detail', 'expectations', 'runtime_s')}


def smoke(cache):
    """Plumbing only: S1, DNg75_R, 100 Hz, seed 0 (not a protocol seed). Exit status and swap audit are read."""
    data = load_cache(cache)
    mns = v1.front_left_mns(data.bodymap)
    net = r1.build_network(data, mns)[0]
    E = Edges(data)
    live = MaleCNSBrain(data)
    live_w, live_sign = np.array(live.weights), np.array(live.pre_sign)
    p = ModelConfig.calibrated()                # the Part A and C functions run so a crash shows now; output discarded
    dns = {k: dense_of(data, b) for k, b in DNS.items()}
    cells = {k: dense_of(data, b) for k, b in CORE.items()}
    a3_weights(data, live, p, E, list(cells.values()) + list(mns)), a4_signs(data, live.pre_sign, net)
    a5_sizes(data, p, net), a7_mask(data, live, p, E, net), part_c(data, live, E, net, dns, cells)
    del live
    brain = build(data, 'S1_ISOLATED', E, net)
    audit = swap_audit('S1_ISOLATED', brain, live_w, live_sign, data, E, net)
    core = {k: dense_of(data, b) for k, b in CORE.items()}
    t = time.time()
    run_cell(brain, v1.protocol(), dense_of(data, DNS['DNg75_R']), 100, 0, mns, core, net)
    print(json.dumps(dict(status='SMOKE', swap_audit=audit, one_simulation_s=round(time.time() - t, 1)), indent=1))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args(argv)
    if args.smoke:
        return smoke(args.cache)
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(v1.clean(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(v1.clean(headline(result)), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
