"""Step A: do SNpp45 hair plates in our connectome match published CxHP8 output wiring?

Preregistered in docs/evidence/hair-plate-identity-v1/protocol.json. Connectivity only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from ..cache import load_cache
from .posture_sense_inventory import adjacency

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/hair-plate-identity-v1/protocol.json'
PROTOCOL_SHA256 = 'd24c76f6b0ef873451a7136dd9698349e464f78b69cafcee52f75259a292f72d'
SCHEMA = 'hair-plate-identity-result-v1'
NERVES = {'T1': 'VProN', 'T2': 'MesoLN', 'T3': 'MetaLN'}
SIDES = {'L': 'left', 'R': 'right'}
LEG_NAME = re.compile(r'^(.+) (T[123]) (left|right)$')
NT_SIGN = {'acetylcholine': 1, 'gaba': -1, 'glutamate': -1}


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def side_of(row):
    for column in ('rootSide', 'somaSide'):
        v = row.get(column)
        if isinstance(v, str) and v in SIDES:
            return SIDES[v]
    return None


def sensory_sets(table, index):
    """{(seg, side): set(dense)} for SNpp45 by declared nerve; plus excluded records."""
    sets, excluded = {}, []
    rows = table[table['type'] == 'SNpp45']
    for _, r in rows.iterrows():
        seg = next((s for s, n in NERVES.items() if r.get('entryNerve') == n), None)
        side = side_of(r)
        dense = index.get(int(r['bodyId']))
        if seg is None or side is None or dense is None:
            excluded.append(dict(body_id=int(r['bodyId']), entry_nerve=r.get('entryNerve'), side=side,
                                 matched=dense is not None))
            continue
        sets.setdefault((seg, side), set()).add(int(dense))
    return sets, excluded


def motor_sets(bodymap):
    """{(seg, side): {population: set(dense)}} with neurons deduplicated per population."""
    out = {}
    for e in bodymap['muscles']:
        m = LEG_NAME.match(e['name'])
        if m:
            out.setdefault((m.group(2), m.group(3)), {}).setdefault(m.group(1), set()).update(int(i) for i in e['idx'])
    return out


def leg_result(adj, signs, interneuron, sources, pools, spec):
    s = sorted(sources)
    direct = {name: int(adj[s][:, sorted(ids)].sum()) for name, ids in sorted(pools.items())}
    weighted = adj[s].multiply(1).tocsr()
    to_k = np.asarray(weighted.sum(axis=0)).ravel() * signs * interneuron  # signed S->k drive
    sets = spec['motor_sets']
    net = {}
    for label in ('posterior', 'anterior'):
        ids = sorted(set().union(*(pools.get(n, set()) for n in sets[label])))
        net[label] = float(to_k @ np.asarray(adj[:, ids].sum(axis=1)).ravel()) if ids else None
    post = sum(direct.get(n, 0) for n in sets['posterior'])
    ant = sum(direct.get(n, 0) for n in sets['anterior'])
    top = max(sorted(direct), key=lambda n: direct[n]) if direct and max(direct.values()) > 0 else None
    checks = dict(i_posterior_exceeds_anterior=post > ant, ii_top_population_posterior=top in sets['posterior'],
                  iii_net_two_hop_anterior_negative=net['anterior'] is not None and net['anterior'] < 0)
    return dict(sensory_neurons=len(s), direct=direct, posterior_direct=post, anterior_direct=ant,
                top_population=top, net_two_hop=net, checks=checks, match=all(checks.values()))


def verdict(legs):
    front = all(legs.get(('T1', side), {}).get('match') for side in ('left', 'right'))
    serial = sum(bool(legs.get((seg, side), {}).get('match')) for seg in ('T2', 'T3') for side in ('left', 'right')) >= 3
    return {(True, True): 'MATCH_ALL', (True, False): 'FRONT_ONLY', (False, True): 'SERIAL_ONLY',
            (False, False): 'NO_MATCH'}[(front, serial)]


def run(cache):
    spec = protocol()
    src = spec['sources']['annotations']
    if hashlib.sha256((ROOT/src['path']).read_bytes()).hexdigest() != src['sha256']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='annotation hash mismatch')
    import pandas as pd
    table = pd.read_feather(ROOT/src['path'])
    data = load_cache(cache)
    sources, excluded = sensory_sets(table, data.body_id_to_index)
    pools = motor_sets(data.bodymap)
    adj = adjacency(data, 6)
    nts = np.asarray(data.neurotransmitter_ids)
    signs = np.array([NT_SIGN.get(data.neurotransmitters[i], 0) for i in nts], dtype=float)
    sup = np.asarray(data.superclass_ids)
    interneuron = np.array([0. if ('sensory' in data.superclasses[i] or 'motor' in data.superclasses[i]) else 1.
                            for i in sup])
    legs = {}
    for leg in sorted(pools):
        if leg not in sources:
            return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason=f'no sensory neurons for {leg}')
        legs[leg] = leg_result(adj, signs, interneuron, sources[leg], pools[leg], spec)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict=verdict(legs),
                legs={f'{seg} {side}': v for (seg, side), v in legs.items()}, excluded=excluded,
                interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run(args.cache)
        stream.write((json.dumps(result, indent=1, allow_nan=False, default=str) + '\n').encode())
    print(json.dumps(dict(verdict=result['verdict'], matches={k: v['match'] for k, v in result.get('legs', {}).items()}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
