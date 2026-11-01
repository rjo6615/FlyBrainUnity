"""Blind serial-homology test: presynaptic cell-type fingerprints of annotated leg motor neurons.

Offline connectome analysis under docs/evidence/serial-motor-fingerprint-v1/protocol.json.
No physics, CNS simulation, mapping, sign, gain or admission change.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from ..cache import load_cache

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/serial-motor-fingerprint-v1/protocol.json'
PROTOCOL_SHA256 = 'f02fdd8fcde2171c53da482ac7c167e85dca10f20a0de3514a372c774a885e02'
SCHEMA = 'serial-motor-fingerprint-result-v1'
NAME = re.compile(r'^(.+) T([123]) (left|right)$')
LEGS = tuple((s, side) for side in ('left', 'right') for s in (1, 2, 3))
ADMITTED = ('tibia', 'femur', 'femur_twist')


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def labels(bodymap):
    """Exact annotated leg MN populations; neurons listed under two populations/legs are ambiguous."""
    seen, populations = {}, {}
    for entry in bodymap['muscles']:
        match = NAME.match(entry['name'])
        if not match:
            continue
        base, segment, side = match.group(1), int(match.group(2)), match.group(3)
        suffix = f'_T{segment}_{side}'
        if not entry['actuator'].endswith(suffix):
            raise ValueError('actuator/leg label disagreement: ' + entry['name'])
        key = ((segment, side), base)
        pop = populations.setdefault(key, dict(neurons=set(), joints=set()))
        pop['neurons'].update(int(i) for i in entry['idx'])
        pop['joints'].add(entry['actuator'][:-len(suffix)])
        for i in entry['idx']:
            seen.setdefault(int(i), set()).add(key)
    ambiguous = {i for i, keys in seen.items() if len(keys) > 1}
    neurons = {}
    for (leg, base), pop in populations.items():
        for i in pop['neurons'] - ambiguous:
            neurons[i] = dict(leg=leg, population=base, joints=frozenset(pop['joints']))
    return neurons, sorted(ambiguous)


def fingerprints(data, targets):
    """L1-normalized incoming synapse counts by presynaptic type (empty types excluded)."""
    targets = np.asarray(sorted(targets), dtype=np.int64)
    row_ptr = np.asarray(data.row_ptr, dtype=np.int64)
    post = np.asarray(data.target_indices, dtype=np.int64)
    counts = np.asarray(data.synapse_counts, dtype=np.float64)
    pre = np.repeat(np.arange(len(row_ptr) - 1), np.diff(row_ptr))
    keep = np.isin(post, targets)
    pre, post, counts = pre[keep], post[keep], counts[keep]
    types = data.types
    vocabulary = sorted({types[i] for i in np.unique(pre) if types[i]})
    column = {t: k for k, t in enumerate(vocabulary)}
    row = {int(t): k for k, t in enumerate(targets)}
    matrix = np.zeros((len(targets), len(vocabulary)))
    for p, q, c in zip(pre, post, counts):
        t = types[p]
        if t:
            matrix[row[int(q)], column[t]] += c
    totals = matrix.sum(1)
    result = {int(t): matrix[k]/totals[k] for k, t in enumerate(targets) if totals[k] > 0}
    return result, vocabulary, sorted(int(t) for k, t in enumerate(targets) if totals[k] == 0)


def centroids(members, prints):
    names = sorted(members)
    matrix = np.stack([np.mean([prints[i] for i in members[n]], axis=0) for n in names])
    return names, matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def assign(vector, names, unit):
    scores = unit @ (vector/np.linalg.norm(vector))
    return names[int(np.argmax(scores))]  # names are sorted, argmax takes the first maximum


def leg_members(neurons, prints, leg):
    members = {}
    for i, n in neurons.items():
        if n['leg'] == leg and i in prints:
            members.setdefault(n['population'], []).append(i)
    return members


def score_pair(neurons, prints, reference, target, members=None):
    members = members or leg_members(neurons, prints, reference)
    names, unit = centroids(members, prints)
    joints = {n: neurons[members[n][0]]['joints'] for n in names}
    rows = []
    for i in sorted(i for i, n in neurons.items() if n['leg'] == target and i in prints and n['population'] in members):
        predicted = assign(prints[i], names, unit)
        rows.append(dict(neuron=i, population=neurons[i]['population'], predicted=predicted,
                         joints=sorted(neurons[i]['joints']), type_correct=predicted == neurons[i]['population'],
                         joint_correct=bool(joints[predicted] & neurons[i]['joints'])))
    return rows


def pairs(kind):
    if kind == 'serial':
        return [(a, b) for a in LEGS for b in LEGS if a[1] == b[1] and a[0] != b[0]]
    return [(a, b) for a in LEGS for b in LEGS if a[0] == b[0] and a[1] != b[1]]


def accuracy(rows, key='type_correct'):
    return sum(r[key] for r in rows)/len(rows) if rows else None


def permuted_serial_accuracy(neurons, prints, rng):
    rows = []
    for reference, target in pairs('serial'):
        members = leg_members(neurons, prints, reference)
        ids = [i for n in sorted(members) for i in members[n]]
        shuffled = list(rng.permutation(ids))
        new, start = {}, 0
        for n in sorted(members):
            new[n] = shuffled[start:start+len(members[n])]
            start += len(members[n])
        rows += score_pair(neurons, prints, reference, target, new)
    return accuracy(rows)


def evaluate(neurons, prints, spec):
    tasks = {kind: {f'T{a[0]}{a[1][0].upper()}->T{b[0]}{b[1][0].upper()}': score_pair(neurons, prints, a, b)
                    for a, b in pairs(kind)} for kind in ('serial', 'contralateral')}
    serial = [r for rows in tasks['serial'].values() for r in rows]
    t1 = [r for name, rows in tasks['serial'].items() if name.startswith('T1') for r in rows]
    per_class = {}
    for cls in sorted({j for r in serial for j in r['joints']}):
        rows = [r for r in serial if cls in r['joints']]
        per_class[cls] = dict(n=len(rows), type_accuracy=accuracy(rows), joint_accuracy=accuracy(rows, 'joint_correct'))
    null_spec = spec['null']
    rng = np.random.default_rng(null_spec['seed'])
    observed = accuracy(serial)
    null = [permuted_serial_accuracy(neurons, prints, rng) for _ in range(null_spec['permutations'])]
    p = (1 + sum(v >= observed for v in null))/(null_spec['permutations'] + 1)
    gate = spec['acceptance']['PASS_requires_all']
    admitted_n = {c: per_class.get(c, {}).get('n', 0) for c in ADMITTED}
    checks = dict(
        a_pooled_serial_type_accuracy=observed >= gate['a_pooled_serial_type_accuracy_min'],
        b_permutation_p=p <= gate['b_permutation_p_max'],
        c_admitted_class_joint_accuracy=all(per_class.get(c, {}).get('joint_accuracy') is not None
            and per_class[c]['joint_accuracy'] >= gate['c_serial_joint_accuracy_min_per_admitted_class']['min'] for c in ADMITTED),
        d_T1_reference_serial_type_accuracy=accuracy(t1) is not None
            and accuracy(t1) >= gate['d_T1_reference_serial_type_accuracy_min'])
    if min(admitted_n.values()) < 10:
        verdict = 'INCONCLUSIVE'
    else:
        verdict = 'PASS' if all(checks.values()) else 'FAIL'
    contra = [r for rows in tasks['contralateral'].values() for r in rows]
    return dict(verdict=verdict, checks=checks, pooled_serial_type_accuracy=observed,
                pooled_serial_joint_accuracy=accuracy(serial, 'joint_correct'), serial_scored=len(serial),
                T1_reference_serial_type_accuracy=accuracy(t1), T1_reference_scored=len(t1),
                permutation=dict(p=p, null_mean=float(np.mean(null)), null_max=float(np.max(null))),
                per_joint_class_serial=per_class, admitted_class_serial_n=admitted_n,
                contralateral_descriptive=dict(type_accuracy=accuracy(contra), joint_accuracy=accuracy(contra, 'joint_correct'),
                                               scored=len(contra)),
                per_pair={kind: {name: dict(n=len(rows), type_accuracy=accuracy(rows)) for name, rows in t.items()}
                          for kind, t in tasks.items()},
                assignments=tasks)


def run(cache, data_dir=None):
    spec = protocol()
    data = load_cache(cache, **({'data_dir': data_dir} if data_dir else {}))
    from ..cache import _fingerprints
    from ..loader import DEFAULT_DATA_DIR
    sources = {k: v['sha256'] for k, v in _fingerprints(data_dir or DEFAULT_DATA_DIR).items()}
    if sources != spec['data']['canonical_sources_sha256']:
        return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, verdict='INCONCLUSIVE', reason='canonical source hash mismatch')
    neurons, ambiguous = labels(data.bodymap)
    prints, vocabulary, zero = fingerprints(data, neurons)
    result = evaluate(neurons, prints, spec)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, sources=sources,
                labeled_neurons=len(neurons), ambiguous_excluded=ambiguous, zero_typed_input_excluded=zero,
                presynaptic_type_features=len(vocabulary), **result,
                interpretation_limits=spec['interpretation_limits'])


def native(value):
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.cache)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        stream.write((json.dumps(native(result), indent=1, allow_nan=False) + '\n').encode())
    print(json.dumps(native({k: result.get(k) for k in ('verdict', 'checks', 'pooled_serial_type_accuracy',
          'T1_reference_serial_type_accuracy', 'permutation', 'admitted_class_serial_n')}), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
