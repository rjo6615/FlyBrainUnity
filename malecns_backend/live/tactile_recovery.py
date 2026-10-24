"""Matched-state, versioned tactile withdrawal / disturbance factorial."""
from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import numpy as np

from . import contact_context as context, matched_tactile_delivery as matched
from .tactile_boundary import Trial, native
from . import tactile_recovery_metrics as metrics
from ..embodiment import m9b_external_perturbation as pulse

ROOT = context.ROOT
FRESH = ('OFF_C', 'OFF_P', 'ON_P')
CONDITIONS = ('ON_C', *FRESH)
STEPS, NEURAL_STEPS = 20000, 4000
START, STOP, WITHDRAW_INDEX = 5000, 5200, 1000
PROTOCOL = dict(schema='tactile-disturbance-recovery-v1', seed=1, duration_s=2., physics_steps=STEPS,
    neural_steps=NEURAL_STEPS, dt_s=.0001, fresh_order=list(FRESH), reused_control='matched-pair ENABLED',
    pulse_world_force=[0., 1.024, 0.], pulse_start_transition=START, pulse_stop_transition=STOP,
    withdraw_first_neural_step=WITHDRAW_INDEX+1, recovery_bands=metrics.BANDS,
    response_resolution=metrics.RESOLUTION, automatic_retries=0, ordinary_live_mode_changed=False)
SOURCES = ('docs/TACTILE_DISTURBANCE_RECOVERY_V1.md', 'malecns_backend/live/tactile_recovery.py',
    'malecns_backend/live/tactile_recovery_metrics.py', 'malecns_backend/embodiment/m9b_external_perturbation.py',
    'malecns_backend/embodiment/m10c_m10b_analysis.py')


def sources():
    return dict(matched.source_hashes(), **{p: hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in SOURCES})


def read_gzip(path):
    packed = Path(path).read_bytes()
    raw = gzip.decompress(packed)
    return json.loads(raw), dict(gzip_sha256=hashlib.sha256(packed).hexdigest(),
        raw_json_sha256=hashlib.sha256(raw).hexdigest(), gzip_bytes=len(packed), raw_json_bytes=len(raw))


def prerequisite():
    earlier = matched.prerequisites()
    checkpoint = json.loads((ROOT/'docs/evidence/matched-tactile-checkpoint.json').read_text())
    baseline_path = ROOT/'docs/evidence'/checkpoint['raw_artifact']
    pair, hashes = read_gzip(baseline_path)
    if any(hashes[k] != checkpoint[k] for k in ('gzip_sha256', 'raw_json_sha256')):
        raise RuntimeError('matched tactile archive hash mismatch')
    if (not pair['evaluation']['integrity_passed'] or pair['evaluation'] != matched.evaluate(pair)
            or pair['sources_before'] != pair['sources_after'] or pair['sources_after'] != matched.source_hashes()):
        raise RuntimeError('matched tactile prerequisite/source mismatch')
    provenance = pulse.verify_m9a_provenance()
    if (pulse.MAGNITUDE_NATIVE != 1.024 or pulse.START_TRANSITION != START or pulse.STOP_TRANSITION != STOP):
        raise RuntimeError('historical pulse definition changed')
    reference = dict(path=baseline_path.relative_to(ROOT).as_posix(), arm='ENABLED', **hashes)
    baseline = pair['arms']['ENABLED']
    return baseline, dict(verified=True, earlier=earlier, baseline=reference, force_provenance=provenance)


def force_at_transition(pushed, transition):
    return pulse.force_at_transition('A_P' if pushed else 'A_C', transition)


