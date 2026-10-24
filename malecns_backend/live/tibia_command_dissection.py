"""Preselected anatomical tibia command-group yoke; no neural tuning."""
import argparse
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import numpy as np

from . import tactile_motor_yoke as yoke
from . import tactile_recovery as recovery
from .tactile_boundary import native
from ..embodiment import m11_motor_channel_dissection as m11
from ..embodiment import live_v3_motor_interface as v3

ROOT=recovery.ROOT
CONDITIONS=('T_C','T_P')
SELECTED=tuple((n,i) for n,i,_ in m11.MOTOR_CHANNELS if n.endswith('Tibia'))
EXPECTED=(('joint_LFTibia',5),('joint_LMTibia',12),('joint_LHTibia',19),
          ('joint_RFTibia',26),('joint_RMTibia',33),('joint_RHTibia',40))
if SELECTED!=EXPECTED or not set(n for n,_ in SELECTED)<=set(v3.V3_MOTOR):
    raise RuntimeError('exact anatomical tibia inventory required')
INDICES=np.asarray([i for _,i in SELECTED],dtype=int)
PROTOCOL=dict(schema='tibia-command-dissection-v1',conditions=list(CONDITIONS),
    selected=[dict(name=n,action_index=i) for n,i in SELECTED],seed=1,steps=20000,
    neural_steps=4000,source='matched-pair ENABLED commanded_joints sample n+1',
    classification_inclusive_deg=.25,retries=0,ordinary_live_mode_changed=False)
FILES=('docs/TIBIA_COMMAND_DISSECTION_V1.md','malecns_backend/live/tibia_command_dissection.py',
       'malecns_backend/embodiment/m11_motor_channel_dissection.py',
       'malecns_backend/embodiment/live_v3_motor_interface.py')


def sources():
    return dict(yoke.sources(),**{p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in FILES})


def selected_action(proposed,archived):
    proposed=np.asarray(proposed,dtype=float)
    archived=np.asarray(archived,dtype=float)
    if proposed.shape!=(42,) or archived.shape!=(42,) or not np.isfinite(proposed).all() or not np.isfinite(archived).all():
        raise ValueError('finite 42-coordinate proposed and archived actions required')
    applied=proposed.copy()
    applied[INDICES]=archived[INDICES]
    return applied


class TibiaTrial(yoke.YokeTrial):
    def __init__(self,identity,baseline):
        if identity not in CONDITIONS: raise ValueError('unknown dissection condition')
        super().__init__('Y_P' if identity=='T_P' else 'Y_C',baseline)
        self.identity=identity
        self.applied=None

    def attach(self,brain,channels,*,sensory_sources):
        result=super().attach(brain,channels,sensory_sources=sensory_sources)
        if set(channels)!=set(v3.V3_MOTOR) or any(channels[n]['index']!=i for n,i in SELECTED):
            raise RuntimeError('actual admitted channel/action identity mismatch')
        return result

    def apply(self,action):
        index=len(self.samples)-1
        if not 0<=index<len(self.actions) or set(action)!={'joints','adhesion'} or not np.array_equal(action['adhesion'],np.zeros(6)):
            raise ValueError('invalid outgoing transition, fields or adhesion')
        applied=selected_action(action['joints'],self.actions[index])
        self.proposed=np.asarray(action['joints'],dtype=float).copy().tolist()
        self.applied=dict(joints=applied.copy(),adhesion=np.zeros(6))
        return self.original_sim_step(dict(joints=applied.copy(),adhesion=np.zeros(6)))

    def capture(self,physics,obs,action):
        applied=None if action is None else self.applied
        if action is not None and applied is None: raise RuntimeError('missing applied action')
        recovery.RecoveryTrial.capture(self,physics,obs,applied)
        self.samples[-1]['proposed_joints']=self.proposed


