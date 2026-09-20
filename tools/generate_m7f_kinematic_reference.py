#!/usr/bin/env python3
"""Generate static M7F kinematic evidence.  This script never creates/steps physics.

The implementation deliberately evaluates the frozen MJCF transform tree directly;
it is also usable on Windows without MuJoCo.  ``--verify-mujoco`` additionally calls
only ``mujoco.mj_forward`` to exercise the assigned poses (never ``mj_step``).
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
import xml.etree.ElementTree as ET
import math

ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / "fly-brain-main/body/flybody/fruitfly.xml"
MANIFEST = ROOT / "FlyBrainUnity/Assets/StreamingAssets/M7FReplay/m7f_manifest.json"
REPLAY = ROOT / "FlyBrainUnity/Assets/StreamingAssets/M7FReplay/m7f_enabled_replay.bin"
OUTPUT = ROOT / "FlyBrainUnity/Assets/StreamingAssets/M7FValidation/m7f_frame0_kinematic_reference.json"
FRAMES = (0, 540, 541, 785, 1210, 1570, 2500, 3980, 5000)
LEGS = (("LF",1,"left"),("LM",2,"left"),("LH",3,"left"),("RF",1,"right"),("RM",2,"right"),("RH",3,"right"))
SUFFIX = ("Coxa","Coxa_roll","Coxa_yaw","Femur","Femur_roll","Tibia","Tarsus1")

def mul(a,b):
    w,x,y,z=a; W,X,Y,Z=b
    return [w*W-x*X-y*Y-z*Z,w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W]
def rot(q,v): return mul(mul(q,[0.,*v]),[q[0],-q[1],-q[2],-q[3]])[1:]
def axisq(axis,angle):
    s=math.sin(angle/2); return [math.cos(angle/2),axis[0]*s,axis[1]*s,axis[2]*s]
def vec(text, default): return [float(x) for x in text.split()] if text else list(default)
def add(a,b): return [x+y for x,y in zip(a,b)]
def norm(q):
    n=math.sqrt(sum(x*x for x in q)); return [x/n for x in q]
def rounded(v): return [round(float(x),12) for x in v]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def arrays():
    m=json.loads(MANIFEST.read_text()); layout={x["name"]:x for x in m["binary"]["layout"]}
    raw=REPLAY.read_bytes(); n=m["frame_counts"]["physics"]
    def read(name, width):
        x=layout[name]; flat=struct.unpack_from("<"+"d"*(n*width),raw,x["offset_bytes"])
        return [flat[i*width:(i+1)*width] for i in range(n)]
    return m,read("physics_body_position",3),read("physics_body_orientation",4),read("physics_joint_position",42)

def element_index():
    thorax=ET.parse(XML).getroot().find("worldbody/body[@name='thorax']")
    return {b.attrib["name"]:b for b in thorax.iter("body")}

def evaluate(frame, root_p, root_q, qvalues, names, bodies):
    qi=dict(zip(names,qvalues)); records=[]
    for code,tier,side in LEGS:
        body_names=[f"coxa_T{tier}_{side}",f"femur_T{tier}_{side}",f"tibia_T{tier}_{side}",f"tarsus_T{tier}_{side}"]
        p=list(root_p); q=list(root_q)
        canonical=((f"joint_{code}Coxa_roll",f"joint_{code}Coxa_yaw",f"joint_{code}Coxa"),
                   (f"joint_{code}Femur_roll",f"joint_{code}Femur"),(f"joint_{code}Tibia",),(f"joint_{code}Tarsus1",))
        for si,(bn,jns) in enumerate(zip(body_names,canonical)):
            b=bodies[bn]; bp=vec(b.get("pos"),[0,0,0]); bq=norm(vec(b.get("quat"),[1,0,0,0]))
            p=add(p,rot(q,bp)); q=mul(q,bq); pivot=list(p); joints=[]
            axes=((0,0,1),(0,1,0),(1,0,0)) if si==0 else ((0,1,0),(1,0,0)) if si==1 else ((1,0,0),)
            for jn,axis in zip(jns,axes):
                world_axis=rot(q,axis); joints.append({"canonical_name":jn,"pivot":rounded(pivot),"axis":rounded(world_axis)})
                q=norm(mul(q,axisq(axis,qi[jn])))
            if si<3: endpoint=add(p,rot(q,vec(bodies[body_names[si+1]].get("pos"),[0,0,0])))
            else:
                geom=next(g for g in b.findall("geom") if g.get("name")==bn+"_collision")
                endpoint=add(p,rot(q,vec(geom.get("fromto"),[0,0,0,0,0,0])[3:]))
            records.append({"leg":code,"segment":("coxa","femur","tibia","tarsus1")[si],"body":bn,
                "parent_body":"thorax" if si==0 else body_names[si-1],"position":rounded(pivot),
                "orientation_wxyz":rounded(q),"endpoint":rounded(endpoint),"joints":joints})
    return records

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path,default=OUTPUT); ap.add_argument("--verify-mujoco",action="store_true"); a=ap.parse_args()
    manifest,pos,quat,joints=arrays(); names=manifest["joint_names"]; bodies=element_index()
    frames=[{"frame":f,"time_ms":round(f*.1,1),"root_position":rounded(pos[f]),"root_orientation_wxyz":rounded(quat[f]),
             "segments":evaluate(f,pos[f],norm(quat[f]),joints[f],names,bodies)} for f in FRAMES]
    out={"schema":"m7f-kinematic-reference-v1","purpose":"visualization validation only","source_xml":str(XML.relative_to(ROOT)),
         "source_xml_sha256":sha(XML),"source_replay":str(REPLAY.relative_to(ROOT)),"source_replay_sha256":sha(REPLAY),
         "coordinate_convention":"frozen MJCF source coordinates and model units; quaternion wxyz","frames":frames,
         "evaluation":{"method":"deterministic static MJCF tree forward kinematics","mj_forward_calls":0,"mj_step_calls":0,"physics_transitions":0,"MaleCNS_updates":0}}
    if a.verify_mujoco:
        import mujoco
        model=mujoco.MjModel.from_xml_path(str(XML)); data=mujoco.MjData(model); calls=0
        xml_joint = {}
        for code,tier,side in LEGS:
            xml_joint.update({f"joint_{code}Coxa":f"coxa_T{tier}_{side}",f"joint_{code}Coxa_roll":f"coxa_abduct_T{tier}_{side}",
                              f"joint_{code}Coxa_yaw":f"coxa_twist_T{tier}_{side}",f"joint_{code}Femur":f"femur_T{tier}_{side}",
                              f"joint_{code}Femur_roll":f"femur_twist_T{tier}_{side}",f"joint_{code}Tibia":f"tibia_T{tier}_{side}",
                              f"joint_{code}Tarsus1":f"tarsus_T{tier}_{side}"})
        for f in FRAMES:
            data.qpos[:3]=pos[f]; data.qpos[3:7]=quat[f];
            for name,value in zip(names,joints[f]): data.qpos[model.jnt_qposadr[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,xml_joint[name])]]=value
            mujoco.mj_forward(model,data); calls+=1
        out["evaluation"].update(method="static tree FK plus MuJoCo xpose verification",mj_forward_calls=calls)
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2)+"\n")
    print(f"wrote {a.output}; frames={len(FRAMES)}; mj_step=0; physics transitions=0; MaleCNS updates=0")
if __name__=="__main__": main()
