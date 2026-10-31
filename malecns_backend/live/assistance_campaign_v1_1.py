"""Assistance campaign V1.1: same eight-arm science, corrected live-data guard.

The executed V1 campaign/adapter sources and failed run-desktop-01 stay
immutable and locked. Scientific design, arm order, budget, prerequisites,
piecewise/frozen auditors, comparisons and acceptance are reused unchanged.
Default --output is construction-free; --live is ONE attempt with no retry.
"""
from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from . import assistance_campaign as v1
from . import assistance_native_v1_1 as guard
from . import assistance_trial_v1_1 as adapter

base, original, driver, mechanical, plan, ROOT = v1.base, v1.original, v1.driver, v1.mechanical, v1.plan, v1.ROOT
SCHEMA = 'assistance-contribution-campaign-v1.1'
AMENDMENT = 'docs/evidence/assistance-campaign-v1_1/protocol.json'
AMENDMENT_SHA256 = 'd9cc02308be22d8b7101db1d67a610394f167d122d378cbbee014536ed06d485'
MANIFEST = 'docs/evidence/assistance-campaign-v1_1/implementation.json'
MODULE = 'malecns_backend/live/assistance_campaign_v1_1.py'
OWN_SOURCES = (MODULE, 'malecns_backend/live/assistance_native_v1_1.py',
               'malecns_backend/live/assistance_trial_v1_1.py', 'docs/ASSISTANCE_CAMPAIGN_V1_1.md',
               'tests/test_assistance_campaign_v1_1.py')
ARM_IDS, FIRST, QUALIFICATION = v1.ARM_IDS, v1.FIRST, v1.QUALIFICATION
CAMPAIGN = dict(v1.CAMPAIGN, schema=SCHEMA, amendment=AMENDMENT, live_guard=guard.GUARD)
preflight, verified_preflight, save = v1.preflight, v1.verified_preflight, v1.save
read_arm, read_display, read_artifact = v1.read_arm, v1.read_display, v1.read_artifact


