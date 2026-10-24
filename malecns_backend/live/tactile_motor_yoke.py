"""Prospective motor-application yoke using the unchanged recovery kernel."""
import argparse
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import numpy as np

from . import tactile_recovery as prior
from .tactile_boundary import native

ROOT=prior.ROOT
CONDITIONS=('Y_C','Y_P')
PROTOCOL=dict(schema='tactile-motor-yoke-v1',conditions=list(CONDITIONS),seed=1,
              steps=20000,neural_steps=4000,command_source='matched-pair ENABLED commanded_joints',
              boundary='every outgoing physical transition; archived sample n+1',
              retries=0,ordinary_live_mode_changed=False)
FILES=('docs/TACTILE_MOTOR_YOKE_V1.md','malecns_backend/live/tactile_motor_yoke.py')


def sources():
    return dict(prior.sources(),**{p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in FILES})


def commands(baseline):
    values=np.asarray([s['commanded_joints'] for s in baseline['samples'][1:]],dtype=float)
    if values.shape!=(prior.STEPS,42) or not np.isfinite(values).all():
        raise ValueError('complete finite archived action schedule required')
    if any(s['adhesion']!=[0.]*6 for s in baseline['samples'][1:]):
        raise ValueError('archived adhesion must be zero')
    return values


class YokeTrial(prior.RecoveryTrial):
    def __init__(self,identity,baseline):
        if identity not in CONDITIONS: raise ValueError('unknown yoke condition')
        super().__init__('ON_P')
        self.identity=identity
        self.withdraw=False
        self.actions=commands(baseline)
        self.original_sim_step=None
        self.proposed=None

    def bind(self,sim,physics,obs):
        super().bind(sim,physics,obs)
        self.sim=sim
        self.original_sim_step=sim.step
        sim.step=self.apply

    def apply(self,action):
        index=len(self.samples)-1
        proposed=np.asarray(action['joints'],dtype=float)
        if not 0<=index<len(self.actions) or proposed.shape!=(42,) or not np.isfinite(proposed).all():
            raise ValueError('invalid proposed action or transition')
        if set(action)!={'joints','adhesion'} or not np.array_equal(action['adhesion'],np.zeros(6)):
            raise ValueError('unexpected action fields or adhesion')
        self.proposed=proposed.copy().tolist()
        return self.original_sim_step(dict(joints=self.actions[index].copy(),adhesion=np.zeros(6)))

    def capture(self,physics,obs,action):
        # ObservedSimulation passes the proposed action. Record actual application.
        applied=None if action is None else dict(joints=self.actions[len(self.samples)-1],adhesion=np.zeros(6))
        super().capture(physics,obs,applied)
        self.samples[-1]['proposed_joints']=self.proposed

    def detach(self):
        if self.original_sim_step is not None:
            self.sim.step=self.original_sim_step
        super().detach()


def run_arm(identity,baseline,progress):
    trial=YokeTrial(identity,baseline)
    result=dict(schema='motor-yoke-arm-v1',identity=identity,protocol=prior.PROTOCOL,
                yoke_protocol=PROTOCOL,run_status='ERROR',samples=trial.samples,neural=trial.neural,
                sources_before=sources())
    session=None
    try:
        session=prior.create_session(trial)
        progress(f'{identity}: initializing fresh CNS; baseline motor actions will be replayed.')
        state=session.initialize()
        if state.time_ms!=0.: raise RuntimeError('nonzero reset')
        last=time.monotonic()
        for step in range(1,prior.STEPS+1):
            state=session.step(lightweight=True)
            if state.physics_transitions!=step or state.neural_transitions!=step//5:
                raise RuntimeError('transition count mismatch')
            if time.monotonic()-last>=15:
                progress(f'{identity}: {step}/{prior.STEPS} physics transitions.')
                last=time.monotonic()
        result['run_status']='COMPLETE'
    except (Exception,KeyboardInterrupt) as exc:
        result.update(error=f'{type(exc).__name__}: {exc}',interrupted=isinstance(exc,KeyboardInterrupt))
    finally:
        if session is not None:
            try: session.close()
            except Exception as exc: result.update(run_status='ERROR',close_error=str(exc))
        trial.detach()
        result.update(initial=trial.initial,context=trial.context,sources_after=sources())
    return result