class RecoveryTrial(Trial):
    def __init__(self, identity, populations=None):
        if identity not in FRESH:
            raise ValueError('unknown fresh condition')
        self.identity = identity
        self.withdraw = identity.startswith('OFF')
        super().__init__('ENABLED', populations=populations)

    def bind(self, sim, physics, obs):
        if not (int(physics.model.jnt_type[0])==0 and int(physics.model.jnt_qposadr[0])==0
                and int(physics.model.jnt_dofadr[0])==0):
            raise RuntimeError('native leading free-joint pose/velocity layout required')
        names = [context.identities.compiled_name(physics.model, 'body', i) for i in range(int(physics.model.nbody))]
        candidates = [i for i, name in enumerate(names) if context.identities.namespace_component(name) == 'Thorax']
        if len(candidates) != 1 or candidates[0] == 0:
            raise RuntimeError('unique exact Thorax body required')
        self.thorax_id = candidates[0]
        super().bind(sim, physics, obs)
        if self.thorax_id in self.context['identity']['tarsus5_body_ids'].values():
            raise RuntimeError('disturbance body overlaps a distal force sensor')
        self.context['force_body'] = dict(id=self.thorax_id, name=names[self.thorax_id],
                                          frame='world', point='body COM', torque=[0.,0.,0.])

    def capture(self, physics, obs, action):
        super().capture(physics, obs, action)
        wrenches = np.asarray(physics.data.xfrc_applied)
        self.samples[-1]['applied_body_wrenches'] = [dict(body_id=int(i), wrench=wrenches[i].tolist())
            for i in np.flatnonzero(np.any(wrenches != 0, axis=1))]
        self.samples[-1]['thorax_com_position'] = np.asarray(physics.data.xipos[self.thorax_id]).tolist()

    def step(self):
        self.condition = 'WITHHELD' if self.withdraw and len(self.neural) >= WITHDRAW_INDEX else 'ENABLED'
        fired = super().step()
        self.neural[-1]['delivery_phase'] = self.condition
        return fired


def create_session(trial):
    """Existing session settings, with the kernel's existing force callback."""
    from ..embodiment import _windows_m7d_corrected_spontaneous_adapter as adapter
    from ..embodiment import _windows_m8_live_condition as kernel
    from ..embodiment import live_v2_motor_interface as v2, live_v3_motor_interface as v3
    from ..embodiment import m7d_corrected_spontaneous as m7d
    value, records, table = adapter._protocol()
    value, records, table = v2.derive_v2(value, records, table)
    value, records, table = v3.derive_v3(value, records, table)
    def runtime(flygym, interfaces):
        sim, physics, obs, tid, sid = adapter._runtime(flygym, interfaces)
        try:
            trial.bind(sim, physics, obs)
        except BaseException:
            sim.close()
            raise
        return context.ObservedSimulation(sim, physics, trial), physics, obs, tid, sid
    return kernel.create_scientific_session(
        protocol=value, condition=m7d.CONDITIONS[0], condition_number=1, progress=lambda *_:'',
        cached_admission_assertion=v3.assert_v3_physical_admission, cached_records=records, cached_table=table,
        condition_names=m7d.CONDITIONS, contribution_gate=v3.gate_contributions, compact_telemetry=False,
        runtime_factory=runtime, proprioception_only=True, fixed_initial_baseline=True,
        m8_extended_telemetry=False, continuous=True, motor_channel_names=v3.V3_MOTOR,
        supplemental_motor_channels=v3.SUPPLEMENTAL_MOTOR_CHANNELS,
        telemetry_observer=trial.observe, motor_state_probe_factory=trial.attach,
        external_force_by_transition=lambda _, i: force_at_transition(trial.identity.endswith('_P'), i))


def run_arm(identity, progress):
    trial = RecoveryTrial(identity)
    result = dict(schema='tactile-recovery-arm-v1', identity=identity, protocol=PROTOCOL.copy(),
        run_status='ERROR', samples=trial.samples, neural=trial.neural, sources_before=sources())
    session = None
    try:
        session = create_session(trial)
        progress(f'{identity}: initializing fresh CNS; tactile is enabled before the common push time.')
        state = session.initialize()
        if state.time_ms != 0.:
            raise RuntimeError('nonzero reset time')
        last = time.monotonic()
        for step in range(1, STEPS+1):
            state = session.step(lightweight=True)
            if state.physics_transitions != step or state.neural_transitions != step//5:
                raise RuntimeError('authoritative transition count mismatch')
            if time.monotonic()-last >= 15:
                progress(f'{identity}: {step}/{STEPS} physics transitions.')
                last = time.monotonic()
        result['run_status'] = 'COMPLETE'
    except (Exception, KeyboardInterrupt) as exc:
        result.update(error=f'{type(exc).__name__}: {exc}', interrupted=isinstance(exc, KeyboardInterrupt))
    finally:
        if session is not None:
            try: session.close()
            except Exception as exc: result.update(run_status='ERROR', close_error=str(exc))
        trial.detach()
        result.update(context=trial.context, initial=trial.initial, sources_after=sources())
    return result


