"""Fixed matched delivery experiment; ordinary live/Unity defaults are untouched."""
from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import time

import numpy as np

from . import contact_context as context
from .tactile_boundary import Trial, create_session, native

ROOT = context.ROOT
CONDITIONS = ('WITHHELD', 'ENABLED')
PROTOCOL = dict(schema='matched-tactile-delivery-v1', conditions=list(CONDITIONS),
    duration_s=2., physics_steps=20000, neural_steps=4000, physics_dt_s=.0001,
    neural_dt_ms=.5, seed=1, threshold=1e-12, maximum_modeled_rate_hz=120., transient_ms=20.,
    tactile_neurons=1877, proprioceptive_neurons=392, common_external_slots=2269,
    automatic_retries=0, ordinary_live_tactile_enabled=False)
EXTRA_SOURCES = ('docs/MATCHED_TACTILE_DELIVERY_V1.md',
    'malecns_backend/live/tactile_boundary.py', 'malecns_backend/live/matched_tactile_delivery.py',
    'malecns_backend/embodiment/proprioceptive_activation.py',
    'malecns_backend/embodiment/sensory.py', 'malecns_backend/embodiment/tactile_contact.py',
    'malecns_backend/embodiment/m5d_tarsal_contact_load.py',
    'malecns_backend/embodiment/m5c_leg_sensory_inventory.py', 'malecns_backend/interface_map.json')


def source_hashes():
    return dict(context.source_hashes(), **{p: hashlib.sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                          for p in EXTRA_SOURCES})


def prerequisites():
    earlier = context.prerequisite()
    folder = ROOT / 'docs/evidence'
    manifest = json.loads((folder / 'live-contact-context-checkpoint.json').read_text())
    packed = (folder / manifest['raw_artifact']).read_bytes()
    raw = gzip.decompress(packed)
    if (hashlib.sha256(packed).hexdigest() != manifest['gzip_sha256']
            or hashlib.sha256(raw).hexdigest() != manifest['raw_json_sha256']):
        raise RuntimeError('live-context prerequisite hash mismatch')
    report = json.loads(raw)
    if (report['evaluation'] != context.evaluate(report) or not report['evaluation']['accepted']
            or report['sources_before'] != report['sources_after'] or report['sources_after'] != context.source_hashes()):
        raise RuntimeError('live-context prerequisite or source integrity failed')
    return dict(verified=True, isolated=earlier, live_context_raw_sha256=manifest['raw_json_sha256'],
                configuration=report['context']['configuration'])


def run_arm(condition, progress):
    trial = Trial(condition)
    result = dict(condition=condition, run_status='ERROR', samples=trial.samples, neural=trial.neural)
    session = None
    try:
        session = create_session(trial)
        progress(f'{condition}: initializing fresh supported live-v3 CNS; experimental delivery gate only.')
        state = session.initialize()
        if state.time_ms != 0.:
            raise RuntimeError('nonzero initial simulation time')
        last = time.monotonic()
        for step in range(1, PROTOCOL['physics_steps'] + 1):
            state = session.step(lightweight=True)
            if state.physics_transitions != step or state.neural_transitions != step // 5:
                raise RuntimeError('authoritative transition count mismatch')
            if time.monotonic() - last >= 15:
                progress(f'{condition}: {step}/{PROTOCOL["physics_steps"]} physics transitions.')
                last = time.monotonic()
        result['run_status'] = 'COMPLETE'
    except (Exception, KeyboardInterrupt) as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if session is not None:
            try:
                session.close()
            except Exception as exc:
                result.update(run_status='ERROR', close_error=f'{type(exc).__name__}: {exc}')
        trial.detach()
        result.update(context=trial.context, initial=trial.initial)
    return result


def first_difference(a, b, field, time_field):
    return next((float(x[time_field]) for x, y in zip(a, b) if x[field] != y[field]), None)


