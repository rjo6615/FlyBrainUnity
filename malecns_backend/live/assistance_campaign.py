"""Assistance contribution V1: fixed eight-arm fresh-process campaign/evaluator.

Default --output performs construction-free complete prerequisite checks only.
--live requires committed sources and a prior review note, then launches ONE
fixed A_NC..R_WP sequence: no retry, resume, prior-control reuse or fall stop.
Science still runs through the frozen original Trial/kernel via the adapter.
"""
from __future__ import annotations

import argparse
import copy
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from . import assistance_contribution_plan as plan
from . import assistance_native as mechanical
from . import assistance_trial as adapter
from . import controlled_live_balance as driver
from . import controlled_live_balance_v1_1 as guard
from . import tactile_recovery_metrics as metrics

base, original, ROOT = guard.base, guard.original, guard.ROOT
SCHEMA = 'assistance-contribution-campaign-v1'
PROTOCOL = 'docs/evidence/assistance-contribution-v1/protocol.json'
MANIFEST = 'docs/evidence/assistance-campaign-v1/implementation.json'
MODULE = 'malecns_backend/live/assistance_campaign.py'
OWN_SOURCES = (MODULE, 'docs/ASSISTANCE_CAMPAIGN_V1.md', 'tests/test_assistance_campaign.py')
ARM_IDS = plan.ARM_IDS
FIRST = 'A_NC'
QUALIFICATION = FIRST + '.qualification.json.gz'
FIRST_AFFECTED = 5006
CLEARED = slice(5201, None)
RESOLUTION_DEG = .25
POSTURE_LOSS = ('rollover_samples', 'below_minimum_up_samples', 'low_height_samples',
                'below_three_ground_support_samples')
CAMPAIGN = dict(schema=SCHEMA, protocol=PROTOCOL, arm_order=list(ARM_IDS), process_per_arm=True,
    qualification='FIRST_A_NC_ACTUAL_MODEL_ONCE_TRANSFERRED_UNCHANGED_TO_LATER_ARMS',
    complete_prerequisites=['controller_before', 'controller_after', 'worker_before', 'worker_after'],
    model_audit=dict(A='FROZEN_CONSTANT_AUDITOR_AND_PIECEWISE_MUST_AGREE',
                     R='PIECEWISE_M0_STATES_0_5005_MR_STATES_5006_20000'),
    physics_transitions_total=160000, states_total=160008, neural_updates_total=32000,
    automatic_retries=0, resume=False, reuse_previous_controls=False, stop_on_fall=False)


