"""Coxa motor hypothesis track, Steps D1 (action table) and D2 (H1/H2 bindings).

Preregistered in docs/evidence/coxa-hypothesis-v1/protocol.json; design in
docs/COXA_HYPOTHESIS_TRACK_V1.md. Geometry and data only: no CNS, no physics stepping.
The bindings are labelled hypotheses (COXA_HYPOTHESIS_H1/H2), never admissions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from .hair_plate_encoder import COXA_JOINTS, LEGS, SEGMENT, SIDE, BodyFrames, kinematics

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = 'docs/evidence/coxa-hypothesis-v1/protocol.json'
PROTOCOL_SHA256 = '147228696e2656a563f19167ef9b5862fff8bb95bc012ef6a327c7a18f708538'
SCHEMA = 'coxa-hypothesis-result-v1'
STEP = .01
MIN_COS = .5
LABEL_JOINT = {'coxa': 'Coxa', 'coxa_abduct': 'Coxa_roll', 'coxa_twist': 'Coxa_yaw'}
SWING = ('Tergopleural/Pleural promotor', 'Pleural remotor/abductor',
         'Sternal anterior rotator', 'Sternal posterior rotator')
ACTUATOR = re.compile(r'^(coxa|coxa_abduct|coxa_twist)_(T[123])_(left|right)$')
POOL = re.compile(r'^(.+) MN (T[123]) (left|right)$')
LEG_BASE = {leg: 7*k for k, leg in enumerate(LEGS)}  # action vector order LF LM LH RF RM RH


def protocol():
    raw = (ROOT/PROTOCOL).read_bytes()
    if PROTOCOL_SHA256 is None or hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('preregistered protocol changed')
    return json.loads(raw)


def action_index(leg, joint):
    return LEG_BASE[leg] + COXA_JOINTS.index(joint)


def leg_of(segment, side):
    return next(leg for leg in LEGS if SEGMENT[leg[1]] == segment and SIDE[leg[0]] == side)


def coxa_pools(bodymap):
    """{leg: {full pool name: dict(pool, dense, labels)}} from coxa-labelled bodymap muscles."""
    out = {leg: {} for leg in LEGS}
    for e in bodymap['muscles']:
        a = ACTUATOR.match(e.get('actuator', ''))
        if not a:
            continue
        p = POOL.match(e['name'])
        if not p or (p.group(2), p.group(3)) != (a.group(2), a.group(3)):
            raise ValueError('coxa muscle name/actuator mismatch: ' + e['name'])
        entry = out[leg_of(a.group(2), a.group(3))].setdefault(
            e['name'], dict(pool=p.group(1), dense=set(), labels=set()))
        entry['dense'].update(int(i) for i in e['idx'])
        entry['labels'].add(a.group(1))
    return out


def unit(v):
    v = np.asarray(v, float)
    return v/np.linalg.norm(v)


def action_vectors(model, data, frames):
    """{leg: {joint: [anterior, outward, dorsal]}} tip velocity per rad at the rest pose."""
    import mujoco
    tip = {leg: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, _body_name(model, leg + 'Tarsus5'))
           for leg in LEGS}
    saved = np.array(data.qpos, copy=True)

    def local(body):
        r = np.asarray(data.xmat[frames.thorax]).reshape(3, 3)
        return r.T @ (np.asarray(data.xpos[body]) - np.asarray(data.xpos[frames.thorax]))
    out = {}
    try:
        mujoco.mj_kinematics(model, data)
        for leg in LEGS:
            outward = 1. if local(frames.coxa[leg])[1] > 0 else -1.
            out[leg] = {}
            for j in COXA_JOINTS:
                ends = []
                for d in (STEP, -STEP):
                    data.qpos[:] = saved
                    data.qpos[frames.qpos[leg][j]] += d
                    mujoco.mj_kinematics(model, data)
                    ends.append(local(tip[leg]))
                v = (ends[0] - ends[1])/(2*STEP)
                out[leg][j] = [float(v[0]), float(outward*v[1]), float(v[2])]
    finally:
        data.qpos[:] = saved
        mujoco.mj_kinematics(model, data)
    return out


def _body_name(model, suffix):
    import mujoco
    hits = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(model.nbody)]
    hits = [n for n in hits if n and n.split('/')[-1] == suffix]
    if len(hits) != 1:
        raise ValueError('exact unique model element required: ' + suffix)
    return hits[0]


def walking_range(kin):
    return {leg: {j: float(np.ptp(np.asarray(kin[f'joint_{leg}{j}'], float))) for j in COXA_JOINTS} for leg in LEGS}


def assign(pools, vectors, named, restrict):
    """Per leg/pool: cosines, chosen joint and sign (or UNASSIGNED)."""
    out = {}
    for leg in LEGS:
        out[leg] = {}
        for name, p in sorted(pools[leg].items()):
            if p['pool'] not in named:
                raise ValueError('no named action for pool: ' + p['pool'])
            a = unit(named[p['pool']])
            joints = sorted({LABEL_JOINT[l] for l in p['labels']}) if restrict else list(COXA_JOINTS)
            cos = {j: float(a @ unit(vectors[leg][j])) for j in joints}
            best = max(joints, key=lambda j: (abs(cos[j]), -COXA_JOINTS.index(j)))
            ok = abs(cos[best]) >= MIN_COS
            out[leg][name] = dict(pool=p['pool'], candidates=joints, cos=cos,
                                  joint=best if ok else None, sign=int(np.sign(cos[best])) if ok else 0,
                                  status='ASSIGNED' if ok else 'UNASSIGNED')
    return out


def channels(assignment, body_ids):
    """Supplemental-channel definitions in the kernel's existing format."""
    out = {}
    for leg in LEGS:
        by_joint = {}
        for name, a in sorted(assignment[leg].items()):
            if a['joint']:
                by_joint.setdefault(a['joint'], {1: {}, -1: {}})[a['sign']][name] = tuple(sorted(body_ids[name]))
        for joint, sides in sorted(by_joint.items()):
            actuator = f'joint_{leg}{joint}'
            base = dict(actuator=actuator, action_index=action_index(leg, joint))
            if sides[1] and sides[-1]:
                out[actuator] = dict(base, decoder_mode='antagonist_pair', coordinate_sign=1,
                                     positive_populations=sides[1], negative_populations=sides[-1])
            else:
                sign = 1 if sides[1] else -1
                pops = sides[sign]
                out[actuator] = dict(base, decoder_mode='unidirectional_positive', coordinate_sign=sign,
                                     population_name=' + '.join(sorted(pops)),
                                     body_ids=tuple(sorted(i for ids in pops.values() for i in ids)))
    return out


