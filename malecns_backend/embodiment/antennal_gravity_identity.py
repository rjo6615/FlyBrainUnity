"""Step A: Johnston's organ zone C/E identity and wiring (data only).

Preregistered in docs/evidence/antennal-gravity-identity-v1/protocol.json. No simulation,
encoder, admission or behavioral claim. Reuses posture_sense_inventory graph code.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from ..cache import load_cache
from .posture_sense_inventory import ROOT, adjacency, motor_pools, sha

PROTOCOL = 'docs/evidence/antennal-gravity-identity-v1/protocol.json'
PROTOCOL_SHA256 = 'dcbe4e5ca433f1035d946f98f352d86b60399a580cd26da59af132e91389bd55'
SCHEMA = 'antennal-gravity-identity-result-v1'
SIDES = {'L': 'left', 'R': 'right'}
ZONES = ('C', 'E')
KEYS = tuple((z, s) for z in ZONES for s in SIDES.values())
MIN_SET = 10
OVERLAP_MAX = .5


def protocol():
    if sha(PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads((ROOT/PROTOCOL).read_text(encoding='utf-8'))


def zone_of(type_name):
    if not isinstance(type_name, str):
        return None
    if type_name == 'JO-unclear':
        return 'unclear'
    for z in ZONES:
        if type_name.startswith(f'JO-{z}'):
            return z
    return 'other'


def populations(table):
    """{(zone, side): [bodyId]} over subclass wind_gravity with an L/R rootSide."""
    out = {}
    rows = table[table['subclass'] == 'wind_gravity']
    for body, typ, root in zip(rows['bodyId'], rows['type'], rows['rootSide']):
        side = SIDES.get(root) if isinstance(root, str) else None
        z = zone_of(typ)
        if side and z:
            out.setdefault((z, side), []).append(int(body))
    return {k: sorted(v) for k, v in out.items()}


def target_weights(adj, sources):
    if not sources:
        return {}
    row = np.asarray(adj[sorted(sources)].sum(axis=0)).ravel()
    return {int(t): float(row[t]) for t in np.nonzero(row)[0]}


def overlap(wa, wb):
    keys = set(wa) | set(wb)
    hi = sum(max(wa.get(k, 0.), wb.get(k, 0.)) for k in keys)
    return sum(min(wa.get(k, 0.), wb.get(k, 0.)) for k in keys) / hi if hi else 0.


def within_two(adj, binary, sources, targets):
    """Source neurons with a direct edge or a two-hop path onto any target."""
    if not sources or not targets:
        return set()
    s, t = sorted(sources), sorted(targets)
    hit = (adj[s][:, t].getnnz(axis=1) > 0) | ((binary[s] @ binary[:, t]).getnnz(axis=1) > 0)
    return {s[i] for i in np.nonzero(hit)[0]}


def targets_reached(binary, sources, targets):
    """Targets reached by a direct edge or a two-hop path from any source."""
    if not sources or not targets:
        return set()
    v = np.zeros(binary.shape[0])
    v[sorted(sources)] = 1.
    one = binary.T @ v
    two = binary.T @ (one > 0).astype(float)
    return {x for x in targets if one[x] > 0 or two[x] > 0}


def evaluate(pops, index, adj, dn_types, leg_pools):
    """pops {(zone, side): [bodyId]}; index bodyId->dense; dn_types {dense: (bodyId, type)}."""
    adj = adj.tocsr()
    binary = (adj > 0).astype(np.float64).tocsr()
    unmatched, duplicated = [], []
    sets = {}
    for key in KEYS:
        bodies = pops.get(key, [])
        duplicated += [b for b, n in Counter(bodies).items() if n > 1]
        unmatched += [b for b in bodies if index.get(b) is None]
        sets[key] = {index[b] for b in bodies if index.get(b) is not None}
    all_ids = [i for key in KEYS for i in sets[key]]
    a1 = not unmatched and not duplicated and len(all_ids) == len(set(all_ids))
    counts = {f'{z}_{s}': len(sets[(z, s)]) for z, s in KEYS}
    a2 = all(n >= MIN_SET for n in counts.values())
    weights = {k: target_weights(adj, sets[k]) for k in KEYS}
    ov = {s: overlap(weights[('C', s)], weights[('E', s)]) for s in SIDES.values()}
    a3 = all(v < OVERLAP_MAX for v in ov.values())
    dn = set(dn_types)
    reach_dn = {f'{z}_{s}': within_two(adj, binary, sets[(z, s)], dn) for z, s in KEYS}
    a4 = all(reach_dn.values())
    checks = dict(A1_identity=a1, A2_bilateral=a2, A3_zone_segregation=a3, A4_descending_reach=a4)
    verdict = ('IDENTITY_READY' if all(checks.values()) else
               'IDENTITY_PARTIAL' if a1 and a2 else 'NOT_READY')
    report = {}
    for z, s in KEYS:
        k, v = f'{z}_{s}', sets[(z, s)]
        reached = sorted(targets_reached(binary, v, dn))
        dsyn = (np.asarray(adj[sorted(v)][:, reached].sum(axis=0)).ravel().tolist()
                if v and reached else [0.]*len(reached))
        report[k] = dict(
            neurons=len(v), output_synapses=float(adj[sorted(v)].sum()) if v else 0.,
            neurons_reaching_descending=len(reach_dn[k]),
            descending_reached=[dict(body_id=dn_types[d][0], type=dn_types[d][1], direct_synapses=float(w))
                                for d, w in zip(reached, dsyn)],
            leg_mn_two_hop_neurons={leg: len(within_two(adj, binary, v, pool))
                                    for leg, pool in sorted(leg_pools.items())})

    def ratio(a, b):
        return a/b if b else None
    lr = {z: dict(count_left_over_right=ratio(counts[f'{z}_left'], counts[f'{z}_right']),
                  synapses_left_over_right=ratio(report[f'{z}_left']['output_synapses'],
                                                 report[f'{z}_right']['output_synapses'])) for z in ZONES}
    unclear = {index[b] for b in pops.get(('unclear', 'right'), []) if index.get(b) is not None}
    wu = target_weights(adj, unclear)
    descriptive = dict(unclear_right_neurons=len(unclear),
                       unclear_right_overlap_with_C_right=overlap(wu, weights[('C', 'right')]),
                       unclear_right_overlap_with_E_right=overlap(wu, weights[('E', 'right')]),
                       other_and_unclear_counts={f'{z}_{s}': len(pops.get((z, s), []))
                                                 for z in ('other', 'unclear') for s in SIDES.values()})
    return dict(verdict=verdict, checks=checks, counts=counts,
                unmatched_body_ids=sorted(unmatched), duplicated_body_ids=sorted(set(duplicated)),
                overlap_C_vs_E=ov, populations=report, left_right=lr, descriptive=descriptive,
                body_ids={f'{z}_{s}': pops.get((z, s), []) for z, s in KEYS})


def run(cache, table=None):
    spec = protocol()
    src = spec['sources']['annotations']
    if sha(src['path']) != src['sha256']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='annotation hash mismatch')
    if table is None:
        import pandas as pd
        table = pd.read_feather(ROOT/src['path'])
    data = load_cache(cache)
    index = {int(k): int(v) for k, v in data.body_id_to_index.items()}
    adj = adjacency(data, 6)
    dns = table[table['superclass'] == 'descending_neuron']
    dn_types = {index[int(b)]: (int(b), t if isinstance(t, str) else None)
                for b, t in zip(dns['bodyId'], dns['type']) if int(b) in index}
    legs = {f'{seg} {side}': set().union(*p.values()) for (seg, side), p in motor_pools(data.bodymap).items()}
    result = evaluate(populations(table), index, adj, dn_types, legs)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, **result,
                interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run(args.cache)
        stream.write((json.dumps(result, indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps({k: result.get(k) for k in ('verdict', 'checks', 'counts', 'overlap_C_vs_E')}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
