"""Versioned native reference-fixture check; saved review never reruns dynamics."""
import argparse
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from . import lf_force_reference as force

ROOT = force.ROOT
SCHEMA = 'lf-force-reference-validation-v1.1'
CASES = (('ZERO', (0., 0., 0., 0.)), ('REMOTOR', (1., 0., 0., 0.)),
         ('ADDUCTOR', (0., 1., 0., 0.)), ('ANTERIOR', (0., 0., 1., 0.)),
         ('POSTERIOR', (0., 0., 0., 1.)), ('MIXED', (.25, .5, .75, 1.)))
SOURCES = ('docs/LF_FORCE_REFERENCE_V1.md', 'docs/LF_FORCE_REFERENCE_V1_1.md', force.FIXTURE,
           'malecns_backend/embodiment/lf_force_static_reference.py',
           'malecns_backend/embodiment/_windows_m7_spontaneous_locomotion_adapter.py',
           'malecns_backend/embodiment/integrated_whole_leg_readiness.py',
           'malecns_backend/embodiment/lf_force_reference.py',
           'malecns_backend/embodiment/lf_force_reference_validation.py',
           'malecns_backend/embodiment/six_tibia_physics_diagnostic.py',
           'malecns_backend/embodiment/body.py', 'malecns_backend/embodiment/motor.py',
           'malecns_backend/embodiment/_windows_m8_live_condition.py',
           force.crosswalk.DIRECTORY+'crosswalk.json', force.crosswalk.SOURCE)


def source_hashes():
    paths = set(SOURCES) | set(force.audit.PATHS.values()) | set(force.audit.SOURCES) | set(force.crosswalk.SOURCES)
    result = {}
    for p in sorted(paths):
        raw = (ROOT/p).read_bytes()
        if Path(p).suffix in ('.py', '.json', '.md', '.xml'):
            raw = raw.replace(b'\r\n', b'\n')
        result[p] = force.audit.sha(raw)
    return result


def preflight():
    before = source_hashes()
    reference = force.load_reference()
    if before != source_hashes():
        raise ValueError('source changed during preflight')
    return dict(schema=SCHEMA, status='PREFLIGHT_PASSED', reference=reference,
                source_hashes=before, integration_steps=0, neural_transitions=0,
                native_forward_calls=0, new_admissions=0, current_motor_count=20)


def _snapshot(mujoco, model, data):
    mass = np.empty((model.nv, model.nv))
    mujoco.mj_fullM(model, mass, data.qM)
    result = {key: np.asarray(getattr(data, key)).tolist() for key in
              ('qpos', 'qvel', 'qacc', 'qfrc_applied', 'xfrc_applied', 'qfrc_bias',
               'qfrc_passive', 'qfrc_constraint', 'qfrc_actuator', 'actuator_force', 'ctrl')}
    return dict(result, mass_matrix=mass.tolist(), time=float(data.time),
                ncon=int(data.ncon), nefc=int(data.nefc))


def execute(ready):
    import mujoco
    if mujoco.__version__ != '3.2.7':
        raise ValueError('validated MuJoCo 3.2.7 required; no environment upgrade')
    model = mujoco.MjModel.from_xml_path(str(ROOT/force.FIXTURE))
    report = dict(schema=SCHEMA, status='COMPLETE', reference=ready['reference'],
        source_hashes_before=ready['source_hashes'], protocol_commit=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        environment=dict(python=platform.python_version(), numpy=np.__version__, mujoco=mujoco.__version__),
        integration_steps=0, neural_transitions=0, new_admissions=0, current_motor_count=20,
        native_forward_calls=0, model_dimensions=dict(nq=int(model.nq), nv=int(model.nv), nu=int(model.nu), nbody=int(model.nbody)),
        cases=[])
    for name, tensions in CASES:
        row = dict(name=name, tensions=list(tensions), snapshots={})
        report['cases'].append(row)
        try:
            data = mujoco.MjData(model)
            mujoco.mj_forward(model, data)
            report['native_forward_calls'] += 1
            row['snapshots']['baseline'] = _snapshot(mujoco, model, data)
            adapter = force.ReferenceForceAdapter(model, data, ready['reference'])
            row['metadata'] = adapter.metadata
            row['projected_torque'] = adapter.apply(tensions).tolist()
            mujoco.mj_forward(model, data)
            report['native_forward_calls'] += 1
            row['snapshots']['applied'] = _snapshot(mujoco, model, data)
            adapter.clear()
            mujoco.mj_forward(model, data)
            report['native_forward_calls'] += 1
            row['snapshots']['cleared'] = _snapshot(mujoco, model, data)
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
            report['status'] = 'INCOMPLETE'
    report['source_hashes_after'] = source_hashes()
    return report


