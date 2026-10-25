"""Native activation-only transient assay; numerical failures remain explicit."""
import argparse
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
from scipy.integrate import solve_ivp

from . import lf_pose_force as pose

ROOT = pose.ROOT
DIRECTORY = 'docs/evidence/lf-activation-transient-v1/'
FIXTURE = 'docs/fixtures/lf-activation-transient-v1.xml'
BINDING = DIRECTORY+'source-binding.json'
UPSTREAM = pose.DIRECTORY+'run/validation.json'
SCHEMA = 'lf-activation-transient-v1'
DTS = (1e-4, 5e-5, 2.5e-5)
CONDITIONS = ('RELAX_ZERO', 'FLOOR_BASELINE', 'PULSE')
DURATION = .01


def raw_control(condition, step, dt):
    if condition not in CONDITIONS: raise ValueError('unknown transient condition')
    return 1. if condition == 'PULSE' and round(.002/dt) <= step < round(.005/dt) else 0.


def generate_fixture(source_xml):
    """Static extraction, before outcomes; no source physiology or clamp changes."""
    raw = Path(source_xml).read_bytes()
    registration = json.loads((ROOT/pose.force.audit.PATHS['registration']).read_text(encoding='utf-8'))
    inspected = pose.binding.inspect_model(raw, pose.binding.MODEL_HASH,
        [r['flymimic_tendon'] for r in registration['muscle_mechanics']])
    reference = json.loads((ROOT/UPSTREAM).read_text(encoding='utf-8'))
    ready = pose.preflight()
    ready['reference']['original_raw_freezes_satisfied'] = reference['ready']['reference']['original_raw_freezes_satisfied']
    if not pose.evaluate(reference, ready)['passed']: raise ValueError('accepted pose/source-force evidence required')
    sample = reference['poses'][0]['samples'][0]
    ids, tids = reference['metadata']['actuator_ids'], reference['metadata']['tendon_ids']
    lengths = np.asarray(sample['ten_length'])[tids].tolist()
    xml = ET.Element('mujoco', model='lf_activation_transient_v1')
    ET.SubElement(xml, 'compiler', angle='radian', autolimits='true')
    ET.SubElement(xml, 'option', timestep='0.0001', integrator='Euler', gravity='0 0 0')
    default = ET.SubElement(ET.SubElement(xml, 'default'), 'default', {'class': 'muscle'})
    ET.SubElement(default, 'general', inspected['muscle_default'])
    world, tendon, actuators = [ET.SubElement(xml, k) for k in ('worldbody', 'tendon', 'actuator')]
    selected = []
    by_name = {r['tendon']: r for r in inspected['bindings']}
    for index, (name, length) in enumerate(zip(pose.force.TENDONS, lengths)):
        if not np.isfinite(length) or length <= 0: raise ValueError('positive frozen reference length required')
        ET.SubElement(world, 'site', name=f'origin_{index}', pos=f'0 {index} 0')
        ET.SubElement(world, 'site', name=f'insertion_{index}', pos=f'{length!r} {index} 0')
        spatial = ET.SubElement(tendon, 'spatial', name=name)
        ET.SubElement(spatial, 'site', site=f'origin_{index}')
        ET.SubElement(spatial, 'site', site=f'insertion_{index}')
        attrs = dict(by_name[name]['actuator_attributes'])
        ET.SubElement(actuators, 'general', attrs)
        selected.append(dict(tendon=name, length=length, source_attributes=attrs))
    ET.indent(xml)
    text = ET.tostring(xml, encoding='unicode')+'\n'
    binding = dict(schema='lf-activation-source-binding-v1', source_xml_sha256=pose.binding.MODEL_HASH,
        upstream_sha256=pose.force.audit.sha((ROOT/UPSTREAM).read_bytes()),
        fixture_sha256=pose.force.audit.sha(text.encode()), selected=selected,
        muscle_default=inspected['muscle_default'],
        frozen_forces=[np.asarray(s['actuator_force'])[ids].tolist() for s in reference['poses'][0]['samples']],
        frozen_gain=sample['gain'], frozen_bias=sample['bias'],
        dynprm=reference['metadata']['dynprm'], gainprm=reference['metadata']['gainprm'],
        biasprm=reference['metadata']['biasprm'], ctrlrange=reference['metadata']['ctrlrange'])
    return text, binding


