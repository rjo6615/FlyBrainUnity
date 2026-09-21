"""M8 data-layer adapter for the validated M7F Unity replay binary schema."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
from . import m8_extended_spontaneous as m8
from . import m7f_canonical_replay as m7f


def _sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def export(raw_path=m8.RAW_PATH, source_manifest=m8.MANIFEST_PATH, output_manifest=m8.REPLAY_MANIFEST_PATH):
    source=json.loads(Path(source_manifest).read_text())
    if source.get('raw',{}).get('sha256') != _sha(raw_path): raise RuntimeError('M8 raw identity mismatch')
    with np.load(raw_path,allow_pickle=False) as z: arrays={k:z[k].copy() for k in z.files}
    artifacts=[]
    for condition,name in zip(m8.CONDITIONS,("m8_enabled_replay.bin","m8_disabled_replay.bin")):
        data=m7f.serialize_condition(arrays,condition); path=Path(output_manifest).with_name(name)
        with path.open('xb') as f: f.write(data)
        artifacts.append({"path":path.name,"byte_size":len(data),"sha256":_sha(path)})
    value={"schema":"M8-UNITY-REPLAY-EXPORT.1","status":"COMPLETE","source_raw_sha256":_sha(raw_path),"consumer":"existing validated M7F Unity replay loader","scientific_rig_changed":False,"vis3_anatomy_changed":False,"physics_frames":m8.EXPECTED_PHYSICS_STATES,"neural_frames":m8.EXPECTED_NEURAL_UPDATES,"cadence_ms":{"physics":.1,"neural":.5},"artifacts":artifacts,"contact_and_foot_telemetry":"retained in raw M8 archive; replay binary remains backward-compatible"}
    Path(output_manifest).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n'); return value
