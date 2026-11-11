"""Engine fidelity Step F2: what outside the front-left network keeps DNg100_L's core active?

Preregistered in docs/evidence/core-support-map-v1/protocol.json. Neural only. DNg100_L is driven at
100 Hz in the live, calibrated whole-CNS LIF engine (F1's harness). The CNS outside R1's network is
split by superclass into seven groups; each is removed (outgoing weights zeroed: necessity) or kept
alone with the network (sufficiency) in model copies. The live engine is not changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from ..cache import load_cache
from ..neural import MaleCNSBrain, ModelConfig, region_scales
from . import dng100_engaged_rhythm as r3
from . import dng100_rate_model as r1
from . import dng100_rhythm as v1
from . import engine_fidelity_audit as f1
from . import lif_driver_rhythm as l1

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/core-support-map-v1/protocol.json'
PROTOCOL_SHA256 = '60359bb6009cd6a85e211d00b41a26217f42e5ecf00543f01cb3b4a290901c7d'
SCHEMA = 'core-support-map-result-v1'
TEXT_SOURCES = {'neural_py_lf_sha256': 'malecns_backend/neural.py',
                'brain_params_lf_sha256': 'fly-brain-main/public/data/brain_params.json',
                'lif_driver_rhythm_py_lf_sha256': 'malecns_backend/embodiment/lif_driver_rhythm.py',
                'dng100_rhythm_py_lf_sha256': 'malecns_backend/embodiment/dng100_rhythm.py',
                'dng100_rate_model_py_lf_sha256': 'malecns_backend/embodiment/dng100_rate_model.py',
                'engine_fidelity_audit_py_lf_sha256': 'malecns_backend/embodiment/engine_fidelity_audit.py'}
BINARY_SOURCES = {'f1_protocol_json_sha256': 'docs/evidence/engine-fidelity-audit-v1/protocol.json',
                  'f1_result_json_sha256': 'docs/evidence/engine-fidelity-audit-v1/run/result.json',
                  'v1_protocol_json_sha256': 'docs/evidence/dng100-rhythm-v1/protocol.json'}
F1_RESULT = 'docs/evidence/engine-fidelity-audit-v1/run/result.json'
DRIVER = ('DNg100_L', 10045, 36)                                            # name, body ID, dense index
RATE = 100
SEEDS = range(1, 9)
GROUPS = ('OPTIC', 'BRAIN', 'VNC', 'AN', 'DN', 'SENSORY', 'OTHER')
GROUP_SIZES = {'OPTIC': 99156, 'BRAIN': 32343, 'VNC': 12941, 'AN': 1749, 'DN': 414, 'SENSORY': 15845, 'OTHER': 563}
NETWORK_SIZE = 2111
CONDITIONS = (('LIVE', 'LIVE_VIA_WEIGHTS', 'ISOLATED') + tuple(f'MINUS_{g}' for g in GROUPS)
              + tuple(f'ONLY_{g}' for g in GROUPS))


def sources():
    return {**{k: f1.lf_sha(p) for k, p in TEXT_SOURCES.items()}, **{k: f1.raw_sha(p) for k, p in BINARY_SOURCES.items()}}


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


# ---- groups --------------------------------------------------------------------------------------

def group_of(superclass):
    if 'sensory' in superclass:
        return 'SENSORY'
    if superclass.startswith(('ol_', 'visual_')):
        return 'OPTIC'
    if superclass.startswith('cb_'):
        return 'BRAIN'
    if superclass in ('descending_neuron', 'efferent_descending'):
        return 'DN'
    if superclass in ('ascending_neuron', 'efferent_ascending'):
        return 'AN'
    if superclass.startswith('vnc_'):
        return 'VNC'
    return 'OTHER'


def group_ids(data, net):
    """Per neuron: -1 for the network, else the index of its group in GROUPS."""
    table = np.array([GROUPS.index(group_of(n)) for n in data.superclasses], np.int8)
    out = table[np.asarray(data.superclass_ids)]
    out[np.asarray(net, np.intp)] = -1
    return out


def group_sizes(grp):
    return dict(NETWORK=int((grp == -1).sum()), **{g: int((grp == i).sum()) for i, g in enumerate(GROUPS)})


# ---- conditions ----------------------------------------------------------------------------------

def pre_gain_weights(data, p, E):
    """The constructor's weight rule before the inhibitory gain (which the constructor applies)."""
    scale = region_scales(data, p)[0]
    sensory = f1.sensory_mask(data)
    return np.where((E.count >= p.min_synapses) & ~sensory[E.tgt], E.count*scale[E.tgt], 0).astype(np.float32)


