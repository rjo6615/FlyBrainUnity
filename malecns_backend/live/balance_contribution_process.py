"""Balance V1.1: one fresh process per fixed arm; unchanged V1 science/auditors."""
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

from . import balance_contribution as base

ROOT = base.ROOT
SCHEMA = 'balance-contribution-process-v1.1'
SPEC = 'docs/evidence/balance-contribution-process-v1_1/protocol.json'
DOCUMENT = 'docs/BALANCE_CONTRIBUTION_PROCESS_V1_1.md'
MODULE = 'malecns_backend/live/balance_contribution_process.py'
RNG_FIELDS = ('rng_state', 'uniforms_sha256', 'rng_indices', 'draws', 'proprio_rng_state')
PRE_GATE_FIELDS = ('pre_state_sha256', 'post_state_sha256', 'previous', 'raw', 'offered',
                   'eligible', 'delivered', 'fired', 'encoder_state')


def protocol():
    return json.loads((ROOT / SPEC).read_text(encoding='utf-8'))


def sources():
    return dict(base.source_hashes(), **{p: hashlib.sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                       for p in (SPEC, DOCUMENT, MODULE)})


def validate_protocol():
    p = protocol()
    if (p['schema'] != SCHEMA or p['conditions'] != list(base.CONDITIONS)
            or p['process_per_arm'] is not True or p['automatic_retries'] != 0
            or p['reuse_previous_control'] is not False
            or p['scientific_parameters_changed'] is not False
            or p['native_execution_in_this_specification'] is not False
            or (p['physics_transitions_per_arm'], p['neural_updates_per_arm']) != (20000, 4000)
            or p['original_design_raw_sha256'] != hashlib.sha256((ROOT / base.DESIGN).read_bytes()).hexdigest()
            or p['previous_attempt_report_sha256'] != hashlib.sha256((ROOT / p['previous_attempt_report']).read_bytes()).hexdigest()):
        raise ValueError('prospective process-boundary protocol changed')
    base.validate_design()
    return p


def committed():
    head = base.implementation_committed()
    for path in (MODULE, SPEC, DOCUMENT):
        if base.git('show', 'HEAD:' + path).replace(b'\r\n', b'\n') != (ROOT / path).read_bytes().replace(b'\r\n', b'\n'):
            raise ValueError('commit process implementation/protocol before execution: ' + path)
    return head


def fresh_registry(flygym):
    observed = dict(existing_names=sorted(map(str, flygym.Fly._existing_fly_names)),
                    default_name=int(flygym.Fly._default_fly_name))
    if observed != dict(existing_names=[], default_name=0):
        raise ValueError('worker did not start with fresh FlyGym process state')
    return observed


def process_boundary(folder):
    """Measure the real OS chain, including Windows' venv redirector process."""
    import psutil
    path = Path(folder) / 'launch.json'
    deadline = time.monotonic() + 30.
    # The parent publishes this atomically immediately after Popen returns.
    while not path.exists():
        if (Path(folder).parent / 'STOP.json').exists():
            raise KeyboardInterrupt('stopped before launch receipt')
        if time.monotonic() > deadline:
            raise RuntimeError('controller launch receipt missing before initialization')
        time.sleep(.05)
    launch = json.loads(path.read_text(encoding='utf-8'))
    pid, parent = os.getpid(), os.getppid()
    if pid == launch['launch_pid'] and parent == launch['controller_pid']:
        mode, launcher_parent = 'direct', parent
    elif os.name == 'nt' and parent == launch['launch_pid']:
        launcher_parent = psutil.Process(parent).ppid()
        if launcher_parent != launch['controller_pid']:
            raise ValueError('venv redirector does not belong to controller')
        mode = 'windows_venv_redirector'
    else:
        raise ValueError('worker OS ancestry does not match launched process')
    return dict(pid=pid, parent_pid=parent, launch_pid=launch['launch_pid'],
                controller_pid=launch['controller_pid'], launcher_parent_pid=launcher_parent, mode=mode)


