"""Fixed six-foot batch of the existing environment-only contact calibration."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from . import tactile_targeted_contact_calibration as single

LEGS = ('LF', 'LM', 'LH', 'RF', 'RM', 'RH')
DURATION_S = .05
TIMESTEP_S = single.DEFAULT_TIMESTEP_S


def evaluate_leg(report, leg):
    """Fail closed; legacy COMPLETE or threshold acceptance alone is insufficient."""
    if report.get('run_status') != 'COMPLETE':
        return {'accepted': False, 'checks': {}, 'status': report.get('run_status', 'INVALID_REPORT')}
    try:
        control, contact = report['control'], report['contact']
        expected = int(math.ceil(DURATION_S / TIMESTEP_S)) + 1
        schedules = [[float(s['simulation_time_s']) for s in condition['samples']]
                     for condition in (control, contact)]
        finite = True
        contact_truth = True
        for condition in (control, contact):
            for sample in condition['samples']:
                metadata = single.contact_metadata(
                    (single.ContactPair(**pair) for pair in sample['contact_metadata']['all_contact_pairs']),
                    condition['tarsus_geom']['id'], condition['surface_geom']['id'])
                contact_truth &= sample['selected_pair_present'] is metadata['selected_pair_present']
                vector = sample['raw_tarsus5_vector']
                magnitude = float(sample['magnitude'])
                finite &= (len(vector) == 3 and all(math.isfinite(float(x)) for x in vector)
                           and math.isfinite(magnitude) and magnitude >= 0
                           and math.isclose(math.sqrt(sum(float(x)**2 for x in vector)),
                                            magnitude, rel_tol=1e-10, abs_tol=1e-15))
        poses = [condition['pose_proof'] for condition in (control, contact)]
        qpos = poses[0]['qpos_before']
        poses_match = (bool(qpos) and all(math.isfinite(float(x)) for x in qpos)
                       and all(proof['qpos_before'] == qpos and
                               proof['qpos_after_surface_placement'] == qpos and
                               proof['exactly_equal'] is True for proof in poses))
        negative = [float(s['magnitude']) for s in control['samples'] if not s['selected_pair_present']]
        positive = [float(s['magnitude']) for s in contact['samples'] if s['selected_pair_present']]
        checks = {
            'fixed_protocol': (report['selected_leg'] == leg and report['selected_segment'] == 'Tarsus5'
                               and report['duration_s'] == DURATION_S and report['timestep_s'] == TIMESTEP_S
                               and report['male_cns_used'] is False),
            'complete_samples': all(len(s) == expected for s in schedules),
            'finite_force_measurements': bool(finite),
            'exact_contact_truth_consistent': bool(contact_truth),
            'matched_finite_increasing_schedule': (schedules[0] == schedules[1]
                and all(math.isfinite(t) for t in schedules[0])
                and all(b > a for a, b in zip(schedules[0], schedules[0][1:]))
                and len(schedules[0]) > 1
                and math.isclose(schedules[0][-1] - schedules[0][0], DURATION_S, abs_tol=TIMESTEP_S * 1e-6)),
            'matched_unchanged_reset_pose': poses_match,
            'exact_selected_geometries': all(
                condition['tarsus_geom']['name'].rsplit('/', 1)[-1] == f'{leg}Tarsus5'
                and condition['surface_geom']['name'].rsplit('/', 1)[-1] == single.SURFACE_NAME
                for condition in (control, contact)),
            'fixed_surface_rule': (control['placement']['gap'] == single.CONTROL_GAP
                and control['placement']['penetration'] == 0
                and contact['placement']['gap'] == 0
                and contact['placement']['penetration'] == single.CONTACT_PENETRATION
                and all(tuple(c['placement']['surface_half_size']) == single.SURFACE_HALF_SIZE
                        for c in (control, contact))),
            'control_never_touches_target_surface': not any(s['selected_pair_present'] for s in control['samples']),
            'negative_control_observed': bool(negative),
            'verified_target_contact_observed': bool(positive),
            'control_force_below_existing_threshold': bool(negative) and all(x <= single.ENGINEERING_THRESHOLD for x in negative),
            'verified_contact_force_above_existing_threshold': bool(positive) and all(x > single.ENGINEERING_THRESHOLD for x in positive),
        }
        accepted = all(checks.values())
        return {'accepted': accepted, 'checks': checks,
                'status': 'MATCHED_CALIBRATION_ACCEPTED' if accepted else 'CALIBRATION_INCONCLUSIVE_OR_DISAGREEMENT',
                'negative_control_samples': len(negative), 'verified_contact_samples': len(positive)}
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return {'accepted': False, 'checks': {}, 'status': 'INVALID_REPORT', 'reason': str(exc)}


def finite_evidence(value, path='evidence', invalid=None):
    """Preserve invalid measurement locations while keeping saved JSON strict."""
    if invalid is None:
        invalid = []
    if isinstance(value, float) and not math.isfinite(value):
        invalid.append(path)
        return None
    if isinstance(value, dict):
        return {key: finite_evidence(item, f'{path}.{key}', invalid) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_evidence(item, f'{path}[{i}]', invalid) for i, item in enumerate(value)]
    return value


def build_report(*, live=False, progress=print):
    results = {}
    for leg in LEGS:
        progress(f'Calibrating {leg}: fixed control/contact pair; no CNS or tactile delivery.')
        try:
            evidence = single.build_report(live=live, leg=leg, duration_s=DURATION_S,
                                           timestep_s=TIMESTEP_S)
        except Exception as exc:
            evidence = {'run_status': 'ERROR', 'reason': f'{type(exc).__name__}: {exc}'}
        evaluation = evaluate_leg(evidence, leg)
        invalid = []
        safe_evidence = finite_evidence(evidence, invalid=invalid)
        if invalid:
            evaluation.update(accepted=False, status='INVALID_NONFINITE_EVIDENCE')
        results[leg] = {'evaluation': evaluation, 'evidence': safe_evidence,
                        'nonfinite_measurement_paths': invalid}
    accepted = [leg for leg, value in results.items() if value['evaluation']['accepted']]
    complete = all(value['evidence'].get('run_status') == 'COMPLETE' for value in results.values())
    return {
        'schema': 'six-foot-contact-calibration-v1', 'run_status': 'COMPLETE' if complete else 'INCOMPLETE',
        'all_six_accepted': len(accepted) == 6, 'accepted_legs': accepted,
        'protocol': {'duration_s_per_condition': DURATION_S, 'timestep_s': TIMESTEP_S,
                     'leg_order': list(LEGS), 'conditions_per_leg': ['control', 'contact'],
                     'engineering_threshold': single.ENGINEERING_THRESHOLD,
                     'automatic_retries': 0, 'parameter_tuning': False,
                     'male_cns_used': False, 'tactile_delivery_enabled': False},
        'interpretation': 'Environment-only calibration of the existing force proxy and threshold; not biological transduction validation. Force in a control can reflect other collisions. No parameter revision or sensory admission is automatic. Calibration uses the legacy fresh physics/held-joint protocol, not the live v3 body-support context.',
        'source_sha256_lf': {name: hashlib.sha256(Path(single.__file__).with_name(name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                             for name in ('tactile_targeted_contact_calibration.py', 'tactile_contact.py')},
        'legs': results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    # The batch is fixed: no seed/threshold/placement/duration knobs are exposed.
    report = build_report(live=args.live, progress=lambda message: print(message, flush=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(single.serialized_report(report), encoding='utf-8')
    print(f"Saved {args.output}; accepted={report['accepted_legs']}", flush=True)
    return 0 if report['all_six_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