def write_arm(path, result):
    invalid = []
    safe = context.batch.finite_evidence(result, invalid=invalid)
    safe['nonfinite_measurement_paths'] = invalid
    raw = json.dumps(safe, separators=(',', ':'), allow_nan=False).encode()
    with Path(path).open('xb') as stream:
        with gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as archive:
            archive.write(raw)
    packed = Path(path).read_bytes()
    return dict(path=Path(path).name, gzip_sha256=hashlib.sha256(packed).hexdigest(),
        raw_json_sha256=hashlib.sha256(raw).hexdigest(), gzip_bytes=len(packed), raw_json_bytes=len(raw))


def force_audit(arm, identity):
    body = arm['context']['force_body']
    table = arm['context']['identity']
    bid = body['id']
    exact = (table['body_names'][bid] == body['name']
             and context.identities.namespace_component(body['name']) == 'Thorax'
             and sum(context.identities.namespace_component(n) == 'Thorax' for n in table['body_names']) == 1
             and bid not in table['tarsus5_body_ids'].values()
             and body['frame']=='world' and body['point']=='body COM' and body['torque']==[0.,0.,0.])
    good, active, impulse = bool(exact), 0, np.zeros(3)
    for i, sample in enumerate(arm['samples']):
        vector = np.asarray(force_at_transition(identity.endswith('_P'), i-1) if i else (0.,0.,0.))
        expected = [] if not np.any(vector) else [dict(body_id=bid, wrench=vector.tolist()+[0.,0.,0.])]
        good &= (sample['applied_body_wrenches'] == expected
                 and sample['external_applied_max'] == float(np.max(np.abs(vector)))
                 and sample['generalized_applied_max'] == 0)
        active += bool(sample['applied_body_wrenches'])
        for observed in sample['applied_body_wrenches']:
            impulse += np.asarray(observed['wrench'][:3])*context.DT
    return dict(passed=bool(good), active_applied_samples=active, impulse_native_force_s=impulse.tolist(), exact_body=body)


def arm_audit(arm, identity, prerequisite_info):
    old = context.evaluate(dict(protocol=context.PROTOCOL.copy(), run_status=arm['run_status'],
        prerequisite=prerequisite_info, sources_before=arm['sources_before'], sources_after=arm['sources_after'],
        context=arm['context'], samples=arm['samples']))
    nonforce = dict(old['checks'])
    present = 'no_external_forcing' in nonforce
    nonforce.pop('no_external_forcing', None)
    force = force_audit(arm, identity)
    gate = schedule = readout = finite = True
    inputs = set(arm['initial']['external_schedule'])
    tactile = {i for p in arm['initial']['tactile_inventory'].values() for i in p['dense_indices']}
    for k, row in enumerate(arm['neural']):
        withdrawn = identity.startswith('OFF') and k >= WITHDRAW_INDEX
        expected_mask = sorted(tactile) if withdrawn else []
        offered_t = set().union(*(set(v) for v in row['offered_tactile'].values()))
        offered_p = set(row['offered_proprio'])
        eligible, delivered = set(row['eligible']), set(row['delivered'])
        gate &= (delivered == (eligible-tactile if withdrawn else eligible)
            and row['withheld_mask_sha256'] == context.digest(expected_mask)
            and row['delivery_phase'] == ('WITHHELD' if withdrawn else 'ENABLED')
            and offered_t <= tactile and offered_p <= inputs-tactile and eligible <= offered_t|offered_p
            and row['sampling']['eligible_indices'] == row['eligible'])
        gate &= all(set(row['offered_tactile'][leg]) <= set(population['dense_indices'])
                    for leg,population in arm['initial']['tactile_inventory'].items())
        schedule &= (abs(row['time_ms']-(k+1)*.5) <= 1e-8 and row['sampling']['draws'] == 2269)
        readout &= (row['motor_readout_verified'] is True
            and set(row['motor_telemetry']['delivered_external_sensory_events']) == delivered
            and set(row['non_input_fired']) == set(row['fired'])-inputs)
        finite &= bool(np.isfinite(row['motor_telemetry']['commanded_joint_targets']).all())
    legs_ok = bool(old['legs']) and all(row['positive_samples'] and row['negative_samples'] and not any(row[k]
        for k in ('ambiguous_samples','force_disagreements','reconstruction_disagreements','telemetry_disagreements',
                  'calibration_surface_positive_samples')) for row in old['legs'].values())
    checks = dict(complete=arm['run_status']=='COMPLETE' and len(arm['samples'])==STEPS+1 and len(arm['neural'])==NEURAL_STEPS,
        complete_input_inventory=len(inputs)==2269 and len(tactile)==1877 and len(inputs-tactile)==392,
        fixed_protocol=arm['protocol']==PROTOCOL, source_integrity=arm['sources_before']==arm['sources_after']==sources(),
        finite_evidence=not arm['nonfinite_measurement_paths'], inherited_nonforce_checks=present and bool(nonforce) and all(nonforce.values()),
        exact_planned_force=force['passed'], distal_attribution_and_coverage=bool(legs_ok), phase_gate=bool(gate),
        neural_schedule=bool(schedule), motor_readout=bool(readout and finite),
        calibrated_configuration=arm['context']['configuration']==prerequisite_info['earlier']['configuration'])
    return dict(passed=all(checks.values()), checks=checks, force=force, legacy_no_force_audit=old)


