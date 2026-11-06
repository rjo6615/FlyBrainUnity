"""Rhythm Step R1b: does R1's whole-CNS size scaling match the preprint's nerve-cord-only scaling?

Preregistered in docs/evidence/dng100-size-audit-v1/protocol.json. Structure only: no neural
simulation, no engine, calibration, mapping or admission change. Skeletons are decoded by the
checked-in fly-brain-main decodeSkel (through skeleton_dump.mjs); R1's network rule is reused from
dng100_rate_model and the median rule from neural.region_scales.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from ..cache import load_cache
from ..neural import ModelConfig, region_scales
from .dng100_rate_model import build_network, dense
from .dng100_rhythm import clean, front_left_mns

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/dng100-size-audit-v1/protocol.json'
PROTOCOL_SHA256 = '3813e57746be8973a0930c4b11b641edabf94f990fb5ec3e34925398f234ef55'
SCHEMA = 'dng100-size-audit-result-v1'
DUMP = 'malecns_backend/embodiment/skeleton_dump.mjs'
SKELETONS = 'fly-brain-main/public/data/skeletons.flys'
TEXT_SOURCES = {'skel_js_lf_sha256': 'fly-brain-main/src/codec/skel.js',
                'rc_js_lf_sha256': 'fly-brain-main/src/codec/rc.js',
                'skeleton_dump_mjs_lf_sha256': DUMP,
                'meta_json_lf_sha256': 'fly-brain-main/public/data/meta.json',
                'dng100_rate_model_py_lf_sha256': 'malecns_backend/embodiment/dng100_rate_model.py',
                'neural_py_lf_sha256': 'malecns_backend/neural.py'}
BINARY_SOURCES = {'skeletons_flys_sha256': SKELETONS,
                  'neuron_size_bin_sha256': 'fly-brain-main/public/data/neuron_size.bin',
                  'neurons_bin_sha256': 'fly-brain-main/public/data/neurons.bin'}
CELLS = {'DNg100_L': 10045, 'DNg100_R': 10056, 'E1': 800173, 'E2': 800863, 'I1': 801884}
CORE = ('DNg100_L', 'E1', 'E2', 'I1')
M_R1 = 542747200.
G1_MAX = 0.01
MATERIAL = 2.
SOMA_UM_PER_UNIT = 0.008
SOMA_TOLERANCE_UM = 10.
I2_SEED, I2_DRAW = 20261108, 15


def jsonable(value):
    """dng100_rhythm.clean plus infinity -> the string 'inf' (rho for a neuron with no cord cable)."""
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (float, np.floating)) and math.isinf(value):
        return 'inf' if value > 0 else '-inf'
    return clean(value)


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


# ---- skeletons -----------------------------------------------------------------------

def decode(path=ROOT/SKELETONS):
    """(vOff[N+1], pos[V, 3] µm, seg[S, 2]) from the checked-in decoder."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)/'skel.bin'
        subprocess.run(['node', str(ROOT/DUMP), str(path), str(out)], check=True)
        raw = out.read_bytes()
    n, v, s = np.frombuffer(raw[:12], np.uint32).astype(np.int64)
    o = 12
    voff = np.frombuffer(raw[o:o + 4*(n + 1)], np.uint32).astype(np.int64); o += 4*(n + 1)
    pos = np.frombuffer(raw[o:o + 12*v], np.float32).reshape(v, 3).astype(np.float64); o += 12*v
    seg = np.frombuffer(raw[o:o + 8*s], np.uint32).reshape(s, 2).astype(np.int64); o += 8*s
    if o != len(raw):
        raise ValueError('skeleton dump size mismatch')
    return voff, pos, seg


