"""Predeclared time-aligned analysis of frozen command-policy evidence; no physics."""
import argparse
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess

import numpy as np

from . import complement_command_dissection as upstream
from .tactile_boundary import native
from .protocol import JOINT_NAMES

ROOT=upstream.ROOT
metrics=upstream.recovery.metrics
POLICIES=('ON_P','T_P','C_P','Y_P')
CONTROLS=dict(ON_P='ON_C',T_P='T_C',C_P='C_C',Y_P='Y_C')
LABELS=dict(ON_P='Full closed loop',T_P='Tibia commands replayed',
            C_P='Complement commands replayed',Y_P='All commands replayed')
PROTOCOL=dict(schema='group-posture-analysis-v1',steps=20000,dt_s=.0001,
    policies=list(POLICIES),controls=CONTROLS,post_start_index=5201,
    interaction_order=['Y_P','-T_P','-C_P','ON_P'],position_resolution_mm=.005,
    scientific_transitions=0,ordinary_live_mode_changed=False)
FILES=('docs/GROUP_POSTURE_ANALYSIS_V1.md','malecns_backend/live/group_posture_analysis.py',
       'malecns_backend/live/protocol.py')


def sources():
    return dict(upstream.sources(),**{p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in FILES})


def inventory():
    rows=(*upstream.tibia.SELECTED,*upstream.SELECTED)
    if len(JOINT_NAMES)!=42 or len(rows)!=20 or len(set(i for _,i in rows))!=20 or any(JOINT_NAMES[i]!=n for n,i in rows):
        raise ValueError('canonical model/admitted motor correspondence failed')
    admitted={n for n,_ in rows}
    remaining=[dict(name=n,action_index=i) for i,n in enumerate(JOINT_NAMES) if n not in admitted]
    coxa=[r for r in remaining if 'Coxa' in r['name']]
    tarsus=[r for r in remaining if r['name'].endswith('Tarsus1')]
    if len(coxa)!=18 or len(tarsus)!=4 or len(remaining)!=22: raise ValueError('unexpected remaining inventory')
    return dict(model_coordinates=42,admitted_motor_coordinates=20,
        admitted=[dict(name=n,action_index=i) for n,i in sorted(rows,key=lambda r:r[1])],
        breakdown=dict(tibia=6,femur=6,femur_roll=6,front_tarsus=2),remaining=remaining,
        remaining_breakdown=dict(coxa=18,middle_hind_tarsus=4),
        proprioceptive_populations=6,proprioceptive_neurons=392,
        experimental_tactile_populations=6,experimental_tactile_neurons=1877,
        ordinary_live_tactile_enabled=False,
        interpretation='Motor admission count, not percent biological mapping or project completion.')


def world_up(quaternion):
    q=np.asarray(quaternion,dtype=float)
    return metrics.angular_velocity_world(q,np.tile([0.,0.,1.],(len(q),1)))


def angle_between(a,b):
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    if a.shape!=b.shape or a.ndim!=2 or a.shape[1]!=3 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('aligned finite world vectors required')
    norms=np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)
    if np.any(norms<=0): raise ValueError('nonzero world vectors required')
    return np.degrees(np.arccos(np.clip(np.sum(a*b,axis=1)/norms,-1.,1.)))


def interaction(vectors):
    arrays=[np.asarray(vectors[p],dtype=float) for p in POLICIES]
    if arrays[0].ndim!=2 or arrays[0].shape[1]!=3 or any(a.shape!=arrays[0].shape or not np.isfinite(a).all() for a in arrays):
        raise ValueError('four aligned finite Nx3 response vectors required')
    return arrays[3]-arrays[1]-arrays[2]+arrays[0]


def curves(traces):
    result={}
    for policy in POLICIES:
        pushed,control=traces[policy],traces[CONTROLS[policy]]
        p,q=np.asarray(pushed['position']),np.asarray(control['position'])
        if p.shape!=q.shape or p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all() or not np.isfinite(q).all():
            raise ValueError('aligned finite root positions required')
        up,base_up=world_up(pushed['quaternion']),world_up(control['quaternion'])
        result[policy]=dict(absolute_tilt_deg=np.degrees(np.arccos(np.clip(up[:,2],-1.,1.))),
            control_tilt_deg=np.degrees(np.arccos(np.clip(base_up[:,2],-1.,1.))),
            relative_rotation_deg=metrics.quaternion_shortest_arc_deg(pushed['quaternion'],control['quaternion']),
            relative_up_deg=angle_between(up,base_up),root_response=p-q,up_response=up-base_up)
    return result