def sources():
    hashes = pose.sources()
    for p in ('docs/LF_ACTIVATION_TRANSIENT_V1.md', 'malecns_backend/embodiment/lf_activation_transient.py', BINDING, FIXTURE, UPSTREAM):
        raw = (ROOT/p).read_bytes()
        # Native upstream evidence is LFS/-text; preserve its exact original bytes.
        hashes[p] = pose.force.audit.sha(raw if p == UPSTREAM else raw.replace(b'\r\n', b'\n'))
    return hashes


def preflight():
    before = sources()
    binding = json.loads((ROOT/BINDING).read_text(encoding='utf-8'))
    if pose.force.audit.sha((ROOT/UPSTREAM).read_bytes()) != binding['upstream_sha256']:
        raise ValueError('source force evidence raw hash mismatch')
    if pose.force.audit.sha((ROOT/FIXTURE).read_bytes().replace(b'\r\n', b'\n')) != binding['fixture_sha256']:
        raise ValueError('fixed fixture content hash mismatch')
    reference = json.loads((ROOT/UPSTREAM).read_text(encoding='utf-8'))
    ready = pose.preflight()
    ready['reference']['original_raw_freezes_satisfied'] = reference['ready']['reference']['original_raw_freezes_satisfied']
    if not pose.evaluate(reference, ready)['passed']: raise ValueError('upstream pose/force evaluation failed')
    if before != sources(): raise ValueError('source changed during static preflight')
    return dict(sources=before, binding=binding,
        original_raw_freezes_satisfied=reference['ready']['reference']['original_raw_freezes_satisfied'])


def continuous_reference(mj, params, floor, condition, times):
    initial = np.zeros(4) if condition == 'RELAX_ZERO' else floor.copy()
    result = np.empty((len(times), 4))
    for start, end in ((0., .002), (.002, .005), (.005, .01)):
        control = np.ones(4) if condition == 'PULSE' and start == .002 else floor
        def rhs(t, state):
            return [mj.mju_muscleDynamics(float(c), float(a), p[:3]) for c, a, p in zip(control, state, params)]
        solved = solve_ivp(rhs, (start, end), initial, method='DOP853', rtol=1e-11, atol=1e-13,
                           max_step=2.5e-6, dense_output=True)
        if not solved.success: raise ValueError('independent reference ODE failed: '+solved.message)
        selected = (times >= start-1e-14)&(times <= end+1e-14)
        result[selected] = solved.sol(times[selected]).T
        initial = solved.y[:, -1]
    return result


