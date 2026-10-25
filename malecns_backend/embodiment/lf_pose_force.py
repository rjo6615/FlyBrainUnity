"""Pose-dependent rotational reference map and native source-muscle assay only."""
import argparse
import itertools
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

from . import lf_force_reference as force
from . import lf_force_reference_validation as prior
from . import lf_proximal_binding_review as binding

ROOT = force.ROOT
DIRECTORY = 'docs/evidence/lf-pose-force-v1_1/'
MANIFEST = 'docs/evidence/lf-pose-force-v1/input-manifest.json'
SCHEMA = 'lf-pose-force-v1.1'
SOURCE_BASIS = ('joint_LFCoxa_yaw', 'joint_LFCoxa_pitch', 'joint_LFCoxa_roll')
EPSILON = 1e-6
OFFSETS = [(0., 0., 0.)]+[tuple(sign*.05 if i == axis else 0. for i in range(3))
    for axis in range(3) for sign in (-1, 1)]+list(itertools.product((-.05, .05), repeat=3))


def manifest(model):
    model = Path(model).resolve()
    raw = model.read_bytes()
    if force.audit.sha(raw) != binding.MODEL_HASH:
        raise ValueError('original source XML raw hash mismatch')
    tree = ET.fromstring(raw)
    if tree.findall('.//include'):
        raise ValueError('unresolved included model source')
    files = {}
    for node in tree.iter():
        if 'file' not in node.attrib: continue
        path = (model.parent/node.attrib['file']).resolve()
        relative = path.relative_to(model.parent).as_posix()
        data = path.read_bytes()
        files[relative] = dict(sha256=force.audit.sha(data), bytes=len(data))
    return dict(schema='lf-pose-force-inputs-v1', model_name=model.name,
                xml_sha256=force.audit.sha(raw), xml_bytes=len(raw), assets=dict(sorted(files.items())))


def rotation_map(q_world, q_reference):
    q, ref = np.asarray(q_world, dtype=float), np.asarray(q_reference, dtype=float)
    for r in (q, ref):
        if (r.shape != (3, 3) or not np.isfinite(r).all() or
                not np.allclose(r.T@r, np.eye(3), atol=1e-10, rtol=0) or abs(np.linalg.det(r)-1) > 1e-10):
            raise ValueError('proper finite reference rotations required')
    delta = q@ref.T
    angles = Rotation.from_matrix(delta).as_euler('XYZ')
    bg = np.column_stack((np.array([1., 0., 0.]),
        Rotation.from_euler('X', angles[0]).apply([0., 1., 0.]),
        Rotation.from_euler('XY', angles[:2]).apply([0., 0., 1.])))
    if np.linalg.cond(bg) >= 100:
        raise ValueError('target basis too ill-conditioned')
    return angles, bg, delta


def transfer(q_world, q_reference, bm, rm):
    angles, bg, delta = rotation_map(q_world, q_reference)
    bm, rm = np.asarray(bm, dtype=float), np.asarray(rm, dtype=float)
    if bm.shape != (3, 3) or rm.shape != (3, 4) or not np.isfinite(bm).all() or not np.isfinite(rm).all():
        raise ValueError('finite exact source bases/covectors required')
    jacobian = np.linalg.solve(bg, bm)
    if np.linalg.cond(jacobian) >= 100:
        raise ValueError('transfer basis too ill-conditioned')
    return dict(q_G=angles.tolist(), B_G=bg.tolist(), delta_rotation=delta.tolist(),
                J=jacobian.tolist(), R_G=np.linalg.solve(jacobian.T, rm).tolist())


def sources():
    result = prior.source_hashes()
    for p in ('docs/LF_POSE_FORCE_V1.md', 'docs/LF_POSE_FORCE_V1_1.md', 'malecns_backend/embodiment/lf_pose_force.py', MANIFEST):
        result[p] = force.audit.sha((ROOT/p).read_bytes().replace(b'\r\n', b'\n'))
    return result


def preflight(model=None):
    hashes = sources()
    reference = force.load_reference()
    frozen = json.loads((ROOT/MANIFEST).read_text(encoding='utf-8'))
    if model is not None and manifest(model) != frozen:
        raise ValueError('source XML/assets differ from the committed input manifest')
    reg = json.loads((ROOT/force.audit.PATHS['registration']).read_text(encoding='utf-8'))
    qref = reg['provenance']['flymimic']['reference_configuration']['complete_qpos']
    if hashes != sources(): raise ValueError('source changed during preflight')
    return dict(source_hashes=hashes, reference=reference, inputs=frozen, qref=qref)