def valid_boundary(boundary, controller_pid):
    if boundary['controller_pid'] != controller_pid or boundary['pid'] == controller_pid:
        return False
    if boundary['mode'] == 'direct':
        return boundary['pid'] == boundary['launch_pid'] and boundary['parent_pid'] == controller_pid
    if boundary['mode'] == 'windows_venv_redirector':
        return (boundary['pid'] != boundary['launch_pid'] and boundary['parent_pid'] == boundary['launch_pid']
                and boundary['launcher_parent_pid'] == controller_pid)
    return False


class StopAwareSession:
    """Only a stop-request boundary; delegates every scientific operation."""
    def __init__(self, session, stop_path):
        self.session, self.stop_path = session, Path(stop_path)

    def _check(self):
        if self.stop_path.exists():
            raise KeyboardInterrupt('controller stop request; preserve partial arm')

    def initialize(self):
        self._check()
        return self.session.initialize()

    def step(self, **kwargs):
        self._check()
        return self.session.step(**kwargs)

    def close(self):
        return self.session.close()


def worker(request_path):
    """Internal worker: no reset/normalization of the FlyGym registry or names."""
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text(encoding='utf-8'))
    folder = request_path.parent
    condition = request['condition']
    if condition not in base.CONDITIONS or request_path.name != condition + '.request.json':
        raise ValueError('invalid fixed worker request')
    parent = json.loads((folder / 'controller.json').read_text(encoding='utf-8'))
    if (parent['schema'] != SCHEMA or parent['protocol'] != validate_protocol()
            or parent['commit'] != committed() or parent['sources'] != sources()
            or request['controller_sha256'] != hashlib.sha256((folder / 'controller.json').read_bytes()).hexdigest()):
        raise ValueError('worker source/protocol/commit does not match committed controller')
    base.save(folder / f'{condition}.claim.json', dict(pid=os.getpid(), condition=condition))
    result = dict(condition=condition, run_status='ERROR', samples=[], neural=[])
    before = sources()
    try:
        boundary = process_boundary(folder / condition)
        if not base.environment()['verified']:
            raise ValueError('worker environment changed')
        physical_protocol, table = base.static_authority()
        base.data_identities()
        import flygym
        registry = fresh_registry(flygym)
        original_factory = base.create_session
        def factory(trial, p, t):
            return StopAwareSession(original_factory(trial, p, t), folder / 'STOP.json')
        base.create_session = factory
        try:
            result = base.run_arm(condition, physical_protocol, table)
        finally:
            base.create_session = original_factory
        result['process_boundary'] = dict(boundary, fresh_registry=registry, commit=parent['commit'])
    except (Exception, KeyboardInterrupt) as exc:
        result.update(run_status='ERROR', worker_error=f'{type(exc).__name__}: {exc}')
    result.update(worker_sources_before=before, worker_sources_after=sources())
    artifact = base.save(folder / f'{condition}.json.gz', result)
    base.save(folder / f'{condition}.done.json', dict(condition=condition, run_status=result['run_status'],
        pid=os.getpid(), process_boundary=result.get('process_boundary'), states=len(result['samples']),
        neural_updates=len(result['neural']), artifact=artifact))
    return 0 if result['run_status'] == 'COMPLETE' else 1