def peak(values,start):
    values=np.asarray(values,dtype=float)
    if values.ndim!=1 or not np.isfinite(values).all() or not 0<=start<len(values):
        raise ValueError('finite vector and valid summary window required')
    index=int(start+np.argmax(values[start:]))
    return dict(value=float(values[index]),index=index,time_ms=index*.1)


def summarize(curve,start=5201):
    absolute=peak(curve['absolute_tilt_deg'],start)
    relative=peak(curve['relative_rotation_deg'],start)
    up=peak(curve['relative_up_deg'],start)
    i,j=absolute['index'],relative['index']
    return dict(absolute_tilt_peak=absolute,relative_rotation_peak=relative,relative_up_peak=up,
        at_absolute_tilt_peak=dict(relative_rotation_deg=float(curve['relative_rotation_deg'][i]),
            control_tilt_deg=float(curve['control_tilt_deg'][i])),
        at_relative_rotation_peak=dict(absolute_tilt_deg=float(curve['absolute_tilt_deg'][j]),
            control_tilt_deg=float(curve['control_tilt_deg'][j]),relative_up_deg=float(curve['relative_up_deg'][j])))


def vector_summary(vector,start=5201):
    norm=np.linalg.norm(vector,axis=1)
    maximum=peak(norm,start)
    return dict(peak_norm=maximum,xyz_at_peak=vector[maximum['index']].tolist(),
        mean_norm=float(np.mean(norm[start:])),
        signed_xyz_integral=(np.sum((vector[start:-1]+vector[start+1:])*.5,axis=0)*.0001).tolist())


def analyze(traces,expected):
    if set(traces)!=set((*POLICIES,*CONTROLS.values())): raise ValueError('all eight frozen arms required')
    for trace in traces.values():
        for field,shape in (('position',(20001,3)),('quaternion',(20001,4)),('velocity',(20001,6)),('up_z',(20001,)),('supports',(20001,))):
            value=np.asarray(trace[field])
            if value.shape!=shape or not np.isfinite(value).all(): raise ValueError('complete finite root traces required')
        if np.any((trace['supports']<0)|(trace['supports']>6)) or np.any(trace['supports']!=np.floor(trace['supports'])):
            raise ValueError('exact six-foot support counts required')
    baseline=traces['ON_C']
    checks=dict(all_controls_equal=all(all(np.array_equal(traces[c][f],baseline[f]) for f in baseline) for c in CONTROLS.values()),
        pre_force_matching=all(all(np.array_equal(traces[p][f][:5001],traces[CONTROLS[p]][f][:5001]) for f in baseline) for p in POLICIES))
    response={p:metrics.response(traces[p],traces[CONTROLS[p]]) for p in POLICIES}
    checks['saved_responses_reproduced']=response==expected
    data=curves(traces)
    position=interaction({p:data[p]['root_response'] for p in POLICIES})
    up=interaction({p:data[p]['up_response'] for p in POLICIES})
    position_summary=vector_summary(position)
    position_summary['resolution_label']=('RESOLVED_ROOT_VECTOR_NONADDITIVITY' if position_summary['peak_norm']['value']>.005
                                          else 'NOT_RESOLVED_AT_INHERITED_POSITION_RESOLUTION')
    report=dict(integrity_passed=all(checks.values()),checks=checks,protocol=PROTOCOL,
        inventory=inventory(),responses=response,time_aligned={p:summarize(data[p]) for p in POLICIES},
        position_interaction=position_summary,dimensionless_up_interaction=vector_summary(up),
        active_balance_proven=False,scientific_transitions=0,
        limits='One frozen deterministic history; vector interaction is not a statistical test or independent channel contribution. Full orientation includes heading; relative up excludes pure yaw.')
    return native(report),data,dict(position=position,up=up)