def support_counts(arm):
    table = arm['context']['identity']
    ground = {i for i in table['ground_geom_ids'] if context.identities.namespace_component(table['geom_names'][i])=='ground'}
    by_geom = {i:l for l in context.LEGS for i, name in enumerate(table['geom_names'])
               if context.identities.namespace_component(name)==f'{l}Tarsus5'}
    counts = []
    for sample in arm['samples']:
        legs = set()
        for pair in sample['contacts']:
            a,b = pair['geom1_id'],pair['geom2_id']
            if a in ground and b in by_geom: legs.add(by_geom[b])
            if b in ground and a in by_geom: legs.add(by_geom[a])
        counts.append(len(legs))
    return counts


def prefix_checks(arm, reference):
    fields = ('qpos','qvel','ctrl','joint_positions','telemetry_forces','tactile')
    physics = all(all(a[k]==b[k] for k in fields) for a,b in zip(arm['samples'][:START+1],reference['samples'][:START+1]))
    neural = all(a==b for a,b in zip(arm['neural'][:WITHDRAW_INDEX],
        [dict(row,delivery_phase='ENABLED') for row in reference['neural'][:WITHDRAW_INDEX]]))
    return dict(initial=arm['initial']==reference['initial'] and arm['context']['physics_model_identity']==reference['context']['physics_model_identity'],
                physical_prefix=physics, neural_prefix=neural)