def flipped(defs):
    return {k: dict(v, coordinate_sign=-v['coordinate_sign']) for k, v in defs.items()}


def swing_check(assignment, ranges):
    out = {}
    for leg in LEGS:
        counts = {}
        for a in assignment[leg].values():
            if a['joint'] and a['pool'] in SWING:
                counts[a['joint']] = counts.get(a['joint'], 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])
        swing = None if not top else ('SPLIT' if len(top) > 1 and top[0][1] == top[1][1] else top[0][0])
        walk = max(COXA_JOINTS, key=lambda j: ranges[leg][j])
        out[leg] = dict(swing_pool_counts=counts, h1_swing_joint=swing, largest_walking_range=walk,
                        match=swing == walk)
    return out


def audit_ids(audit):
    ids = {}
    for row in audit['rows']:
        for c in row.get('candidates') or ():
            prev = ids.setdefault(c['name'], tuple(sorted(int(i) for i in c['body_ids'])))
            if prev != tuple(sorted(int(i) for i in c['body_ids'])):
                raise ValueError('audit candidate identity conflict: ' + c['name'])
    return ids


def evaluate(vectors, ranges, pools, body_ids, audited, named, anterior, resolver=None):
    checks = dict(anterior=anterior > .99)
    checks['D1a_nonzero'] = all(np.all(np.isfinite(v)) and np.linalg.norm(v) > 1e-6
                                for leg in LEGS for v in vectors[leg].values())
    checks['D1b_step_b_sign'] = all(vectors[leg]['Coxa'][0] < 0 for leg in LEGS)
    h1 = assign(pools, vectors, named, restrict=False)
    h2 = assign(pools, vectors, named, restrict=True)
    defs = dict(H1=channels(h1, body_ids), H2=channels(h2, body_ids))
    defs['H1_FLIP'] = flipped(defs['H1'])
    identity = all(audited.get(name) == tuple(sorted(body_ids[name])) for leg in LEGS for name in pools[leg])
    accepted = True
    if resolver is not None:
        try:
            for d in defs.values():
                resolver(d)
        except ValueError:
            accepted = False
    checks['D2a_identity'] = identity and accepted
    if not checks['anterior']:
        status = 'INCONCLUSIVE'
    else:
        status = 'D1_D2_READY' if all(checks[k] for k in ('D1a_nonzero', 'D1b_step_b_sign', 'D2a_identity')) else 'NOT_READY'
    return dict(status=status, checks=checks, action_vectors=vectors, walking_range=ranges,
                assignment=dict(H1=h1, H2=h2), channels=defs,
                h2_identical_to_h1=_canon(defs['H1']) == _canon(defs['H2']),
                D1c_swing_cross_check=swing_check(h1, ranges))


