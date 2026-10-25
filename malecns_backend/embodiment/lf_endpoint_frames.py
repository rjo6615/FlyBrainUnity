"""Paired source endpoint/native body-frame measurements; no target muscle sites."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy.spatial.transform import Rotation

from . import lf_route_attachment as route

o = route.orientation
n = o.native
ROOT = route.ROOT
DIRECTORY = 'docs/evidence/lf-endpoint-frames-v1/'
SCHEMA = 'lf-endpoint-frames-v1'
AUDIT = route.DIRECTORY+'run/audit.json'
ARRAYS = tuple(dict.fromkeys((*o.KIN_FIELDS, 'jnt_bodyid', 'jnt_qposadr', 'jnt_dofadr', 'jnt_range', 'jnt_limited',
    'site_bodyid', 'site_pos', 'geom_bodyid', 'geom_dataid', 'geom_pos', 'geom_quat',
    'mesh_pos', 'mesh_quat', 'mesh_scale', 'tendon_adr', 'tendon_num', 'wrap_type', 'wrap_objid',
    *('actuator_'+key for key in n.ACT_FIELDS))))


def sources():
    result = route.sources()
    for p in (AUDIT, 'docs/LF_ENDPOINT_FRAMES_V1.md', 'malecns_backend/embodiment/lf_endpoint_frames.py'):
        result[p] = o.lineage.sha((ROOT/p).read_bytes().replace(b'\r\n', b'\n'))
    return result


def preflight(model_path=None):
    before = sources()
    _, audit = route.verify(ROOT/AUDIT)
    snapshot = o.lineage.transfer.read(route.SNAPSHOT)
    route.inspect_assets(snapshot, model_path)
    orient = n.load_report(ROOT/route.UPSTREAM)
    source = n.load_report(ROOT/o.POSE_RECORD)
    plans = []
    meta = source['metadata']
    for row, target in zip(source['poses'], orient['cases']):
        src = [row['samples'][0]]+[sample for pair in row['differences'] for sample in pair]
        dst = [target['samples'][0]]+target['samples'][7:]
        samples = [dict(source_qpos=s['qpos'], source_rotation=s['rotation'],
            old_lengths=np.asarray(s['ten_length'])[meta['tendon_ids']].tolist(),
            target_angles=t['angles'], target_thorax=t['thorax_rotation'], target_coxa=t['coxa_rotation'])
            for s, t in zip(src, dst)]
        rm = -np.asarray(row['samples'][0]['moments'])[np.ix_(meta['actuator_ids'], meta['dofs'])].T
        plans.append(dict(offset=row['offset'], samples=samples, old_moment_arms=rm.tolist()))
    if sources() != before: raise ValueError('source changed during static endpoint preflight')
    return dict(sources=before, installed_inputs=n.installed_inputs(), plans=plans, source_metadata=meta,
        source_routes=snapshot['files']['source_xml']['extract']['routes'],
        source_bodies=snapshot['files']['source_xml']['extract']['bodies'],
        target_bodies=snapshot['files']['target_xml']['extract']['bodies'],
        target_center=orient['center'], target_reference=orient['reference'],
        expected_target_model=orient['models']['BEFORE'],
        original_raw_freezes_satisfied=audit['current_original_raw_freezes_satisfied'])


def metadata(model, data, bodies):
    identity = n.physics_model_identity(model, data)
    names = {kind: [n.compiled_name(model, kind, i) for i in range(int(getattr(model, count)))]
        for kind, count in [('body', 'nbody'), ('geom', 'ngeom'), ('site', 'nsite'), ('mesh', 'nmesh'),
                            ('joint', 'njnt'), ('actuator', 'nu'), ('tendon', 'ntendon')]}
    def exact(kind, name):
        found = [i for i, value in enumerate(names[kind]) if n.namespace_component(value) == name]
        if len(found) != 1: raise ValueError('unique compiled identity required: '+name)
        return found[0]
    body_ids = [exact('body', row['body']['name']) for row in bodies]
    geom_ids = [exact('geom', row['geom']['name']) for row in bodies]
    arrays = {key: np.asarray(getattr(model, key)).tolist() for key in ARRAYS}
    if any(int(model.geom_bodyid[g]) != b or names['mesh'][int(model.geom_dataid[g])] != row['mesh']['name']
           for g, b, row in zip(geom_ids, body_ids, bodies)):
        raise ValueError('compiled geom/body/mesh ownership mismatch')
    return dict(identity=identity, names=names, arrays=arrays, body_ids=body_ids, geom_ids=geom_ids)


def validate_metadata(meta, expected_bodies):
    ident, arrays, names = meta['identity'], meta['arrays'], meta['names']
    if ident['sha256'] != o.lineage.sha(json.dumps(ident['components'], sort_keys=True, separators=(',', ':'), allow_nan=False).encode()):
        raise ValueError('model identity digest mismatch')
    for key in ARRAYS:
        expected = ident['components']['model_arrays'][key]
        if n._canonical_array_identity(np.asarray(arrays[key], dtype=expected['dtype'])) != expected:
            raise ValueError('compiled table/hash mismatch: '+key)
    if len(meta['body_ids']) != 2 or len(set(meta['body_ids'])) != 2 or len(meta['geom_ids']) != 2:
        raise ValueError('two exact body/geom carriers required')
    for kind in ('body', 'geom', 'site', 'joint', 'actuator'):
        if [n.namespace_component(s) for s in names[kind]] != ident['components']['inventories'][kind]:
            raise ValueError('compiled name inventory differs')
    for row, bid, gid in zip(expected_bodies, meta['body_ids'], meta['geom_ids']):
        if (n.namespace_component(names['body'][bid]) != row['body']['name']
                or n.namespace_component(names['geom'][gid]) != row['geom']['name']
                or arrays['geom_bodyid'][gid] != bid
                or names['mesh'][arrays['geom_dataid'][gid]] != row['mesh']['name']):
            raise ValueError('exact body/geom/mesh link differs')
    return True


def resolve_sites(model, ready, meta):
    names = [s['attributes']['name'] for row in ready['source_routes'] for s in row['sites']]
    ids = [int(model.site(name).id) for name in names]
    if len(set(ids)) != 8: raise ValueError('eight unique compiled source sites required')
    for sid, site in zip(ids, [s for row in ready['source_routes'] for s in row['sites']]):
        owner = int(model.body(site['owner_body']).id)
        if (model.site_bodyid[sid] != owner or not np.array_equal(model.site_pos[sid], site['local_position'])):
            raise ValueError('compiled source local site/body definition differs')
    expected = ready['source_metadata']
    if (any(int(getattr(model, k)) != expected[k] for k in ('nq', 'nv', 'nu', 'na'))
            or [int(model.joint(name).id) for name in n.pose.SOURCE_BASIS] != expected['joint_ids']
            or [int(model.tendon(name).id) for name in route.TENDONS] != expected['tendon_ids']
            or [int(model.actuator(name.removesuffix('_tendon')).id) for name in route.TENDONS] != expected['actuator_ids']):
        raise ValueError('original source indices/dimensions differ')
    if meta['body_ids'][1] != expected['body_id']: raise ValueError('original source Coxa ID differs')
    for tid, pair in zip(expected['tendon_ids'], np.asarray(ids).reshape(4, 2)):
        start, count = int(model.tendon_adr[tid]), int(model.tendon_num[tid])
        if (count != 2 or model.wrap_type[start:start+2].tolist() != [3, 3]
                or model.wrap_objid[start:start+2].tolist() != pair.tolist()):
            raise ValueError('exact two-SITE compiled tendon path required')
    return ids


def observe(mj, model, qpos, meta, site_ids=()):
    data = mj.MjData(model); data.qpos[:] = qpos
    for key in n.STATE[1:]: getattr(data, key)[:] = 0
    data.time = 0.
    before = n.state(data); mj.mj_kinematics(model, data)
    return dict(before=before, after=n.state(data),
        body_positions=data.xpos[meta['body_ids']].tolist(),
        body_rotations=data.xmat[meta['body_ids']].reshape(2, 3, 3).tolist(),
        geom_positions=data.geom_xpos[meta['geom_ids']].tolist(),
        geom_rotations=data.geom_xmat[meta['geom_ids']].reshape(2, 3, 3).tolist(),
        source_site_positions=data.site_xpos[list(site_ids)].reshape(len(site_ids), 3).tolist())


def execute(model_path, ready):
    import mujoco as mj
    import flygym
    from .tactile_motor_loop_audit import _make_live
    report = dict(schema=SCHEMA, status='INCOMPLETE', ready=ready, cases=[],
        physics_transitions=0, cns_transitions=0, current_motor_count=20, new_admissions=0,
        source_compilations=0, target_initializers=0,
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    sim = None
    with o.accounting(mj) as (counts, phase):
        try:
            report['source_compilations'] += 1
            source = mj.MjModel.from_xml_path(str(Path(model_path).resolve())); source_data = mj.MjData(source)
            report['source'] = sm = metadata(source, source_data, ready['source_bodies'])
            ids = resolve_sites(source, ready, sm); report['source_site_ids'] = ids
            report['target_initializers'] += 1
            sim, physics, *_ = _make_live(flygym, {})
            target, initial = physics.model.ptr, physics.data
            report['target'] = tm = metadata(physics.model, initial, ready['target_bodies'])
            inv = n.inventory(physics.model, sim.flies[0]); inv.update(nq=int(target.nq), nv=int(target.nv))
            n.validate_inventory(inv, tm['identity'])
            if tm['identity'] != ready['expected_target_model'] or tm['body_ids'] != [3, 13]:
                raise ValueError('original native target context differs')
            phase[0] = 'probes'
            q = np.asarray(ready['target_center']).copy(); q[[7, 8, 9]] = 0
            report['target_reference'] = observe(mj, target, q, tm)
            for plan in ready['plans']:
                case = dict(offset=plan['offset'], samples=[]); report['cases'].append(case)
                for sample in plan['samples']:
                    q = np.asarray(ready['target_center']).copy(); q[[7, 8, 9]] = sample['target_angles']
                    case['samples'].append(dict(source=observe(mj, source, sample['source_qpos'], sm, ids),
                                              target=observe(mj, target, q, tm)))
            report['source_after'] = n.physics_model_identity(source, source_data)
            report['target_after'] = n.physics_model_identity(physics.model, initial)
            report['status'] = 'COMPLETE'
        except Exception as exc: report['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            if sim is not None: sim.close()
            report['api_calls'] = counts
    try:
        report['sources_after'] = sources(); report['installed_after'] = n.installed_inputs()
        report['source_inputs_after'] = n.pose.manifest(model_path)
    except Exception as exc:
        report.update(status='INCOMPLETE', postflight_error=f'{type(exc).__name__}: {exc}')
    return report


def lengths(points):
    a = np.asarray(points).reshape(4, 2, 3)
    return np.linalg.norm(a[:, 1]-a[:, 0], axis=1)


def local_to_world(position, rotation, local):
    return np.asarray(position)+np.asarray(rotation)@local


def error(a, b): return float(np.max(np.abs(np.asarray(a)-np.asarray(b))))


def frame_errors(sample, meta, site_ids):
    a = meta['arrays']; bids, gids = meta['body_ids'], meta['geom_ids']
    local_error = 0.
    for i, sid in enumerate(site_ids):
        owner = bids.index(a['site_bodyid'][sid])
        expected = local_to_world(sample['body_positions'][owner], sample['body_rotations'][owner], a['site_pos'][sid])
        local_error = max(local_error, error(expected, sample['source_site_positions'][i]))
    geom_error = 0.
    for i, gid in enumerate(gids):
        expected = local_to_world(sample['body_positions'][i], sample['body_rotations'][i], a['geom_pos'][gid])
        rot = Rotation.from_quat(np.roll(a['geom_quat'][gid], -1)).as_matrix()
        geom_error = max(geom_error, error(expected, sample['geom_positions'][i]),
                         error(np.asarray(sample['body_rotations'][i])@rot, sample['geom_rotations'][i]))
    return local_error, geom_error


def evaluate(report, ready):
    checks = dict(schema=report.get('schema') == SCHEMA, complete=report.get('status') == 'COMPLETE',
        ready=report.get('ready') == ready, sources=report.get('sources_after') == ready['sources'],
        installed=report.get('installed_after') == ready['installed_inputs'],
        source_inputs=report.get('source_inputs_after') == o.lineage.transfer.read(n.pose.MANIFEST),
        scope=all(report.get(k) == v for k, v in dict(source_compilations=1, target_initializers=1,
            physics_transitions=0, cns_transitions=0, current_motor_count=20, new_admissions=0).items()),
        poses=[r.get('offset') for r in report.get('cases', [])] == [list(p) for p in n.pose.OFFSETS])
    rows, limits = [], []
    try:
        sm, tm, ids = report['source'], report['target'], report['source_site_ids']
        checks['metadata'] = validate_metadata(sm, ready['source_bodies']) and validate_metadata(tm, ready['target_bodies'])
        checks['models'] = sm['identity'] == report['source_after'] and tm['identity'] == report['target_after'] == ready['expected_target_model']
        checks['accounting'] = report['api_calls'] == {p: dict(mj_forward=f, mj_resetData=r, mj_kinematics=k,
            **{name: 0 for name in n.INTEGRATORS}) for p, f, r, k in [('initialization', 7, 3, 0), ('probes', 0, 0, 211)]}
        definitions = [s for row in ready['source_routes'] for s in row['sites']]
        checks['site_ownership'] = len(ids) == len(set(ids)) == 8 and all(
            sm['names']['site'][sid] == site['attributes']['name']
            and sm['names']['body'][sm['arrays']['site_bodyid'][sid]] == site['owner_body']
            and sm['arrays']['site_pos'][sid] == site['local_position'] for sid, site in zip(ids, definitions))
        meta = ready['source_metadata']; a = sm['arrays']
        checks['source_indices'] = sm['body_ids'][1] == meta['body_id'] and all(a['jnt_bodyid'][j] == meta['body_id']
            and sm['names']['joint'][j] == name and a['jnt_qposadr'][j] == q and a['jnt_dofadr'][j] == d
            for name, j, q, d in zip(n.pose.SOURCE_BASIS, meta['joint_ids'], meta['qpos_addresses'], meta['dofs']))
        checks['source_transmission'] = all(sm['names']['tendon'][tid] == name
            and sm['names']['actuator'][aid] == name.removesuffix('_tendon')
            and a['actuator_trnid'][aid] == [tid, -1] and a['actuator_trntype'][aid] == 3
            and a['actuator_gear'][aid] == [1., 0., 0., 0., 0., 0.]
            and a['actuator_actadr'][aid] == act and all(a['actuator_'+field][aid] == meta[field][i]
                for field in ('dynprm', 'gainprm', 'biasprm', 'ctrlrange'))
            for i, (name, tid, aid, act) in enumerate(zip(route.TENDONS, meta['tendon_ids'], meta['actuator_ids'], meta['activation_addresses'])))
        checks['tendon_paths'] = all(a['tendon_num'][tid] == 2 and a['wrap_type'][a['tendon_adr'][tid]:a['tendon_adr'][tid]+2] == [3, 3]
            and a['wrap_objid'][a['tendon_adr'][tid]:a['tendon_adr'][tid]+2] == ids[2*i:2*i+2] for i, tid in enumerate(meta['tendon_ids']))
        observations = [(report['target_reference'], tm, np.asarray(ready['target_center']).copy(), [], [1, 2, 3])]
        observations[0][2][[7, 8, 9]] = 0
        proper, numerical_reference = True, True
        ref = report['target_reference']
        numerical_reference &= error(ref['body_rotations'][0], ready['target_reference']['thorax_rotation']) <= 1e-10
        numerical_reference &= error(ref['body_rotations'][1], ready['target_reference']['coxa_rotation']) <= 1e-10
        for case, plan in zip(report['cases'], ready['plans']):
            if len(case['samples']) != 7: raise ValueError('whole seven-sample pose required')
            metrics = dict(endpoint=0., length=0., derivative=0., orientation=0., geom=0.)
            all_lengths = []
            for pair, expected in zip(case['samples'], plan['samples']):
                s, t = pair['source'], pair['target']; q = np.asarray(ready['target_center']).copy(); q[[7, 8, 9]] = expected['target_angles']
                observations.extend([(s, sm, np.asarray(expected['source_qpos']), ids, meta['joint_ids']), (t, tm, q, [], [1, 2, 3])])
                se, sg = frame_errors(s, sm, ids); _, tg = frame_errors(t, tm, [])
                observed = lengths(s['source_site_positions']); all_lengths.append(observed)
                metrics['endpoint'] = max(metrics['endpoint'], se)
                metrics['length'] = max(metrics['length'], error(observed, expected['old_lengths']))
                metrics['geom'] = max(metrics['geom'], sg, tg)
                metrics['orientation'] = max(metrics['orientation'], error(s['body_rotations'][1], expected['source_rotation']),
                    error(t['body_rotations'][0], expected['target_thorax']), error(t['body_rotations'][1], expected['target_coxa']))
            derivative = np.asarray([-(all_lengths[2+2*i]-all_lengths[1+2*i])/(2*o.EPSILON) for i in range(3)])
            metrics['derivative'] = error(derivative, plan['old_moment_arms'])
            passed = all(v <= (1e-7 if k == 'derivative' else 1e-10) for k, v in metrics.items())
            rows.append(dict(offset=case['offset'], metrics=metrics, numerical_passed=passed,
                source_coxa_origin_in_thorax=(np.asarray(case['samples'][0]['source']['body_rotations'][0]).T@
                    (np.asarray(case['samples'][0]['source']['body_positions'][1])-case['samples'][0]['source']['body_positions'][0])).tolist(),
                target_coxa_origin_in_thorax=(np.asarray(case['samples'][0]['target']['body_rotations'][0]).T@
                    (np.asarray(case['samples'][0]['target']['body_positions'][1])-case['samples'][0]['target']['body_positions'][0])).tolist()))
        states = True
        for sample, model, q, site_ids, joints in observations:
            state = sample['before']; dims = model['identity']['components']['dimensions']
            shapes = dict(qpos=(dims['nq'],), qvel=(dims['nv'],), act=(dims['na'],), ctrl=(dims['nu'],),
                qfrc_applied=(dims['nv'],), xfrc_applied=(dims['nbody'], 6))
            states &= state == sample['after'] and state['qpos'] == q.tolist() and state['time'] == 0 and all(not np.any(state[k]) for k in n.STATE[1:])
            states &= all(np.asarray(state[k]).shape == shape and np.isfinite(state[k]).all() for k, shape in shapes.items())
            for key, shape in [('body_positions', (2, 3)), ('body_rotations', (2, 3, 3)), ('geom_positions', (2, 3)), ('geom_rotations', (2, 3, 3)), ('source_site_positions', (len(site_ids), 3))]:
                value = np.asarray(sample[key]); actual_shape = value.shape if value.size else (0, 3)
                proper &= actual_shape == shape and np.isfinite(value).all()
            for rotation in sample['body_rotations']+sample['geom_rotations']:
                proper &= error(np.asarray(rotation).T@rotation, np.eye(3)) <= 1e-10 and abs(np.linalg.det(rotation)-1) <= 1e-10
            arr = model['arrays']; angles = q[np.asarray(arr['jnt_qposadr'])[joints]]
            bounds = np.asarray(arr['jnt_range'])[joints]; limited = np.asarray(arr['jnt_limited'], dtype=bool)[joints]
            limits.append(bool(np.all(angles[limited] >= bounds[limited, 0]) and np.all(angles[limited] <= bounds[limited, 1])))
        checks['all_states'] = bool(states and len(observations) == 211)
        checks['finite_proper_frames'] = bool(proper)
        checks['target_no_sites_added'] = tm['identity']['components']['dimensions']['ntendon'] == 0 and ref['source_site_positions'] == []
    except Exception as exc:
        checks['evaluation_complete'] = False; checks['error'] = str(exc); numerical_reference = False
    integrity = all(v is True for v in checks.values()) and len(rows) == 15
    in_range = len(limits) == 211 and all(limits)
    numerical = bool(numerical_reference and len(rows) == 15 and all(r['numerical_passed'] for r in rows))
    classification = ('ENDPOINT_FRAME_INTEGRITY_FAILURE' if not integrity else 'ENDPOINT_FRAME_OUTSIDE_LIMITS_TRANSFER_BLOCKED' if not in_range else
        'ENDPOINT_FRAME_OBSERVER_VERIFIED_TRANSFER_BLOCKED' if numerical else 'ENDPOINT_FRAME_DISAGREEMENT_TRANSFER_BLOCKED')
    return dict(checks=checks, cases=rows, sample_range_checks=limits, all_samples_in_range=in_range,
        numerical_passed=numerical, integrity_passed=integrity, classification=classification)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--report', type=Path)
    group.add_argument('--preflight', action='store_true'); parser.add_argument('--model', type=Path); parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.preflight: preflight(args.model); print('ENDPOINT PREFLIGHT VERIFIED; no native construction.'); return 0
    if args.execute:
        if args.model is None or args.output_dir is None: parser.error('--execute requires original --model and fresh --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        try:
            ready = preflight(args.model); report = execute(args.model, ready); report['evaluation'] = evaluate(report, ready)
        except Exception as exc: report = dict(schema=SCHEMA, status='ERROR', error=f'{type(exc).__name__}: {exc}')
        with (args.output_dir/'validation.json').open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(n.encode_nonfinite(report), indent=2, allow_nan=False)+'\n')
    else:
        report = n.load_report(args.report); ready = preflight(args.model)
        ready['original_raw_freezes_satisfied'] = report['ready']['original_raw_freezes_satisfied']
        if evaluate(report, ready) != report['evaluation']: raise ValueError('saved endpoint/frame evidence differs')
    evaluated = report.get('evaluation', {})
    if not evaluated.get('integrity_passed'):
        print('ENDPOINT INTEGRITY FAILED; evidence retained.', report.get('error', evaluated)); return 1
    print('ENDPOINT EVIDENCE VERIFIED:', evaluated['classification'])
    print('15 poses;105source/106target recorded kinematics;0 probe forwards/integration/CNS. Saved review executes none.')
    print('Maximum errors:', {k: max(r['metrics'][k] for r in evaluated['cases']) for k in ('endpoint', 'length', 'derivative', 'orientation', 'geom')})
    print('Roadmap:20/42;new admissions0;target attachments/units/neural/raw gates open;no new Unity behavior.')
    return 0


if __name__ == '__main__': raise SystemExit(main())