def canonical_sha256(path):
    return hashlib.sha256((ROOT/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def specification():
    """Frozen design, adapter checkpoint and V1.1 complete source authority."""
    plan.verify(ROOT/PROTOCOL)
    adapter.source_check()
    guard.specification()
    p = plan.read_json(ROOT/PROTOCOL)
    if ([a['id'] for a in p['arms']] != list(ARM_IDS) or p['automatic_retries'] != 0 or p['resume']
            or p['reuse_previous_controls'] or p['stop_on_fall']
            or p['planned_physics_transitions_total'] != CAMPAIGN['physics_transitions_total']):
        raise ValueError('prospective assistance protocol does not match fixed campaign policy')
    return p


def implementation_record():
    """Static source identity, deliberately not runtime/scientific readiness."""
    specification()
    return dict(schema='assistance-campaign-implementation-v1',
        status='IMPLEMENTED_ENGINEERING_TESTED_NATIVE_NOT_RUN', campaign=CAMPAIGN,
        protocol=dict(path=PROTOCOL, raw_sha256=hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest()),
        sources_canonical_lf_sha256={p: canonical_sha256(p) for p in OWN_SOURCES},
        native_qualification_executed=False, scientific_campaign_executed=False,
        motor_coverage=[20, 42], new_motor_admissions=0)


def source_check(path=None):
    record = plan.read_json(path or ROOT/MANIFEST)
    mechanical.require(record == implementation_record(), 'campaign implementation source checkpoint mismatch')
    return record


def sources():
    paths = (*plan.SOURCE_PATHS, *adapter.SOURCES, adapter.MANIFEST, PROTOCOL, MANIFEST, *OWN_SOURCES)
    return dict(guard.sources(), **{p: canonical_sha256(p) for p in paths})


def committed():
    head = guard.committed()
    for path in sources():
        if base.git('show', 'HEAD:'+path).replace(b'\r\n', b'\n') != (ROOT/path).read_bytes().replace(b'\r\n', b'\n'):
            raise ValueError('commit campaign implementation and every source before execution: '+path)
    return head


preflight = guard.preflight
verified_preflight = guard.verified_preflight


def save(path, payload):
    """Existing exclusive publication, then flushed to stable storage."""
    artifact = base.save(path, payload)
    with Path(path).open('r+b') as stream:
        os.fsync(stream.fileno())
    return artifact


def read_artifact(folder, artifact, expected_path):
    if artifact['path'] != expected_path:
        raise ValueError('invalid fixed artifact path')
    raw = (Path(folder)/artifact['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != artifact['sha256']:
        raise ValueError('raw artifact SHA256 mismatch: '+expected_path)
    return json.loads(gzip.decompress(raw))


def read_arm(folder, arm_id, artifact):
    if arm_id not in ARM_IDS:
        raise ValueError('unknown fixed arm')
    return read_artifact(folder, artifact, arm_id+'.json.gz')


def read_display(folder, arm_id, artifact):
    if arm_id not in ARM_IDS:
        raise ValueError('unknown fixed arm')
    return read_artifact(folder, artifact, arm_id+'.display.json.gz')


def read_qualification(folder, artifact):
    """Re-evaluate the transferred first-model record; never trust a status flag."""
    report = read_artifact(folder, artifact, QUALIFICATION)
    mechanical.evaluate_qualification(report)
    return report


def worker(request_path):
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text(encoding='utf-8'))
    folder, arm_id = request_path.parent, request['arm_id']
    if (arm_id not in ARM_IDS or request_path.name != arm_id+'.request.json'
            or set(request) != {'arm_id', 'controller_sha256', 'qualification'}
            or (request['qualification'] is None) != (arm_id == FIRST)):
        raise ValueError('invalid fixed assistance worker request')
    control_path = folder/'controller.json'
    control = json.loads(control_path.read_text(encoding='utf-8'))
    if (control['schema'] != SCHEMA or control['campaign'] != CAMPAIGN
            or control['specification'] != specification() or control['commit'] != committed()
            or control['sources'] != sources() or not isinstance(control['prior_full_body_review_note'], str)
            or not control['prior_full_body_review_note'].strip()
            or not verified_preflight(control['complete_preflight'])
            or request['controller_sha256'] != hashlib.sha256(control_path.read_bytes()).hexdigest()):
        raise ValueError('assistance worker source/commit/controller/prerequisite mismatch')
    save(folder/f'{arm_id}.claim.json', dict(arm_id=arm_id, pid=os.getpid()))
    before = sources()
    arm = dict(arm_id=arm_id, condition=arm_id.split('_')[1], run_status='ERROR', samples=[], neural=[])
    display = None
    try:
        boundary = original.process_boundary(folder/arm_id)
        if (folder/'STOP.json').exists():
            raise KeyboardInterrupt('stopped before complete prerequisite check')
        checked = preflight()
        arm['complete_preflight_before'] = checked
        if not verified_preflight(checked) or checked != control['complete_preflight']:
            raise ValueError('worker complete original source prerequisites failed before initialization')
        qualification = None if arm_id == FIRST else read_qualification(folder, request['qualification'])
        physical_protocol, table = base.static_authority()
        import flygym
        registry = original.fresh_registry(flygym)
        arm, display = adapter.run_arm(arm_id, physical_protocol, table, folder/'STOP.json',
                                       qualification=qualification)
        arm.update(complete_preflight_before=checked, transferred_qualification=request['qualification'],
                   process_boundary=dict(boundary, fresh_registry=registry, commit=control['commit']))
        arm['complete_preflight_after'] = preflight()
        if not verified_preflight(arm['complete_preflight_after']) or arm['complete_preflight_after'] != checked:
            raise ValueError('worker original source prerequisites changed after acquisition')
    except (Exception, KeyboardInterrupt) as exc:
        arm.update(run_status='ERROR', worker_error=f'{type(exc).__name__}: {exc}')
    arm.update(worker_sources_before=before, worker_sources_after=sources())
    # A failed/partial first-model qualification is retained, never retried.
    qualification_artifact = (save(folder/QUALIFICATION, arm.get('assistance', {}).get('qualification'))
                              if arm_id == FIRST else None)
    artifact = save(folder/f'{arm_id}.json.gz', arm)
    display_artifact = save(folder/f'{arm_id}.display.json.gz', display)
    save(folder/f'{arm_id}.done.json', dict(arm_id=arm_id, pid=os.getpid(), run_status=arm['run_status'],
        process_boundary=arm.get('process_boundary'), states=len(arm['samples']),
        neural_updates=len(arm['neural']), mechanical_states=len(arm.get('assistance', {}).get('samples', [])),
        artifact=artifact, display_artifact=display_artifact, qualification_artifact=qualification_artifact))
    return 0 if arm['run_status'] == 'COMPLETE' else 1


def run_child(folder, arm_id, controller_sha256, qualification):
    """A single fresh OS launch; no retry, registry reset or scientific options."""
    folder = Path(folder)
    if arm_id not in ARM_IDS or (qualification is None) != (arm_id == FIRST):
        raise ValueError('unknown fixed arm or qualification transfer')
    request = folder/f'{arm_id}.request.json'
    save(request, dict(arm_id=arm_id, controller_sha256=controller_sha256, qualification=qualification))
    launch_dir = folder/arm_id
    launch_dir.mkdir(exist_ok=False)
    command = [sys.executable, '-u', '-m', 'malecns_backend.live.assistance_campaign',
               '--worker-request', str(request.resolve())]
    isolation = ({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
                 if os.name == 'nt' else {'start_new_session': True})
    log_path, interrupted = folder/f'{arm_id}.log.txt', False
    with log_path.open('xb') as log:
        process = subprocess.Popen(command, cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING='utf-8',
            PYTHONUNBUFFERED='1'), stdout=log, stderr=subprocess.STDOUT, **isolation)
        save(launch_dir/'launch.tmp.json', dict(launch_pid=process.pid, controller_pid=os.getpid()))
        (launch_dir/'launch.tmp.json').replace(launch_dir/'launch.json')
        position = 0
        while True:
            try:
                code = process.poll()
                with log_path.open('rb') as reader:
                    reader.seek(position)
                    output = reader.read()
                    position = reader.tell()
                if output:
                    print(output.decode('utf-8', errors='replace'), end='', flush=True)
                if code is not None:
                    break
                time.sleep(1.)  # Controller polling only; no scientific pacing.
            except KeyboardInterrupt:
                interrupted = True
                if not (folder/'STOP.json').exists():
                    save(folder/'STOP.json', dict(reason='user stop', arm_id=arm_id))
                print('Stop requested; waiting for partial evidence preservation.', flush=True)
    path = folder/f'{arm_id}.done.json'
    if not path.exists():
        raise RuntimeError(f'{arm_id} worker exited {code} without raw-file receipt; no retry')
    receipt = json.loads(path.read_text(encoding='utf-8'))
    boundary = receipt.get('process_boundary')
    if (receipt['arm_id'] != arm_id or receipt['run_status'] == 'COMPLETE' and (code != 0 or boundary is None)
            or boundary is not None and (boundary['launch_pid'] != process.pid
                or not original.valid_boundary(boundary, os.getpid()) or boundary['pid'] != receipt['pid'])):
        raise ValueError('assistance worker receipt/exit/ancestry mismatch')
    return receipt, interrupted


def configuration_phases(arm):
    """Independently derive MR's guarded configuration from recorded M0."""
    ctx = arm['context']
    if ctx['configuration_sha256'] != base.context.digest(ctx['configuration']):
        raise ValueError('recorded M0 configuration digest mismatch')
    ids = [r['actuator_id'] for r in mechanical.partition(ctx['native_inventory'])[1]]
    neutral = copy.deepcopy(ctx['configuration'])
    for name in mechanical.FIELDS:
        rows = neutral['arrays'][name]
        for aid in ids:
            rows[aid] = [0.]*len(rows[aid])
    phases = dict(M0=ctx['configuration_sha256'], MR=base.context.digest(neutral))
    if phases['M0'] == phases['MR']:
        raise ValueError('selected gain/bias rows already zero; intervention would be vacuous')
    return phases, ids, neutral


def audit_piecewise(arm, arm_id):
    """Original audit_arm mathematics with an explicit M0/MR phase guard.

    Every reconstruction, force, RNG and command check delegates to the frozen
    helpers. Only the per-sample configuration identity follows the declared
    piecewise phase instead of the frozen constant-model expectation.
    """
    if arm['condition'] != arm_id.split('_')[1]:
        raise ValueError('arm/base condition mismatch')
    if arm['run_status'] != 'COMPLETE' or len(arm['samples']) != base.STEPS+1 or len(arm['neural']) != base.TICKS:
        raise ValueError('incomplete fixed budget')
    samples, neural, ctx, initial = arm['samples'], arm['neural'], arm['context'], arm['initial']
    base.context.validate_identity(ctx['identity'])
    if (ctx['adhesion_enabled'] or not ctx['inherited_surface_unchanged']
            or ctx['configuration']['timestep'] != .0001 or not arm['initialization_operations']):
        raise ValueError('support context or initialization accounting missing')
    phases, _, _ = configuration_phases(arm)
    schedule = initial['external_schedule']
    if len(schedule) != 392 or schedule != sorted(set(schedule)):
        raise ValueError('392 unique common slots required')
    from .tactile_recovery import support_counts
    from ..embodiment.m8_contact_kinematics import namespace_component
    from ..embodiment.proprioceptive_activation import sample_candidates
    ground_counts = support_counts(arm)
    calibration_counts, unexpected, correspondence = [], [], []
    ground = ctx['identity']['ground_geom_ids']
    gid = next(g for g in ground if namespace_component(ctx['identity']['geom_names'][g]) == 'ground')
    sid = next(g for g in ground if g != gid)
    inv = ctx['native_inventory']
    for i, s in enumerate(samples):
        if (np.asarray(s['qpos']).shape != (inv['nq'],) or np.asarray(s['qvel']).shape != (inv['nv'],)
                or np.asarray(s['ctrl']).shape != (48,)
                or np.asarray(s['xfrc_applied']).shape != (len(ctx['identity']['body_names']), 6)
                or np.asarray(s['qfrc_applied']).shape != (inv['nv'],)):
            raise ValueError('incomplete native state/control/force array shape')
        if not np.isfinite(np.asarray(s['qpos']+s['qvel']+s['ctrl'], dtype=float)).all():
            raise ValueError('nonfinite physical evidence')
        if (abs(s['time_s']-i*.0001) > 1e-10
                or s['configuration_sha256'] != phases[plan.expected_model_phase(arm_id, i)]
                or s['observer_state_before_sha256'] != s['observer_state_after_sha256']):
            raise ValueError('physical clock/piecewise configuration/observer mismatch')
        xfrc = np.zeros(np.asarray(s['xfrc_applied']).shape)
        if i:
            xfrc[ctx['thorax_body_id'], :3] = base.force(arm['condition'], i-1)
        if (not np.array_equal(s['xfrc_applied'], xfrc) or np.any(s['qfrc_applied'])
                or s['external_applied_max'] != float(np.max(np.abs(xfrc)))
                or s['generalized_applied_max'] != 0):
            raise ValueError('complete declared force arrays mismatch')
        summary = base.context.summarize_sample(s, ctx['identity'])
        if any(not v['reconstruction_matches'] or not v['telemetry_matches'] for v in summary.values()):
            raise ValueError('force/contact reconstruction mismatch')
        calibration_counts.append(sum(np.linalg.norm(v['reconstructed_by_surface'][str(sid)]) > base.context.THRESHOLD
                                      for v in summary.values()))
        unexpected.append(sum(v['unselected_pairs'] for v in summary.values()))
        correspondence.append(sum(not v['correspondence'] for v in summary.values()))
    cns_rng = np.random.Generator(np.random.PCG64())
    cns_rng.bit_generator.state = copy.deepcopy(initial['rng_state'])
    local_rngs = {l: np.random.Generator(np.random.PCG64()) for l in base.context.LEGS}
    for l, r in local_rngs.items():
        r.bit_generator.state = copy.deepcopy(initial['proprio_rng_state'][l])
    for t, n in enumerate(neural, 1):
        if (abs(n['time_ms']-t*.5) > 1e-8 or n['rng_indices'] != schedule or n['draws'] != 392
                or not n['readout_verified'] or set(n['offered'])-set(schedule)
                or set(n['delivered'])-set(n['offered']) or set(n['eligible'])-set(n['offered'])
                or n['telemetry']['scheduled_sensory_candidate_events'] != n['offered']
                or n['telemetry']['delivered_external_sensory_events'] != n['delivered']):
            raise ValueError('neural clock/RNG/input/readout boundary mismatch')
        uniforms = cns_rng.random(392)
        if base.array_digest(uniforms) != n['uniforms_sha256'] or cns_rng.bit_generator.state != n['rng_state']:
            raise ValueError('independent CNS common-slot replay mismatch')
        offered = []
        for l, r in local_rngs.items():
            rates = n['telemetry']['encoded_sensory_rates'][l]
            indices = initial['encoder_state'][l]['dense_indices']
            if len(rates) != len(indices):
                raise ValueError('per-leg encoded sensory inventory mismatch')
            offered.extend(indices[int(i)] for i in sample_candidates(rates, r))
            if r.bit_generator.state != n['proprio_rng_state'][l]:
                raise ValueError('independent per-leg candidate RNG replay mismatch')
        if sorted(set(offered)) != n['offered']:
            raise ValueError('independent candidate event replay mismatch')
    return dict(commands=base.audit_commands(arm), ground_support_counts=ground_counts,
                calibration_support_counts=calibration_counts, unexpected_distal_contact_counts=unexpected,
                contact_correspondence_mismatch_counts=correspondence)


def audit_scientific(arm, arm_id):
    """A: frozen constant auditor genuinely accepts AND equals piecewise. R: piecewise."""
    audit = audit_piecewise(arm, arm_id)
    if arm_id.startswith('A_'):
        if base.audit_arm(arm) != audit:
            raise ValueError('frozen constant-model auditor disagrees with piecewise A audit')
        return dict(audit, model_context='M0_CONSTANT_FROZEN_AUDITOR_ACCEPTED')
    return dict(audit, model_context='PIECEWISE_M0_0_5005_MR_5006_20000')


def audit_mechanical(arm, arm_id, qualification):
    evidence = arm['assistance']
    ctx = evidence['context']
    inv, record = ctx['inventory'], ctx['original']
    if (arm['schema'] != 'assistance-arm-adapter-v1' or arm['arm_id'] != arm_id
            or ctx['schema'] != mechanical.SCHEMA or ctx['arm_id'] != arm_id
            or inv != arm['context']['native_inventory']):
        raise ValueError('mechanical evidence identity mismatch')
    mechanical.validate_binding(inv, record)
    if ctx['neutral'] != mechanical.neutral_record(record, inv):
        raise ValueError('recorded MR does not equal independently derived MR')
    if evidence['qualification'] != qualification or record != qualification['original']:
        raise ValueError('actual model/qualification transfer differs from qualified first M0')
    _, ids, neutral_config = configuration_phases(arm)
    if evidence['event']['selected_actuator_ids'] != ids:
        raise ValueError('scientific and mechanical selected actuator IDs disagree')
    for name in mechanical.FIELDS:
        for phase, config in ((record, arm['context']['configuration']), (ctx['neutral'], neutral_config)):
            if not np.array_equal(mechanical.array_values(phase, name), np.asarray(config['arrays'][name], dtype=float)):
                raise ValueError('mechanical model record and guarded configuration disagree: '+name)
    trace = mechanical.audit_trace(arm_id, inv, record, evidence['event'], evidence['samples'])
    for m, s in zip(evidence['samples'], arm['samples']):
        if any(m[k] != s[k] for k in ('time_s', 'ctrl', 'xfrc_applied', 'qfrc_applied')):
            raise ValueError('mechanical and scientific samples describe different states')
    return trace


def proof(arm):
    """Original proof material; pose compacted to arrays for eight-arm memory."""
    value = original.proof(arm)
    value['pose'] = dict(samples=[dict(qpos=np.asarray(s['qpos'], dtype=float), qvel=np.asarray(s['qvel'], dtype=float))
                                  for s in value['pose']['samples']])
    return value


def compare_all(proofs):
    ref = proofs[FIRST]
    for arm_id in ARM_IDS:
        for field in ('initial', 'context', 'physical_prefix', 'neural_prefix', 'rng'):
            if proofs[arm_id][field] != ref[field]:
                raise ValueError('all-eight full science prefix/RNG check failed: '+arm_id+'/'+field)
    exposure = {}
    for level in ('A', 'R'):
        within = original.compare_proofs({c: proofs[f'{level}_{c}'] for c in base.CONDITIONS})
        exposure.update({f'{level}_{k[:2]}_vs_{level}_{k[-2:]}': v for k, v in within.items()})
    for push in ('C', 'P'):
        group = [f'{m}_{n}{push}' for m in 'AR' for n in 'NW']
        for arm_id in group:
            if (proofs[arm_id]['same_push_prefix'] != proofs[group[0]]['same_push_prefix']
                    or proofs[arm_id]['pre_gate'] != proofs[group[0]]['pre_gate']):
                raise ValueError('same-push physical/applied/pre-gate prefix mismatch: '+arm_id)
    for c in base.CONDITIONS:
        a, r = proofs['A_'+c], proofs['R_'+c]
        action = next((i-1 for i, (x, y) in enumerate(zip(a['actions'], r['actions'])) if i and x != y), None)
        physical = next((i for i, (x, y) in enumerate(zip(a['physics'], r['physics'])) if x != y), None)
        if physical is not None and physical < FIRST_AFFECTED:
            raise ValueError('mechanical pair diverged before first affected state')
        exposure[f'A_{c}_vs_R_{c}'] = dict(first_actual_outgoing_command_difference=action,
            first_physical_difference_state=physical,
            first_actual_command_effect_state=None if action is None else action+1)
    return exposure


def same_policy_mechanical_prefix(proofs):
    """Diagnostic only, not acceptance: A_x/R_x complete state-0..5005 records."""
    result = {}
    for c in base.CONDITIONS:
        a, r = proofs['A_'+c], proofs['R_'+c]
        result[c] = ('EXACT_MATCH' if a['full_boundary_prefix'] == r['full_boundary_prefix']
                     and a['neural_boundary_prefix'] == r['neural_boundary_prefix'] else 'MISMATCH')
    return result


def posture_lost(posture):
    return any(posture[k] > 0 for k in POSTURE_LOSS)


def tilt_label(first, second, posture):
    peak = posture[first]['world_tilt_peak_deg']-posture[second]['world_tilt_peak_deg']
    mean = posture[first]['world_tilt_mean_deg']-posture[second]['world_tilt_mean_deg']
    label = (f'LOWER_WORLD_TILT_IN_{first}' if peak < -RESOLUTION_DEG and mean < -RESOLUTION_DEG else
             f'HIGHER_WORLD_TILT_IN_{first}' if peak > RESOLUTION_DEG and mean > RESOLUTION_DEG else
             'MIXED_OR_UNRESOLVED')
    return label, peak, mean


def behavior(poses, audits, protocol):
    """Declared descriptors only: no successful arm, score or balance fraction."""
    levels = {m: base.behavior({c: poses[f'{m}_{c}'] for c in base.CONDITIONS},
                               {c: audits[f'{m}_{c}'] for c in base.CONDITIONS}) for m in 'AR'}
    traces = {a: metrics.trace(poses[a], audits[a]['ground_support_counts']) for a in ARM_IDS}
    posture = {f'{m}_{c}': levels[m]['posture'][c] for m in 'AR' for c in base.CONDITIONS}
    descriptors, recovery = {}, {}
    for a, tr in traces.items():
        p, v = tr['position'], tr['velocity']
        linear, angular = np.linalg.norm(v[CLEARED, :3], axis=1), np.linalg.norm(v[CLEARED, 3:], axis=1)
        descriptors[a] = dict(posture[a], root_height_mean_mm=float(np.mean(p[CLEARED, 2])),
            root_height_min_mm=float(np.min(p[CLEARED, 2])), root_height_final_mm=float(p[-1, 2]),
            root_position_final_mm=p[-1].tolist(), root_displacement_final_mm=(p[-1]-p[0]).tolist(),
            world_linear_speed_mean_mm_s=float(np.mean(linear)), world_linear_speed_peak_mm_s=float(np.max(linear)),
            world_angular_speed_mean_rad_s=float(np.mean(angular)),
            world_angular_speed_peak_rad_s=float(np.max(angular)),
            minimum_ground_support=int(np.min(tr['supports'][CLEARED])),
            posture_lost_in_cleared_window=posture_lost(posture[a]))
    for m in 'AR':
        for n in 'NW':
            pushed, control = f'{m}_{n}P', f'{m}_{n}C'
            recovery[pushed] = dict(levels[m]['responses'][n+'P'], own_control=control,
                qualifiers=['CONTROL_POSTURE_LOSS_CONFOUNDS_RECOVERY'] if posture_lost(posture[control]) else [])
    comparisons = {}
    declared = protocol['comparisons']
    for kind in ('mechanical_pairs', 'neural_pairs'):
        for first, second in declared[kind]:
            label, peak, mean = tilt_label(first, second, posture)
            qualifiers = sorted({f'{a}_CONTROL_POSTURE_LOSS_CONFOUNDS_RECOVERY' for a in (first, second)
                                 if a in recovery and recovery[a]['qualifiers']})
            comparisons[f'{first}_vs_{second}'] = dict(kind=kind[:-6], first=first, second=second,
                tilt_label=label, world_tilt_peak_first_minus_second_deg=peak,
                world_tilt_mean_first_minus_second_deg=mean,
                descriptors={a: descriptors[a] for a in (first, second)},
                own_control_recovery={a: recovery.get(a) for a in (first, second)}, qualifiers=qualifiers)
    up = {a: metrics.angular_velocity_world(tr['quaternion'], np.tile([0., 0., 1.], (len(tr['quaternion']), 1)))
          for a, tr in traces.items()}
    position = {a: tr['position'] for a, tr in traces.items()}
    contrasts = {}
    for name, values in (('root_position', position), ('world_up', up)):
        push = {f'{m}_{n}': values[f'{m}_{n}P']-values[f'{m}_{n}C'] for m in 'AR' for n in 'NW'}
        neural = {m: push[m+'_N']-push[m+'_W'] for m in 'AR'}
        contrasts[name] = dict(
            mechanical_push_at_neural={n: (push['R_'+n]-push['A_'+n]).tolist() for n in 'NW'},
            neural_push_at_assistance={m: neural[m].tolist() for m in 'AR'},
            neural_push_R_minus_A=(neural['R']-neural['A']).tolist())
    for m in 'AR':
        if (contrasts['root_position']['neural_push_at_assistance'][m] != levels[m]['factorial_root_vector']
                or contrasts['world_up']['neural_push_at_assistance'][m] != levels[m]['factorial_world_up_vector']):
            raise ValueError('factorial contrast disagrees with original behavior convention')
    limits = ['ONE_SEED_ASSISTED_POSITION_CONTROL_NOT_INDEPENDENT_BALANCE_OR_GAIT',
              'PARTIAL_ASSISTANCE_CONTRIBUTION_20_NEURAL_POSITION_SERVOS_STILL_ASSIST',
              'FRESH_A_ARMS_ARE_ENGINEERING_REFERENCE_PRIOR_OUTCOME_KNOWN',
              'NONLINEAR_CONTRASTS_NOT_ADDITIVE_FRACTIONS_OF_BALANCE']
    limits += [f'{m}_{limit}' for m in 'AR' for limit in levels[m]['interpretation_limits']
               if limit != limits[0]]
    return dict(levels=levels, comparisons=comparisons, own_control_recovery=recovery,
        signed_contrasts=contrasts, interpretation_limits=limits, independent_balance_proven=False,
        gait_proven=False, motor_coverage=[20, 42], new_motor_admissions=0)


def evaluate(report, folder, *, loader=read_arm, display_loader=read_display,
             qualification_loader=read_qualification, reference_comparator=driver.compare_reference):
    checks, audits, mechanics, proofs, pids, display, comparisons = {}, {}, {}, {}, [], {}, {}
    try:
        protocol = specification()
        checks.update(schema=report['schema'] == SCHEMA, campaign=report['campaign'] == CAMPAIGN,
            specification=report['specification'] == protocol, complete=report['run_status'] == 'COMPLETE',
            original_design=report['design'] == base.design(),
            prerequisites_before=verified_preflight(report['preflight']),
            prerequisites_after=verified_preflight(report['preflight_after'])
                and report['preflight_after'] == report['preflight'],
            sources=bool(report['sources_before']) and report['sources_before'] == report['sources_after'] == sources(),
            review_note=isinstance(report['prior_full_body_review_note'], str)
                and bool(report['prior_full_body_review_note'].strip()),
            fixed_arm_order=list(report['arm_artifacts']) == list(report['display_artifacts']) == list(ARM_IDS),
            qualification_transfer=isinstance(report['qualification_artifact'], dict)
                and report['qualification_artifact'].get('path') == QUALIFICATION)
        if not all(checks.values()):
            raise ValueError('incomplete or changed assistance campaign')
        qualification = qualification_loader(folder, report['qualification_artifact'])
        qualified = mechanical.evaluate_qualification(qualification)
        for arm_id in ARM_IDS:
            arm = loader(folder, arm_id, report['arm_artifacts'][arm_id])
            boundary = arm['process_boundary']
            if (arm['arm_id'] != arm_id or arm['condition'] != arm_id.split('_')[1]
                    or arm['worker_sources_before'] != report['sources_before']
                    or arm['worker_sources_after'] != report['sources_after']
                    or arm['complete_preflight_before'] != report['preflight']
                    or arm['complete_preflight_after'] != report['preflight']
                    or arm['transferred_qualification'] != (None if arm_id == FIRST else report['qualification_artifact'])
                    or boundary['fresh_registry'] != dict(existing_names=[], default_name=0)
                    or boundary['commit'] != report['implementation_commit']
                    or not original.valid_boundary(boundary, report['controller_pid'])):
                raise ValueError('assistance worker identity/source/freshness mismatch: '+arm_id)
            if boundary['pid'] in pids:
                raise ValueError('distinct fresh worker PIDs required')
            pids.append(boundary['pid'])
            audits[arm_id] = audit_scientific(arm, arm_id)
            mechanics[arm_id] = audit_mechanical(arm, arm_id, qualification)
            proofs[arm_id] = proof(arm)
            proofs[arm_id].update(full_boundary_prefix=[base.context.digest(s) for s in arm['samples'][:FIRST_AFFECTED]],
                                  neural_boundary_prefix=[base.context.digest(n) for n in arm['neural'][:1001]])
            # Display/reference failures never bypass or change the science audit.
            try:
                display[arm_id] = driver.audit_display(arm, display_loader(folder, arm_id, report['display_artifacts'][arm_id]))
            except (OSError, KeyError, TypeError, ValueError) as exc:
                display[arm_id] = dict(status='FAILED', reason=f'{type(exc).__name__}: {exc}')
            if arm_id.startswith('A_'):
                try:
                    comparisons[arm_id] = reference_comparator(arm, report, arm['condition'])
                except Exception as exc:
                    comparisons[arm_id] = dict(status='UNAVAILABLE_OR_INVALID_REFERENCE', reason=f'{type(exc).__name__}: {exc}')
            del arm
            gc.collect()
        checks['per_arm_piecewise_and_mechanical_integrity'] = True
        exposure = compare_all(proofs)
        checks['cross_arm_prefix_rng_integrity'] = True
        scientific = dict(accepted=True, status='INTEGRITY_ACCEPTED', checks=checks, arms=audits,
            mechanical=mechanics, qualification=qualified, pair_exposure=exposure,
            same_policy_mechanical_prefix_diagnostic=same_policy_mechanical_prefix(proofs),
            behavior=behavior({a: p['pose'] for a, p in proofs.items()}, audits, protocol),
            unity_replay_eligible=True,
            unity_replay_entry_point='NOT_IMPLEMENTED_FOR_THIS_SCHEMA')
    except (OSError, KeyError, TypeError, ValueError, IndexError, OverflowError, gzip.BadGzipFile) as exc:
        scientific = dict(accepted=False, status='INCONCLUSIVE_INTEGRITY', checks=checks, arms=audits,
            mechanical=mechanics, behavior=None, unity_replay_eligible=False, reason=f'{type(exc).__name__}: {exc}')
    sessions = [d['session_id'] for d in display.values() if d.get('session_id')]
    if len(set(sessions)) != len(sessions):
        for arm_id in display:
            display[arm_id] = dict(status='FAILED', projection_status='FAILED', reason='display session identity reused across arms')
    return dict(scientific=scientific, display=display, reference_comparison=comparisons,
                visual_review='UNCONFIRMED')


def execute(folder, *, live=False, review_note='', child_runner=None):
    child_runner = child_runner or run_child
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, campaign=CAMPAIGN, specification=specification(), design=base.design(),
        sources_before=sources(), run_status='NOT_RUN', controller_pid=os.getpid(),
        prior_full_body_review_note=review_note, scientific_experiment_started=False,
        arm_artifacts={}, display_artifacts={}, qualification_artifact=None)
    report['preflight'] = preflight()
    save(folder/'preflight.json', report['preflight'])
    if live:
        try:
            if not review_note.strip():
                raise ValueError('prior full-body human review note is required before native execution')
            if not verified_preflight(report['preflight']):
                raise ValueError('complete original scientific prerequisites failed')
            report['implementation_commit'] = committed()
            control = dict(schema=SCHEMA, campaign=CAMPAIGN, specification=report['specification'],
                sources=report['sources_before'], commit=report['implementation_commit'],
                prior_full_body_review_note=review_note, complete_preflight=report['preflight'])
            artifact = save(folder/'controller.json', control)
            report['scientific_experiment_started'] = True
            completed = []
            for arm_id in ARM_IDS:
                if (folder/'STOP.json').exists():
                    break
                receipt, interrupted = child_runner(folder, arm_id, artifact['sha256'], report['qualification_artifact'])
                report['arm_artifacts'][arm_id] = receipt['artifact']
                report['display_artifacts'][arm_id] = receipt['display_artifact']
                save(folder/f'{arm_id}.controller-receipt.json', receipt)
                completed.append(receipt['run_status'] == 'COMPLETE')
                if not completed[-1] or interrupted:
                    break
                if arm_id == FIRST:
                    transfer = receipt['qualification_artifact']
                    evaluation = mechanical.evaluate_qualification(read_qualification(folder, transfer))
                    report['qualification_artifact'] = transfer
                    save(folder/'qualification-transfer.json', dict(artifact=transfer, evaluation=evaluation))
            report['run_status'] = ('COMPLETE' if len(completed) == len(ARM_IDS) and all(completed)
                                    and not (folder/'STOP.json').exists() else 'INCOMPLETE')
        except (Exception, KeyboardInterrupt) as exc:
            report.update(run_status='ERROR', error=f'{type(exc).__name__}: {exc}')
    report['preflight_after'] = preflight()
    report['sources_after'] = sources()
    report['evaluation'] = evaluate(report, folder)
    save(folder/'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path, help='new exclusive folder; construction-free unless --live')
    group.add_argument('--evaluate', type=Path, help='re-evaluate saved raw evidence; no native/CNS execution')
    group.add_argument('--check', action='store_true', help='static source checkpoint only')
    group.add_argument('--worker-request', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--review-note', default='')
    args = parser.parse_args(argv)
    if not args.output and (args.live or args.review_note):
        parser.error('only --output may request the one live campaign or carry its review note')
    if args.live and not args.review_note.strip():
        parser.error('--live requires --review-note describing actual prior full-body replay review')
    if args.worker_request:
        return worker(args.worker_request)
    if args.check:
        source_check()
        print('ASSISTANCE CAMPAIGN SOURCE CHECK VERIFIED; eight-arm evaluator/controller implemented; '
              'native qualification and physics/CNS campaign not run by this check.')
        return 0
    if args.evaluate:
        saved = json.loads((args.evaluate/'report.json').read_text(encoding='utf-8'))
        evaluation = evaluate(saved, args.evaluate)
        print(json.dumps(base.native(dict(status=evaluation['scientific']['status'],
            reason=evaluation['scientific'].get('reason'))), allow_nan=False))
        return 0 if evaluation['scientific']['accepted'] else 1
    report = execute(args.output, live=args.live, review_note=args.review_note)
    print(json.dumps(base.native(dict(status=report['run_status'], preflight_verified=report['preflight']['verified'],
        integrity=report['evaluation']['scientific']['status'],
        reason=report['evaluation']['scientific'].get('reason'))), allow_nan=False))
    return 0 if report['preflight']['verified'] and (not args.live or report['evaluation']['scientific']['accepted']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
