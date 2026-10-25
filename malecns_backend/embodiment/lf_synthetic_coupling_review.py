"""Verify and diagnose the preserved failed V1 record without changing acceptance."""
import argparse
import json
from pathlib import Path
import importlib.metadata as packages

import numpy as np

from . import lf_synthetic_coupling as assay

RECORD_SHA = '12805789411e5b7b2aa9dbaea0f4e18e5075671a9945501970d9e952f99d822e'


def diagnostics(report):
    actual = assay.evaluate(report, report['ready'])
    if actual != report['evaluation']:
        raise ValueError('stored V1 evaluation does not reproduce')
    rows = []
    for case, result in zip(report['cases'], actual['cases']):
        errors = [float(np.max(np.abs(np.asarray(r['solver']['samples'][0])-r['solver']['after'])))
                  for r in case['steps']]
        authoritative = all(r['activation_after'] == r['solver']['after'] == r['solver']['solver']['activations'][-1]
                            for r in case['steps'])
        rows.append(dict(dt=case['dt'], condition=case['condition'],
            original_integrity_passed=result['integrity_passed'], original_solver_guard=result['checks']['solver'],
            original_numerical_acceptance=result['numerical_acceptance'],
            nonidentical_dense_endpoints=sum(e != 0 for e in errors), maximum_dense_endpoint_difference=max(errors),
            committed_state_matches_authoritative_terminal=authoritative,
            maximum_position_error=result['maximum_position_error'], maximum_velocity_error=result['maximum_velocity_error']))
    radau = Path(packages.distribution('scipy').locate_file('scipy/integrate/_ivp/radau.py'))
    return dict(schema='lf-synthetic-coupling-v1-failure-review', record_sha256=RECORD_SHA,
        original_classification=actual['classification'], acceptance_changed=False, campaign_repeated=False,
        cases=rows, refinement=actual['refinement'],
        scipy_radau_source_sha256=assay.force.audit.sha(radau.read_bytes()), scipy_version=packages.version('scipy'),
        interpretation='Dense interpolation and solver terminal state are separately computed; V1 exact-equality failure is retained.',
        next='Specify and test endpoint ownership semantics independently before any new acceptance protocol or experiment.',
        current_motor_count=20, new_admissions=0)


def verify(path):
    raw = Path(path).read_bytes()
    if assay.force.audit.sha(raw) != RECORD_SHA: raise ValueError('original V1 raw evidence hash mismatch')
    report = assay.upstream.load_report(path)
    if report['ready'] != assay.preflight(): raise ValueError('V1 sources/prerequisites changed')
    return diagnostics(report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--write-summary', type=Path)
    args = parser.parse_args(argv)
    summary = verify(args.report)
    if args.write_summary:
        with args.write_summary.open('x', encoding='utf-8') as stream:
            json.dump(summary, stream, indent=2, allow_nan=False); stream.write('\n')
    print('SYNTHETIC RECORD VERIFIED:', summary['original_classification'], '(unchanged; experiment NOT accepted).')
    for r in summary['cases']:
        print(f"{r['dt']*1e6:g}us {r['condition']}: numerical {'PASS' if r['original_numerical_acceptance'] else 'FAIL'}; solver guard {'PASS' if r['original_solver_guard'] else 'FAIL'}; dense difference {r['maximum_dense_endpoint_difference']:.8g}")
    print('No model, native step, solver or CNS execution; no threshold changes or campaign repeat.')
    print('Roadmap: production20/42, new admissions0. Next:', summary['next'])
    return 0


if __name__ == '__main__': raise SystemExit(main())
