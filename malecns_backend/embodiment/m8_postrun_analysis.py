"""Read-only, preregistered descriptive analysis of an immutable M8 archive."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
import numpy as np
from . import m8_extended_spontaneous as m8
from .m8_contact_kinematics import LEGS
from .m7e_postrun_analysis import JOINT_NAMES, ADMITTED, periodicity_metrics

def _long_periodicity(signal, time_ms):
    # The preregistered 5-ms diagnostic cadence bounds long-record FFT/autocorrelation cost.
    stride=max(1,int(round(5.0/m8.PHYSICS_DT_MS)))
    value=periodicity_metrics(signal[::stride],time_ms[::stride])
    value['diagnostic_sampling_ms']=stride*m8.PHYSICS_DT_MS
    value['raw_physics_telemetry_retained_ms']=m8.PHYSICS_DT_MS
    return value


def sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def _first(mask,t):
    x=np.flatnonzero(mask); return None if not x.size else float(t[x[0]])


def _episodes(flags,t):
    starts=np.flatnonzero(flags & ~np.r_[False,flags[:-1]])
    ends=np.flatnonzero(flags & ~np.r_[flags[1:],False])
    return [{"start_ms":float(t[a]),"end_ms":float(t[b]),"duration_ms":float(t[b]-t[a]+m8.PHYSICS_DT_MS)} for a,b in zip(starts,ends)]


def analyze(raw_path=m8.RAW_PATH, manifest_path=m8.MANIFEST_PATH, output_path=m8.ANALYSIS_PATH, report_path=m8.REPORT_PATH):
    manifest=json.loads(Path(manifest_path).read_text()); digest=sha256(Path(raw_path))
    if manifest.get('status')!='COMPLETE' or manifest.get('raw',{}).get('sha256')!=digest: raise RuntimeError('M8 evidence identity mismatch')
    with np.load(raw_path,allow_pickle=False) as z: arrays={k:z[k].copy() for k in z.files}
    per={}
    for condition in m8.CONDITIONS:
        g=lambda n: arrays[f'{condition}__{n}']; t=g('physics_time_ms'); nt=g('neural_time_ms'); xyz=g('physics_body_position'); q=g('physics_body_orientation'); joints=g('physics_joint_position')
        horizontal=np.linalg.norm(np.diff(xyz[:,:2],axis=0),axis=1); speed=horizontal/(m8.PHYSICS_DT_MS/1000)
        up=1-2*(q[:,1]**2+q[:,2]**2); fall=xyz[:,2] <= xyz[0,2]*.5; roll=up<=0
        contrib=g('neural_admitted_contributions'); active=np.abs(contrib)>np.maximum(1e-12,np.max(np.abs(contrib),axis=0)*1e-9)
        contacts=g('physics_tarsal_contact'); feet=g('physics_tarsus5_world_position')
        per[condition]={"upright_through_end":bool(not np.any(fall|roll)),"first_fall_time_ms":_first(fall,t),"first_rollover_time_ms":_first(roll,t),
            "net_horizontal_displacement":float(np.linalg.norm(xyz[-1,:2]-xyz[0,:2])),"horizontal_displacement_vector":(xyz[-1,:2]-xyz[0,:2]).tolist(),
            "horizontal_path_length":float(horizontal.sum()),"mean_horizontal_speed":float(speed.mean()),"max_horizontal_speed":float(speed.max(initial=0)),
            "body_height_range":[float(xyz[:,2].min()),float(xyz[:,2].max())],"body_orientation_quaternion_component_ranges":[[float(q[:,i].min()),float(q[:,i].max())] for i in range(4)],"body_up_z_range":[float(up.min()),float(up.max())],
            "motor_channels":{name:{"active":bool(active[:,i].any()),"first_activation_ms":_first(active[:,i],nt),"range":[float(contrib[:,i].min()),float(contrib[:,i].max())]} for i,name in enumerate(ADMITTED)},
            "joints":{name:{"range":[float(joints[:,i].min()),float(joints[:,i].max())],"excursion":float(np.ptp(joints[:,i])),"repeated_activity":_long_periodicity(joints[:,i],t)} for i,name in enumerate(JOINT_NAMES)},
            "authoritative_contacts":{"available":bool(manifest['contact_identity']['available']),"support_count_range":[int(contacts.sum(1).min()),int(contacts.sum(1).max())],"per_leg":{leg:{"contact_duration_ms":float(contacts[:,i].sum()*m8.PHYSICS_DT_MS),"episodes":_episodes(contacts[:,i],t)} for i,leg in enumerate(LEGS)},"support_pattern_counts":{''.join(leg for i,leg in enumerate(LEGS) if row[i]):int(count) for row,count in zip(*np.unique(contacts,axis=0,return_counts=True))}},
            "tarsus5_world_position_ranges":{leg:[[float(feet[:,i,j].min()),float(feet[:,i,j].max())] for j in range(3)] for i,leg in enumerate(LEGS)}}
    a,b=(arrays[f'{c}__physics_qpos'] for c in m8.CONDITIONS); na,nb=(arrays[f'{c}__neural_sensory_encoded'] for c in m8.CONDITIONS); da,db=(arrays[f'{c}__neural_delivered_drive_count'] for c in m8.CONDITIONS); ca,cb=(arrays[f'{c}__neural_aggregate_spikes'] for c in m8.CONDITIONS); ma,mb=(arrays[f'{c}__neural_observer_outputs'] for c in m8.CONDITIONS); acta,actb=(arrays[f'{c}__physics_action'] for c in m8.CONDITIONS)
    pt=arrays[f'{m8.CONDITIONS[0]}__physics_time_ms']; nt=arrays[f'{m8.CONDITIONS[0]}__neural_time_ms']
    first_s=_first(np.any(na!=nb,axis=1),nt)
    milestones={"mapped_motor_output_ms":_first(np.any(ma!=0,axis=1),nt),"physical_action_divergence_ms":_first(np.any(acta!=actb,axis=1),pt),"physical_state_divergence_ms":_first(np.any(a!=b,axis=1),pt),"tibial_encoding_divergence_ms":first_s,"delivered_sensory_divergence_ms":_first(da!=db,nt),"downstream_cns_divergence_ms":_first((ca!=cb)&(nt>=(first_s if first_s is not None else np.inf)),nt),"later_mapped_motor_state_divergence_ms":_first(np.any(ma!=mb,axis=1)&(nt>=(first_s if first_s is not None else np.inf)),nt)}
    analysis={"schema":"M8-POSTRUN-ANALYSIS.1","status":"COMPLETE","source_raw_sha256":digest,"preregistered_descriptive_analysis":True,"walking_classification":None,"gait_classification":None,"conditions":per,"causal_sequence":milestones,"inter_leg_temporal_relationships":{"method":"pairwise first admitted-motor activation offsets; descriptive only","enabled_first_activation_offsets_ms":{f"{a}_minus_{b}":(None if per[m8.CONDITIONS[0]]["motor_channels"][a]["first_activation_ms"] is None or per[m8.CONDITIONS[0]]["motor_channels"][b]["first_activation_ms"] is None else per[m8.CONDITIONS[0]]["motor_channels"][a]["first_activation_ms"]-per[m8.CONDITIONS[0]]["motor_channels"][b]["first_activation_ms"]) for a in ADMITTED for b in ADMITTED if a<b}},"between_condition_difference":{"net_horizontal_displacement":per[m8.CONDITIONS[0]]["net_horizontal_displacement"]-per[m8.CONDITIONS[1]]["net_horizontal_displacement"],"horizontal_path_length":per[m8.CONDITIONS[0]]["horizontal_path_length"]-per[m8.CONDITIONS[1]]["horizontal_path_length"]},"limitations":["No movement is classified as walking, gait, reflex, or CPG.","Spectral and correlation summaries are descriptive and were not tuned on M8 outcomes."]}
    Path(output_path).write_text(json.dumps(analysis,indent=2,sort_keys=True,allow_nan=False)+'\n')
    lines=['# M8 post-run descriptive report','',f'Raw SHA-256: `{digest}`','', 'This report does not classify walking, gait, reflex, or CPG.','', '## Causal sequence','']+[f'- {k}: {v}' for k,v in milestones.items()]
    for c,v in per.items(): lines += ['',f'## {c}','',f'- Upright through end: {v["upright_through_end"]}',f'- Fall / rollover (ms): {v["first_fall_time_ms"]} / {v["first_rollover_time_ms"]}',f'- Net horizontal displacement: {v["net_horizontal_displacement"]}',f'- Horizontal path length: {v["horizontal_path_length"]}',f'- Mean / max horizontal speed: {v["mean_horizontal_speed"]} / {v["max_horizontal_speed"]}',f'- Authoritative contact identity available: {v["authoritative_contacts"]["available"]}']
    Path(report_path).write_text('\n'.join(lines)+'\n')
    return analysis