def analyze(directory, manifest, baseline):
    checks = dict(prerequisite=manifest['prerequisite']['verified'], fixed_protocol=manifest['protocol']==PROTOCOL,
                  sources=manifest['sources_before']==manifest['sources_after']==sources(),
                  all_fresh=set(manifest['artifacts'])==set(FRESH))
    summaries, traces, samplings, arms = {}, {}, {}, {}
    baseline_trace = metrics.trace(baseline, support_counts(baseline))
    traces['ON_C'] = baseline_trace
    for identity in FRESH:
        arm, hashes = read_gzip(Path(directory)/manifest['artifacts'][identity]['path'])
        checks[f'{identity}_archive'] = all(hashes[k]==manifest['artifacts'][identity][k] for k in hashes)
        audit = arm_audit(arm, identity, manifest['prerequisite'])
        audit['prefix'] = prefix_checks(arm, baseline)
        checks[f'{identity}_integrity'] = audit['passed'] and all(audit['prefix'].values())
        samplings[identity] = [dict(row['sampling'],eligible_indices=[]) for row in arm['neural']]
        traces[identity] = metrics.trace(arm, support_counts(arm))
        tactile = {i for p in arm['initial']['tactile_inventory'].values() for i in p['dense_indices']}
        first = next((k for k,row in enumerate(arm['neural']) if k>=WITHDRAW_INDEX and set(row['eligible'])&tactile),None)
        cut = len(arm['samples']) if first is None else (first+1)*5+1
        # Only the matching prefix and neural records are needed after reducing physics.
        arms[identity] = dict(initial=arm['initial'],neural=arm['neural'],samples=arm['samples'][:cut])
        summaries[identity] = audit
        del arm
        gc.collect()
    baseline_sampling = [dict(r['sampling'],eligible_indices=[]) for r in baseline['neural']]
    checks['common_uniform_schedule'] = all(s==baseline_sampling for s in samplings.values())
    exposure = {}
    for off,on in (('OFF_C','ON_C'),('OFF_P','ON_P')):
        reference = baseline if on=='ON_C' else arms[on]
        arm = arms[off]
        tactile = {i for p in arm['initial']['tactile_inventory'].values() for i in p['dense_indices']}
        first = next((k for k,row in enumerate(arm['neural']) if k>=WITHDRAW_INDEX and set(row['eligible'])&tactile),None)
        boundary = len(arm['neural']) if first is None else first+1
        checks[f'{off}_matched_until_withdrawal'] = all(all(a[k]==b[k] for k in ('pre_state_sha256','offered_proprio','offered_tactile'))
            for a,b in zip(arm['neural'][:boundary],reference['neural'][:boundary]))
        physical_boundary = len(arm['samples']) if first is None else (first+1)*5+1
        checks[f'{off}_physical_matching_until_withdrawal'] = len(reference['samples'])>=physical_boundary and all(
            all(a[k]==b[k] for k in ('qpos','qvel','joint_positions','tactile'))
            for a,b in zip(arm['samples'][:physical_boundary],reference['samples'][:physical_boundary]))
        exposure[off] = dict(first_withdrawn_eligible_ms=None if first is None else arm['neural'][first]['time_ms'],
            withheld_eligible_events=sum(len(set(row['eligible'])&tactile) for row in arm['neural'][WITHDRAW_INDEX:]))
    on = metrics.response(traces['ON_P'],traces['ON_C'])
    off = metrics.response(traces['OFF_P'],traces['OFF_C'])
    interaction = ((traces['ON_P']['position']-traces['ON_C']['position'])
                   -(traces['OFF_P']['position']-traces['OFF_C']['position']))
    difference = metrics.contrast(on,off)
    for identity,value in exposure.items():
        if value['withheld_eligible_events']==0:
            difference['interpretation_limits'].append(f'{identity}_NO_WITHDRAWAL_EXPOSURE')
    return dict(integrity_passed=all(checks.values()), checks=checks, fresh_audits=summaries,
        withdrawal_exposure=exposure, responses=dict(ON=on,OFF=off), contrast=difference,
        peak_root_position_interaction_mm=float(np.max(np.linalg.norm(interaction[STOP+1:],axis=1))),
        active_balance_proven=False,
        interpretation='One modeled disturbance and tactile-withdrawal factorial; recovery bands and orientation attenuation are not proof of biological balance or gait.')


def build_run(directory, *, live=False, progress=print):
    manifest = dict(schema=PROTOCOL['schema'], protocol=PROTOCOL, run_status='NOT_RUN', artifacts={},
        sources_before=sources(), implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    baseline = None
    try:
        if live:
            baseline, info = prerequisite()
            manifest['prerequisite'] = info
            from ..embodiment._windows_m7d_corrected_spontaneous_adapter import _environment
            _environment()
            manifest['environment'] = {p:importlib.metadata.version(p) for p in ('flygym','mujoco','numpy')}
            statuses = []
            for identity in FRESH:
                result = run_arm(identity, progress)
                statuses.append(result['run_status'])
                manifest['artifacts'][identity] = write_arm(Path(directory)/f'{identity}.json.gz', result)
                interrupted = result.get('interrupted',False)
                del result
                gc.collect()
                if interrupted: break
            manifest['run_status'] = 'COMPLETE' if len(manifest['artifacts'])==len(FRESH) and all(s=='COMPLETE' for s in statuses) else 'INCOMPLETE'
    except (Exception,KeyboardInterrupt) as exc:
        manifest.update(run_status='ERROR',error=f'{type(exc).__name__}: {exc}')
    manifest['sources_after'] = sources()
    try:
        manifest['evaluation'] = analyze(directory,manifest,baseline) if baseline is not None and set(manifest['artifacts'])==set(FRESH) else dict(integrity_passed=False,status='NOT_RUN_OR_INCOMPLETE')
    except (KeyError,TypeError,ValueError,IndexError,OverflowError) as exc:
        manifest['evaluation'] = dict(integrity_passed=False,status='INVALID_OR_INCOMPLETE',reason=str(exc))
    return native(manifest)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(argv)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    manifest=build_run(args.output_dir,live=args.live,progress=lambda m:print(m,flush=True))
    with (args.output_dir/'manifest.json').open('x',encoding='utf-8') as stream:
        json.dump(manifest,stream,indent=2,allow_nan=False)
        stream.write('\n')
    print(f"Saved {args.output_dir}; integrity={manifest['evaluation']['integrity_passed']}",flush=True)
    return 0 if manifest['evaluation']['integrity_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