FOLDERS=dict(ON_P='tactile-recovery-v1',T_P='tibia-command-dissection-v1',
             C_P='complement-command-dissection-v1',Y_P='tactile-motor-yoke-v1')


def reduce_arm(arm):
    times=np.asarray([s['time_s'] for s in arm['samples']])
    if times.shape!=(20001,) or not np.allclose(times,np.arange(20001)*.0001,rtol=0,atol=1e-10):
        raise ValueError('complete aligned 0.1 ms time grid required')
    return metrics.trace(arm,upstream.recovery.support_counts(arm))


def load_verified(progress=print):
    cached={p:(ROOT/'docs/evidence'/folder/'manifest.json').read_bytes() for p,folder in FOLDERS.items()}
    progress('Verifying full frozen provenance and evaluations; no CNS/physics execution.')
    baseline,info=upstream.prerequisite()
    current=json.loads(cached['C_P'])
    evaluation=upstream.analyze(ROOT/'docs/evidence'/FOLDERS['C_P'],current,baseline)
    if current['prerequisite']!=info or evaluation!=current['evaluation'] or not evaluation['integrity_passed']:
        raise ValueError('frozen complementary evidence/prerequisite mismatch')
    if any((ROOT/'docs/evidence'/FOLDERS[p]/'manifest.json').read_bytes()!=raw for p,raw in cached.items()):
        raise ValueError('reference manifests changed during verification')
    expected=dict(ON_P=evaluation['responses']['closed_loop'],T_P=evaluation['responses']['tibia_only'],
                  C_P=evaluation['responses']['selected'],Y_P=evaluation['responses']['all_command_yoke'])
    traces={'ON_C':reduce_arm(baseline)}
    references={'ON_C':info['recovery_prerequisite']['baseline']}
    del baseline
    gc.collect()
    for policy,folder in FOLDERS.items():
        manifest=json.loads(cached[policy])
        identities=(policy,) if policy=='ON_P' else (policy,CONTROLS[policy])
        for identity in identities:
            record=manifest['artifacts'][identity]
            if record['path']!=f'{identity}.json.gz': raise ValueError('unexpected frozen archive path')
            path=ROOT/'docs/evidence'/folder/record['path']
            progress(f'Reducing verified {identity} root trace.')
            arm,hashes=upstream.recovery.read_gzip(path)
            if any(hashes[k]!=record[k] for k in hashes): raise ValueError('frozen raw artifact mismatch')
            traces[identity]=reduce_arm(arm)
            references[identity]=dict(path=path.relative_to(ROOT).as_posix(),**hashes,
                manifest_path=f'docs/evidence/{folder}/manifest.json',
                manifest_sha256=hashlib.sha256(cached[policy]).hexdigest())
            del arm
            gc.collect()
    return traces,expected,references


def write_npz(path,traces):
    arrays={f'{identity}__{field}':value for identity,trace in traces.items() for field,value in trace.items()}
    if any(np.asarray(value).dtype.kind not in 'biuf' for value in arrays.values()):
        raise ValueError('numeric aligned arrays only; no object/pickle data')
    with Path(path).open('xb') as stream: np.savez_compressed(stream,**arrays)


def read_npz(path):
    with np.load(path,allow_pickle=False) as packed:
        expected={f'{i}__{f}' for i in (*POLICIES,*CONTROLS.values()) for f in ('position','quaternion','velocity','up_z','supports')}
        if set(packed.files)!=expected: raise ValueError('exact aligned artifact fields required')
        return {i:{f:packed[f'{i}__{f}'].copy() for f in ('position','quaternion','velocity','up_z','supports')}
                for i in (*POLICIES,*CONTROLS.values())}