def run_arm(identity,baseline,progress):
    trial=TibiaTrial(identity,baseline)
    result=dict(schema='tibia-dissection-arm-v1',identity=identity,protocol=recovery.PROTOCOL,
        dissection_protocol=PROTOCOL,run_status='ERROR',samples=trial.samples,neural=trial.neural,sources_before=sources())
    session=None
    try:
        session=recovery.create_session(trial)
        progress(f'{identity}: initializing CNS; only six tibia actions are yoked.')
        state=session.initialize()
        if state.time_ms!=0.: raise RuntimeError('nonzero reset')
        last=time.monotonic()
        for step in range(1,recovery.STEPS+1):
            state=session.step(lightweight=True)
            if state.physics_transitions!=step or state.neural_transitions!=step//5:
                raise RuntimeError('transition count mismatch')
            if time.monotonic()-last>=15:
                progress(f'{identity}: {step}/{recovery.STEPS} physics transitions.')
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


def command_audit(arm,baseline):
    rows=arm['samples']
    schedule=yoke.commands(baseline)
    valid=len(rows)==len(schedule)+1 and rows[0]['proposed_joints'] is None
    count={n:0 for n,_ in SELECTED}
    first=None
    altered=0
    for index,row in enumerate(rows[1:]):
        if index>=len(schedule): return dict(passed=False)
        proposed=np.asarray(row['proposed_joints'],dtype=float)
        expected=selected_action(proposed,schedule[index])
        actual=np.asarray(row['commanded_joints'],dtype=float)
        valid &= np.array_equal(actual,expected) and row['adhesion']==[0.]*6
        differences=actual!=proposed
        if np.any(differences):
            altered+=1
            if first is None: first=index
        for n,i in SELECTED: count[n]+=int(differences[i])
    return dict(passed=bool(valid),altered_transitions=altered,first_altered_outgoing_transition=first,per_channel=count)


def comparison(selected,reference):
    peak=m11.ablation_effect(selected['post_peak_orientation_deg'],reference['post_peak_orientation_deg'])
    mean=m11.ablation_effect(selected['post_mean_orientation_deg'],reference['post_mean_orientation_deg'])
    labels=[m11.classify(d,.25) for d in (peak,mean)]
    label=('SELECTIVE_YOKING_REDUCES_RESPONSE' if labels==[m11.CLASSIFICATIONS[0]]*2 else
           'SELECTIVE_YOKING_INCREASES_RESPONSE' if labels==[m11.CLASSIFICATIONS[1]]*2 else 'MIXED_OR_UNRESOLVED')
    limits=[]
    for name,response in (('SELECTED',selected),('REFERENCE',reference)):
        if not response['baseline_qualified']: limits.append(name+'_BASELINE_NOT_QUALIFIED')
        if not response['resolved_perturbation']: limits.append(name+'_PERTURBATION_BELOW_RESOLUTION')
        if not response['relative_band_exited']: limits.append(name+'_NO_RECOVERY_BAND_EXIT')
    return dict(label=label,peak_selected_minus_reference_deg=peak,mean_selected_minus_reference_deg=mean,
        inherited_m11_metric_labels=labels,interpretation_limits=limits,active_balance_proven=False)


