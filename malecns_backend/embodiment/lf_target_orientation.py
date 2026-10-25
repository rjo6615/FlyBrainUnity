"""Prospective native LF orientation assay; kinematics only, no muscle coupling."""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy.spatial.transform import Rotation

from . import lf_unit_lineage as lineage
from . import lf_native_isolation as native

ROOT = native.ROOT
DIRECTORY = 'docs/evidence/lf-target-orientation-v1/'
SCHEMA = 'lf-target-orientation-v1'
POSE_RECORD = native.pose.DIRECTORY+'run/validation.json'
POSE_SHA = '24332543da1d4b8a1c475bef518c334058cb95c9ecad8c5a4173c0043d0449fe'
NATIVE_RECORD = native.DIRECTORY+'run/validation.json'
LINEAGE_RECORD = lineage.DIRECTORY+'run/audit.json'
EPSILON = native.pose.EPSILON
KIN_FIELDS = ('body_parentid', 'body_pos', 'body_quat', 'jnt_pos', 'jnt_axis', 'qpos0')


def sources():
    result = native.sources() | lineage.source_hashes()
    for path in (POSE_RECORD, NATIVE_RECORD, LINEAGE_RECORD,
                 'docs/LF_TARGET_ORIENTATION_V1.md', 'malecns_backend/embodiment/lf_target_orientation.py'):
        raw = (ROOT/path).read_bytes()
        result[path] = lineage.sha(raw if path in (POSE_RECORD, NATIVE_RECORD) else raw.replace(b'\r\n', b'\n'))
    if result[POSE_RECORD] != POSE_SHA:
        raise ValueError('original source-pose raw record changed')
    if result[NATIVE_RECORD] != 'ee3ddfe2e9d298d3b3f269ab04c114d7f3a332ebc68ea20c184deb7b1df2a628':
        raise ValueError('original accepted native record changed')
    return result


def preflight():
    before = sources()
    _, audited = lineage.verify(ROOT/LINEAGE_RECORD)
    source = native.load_report(ROOT/POSE_RECORD)
    source_ready = native.pose.preflight()
    source_ready['reference']['original_raw_freezes_satisfied'] = source['ready']['reference']['original_raw_freezes_satisfied']
    if not native.pose.evaluate(source, source_ready)['passed']:
        raise ValueError('original source-pose evaluator failed')
    source_reference = source['poses'][0]['samples'][0]['rotation']
    plans = []
    for row in source['poses']:
        base = row['samples'][0]
        meta = source['metadata']
        rm = -np.asarray(base['moments'])[np.ix_(meta['actuator_ids'], meta['dofs'])].T
        mapped = native.pose.transfer(base['rotation'], source_reference, base['B_M'], rm)
        chain = [[native.pose.rotation_map(sample['rotation'], source_reference)[0].tolist()
                  for sample in pair] for pair in row['differences']]
        plans.append(dict(offset=row['offset'], mapped=mapped, source_basis=base['B_M'], chain_angles=chain))
    old = native.load_report(ROOT/NATIVE_RECORD)
    if sources() != before:
        raise ValueError('sources changed during static orientation preflight')
    return dict(sources=before, installed_inputs=native.installed_inputs(), plans=plans,
        expected_model=old['models']['BASELINE'], original_raw_freezes_satisfied=audited['current_original_raw_freezes_satisfied'])


def angles_for(plan):
    center = np.asarray(plan['mapped']['q_G'])
    return [('BASE', center)]+[(f'TARGET_{i}_{sign}', center+sign*EPSILON*np.eye(3)[i])
        for i in range(3) for sign in (-1, 1)]+[(f'CHAIN_{i}_{sign}', np.asarray(value))
        for i, pair in enumerate(plan['chain_angles']) for sign, value in zip((-1, 1), pair)]


def exact_frames(inv, arrays):
    selected = native.targets(inv)
    if ([r['joint_id'] for r in selected] != [1, 2, 3]
            or [r['qpos_range'] for r in selected] != [[7, 8], [8, 9], [9, 10]]
            or [r['dof_range'] for r in selected] != [[6, 7], [7, 8], [8, 9]]
            or [r['action_index'] for r in selected] != [2, 0, 1]
            or any(r['body_id'] != 13 or native.namespace_component(r['body_name']) != 'LFCoxa' for r in selected)):
        raise ValueError('exact original LF joint/body/address contract required')
    thorax = [i for i, n in enumerate(inv['names']['body']) if native.namespace_component(n) == 'Thorax']
    if len(thorax) != 1:
        raise ValueError('unique native Thorax required')
    parents, path, current = arrays['body_parentid'], [], 13
    while current:
        if current in path: raise ValueError('cyclic native body ancestry')
        path.append(current); current = parents[current]
    if thorax[0] not in path:
        raise ValueError('Thorax is not an ancestor of exact LFCoxa body')
    return dict(thorax_id=thorax[0], coxa_id=13, joint_ids=[1, 2, 3], qpos_addresses=[7, 8, 9], ancestry=path)