def execute(ready):
    import mujoco as mj
    if mj.__version__ != '3.2.7': raise ValueError('validated MuJoCo3.2.7 required')
    report = dict(schema=SCHEMA, status='COMPLETE', ready=ready, commit=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), mujoco=mj.__version__,
        neural_transitions=0, body_joint_transitions=0, new_admissions=0, current_motor_count=20,
        reference_solver=dict(method='DOP853', rtol=1e-11, atol=1e-13, max_step=2.5e-6),
        calibrations=[], cases=[])
    reference_cache = {}
    for dt_index, dt in enumerate(DTS):
        model = mj.MjModel.from_xml_path(str(ROOT/FIXTURE))
        model.opt.timestep = dt  # The fixed numerical grid, not a production parameter change.
        if (model.nq or model.nv or model.nu != 4 or model.na != 4 or model.ntendon != 4
                or np.any(model.actuator_actearly) or model.ngeom):
            raise ValueError('zero-DOF, four source muscle states and actearly=false required')
        if any(not np.array_equal(getattr(model, 'actuator_'+key), ready['binding'][key])
               for key in ('dynprm', 'gainprm', 'biasprm', 'ctrlrange')):
            raise ValueError('compiled source muscle parameters changed')
        if dt_index == 0:
            report['compiled'] = dict(nq=int(model.nq), nv=int(model.nv), nu=int(model.nu), na=int(model.na),
                ntendon=int(model.ntendon), actlimited=model.actuator_actlimited.tolist(),
                actrange=model.actuator_actrange.tolist(), actearly=model.actuator_actearly.tolist(),
                dynprm=model.actuator_dynprm.tolist(), ctrlrange=model.actuator_ctrlrange.tolist())
            for level in (0., .5, 1.):
                d = mj.MjData(model)
                d.act[:] = level
                d.ctrl[:] = level
                mj.mj_forward(model, d)
                report['calibrations'].append(dict(level=level, force=d.actuator_force.tolist(), length=d.actuator_length.tolist()))
        floor = np.clip(np.zeros(4), model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
        steps = round(DURATION/dt)
        times = np.arange(steps+1)*dt
        if not reference_cache:
            fine_times = np.arange(round(DURATION/DTS[-1])+1)*DTS[-1]
            reference_cache = {c: continuous_reference(mj, model.actuator_dynprm, floor, c, fine_times)
                               for c in CONDITIONS}
        for condition in CONDITIONS:
            case = dict(dt=dt, condition=condition, steps=[])
            report['cases'].append(case)
            try:
                reference = reference_cache[condition][::round(dt/DTS[-1])]
                case['reference_activations'] = reference.tolist()
                d = mj.MjData(model)
                d.act[:] = np.zeros(4) if condition == 'RELAX_ZERO' else floor
                mj.mj_forward(model, d)
                case['initial'] = dict(activation=d.act.tolist(), force=d.actuator_force.tolist(), time=float(d.time))
                for index in range(steps):
                    control = raw_control(condition, index, dt)
                    d.ctrl[:] = control
                    before = d.act.copy()
                    mj.mj_step(model, d)
                    row = dict(index=index, raw_control=control,
                        effective_control=np.clip(d.ctrl, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1]).tolist(),
                        before=before.tolist(), after=d.act.tolist(), derivative=d.act_dot.tolist(),
                        during_force=d.actuator_force.tolist(), time=float(d.time))
                    mj.mj_forward(model, d)
                    row.update(refreshed_force=d.actuator_force.tolist(), refreshed_derivative=d.act_dot.tolist(),
                        length=d.actuator_length.tolist(), qpos=d.qpos.tolist(), qvel=d.qvel.tolist(),
                        external_generalized=d.qfrc_applied.tolist(), external_body=d.xfrc_applied.tolist())
                    case['steps'].append(row)
            except Exception as exc:
                case['error'] = f'{type(exc).__name__}: {exc}'
                report['status'] = 'INCOMPLETE'
    report['sources_after'] = sources()
    return report