def amendment():
    raw = (ROOT/AMENDMENT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != AMENDMENT_SHA256:
        raise ValueError('V1.1 campaign amendment identity changed')
    p = plan.read_json(ROOT/AMENDMENT)
    failed = p['failed_attempt']
    if (p['scientific_parameters_changed'] or p['acceptance_changed'] or p['arm_order_changed']
            or p['budget_changed'] or p['automatic_retries'] != 0 or p['live_guard'] != guard.GUARD
            or p['guarded_fields'] != list(guard.INTEGRATION_FIELDS)
            or hashlib.sha256((ROOT/p['scientific_protocol']).read_bytes()).hexdigest() != p['scientific_protocol_raw_sha256']
            or hashlib.sha256((ROOT/failed['report']).read_bytes()).hexdigest() != failed['report_sha256']):
        raise ValueError('amendment declares a scientific change or retained failure changed')
    return p


def specification():
    """Unchanged V1 scientific specification, executed V1 sources and amendment."""
    v1.source_check()   # executed V1 campaign sources remain byte-identical
    return dict(scientific=v1.specification(), amendment=amendment())


def implementation_record():
    specification()
    return dict(schema='assistance-campaign-implementation-v1.1',
        status='IMPLEMENTED_ENGINEERING_TESTED_NATIVE_NOT_RUN', campaign=CAMPAIGN,
        amendment=dict(path=AMENDMENT, raw_sha256=AMENDMENT_SHA256),
        sources_canonical_lf_sha256={p: v1.canonical_sha256(p) for p in OWN_SOURCES},
        native_qualification_executed=False, scientific_campaign_executed=False,
        motor_coverage=[20, 42], new_motor_admissions=0)


def source_check(path=None):
    record = plan.read_json(path or ROOT/MANIFEST)
    mechanical.require(record == implementation_record(), 'V1.1 campaign implementation source checkpoint mismatch')
    return record


def sources():
    return dict(v1.sources(), **{p: v1.canonical_sha256(p) for p in (AMENDMENT, MANIFEST, *OWN_SOURCES)})


def committed():
    head = v1.guard.committed()
    for path in sources():
        if base.git('show', 'HEAD:'+path).replace(b'\r\n', b'\n') != (ROOT/path).read_bytes().replace(b'\r\n', b'\n'):
            raise ValueError('commit V1.1 campaign implementation and every source before execution: '+path)
    return head


def read_qualification(folder, artifact):
    report = v1.read_qualification(folder, artifact)
    if report.get('live_guard') != guard.GUARD:
        raise ValueError('transferred qualification was not produced under the V1.1 live-data guard')
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
    assistance = arm.get('assistance') or {}
    qualification_artifact = save(folder/QUALIFICATION, assistance.get('qualification')) if arm_id == FIRST else None
    artifact = save(folder/f'{arm_id}.json.gz', arm)
    display_artifact = save(folder/f'{arm_id}.display.json.gz', display)
    save(folder/f'{arm_id}.done.json', dict(arm_id=arm_id, pid=os.getpid(), run_status=arm['run_status'],
        process_boundary=arm.get('process_boundary'), states=len(arm['samples']),
        neural_updates=len(arm['neural']), mechanical_states=len(assistance.get('samples', [])),
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
    command = [sys.executable, '-u', '-m', 'malecns_backend.live.assistance_campaign_v1_1',
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


def audit_mechanical(arm, arm_id, qualification):
    """V1 mechanical evidence checks for V1.1-guard arms; same trace/force audit."""
    evidence = arm['assistance']
    ctx = evidence['context']
    inv, record = ctx['inventory'], ctx['original']
    if (arm['schema'] != adapter.SCHEMA or arm['arm_id'] != arm_id or arm['live_guard'] != guard.GUARD
            or ctx['schema'] != mechanical.SCHEMA or ctx['live_guard'] != guard.GUARD or ctx['arm_id'] != arm_id
            or evidence['event']['live_guard'] != guard.GUARD or inv != arm['context']['native_inventory']):
        raise ValueError('mechanical evidence identity mismatch')
    mechanical.validate_binding(inv, record)
    if ctx['neutral'] != mechanical.neutral_record(record, inv):
        raise ValueError('recorded MR does not equal independently derived MR')
    if evidence['qualification'] != qualification or record != qualification['original']:
        raise ValueError('actual model/qualification transfer differs from qualified first M0')
    _, ids, neutral_config = v1.configuration_phases(arm)
    if evidence['event']['selected_actuator_ids'] != ids:
        raise ValueError('scientific and mechanical selected actuator IDs disagree')
    for name in mechanical.FIELDS:
        for phase, config in ((record, arm['context']['configuration']), (ctx['neutral'], neutral_config)):
            if not v1.np.array_equal(mechanical.array_values(phase, name), v1.np.asarray(config['arrays'][name], dtype=float)):
                raise ValueError('mechanical model record and guarded configuration disagree: '+name)
    trace = mechanical.audit_trace(arm_id, inv, record, evidence['event'], evidence['samples'])
    for m, s in zip(evidence['samples'], arm['samples']):
        if any(m[k] != s[k] for k in ('time_s', 'ctrl', 'xfrc_applied', 'qfrc_applied')):
            raise ValueError('mechanical and scientific samples describe different states')
    return trace


def evaluate(report, folder, *, loader=read_arm, display_loader=read_display,
             qualification_loader=read_qualification, reference_comparator=driver.compare_reference):
    checks, audits, mechanics, proofs, pids, display, comparisons = {}, {}, {}, {}, [], {}, {}
    try:
        spec = specification()
        checks.update(schema=report['schema'] == SCHEMA, campaign=report['campaign'] == CAMPAIGN,
            specification=report['specification'] == spec, complete=report['run_status'] == 'COMPLETE',
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
            audits[arm_id] = v1.audit_scientific(arm, arm_id)
            mechanics[arm_id] = audit_mechanical(arm, arm_id, qualification)
            proofs[arm_id] = v1.proof(arm)
            proofs[arm_id].update(full_boundary_prefix=[base.context.digest(s) for s in arm['samples'][:v1.FIRST_AFFECTED]],
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
        exposure = v1.compare_all(proofs)
        checks['cross_arm_prefix_rng_integrity'] = True
        scientific = dict(accepted=True, status='INTEGRITY_ACCEPTED', checks=checks, arms=audits,
            mechanical=mechanics, qualification=qualified, pair_exposure=exposure,
            same_policy_mechanical_prefix_diagnostic=v1.same_policy_mechanical_prefix(proofs),
            behavior=v1.behavior({a: p['pose'] for a, p in proofs.items()}, audits, spec['scientific']),
            unity_replay_eligible=True, unity_replay_entry_point='NOT_IMPLEMENTED_FOR_THIS_SCHEMA')
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
        print('ASSISTANCE CAMPAIGN V1.1 SOURCE CHECK VERIFIED; corrected live-data guard; executed V1 '
              'sources and failed run-desktop-01 locked; native qualification and physics/CNS not run by this check.')
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