def _array(row, key, shape):
    value = np.asarray(row[key], dtype=float)
    if value.shape != shape or not np.isfinite(value).all():
        raise ValueError('invalid saved native array: '+key)
    return value


def evaluate(report, reference):
    checks = dict(schema=report.get('schema') == SCHEMA, complete=report.get('status') == 'COMPLETE',
        source_unchanged=report.get('source_hashes_before') == report.get('source_hashes_after'),
        reference=report.get('reference') == reference,
        operations=report.get('native_forward_calls') == 18 and report.get('integration_steps') == 0
            and report.get('neural_transitions') == 0 and report.get('new_admissions') == 0
            and report.get('current_motor_count') == 20,
        observed_api_calls=report.get('observed_python_api_calls') == dict(mj_forward=18, mj_step=0),
        dimensions=report.get('model_dimensions') == dict(nq=11, nv=10, nu=0, nbody=6),
        version=report.get('environment', {}).get('mujoco') == '3.2.7',
        case_inventory=[r.get('name') for r in report.get('cases', [])] == [c[0] for c in CASES])
    result = []
    j = np.asarray(reference['J'])
    rm = np.asarray(reference['R_M'])
    dq_m = np.array([.013, -.027, .009])
    q0 = np.zeros(11)
    q0[3] = 1.
    for row, (name, tensions) in zip(report.get('cases', []), CASES):
        c = dict(name=name, checks={}, maximum_force_error=0., maximum_dynamics_residual=0., work_error=0.)
        result.append(c)
        try:
            if row.get('error') or row['tensions'] != list(tensions):
                raise ValueError('condition incomplete or tension schedule changed')
            metadata = row['metadata']
            c['checks']['exact_metadata'] = (len(metadata) == 3 and all(
                r['resolved'] and r['joint_name'] == target and r['body_name'] == body and r['joint_type'] == 'hinge'
                and r['joint_id'] == i+2 and r['dof_address_range'] == [i+7, i+8]
                and r['qpos_address_range'] == [i+8, i+9] and r['dof_index'] == i+7 and not r['actuators']
                for i, (r, target, body) in enumerate(zip(metadata, force.BASIS, force.BODY_NAMES))))
            torque = np.linalg.inv(j).T @ (rm @ np.asarray(tensions))
            c['checks']['adapter_projection'] = bool(np.max(np.abs(_array(row, 'projected_torque', (3,))-torque)) <= 1e-12)
            c['checks']['snapshots_complete'] = set(row['snapshots']) == {'baseline', 'applied', 'cleared'}
            for phase in ('baseline', 'applied', 'cleared'):
                s = row['snapshots'][phase]
                applied = _array(s, 'qfrc_applied', (10,))
                expected = np.zeros(10)
                if phase == 'applied': expected[7:10] = torque
                error = float(np.max(np.abs(applied-expected)))
                c['maximum_force_error'] = max(c['maximum_force_error'], error)
                c['checks'][phase+'_force'] = bool(error <= 1e-12 and np.array_equal(applied[:7], np.zeros(7)))
                c['checks'][phase+'_state'] = bool(np.array_equal(_array(s, 'qpos', (11,)), q0)
                    and np.array_equal(_array(s, 'qvel', (10,)), np.zeros(10)) and s['time'] == 0 and s['ncon'] == s['nefc'] == 0)
                c['checks'][phase+'_other_forces_zero'] = bool(all(np.count_nonzero(_array(s, k, shape)) == 0 for k, shape in
                    (('xfrc_applied', (6, 6)), ('qfrc_bias', (10,)), ('qfrc_passive', (10,)),
                     ('qfrc_constraint', (10,)), ('qfrc_actuator', (10,)), ('actuator_force', (0,)), ('ctrl', (0,)))))
                mass = _array(s, 'mass_matrix', (10, 10))
                accel = _array(s, 'qacc', (10,))
                residual = float(np.max(np.abs(mass @ accel-applied)))
                c['maximum_dynamics_residual'] = max(c['maximum_dynamics_residual'], residual)
                c['checks'][phase+'_dynamics'] = bool(residual <= 1e-10
                    and np.allclose(mass, mass.T, atol=1e-12, rtol=0) and np.min(np.linalg.eigvalsh(mass)) > 0)
                if phase != 'applied':
                    c['checks'][phase+'_zero_acceleration'] = bool(np.max(np.abs(accel)) <= 1e-10 and np.count_nonzero(applied) == 0)
            observed = np.asarray(row['snapshots']['applied']['qfrc_applied'])[7:10]
            c['work_error'] = abs(float(observed @ (j @ dq_m)-(rm @ tensions) @ dq_m))
            c['checks']['virtual_work'] = c['work_error'] <= 1e-12
        except Exception as exc:
            c['error'] = f'{type(exc).__name__}: {exc}'
            c['checks']['complete_valid_case'] = False
        c['passed'] = bool(c['checks']) and all(c['checks'].values())
    return dict(checks=checks, cases=result,
                passed=all(checks.values()) and len(result) == 6 and all(c['passed'] for c in result))