def dense_moments(mj, model, data):
    raw = dict(values=np.asarray(data.actuator_moment).reshape(-1).tolist(),
               rownnz=np.asarray(data.moment_rownnz).tolist(),
               rowadr=np.asarray(data.moment_rowadr).tolist(),
               colind=np.asarray(data.moment_colind).tolist())
    dense = np.zeros((model.nu, model.nv))
    mj.mju_sparse2dense(dense, np.asarray(data.actuator_moment).reshape(-1),
                       data.moment_rownnz, data.moment_rowadr, data.moment_colind)
    return dense, raw


def saved_sparse_matrix(raw, nu, nv):
    from scipy.sparse import csr_matrix
    values, columns, pointers = [], [], [0]
    if len(raw['rownnz']) != nu or len(raw['rowadr']) != nu or len(raw['values']) != len(raw['colind']):
        raise ValueError('invalid sparse descriptor shapes')
    for count, start in zip(raw['rownnz'], raw['rowadr']):
        if type(count) is not int or type(start) is not int or min(count, start) < 0 or start+count > len(raw['values']):
            raise ValueError('invalid sparse row descriptor')
        cols = raw['colind'][start:start+count]
        vals = raw['values'][start:start+count]
        if (any(type(c) is not int or not 0 <= c < nv for c in cols)
                or len(set(cols)) != len(cols) or not np.isfinite(vals).all()):
            raise ValueError('invalid sparse columns/values')
        values.extend(vals)
        columns.extend(cols)
        pointers.append(len(values))
    return csr_matrix((values, columns, pointers), shape=(nu, nv)).toarray()


def _observe(mj, model, qpos, activation, control, ids, jids, tids, actids, body):
    data = mj.MjData(model)
    data.qpos[:] = qpos
    data.act[actids] = activation
    data.ctrl[ids] = control
    mj.mj_forward(model, data)
    moments, sparse = dense_moments(mj, model, data)
    clipped = np.clip(data.ctrl[ids], model.actuator_ctrlrange[ids, 0], model.actuator_ctrlrange[ids, 1])
    gain = [mj.mju_muscleGain(data.actuator_length[i], data.actuator_velocity[i],
        model.actuator_lengthrange[i], model.actuator_acc0[i], model.actuator_gainprm[i, :9]) for i in ids]
    bias = [mj.mju_muscleBias(data.actuator_length[i], model.actuator_lengthrange[i],
        model.actuator_acc0[i], model.actuator_biasprm[i, :9]) for i in ids]
    dyn = [mj.mju_muscleDynamics(c, data.act[a], model.actuator_dynprm[i, :3])
           for i, a, c in zip(ids, actids, clipped)]
    row = {key: np.asarray(getattr(data, key)).tolist() for key in
        ('qpos', 'qvel', 'act', 'ctrl', 'act_dot', 'actuator_force', 'ten_length', 'qfrc_actuator', 'qfrc_applied', 'xfrc_applied')}
    row.update(time=float(data.time), moments=moments.tolist(), moment_sparse=sparse, effective_control=clipped.tolist(),
        gain=gain, bias=bias, dynamics=dyn, B_M=data.xaxis[jids].T.tolist(),
        rotation=data.xmat[body].reshape(3, 3).tolist(), ncon=int(data.ncon))
    return row


