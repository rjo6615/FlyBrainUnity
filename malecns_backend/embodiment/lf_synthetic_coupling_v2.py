"""V2 synthetic coupling using explicit endpoint roles; no physical transfer."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np

from . import lf_synthetic_coupling as v1
from . import lf_activation_endpoint as endpoint

ROOT = v1.ROOT
DIRECTORY = 'docs/evidence/lf-synthetic-coupling-v2/'
SCHEMA = 'lf-synthetic-coupling-v2'
CONTRACT = endpoint.DIRECTORY+'run/contract.json'
CONTRACT_SHA = '1f79cb1435fbc149c3691d800f6106bc985fbb53de5e6a672f349306ce72908d'


def dense_hash(values):
    return v1.force.audit.sha(json.dumps(values, separators=(',', ':'), allow_nan=False).encode())


def sources():
    result = v1.sources()
    for path in (endpoint.OLD, endpoint.MANIFEST, CONTRACT, 'docs/LF_ENDPOINT_CONTRACT_V1.md',
                 'malecns_backend/embodiment/lf_activation_endpoint.py',
                 'docs/LF_SYNTHETIC_COUPLING_V2.md', 'malecns_backend/embodiment/lf_synthetic_coupling_v2.py'):
        raw = (ROOT/path).read_bytes()
        result[path] = v1.force.audit.sha(raw if path == endpoint.OLD else raw.replace(b'\r\n', b'\n'))
    if result[endpoint.OLD] != endpoint.OLD_SHA or result[CONTRACT] != CONTRACT_SHA:
        raise ValueError('historical V1 or endpoint-contract evidence changed')
    return result


def preflight():
    before = sources()
    endpoint_ready = endpoint.preflight()
    saved = json.loads((ROOT/CONTRACT).read_text(encoding='utf-8'))
    actual = endpoint.evaluate(saved, endpoint_ready)
    if not actual['passed'] or actual != saved['evaluation']:
        raise ValueError('independent endpoint contract does not verify')
    ready = v1.preflight()
    ready['sources'] = before
    ready['endpoint_prerequisite'] = dict(canonical_sha256=CONTRACT_SHA, classification=actual['classification'],
        historical_v1_classification=endpoint_ready['historical_classification'], historical_v1_sha256=endpoint.OLD_SHA)
    if sources() != before: raise ValueError('sources changed during static V2 preflight')
    return ready


class EndpointSplitAdapter(v1.SyntheticSplitAdapter):
    """Inherit V1 mechanics/guards; consume the independently verified API."""
    def advance(self, condition):
        self.guard()
        index, dt = self.transitions, self.dt
        raw = v1.schedule.raw_control(condition, index, dt)
        effective = np.clip(np.full(4, raw), *np.asarray(self.ready['binding']['ctrlrange']).T)
        before = self.activation
        row = dict(index=index, before=v1.physical_state(self.data), activation_before=before.tolist(),
                   raw_control=raw, effective_control=effective.tolist(), phase='BEFORE_SOLVE',
                   endpoint_contract=endpoint.SCHEMA)
        self.last_attempt = row
        try:
            solved = endpoint.integrate_interval(self.native, before, effective,
                self.ready['binding']['dynprm'], dt, [dt])
            torque = v1.projected_torque(self.ready, before)
            self.apply(torque)
            row.update(torque=torque.tolist(), applied=v1.physical_state(self.data), solver=solved,
                       interpolated_samples_sha256=dense_hash(solved['interpolated_samples']), phase='BEFORE_BODY')
            self.native.mj_step(self.model, self.data)
            row.update(after_body=v1.physical_state(self.data), native_acceleration=self.data.qacc.tolist(), phase='AFTER_BODY')
            self.clear()
            self.native.mj_forward(self.model, self.data)
            self._activation = np.asarray(solved['after']).copy()
            self.transitions += 1
            row.update(after_clear=v1.physical_state(self.data), activation_after=self.activation.tolist(),
                       commit_index=self.transitions, phase='COMMITTED')
            return row
        except Exception as exc:
            self.failed = True
            row.update(error=f'{type(exc).__name__}: {exc}', failure_state=v1.physical_state(self.data),
                       activation_at_failure=self.activation.tolist())
            if self.owned is not None:
                try: self.clear()
                except Exception as clear_exc: row['clear_error'] = str(clear_exc)
            raise


def execute(ready):
    import mujoco as native
    report = dict(schema=SCHEMA, status='COMPLETE', ready=ready, cases=[], calibrations=[],
        current_motor_count=20, new_admissions=0, neural_transitions=0, synthetic_only=True,
        activation_settings=endpoint.prior.SETTINGS, models_constructed=0,
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    with v1.accounting(native) as counts:
        try:
            report['references'] = {c: v1.continuous_reference(native, ready, c) for c in v1.schedule.CONDITIONS}
            for dt in v1.schedule.DTS:
                model = native.MjModel.from_xml_path(str(ROOT/v1.FIXTURE))
                report['models_constructed'] += 1
                model.opt.timestep = dt
                check = native.MjData(model)
                native.mj_forward(model, check)
                mass = np.zeros((4, 4)); native.mj_fullM(model, mass, check.qM)
                report['calibrations'].append(dict(dt=dt, mass=mass.tolist(), nq=int(model.nq), nv=int(model.nv),
                    nu=int(model.nu), na=int(model.na), ngeom=int(model.ngeom)))
                for condition in v1.schedule.CONDITIONS:
                    case = dict(dt=dt, condition=condition, steps=[])
                    report['cases'].append(case)
                    data = native.MjData(model)
                    data.qfrc_applied[:] = v1.FOREIGN
                    data.xfrc_applied[:] = v1.foreign_body()
                    native.mj_forward(model, data)
                    a0 = np.zeros(4) if condition == 'RELAX_ZERO' else np.asarray(ready['binding']['ctrlrange'])[:, 0]
                    adapter = EndpointSplitAdapter(native, model, data, ready, a0)
                    case.update(initial=v1.physical_state(data), activation_initial=a0.tolist(), metadata=adapter.metadata)
                    try:
                        for _ in range(round(v1.schedule.DURATION/dt)): case['steps'].append(adapter.advance(condition))
                    except Exception as exc:
                        case.update(error=str(exc), last_attempt=adapter.last_attempt); report['status'] = 'INCOMPLETE'
        except Exception as exc:
            report.update(status='INCOMPLETE', error=f'{type(exc).__name__}: {exc}')
        report['api_calls'] = counts
    report['sources_after'] = sources()
    return report


def evaluate(report, ready):
    # Keep every V1 physical/numerical guard, but validate V2's own schema rather
    # than passing a V2 record off as the historical protocol. V1 is unmodified.
    mechanical = v1.evaluate(report, ready)
    checks = {k: v for k, v in mechanical['checks'].items() if k != 'schema'}
    checks['schema_v2'] = report.get('schema') == SCHEMA
    checks['endpoint_prerequisite'] = ready.get('endpoint_prerequisite') == dict(canonical_sha256=CONTRACT_SHA,
        classification='ENDPOINT_CONTRACT_VERIFIED_COUPLING_NOT_REVALIDATED',
        historical_v1_classification='INTEGRITY_FAILURE', historical_v1_sha256=endpoint.OLD_SHA)
    diagnostics = []
    try:
        for case in report['cases']:
            good, errors = True, []
            for row in case['steps']:
                result = row['solver']
                dense = np.asarray(result['interpolated_samples'])
                good = good and (row['endpoint_contract'] == endpoint.SCHEMA
                    and result['sample_kinds'] == ['SOLVER_TERMINAL_STATE']
                    and result['endpoint_state_source'] == 'SOLVER_INTERNAL_TERMINAL_VECTOR'
                    and dense.shape == (1, 4) and np.isfinite(dense).all()
                    and row['interpolated_samples_sha256'] == dense_hash(result['interpolated_samples'])
                    and result['samples'] == [result['after']]
                    and result['after'] == result['solver']['activations'][-1] == row['activation_after'])
                errors.append(float(np.max(np.abs(dense[0]-result['after']))))
            diagnostics.append(dict(dt=case['dt'], condition=case['condition'], endpoint_roles_passed=bool(good),
                retained_dense_mismatches=sum(e != 0 for e in errors), maximum_dense_terminal_difference=max(errors)))
        checks['all_endpoint_roles_and_raw_records'] = len(diagnostics) == 9 and all(r['endpoint_roles_passed'] for r in diagnostics)
    except Exception as exc:
        checks['all_endpoint_roles_and_raw_records'] = False; checks['endpoint_error'] = str(exc)
    integrity = (all(v is True for v in checks.values()) and len(mechanical['cases']) == 9
                 and all(r['integrity_passed'] for r in mechanical['cases']))
    numerical, refinement = mechanical['numerical_accepted'], mechanical['refinement_accepted']
    return dict(checks=checks, cases=mechanical['cases'], refinement=mechanical['refinement'],
        dense_diagnostics=diagnostics, integrity_passed=integrity, numerical_accepted=numerical,
        refinement_accepted=refinement,
        classification='SYNTHETIC_COUPLING_V2_VERIFIED_TRANSFER_BLOCKED' if integrity and numerical and refinement
            else 'NUMERICAL_LIMITS_OBSERVED' if integrity else 'INTEGRITY_FAILURE')


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
        text = json.dumps(v1.upstream.encode_nonfinite(report), indent=2, allow_nan=False)+'\n'
        with (args.output_dir/'validation.json').open('x', encoding='utf-8') as stream: stream.write(text)
        if not report.get('evaluation', {}).get('integrity_passed'):
            print('V2 SYNTHETIC INTEGRITY FAILED; evidence retained.', report.get('error', report.get('evaluation'))); return 1
    else:
        report = v1.upstream.load_report(args.report)
        actual = evaluate(report, preflight())
        if not actual['integrity_passed'] or actual != report['evaluation']:
            raise ValueError('saved V2 coupling/source verification failed')
    print('SYNTHETIC COUPLING V2 EVIDENCE VERIFIED:', report['evaluation']['classification'])
    for row in report['evaluation']['cases']:
        print(f"{row['dt']*1e6:g}us {row['condition']}: {'PASS' if row['numerical_acceptance'] else 'FAIL'}; q error{row['maximum_position_error']:.8g}, v error{row['maximum_velocity_error']:.8g}")
    print('Historical V1 remains INTEGRITY_FAILURE; all raw dense samples retained; no acceptance thresholds changed.')
    print('Roadmap: production20/42,new admissions0; synthetic evidence only, no FlyGym muscle/CNS/Unity run.')
    print('Next: source-to-body physical units/geometry/length/velocity and anatomical/neural transfer prerequisite review.')
    return 0


if __name__ == '__main__': raise SystemExit(main())