@contextmanager
def accounting(mj):
    # Reuse the existing six-entry integration prohibition and phase counters.
    with native.native_accounting(mj) as (counts, phase):
        original_k, original_f, original_r = mj.mj_kinematics, mj.mj_forward, mj.mj_resetData
        for values in counts.values(): values['mj_kinematics'] = 0
        def kin(*args, **kwargs):
            counts[phase[0]]['mj_kinematics'] += 1
            return original_k(*args, **kwargs)
        def guarded(function, name):
            def call(*args, **kwargs):
                if phase[0] == 'probes':
                    counts['probes'][name] += 1
                    raise ValueError('forward/reset prohibited during kinematic probes')
                return function(*args, **kwargs)
            return call
        mj.mj_kinematics, mj.mj_forward, mj.mj_resetData = kin, guarded(original_f, 'mj_forward'), guarded(original_r, 'mj_resetData')
        try: yield counts, phase
        finally: mj.mj_kinematics, mj.mj_forward, mj.mj_resetData = original_k, original_f, original_r


def observe(mj, model, center, frames, angles, label):
    data = mj.MjData(model)
    data.qpos[:] = center
    data.qpos[frames['qpos_addresses']] = angles
    for key in native.STATE[1:]: getattr(data, key)[:] = 0
    data.time = 0.
    before = native.state(data)
    mj.mj_kinematics(model, data)
    return dict(label=label, angles=np.asarray(angles).tolist(), before=before, after=native.state(data),
        thorax_rotation=data.xmat[frames['thorax_id']].reshape(3, 3).tolist(),
        coxa_rotation=data.xmat[frames['coxa_id']].reshape(3, 3).tolist(),
        world_axes=data.xaxis[frames['joint_ids']].T.tolist())


