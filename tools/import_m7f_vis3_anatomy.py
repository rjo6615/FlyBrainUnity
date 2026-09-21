#!/usr/bin/env python3
"""Copy only MJCF-referenced FlyGym meshes and bake the M7F improper basis into OBJ.

This tool is deliberately offline: point --flygym-root at the *same* FlyGym 1.2.1
installation recorded by M7F. It never imports FlyGym or runs MuJoCo.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, struct, xml.etree.ElementTree as ET

EXPECTED_XML_SHA256 = "413b3a1dcb7537d08122e16f256f27ec0d8bb9f52c58670345b6c24c9e72e05a"

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def numbers(text, default): return [float(x) for x in (text or default).split()]
def triangles(path):
    data=path.read_bytes()
    if len(data)>=84 and 84+struct.unpack_from('<I',data,80)[0]*50==len(data):
        n=struct.unpack_from('<I',data,80)[0]
        for i in range(n):
            values=struct.unpack_from('<12fH',data,84+i*50)
            yield tuple(tuple(values[j:j+3]) for j in (3,6,9))
    else:
        verts=[]
        for line in data.decode('ascii',errors='strict').splitlines():
            fields=line.split()
            if fields and fields[0].lower()=='vertex':
                verts.append(tuple(map(float,fields[1:4])))
                if len(verts)==3: yield tuple(verts); verts=[]

def convert_stl(source, destination, mesh_scale):
    # B(x,y,z)=(x,z,y), det(B)=-1. Reverse each face to preserve outward winding.
    factor=[0.1*x for x in mesh_scale]
    with destination.open('w',newline='\n') as out:
        out.write('# FlyGym 1.2.1 STL; B(x,y,z)=(x,z,y); winding reversed\n')
        index=1
        for tri in triangles(source):
            mapped=[]
            for x,y,z in tri: mapped.append((x*factor[0],z*factor[2],y*factor[1]))
            for v in mapped: out.write('v %.9g %.9g %.9g\n'%v)
            out.write(f'f {index} {index+2} {index+1}\n'); index+=3

def walk_bodies(node,parent,out,mesh_defs,defaults):
    name=node.get('name',parent)
    for geom in node.findall('geom'):
        mesh=geom.get('mesh')
        if not mesh: continue
        cls=geom.get('class','')
        contype=geom.get('contype',defaults.get(cls,{}).get('contype','1'))
        conaff=geom.get('conaffinity',defaults.get(cls,{}).get('conaffinity','1'))
        group=geom.get('group',defaults.get(cls,{}).get('group','0'))
        collision=contype!='0' or conaff!='0'; visual=group!='3'
        out.append({'mesh_name':mesh,'source_stl':mesh_defs[mesh]['file'],'body':name,
          'scientific_body':name if name=='Thorax' or name.endswith(('Coxa','Femur','Tibia','Tarsus1')) else 'Thorax',
          'mesh_scale':mesh_defs[mesh]['scale'],'position':numbers(geom.get('pos'),'0 0 0'),
          'quaternion_wxyz':numbers(geom.get('quat'),'1 0 0 0'),'role':'both' if collision and visual else ('collision' if collision else 'visual')})
    for child in node.findall('body'): walk_bodies(child,name,out,mesh_defs,defaults)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--flygym-root',type=pathlib.Path,required=True); p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('FlyBrainUnity/Assets/StreamingAssets/M7FAnatomy')); a=p.parse_args()
    xml=a.flygym_root/'data/mjcf/neuromechfly_seqik_kinorder_ypr.xml'
    if sha(xml)!=EXPECTED_XML_SHA256: raise SystemExit(f'wrong authoritative MJCF: {sha(xml)}')
    root=ET.parse(xml).getroot(); meshdir=root.find('compiler').get('meshdir','../mesh'); meshbase=(xml.parent/meshdir).resolve()
    meshes={m.get('name'):{'file':m.get('file'),'scale':numbers(m.get('scale'),'1 1 1')} for m in root.findall('./asset/mesh')}
    defaults={}
    for d in root.findall('.//default'):
        g=d.find('geom')
        if d.get('class') and g is not None: defaults[d.get('class')]=g.attrib
    records=[]
    for body in root.findall('./worldbody/body'): walk_bodies(body,'',records,meshes,defaults)
    required=sorted({r['mesh_name'] for r in records}); a.output.mkdir(parents=True,exist_ok=True)
    for name in required:
        info=meshes[name]; source=meshbase/info['file']; convert_stl(source,a.output/(name+'.obj'),info['scale']); info['sha256']=sha(source)
    manifest={'schema':'M7F-VIS3-ANATOMY.1','flygym_version':'1.2.1','mjcf':'neuromechfly_seqik_kinorder_ypr.xml','mjcf_sha256':sha(xml),'basis':'[x,y,z] -> [x,z,y]','presentation_scale':0.1,'meshes':records}
    (a.output/'m7f_vis3_anatomy.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'wrote {len(required)} meshes and {len(records)} placements to {a.output}')
if __name__=='__main__': main()