def _canon(d):
    return json.dumps(d, sort_keys=True, default=list)


def run(cache):
    spec = protocol()
    import flygym
    from ..cache import load_cache
    from . import _windows_m7d_corrected_spontaneous_adapter as adapter
    from . import live_v3_motor_interface as v3
    from ._windows_m8_live_condition import _resolve_supplemental_channels
    raw = (ROOT/spec['sources']['audit']['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec['sources']['audit']['sha256']:
        raise ValueError('audit identity mismatch')
    audit = json.loads(raw)
    kin = kinematics(dict(basis=dict(kinematics=spec['sources']['kinematics'])))
    data = load_cache(cache)
    pools = coxa_pools(data.bodymap)
    body_ids = {name: [int(data.body_ids[i]) for i in sorted(p['dense'])] for leg in LEGS for name, p in pools[leg].items()}
    table = {r['actuator']: dict(action_index=r['action_index']) for r in audit['rows']}
    resolver = lambda d: _resolve_supplemental_channels(d, data, table, tuple(v3.V3_MOTOR))
    sim, physics, obs, _, _ = adapter._runtime(flygym, None)
    try:
        model, mdata = physics.model.ptr, physics.data.ptr
        frames = BodyFrames(model)
        anterior = frames.anterior_fraction(mdata)
        vectors = action_vectors(model, mdata, frames)
    finally:
        sim.close()
    result = evaluate(vectors, walking_range(kin), pools, body_ids, audit_ids(audit),
                      spec['D2']['named_actions'], anterior, resolver)
    return dict(schema=SCHEMA, protocol_sha256=PROTOCOL_SHA256, label='COXA_HYPOTHESIS (not admitted)',
                anterior_fraction=anterior,
                pools={leg: {n: dict(pool=p['pool'], labels=sorted(p['labels']), dense=sorted(p['dense']),
                                     body_ids=body_ids[n]) for n, p in pools[leg].items()} for leg in LEGS},
                **result, interpretation_limits=spec['interpretation_limits'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open('xb') as stream:  # exclusive: never overwrite evidence
        result = run(args.cache)
        stream.write((json.dumps(result, indent=1, allow_nan=False, default=list) + '\n').encode())
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'h2_identical_to_h1', 'D1c_swing_cross_check')}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