def matching(arm,baseline,end):
    fields=('qpos','qvel','ctrl','joint_positions','telemetry_forces','tactile','commanded_joints','adhesion')
    def contacts(row):
        return [dict(pair,geom1_name=prior.context.identities.namespace_component(pair['geom1_name']),
                     geom2_name=prior.context.identities.namespace_component(pair['geom2_name'])) for pair in row['contacts']]
    return (len(arm['samples'])>=end and len(baseline['samples'])>=end and
            all(all(a[k]==b[k] for k in fields) and contacts(a)==contacts(b)
                for a,b in zip(arm['samples'][:end],baseline['samples'][:end])))


def command_audit(arm,baseline):
    rows=arm['samples']
    expected=commands(baseline)
    valid=len(rows)==len(expected)+1 and rows[0]['proposed_joints'] is None
    differences=[]
    for i,row in enumerate(rows[1:]):
        actual=np.asarray(row['commanded_joints'],dtype=float)
        proposed=np.asarray(row['proposed_joints'],dtype=float)
        valid &= (i<len(expected) and actual.shape==(42,) and proposed.shape==(42,)
                  and bool(np.isfinite(proposed).all()) and np.array_equal(actual,expected[i])
                  and row['adhesion']==[0.]*6)
        if not np.array_equal(actual,proposed): differences.append(i)
    return dict(passed=bool(valid),altered_transitions=len(differences),
                first_altered_outgoing_transition=None if not differences else differences[0])


def analyze(directory,manifest,baseline,closed):
    checks=dict(prerequisite=manifest['prerequisite']['verified'],protocol=manifest['protocol']==PROTOCOL,
                sources=manifest['sources_before']==manifest['sources_after']==sources(),
                all_arms=set(manifest['artifacts'])==set(CONDITIONS))
    audits={}
    traces={}
    baseline_sampling=[dict(r['sampling'],eligible_indices=[]) for r in baseline['neural']]
    for identity in CONDITIONS:
        arm,hashes=prior.read_gzip(Path(directory)/manifest['artifacts'][identity]['path'])
        checks[identity+'_archive']=all(hashes[k]==manifest['artifacts'][identity][k] for k in hashes)
        inherited=prior.arm_audit(arm,'ON_P' if identity=='Y_P' else 'ON_C',manifest['prerequisite']['recovery_prerequisite'])
        # Retain the old failure: this version explicitly audits the enlarged set.
        old={k:v for k,v in inherited['checks'].items() if k!='source_integrity'}
        audit=command_audit(arm,baseline)
        prefix=prior.prefix_checks(arm,baseline)
        own=dict(inherited_except_source_list=all(old.values()),
                 versioned_sources=arm['sources_before']==arm['sources_after']==sources(),
                 yoke_protocol=arm['yoke_protocol']==PROTOCOL,commands=audit['passed'],
                 initial_and_prefix=all(prefix.values()) and matching(arm,baseline,prior.START+1),
                 common_rng=[dict(r['sampling'],eligible_indices=[]) for r in arm['neural']]==baseline_sampling)
        if identity=='Y_C':
            own['full_control_reproduction']=matching(arm,baseline,prior.STEPS+1)
            own['full_neural_reproduction']=arm['neural']==[dict(r,delivery_phase='ENABLED') for r in baseline['neural']]
            own['no_command_changes']=audit['altered_transitions']==0
        audits[identity]=dict(checks=own,command_audit=audit,inherited_recovery_audit=inherited)
        checks[identity+'_integrity']=all(own.values())
        traces[identity]=prior.metrics.trace(arm,prior.support_counts(arm))
        del arm
        gc.collect()
    yoked=prior.metrics.response(traces['Y_P'],traces['Y_C'])
    comparison=prior.metrics.contrast(yoked,closed)
    label=comparison['orientation_label']
    comparison['orientation_label']={'ATTENUATED_ORIENTATION_RESPONSE_WITH_TACTILE':'YOKING_REDUCES_RESPONSE',
        'AMPLIFIED_ORIENTATION_RESPONSE_WITH_TACTILE':'YOKING_INCREASES_RESPONSE','MIXED_OR_UNRESOLVED':'MIXED_OR_UNRESOLVED'}[label]
    comparison['estimand']='yoked minus closed-loop response, each versus own undisturbed control'
    if audits['Y_P']['command_audit']['altered_transitions']==0:
        comparison['interpretation_limits'].append('NO_MOTOR_COMMAND_INTERVENTION_EXPOSURE')
    return dict(integrity_passed=all(checks.values()),checks=checks,audits=audits,
                responses=dict(yoked=yoked,closed_loop=closed),contrast=comparison,active_balance_proven=False)


