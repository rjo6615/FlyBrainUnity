"""Explicit initial/terminal/interpolation sampling; no state commit or physics."""
import argparse
import copy
import hashlib
import importlib.metadata as packages
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np

from . import lf_activation_integrator as prior

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = 'docs/evidence/lf-endpoint-contract-v1/'
MANIFEST = DIRECTORY+'input-manifest.json'
OLD = 'docs/evidence/lf-synthetic-coupling-v1/run/validation.json'
OLD_SHA = '12805789411e5b7b2aa9dbaea0f4e18e5075671a9945501970d9e952f99d822e'
FROZEN = ('malecns_backend/embodiment/lf_activation_integrator.py',
          'malecns_backend/embodiment/lf_synthetic_coupling.py', 'docs/LF_SYNTHETIC_COUPLING_V1.md')
SCHEMA = 'lf-endpoint-contract-v1'
DURATIONS = (.0001, .001)
INITIAL = np.array([.2, .4, .6, .8])
CONTROL = np.array([.9, .7, .5, .3])
TAU = np.array([.001, .002, .003, .004])


def select_samples(result, initial, duration, offsets):
    """A new data contract, retaining every original interpolated sample.

    An exact endpoint request selects the authoritative stored state. Interior
    requests keep the interpolant, even one representable time below the end.
    No epsilon, snapping, solver change, physical update or input mutation.
    """
    a0, t = np.asarray(initial, dtype=float), np.asarray(offsets, dtype=float)
    endpoint = np.asarray(result['after'], dtype=float)
    dense = np.asarray(result['samples'], dtype=float)
    solver = result['solver']
    nodes, states = np.asarray(solver['times']), np.asarray(solver['activations'])
    if (a0.ndim != 1 or not a0.size or not np.isfinite(duration) or duration <= 0
            or t.ndim != 1 or not t.size or t[0] < 0 or t[-1] > duration or np.any(np.diff(t) <= 0)
            or endpoint.shape != a0.shape or dense.shape != (len(t), len(a0))
            or nodes.ndim != 1 or len(nodes) < 2 or states.shape != (len(nodes), len(a0))
            or not all(np.isfinite(x).all() for x in (a0, t, endpoint, dense, nodes, states))
            or solver['success'] is not True or solver['status'] != 0
            or nodes[0] != 0 or nodes[-1] != duration or np.any(np.diff(nodes) <= 0)
            or not np.array_equal(states[0], a0) or not np.array_equal(states[-1], endpoint)
            or not np.array_equal(result['sample_offsets'], t)):
        raise ValueError('consistent finite authoritative endpoint and dense records required')
    selected, kinds = [], []
    for index, offset in enumerate(t):
        value, kind = (a0, 'INITIAL_STATE') if offset == 0 else (
            (endpoint, 'SOLVER_TERMINAL_STATE') if offset == duration else (dense[index], 'DENSE_INTERPOLANT'))
        selected.append(value.tolist()); kinds.append(kind)
    copied = copy.deepcopy(result)
    copied.update(interpolated_samples=copy.deepcopy(result['samples']), samples=selected, sample_kinds=kinds,
                  endpoint_state_source='SOLVER_INTERNAL_TERMINAL_VECTOR')
    return copied


def integrate_interval(native, initial, effective_control, dynprm, duration, offsets):
    """Delegate exactly once to the unchanged validated solver, then label data."""
    result = prior.integrate_interval(native, initial, effective_control, dynprm, duration, offsets)
    return select_samples(result, initial, duration, offsets)


def sha(raw): return hashlib.sha256(raw).hexdigest()