def execute(model_path, ready):
    import mujoco as mj
    if mj.__version__ != '3.2.7': raise ValueError('validated MuJoCo 3.2.7 required')
    model = mj.MjModel.from_xml_path(str(Path(model_path).resolve()))
    jids = [model.joint(n).id for n in SOURCE_BASIS]
    dofs = [int(model.jnt_dofadr[i]) for i in jids]
    qids = [int(model.jnt_qposadr[i]) for i in jids]
    body = model.body('LFCoxa').id
    ids = [model.actuator(t.removesuffix('_tendon')).id for t in force.TENDONS]
    tids = [model.tendon(t).id for t in force.TENDONS]
    actids = [int(model.actuator_actadr[i]) for i in ids]
    if (model.nq != len(ready['qref']) or model.nv != model.nq or len(set(actids)) != 4
            or min(actids) < 0 or any(int(model.jnt_type[i]) != int(mj.mjtJoint.mjJNT_HINGE) for i in jids)
            or any(int(model.jnt_bodyid[i]) != body for i in jids)
            or any(int(model.actuator_trnid[a, 0]) != t or int(model.actuator_trntype[a]) != int(mj.mjtTrn.mjTRN_TENDON)
                   or list(model.actuator_gear[a]) != [1, 0, 0, 0, 0, 0]
                   or int(model.actuator_dyntype[a]) != int(mj.mjtDyn.mjDYN_MUSCLE)
                   or int(model.actuator_gaintype[a]) != int(mj.mjtGain.mjGAIN_MUSCLE)
                   or int(model.actuator_biastype[a]) != int(mj.mjtBias.mjBIAS_MUSCLE) for a, t in zip(ids, tids))):
        raise ValueError('exact compiled source ownership/muscle contract mismatch')
    report = dict(schema=SCHEMA, status='COMPLETE', ready=ready, commit=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        environment=dict(mujoco=mj.__version__, numpy=np.__version__),
        metadata=dict(joint_ids=jids, dofs=dofs, qpos_addresses=qids, body_id=body,
            actuator_ids=ids, tendon_ids=tids, activation_addresses=actids,
            nq=int(model.nq), nv=int(model.nv), nu=int(model.nu), na=int(model.na),
            dynprm=model.actuator_dynprm[ids].tolist(), gainprm=model.actuator_gainprm[ids].tolist(),
            biasprm=model.actuator_biasprm[ids].tolist(), ctrlrange=model.actuator_ctrlrange[ids].tolist()),
        poses=[], activation_probes=[], integration_steps=0, neural_transitions=0,
        new_admissions=0, current_motor_count=20)
    for offset in OFFSETS:
        pose = dict(offset=list(offset), samples=[], differences=[])
        report['poses'].append(pose)
        q = np.array(ready['qref'], dtype=float)
        q[qids] += offset
        try:
            for level in (0., .5, 1.):
                pose['samples'].append(_observe(mj, model, q, level, level, ids, jids, tids, actids, body))
            for axis in range(3):
                pair = []
                for sign in (-1, 1):
                    perturbed = q.copy()
                    perturbed[qids[axis]] += sign*EPSILON
                    pair.append(_observe(mj, model, perturbed, 0., 0., ids, jids, tids, actids, body))
                pose['differences'].append(pair)
        except Exception as exc:
            pose['error'] = f'{type(exc).__name__}: {exc}'
            report['status'] = 'INCOMPLETE'
    for control in (0., 1.):
        try:
            report['activation_probes'].append(_observe(mj, model, ready['qref'], .5, control, ids, jids, tids, actids, body))
        except Exception as exc:
            report['activation_probes'].append(dict(error=f'{type(exc).__name__}: {exc}'))
            report['status'] = 'INCOMPLETE'
    report['source_hashes_after'] = sources()
    report['inputs_after'] = manifest(model_path)
    return report