def prerequisite():
    baseline,info=prior.prerequisite()
    path=ROOT/'docs/evidence/tactile-recovery-v1/manifest.json'
    raw=path.read_bytes()
    manifest=json.loads(raw)
    evaluation=prior.analyze(path.parent,manifest,baseline)
    if evaluation!=manifest['evaluation'] or not evaluation['integrity_passed']:
        raise RuntimeError('recovery prerequisite mismatch')
    return baseline,dict(verified=True,recovery_prerequisite=info,
        recovery_manifest_sha256=hashlib.sha256(raw).hexdigest(),
        recovery_manifest_path=path.relative_to(ROOT).as_posix(),
        closed_loop_response=evaluation['responses']['ON'])


def build_run(directory,live=False,progress=print):
    manifest=dict(protocol=PROTOCOL,run_status='NOT_RUN',artifacts={},sources_before=sources(),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    baseline=None
    try:
        if live:
            baseline,info=prerequisite()
            manifest['prerequisite']=info
            manifest['environment']={p:importlib.metadata.version(p) for p in ('flygym','mujoco','numpy')}
            from ..embodiment._windows_m7d_corrected_spontaneous_adapter import _environment
            _environment()
            statuses=[]
            for identity in CONDITIONS:
                arm=run_arm(identity,baseline,progress)
                statuses.append(arm['run_status'])
                manifest['artifacts'][identity]=prior.write_arm(Path(directory)/f'{identity}.json.gz',arm)
                interrupted=arm.get('interrupted',False)
                del arm
                gc.collect()
                if interrupted: break
            manifest['run_status']='COMPLETE' if len(statuses)==2 and all(s=='COMPLETE' for s in statuses) else 'INCOMPLETE'
    except (Exception,KeyboardInterrupt) as exc:
        manifest.update(run_status='ERROR',error=f'{type(exc).__name__}: {exc}')
    manifest['sources_after']=sources()
    try:
        manifest['evaluation']=(analyze(directory,manifest,baseline,manifest['prerequisite']['closed_loop_response'])
            if baseline is not None and set(manifest['artifacts'])==set(CONDITIONS) else dict(integrity_passed=False,status='NOT_RUN_OR_INCOMPLETE'))
    except Exception as exc:
        manifest['evaluation']=dict(integrity_passed=False,status='INVALID_OR_INCOMPLETE',error=f'{type(exc).__name__}: {exc}')
    return native(manifest)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(argv)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    manifest=build_run(args.output_dir,args.live,lambda m:print(m,flush=True))
    with (args.output_dir/'manifest.json').open('x',encoding='utf-8') as stream:
        json.dump(manifest,stream,indent=2,allow_nan=False)
        stream.write('\n')
    print(f"Saved {args.output_dir}; integrity={manifest['evaluation']['integrity_passed']}",flush=True)
    return 0 if manifest['evaluation']['integrity_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