def evaluate(report):
    checks = dict(fixed_protocol=report.get('protocol') == PROTOCOL,
                  prerequisite=report.get('prerequisite', {}).get('verified') is True,
                  sources_unchanged=bool(report.get('sources_before')) and report.get('sources_before') == report.get('sources_after'))
    milestones = {}
    per_arm = {}
    try:
        a, b = (report['arms'][c] for c in CONDITIONS)
        an, bn = a['neural'], b['neural']
        checks['complete_pair'] = all(r['run_status'] == 'COMPLETE' and len(r['samples']) == PROTOCOL['physics_steps'] + 1
            and len(r['neural']) == PROTOCOL['neural_steps'] for r in (a, b))
        checks['matched_initial_neural_observer_encoder_inventory'] = a['initial'] == b['initial'] and bool(a['initial'])
        checks['matched_initial_physics'] = (a['context']['physics_model_identity'] == b['context']['physics_model_identity']
            and all(a['samples'][0][k] == b['samples'][0][k] for k in ('qpos', 'qvel', 'ctrl', 'joint_positions')))
        schedule = set(a['initial']['external_schedule'])
        tactile_by_leg = {l: set(v['dense_indices']) for l, v in a['initial']['tactile_inventory'].items()}
        tactile = set().union(*tactile_by_leg.values())
        proprio = schedule - tactile
        checks['complete_disjoint_input_inventory'] = (len(schedule) == 2269 and len(tactile) == 1877 and len(proprio) == 392
            and all(len(indices) == len(a['initial']['tactile_inventory'][l]['body_ids']) for l, indices in tactile_by_leg.items()))
        for condition, arm in zip(CONDITIONS, (a, b)):
            old_report = dict(protocol=context.PROTOCOL.copy(), run_status=arm['run_status'],
                prerequisite=report['prerequisite'], sources_before=report['sources_before'], sources_after=report['sources_after'],
                context=arm['context'], samples=arm['samples'])
            observational = context.evaluate(old_report)
            checks[f'{condition}_calibrated_context'] = (observational['accepted']
                and arm['context']['configuration'] == report['prerequisite']['configuration']
                and not any(row['calibration_surface_positive_samples'] for row in observational['legs'].values()))
            counts = {l: dict(offered=0, eligible=0, delivered=0) for l in context.LEGS}
            gate_ok = schedule_ok = readout_ok = finite = True
            for i, row in enumerate(arm['neural']):
                offered_tactile = set().union(*(set(row['offered_tactile'][l]) for l in context.LEGS))
                offered_proprio = set(row['offered_proprio'])
                eligible, delivered = set(row['eligible']), set(row['delivered'])
                expected = eligible - tactile if condition == 'WITHHELD' else eligible
                gate_ok &= (offered_tactile <= tactile and offered_proprio <= proprio
                    and eligible <= offered_tactile | offered_proprio and delivered == expected
                    and row['sampling']['eligible_indices'] == row['eligible']
                    and row['withheld_mask_sha256'] == context.digest(sorted(tactile) if condition == 'WITHHELD' else []))
                schedule_ok &= (math.isclose(row['time_ms'], (i + 1)*.5, rel_tol=0, abs_tol=1e-8)
                                and row['sampling']['draws'] == 2269)
                readout_ok &= (row['motor_readout_verified'] is True
                    and set(row['motor_telemetry']['delivered_external_sensory_events']) == delivered
                    and set(row['non_input_fired']) == set(row['fired']) - schedule)
                finite &= all(np.isfinite(row['motor_telemetry'][k]).all()
                              for k in ('commanded_joint_targets',))
                for leg, indices in tactile_by_leg.items():
                    gate_ok &= set(row['offered_tactile'][leg]) <= indices
                    counts[leg]['offered'] += len(row['offered_tactile'][leg])
                    counts[leg]['eligible'] += len(eligible & indices)
                    counts[leg]['delivered'] += len(delivered & indices)
            checks[f'{condition}_gate'] = bool(gate_ok)
            checks[f'{condition}_neural_schedule'] = bool(schedule_ok)
            checks[f'{condition}_readout'] = bool(readout_ok and finite)
            totals = {name: sum(sum(row['motor_telemetry']['per_neuron_spike_increments'][name]) for row in arm['neural'])
                      for name in arm['initial']['motor_inventory']}
            per_arm[condition] = dict(context_evaluation=observational, tactile=counts, motor_spikes=totals)
        checks['common_external_uniforms_full_window'] = all(
            x['sampling'] == dict(y['sampling'], eligible_indices=x['sampling']['eligible_indices']) for x, y in zip(an, bn))
        first = next((i for i, row in enumerate(bn) if set(row['eligible']) & tactile), None)
        milestones['first_eligible_tactile_ms'] = None if first is None else bn[first]['time_ms']
        boundary = len(bn) if first is None else first + 1
        checks['matched_pre_delivery_neural_and_offers'] = all(
            all(x[k] == y[k] for k in ('pre_state_sha256', 'offered_proprio', 'offered_tactile'))
            for x, y in zip(an[:boundary], bn[:boundary]))
        first_physical = first_difference(a['samples'], b['samples'], 'qpos', 'time_s')
        first_velocity = first_difference(a['samples'], b['samples'], 'qvel', 'time_s')
        physical_times = [t for t in (first_physical, first_velocity) if t is not None]
        physical = min(physical_times) if physical_times else None
        if first is not None:
            checks['matched_pre_delivery_physics'] = all(
                x['qpos'] == y['qpos'] and x['qvel'] == y['qvel'] and x['tactile'] == y['tactile']
                for x, y in zip(a['samples'], b['samples']) if x['time_s']*1000 <= bn[first]['time_ms'] + 1e-9)
        else:
            checks['matched_pre_delivery_physics'] = physical is None
        checks['matched_encoder_candidates_before_feedback'] = all(
            x['tactile'] == y['tactile'] for x, y in zip(a['samples'], b['samples'])
            if physical is None or x['time_s'] < physical)
        for field, label in (('post_state_sha256', 'first_cns_divergence_ms'),
                             ('downstream_state_sha256', 'first_non_input_state_divergence_ms'),
                             ('non_input_fired', 'first_non_input_spike_divergence_ms')):
            milestones[label] = first_difference(an, bn, field, 'time_ms')
        for field, label in (('per_neuron_spike_increments', 'first_motor_spike_divergence_ms'),
                             ('raw_signed_contribution_rad', 'first_decoder_divergence_ms'),
                             ('commanded_joint_targets', 'first_motor_command_divergence_ms')):
            milestones[label] = next((x['time_ms'] for x, y in zip(an, bn)
                if x['motor_telemetry'][field] != y['motor_telemetry'][field]), None)
        milestones['first_physical_divergence_ms'] = None if physical is None else physical * 1000
        joints = first_difference(a['samples'], b['samples'], 'joint_positions', 'time_s')
        milestones['first_joint_divergence_ms'] = None if joints is None else joints * 1000
        contact = first_difference(a['samples'], b['samples'], 'telemetry_forces', 'time_s')
        milestones['first_contact_force_feedback_divergence_ms'] = None if contact is None else contact * 1000
        if not all(checks.values()):
            outcome = 'INTEGRITY_OR_CONTEXT_INCONCLUSIVE'
        elif first is None:
            outcome = 'NO_ELIGIBLE_TACTILE_EVENTS'
        elif physical is not None:
            outcome = 'PHYSICAL_DIVERGENCE_OBSERVED'
        elif milestones['first_motor_command_divergence_ms'] is not None:
            outcome = 'MOTOR_COMMAND_DIVERGENCE_WITHOUT_PHYSICAL_DIVERGENCE'
        elif milestones['first_non_input_state_divergence_ms'] is not None:
            outcome = 'DOWNSTREAM_NEURAL_CHANGE_WITHOUT_MOTOR_COMMAND_DIVERGENCE'
        else:
            outcome = 'DELIVERY_VERIFIED_NO_DOWNSTREAM_CHANGE'
        return dict(integrity_passed=all(checks.values()), outcome=outcome, checks=checks,
                    milestones=milestones, arms=per_arm)
    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
        checks['valid_complete_evidence'] = False
        return dict(integrity_passed=False, outcome='INVALID_OR_INCOMPLETE', checks=checks,
                    milestones=milestones, arms=per_arm, reason=str(exc))