def execute(ready):
    import mujoco as mj
    import flygym
    from .tactile_motor_loop_audit import _make_live
    report = dict(schema=SCHEMA, status='INCOMPLETE', ready=ready, cases=[], models={}, initializer_calls=0,
        current_motor_count=20, new_admissions=0, physics_transitions=0, cns_transitions=0,
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    sim = None
    with accounting(mj) as (counts, phase):
        try:
            report['initializer_calls'] += 1
            sim, physics, *_ = _make_live(flygym, {})
            model, initial = physics.model.ptr, physics.data
            inv = native.inventory(physics.model, sim.flies[0])
            inv.update(nq=int(model.nq), nv=int(model.nv))
            report['inventory'] = inv
            report['models']['BEFORE'] = native.physics_model_identity(physics.model, initial)
            native.validate_inventory(inv, report['models']['BEFORE'])
            if report['models']['BEFORE'] != ready['expected_model']:
                raise ValueError('full native baseline differs from original isolation context')
            report['kinematic_arrays'] = {k: np.asarray(getattr(model, k)).tolist() for k in KIN_FIELDS}
            report['frames'] = frames = exact_frames(inv, report['kinematic_arrays'])
            report['center'] = np.asarray(initial.qpos).tolist()
            phase[0] = 'probes'
            report['reference'] = observe(mj, model, report['center'], frames, np.zeros(3), 'REFERENCE_ZERO')
            for plan in ready['plans']:
                case = dict(offset=plan['offset'], samples=[]); report['cases'].append(case)
                for label, q in angles_for(plan):
                    case['samples'].append(observe(mj, model, report['center'], frames, q, label))
            report['models']['AFTER'] = native.physics_model_identity(physics.model, initial)
            report['status'] = 'COMPLETE'
        except Exception as exc:
            report['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            if sim is not None: sim.close()
            report['api_calls'] = counts
    report['sources_after'] = sources()
    report['installed_inputs_after'] = native.installed_inputs()
    return report


def relative(sample):
    return np.asarray(sample['thorax_rotation']).T@sample['coxa_rotation']


def basis(sample):
    return np.asarray(sample['thorax_rotation']).T@sample['world_axes']


def derivative(minus, plus):
    return Rotation.from_matrix(relative(plus)@relative(minus).T).as_rotvec()/(2*EPSILON)


def metrics(samples, reference, plan):
    base = samples[0]
    observed = basis(base)
    j = np.linalg.solve(observed, plan['source_basis'])
    target_fd = np.column_stack([derivative(*samples[1+2*i:3+2*i]) for i in range(3)])
    chain_fd = np.column_stack([derivative(*samples[7+2*i:9+2*i]) for i in range(3)])
    error = lambda a, b: float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
    return dict(rotation=error(relative(base)@relative(reference).T, plan['mapped']['delta_rotation']),
        basis=error(observed, plan['mapped']['B_G']), target_fd=error(target_fd, observed),
        jacobian=error(j, plan['mapped']['J']), chain_fd=error(chain_fd, plan['source_basis']),
        basis_condition=float(np.linalg.cond(observed)), jacobian_condition=float(np.linalg.cond(j)))


def evaluate(report, ready):
    checks = dict(schema=report.get('schema') == SCHEMA, complete=report.get('status') == 'COMPLETE',
        ready=report.get('ready') == ready, sources=report.get('sources_after') == ready['sources'],
        installed=report.get('installed_inputs_after') == ready['installed_inputs'],
        scope=all(report.get(k) == v for k, v in dict(initializer_calls=1, current_motor_count=20,
            new_admissions=0, physics_transitions=0, cns_transitions=0).items()),
        whole_pose_inventory=[r.get('offset') for r in report.get('cases', [])] == [list(p) for p in native.pose.OFFSETS])
    rows, limits = [], []
    try:
        inv, arrays = report['inventory'], report['kinematic_arrays']
        checks['inventory'] = native.validate_inventory(inv, report['models']['BEFORE'])
        checks['frames'] = report['frames'] == exact_frames(inv, arrays)
        checks['models_unchanged'] = report['models']['BEFORE'] == report['models']['AFTER'] == ready['expected_model']
        checks['model_identity_digest'] = all(v['sha256'] == lineage.sha(json.dumps(v['components'],
            sort_keys=True, separators=(',', ':'), allow_nan=False).encode()) for v in report['models'].values())
        checks['kinematic_table_identity'] = all(native._canonical_array_identity(np.asarray(arrays[k],
            dtype=report['models']['BEFORE']['components']['model_arrays'][k]['dtype'])) ==
            report['models']['BEFORE']['components']['model_arrays'][k] for k in KIN_FIELDS)
        center_record = report['models']['BEFORE']['components']['initial_state']['qpos']
        checks['center_identity'] = native._canonical_array_identity(np.asarray(report['center'],
            dtype=center_record['dtype'])) == center_record
        checks['accounting'] = report['api_calls'] == {p: dict(mj_forward=f, mj_resetData=r,
            mj_kinematics=k, **{name: 0 for name in native.INTEGRATORS})
            for p, f, r, k in [('initialization', 7, 3, 0), ('probes', 0, 0, 196)]}
        reference, frames = report['reference'], report['frames']
        observations = [(reference, 'REFERENCE_ZERO', np.zeros(3))]
        for case, plan in zip(report['cases'], ready['plans']):
            expected = angles_for(plan)
            if len(case['samples']) != 13: raise ValueError('complete thirteen-sample pose required')
            observations.extend((s, label, angle) for s, (label, angle) in zip(case['samples'], expected))
            values = metrics(case['samples'], reference, plan)
            numerical = all(values[key] <= bound for key, bound in
                [('rotation', 1e-10), ('basis', 1e-10), ('target_fd', 1e-7), ('jacobian', 1e-7), ('chain_fd', 1e-7)])
            numerical &= values['basis_condition'] < 100 and values['jacobian_condition'] < 100
            rows.append(dict(offset=case['offset'], metrics=values, numerical_passed=bool(numerical)))
        valid_states, proper = True, True
        for sample, label, angle in observations:
            q = np.asarray(report['center']).copy(); q[frames['qpos_addresses']] = angle
            state = sample['before']
            valid_states &= (sample['label'] == label and sample['angles'] == angle.tolist()
                and state == sample['after'] and state['qpos'] == q.tolist() and state['time'] == 0
                and all(not np.any(state[k]) for k in native.STATE[1:]))
            shapes = dict(qpos=(inv['nq'],), qvel=(inv['nv'],), act=(0,), ctrl=(48,),
                          qfrc_applied=(inv['nv'],), xfrc_applied=(len(inv['names']['body']), 6))
            valid_states &= all(np.asarray(state[k]).shape == shape and np.isfinite(state[k]).all()
                                for k, shape in shapes.items())
            for key in ('thorax_rotation', 'coxa_rotation'):
                r = np.asarray(sample[key]); proper &= (r.shape == (3, 3) and np.isfinite(r).all()
                    and np.max(np.abs(r.T@r-np.eye(3))) <= 1e-10 and abs(np.linalg.det(r)-1) <= 1e-10)
            proper &= np.array_equal(sample['thorax_rotation'], reference['thorax_rotation'])
            proper &= np.asarray(sample['world_axes']).shape == (3, 3) and np.isfinite(sample['world_axes']).all()
            jids = frames['joint_ids']; bounds = np.asarray(inv['joints']['range'])[jids]
            limited = np.asarray(inv['joints']['limited'], dtype=bool)[jids]
            limits.append(bool(np.all(angle[limited] >= bounds[limited, 0]) and np.all(angle[limited] <= bounds[limited, 1])))
        checks['all_196_states'] = bool(valid_states and len(observations) == 196)
        checks['proper_frames_and_axes'] = bool(proper)
        reference_error = float(np.max(np.abs(basis(reference)-np.eye(3))))
    except Exception as exc:
        checks['evaluation_complete'] = False; checks['error'] = str(exc)
        reference_error = None
    integrity = all(v is True for v in checks.values()) and len(rows) == 15
    in_range = len(limits) == 196 and all(limits)
    numerical = reference_error is not None and reference_error <= 1e-10 and all(r['numerical_passed'] for r in rows) and len(rows) == 15
    classification = ('TARGET_ORIENTATION_INTEGRITY_FAILURE' if not integrity else
        'TARGET_ORIENTATION_OUTSIDE_NATIVE_LIMITS_TRANSFER_BLOCKED' if not in_range else
        'TARGET_ORIENTATION_GEOMETRY_VERIFIED_TRANSFER_BLOCKED' if numerical else
        'TARGET_ORIENTATION_DISAGREEMENT_TRANSFER_BLOCKED')
    return dict(checks=checks, cases=rows, reference_basis_error=reference_error,
        all_samples_in_range=in_range, sample_range_checks=limits, numerical_passed=bool(numerical),
        integrity_passed=integrity, classification=classification)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--report', type=Path)
    group.add_argument('--preflight', action='store_true'); parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.preflight:
        preflight(); print('ORIENTATION PREFLIGHT VERIFIED; no model or native execution.'); return 0
    if args.execute:
        if args.output_dir is None: parser.error('--execute requires fresh --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        try:
            ready = preflight(); report = execute(ready); report['evaluation'] = evaluate(report, ready)
        except Exception as exc: report = dict(schema=SCHEMA, status='ERROR', error=f'{type(exc).__name__}: {exc}')
        with (args.output_dir/'validation.json').open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(native.encode_nonfinite(report), indent=2, allow_nan=False)+'\n')
    else:
        report = native.load_report(args.report)
        ready = preflight()
        ready['original_raw_freezes_satisfied'] = report['ready']['original_raw_freezes_satisfied']
        if evaluate(report, ready) != report['evaluation']:
            raise ValueError('saved orientation evidence/evaluation differs')
    evaluated = report.get('evaluation', {})
    if not evaluated.get('integrity_passed'):
        print('ORIENTATION INTEGRITY FAILED; evidence retained.', report.get('error', evaluated)); return 1
    print('ORIENTATION EVIDENCE VERIFIED:', evaluated['classification'])
    print('15 poses;196 recorded kinematics probes;0 probe forwards/integration/CNS. Saved review executes none.')
    print('Maximum errors:', {k: max(r['metrics'][k] for r in evaluated['cases'])
        for k in ('rotation', 'basis', 'target_fd', 'jacobian', 'chain_fd')})
    print('Roadmap:20/42; new admissions0; physical/anatomical/neural/raw transfer gates remain open; no new Unity behavior.')
    print('Original raw prerequisites:', report['ready']['original_raw_freezes_satisfied'])
    return 0


if __name__ == '__main__': raise SystemExit(main())