def kept_edges(name, E, grp):
    """Boolean mask of edges a condition keeps (None for LIVE, which uses the normal constructor)."""
    if name in ('LIVE', 'LIVE_VIA_WEIGHTS'):
        return np.ones(len(E.src), bool)
    if name == 'ISOLATED':
        inside = grp == -1
        return inside[E.src] & inside[E.tgt]
    kind, g = name.split('_', 1)
    gi = GROUPS.index(g)
    if kind == 'MINUS':
        return grp[E.src] != gi
    inside = (grp == -1) | (grp == gi)
    return inside[E.src] & inside[E.tgt]


def build(data, name, E, grp, base):
    p = ModelConfig.calibrated()
    if name == 'LIVE':
        return MaleCNSBrain(data, p)
    w = base.copy()                     # the constructor scales this array in place; never pass `base` itself
    w[~kept_edges(name, E, grp)] = 0
    return MaleCNSBrain(data, p, effective_weights=w)


def lesion_audit(name, brain, live_w, live_sign, E, grp):
    """Z3: weights equal LIVE's on kept edges and are zero on removed edges; signs and config unchanged."""
    keep = kept_edges(name, E, grp)
    w = np.asarray(brain.weights)
    ok = (np.array_equal(w[keep], live_w[keep]) and not w[~keep].any()
          and np.array_equal(np.asarray(brain.pre_sign), live_sign) and brain.config == ModelConfig.calibrated())
    return dict(passed=bool(ok), removed_edges=int((~keep).sum()), changed_weights=int(np.count_nonzero(w != live_w)))


# ---- readout and criteria -------------------------------------------------------------------------

def run_one(brain, spec, d, seed, mns, core, grp):
    r = l1.one(brain, spec, d, RATE, seed, mns, core)
    r.pop('mn_detail')
    counts = np.asarray(brain.spike_counts)
    on = counts > 0
    r['active_fraction'] = float(np.count_nonzero(counts)/len(counts))
    r['network_active_fraction'] = float(np.count_nonzero(on[grp == -1])/np.count_nonzero(grp == -1))
    r['active_neurons'] = dict(NETWORK=int(on[grp == -1].sum()), **{g: int(on[grp == i].sum()) for i, g in enumerate(GROUPS)})
    return r


def norm(x):
    """JSON-normalised copy (NaN -> None), so in-memory runs compare with stored ones and with each other."""
    return json.loads(json.dumps(v1.clean(x), allow_nan=False))


def same_run(a, b, fields=('score', 'mn_spikes', 'core')):
    a, b = norm(a), norm(b)
    for k in fields:
        if k == 'score':
            if not r3.same(a['score'], b['score']):
                return False
        elif a[k] != b[k]:
            return False
    return True


def same_runs(mine, ref, fields=('score', 'mn_spikes', 'core')):
    ref = {r['seed']: r for r in ref}
    bad = [r['seed'] for r in mine if r['seed'] not in ref or not same_run(r, ref[r['seed']], fields)]
    return dict(passed=not bad and len(mine) == len(ref), checked=len(mine), mismatches=bad)