def neck_plane(z_brain, z_cord):
    """Integer plane z* minimising (brain z > z*) + (cord z < z*); ties -> lower-middle minimiser."""
    zb, zc = np.sort(np.asarray(z_brain, float)), np.sort(np.asarray(z_cord, float))
    lo = math.floor(min(zb[0], zc[0])); hi = math.ceil(max(zb[-1], zc[-1]))
    cand = np.arange(lo, hi + 1, dtype=float)
    err = (len(zb) - np.searchsorted(zb, cand, 'right')) + np.searchsorted(zc, cand, 'left')
    best = np.flatnonzero(err == err.min())
    k = best[(len(best) - 1)//2]
    return dict(z_star=float(cand[k]), misclassified=int(err[k]), vertices=int(len(zb) + len(zc)),
                rate=float(err[k]/(len(zb) + len(zc))), minimiser_range=[float(cand[best[0]]), float(cand[best[-1]])],
                brain_above=int(len(zb) - np.searchsorted(zb, cand[k], 'right')),
                cord_below=int(np.searchsorted(zc, cand[k], 'left')))


def cable_split(voff, pos, seg, z_star):
    """Per-neuron total cable and cable with z > z* (µm); a crossing segment is split at the plane."""
    a, b = pos[seg[:, 0]], pos[seg[:, 1]]
    length = np.linalg.norm(b - a, axis=1)
    za, zb = a[:, 2], b[:, 2]
    zlo, zhi = np.minimum(za, zb), np.maximum(za, zb)
    span = zhi - zlo
    frac = np.where(zlo > z_star, 1., np.where(zhi <= z_star, 0., (zhi - z_star)/np.where(span > 0, span, 1.)))
    owner = np.searchsorted(voff, seg[:, 1], 'right') - 1
    n = len(voff) - 1
    return np.bincount(owner, length, n), np.bincount(owner, length*frac, n)


# ---- scaling --------------------------------------------------------------------------

def median_rule(values):
    """region_scales / ratenet.js rule: upper-middle element of the positive values."""
    v = np.asarray(values, float)
    v = v[v > 0]
    return float(np.partition(v, len(v)//2)[len(v)//2])


def scaling(size, f, region2, m_r1=M_R1):
    """s_R1, s_VNC, rho (= s_R1/s_VNC) and m_VNC. f NaN (no cable) -> NaN; f = 0 -> s_VNC 0, rho inf."""
    size = np.asarray(size, float)
    size_vnc = size*f
    m_vnc = median_rule(size_vnc[region2 & np.isfinite(size_vnc)])
    s_r1 = size/m_r1
    s_vnc = size_vnc/m_vnc
    with np.errstate(divide='ignore', invalid='ignore'):
        rho = np.where(np.isnan(s_vnc), np.nan, np.where(s_vnc > 0, s_r1/s_vnc, np.inf))
    return s_r1, s_vnc, rho, m_vnc


def label(g1_rate, rho_dng100, rho_dns, core_cable, sources_ok=True):
    if not sources_ok:
        return 'INCONCLUSIVE', dict(reason='source hash mismatch')
    if not g1_rate < G1_MAX:
        return 'INCONCLUSIVE', dict(reason='G1 failed: no clean neck plane')
    if any(not c > 0 for c in core_cable.values()):
        return 'INCONCLUSIVE', dict(reason='a core cell has zero cable')
    dns = np.asarray([r for r in rho_dns if not np.isnan(r)], float)
    med = float(np.median(dns)) if len(dns) else math.nan
    checks = dict(a_dng100_L=bool(rho_dng100 >= MATERIAL), b_network_dn_median=bool(med >= MATERIAL))
    v = 'SIZE_MISMATCH_MATERIAL' if any(checks.values()) else 'SIZE_MISMATCH_MINOR'
    return v, dict(checks=checks, network_dn_median_rho=med, network_dns_scored=int(len(dns)))


# ---- run ------------------------------------------------------------------------------

def brain_cord_sets(superclasses):
    brain = [k for k, s in enumerate(superclasses) if s.startswith(('cb_', 'ol_', 'visual_'))
             and 'sensory' not in s and 'efferent' not in s]
    cord = [k for k, s in enumerate(superclasses) if s.startswith('vnc_')]
    return brain, cord


def i2_draw(n, voff, soma):
    ok = np.flatnonzero((np.diff(voff) > 0) & np.all(np.isfinite(soma), axis=1))
    return sorted(int(i) for i in np.random.default_rng(I2_SEED).choice(ok, I2_DRAW, replace=False))


def soma_in_bbox(i, voff, pos, soma):
    p = pos[voff[i]:voff[i + 1]]
    s = soma[i]*SOMA_UM_PER_UNIT
    if not len(p) or not np.all(np.isfinite(s)):
        return None
    return bool(np.all(s >= p.min(0) - SOMA_TOLERANCE_UM) and np.all(s <= p.max(0) + SOMA_TOLERANCE_UM))


def quantiles(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if not len(x):
        return None
    q = np.percentile(x, [0, 10, 25, 50, 75, 90, 100])
    return dict(n=int(len(x)), min=q[0], p10=q[1], p25=q[2], median=q[3], p75=q[4], p90=q[5], max=q[6])


def audit(data, voff, pos, seg):
    sup = np.asarray(data.superclass_ids)
    names = data.superclasses
    brain_sc, cord_sc = brain_cord_sets(names)
    vowner = np.repeat(np.arange(len(voff) - 1), np.diff(voff))
    vsc = sup[vowner]
    plane = neck_plane(pos[np.isin(vsc, brain_sc), 2], pos[np.isin(vsc, cord_sc), 2])
    total, above = cable_split(voff, pos, seg, plane['z_star'])
    with np.errstate(divide='ignore', invalid='ignore'):
        f = np.where(total > 0, above/total, np.nan)
    _, regions, med = region_scales(data, ModelConfig())
    size = np.asarray(data.neuron_sizes, float)
    s_r1, s_vnc, rho, m_vnc = scaling(size, f, regions == 2, float(med[2]))
    net, _ = build_network(data)
    net = np.asarray(net)
    mns = set(front_left_mns(data.bodymap))
    sc_name = np.asarray(names, object)[sup]
    klass = {'mn': [i for i in net if i in mns],
             'dn': [i for i in net if sc_name[i] == 'descending_neuron'],
             'an': [i for i in net if sc_name[i] == 'ascending_neuron'],
             'cord_premotor': [i for i in net if i not in mns and str(sc_name[i]).startswith('vnc_')]}
    klass['other'] = sorted(set(net) - set().union(*map(set, klass.values())))
    ids = {k: dense(data, b) for k, b in CELLS.items()}

    def cell(i):
        return dict(dense_index=int(i), body_id=int(data.body_ids[i]), instance=data.instances[i],
                    superclass=str(sc_name[i]), size=size[i], cable_um=total[i], cable_vnc_um=above[i], f=f[i],
                    s_r1=s_r1[i], s_vnc=s_vnc[i], rho=rho[i])

    v, details = label(plane['rate'], rho[ids['DNg100_L']], rho[klass['dn']], {k: total[ids[k]] for k in CORE})
    whole = {k: quantiles(f[sc_name == k]) for k in ('descending_neuron', 'ascending_neuron')}
    return dict(verdict=v, **details, plane=plane, medians=dict(m_r1=float(med[2]), m_vnc=m_vnc,
                                                                 ratio_m_vnc_over_m_r1=m_vnc/float(med[2])),
                cells={k: cell(i) for k, i in ids.items()},
                network=dict(size=len(net), classes={k: len(x) for k, x in klass.items()},
                             rho={k: quantiles(rho[x][np.isfinite(rho[x])]) for k, x in klass.items()},
                             rho_infinite={k: int(np.isinf(rho[x]).sum()) for k, x in klass.items()},
                             f={k: quantiles(f[x]) for k, x in klass.items()},
                             no_cable={k: int(np.isnan(f[x]).sum()) for k, x in klass.items()},
                             s_over_20=dict(r1=int((s_r1[net] > 20).sum()),
                                            vnc=int((s_vnc[net] > 20).sum()))),
                mns={str(i): dict(f=f[i], s_r1=s_r1[i], s_vnc=s_vnc[i], rho=rho[i]) for i in klass['mn']},
                whole_dataset_f=whole, no_cable_neurons=int(np.isnan(f).sum())), net, ids


def run(cache):
    spec = protocol()
    src = sources()
    if src != spec['sources']['files']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='source hash mismatch', sources=src)
    data = load_cache(cache)
    voff, pos, seg = decode()
    soma = np.asarray(data.soma, float).reshape(-1, 3)
    integrity = dict(skeleton_n=int(len(voff) - 1), meta_n=int(data.neuron_count))
    draw = i2_draw(data.neuron_count, voff, soma)
    ids = {k: dense(data, b) for k, b in CELLS.items()}
    integrity['i2_draw'] = draw
    integrity['i2_draw_matches_protocol'] = draw == spec['integrity']['I2_draw_dense_indices']
    integrity['soma_in_bbox'] = {str(i): soma_in_bbox(i, voff, pos, soma) for i in [*ids.values(), *draw]}
    checked = [x for x in integrity['soma_in_bbox'].values() if x is not None]
    integrity['I2_pass'] = bool(integrity['skeleton_n'] == integrity['meta_n'] and integrity['i2_draw_matches_protocol']
                                and len(checked) >= 15 and all(checked))
    if not integrity['I2_pass']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE',
                    reason='I2 index identity failed', integrity=integrity, sources=src)
    result, net, _ = audit(data, voff, pos, seg)
    body_sha = hashlib.sha256(json.dumps(sorted(int(data.body_ids[i]) for i in net)).encode()).hexdigest()
    integrity['r1_network_body_ids_sha256'] = body_sha
    if body_sha != spec['integrity']['r1_network_body_ids_sha256']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE',
                    reason='R1 network mismatch', integrity=integrity, sources=src)
    exp = result['verdict'] == 'SIZE_MISMATCH_MATERIAL' and result.get('checks', {}).get('a_dng100_L')
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, **result, expectations=dict(X1=bool(exp)),
                integrity=integrity, sources=src, interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--describe', action='store_true',
                        help='plumbing: print source hashes, N, the I2 draw and soma checks (no plane, cable or size)')
    args = parser.parse_args(argv)
    if args.describe:
        data = load_cache(args.cache)
        voff, pos, _ = decode()
        soma = np.asarray(data.soma, float).reshape(-1, 3)
        draw = i2_draw(data.neuron_count, voff, soma)
        ids = [dense(data, b) for b in CELLS.values()]
        print(json.dumps(dict(sources=sources(), skeleton_n=len(voff) - 1, meta_n=data.neuron_count, i2_draw=draw,
                              soma_in_bbox={str(i): soma_in_bbox(i, voff, pos, soma) for i in [*ids, *draw]}), indent=1))
        return 0
    with args.output.open('xb') as stream:  # exclusive: claim the evidence path before running
        result = run(args.cache)
        stream.write((json.dumps(jsonable(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(jsonable({k: result.get(k) for k in ('verdict', 'checks', 'network_dn_median_rho', 'plane',
                                                         'medians', 'expectations', 'reason')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