def run_child(folder, condition, controller_sha256):
    folder = Path(folder)
    if condition not in base.CONDITIONS:
        raise ValueError('unknown fixed arm')
    request = folder / f'{condition}.request.json'
    base.save(request, dict(condition=condition, controller_sha256=controller_sha256))
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    command = [sys.executable, '-u', '-m', 'malecns_backend.live.balance_contribution_process',
               '--worker-request', str(request.resolve())]
    interrupted = False
    log_path = folder / f'{condition}.log.txt'
    launch_dir = folder / condition
    launch_dir.mkdir(exist_ok=False)
    with log_path.open('xb') as log:
        isolation = ({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
                     if os.name == 'nt' else {'start_new_session': True})
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, **isolation)
        temporary = launch_dir / 'launch.tmp.json'
        base.save(temporary, dict(launch_pid=process.pid, controller_pid=os.getpid()))
        temporary.replace(launch_dir / 'launch.json')
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
                time.sleep(1.)
            except KeyboardInterrupt:
                interrupted = True
                stop = folder / 'STOP.json'
                if not stop.exists():
                    base.save(stop, dict(reason='user/controller interruption', condition=condition))
                print('Stop requested; waiting for the worker to preserve partial data.', flush=True)
    done = folder / f'{condition}.done.json'
    if not done.exists():
        raise RuntimeError(f'{condition} worker exited {code} without a complete raw-file receipt; see {log_path.name}')
    receipt = json.loads(done.read_text(encoding='utf-8'))
    boundary = receipt.get('process_boundary')
    if (receipt['condition'] != condition or receipt['run_status'] == 'COMPLETE' and boundary is None
            or boundary is not None and (
            boundary['launch_pid'] != process.pid or not valid_boundary(boundary, os.getpid())
            or boundary['pid'] != receipt['pid'])):
        raise ValueError('worker receipt identity mismatch')
    if code != 0 and receipt['run_status'] == 'COMPLETE':
        raise ValueError('worker exit/receipt disagreement')
    return receipt, interrupted