def gates(table, f1res):
    """Z2: LIVE = F1 S0, ISOLATED = F1 S1 (incl. F1's network-only active fraction), LIVE_VIA_WEIGHTS = LIVE."""
    out = {}
    if 'LIVE' in table:
        ref = f1res['runs']['S0_LIVE']['DNg100_L'][str(RATE)]
        out['LIVE'] = same_runs(table['LIVE'], ref, ('score', 'mn_spikes', 'core', 'active_fraction'))
    if 'LIVE_VIA_WEIGHTS' in table:
        out['LIVE_VIA_WEIGHTS'] = same_runs(table['LIVE_VIA_WEIGHTS'], table['LIVE'],
                                            ('score', 'mn_spikes', 'core', 'active_fraction', 'active_neurons'))
    if 'ISOLATED' in table:
        ref = [dict(r, network_active_fraction=r['active_fraction'])
               for r in f1res['runs']['S1_ISOLATED']['DNg100_L'][str(RATE)]]
        out['ISOLATED'] = same_runs(table['ISOLATED'], ref, ('score', 'mn_spikes', 'core', 'network_active_fraction'))
    return out


def engaged(table):
    return {c: f1.cell_engaged(runs)[0] for c, runs in table.items()}


def label(eng, gates_ok=True, audits_ok=True, complete=True):
    if not (gates_ok and audits_ok and complete):
        return 'INCONCLUSIVE', dict(reason='gate, lesion audit or completeness failed')
    if not eng['LIVE']:
        return 'INCONCLUSIVE', dict(reason='LIVE not engaged')
    needed = [g for g in GROUPS if not eng[f'MINUS_{g}']]
    sufficient = [g for g in GROUPS if eng[f'ONLY_{g}']]
    detail = dict(needed=needed, sufficient=sufficient, localised=[g for g in needed if g in sufficient],
                  nonmonotonic=[dict(sufficient=x, needed=y) for x in sufficient for y in needed if x != y])
    if detail['localised']:
        return 'LOCALISED', detail
    if needed:
        return 'NEEDED_NOT_SUFFICIENT', detail
    if sufficient:
        return 'REDUNDANT', detail
    return 'DISTRIBUTED', detail


def sham(table):
    fields = ('score', 'mn_spikes', 'core', 'active_fraction', 'active_neurons')
    return dict(minus_equals_live=same_runs(table['MINUS_SENSORY'], table['LIVE'], fields)['passed'],
                only_equals_isolated=same_runs(table['ONLY_SENSORY'], table['ISOLATED'], fields)['passed'],
                sensory_active_in_live=max(r['active_neurons']['SENSORY'] for r in table['LIVE']))


def expectations(lab, detail, sh):
    return dict(X1='VNC' in detail.get('needed', []), X2=lab == 'LOCALISED' and 'VNC' in detail.get('localised', []),
                X3=bool(sh and sh['minus_equals_live'] and sh['only_equals_isolated']))


def summary(table):
    out = {}
    for c, runs in table.items():
        on, n = f1.cell_engaged(runs)
        out[c] = dict(engaged=on, engaged_seeds=n,
                      median_hz={k: float(np.median([r['core'][k]['mean_hz'] for r in runs])) for k in f1.CORE},
                      median_active_mns=float(np.median([r['active_mns'] for r in runs])),
                      median_active_fraction=float(np.median([r['active_fraction'] for r in runs])),
                      median_active_neurons={g: float(np.median([r['active_neurons'][g] for r in runs]))
                                             for g in ('NETWORK',) + GROUPS})
    return out


# ---- run -------------------------------------------------------------------------------------------

