"""RF hair-plate deficit V1: does BANC replicate the MaleCNS right-front SNpp45 deficit?

Preregistered in docs/evidence/rf-hair-plate-banc-v1/protocol.json. Data only: committed
BANC v888 metadata, the MaleCNS annotations/cache and the Step A result. Read-only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

import numpy as np

from . import hair_plate_identity as a
from .coxa_drive_asymmetry import sha256

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/rf-hair-plate-banc-v1/protocol.json'
PROTOCOL_SHA256 = '856fe70bdf0f87eb12d6c0d7cea8c755c44562237e413a6ae57c63fbeac770a5'
SCHEMA = 'rf-hair-plate-banc-result-v1'
BANC_NERVES = {'T1': 'ventral_prothoracic_nerve', 'T2': 'mesothoracic_leg_nerve', 'T3': 'metathoracic_leg_nerve'}
PRIMARY = re.compile(r'^(left|right)_(%s)$' % '|'.join(BANC_NERVES.values()))
SENSITIVITY_T1 = re.compile(r'^(left|right)_([a-z_]*prothoracic[a-z_]*_nerve|prosternal_nerve)$')
LEGS = tuple(f'{seg} {side}' for seg in ('T1', 'T2', 'T3') for side in ('left', 'right'))
EXPECTED_MALECNS = {'T1 left': 7, 'T1 right': 5, 'T2 left': 12, 'T2 right': 11, 'T3 left': 8, 'T3 right': 9}
COLUMNS = ['root_id', 'cell_type', 'nerve', 'side', 'proofread', 'status', 'l2_cable_length_um', 'volume_nm3']
EXCLUDED_MAX = 0.20


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def _str(v):
    return v if isinstance(v, str) else None


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def banc_legs(table):
    """Primary-rule rows per leg, excluded rows, side disagreements and T1 sensitivity counts."""
    rows = table[table['cell_type'] == 'SNpp45']
    legs, excluded, disagree = {leg: [] for leg in LEGS}, [], []
    sensitivity = {'T1 left': 0, 'T1 right': 0}
    for _, r in rows.iterrows():
        nerve = _str(r.get('nerve'))
        s = SENSITIVITY_T1.match(nerve) if nerve else None
        if s:
            sensitivity[f'T1 {s.group(1)}'] += 1
        m = PRIMARY.match(nerve) if nerve else None
        rec = dict(root_id=str(r.get('root_id')), nerve=nerve, side=_str(r.get('side')),
                   proofread=_str(r.get('proofread')), status=_str(r.get('status')),
                   cable_um=_num(r.get('l2_cable_length_um')), volume_nm3=_num(r.get('volume_nm3')))
        if not m:
            excluded.append(rec)
            continue
        side = m.group(1)
        seg = next(k for k, v in BANC_NERVES.items() if v == m.group(2))
        if rec['side'] != side:
            disagree.append(rec)
        legs[f'{seg} {side}'].append(rec)
    return legs, excluded, disagree, sensitivity, len(rows)


def malecns_sizes(data, sets):
    """{leg: [total raw output synapses per neuron]} from the cache CSR rows."""
    indptr = np.asarray(data.row_ptr, dtype=np.int64)
    counts = np.asarray(data.synapse_counts, dtype=np.float64)
    return {f'{seg} {side}': [float(counts[indptr[s]:indptr[s+1]].sum()) for s in sorted(ids)]
            for (seg, side), ids in sets.items()}


def summary(values):
    return dict(n=len(values), median=statistics.median(values) if values else None,
                sum=float(sum(values)), values=sorted(values))


def ratio(x, y):
    return x / y if x is not None and y else None


def segments(per_leg):
    """Per segment right-left count difference and right/left median and sum ratios."""
    out = {}
    for seg in ('T1', 'T2', 'T3'):
        L, R = per_leg[f'{seg} left'], per_leg[f'{seg} right']
        out[seg] = dict(count_diff=R['n'] - L['n'], median_ratio=ratio(R['median'], L['median']),
                        sum_ratio=ratio(R['sum'], L['sum']))
    return out


def q_count(d):
    return 'COUNT_DEFICIT_REPLICATED' if d <= -2 else 'COUNT_REVERSED' if d >= 2 else 'COUNT_SYMMETRIC'


def q_size(r):
    if r <= 0.67:
        return 'SIZE_DEFICIT_REPLICATED'
    if r >= 1.5:
        return 'SIZE_REVERSED'
    if 0.85 <= r <= 1/0.85:
        return 'SIZE_SYMMETRIC'
    return 'SIZE_INDETERMINATE'


def q_rf(count, size):
    if count == 'COUNT_DEFICIT_REPLICATED' and size == 'SIZE_DEFICIT_REPLICATED':
        return 'RF_DEFICIT_REPLICATED'
    if count in ('COUNT_SYMMETRIC', 'COUNT_REVERSED') and size in ('SIZE_SYMMETRIC', 'SIZE_REVERSED'):
        return 'RF_DEFICIT_NOT_REPLICATED'
    return 'RF_PARTIAL'


def labels(banc_seg):
    t1 = banc_seg['T1']
    c, s = q_count(t1['count_diff']), q_size(t1['median_ratio'])
    return dict(Q_COUNT=dict(label=c, d=t1['count_diff']), Q_SIZE=dict(label=s, r=t1['median_ratio']),
                Q_RF=dict(label=q_rf(c, s)))


def integrity(source_ok, legs, excluded, total, malecns_counts, step_a_counts):
    t1 = legs['T1 left'] + legs['T1 right']
    return dict(I1_sources=bool(source_ok),
                I2_typing=all(len(legs[leg]) >= 1 for leg in LEGS),
                I3_exclusions_bounded=total > 0 and len(excluded) <= EXCLUDED_MAX*total,
                I4_malecns_reproduction=malecns_counts == EXPECTED_MALECNS == step_a_counts,
                I5_size_fields=all(r['cable_um'] is not None and r['cable_um'] > 0 for r in t1))


def evaluate(legs, excluded, disagree, sensitivity, total, mal_sizes, source_ok, step_a_counts):
    mal_counts = {leg: len(v) for leg, v in mal_sizes.items()}
    checks = integrity(source_ok, legs, excluded, total, mal_counts, step_a_counts)
    banc = {leg: summary([r['cable_um'] for r in legs[leg] if r['cable_um'] is not None]) for leg in LEGS}
    mal = {leg: summary(mal_sizes.get(leg, [])) for leg in LEGS}
    out = dict(status='INTEGRITY_ACCEPTED' if all(checks.values()) else 'INCONCLUSIVE_INTEGRITY', checks=checks,
               banc=dict(per_leg=banc, segments=segments(banc), total_snpp45=total,
                         volume_median_nm3={leg: statistics.median(v) if v else None for leg in LEGS
                                   for v in [[r['volume_nm3'] for r in legs[leg] if r['volume_nm3'] is not None]]},
                         t1_rows=legs['T1 left'] + legs['T1 right'], excluded=excluded,
                         side_disagreements=disagree, t1_sensitivity_counts=sensitivity),
               malecns=dict(per_leg=mal, segments=segments(mal)))
    if out['status'] == 'INTEGRITY_ACCEPTED':
        out['labels'] = labels(out['banc']['segments'])
    return out


def run(cache):
    spec = protocol()
    import pandas as pd
    from ..cache import load_cache
    src = spec['sources']
    prov = json.loads((ROOT/src['banc_meta']['provenance']).read_text(encoding='utf-8'))
    prov_sha = next(s['raw_sha256'] for s in prov['sources'] if s['filename'] == 'banc_888_meta.feather')
    banc_sha = sha256(ROOT/src['banc_meta']['path'])
    step_a_path = ROOT/src['step_a_result']['path']
    a_spec = a.protocol()
    ann = ROOT/a_spec['sources']['annotations']['path']
    source_ok = (banc_sha == src['banc_meta']['sha256'] == prov_sha
                 and sha256(step_a_path) == src['step_a_result']['sha256']
                 and sha256(ann) == a_spec['sources']['annotations']['sha256'])
    step_a = json.loads(step_a_path.read_text(encoding='utf-8'))
    step_a_counts = {leg: v['sensory_neurons'] for leg, v in step_a['legs'].items()}
    table = pd.read_feather(ROOT/src['banc_meta']['path'], columns=COLUMNS)
    legs, excluded, disagree, sensitivity, total = banc_legs(table)
    data = load_cache(cache)
    sets, _ = a.sensory_sets(pd.read_feather(ann), data.body_id_to_index)
    result = evaluate(legs, excluded, disagree, sensitivity, total, malecns_sizes(data, sets), source_ok,
                      step_a_counts)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, banc_sha256=banc_sha, evaluation=result,
                interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run(args.cache)
        stream.write((json.dumps(result, indent=1, allow_nan=False, default=str) + '\n').encode())
    e = result['evaluation']
    print(json.dumps(dict(status=e['status'], checks=e['checks'], labels=e.get('labels')), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
