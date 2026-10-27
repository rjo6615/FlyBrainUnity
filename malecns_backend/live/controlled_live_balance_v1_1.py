"""V1.1: require complete original loader source checks around each fresh arm.

Default --output is construction-free. Science and observation delegate to the
immutable executed V1 driver; this version changes prerequisite/report lifecycle.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from . import controlled_live_balance as prior
from . import balance_source_prerequisites as source_guard

base, original, ROOT = prior.base, prior.original, prior.ROOT
SCHEMA = 'controlled-live-balance-execution-v1.1'
SPEC = 'docs/evidence/controlled-live-balance-v1_1/protocol.json'
SPEC_SHA256 = '6dda8ee126e44af1c3dc174d34f17a616c5193e8a3b625ab919ab873c0fef44f'
MODULE = 'malecns_backend/live/controlled_live_balance_v1_1.py'
OWN_SOURCES = (MODULE, SPEC, 'docs/CONTROLLED_LIVE_BALANCE_V1_1.md',
               'malecns_backend/live/balance_source_prerequisites.py')
run_arm = prior.run_arm
read_display = prior.read_display
audit_display = prior.audit_display
compare_reference = prior.compare_reference


def specification():
    raw = (ROOT/SPEC).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SPEC_SHA256:
        raise ValueError('prospective V1.1 protocol identity changed')
    p = json.loads(raw)
    prior.specification()
    if hashlib.sha256((ROOT/p['failed_v1_report']).read_bytes()).hexdigest() != p['failed_v1_report_sha256']:
        raise ValueError('retained failed V1 report changed')
    if prior.sources() != p['executed_v1_sources']:
        raise ValueError('executed V1 sources changed; preserve historical identity')
    if hashlib.sha256((ROOT/p['source_checker']).read_bytes().replace(b'\r\n',b'\n')).hexdigest() != p['source_checker_canonical_sha256']:
        raise ValueError('original complete source checker changed')
    return p


def sources():
    return dict(prior.sources(), **{p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                                   for p in OWN_SOURCES})


def committed():
    head = prior.committed()
    for path in OWN_SOURCES:
        if base.git('show','HEAD:'+path).replace(b'\r\n',b'\n') != (ROOT/path).read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('commit V1.1 implementation/checker/specification before execution: '+path)
    return head


def preflight():
    checked = source_guard.check()
    return dict(checked['original_preflight'], orientation_source=checked['orientation_source'],
                complete_source_schema=checked['schema'], verified=checked['verified'])


def verified_preflight(record):
    """Verify full recorded evidence, never a lone verified=True assertion."""
    try:
        expected = specification()['source_graph_authority']
        graph = record['orientation_source']
        environment = base.design()['expected_environment']
        return (record['verified'] is True and not record['errors']
            and record['complete_source_schema'] == 'balance-loader-source-prerequisites-v1'
            and all(record['checks'][k] is True for k in ('design','original_authorities','original_neural_data'))
            and all(record[k] == 0 for k in ('scientific_transitions','native_constructions','cns_initializations'))
            and record['environment']['verified'] is True
            and environment['dependency_changes_allowed'] is False
            and record['environment']['observed'] == {k:value for k,value in environment.items()
                                                     if k != 'dependency_changes_allowed'}
            and not record['environment']['mismatches'] and graph['verified'] is True
            and graph['expected'] == expected and graph['path'] == source_guard.GRAPH
            and graph['observed'] == {k:expected[k] for k in ('sha256','bytes')})
    except (KeyError, TypeError, ValueError):
        return False


def worker(request_path):
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text(encoding='utf-8'))
    folder, condition = request_path.parent, request['condition']
    if condition not in base.CONDITIONS or request_path.name != condition+'.request.json':
        raise ValueError('invalid fixed V1.1 worker request')
    control_path = folder/'controller.json'
    control = json.loads(control_path.read_text(encoding='utf-8'))
    if (control['schema'] != SCHEMA or control['specification'] != specification()
            or control['commit'] != committed() or control['sources'] != sources()
            or not isinstance(control['prior_full_body_review_note'],str)
            or not control['prior_full_body_review_note'].strip()
            or not verified_preflight(control['complete_preflight'])
            or request['controller_sha256'] != hashlib.sha256(control_path.read_bytes()).hexdigest()):
        raise ValueError('V1.1 worker source/commit/controller/prerequisite mismatch')
    base.save(folder/f'{condition}.claim.json',dict(condition=condition,pid=os.getpid()))
    before = sources()
    arm, display = dict(condition=condition,run_status='ERROR',samples=[],neural=[]), None
    try:
        boundary = original.process_boundary(folder/condition)
        if (folder/'STOP.json').exists():
            raise KeyboardInterrupt('stopped before complete prerequisite check')
        checked = preflight()
        arm['complete_preflight_before'] = checked
        if not verified_preflight(checked) or checked != control['complete_preflight']:
            raise ValueError('worker complete original source prerequisites failed before initialization')
        physical_protocol, table = base.static_authority()
        import flygym
        registry = original.fresh_registry(flygym)
        arm, display = run_arm(condition,physical_protocol,table,folder/'STOP.json')
        arm['complete_preflight_before'] = checked
        arm['process_boundary'] = dict(boundary,fresh_registry=registry,commit=control['commit'])
        arm['complete_preflight_after'] = preflight()
        if not verified_preflight(arm['complete_preflight_after']) or arm['complete_preflight_after'] != checked:
            raise ValueError('worker original source prerequisites changed after acquisition')
    except (Exception, KeyboardInterrupt) as exc:
        arm.update(run_status='ERROR',worker_error=f'{type(exc).__name__}: {exc}')
    arm.update(worker_sources_before=before,worker_sources_after=sources())
    artifact = base.save(folder/f'{condition}.json.gz',arm)
    display_artifact = base.save(folder/f'{condition}.display.json.gz',display)
    base.save(folder/f'{condition}.done.json',dict(condition=condition,pid=os.getpid(),
        run_status=arm['run_status'],process_boundary=arm.get('process_boundary'),
        states=len(arm['samples']),neural_updates=len(arm['neural']),artifact=artifact,display_artifact=display_artifact))
    return 0 if arm['run_status']=='COMPLETE' else 1


def run_child(folder, condition, controller_sha256):
    """A single fresh OS launch; no retry, registry reset or scientific options."""
    folder = Path(folder)
    if condition not in base.CONDITIONS:
        raise ValueError('unknown fixed arm')
    request = folder/f'{condition}.request.json'
    base.save(request, dict(condition=condition, controller_sha256=controller_sha256))
    launch_dir = folder/condition
    launch_dir.mkdir(exist_ok=False)
    command = [sys.executable, '-u', '-m', 'malecns_backend.live.controlled_live_balance_v1_1',
               '--worker-request', str(request.resolve())]
    isolation = ({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
                 if os.name == 'nt' else {'start_new_session': True})
    log_path, interrupted = folder/f'{condition}.log.txt', False
    with log_path.open('xb') as log:
        process = subprocess.Popen(command, cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING='utf-8',
            PYTHONUNBUFFERED='1'), stdout=log, stderr=subprocess.STDOUT, **isolation)
        base.save(launch_dir/'launch.tmp.json', dict(launch_pid=process.pid, controller_pid=os.getpid()))
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
                    base.save(folder/'STOP.json', dict(reason='user stop', condition=condition))
                print('Stop requested; waiting for partial evidence preservation.', flush=True)
    path = folder/f'{condition}.done.json'
    if not path.exists():
        raise RuntimeError(f'{condition} worker exited {code} without raw-file receipt; no retry')
    receipt = json.loads(path.read_text(encoding='utf-8'))
    boundary = receipt.get('process_boundary')
    if (receipt['condition'] != condition or receipt['run_status'] == 'COMPLETE' and (code != 0 or boundary is None)
            or boundary is not None and (boundary['launch_pid'] != process.pid
                or not original.valid_boundary(boundary, os.getpid()) or boundary['pid'] != receipt['pid'])):
        raise ValueError('live worker receipt/exit/ancestry mismatch')
    return receipt, interrupted


def evaluate(report, folder, *, loader=original.read_arm, display_loader=read_display,
             reference_comparator=compare_reference):
    checks, audits, proofs, pids, display, comparisons = {}, {}, {}, [], {}, {}
    try:
        checks.update(schema=report['schema'] == SCHEMA, specification=report['specification'] == specification(),
            complete=report['run_status'] == 'COMPLETE', original_design=report['design'] == base.design(),
            prerequisites=verified_preflight(report['preflight']),
            sources=bool(report['sources_before']) and report['sources_before'] == report['sources_after'] == sources(),
            review_note=isinstance(report['prior_full_body_review_note'], str) and bool(report['prior_full_body_review_note'].strip()),
            fresh_arm_order=list(report['arm_artifacts']) == list(base.CONDITIONS))
        if not all(checks.values()):
            raise ValueError('incomplete or changed controlled-live experiment')
        for c in base.CONDITIONS:
            arm = loader(folder, c, report['arm_artifacts'][c])
            boundary = arm['process_boundary']
            if (arm['condition'] != c or arm['worker_sources_before'] != report['sources_before']
                    or arm['worker_sources_after'] != report['sources_after']
                    or arm.get('complete_preflight_before') != report['preflight']
                    or arm.get('complete_preflight_after') != report['preflight']
                    or boundary['fresh_registry'] != dict(existing_names=[], default_name=0)
                    or boundary['commit'] != report['implementation_commit']
                    or not original.valid_boundary(boundary, report['controller_pid'])):
                raise ValueError('live worker identity/source/freshness mismatch')
            pids.append(boundary['pid'])
            audits[c] = base.audit_arm(arm)
            proofs[c] = original.proof(arm)
            # Display failure never bypasses or changes the original science audit.
            try:
                record = display_loader(folder, c, report['display_artifacts'][c])
                display[c] = audit_display(arm, record)
            except (OSError, KeyError, TypeError, ValueError) as exc:
                display[c] = dict(status='FAILED', reason=f'{type(exc).__name__}: {exc}')
            try:
                comparisons[c] = reference_comparator(arm, report, c)
            except Exception as exc:
                comparisons[c] = dict(status='UNAVAILABLE_OR_INVALID_REFERENCE', reason=f'{type(exc).__name__}: {exc}')
            del arm
            gc.collect()
        if len(set(pids)) != 4:
            raise ValueError('distinct fresh worker PIDs required')
        checks['original_per_arm_integrity'] = True
        exposure = original.compare_proofs(proofs)
        checks['original_cross_arm_prefix_rng_integrity'] = True
        scientific = dict(accepted=True, status='INTEGRITY_ACCEPTED', checks=checks, arms=audits,
            behavior=base.behavior({c:p['pose'] for c,p in proofs.items()}, audits),
            pair_exposure=exposure, unity_replay_eligible=True)
    except (OSError, KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
        scientific = dict(accepted=False, status='INCONCLUSIVE_INTEGRITY', checks=checks, arms=audits,
            behavior=None, unity_replay_eligible=False, reason=f'{type(exc).__name__}: {exc}')
    sessions = [d['session_id'] for d in display.values() if d.get('session_id')]
    if len(set(sessions)) != len(sessions):
        for c in display:
            display[c] = dict(status='FAILED', projection_status='FAILED', reason='display session identity reused across arms')
    return dict(scientific=scientific, display=display, reference_comparison=comparisons,
                visual_review='UNCONFIRMED')


def execute(folder, *, live=False, review_note='', child_runner=run_child):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, specification=specification(), design=base.design(),
        sources_before=sources(), run_status='NOT_RUN', controller_pid=os.getpid(),
        prior_full_body_review_note=review_note, scientific_experiment_started=False,
        arm_artifacts={}, display_artifacts={})
    report['preflight'] = preflight()
    base.save(folder/'preflight.json', report['preflight'])
    if live:
        try:
            if not review_note.strip():
                raise ValueError('prior full-body human review note is required before native execution')
            if not verified_preflight(report['preflight']):
                raise ValueError('original scientific prerequisites failed')
            report['implementation_commit'] = committed()
            control = dict(schema=SCHEMA, specification=specification(), sources=report['sources_before'],
                commit=report['implementation_commit'], prior_full_body_review_note=review_note,
                complete_preflight=report['preflight'])
            artifact = base.save(folder/'controller.json', control)
            report['scientific_experiment_started'] = True
            completed = []
            for c in base.CONDITIONS:
                if (folder/'STOP.json').exists():
                    break
                receipt, interrupted = child_runner(folder, c, artifact['sha256'])
                report['arm_artifacts'][c] = receipt['artifact']
                report['display_artifacts'][c] = receipt['display_artifact']
                base.save(folder/f'{c}.controller-receipt.json', receipt)
                completed.append(receipt['run_status'] == 'COMPLETE')
                if not completed[-1] or interrupted:
                    break
            report['run_status'] = 'COMPLETE' if len(completed) == 4 and all(completed) and not (folder/'STOP.json').exists() else 'INCOMPLETE'
        except (Exception, KeyboardInterrupt) as exc:
            report.update(run_status='ERROR', error=f'{type(exc).__name__}: {exc}')
    report['sources_after'] = sources()
    report['evaluation'] = evaluate(report, folder)
    base.save(folder/'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--evaluate', type=Path)
    group.add_argument('--worker-request', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--review-note', default='')
    args = parser.parse_args(argv)
    if (args.worker_request or args.evaluate) and (args.live or args.review_note):
        parser.error('worker/evaluation cannot request another live execution or alter its review note')
    if args.live and not args.review_note.strip():
        parser.error('--live requires --review-note describing actual prior full-body replay review')
    if args.worker_request:
        return worker(args.worker_request)
    if args.evaluate:
        saved = json.loads((args.evaluate/'report.json').read_text(encoding='utf-8'))
        evaluation = evaluate(saved, args.evaluate)
        print(json.dumps(base.native(evaluation), allow_nan=False))
        return 0 if evaluation['scientific']['accepted'] else 1
    report = execute(args.output, live=args.live, review_note=args.review_note)
    print(json.dumps(base.native(dict(status=report['run_status'], preflight=report['preflight'],
        evaluation=report['evaluation'])), allow_nan=False))
    return 0 if report['preflight']['verified'] and (not args.live or report['evaluation']['scientific']['accepted']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