def analyze(directory,manifest,baseline):
    checks=dict(prerequisite=manifest['prerequisite']['verified'],protocol=manifest['protocol']==PROTOCOL,
        sources=manifest['sources_before']==manifest['sources_after']==sources(),all_arms=set(manifest['artifacts'])==set(CONDITIONS))
    audits={}
    traces={}
    expected_sampling=[dict(r['sampling'],eligible_indices=[]) for r in baseline['neural']]
    for identity in CONDITIONS:
        arm,hashes=recovery.read_gzip(Path(directory)/manifest['artifacts'][identity]['path'])
        checks[identity+'_archive']=all(hashes[k]==manifest['artifacts'][identity][k] for k in hashes)
        inherited=recovery.arm_audit(arm,'ON_P' if identity=='T_P' else 'ON_C',manifest['prerequisite']['recovery_prerequisite'])
        remaining={k:v for k,v in inherited['checks'].items() if k!='source_integrity'}
        action=command_audit(arm,baseline)
        own=dict(inherited_except_source_set=all(remaining.values()),
            versioned_sources=arm['sources_before']==arm['sources_after']==sources(),
            dissection_protocol=arm['dissection_protocol']==PROTOCOL,command_boundary=action['passed'],
            initial_and_prefix=all(recovery.prefix_checks(arm,baseline).values()) and yoke.matching(arm,baseline,recovery.START+1),
            common_rng=[dict(r['sampling'],eligible_indices=[]) for r in arm['neural']]==expected_sampling,
            exact_selected_inventory=all(arm['initial']['motor_inventory'][n]['action_index']==i for n,i in SELECTED)
                and set(arm['initial']['motor_inventory'])==set(v3.V3_MOTOR))
        if identity=='T_C':
            own['full_control_reproduction']=yoke.matching(arm,baseline,recovery.STEPS+1)
            own['full_neural_reproduction']=arm['neural']==[dict(r,delivery_phase='ENABLED') for r in baseline['neural']]
            own['no_command_changes']=action['altered_transitions']==0
        audits[identity]=dict(checks=own,command_audit=action,inherited_recovery_audit=inherited)
        checks[identity+'_integrity']=all(own.values())
        traces[identity]=recovery.metrics.trace(arm,recovery.support_counts(arm))
        del arm
        gc.collect()
    selected=recovery.metrics.response(traces['T_P'],traces['T_C'])
    info=manifest['prerequisite']
    primary=comparison(selected,info['closed_loop_response'])
    if audits['T_P']['command_audit']['altered_transitions']==0:
        primary['interpretation_limits'].append('NO_SELECTED_COMMAND_INTERVENTION_EXPOSURE')
    return dict(integrity_passed=all(checks.values()),checks=checks,audits=audits,
        responses=dict(selected=selected,closed_loop=info['closed_loop_response'],all_command_yoke=info['all_yoke_response']),
        primary=primary,descriptive_vs_all_yoke=comparison(selected,info['all_yoke_response']),active_balance_proven=False)


def prerequisite():
    baseline,info=yoke.prerequisite()
    path=ROOT/'docs/evidence/tactile-motor-yoke-v1/manifest.json'
    raw=path.read_bytes()
    manifest=json.loads(raw)
    evaluation=yoke.analyze(path.parent,manifest,baseline,info['closed_loop_response'])
    if evaluation!=manifest['evaluation'] or not evaluation['integrity_passed']:
        raise RuntimeError('upstream motor-yoke evidence mismatch')
    return baseline,dict(verified=True,recovery_prerequisite=info['recovery_prerequisite'],
        upstream_manifest_path=path.relative_to(ROOT).as_posix(),upstream_manifest_sha256=hashlib.sha256(raw).hexdigest(),
        upstream_prerequisite=info,closed_loop_response=info['closed_loop_response'],
        all_yoke_response=evaluation['responses']['yoked'])


def build_run(directory,live=False,progress=print):
    manifest=dict(protocol=PROTOCOL,run_status='NOT_RUN',artifacts={},sources_before=sources(),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    baseline=None
    try:
        if live:
            baseline,manifest['prerequisite']=prerequisite()
            manifest['environment']={p:importlib.metadata.version(p) for p in ('flygym','mujoco','numpy')}
            from ..embodiment._windows_m7d_corrected_spontaneous_adapter import _environment
            _environment()
            statuses=[]
            for identity in CONDITIONS:
                arm=run_arm(identity,baseline,progress)
                statuses.append(arm['run_status'])
                manifest['artifacts'][identity]=recovery.write_arm(Path(directory)/f'{identity}.json.gz',arm)
                interrupted=arm.get('interrupted',False)
                del arm
                gc.collect()
                if interrupted: break
            manifest['run_status']='COMPLETE' if len(statuses)==2 and all(s=='COMPLETE' for s in statuses) else 'INCOMPLETE'
    except (Exception,KeyboardInterrupt) as exc:
        manifest.update(run_status='ERROR',error=f'{type(exc).__name__}: {exc}')
    manifest['sources_after']=sources()
    try:
        manifest['evaluation']=(analyze(directory,manifest,baseline) if baseline is not None and set(manifest['artifacts'])==set(CONDITIONS)
            else dict(integrity_passed=False,status='NOT_RUN_OR_INCOMPLETE'))
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