def plots(directory,traces,data,vectors):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    time_ms=np.arange(20001)*.1
    colors=dict(ON_P='#1858a8',T_P='#ca6500',C_P='#8b39a3',Y_P='#00846b')
    fig,axes=plt.subplots(3,1,figsize=(11,10),sharex=True,layout='constrained')
    fields=('absolute_tilt_deg','relative_rotation_deg','relative_up_deg')
    labels=('Body tilt from world upright (deg)','Orientation from own control (deg)','Body-up angle from own control (deg)')
    for axis,field,label in zip(axes,fields,labels):
        for policy in POLICIES: axis.plot(time_ms,data[policy][field],color=colors[policy],lw=1,label=LABELS[policy])
        axis.set_ylabel(label)
    axes[0].plot(time_ms,data['ON_P']['control_tilt_deg'],color='#555555',ls='--',lw=1,label='Common undisturbed control')
    axes[0].legend(fontsize=8,ncol=2,loc='upper right')
    fig.suptitle('Frozen command policies: absolute posture and disturbance-relative orientation',fontsize=13)
    finish_plot(fig,axes,directory/'posture.png')
    fig,axes=plt.subplots(3,1,figsize=(11,10),sharex=True,layout='constrained')
    for policy in POLICIES:
        axes[0].plot(time_ms,np.linalg.norm(data[policy]['root_response'],axis=1),lw=1,color=colors[policy],label=LABELS[policy])
    axes[0].plot(time_ms,np.linalg.norm(vectors['position'],axis=1),color='black',ls='--',lw=1,label='Interaction norm')
    axes[0].set_ylabel('Root response norm (model mm)')
    axes[0].legend(fontsize=8,ncol=2,loc='upper right')
    for index,(axis,field,unit) in enumerate(((axes[1],'position','model mm'),(axes[2],'up','dimensionless'))):
        for j,(name,color) in enumerate(zip(('x','y','z'),('#b12d3a','#087d75','#414c9c'))):
            axis.plot(time_ms,vectors[field][:,j],color=color,lw=1,label=name)
        axis.set_ylabel(f'Signed {field} interaction ({unit})')
        axis.axhline(0,color='#777777',lw=.5)
        axis.legend(fontsize=8,ncol=3)
    fig.suptitle('Predeclared vector interaction: all replay - tibia replay - complement replay + closed loop',fontsize=11)
    finish_plot(fig,axes,directory/'interaction.png')


def finish_plot(fig,axes,path):
    import matplotlib.pyplot as plt
    for axis in axes:
        axis.axvspan(500,520,color='#e8c451',alpha=.25)
        axis.axvline(520.1,color='#555555',ls=':',lw=.8)
        axis.set_xlim(0,2000)
        axis.grid(alpha=.2)
    axes[-1].set_xlabel('Saved simulation time (ms); yellow = pulse, dotted = post-force window start')
    fig.savefig(path,dpi=150)
    plt.close(fig)


def file_record(path):
    raw=Path(path).read_bytes()
    return dict(path=Path(path).name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def run(directory,progress=print):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    report=dict(protocol=PROTOCOL,run_status='ERROR',sources_before=sources(),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        scientific_transitions=0,environment={p:importlib.metadata.version(p) for p in ('numpy','matplotlib')})
    try:
        traces,expected,references=load_verified(progress)
        report['references']=references
        report['expected_frozen_responses']=expected
        report['evaluation'],data,vectors=analyze(traces,expected)
        write_npz(directory/'aligned-traces.npz',traces)
        report['artifacts']={'aligned-traces.npz':file_record(directory/'aligned-traces.npz')}
        if report['evaluation']['integrity_passed']:
            plots(directory,traces,data,vectors)
            report['artifacts'].update({name:file_record(directory/name) for name in ('posture.png','interaction.png')})
            report['run_status']='COMPLETE'
    except (Exception,KeyboardInterrupt) as exc:
        report['error']=f'{type(exc).__name__}: {exc}'
    report['sources_after']=sources()
    report['source_integrity']=report['sources_before']==report['sources_after']
    with (directory/'analysis.json').open('x',encoding='utf-8') as stream:
        json.dump(native(report),stream,indent=2,allow_nan=False)
        stream.write('\n')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(argv)
    report=run(args.output_dir,lambda message:print(message,flush=True))
    passed=report['run_status']=='COMPLETE' and report['source_integrity'] and report['evaluation']['integrity_passed']
    print(f'Saved {args.output_dir}; analysis integrity={passed}; scientific transitions=0',flush=True)
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