def verify(path):
    saved = json.loads(Path(path).read_text(encoding='utf-8'))
    ready = preflight()
    recorded_reference = dict(ready['reference'])
    old_raw = saved.get('reference', {}).get('original_raw_freezes_satisfied')
    if type(old_raw) is not bool:
        raise ValueError('recorded original raw-freeze flag required')
    recorded_reference['original_raw_freezes_satisfied'] = old_raw
    evaluation = evaluate(saved, recorded_reference)
    if (saved['source_hashes_before'] != ready['source_hashes'] or not evaluation['passed']
            or evaluation != saved.get('evaluation')):
        raise ValueError('saved fixture checks or source/reference mismatch')
    return saved, ready


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--preflight', action='store_true')
    modes.add_argument('--execute', action='store_true')
    modes.add_argument('--report', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.execute:
        if args.output_dir is None: parser.error('--execute requires a fresh --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        native = None
        observed = dict(mj_forward=0, mj_step=0)
        try:
            import mujoco as native
            original_forward, original_step = native.mj_forward, native.mj_step
            def counted_forward(*a, **k):
                observed['mj_forward'] += 1
                return original_forward(*a, **k)
            def forbidden_step(*a, **k):
                observed['mj_step'] += 1
                raise RuntimeError('time integration is forbidden in this fixture protocol')
            native.mj_forward, native.mj_step = counted_forward, forbidden_step
            report = execute(preflight())
            report['observed_python_api_calls'] = dict(observed)
            report['evaluation'] = evaluate(report, report['reference'])
        except Exception as exc:
            report = dict(schema=SCHEMA, status='INTEGRITY_ERROR', integration_steps=0,
                          neural_transitions=0, new_admissions=0, observed_python_api_calls=dict(observed),
                          error=f'{type(exc).__name__}: {exc}')
        finally:
            if native is not None:
                native.mj_forward, native.mj_step = original_forward, original_step
        with (args.output_dir/'validation.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write('\n')
        if not report.get('evaluation', {}).get('passed'):
            print('FIXTURE FAILED; complete available evidence retained.')
            print(report.get('error', report.get('evaluation')))
            return 1
    elif args.report:
        if args.output_dir is not None: parser.error('--output-dir only applies to --execute')
        report, _ = verify(args.report)
    else:
        if args.output_dir is not None: parser.error('--output-dir only applies to --execute')
        ready = preflight()
        print('PREFLIGHT PASSED: current 20/42; 4 class hypotheses; native forward calls 0; CNS/integration 0.')
        print('Original raw scientific prerequisites:', ready['reference']['original_raw_freezes_satisfied'])
        return 0
    print('FIXTURE VERIFIED: 6 cases; 18 recorded explicit native fixture forward calls; integration/CNS transitions 0.')
    print('Current 20/42; new admissions 0; no neural activation/force calibration or moving-fly transfer.')
    print('Original raw scientific prerequisites:', report['reference']['original_raw_freezes_satisfied'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
