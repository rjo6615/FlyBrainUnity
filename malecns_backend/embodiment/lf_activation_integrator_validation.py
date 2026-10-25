"""Versioned fixed-fixture integration assay; no production or CNS coupling."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np

from . import lf_activation_transient as prior
from . import lf_activation_integrator as integrator

ROOT = prior.ROOT
DIRECTORY = 'docs/evidence/lf-activation-integrator-v1/'
PREVIOUS = prior.DIRECTORY+'run/validation.json'
PREVIOUS_SHA = '539c26fb35d15824d970b482d36af579186e2ed4fe1bf707c03c4e592a90e5fc'
SCHEMA = 'lf-activation-integrator-v1'
FINE = prior.DTS[-1]


def sources():
    hashes = prior.sources()
    for p in ('docs/LF_ACTIVATION_INTEGRATOR_V1.md',
              'malecns_backend/embodiment/lf_activation_integrator.py',
              'malecns_backend/embodiment/lf_activation_integrator_validation.py', PREVIOUS):
        raw = (ROOT/p).read_bytes()
        hashes[p] = prior.pose.force.audit.sha(raw if p == PREVIOUS else raw.replace(b'\r\n', b'\n'))
    return hashes


def preflight():
    before = sources()
    if before[PREVIOUS] != PREVIOUS_SHA:
        raise ValueError('original Euler/reference archive raw hash mismatch')
    old = json.loads((ROOT/PREVIOUS).read_text(encoding='utf-8'))
    ready = prior.preflight()
    ready['original_raw_freezes_satisfied'] = old['ready']['original_raw_freezes_satisfied']
    evaluated = prior.evaluate(old, ready)
    if not evaluated['integrity_passed'] or evaluated != old['evaluation']:
        raise ValueError('original source/reference integrity failed')
    for condition in prior.CONDITIONS:
        fine = next(r['reference_activations'] for r in old['cases'] if r['dt'] == FINE and r['condition'] == condition)
        if any(r['reference_activations'] != fine[::round(r['dt']/FINE)]
               for r in old['cases'] if r['condition'] == condition):
            raise ValueError('original coarse/fine reference slices disagree')
    if sources() != before:
        raise ValueError('sources changed during preflight')
    return dict(sources=before, prior_ready=ready, euler_evaluation=evaluated,
                references={c: next(row['reference_activations'] for row in old['cases']
                                    if row['dt'] == FINE and row['condition'] == c) for c in prior.CONDITIONS})


def metadata(native, model):
    result = {key: int(getattr(model, key)) for key in ('nq', 'nv', 'ngeom', 'nu', 'na', 'ntendon')}
    for key in ('actadr', 'actnum', 'actearly', 'actlimited', 'actrange', 'ctrllimited',
                'dyntype', 'dynprm', 'gainprm', 'biasprm', 'ctrlrange'):
        result[key] = getattr(model, 'actuator_'+key).tolist()
    result['actuator_names'] = [native.mj_id2name(model, native.mjtObj.mjOBJ_ACTUATOR, i) for i in range(model.nu)]
    result['tendon_names'] = [native.mj_id2name(model, native.mjtObj.mjOBJ_TENDON, i) for i in range(model.ntendon)]
    result['transmission_ids'] = model.actuator_trnid.tolist()
    return result


def valid_metadata(compiled, binding):
    return (all(compiled[k] == v for k, v in dict(nq=0, nv=0, ngeom=0, nu=4, na=4, ntendon=4).items())
            and compiled['actadr'] == list(range(4)) and compiled['actnum'] == [1]*4
            and compiled['actearly'] == compiled['actlimited'] == [0]*4
            and compiled['ctrllimited'] == [1]*4 and compiled['dyntype'] == [4]*4
            and compiled['transmission_ids'] == [[i, -1] for i in range(4)]
            and compiled['actuator_names'] == [r['source_attributes']['name'] for r in binding['selected']]
            and compiled['tendon_names'] == [r['tendon'] for r in binding['selected']]
            and all(np.array_equal(compiled[k], binding[k]) for k in
                    ('dynprm', 'gainprm', 'biasprm', 'ctrlrange')))


def execute(ready):
    import mujoco as native
    import scipy
    if native.__version__ != '3.2.7':
        raise ValueError('validated MuJoCo 3.2.7 required')
    binding = ready['prior_ready']['binding']
    report = dict(schema=SCHEMA, status='COMPLETE', ready=ready, settings=integrator.SETTINGS,
                  commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  versions=dict(mujoco=native.__version__, scipy=scipy.__version__, numpy=np.__version__),
                  neural_transitions=0, body_joint_transitions=0, current_motor_count=20,
                  new_admissions=0, cases=[], calibrations=[], compiled=[])
    for dt in prior.DTS:
        try:
            model = native.MjModel.from_xml_path(str(ROOT/prior.FIXTURE))
            meta = metadata(native, model)
            report['compiled'].append(meta)
            if not valid_metadata(meta, binding):
                raise ValueError('exact source muscle fixture identity or parameters changed')
        except Exception as exc:
            report.update(status='INCOMPLETE', error=f'{type(exc).__name__}: {exc}', sources_after=sources())
            return report
        if dt == prior.DTS[0]:
            for level in (0., .5, 1.):
                data = native.MjData(model)
                data.act[:] = level
                data.ctrl[:] = level
                native.mj_forward(model, data)
                report['calibrations'].append(dict(level=level, force=data.actuator_force.tolist()))
        floor = np.clip(np.zeros(4), *model.actuator_ctrlrange.T)
        for condition in prior.CONDITIONS:
            case = dict(dt=dt, condition=condition, steps=[])
            report['cases'].append(case)
            try:
                data = native.MjData(model)
                data.act[:] = np.zeros(4) if condition == 'RELAX_ZERO' else floor
                native.mj_forward(model, data)
                case['initial'] = dict(activation=data.act.tolist(), force=data.actuator_force.tolist(), time=float(data.time))
                stride = round(dt/FINE)
                offsets = np.arange(1, stride+1)*FINE
                for index in range(round(prior.DURATION/dt)):
                    row = integrator.advance_fixed_fixture(native, model, data,
                        prior.raw_control(condition, index, dt), dt, offsets)
                    row['index'] = index
                    case['steps'].append(row)
            except Exception as exc:
                case['error'] = f'{type(exc).__name__}: {exc}'
                report['status'] = 'INCOMPLETE'
    report['sources_after'] = sources()
    return report


def evaluate(report, ready):
    checks = dict(schema=report.get('schema') == SCHEMA, complete=report.get('status') == 'COMPLETE',
                  native_version=report.get('versions', {}).get('mujoco') == '3.2.7',
                  sources=report.get('sources_after') == ready['sources'], ready=report.get('ready') == ready,
                  settings=report.get('settings') == integrator.SETTINGS,
                  api_calls=report.get('api_calls') == dict(mj_forward=4212, mj_step=0),
                  inventory=[(r.get('dt'), r.get('condition')) for r in report.get('cases', [])] ==
                      [(dt, c) for dt in prior.DTS for c in prior.CONDITIONS],
                  scope=all(report.get(k) == v for k, v in dict(neural_transitions=0,
                      body_joint_transitions=0, current_motor_count=20, new_admissions=0).items()))
    results = []
    try:
        binding = ready['prior_ready']['binding']
        gain, bias = np.asarray(binding['frozen_gain']), np.asarray(binding['frozen_bias'])
        floor = np.clip(np.zeros(4), *np.asarray(binding['ctrlrange']).T)
        checks['compiled_source'] = len(report['compiled']) == 3 and all(valid_metadata(m, binding) for m in report['compiled'])
        checks['calibration'] = len(report['calibrations']) == 3 and all(
            r['level'] == level and np.max(np.abs(np.asarray(r['force'])-expected)) <= 1e-8
            for r, level, expected in zip(report['calibrations'], (0., .5, 1.), binding['frozen_forces']))
        for case in report['cases']:
            result = dict(dt=case['dt'], condition=case['condition'], checks={})
            results.append(result)
            try:
                dt, condition, rows = case['dt'], case['condition'], case['steps']
                count, stride = round(prior.DURATION/dt), round(dt/FINE)
                if case.get('error') or len(rows) != count:
                    raise ValueError('incomplete interval inventory')
                ref = np.asarray(ready['references'][condition])
                initial = np.zeros(4) if condition == 'RELAX_ZERO' else floor
                a = np.vstack((case['initial']['activation'], [r['after'] for r in rows]))
                dense = np.vstack((a[0], *[r['samples'] for r in rows]))
                nodes = np.vstack([r['solver']['activations'] for r in rows])
                before = np.asarray([r['before'] for r in rows])
                if a.shape != (count+1, 4) or dense.shape != ref.shape or ref.shape != (401, 4) or nodes.shape[1] != 4:
                    raise ValueError('invalid complete-window state shapes')
                rc = result['checks']
                rc['initial'] = (np.array_equal(a[0], initial) and np.array_equal(ref[0], initial)
                    and case['initial']['time'] == 0 and np.max(np.abs(np.asarray(case['initial']['force'])-(initial*gain+bias))) <= 1e-8)
                rc['finite'] = all(np.isfinite(x).all() for x in (a, dense, ref, nodes, before))
                rc['chain'] = np.array_equal(before, a[:-1])
                rc['controls_time'] = all(r['index'] == i and r['raw_control'] == prior.raw_control(condition, i, dt)
                    and abs(r['time_before']-i*dt) <= 1e-12 and abs(r['time']-(i+1)*dt) <= 1e-12
                    and np.array_equal(r['effective_control'], np.clip(np.full(4, r['raw_control']), *np.asarray(binding['ctrlrange']).T))
                    and np.array_equal(r['sample_offsets'], np.arange(1, stride+1)*FINE) for i, r in enumerate(rows))
                rc['force_alignment'] = (np.max(np.abs(np.asarray([r['force_before'] for r in rows])-(before*gain+bias))) <= 1e-8
                    and np.max(np.abs(np.asarray([r['force_after'] for r in rows])-(a[1:]*gain+bias))) <= 1e-8)
                rc['derivative_agreement'] = all(np.isfinite(r[k]).all() and np.max(np.abs(np.asarray(r[k])-r['native_'+k])) <= 1e-8
                    for r in rows for k in ('derivative_before', 'derivative_after'))
                rc['solver_records'] = all(r['solver']['success'] is True and r['solver']['status'] == 0
                    and all(type(r['solver'][k]) is int and r['solver'][k] > 0 for k in ('nfev', 'njev', 'nlu'))
                    and r['solver']['times'][0] == 0 and r['solver']['times'][-1] == dt
                    and len(r['solver']['times']) == len(r['solver']['activations'])
                    and np.isfinite(r['solver']['times']).all() and np.all(np.diff(r['solver']['times']) > 0)
                    and np.array_equal(r['solver']['activations'][0], r['before'])
                    and np.array_equal(r['solver']['activations'][-1], r['after'])
                    and np.max(np.abs(np.asarray(r['samples'][-1])-r['after'])) <= 1e-12 for r in rows)
                rc['fixed_context'] = all(r['qpos'] == r['qvel'] == r['external_generalized'] == []
                    and not np.any(r['external_body']) and np.max(np.abs(np.asarray(r['length'])-[v['length'] for v in binding['selected']])) <= 1e-12 for r in rows)
                if condition == 'FLOOR_BASELINE':
                    rc['stationary_baseline'] = np.max(np.abs(dense-floor)) <= 1e-10
                extrema = np.concatenate((a.ravel(), dense.ravel(), nodes.ravel()))
                result.update(maximum_activation_error=float(np.max(np.abs(dense-ref))),
                              macro_activation_error=float(np.max(np.abs(a-ref[::stride]))),
                              endpoint_activation_error=float(np.max(np.abs(a[-1]-ref[-1]))),
                              minimum_activation=float(np.min(extrema)), maximum_activation=float(np.max(extrema)),
                              maximum_reference_force_error=float(np.max(np.abs((dense-ref)*gain))),
                              solver_cost={k: sum(r['solver'][k] for r in rows) for k in ('nfev', 'njev', 'nlu')})
                result['numerical_checks'] = dict(full_window_accuracy=result['maximum_activation_error'] <= .01
                    and result['macro_activation_error'] <= .01,
                    bounds=result['minimum_activation'] >= -1e-12 and result['maximum_activation'] <= 1+1e-12)
                result['numerical_acceptance'] = all(result['numerical_checks'].values())
            except Exception as exc:
                result['checks']['complete'] = False
                result['error'] = str(exc)
                result['numerical_acceptance'] = False
            result['checks'] = {k: bool(v) for k, v in result['checks'].items()}
            result['integrity_passed'] = bool(result['checks']) and all(result['checks'].values())
        for dt in prior.DTS:
            baseline, pulse = [next(c for c in report['cases'] if c['dt'] == dt and c['condition'] == condition)
                               for condition in ('FLOOR_BASELINE', 'PULSE')]
            end = round(.002/dt)
            checks['matched_prefix_'+str(dt)] = baseline['initial'] == pulse['initial'] and all(
                b['after'] == p['after'] and b['samples'] == p['samples'] and b['force_after'] == p['force_after']
                for b, p in zip(baseline['steps'][:end], pulse['steps'][:end]))
    except Exception as exc:
        checks['complete_evaluation'] = False
        checks['error'] = str(exc)
    integrity = all(v is True for v in checks.values()) and len(results) == 9 and all(r['integrity_passed'] for r in results)
    accuracy = len(results) == 9 and all(r['numerical_acceptance'] for r in results)
    return dict(checks=checks, cases=results, integrity_passed=integrity, all_numerically_accepted=accuracy,
                classification='ALL_NUMERICALLY_ACCEPTED' if integrity and accuracy else
                    'NUMERICAL_LIMITS_OBSERVED' if integrity else 'INTEGRITY_FAILURE')


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
        import mujoco as native
        forward, step = native.mj_forward, native.mj_step
        counts = dict(mj_forward=0, mj_step=0)
        def counted_forward(*a, **k):
            counts['mj_forward'] += 1
            return forward(*a, **k)
        def forbidden_step(*a, **k):
            counts['mj_step'] += 1
            raise ValueError('native step would double-integrate activation')
        native.mj_forward, native.mj_step = counted_forward, forbidden_step
        try:
            report = execute(preflight())
            report['api_calls'] = counts
            report['evaluation'] = evaluate(report, report['ready'])
        except Exception as exc:
            report = dict(schema=SCHEMA, status='INTEGRITY_ERROR', api_calls=counts, error=f'{type(exc).__name__}: {exc}')
        finally:
            native.mj_forward, native.mj_step = forward, step
        with (args.output_dir/'validation.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write('\n')
        if not report.get('evaluation', {}).get('integrity_passed'):
            print('INTEGRATOR INTEGRITY FAILED; evidence retained.', report.get('error', report.get('evaluation')))
            return 1
    elif args.report:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        ready = preflight()
        actual = evaluate(report, ready)
        if not actual['integrity_passed'] or actual != report['evaluation']:
            raise ValueError('saved integrator verification failed')
    else:
        preflight()
        print('PREFLIGHT VERIFIED: original Euler failures preserved; no native model or integration.')
        return 0
    print('INTEGRATOR EVIDENCE VERIFIED:', report['evaluation']['classification'])
    for r in report['evaluation']['cases']:
        print(f"{r['dt']*1e6:g}us {r['condition']}: {'PASS' if r['numerical_acceptance'] else 'FAIL'}; full-window error {r['maximum_activation_error']:.9g}")
    print('Roadmap: production20/42; new admissions0; activation-only fixture, not movement or biological calibration.')
    print('Next:', 'moving-body state ownership/selective replacement design; original raw prerequisites remain separate.'
          if report['evaluation']['all_numerically_accepted'] else
          'retain numerical limitations; resolve the integration gate before moving-body coupling.')
    print('Original raw prerequisites:', report['ready']['prior_ready']['original_raw_freezes_satisfied'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