def preflight():
    sources = {}
    for path in (*FROZEN, MANIFEST, 'docs/LF_ENDPOINT_CONTRACT_V1.md',
                 'malecns_backend/embodiment/lf_activation_endpoint.py'):
        sources[path] = sha((ROOT/path).read_bytes().replace(b'\r\n', b'\n'))
    raw = (ROOT/OLD).read_bytes()
    if sha(raw) != OLD_SHA: raise ValueError('original failed coupling evidence changed')
    old = json.loads(raw)
    if old['evaluation']['classification'] != 'INTEGRITY_FAILURE':
        raise ValueError('historical failure must remain unaccepted')
    for path in FROZEN:
        if sources[path] != old['ready']['sources'][path]:
            raise ValueError('historical integrator/protocol/evaluator changed: '+path)
    manifest = json.loads((ROOT/MANIFEST).read_text(encoding='utf-8'))
    base = Path(packages.distribution('scipy').locate_file(''))
    for path, expected in manifest['files'].items():
        raw = (base/path).read_bytes()
        if sha(raw) != expected['sha256'] or len(raw) != expected['bytes']:
            raise ValueError('installed solver/API source changed: '+path)
    if {p: packages.version(p) for p in manifest['versions']} != manifest['versions']:
        raise ValueError('validated solver package version changed')
    return dict(sources=sources, installed=manifest, historical_record_sha256=OLD_SHA,
                historical_classification='INTEGRITY_FAILURE')


def constructed_case():
    # Deliberately large disagreements prove selection semantics, not accuracy.
    initial, terminal = [2., -3., .5, 1.], [7., -11., 13., -17.]
    duration = .25
    offsets = [0., .125, float(np.nextafter(duration, 0.)), duration]
    raw = dict(after=list(terminal), sample_offsets=offsets,
        samples=[[102., 103., 104., 105.], [20., 30., 40., 50.], [60., 70., 80., 90.], [107., 111., 113., 117.]],
        solver=dict(success=True, status=0, times=[0., duration], activations=[list(initial), list(terminal)]))
    original = copy.deepcopy(raw)
    adapted = select_samples(raw, initial, duration, offsets)
    return dict(kind='CONSTRUCTED_RETURN_OBJECT_NOT_ODE_OR_PHYSICS', initial=initial, duration=duration,
                offsets=offsets, original=original, adapted=adapted, input_unchanged=raw == original)