def evaluate(report, ready):
    checks = dict(schema=report.get('schema') == SCHEMA, complete=report.get('status') == 'COMPLETE',
        sources=report.get('sources_after') == ready['sources'], ready=report.get('ready') == ready,
        api_calls=report.get('api_calls') == dict(mj_forward=2112, mj_step=2100),
        reference_solver=report.get('reference_solver') == dict(method='DOP853', rtol=1e-11, atol=1e-13, max_step=2.5e-6),
        scope=all(report.get(k) == v for k, v in dict(neural_transitions=0, body_joint_transitions=0,
            new_admissions=0, current_motor_count=20).items()),
        inventory=[(c.get('dt'), c.get('condition')) for c in report.get('cases', [])] ==
            [(dt, condition) for dt in DTS for condition in CONDITIONS])
    results = []
    try:
        binding, compiled = ready['binding'], report['compiled']
        gain, bias = np.asarray(binding['frozen_gain']), np.asarray(binding['frozen_bias'])
        floor = np.clip(np.zeros(4), np.asarray(binding['ctrlrange'])[:, 0], np.asarray(binding['ctrlrange'])[:, 1])
        checks['compiled_scope'] = all(compiled[k] == v for k, v in dict(nq=0, nv=0, nu=4, na=4, ntendon=4).items()) and not any(compiled['actearly'])
        checks['calibration'] = len(report['calibrations']) == 3 and all(
            row['level'] == level and np.max(np.abs(np.asarray(row['force'])-expected)) <= 1e-8
            for row, level, expected in zip(report['calibrations'], (0., .5, 1.), binding['frozen_forces']))
        for case in report['cases']:
            r = dict(dt=case['dt'], condition=case['condition'], checks={})
            results.append(r)
            try:
                dt, condition = case['dt'], case['condition']
                count = round(DURATION/dt)
                rows = case['steps']
                ref = np.asarray(case['reference_activations'])
                initial = np.zeros(4) if condition == 'RELAX_ZERO' else floor
                if case.get('error') or len(rows) != count or ref.shape != (count+1, 4):
                    raise ValueError('incomplete native/reference trajectory')
                a = np.vstack((case['initial']['activation'], [x['after'] for x in rows]))
                before = np.asarray([x['before'] for x in rows])
                after = a[1:]
                derivative = np.asarray([x['derivative'] for x in rows])
                expected_next = before+dt*derivative
                for col, limited in enumerate(compiled['actlimited']):
                    if limited: expected_next[:, col] = np.clip(expected_next[:, col], *compiled['actrange'][col])
                r['checks']['initial'] = bool(np.array_equal(a[0], initial) and np.max(np.abs(ref[0]-initial)) <= 1e-13
                    and np.max(np.abs(np.asarray(case['initial']['force'])-(gain*initial+bias))) <= 1e-8 and case['initial']['time'] == 0)
                r['checks']['finite'] = bool(all(np.isfinite(x).all() for x in (a, ref, before, derivative, expected_next)))
                r['checks']['state_chain'] = bool(np.array_equal(before, a[:-1]))
                r['checks']['euler'] = bool(np.max(np.abs(after-expected_next)) <= 1e-10)
                r['checks']['time_control'] = all(x['index'] == i and x['raw_control'] == raw_control(condition, i, dt)
                    and abs(x['time']-(i+1)*dt) <= 1e-12 and np.array_equal(x['effective_control'],
                        np.clip(np.full(4, x['raw_control']), np.asarray(binding['ctrlrange'])[:, 0], np.asarray(binding['ctrlrange'])[:, 1])) for i, x in enumerate(rows))
                during = np.asarray([x['during_force'] for x in rows])
                refreshed = np.asarray([x['refreshed_force'] for x in rows])
                r['checks']['force_alignment'] = bool(np.max(np.abs(during-(before*gain+bias))) <= 1e-8
                    and np.max(np.abs(refreshed-(after*gain+bias))) <= 1e-8)
                r['checks']['fixed_context'] = all(x['qpos'] == x['qvel'] == x['external_generalized'] == []
                    and not np.any(x['external_body']) and np.max(np.abs(np.asarray(x['length'])-[v['length'] for v in binding['selected']])) <= 1e-12 for x in rows)
                if condition == 'FLOOR_BASELINE':
                    r['checks']['stationary_baseline'] = bool(np.max(np.abs(a-floor)) <= 1e-10
                        and np.max(np.abs(refreshed-(gain*floor+bias))) <= 1e-8)
                r['maximum_activation_error'] = float(np.max(np.abs(a-ref)))
                r['endpoint_activation_error'] = float(np.max(np.abs(a[-1]-ref[-1])))
                r['minimum_activation'] = float(np.min(a))
                r['maximum_activation'] = float(np.max(a))
                r['maximum_reference_force_error'] = float(np.max(np.abs((a-ref)*gain)))
                r['numerical_checks'] = dict(bounds=r['minimum_activation'] >= -1e-12 and r['maximum_activation'] <= 1+1e-12,
                    full_window_accuracy=r['maximum_activation_error'] <= .01)
                r['numerical_acceptance'] = all(r['numerical_checks'].values())
            except Exception as exc:
                r['checks']['complete'] = False
                r['error'] = str(exc)
                r['numerical_acceptance'] = False
            r['integrity_passed'] = bool(r['checks']) and all(r['checks'].values())
        for dt in DTS:
            baseline = next(c for c in report['cases'] if c['dt'] == dt and c['condition'] == 'FLOOR_BASELINE')
            pulse = next(c for c in report['cases'] if c['dt'] == dt and c['condition'] == 'PULSE')
            end = round(.002/dt)
            checks['matched_prefix_'+str(dt)] = baseline['initial'] == pulse['initial'] and all(
                b['after'] == p['after'] and b['refreshed_force'] == p['refreshed_force']
                for b, p in zip(baseline['steps'][:end], pulse['steps'][:end]))
    except Exception as exc:
        checks['complete_evaluation'] = False
        checks['error'] = str(exc)
    integrity = all(v is True for v in checks.values()) and len(results) == 9 and all(r['integrity_passed'] for r in results)
    accuracy = len(results) == 9 and all(r['numerical_acceptance'] for r in results)
    return dict(checks=checks, cases=results, integrity_passed=integrity, all_numerically_accepted=accuracy,
                classification='ALL_NUMERICALLY_ACCEPTED' if integrity and accuracy else 'NUMERICAL_LIMITS_OBSERVED' if integrity else 'INTEGRITY_FAILURE')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true')
    group.add_argument('--preflight', action='store_true')
    group.add_argument('--report', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.execute:
        if args.output_dir is None: parser.error('--execute requires a fresh --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        mj = None
        counts = dict(mj_forward=0, mj_step=0)
        try:
            import mujoco as mj
            original_f, original_s = mj.mj_forward, mj.mj_step
            def forward(*a, **k):
                counts['mj_forward'] += 1
                return original_f(*a, **k)
            def step(*a, **k):
                counts['mj_step'] += 1
                return original_s(*a, **k)
            mj.mj_forward, mj.mj_step = forward, step
            ready = preflight()
            report = execute(ready)
            report['api_calls'] = counts
            report['evaluation'] = evaluate(report, ready)
        except Exception as exc:
            report = dict(schema=SCHEMA, status='INTEGRITY_ERROR', api_calls=counts, error=f'{type(exc).__name__}: {exc}')
        finally:
            if mj is not None: mj.mj_forward, mj.mj_step = original_f, original_s
        with (args.output_dir/'validation.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write('\n')
        if not report.get('evaluation', {}).get('integrity_passed'):
            print('TRANSIENT INTEGRITY FAILED; available evidence retained.')
            print(report.get('error', report.get('evaluation')))
            return 1
    elif args.report:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        ready = preflight()
        ready['original_raw_freezes_satisfied'] = report['ready']['original_raw_freezes_satisfied']
        actual = evaluate(report, ready)
        if not actual['integrity_passed'] or actual != report['evaluation']:
            raise ValueError('saved transient/source verification failed')
    else:
        preflight()
        print('PREFLIGHT PASSED: no native model or dynamics; nine fixed activation cases; current20/42.')
        return 0
    print('TRANSIENT EVIDENCE VERIFIED: 9 cases; 2100 recorded activation-only native steps; CNS/body-joint transitions0.')
    print('Numerical classification:', report['evaluation']['classification'])
    for row in report['evaluation']['cases']:
        print(f"{row['dt']*1e6:g}us {row['condition']}: numerical {'PASS' if row['numerical_acceptance'] else 'FAIL'}; max activation error {row['maximum_activation_error']:.9g}")
    print('Current20/42; newly admitted0; original raw prerequisites:', report['ready']['original_raw_freezes_satisfied'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