def build_report(*, live=False, progress=print):
    report = dict(protocol=PROTOCOL.copy(), run_status='NOT_RUN', arms={}, sources_before=source_hashes())
    try:
        report['prerequisite'] = prerequisites()
        if live:
            from ..embodiment._windows_m7d_corrected_spontaneous_adapter import _environment
            _environment()
            report['environment'] = {p: importlib.metadata.version(p) for p in ('flygym', 'mujoco', 'numpy')}
            for condition in CONDITIONS:
                report['arms'][condition] = run_arm(condition, progress)
                gc.collect()  # closed instance-local hooks must not retain a full CNS between arms
            report['run_status'] = 'COMPLETE' if all(a['run_status'] == 'COMPLETE' for a in report['arms'].values()) else 'INCOMPLETE'
    except (Exception, KeyboardInterrupt) as exc:
        report.update(run_status='ERROR', error=f'{type(exc).__name__}: {exc}')
    report['sources_after'] = source_hashes()
    invalid = []
    safe = context.batch.finite_evidence(report, invalid=invalid)
    safe['nonfinite_measurement_paths'] = invalid
    safe['evaluation'] = evaluate(safe)
    if invalid:
        safe['evaluation'].update(integrity_passed=False, outcome='NONFINITE_EVIDENCE')
    safe['interpretation'] = 'Modeled tactile delivery assay; no biological sensing, balance, gait or useful-movement claim. Ordinary live defaults remain unchanged.'
    return safe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        report = build_report(live=args.live, progress=lambda m: print(m, flush=True))
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as archive:
            archive.write(json.dumps(native(report), allow_nan=False, separators=(',', ':')).encode())
    print(f"Saved {args.output}; {report['evaluation']['outcome']}", flush=True)
    return 0 if report['evaluation']['integrity_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
