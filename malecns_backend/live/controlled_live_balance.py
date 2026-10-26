"""Versioned live observation of the fixed assisted balance-contribution assay.

Default --output performs construction-free prerequisite checks only. --live
requires committed implementation and a user's prior full-body review note.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from . import balance_contribution_process as original
from .balance_live_observer import LiveObserver, audit_display

base = original.base
ROOT = base.ROOT
SCHEMA = 'controlled-live-balance-execution-v1'
SPEC = 'docs/evidence/controlled-live-balance-v1/protocol.json'
DESIGN_SHA256 = 'e686441582f660bdd6dd0828bb8477a0ebbf72e709d681b7f5a0c886a03ef2a4'
MODULE = 'malecns_backend/live/controlled_live_balance.py'
OWN_SOURCES = (MODULE, 'malecns_backend/live/balance_live_observer.py', SPEC,
    'docs/CONTROLLED_LIVE_BALANCE_V1.md', 'docs/CONTROLLED_LIVE_BALANCE_IMPLEMENTATION_V1.md',
    'malecns_backend/live/tactile_replay.py', 'malecns_backend/live/server.py',
    'malecns_backend/live/protocol.py')
REFERENCE = 'docs/evidence/balance-contribution-process-v1_1/run-desktop-01/report.json'


def specification():
    raw = (ROOT/SPEC).read_bytes()
    if hashlib.sha256(raw).hexdigest() != DESIGN_SHA256:
        raise ValueError('original controlled-live prospective design changed')
    p = json.loads(raw)
    for path, lock in p['inherited_reference_locks'].items():
        current = (ROOT/path).read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(current).hexdigest() != lock['canonical_lf_sha256']:
            raise ValueError('inherited reference source changed: ' + path)
    original.validate_protocol()
    return p


def sources():
    return dict(original.sources(), **{p: hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                      for p in OWN_SOURCES})


def committed():
    head = original.committed()
    for path in sources():
        if base.git('show', 'HEAD:' + path).replace(b'\r\n', b'\n') != (ROOT/path).read_bytes().replace(b'\r\n', b'\n'):
            raise ValueError('commit live implementation and all sources before execution: ' + path)
    return head


def run_arm(condition, physical_protocol, table, stop_path, *,
            trial_factory=None, session_factory=None, observer_factory=LiveObserver,
            progress=print, clock=time.monotonic):
    """Lifecycle only; every scientific step/record/audit is an existing API.

    Explicit dependency injection avoids monkeypatching the frozen module's
    factories. State boundaries stay in the original run_arm order, including
    terminal tick4000. Tests can inject synthetic sessions, never CLI fixtures.
    """
    if condition not in base.CONDITIONS:
        raise ValueError('unknown fixed arm')
    trial = (trial_factory or base.Trial)(condition)
    result = dict(condition=condition, run_status='ERROR', samples=trial.samples, neural=trial.neural)
    session, observer, display = None, None, None
    operations = Counter()
    stop_path = Path(stop_path)
    def stop():
        if stop_path.exists():
            raise KeyboardInterrupt('stop requested; preserve partial arm')
    try:
        stop()
        progress(f'LIVE_PROVISIONAL_NOT_YET_AUDITED {condition}: binding output-only display before initialization', flush=True)
        observer = observer_factory()
        observer.start()
        progress(f'{condition}: LIVE_PROVISIONAL display_session={observer.record["session_id"]}', flush=True)
        stop()
        session = (session_factory or base.create_session)(trial, physical_protocol, table)
        progress(f'{condition}: fresh native/CNS initialization; position assistance unchanged', flush=True)
        stop()
        with base.initialization_operations() as operations:
            initial = session.initialize()
        if initial.time_ms != 0:
            raise ValueError('nonzero initial scientific clock')
        trial.state_boundary()
        observer.observe(trial.context, trial.samples[-1], 0)
        last = clock()
        for index in range(1, base.STEPS + 1):
            stop()
            state = session.step(lightweight=True)
            if state.physics_transitions != index or state.neural_transitions != index//base.STRIDE:
                raise ValueError('authoritative scientific counters mismatch')
            trial.state_boundary()
            observer.observe(trial.context, trial.samples[-1], index)
            if clock() - last >= 15:
                progress(f'{condition}: sim={index*.0001:.4f}s physics={index}/20000 neural={index//5}/4000', flush=True)
                last = clock()
        result['run_status'] = 'COMPLETE'
    except (Exception, KeyboardInterrupt) as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        if trial.brain is not None:
            result['neural_failure_snapshot'] = {k: base.native(getattr(trial.brain, k)) for k in (
                'v', 'g_exc', 'g_inh', 'refractory', 'spike_counts', 'external_drive', 'time_ms')}
    finally:
        if session is not None:
            try:
                session.close()
            except Exception as exc:
                result.update(run_status='ERROR', close_error=f'{type(exc).__name__}: {exc}')
        try:
            trial.detach()
        except Exception as exc:
            result.update(run_status='ERROR', detach_error=f'{type(exc).__name__}: {exc}')
        if observer is not None:
            display = observer.close()
        result.update(context=trial.context, initial=trial.initial, initialization_operations=dict(operations),
            initialization_accounting_scope='observed Python/C API entries; native internal calls unobservable')
    return result, display


def worker(request_path):
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text(encoding='utf-8'))
    folder, condition = request_path.parent, request['condition']
    if condition not in base.CONDITIONS or request_path.name != condition + '.request.json':
        raise ValueError('invalid fixed live worker request')
    control_path = folder/'controller.json'
    control = json.loads(control_path.read_text(encoding='utf-8'))
    if (control['schema'] != SCHEMA or control['specification'] != specification()
            or control['commit'] != committed() or control['sources'] != sources()
            or not isinstance(control['prior_full_body_review_note'], str)
            or not control['prior_full_body_review_note'].strip()
            or request['controller_sha256'] != hashlib.sha256(control_path.read_bytes()).hexdigest()):
        raise ValueError('worker committed source/design/controller mismatch')
    base.save(folder/f'{condition}.claim.json', dict(condition=condition, pid=os.getpid()))
    before = sources()
    arm, display = dict(condition=condition, run_status='ERROR', samples=[], neural=[]), None
    try:
        boundary = original.process_boundary(folder/condition)
        if (folder/'STOP.json').exists():
            raise KeyboardInterrupt('stopped before native initialization')
        if not base.environment()['verified']:
            raise ValueError('original environment requirements failed')
        physical_protocol, table = base.static_authority()
        base.data_identities()
        import flygym
        registry = original.fresh_registry(flygym)
        arm, display = run_arm(condition, physical_protocol, table, folder/'STOP.json')
        arm['process_boundary'] = dict(boundary, fresh_registry=registry, commit=control['commit'])
    except (Exception, KeyboardInterrupt) as exc:
        arm.update(run_status='ERROR', worker_error=f'{type(exc).__name__}: {exc}')
    arm.update(worker_sources_before=before, worker_sources_after=sources())
    artifact = base.save(folder/f'{condition}.json.gz', arm)
    display_artifact = base.save(folder/f'{condition}.display.json.gz', display)
    base.save(folder/f'{condition}.done.json', dict(condition=condition, pid=os.getpid(),
        run_status=arm['run_status'], process_boundary=arm.get('process_boundary'),
        states=len(arm['samples']), neural_updates=len(arm['neural']), artifact=artifact,
        display_artifact=display_artifact))
    return 0 if arm['run_status'] == 'COMPLETE' else 1


def run_child(folder, condition, controller_sha256):
    """A single fresh OS launch; no retry, registry reset or scientific options."""
    folder = Path(folder)
    if condition not in base.CONDITIONS:
        raise ValueError('unknown fixed arm')
    request = folder/f'{condition}.request.json'
    base.save(request, dict(condition=condition, controller_sha256=controller_sha256))
    launch_dir = folder/condition
    launch_dir.mkdir(exist_ok=False)
    command = [sys.executable, '-u', '-m', 'malecns_backend.live.controlled_live_balance',
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


def read_display(folder, condition, artifact):
    if condition not in base.CONDITIONS or artifact['path'] != condition + '.display.json.gz':
        raise ValueError('invalid display artifact path')
    raw = (Path(folder)/artifact['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != artifact['sha256']:
        raise ValueError('display raw SHA256 mismatch')
    return json.loads(gzip.decompress(raw))


def compare_reference(arm, report, condition):
    """Read-only diagnostic. Missing/corrupt old files never authorize a retry."""
    try:
        p = specification()
        raw = (ROOT/REFERENCE).read_bytes()
        if hashlib.sha256(raw).hexdigest() != p['inherited_reference_locks'][REFERENCE]['sha256']:
            raise ValueError('accepted reference report identity mismatch')
        prior = json.loads(raw)
        old = original.read_arm(ROOT/Path(REFERENCE).parent, condition, prior['arm_artifacts'][condition])
        differences = dict(environment=report['preflight']['environment'] != prior['preflight']['environment'],
            scientific_sources={k:v for k,v in report['sources_before'].items() if k in original.sources()} != prior['sources_before'])
        for field in ('initial', 'context', 'samples', 'neural', 'initialization_operations'):
            a, b = arm[field], old[field]
            if base.context.digest(a) != base.context.digest(b):
                index = next((i for i,(x,y) in enumerate(zip(a,b)) if base.context.digest(x) != base.context.digest(y)), None) if isinstance(a,list) else None
                return dict(status='EXACT_MISMATCH', field=field, first_index=index,
                    lengths=[len(a),len(b)] if isinstance(a,list) else None, differences=differences)
        return dict(status='EXACT_MATCH', differences=differences)
    except (OSError, KeyError, TypeError, ValueError, gzip.BadGzipFile) as exc:
        return dict(status='UNAVAILABLE_OR_INVALID_REFERENCE', reason=f'{type(exc).__name__}: {exc}')


def evaluate(report, folder, *, loader=original.read_arm, display_loader=read_display,
             reference_comparator=compare_reference):
    checks, audits, proofs, pids, display, comparisons = {}, {}, {}, [], {}, {}
    try:
        checks.update(schema=report['schema'] == SCHEMA, specification=report['specification'] == specification(),
            complete=report['run_status'] == 'COMPLETE', original_design=report['design'] == base.design(),
            prerequisites=report['preflight']['verified'] is True,
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
    report['preflight'] = base.preflight()
    base.save(folder/'preflight.json', report['preflight'])
    if live:
        try:
            if not review_note.strip():
                raise ValueError('prior full-body human review note is required before native execution')
            if not report['preflight']['verified']:
                raise ValueError('original scientific prerequisites failed')
            report['implementation_commit'] = committed()
            control = dict(schema=SCHEMA, specification=specification(), sources=report['sources_before'],
                commit=report['implementation_commit'], prior_full_body_review_note=review_note)
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