def read_arm(folder, condition, artifact):
    if condition not in base.CONDITIONS or artifact['path'] != f'{condition}.json.gz':
        raise ValueError('invalid fixed arm artifact identity')
    raw = (Path(folder) / artifact['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != artifact['sha256']:
        raise ValueError('raw arm SHA256 mismatch')
    return json.loads(gzip.decompress(raw))


def proof(arm):
    """Compact comparison material only; the unchanged auditor sees the FULL arm.

    Sorted strict JSON hashes keep every field of each original prefix record.
    No instance-name field is removed. Raw gzip data is never downsampled.
    """
    samples, neural = arm['samples'], arm['neural']
    digest = base.context.digest
    return dict(initial=arm['initial'], context=arm['context'],
        physical_prefix=[digest(s) for s in samples[:5001]],
        same_push_prefix=[digest({k: v for k, v in s.items() if k != 'proposed_commands'}) for s in samples[:5006]],
        neural_prefix=[digest(n) for n in neural[:1000]],
        pre_gate=digest({k: neural[1000][k] for k in PRE_GATE_FIELDS}),
        rng=[digest({k: n[k] for k in RNG_FIELDS}) for n in neural],
        actions=[digest(s['commanded_joints']) for s in samples],
        physics=[digest(dict(qpos=s['qpos'], qvel=s['qvel'])) for s in samples],
        pose=dict(samples=[dict(qpos=s['qpos'], qvel=s['qvel']) for s in samples]))


def compare_proofs(proofs):
    ref = proofs['NC']
    for c in base.CONDITIONS:
        p = proofs[c]
        for field in ('initial', 'context', 'physical_prefix', 'neural_prefix', 'rng'):
            if p[field] != ref[field]:
                raise ValueError('full original all-arm check failed: ' + c + '/' + field)
    exposure = {}
    for n, w in (('NC', 'WC'), ('NP', 'WP')):
        a, b = proofs[n], proofs[w]
        if a['same_push_prefix'] != b['same_push_prefix'] or a['pre_gate'] != b['pre_gate']:
            raise ValueError('original same-push pre-gate prefix mismatch')
        action = next((i - 1 for i, (x, y) in enumerate(zip(a['actions'], b['actions'])) if i and x != y), None)
        physical = next((i for i, (x, y) in enumerate(zip(a['physics'], b['physics'])) if x != y), None)
        exposure[n + '_vs_' + w] = dict(first_actual_outgoing_command_difference=action,
            first_physical_difference_state=physical, first_actual_command_effect_state=None if action is None else action + 1)
    return exposure


def evaluate(report, folder, loader=read_arm):
    checks, audits, proofs, pids = {}, {}, {}, []
    try:
        checks.update(fixed_schema=report['schema'] == SCHEMA, fixed_protocol=report['protocol'] == validate_protocol(),
            completed_controller=report.get('run_status') == 'COMPLETE',
            fixed_original_design=report['design'] == base.design(), prerequisites=report['preflight']['verified'] is True,
            unchanged_sources=bool(report['sources_before']) and report['sources_before'] == report['sources_after'] == sources(),
            four_fresh_arms_order=list(report['arm_artifacts']) == list(base.CONDITIONS))
        if not all(checks.values()):
            raise ValueError('incomplete or changed fixed process assay')
        for c in base.CONDITIONS:
            arm = loader(folder, c, report['arm_artifacts'][c])
            if (arm['condition'] != c or arm['worker_sources_before'] != report['sources_before']
                    or arm['worker_sources_after'] != report['sources_after']):
                raise ValueError('worker identity/source disagreement')
            boundary = arm['process_boundary']
            if (boundary['fresh_registry'] != dict(existing_names=[], default_name=0)
                    or boundary['commit'] != report['implementation_commit']
                    or not valid_boundary(boundary, report['controller_pid'])):
                raise ValueError('fresh worker process proof missing')
            pids.append(boundary['pid'])
            audits[c] = base.audit_arm(arm)
            proofs[c] = proof(arm)
            del arm
            gc.collect()
        if len(set(pids)) != 4:
            raise ValueError('distinct worker process identities required')
        checks['per_arm_original_integrity'] = True
        exposure = compare_proofs(proofs)
        checks['original_prefix_and_rng_checks'] = True
        return dict(accepted=True, status='INTEGRITY_ACCEPTED', checks=checks, arms=audits,
            behavior=base.behavior({c: p['pose'] for c, p in proofs.items()}, audits),
            pair_exposure=exposure, unity_replay_eligible=True)
    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
        return dict(accepted=False, status='INCONCLUSIVE_INTEGRITY', checks=checks, arms=audits,
                    reason=f'{type(exc).__name__}: {exc}', behavior=None, unity_replay_eligible=False)


def execute(folder, *, live=False):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    report = dict(schema=SCHEMA, protocol=validate_protocol(), design=base.design(), controller_pid=os.getpid(),
        sources_before=sources(), run_status='NOT_RUN', scientific_experiment_started=False, arm_artifacts={})
    report['preflight'] = base.preflight()
    base.save(folder / 'preflight.json', report['preflight'])
    if live and report['preflight']['verified']:
        try:
            report['implementation_commit'] = committed()
            control = dict(schema=SCHEMA, protocol=protocol(), sources=report['sources_before'], commit=report['implementation_commit'])
            controller = base.save(folder / 'controller.json', control)
            report['scientific_experiment_started'] = True
            completed = []
            for c in base.CONDITIONS:
                receipt, interrupted = run_child(folder, c, controller['sha256'])
                report['arm_artifacts'][c] = receipt['artifact']
                completed.append(receipt['run_status'] == 'COMPLETE')
                base.save(folder / f'{c}.controller-receipt.json', receipt)
                if receipt['run_status'] != 'COMPLETE' or interrupted:
                    break
            report['run_status'] = 'COMPLETE' if len(completed) == 4 and all(completed) and not (folder / 'STOP.json').exists() else 'INCOMPLETE'
        except (Exception, KeyboardInterrupt) as exc:
            report.update(run_status='ERROR', error=f'{type(exc).__name__}: {exc}')
    elif live:
        report['run_status'] = 'BLOCKED_PREREQUISITES'
    report['sources_after'] = sources()
    report['evaluation'] = evaluate(report, folder)
    base.save(folder / 'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--evaluate', type=Path)
    group.add_argument('--worker-request', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args(argv)
    if args.worker_request:
        if args.live:
            parser.error('worker cannot request a new live assay')
        return worker(args.worker_request)
    if args.evaluate:
        if args.live:
            parser.error('evaluation cannot execute a live assay')
        report = json.loads((args.evaluate / 'report.json').read_text(encoding='utf-8'))
        result = evaluate(report, args.evaluate)
        print(json.dumps(result, allow_nan=False))
        return 0 if result['accepted'] else 1
    report = execute(args.output, live=args.live)
    print(json.dumps(dict(status=report['run_status'], preflight=report['preflight'], evaluation=report['evaluation']), allow_nan=False))
    return 0 if report['preflight']['verified'] and (not args.live or report['evaluation']['accepted']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