def execute(ready):
    report = dict(schema=SCHEMA, ready=ready, status='COMPLETE', constructed=constructed_case(), analytic=[],
        solver_settings=prior.SETTINGS,
        native_model_constructions=0, native_forward=0, native_body_steps=0, cns_transitions=0,
        current_motor_count=20, new_admissions=0, coupling_revalidated=False,
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    # This derivative is an analytic mock ONLY. It is not native muscle law.
    linear = SimpleNamespace(mju_muscleDynamics=lambda c, a, p: (c-a)/p[0])
    params = np.zeros((4, 10)); params[:, 0] = TAU
    for duration in DURATIONS:
        offsets = [0., duration/2, float(np.nextafter(duration, 0.)), duration]
        count = [0]
        original = prior.solve_ivp
        def counted(*a, **k): count[0] += 1; return original(*a, **k)
        prior.solve_ivp = counted
        try:
            result = integrate_interval(linear, INITIAL, CONTROL, params, duration, offsets)
            report['analytic'].append(dict(duration=duration, offsets=offsets, result=result, solver_calls=count[0]))
        finally: prior.solve_ivp = original
    report['sources_after'] = preflight()
    return report


def evaluate(report, ready):
    checks = dict(schema=report.get('schema') == SCHEMA, complete=report.get('status') == 'COMPLETE',
        solver_settings=report.get('solver_settings') == prior.SETTINGS,
        source_identity=report.get('ready') == ready and report.get('sources_after') == ready,
        scope=all(report.get(k) == v for k, v in dict(native_model_constructions=0, native_forward=0,
            native_body_steps=0, cns_transitions=0, current_motor_count=20, new_admissions=0, coupling_revalidated=False).items()))
    rows = []
    try:
        case = report['constructed']
        expected = constructed_case()
        checks['constructed'] = case == expected and case['input_unchanged']
        checks['inventory'] = [r['duration'] for r in report['analytic']] == list(DURATIONS)
        for case in report['analytic']:
            dt, result = case['duration'], case['result']
            offsets = [0., dt/2, float(np.nextafter(dt, 0.)), dt]
            truth = CONTROL+(INITIAL-CONTROL)*np.exp(-np.asarray(offsets)[:, None]/TAU)
            values = np.asarray(result['samples'])
            dense = np.asarray(result['interpolated_samples'])
            terminal = np.asarray(result['solver']['activations'][-1])
            solver_times = np.asarray(result['solver']['times'])
            rc = dict(single_solve=case['solver_calls'] == 1,
                offsets=case['offsets'] == offsets and result['sample_offsets'] == offsets,
                kinds=result['sample_kinds'] == ['INITIAL_STATE', 'DENSE_INTERPOLANT', 'DENSE_INTERPOLANT', 'SOLVER_TERMINAL_STATE'],
                finite=bool(all(np.isfinite(x).all() for x in (values, dense, terminal))),
                exact_endpoint=np.array_equal(values[-1], result['after']) and np.array_equal(values[-1], terminal),
                exact_initial=np.array_equal(values[0], INITIAL),
                interior=np.array_equal(values[1:3], dense[1:3]),
                solver=result['solver']['success'] is True and result['solver']['status'] == 0
                    and solver_times[0] == 0 and solver_times[-1] == dt and np.all(np.diff(solver_times) > 0),
                source=result['endpoint_state_source'] == 'SOLVER_INTERNAL_TERMINAL_VECTOR')
            error = float(np.max(np.abs(values-truth)))
            endpoint_error = float(np.max(np.abs(terminal-truth[-1])))
            rc['analytic_accuracy'] = error <= 1e-8 and endpoint_error <= 1e-8
            rows.append(dict(duration=dt, checks={k: bool(v) for k, v in rc.items()},
                maximum_analytic_error=error, terminal_analytic_error=endpoint_error,
                dense_terminal_difference=float(np.max(np.abs(dense[-1]-terminal)))))
    except Exception as exc:
        checks['evaluation_complete'] = False; checks['error'] = str(exc)
    passed = all(v is True for v in checks.values()) and len(rows) == 2 and all(all(r['checks'].values()) for r in rows)
    return dict(checks=checks, analytic=rows, passed=passed,
        classification='ENDPOINT_CONTRACT_VERIFIED_COUPLING_NOT_REVALIDATED' if passed else 'ENDPOINT_CONTRACT_FAILED')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--report', type=Path)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.execute:
        if args.output_dir is None: parser.error('--execute requires a new --output-dir')
        args.output_dir.mkdir(parents=True, exist_ok=False)
        try:
            ready = preflight(); report = execute(ready); report['evaluation'] = evaluate(report, ready)
        except Exception as exc: report = dict(schema=SCHEMA, status='ERROR', error=f'{type(exc).__name__}: {exc}')
        text = json.dumps(report, indent=2, allow_nan=False)+'\n'
        with (args.output_dir/'contract.json').open('x', encoding='utf-8') as stream: stream.write(text)
        if not report.get('evaluation', {}).get('passed'):
            print('ENDPOINT CONTRACT FAILED; evidence retained.', report.get('error', report.get('evaluation'))); return 1
    else:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        actual = evaluate(report, preflight())
        if not actual['passed'] or actual != report['evaluation']: raise ValueError('saved endpoint contract verification failed')
    print('ENDPOINT CONTRACT VERIFIED; coupling NOT revalidated; historical V1 remains INTEGRITY_FAILURE.')
    print('Constructed sample-selection check and two analytic LINEAR MOCK solver checks; no native physics or CNS.')
    print('Roadmap: production20/42, new admissions0. Next: separately versioned synthetic coupling validation using explicit endpoint roles.')
    print('Unity: no changed behavior yet; physical force-transfer/neural/raw gates and bounded headless validation remain.')
    return 0


if __name__ == '__main__': raise SystemExit(main())
