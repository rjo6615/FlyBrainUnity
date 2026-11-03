"""RF hair-plate deficit V2: follow the model's own T1 SNpp45 neurons into BANC by neuron-level match.

Preregistered in docs/evidence/rf-hair-plate-banc-v2/protocol.json. Data only: committed
BANC v888 metadata, the MaleCNS v1.0 annotations and the Step A result. Read-only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from . import hair_plate_identity as a
from . import rf_hair_plate_banc as v1
from .coxa_drive_asymmetry import sha256

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/rf-hair-plate-banc-v2/protocol.json'
PROTOCOL_SHA256 = '9b1ec93055f1a6a6e32461fb6db79b3c1d482703849441e5aed361b2b3dbb302'
SCHEMA = 'rf-hair-plate-banc-result-v2'
COLUMNS = ['root_id', 'cell_type', 'nerve', 'side', 'proofread', 'malecns_match', 'manc_match', 'l2_cable_length_um']
EXCLUDED_ANCHOR = 821165
VERSION_MIN, COVERAGE_MIN, SIDE_MIN = 0.90, 0.75, 0.80
NERVE_SIDE = re.compile(r'^(left|right)_')


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def as_int(v):
    """Integer body ID from an int/float/str cell, else None."""
    try:
        f = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    return int(f) if math.isfinite(f) and f == int(f) else None


def id_list(v):
    return [i for i in (as_int(p) for p in str(v).split(',')) if i is not None] if isinstance(v, str) else \
        [i for i in [as_int(v)] if i is not None]


def anchors(annotations):
    """{leg: [bodyId]} by the Step A rule, plus {bodyId: mancBodyid or None}."""
    ids = {int(b): int(b) for b in annotations['bodyId']}
    sets, _ = a.sensory_sets(annotations, ids)
    legs = {f'{seg} {side}': sorted(v) for (seg, side), v in sets.items()}
    snpp = annotations[annotations['type'] == 'SNpp45']
    manc = {int(r['bodyId']): as_int(r.get('mancBodyid')) for _, r in snpp.iterrows()}
    return legs, manc


def side_of(row):
    s = row.get('side')
    if s in ('left', 'right'):
        return s
    m = NERVE_SIDE.match(row['nerve']) if isinstance(row.get('nerve'), str) else None
    return m.group(1) if m else None


def bridge_index(banc):
    """{malecns_id: [row]} and {manc_id: [row]} over all BANC rows with a match."""
    b1, b2 = {}, {}
    for r in banc.to_dict('records'):
        for i in id_list(r.get('malecns_match')):
            b1.setdefault(i, []).append(r)
        for i in id_list(r.get('manc_match')):
            b2.setdefault(i, []).append(r)
    return b1, b2


def counterparts(anchor_ids, manc, b1, b2):
    """{anchor: {root_id: dict(row fields, bridges)}}."""
    out = {}
    for anc in anchor_ids:
        found = {}
        for bridge, rows in (('B1', b1.get(anc, [])), ('B2', b2.get(manc.get(anc), []) if manc.get(anc) else [])):
            for r in rows:
                rec = found.setdefault(str(r['root_id']), dict(
                    root_id=str(r['root_id']), side=side_of(r), cell_type=v1._str(r.get('cell_type')),
                    nerve=v1._str(r.get('nerve')), proofread=v1._str(r.get('proofread')),
                    cable_um=v1._num(r.get('l2_cable_length_um')), bridges=[]))
                if bridge not in rec['bridges']:
                    rec['bridges'].append(bridge)
        out[anc] = found
    return out


def side_tally(per_anchor, legs, seg):
    """Distinct counterparts per side (anchor on the same side), consistency and coverage."""
    left, right = legs.get(f'{seg} left', []), legs.get(f'{seg} right', [])
    anchor_side = {x: 'left' for x in left} | {x: 'right' for x in right}
    owners = {}
    for anc in left + right:
        for root, rec in per_anchor[anc].items():
            owners.setdefault(root, (rec, set()))[1].add(anchor_side[anc])
    usable = {root: v for root, v in owners.items() if v[0]['side'] is not None}
    consistent = {root: v for root, v in usable.items() if v[0]['side'] in v[1]}
    counted = {s: [v[0] for v in consistent.values() if v[0]['side'] == s] for s in ('left', 'right')}
    coverage = {s: (sum(bool(per_anchor[x]) for x in ids) / len(ids) if ids else 0.)
                for s, ids in (('left', left), ('right', right))}
    return dict(counted=counted, coverage=coverage, distinct=len(owners), usable=len(usable),
                side_consistency=len(consistent) / len(usable) if usable else 0.,
                cross_side=[v[0] for v in usable.values() if v[0]['side'] not in v[1]],
                unusable_side=[v[0] for v in owners.values() if v[0]['side'] is None],
                unmatched_anchors=[x for x in left + right if not per_anchor[x]])


def measures(tally):
    sizes = {s: v1.summary([r['cable_um'] for r in tally['counted'][s] if r['cable_um'] is not None])
             for s in ('left', 'right')}
    return dict(n={s: len(tally['counted'][s]) for s in sizes}, size=sizes,
                count_diff=len(tally['counted']['right']) - len(tally['counted']['left']),
                median_ratio=v1.ratio(sizes['right']['median'], sizes['left']['median']),
                sum_ratio=v1.ratio(sizes['right']['sum'], sizes['left']['sum']))


def integrity(source_ok, anchor_counts, step_a_counts, version_fraction, t1):
    return dict(I1_sources=bool(source_ok) and anchor_counts == v1.EXPECTED_MALECNS == step_a_counts,
                I2_bridge_version=version_fraction >= VERSION_MIN,
                I3_coverage=all(t1['coverage'][s] >= COVERAGE_MIN for s in ('left', 'right')),
                I4_side_consistency=t1['side_consistency'] >= SIDE_MIN,
                I5_size_field=all(r['cable_um'] is not None and r['cable_um'] > 0
                                  for s in ('left', 'right') for r in t1['counted'][s]))


def evaluate(banc, annotations, source_ok, step_a_counts):
    legs, manc = anchors(annotations)
    b1, b2 = bridge_index(banc)
    known = {int(b) for b in annotations['bodyId']}
    version_fraction = (sum(i in known for i in b1) / len(b1)) if b1 else 0.
    all_anchors = sorted({x for ids in legs.values() for x in ids} | {EXCLUDED_ANCHOR})
    per_anchor = counterparts(all_anchors, manc, b1, b2)
    tallies = {seg: side_tally(per_anchor, legs, seg) for seg in ('T1', 'T2', 'T3')}
    checks = integrity(source_ok, {leg: len(v) for leg, v in legs.items()}, step_a_counts, version_fraction,
                       tallies['T1'])
    out = dict(status='INTEGRITY_ACCEPTED' if all(checks.values()) else 'INCONCLUSIVE_INTEGRITY', checks=checks,
               bridge_version_fraction=version_fraction, anchors=legs,
               per_anchor={str(k): dict(manc_body_id=manc.get(k), counterparts=list(v.values()))
                           for k, v in per_anchor.items()},
               segments={seg: dict(measures(t), **{k: t[k] for k in ('coverage', 'distinct', 'usable',
                                   'side_consistency', 'cross_side', 'unusable_side', 'unmatched_anchors')})
                         for seg, t in tallies.items()})
    if out['status'] == 'INTEGRITY_ACCEPTED':
        t1 = out['segments']['T1']
        c, s = v1.q_count(t1['count_diff']), v1.q_size(t1['median_ratio'])
        out['labels'] = dict(Q_COUNT=dict(label=c, d=t1['count_diff']), Q_SIZE=dict(label=s, r=t1['median_ratio']),
                             Q_RF=dict(label=v1.q_rf(c, s)))
    return out


def run():
    spec = protocol()
    import pandas as pd
    src = spec['sources']
    prov = json.loads((ROOT/src['banc_meta']['provenance']).read_text(encoding='utf-8'))
    prov_sha = next(s['raw_sha256'] for s in prov['sources'] if s['filename'] == 'banc_888_meta.feather')
    banc_sha = sha256(ROOT/src['banc_meta']['path'])
    source_ok = (banc_sha == src['banc_meta']['sha256'] == prov_sha
                 and sha256(ROOT/src['malecns_annotations']['path']) == src['malecns_annotations']['sha256']
                 and sha256(ROOT/src['step_a_result']['path']) == src['step_a_result']['sha256'])
    step_a = json.loads((ROOT/src['step_a_result']['path']).read_text(encoding='utf-8'))
    step_a_counts = {leg: v['sensory_neurons'] for leg, v in step_a['legs'].items()}
    banc = pd.read_feather(ROOT/src['banc_meta']['path'], columns=COLUMNS)
    annotations = pd.read_feather(ROOT/src['malecns_annotations']['path'])
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, banc_sha256=banc_sha,
                evaluation=evaluate(banc, annotations, source_ok, step_a_counts),
                interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run()
        stream.write((json.dumps(result, indent=1, allow_nan=False, default=str) + '\n').encode())
    e = result['evaluation']
    print(json.dumps(dict(status=e['status'], checks=e['checks'], labels=e.get('labels')), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