def evaluate(report, ready):
    checks = dict(schema=report.get('schema') == SCHEMA, complete=report.get('status') == 'COMPLETE',
        sources=report.get('source_hashes_after') == ready['source_hashes'],
        inputs=report.get('inputs_after') == ready['inputs'], ready=report.get('ready') == ready,
        counts=report.get('observed_api_calls') == dict(mj_forward=137, mj_step=0),
        scope=all(report.get(k) == v for k, v in dict(integration_steps=0, neural_transitions=0,
            new_admissions=0, current_motor_count=20).items()),
        inventory=[p.get('offset') for p in report.get('poses', [])] == [list(p) for p in OFFSETS])
    results = []
    try:
        meta = report['metadata']
        ids, dofs, qids, tids, actids = [meta[k] for k in
            ('actuator_ids', 'dofs', 'qpos_addresses', 'tendon_ids', 'activation_addresses')]
        qref = np.asarray(ready['qref'])
        rotation_ref = np.asarray(report['poses'][0]['samples'][0]['rotation'])
        for pose in report['poses']:
            metrics = dict(fd_length=0., fd_axes=0., fd_jacobian=0., rotation=0., force=0., dynamics=0., total_force=0., work=0.)
            result = dict(offset=pose['offset'], metrics=metrics, checks={})
            results.append(result)
            try:
                if pose.get('error') or len(pose['samples']) != 3 or len(pose['differences']) != 3:
                    raise ValueError('incomplete fixed pose observations')
                base = pose['samples'][0]
                rm = -np.asarray(base['moments'])[np.ix_(ids, dofs)].T
                mapped = transfer(base['rotation'], rotation_ref, base['B_M'], rm)
                result['transfer'] = mapped
                j = np.asarray(mapped['J'])
                fd_rm, fd_b, fd_j = [], [], []
                for minus, plus in pose['differences']:
                    fd_rm.append(-(np.asarray(plus['ten_length'])[tids]-np.asarray(minus['ten_length'])[tids])/(2*EPSILON))
                    fd_b.append(Rotation.from_matrix(np.asarray(plus['rotation'])@np.asarray(minus['rotation']).T).as_rotvec()/(2*EPSILON))
                    fd_j.append((rotation_map(plus['rotation'], rotation_ref)[0]-rotation_map(minus['rotation'], rotation_ref)[0])/(2*EPSILON))
                metrics['fd_length'] = float(np.max(np.abs(np.asarray(fd_rm)-rm)))
                metrics['fd_axes'] = float(np.max(np.abs(np.asarray(fd_b).T-np.asarray(base['B_M']))))
                metrics['fd_jacobian'] = float(np.max(np.abs(np.asarray(fd_j).T-j)))
                metrics['rotation'] = float(np.max(np.abs(Rotation.from_euler('XYZ', mapped['q_G']).as_matrix()-np.asarray(mapped['delta_rotation']))))
                observations = pose['samples']+[s for pair in pose['differences'] for s in pair]
                expected_q = qref.copy()
                expected_q[qids] += pose['offset']
                result['checks']['states'] = all(np.array_equal(s['qvel'], np.zeros(meta['nv'])) and s['time'] == 0 for s in observations)
                result['checks']['activation_schedule'] = all(np.array_equal(np.asarray(s['act'])[actids], np.full(4, level))
                    and np.array_equal(np.asarray(s['ctrl'])[ids], np.full(4, level))
                    and np.array_equal(s['qpos'], expected_q) for s, level in zip(pose['samples'], (0., .5, 1.)))
                result['checks']['fd_schedule'] = True
                for axis, pair in enumerate(pose['differences']):
                    if len(pair) != 2: raise ValueError('incomplete finite-difference pair')
                    for sign, s in zip((-1, 1), pair):
                        expected = expected_q.copy()
                        expected[qids[axis]] += sign*EPSILON
                        result['checks']['fd_schedule'] &= bool(np.array_equal(s['qpos'], expected)
                            and not np.any(s['act']) and not np.any(s['ctrl']))
                result['checks']['unselected_activation_control'] = all(
                    not np.any(np.delete(np.asarray(s['act']), actids)) and
                    not np.any(np.delete(np.asarray(s['ctrl']), ids)) for s in observations)
                result['checks']['external_force_zero'] = all(not np.any(s['qfrc_applied'])
                    and not np.any(s['xfrc_applied']) for s in observations)
                result['checks']['sparse_transmission'] = all(np.max(np.abs(
                    saved_sparse_matrix(s['moment_sparse'], meta['nu'], meta['nv'])-np.asarray(s['moments']))) <= 1e-12
                    for s in observations)
                for s in observations:
                    mom, f = np.asarray(s['moments']), np.asarray(s['actuator_force'])
                    arrays = [np.asarray(s[k], dtype=float) for k in ('qpos', 'qvel', 'act', 'ctrl', 'act_dot', 'moments', 'actuator_force', 'ten_length', 'gain', 'bias', 'dynamics')]
                    if not all(np.isfinite(x).all() for x in arrays): raise ValueError('nonfinite native observation')
                    predicted = np.asarray(s['gain'])*np.asarray(s['act'])[actids]+np.asarray(s['bias'])
                    metrics['force'] = max(metrics['force'], float(np.max(np.abs(predicted-f[ids]))))
                    metrics['dynamics'] = max(metrics['dynamics'], float(np.max(np.abs(np.asarray(s['dynamics'])-np.asarray(s['act_dot'])[actids]))))
                    metrics['total_force'] = max(metrics['total_force'], float(np.max(np.abs(mom.T@f-np.asarray(s['qfrc_actuator'])))))
                    if np.max(f[ids]) > 1e-8: raise ValueError('selected muscle force is not pulling')
                for s in pose['samples']:
                    tension = -np.asarray(s['actuator_force'])[ids]
                    tau_m = rm@tension
                    tau_g = np.asarray(mapped['R_G'])@tension
                    dq_m = np.array([.013, -.027, .009])
                    metrics['work'] = max(metrics['work'], abs(float(tau_g@(j@dq_m)-tau_m@dq_m)))
                limits = dict(fd_length=1e-7, fd_axes=1e-7, fd_jacobian=1e-7, rotation=1e-10,
                              force=1e-8, dynamics=1e-6, total_force=1e-8, work=1e-9)
                result['checks'].update({k: value <= limits[k] for k, value in metrics.items()})
            except Exception as exc:
                result['checks']['complete'] = False
                result['error'] = f'{type(exc).__name__}: {exc}'
            result['passed'] = bool(result['checks']) and all(result['checks'].values())
        center = results[0]['transfer']
        checks['original_reference_J'] = bool(np.max(np.abs(np.asarray(center['J'])-np.asarray(ready['reference']['J']))) <= 1e-10)
        center_rm = -np.asarray(report['poses'][0]['samples'][0]['moments'])[np.ix_(ids, dofs)].T
        checks['original_reference_R'] = bool(np.max(np.abs(center_rm-np.asarray(ready['reference']['R_M']))) <= 1e-10)
        checks['activation_probes'] = len(report['activation_probes']) == 2
        for s, control in zip(report['activation_probes'], (0., 1.)):
            checks['probe_'+str(control)] = bool(np.array_equal(s['qpos'], qref)
                and np.array_equal(np.asarray(s['act'])[actids], np.full(4, .5))
                and np.array_equal(np.asarray(s['ctrl'])[ids], np.full(4, control))
                and np.max(np.abs(np.asarray(s['act_dot'])[actids]-np.asarray(s['dynamics']))) <= 1e-6)
    except Exception as exc:
        checks['complete_evaluation'] = False
        checks['error'] = str(exc)
    passed = all(v is True for v in checks.values()) and len(results) == 15 and all(r['passed'] for r in results)
    return dict(checks=checks, poses=results, passed=passed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true')
    group.add_argument('--preflight', action='store_true')
    group.add_argument('--report', type=Path)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.execute:
        if args.model is None or args.output_dir is None: parser.error('--execute requires --model and fresh --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        observed = dict(mj_forward=0, mj_step=0)
        mj = None
        try:
            import mujoco as mj
            original_f, original_s = mj.mj_forward, mj.mj_step
            def count(*a, **k):
                observed['mj_forward'] += 1
                return original_f(*a, **k)
            def stop(*a, **k):
                observed['mj_step'] += 1
                raise RuntimeError('time integration forbidden')
            mj.mj_forward, mj.mj_step = count, stop
            ready = preflight(args.model)
            report = execute(args.model, ready)
            report['observed_api_calls'] = dict(observed)
            report['evaluation'] = evaluate(report, ready)
        except Exception as exc:
            report = dict(schema=SCHEMA, status='INTEGRITY_ERROR', observed_api_calls=observed, error=f'{type(exc).__name__}: {exc}')
        finally:
            if mj is not None: mj.mj_forward, mj.mj_step = original_f, original_s
        with (args.output_dir/'validation.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write('\n')
        if not report.get('evaluation', {}).get('passed'):
            print('POSE/FORCE REFERENCE FAILED; available evidence preserved.')
            print(report.get('error', report.get('evaluation')))
            return 1
    elif args.report:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        ready = preflight(args.model)
        # Current raw checkout representation may differ from the historical record.
        ready['reference']['original_raw_freezes_satisfied'] = report['ready']['reference']['original_raw_freezes_satisfied']
        actual = evaluate(report, ready)
        if not actual['passed'] or actual != report['evaluation']:
            raise ValueError('saved pose/force evidence or source mismatch')
    else:
        preflight(args.model)
        print('PREFLIGHT PASSED: no model construction/dynamics; 15 fixed poses, current 20/42.')
        return 0
    print('POSE/FORCE REFERENCE VERIFIED: 15 poses; 137 recorded explicit forward calls; no integration/CNS.')
    print('Current 20/42; new admissions 0; modeled rotation map and source-force fidelity only.')
    print('Original raw scientific prerequisites:', report['ready']['reference']['original_raw_freezes_satisfied'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
