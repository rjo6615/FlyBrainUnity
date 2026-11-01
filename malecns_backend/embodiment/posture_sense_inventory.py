"""Data-only inventory of posture-relevant sensory populations in the simulated MaleCNS.

Preregistered in docs/evidence/posture-sense-inventory-v1/protocol.json. No simulation,
encoder, admission or behavioral claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from scipy import sparse

from ..cache import load_cache

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/posture-sense-inventory-v1/protocol.json'
PROTOCOL_SHA256 = '41f7168bd3975765d3fbfbbeab7d3f84070220b81dab8b39973b3c5f09a1cb85'
SCHEMA = 'posture-sense-inventory-result-v1'
LEG_NAME = re.compile(r'^(.+) T([123]) (left|right)$')
SIDES = {'L': 'left', 'R': 'right'}
LEG_ORGANS = ('hair_plate', 'campaniform_sensilla', 'chordotonal_organ')
READY_SIGNALS = ('AVAILABLE_EXISTING_ENCODER', 'AVAILABLE_NO_ENCODER')


def sha(path, lf=False):
    raw = (ROOT/path).read_bytes()
    return hashlib.sha256(raw.replace(b'\r\n', b'\n') if lf else raw).hexdigest()


def protocol():
    if sha(PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads((ROOT/PROTOCOL).read_text(encoding='utf-8'))


def organ_rows(table, spec):
    """{organ: [dict(body_id, leg, side)]} from the annotation table (pandas DataFrame)."""
    legs = spec['assignment']['leg_by_entry_nerve']
    result = {}
    for organ, rule in spec['organs'].items():
        value = re.match(r"subclass == '(.+)'", rule).group(1)
        rows = table[table['subclass'] == value]
        out = []
        for _, r in rows.iterrows():
            side = None
            for column in ('rootSide', 'somaSide'):
                v = r.get(column)
                if isinstance(v, str) and v in SIDES:
                    side = SIDES[v]
                    break
            nerve = r.get('entryNerve')
            out.append(dict(body_id=int(r['bodyId']), leg=legs.get(nerve) if isinstance(nerve, str) else None,
                            side=side, entry_nerve=nerve if isinstance(nerve, str) else None,
                            type=r.get('type') if isinstance(r.get('type'), str) else None))
        result[organ] = out
    return result


def motor_pools(bodymap):
    """{(segment 'T1', side): {joint_class: set(dense)}} from bodymap leg MN entries."""
    pools = {}
    for e in bodymap['muscles']:
        m = LEG_NAME.match(e['name'])
        if not m:
            continue
        seg, side = 'T' + m.group(2), m.group(3)
        cls = e['actuator'][:-len(f'_T{m.group(2)}_{side}')]
        pools.setdefault((seg, side), {}).setdefault(cls, set()).update(int(i) for i in e['idx'])
    return pools


def adjacency(data, floor):
    row_ptr = np.asarray(data.row_ptr, dtype=np.int64)
    post = np.asarray(data.target_indices, dtype=np.int64)
    w = np.asarray(data.synapse_counts, dtype=np.float64)
    pre = np.repeat(np.arange(len(row_ptr) - 1), np.diff(row_ptr))
    keep = w >= floor
    n = len(row_ptr) - 1
    return sparse.csr_matrix((w[keep], (pre[keep], post[keep])), shape=(n, n))


def reach(adj, binary, sources, targets):
    """Direct-edge neurons, two-hop neurons and direct synapses from sources onto targets."""
    if not sources or not targets:
        return dict(direct_neurons=0, two_hop_neurons=0, direct_synapses=0)
    s, t = sorted(sources), sorted(targets)
    direct = adj[s][:, t]
    two = (binary[s] @ binary[:, t])
    return dict(direct_neurons=int((direct.getnnz(axis=1) > 0).sum()),
                two_hop_neurons=int((two.getnnz(axis=1) > 0).sum()),
                direct_synapses=int(direct.sum()))


def classify(organ, summary, signal, leg_reach_fraction):
    if summary['matched_fraction'] < .9:
        return 'BLOCKED'
    ready = signal in READY_SIGNALS
    if organ in LEG_ORGANS:
        ready = ready and summary['leg_side_assigned_fraction'] >= .9 and leg_reach_fraction >= .5
    else:
        ready = ready and summary['any_pool_two_hop_neurons'] > 0
    return 'READY_FOR_ENCODER_DESIGN' if ready else 'PARTIAL'


def run(cache, encoders=None, table=None):
    spec = protocol()
    src = spec['sources']
    if sha(src['annotations']['path']) != src['annotations']['sha256']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='annotation hash mismatch')
    if sha('malecns_backend/interface_map.json', lf=True) != src['interface_map_lf_sha256']:
        return dict(schema=SCHEMA, verdict='INCONCLUSIVE', reason='interface map hash mismatch')
    if table is None:
        import pandas as pd
        table = pd.read_feather(ROOT/src['annotations']['path'])
    data = load_cache(cache)
    index = data.body_id_to_index
    if encoders is None:
        from .six_tibia import load_six_tibia_interfaces
        from .tactile_contact import load_tactile_populations
        tibia = {int(i) for x in load_six_tibia_interfaces().values() for i in x.sensor.dense_indices}
        tactile = {index[int(b)] for x in load_tactile_populations().values() for b in x.body_ids}
        encoders = dict(tibia_angle=tibia, tactile_contact=tactile)
    adj = adjacency(data, 6)
    binary = (adj > 0).astype(np.float64).tocsr()
    pools = motor_pools(data.bodymap)
    classes = sorted({c for p in pools.values() for c in p})
    all_pool = {c: set().union(*(p.get(c, set()) for p in pools.values())) for c in classes}
    organs = {}
    for organ, rows in organ_rows(table, spec).items():
        dense = {r['body_id']: index.get(r['body_id']) for r in rows}
        matched = [r for r in rows if dense[r['body_id']] is not None]
        assigned = [r for r in matched if r['leg'] and r['side']]
        summary = dict(annotated=len(rows), matched=len(matched),
                       matched_fraction=len(matched)/len(rows) if rows else 0.,
                       leg_side_assigned=len(assigned),
                       leg_side_assigned_fraction=len(assigned)/len(matched) if matched else 0.,
                       unmatched_body_ids=sorted(r['body_id'] for r in rows if dense[r['body_id']] is None),
                       entry_nerves={}, types={})
        for r in matched:
            summary['entry_nerves'][str(r['entry_nerve'])] = summary['entry_nerves'].get(str(r['entry_nerve']), 0) + 1
            summary['types'][str(r['type'])] = summary['types'].get(str(r['type']), 0) + 1
        ids = {dense[r['body_id']] for r in matched}
        summary['already_encoded'] = {k: len(ids & v) for k, v in encoders.items()}
        per_leg = {}
        for (seg, side), leg_pools in sorted(pools.items()):
            sources = {dense[r['body_id']] for r in assigned if r['leg'] == seg and r['side'] == side}
            per_leg[f'{seg} {side}'] = dict(sensory_neurons=len(sources),
                joint_classes={c: reach(adj, binary, sources, leg_pools[c]) for c in sorted(leg_pools)})
        summary['per_leg'] = per_leg
        summary['all_pools'] = {c: reach(adj, binary, ids, all_pool[c]) for c in classes}
        summary['any_pool_two_hop_neurons'] = reach(adj, binary, ids, set().union(*all_pool.values()))['two_hop_neurons']
        legs_reached = sum(1 for leg in per_leg.values()
                           if any(v['two_hop_neurons'] > 0 for v in leg['joint_classes'].values()))
        summary['legs_with_two_hop_reach'] = legs_reached
        signal = spec['body_signal_declaration'][organ].split('-> ')[-1]
        summary['body_signal'] = signal
        summary['classification'] = classify(organ, summary, signal, legs_reached/6)
        organs[organ] = summary
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, organs=organs,
                classification={o: v['classification'] for o, v in organs.items()},
                interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run(args.cache)
        stream.write((json.dumps(result, indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(result.get('classification', result), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