def setup(cache):
    data = load_cache(cache)
    mns = v1.front_left_mns(data.bodymap)
    net = r1.build_network(data, mns)[0]
    return data, mns, net


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
    f1res = json.loads((ROOT/F1_RESULT).read_bytes())
    data, mns, net = setup(cache)
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in net)).encode()).hexdigest()
    grp = group_ids(data, net)
    sizes = group_sizes(grp)
    d = f1.dense_of(data, DRIVER[1])
    core = {k: f1.dense_of(data, b) for k, b in f1.CORE.items()}
    z1 = dict(passed=bool(body_sha == f1.NET_SHA and sizes == dict(NETWORK=NETWORK_SIZE, **GROUP_SIZES)
                          and d == DRIVER[2] and core == f1.EXPECTED_CORE and len(mns) == 68),
              network_body_ids_sha256=body_sha, group_sizes=sizes, driver=d, core=core, cache_fingerprints_sha256=fp)
    if not z1['passed']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, status='INCONCLUSIVE', reason='Z1 failed',
                    integrity=dict(Z1=z1), sources=src)
    started = time.time()

    def note(text):
        progress(f'[{time.time()-started:7.0f}s] {text}', flush=True)

    E = f1.Edges(data)
    base = pre_gain_weights(data, ModelConfig.calibrated(), E)
    live_w = live_sign = None
    table, audits, total, stop = {}, {}, 0, None
    for name in CONDITIONS:
        brain = build(data, name, E, grp, base)
        if name == 'LIVE':
            live_w, live_sign = np.array(brain.weights), np.array(brain.pre_sign)
        audits[name] = lesion_audit(name, brain, live_w, live_sign, E, grp)
        table[name] = [run_one(brain, v1spec, d, s, mns, core, grp) for s in SEEDS]
        total += len(SEEDS)
        del brain
        on, n = f1.cell_engaged(table[name])
        note(f'{name}: audit {audits[name]["passed"]} engaged {on} ({n}/8)')
        if name in ('LIVE', 'LIVE_VIA_WEIGHTS', 'ISOLATED'):
            g = gates(table, f1res)[name]
            note(f'{name} gate: {g["passed"]}')
            if not g['passed']:
                stop = name
                break
    z2 = gates(table, f1res)
    gates_ok = stop is None and all(g['passed'] for g in z2.values()) and len(z2) == 3
    audits_ok = all(a['passed'] for a in audits.values())
    complete = total == len(CONDITIONS)*len(SEEDS) and v1spec['stimulus']['duration_ms'] == 3000
    eng = engaged(table) if complete else None
    lab, detail = label(eng, gates_ok, audits_ok, complete) if complete else ('INCONCLUSIVE', dict(reason='incomplete'))
    sh = sham(table) if complete else None
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, label=lab, detail=detail,
                expectations=expectations(lab, detail, sh) if complete else None, sham=sh,
                cells=summary(table), runs=table,
                integrity=dict(Z1=z1, Z2=dict(passed=gates_ok, gates=z2), Z3=dict(passed=audits_ok, audits=audits),
                               Z4=dict(passed=complete, simulations=total)),
                sources=src, runtime_s=round(time.time() - started, 1), interpretation_limits=spec['interpretation_limits'])


def headline(r):
    return {k: r.get(k) for k in ('status', 'reason', 'label', 'detail', 'expectations', 'sham', 'runtime_s')}


def smoke(cache):
    """Plumbing only: MINUS_VNC, seed 0 (not a protocol seed). Exit status and lesion audit are read."""
    data, mns, net = setup(cache)
    grp = group_ids(data, net)
    E = f1.Edges(data)
    base = pre_gain_weights(data, ModelConfig.calibrated(), E)
    live = build(data, 'LIVE', E, grp, base)
    live_w, live_sign = np.array(live.weights), np.array(live.pre_sign)
    del live
    brain = build(data, 'MINUS_VNC', E, grp, base)
    audit = lesion_audit('MINUS_VNC', brain, live_w, live_sign, E, grp)
    core = {k: f1.dense_of(data, b) for k, b in f1.CORE.items()}
    t = time.time()
    run_one(brain, v1.protocol(), f1.dense_of(data, DRIVER[1]), 0, mns, core, grp)
    print(json.dumps(dict(status='SMOKE', lesion_audit=audit, one_simulation_s=round(time.time() - t, 1)), indent=1))
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
