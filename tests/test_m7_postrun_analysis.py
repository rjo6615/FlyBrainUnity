"""Synthetic-only M7B tests; no scientific runtime is imported or executed."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from malecns_backend.embodiment import m7_postrun_analysis as post
from malecns_backend.embodiment import m7_replay


def fixture(tmp_path: Path, *, p: int = 21, n: int = 5):
    arrays = {}
    shapes = {"physics_time_ms": (p,), "physics_qpos": (p,94), "physics_qvel": (p,93),
        "physics_joint_position": (p,42), "physics_action": (p,42), "physics_ctrl": (p,48),
        "physics_body_position": (p,3), "physics_body_orientation": (p,4),
        "physics_contact_forces": (p,36,3), "physics_finite": (p,), "neural_time_ms": (n,),
        "neural_sensory_encoded": (n,6), "neural_delivered_drive_count": (n,),
        "neural_aggregate_spikes": (n,), "neural_observer_outputs": (n,11),
        "neural_decoder_outputs": (n,11), "neural_admitted_contributions": (n,11)}
    for condition in post.CONDITIONS:
        for field, shape in shapes.items():
            dtype = bool if field == "physics_finite" else (np.int64 if field in ("neural_delivered_drive_count","neural_aggregate_spikes") else np.float64)
            value = np.ones(shape,dtype=dtype) if field == "physics_finite" else np.zeros(shape,dtype=dtype)
            arrays[f"{condition}__{field}"] = value
        arrays[f"{condition}__physics_time_ms"] = np.arange(p,dtype=float)*.1
        arrays[f"{condition}__neural_time_ms"] = np.arange(n,dtype=float)*.5
        arrays[f"{condition}__physics_body_position"][:,2] = 1
        arrays[f"{condition}__physics_body_orientation"][:,0] = 1
    raw=tmp_path/"raw.npz"; np.savez(raw,**arrays); digest=hashlib.sha256(raw.read_bytes()).hexdigest()
    manifest={"schema":"M7-MANIFEST.1","raw_sha256":digest,"seed":1,"duration_ms":5000,
        "conditions":list(post.CONDITIONS),"arrays":{k:{"shape":list(v.shape),"dtype":str(v.dtype)} for k,v in arrays.items()}}
    summary={"schema":"M7-RESULT.1","run_status":"COMPLETE","seed":1,"duration_ms":5000,
        "conditions":list(post.CONDITIONS),"walking":None}
    mp=tmp_path/"manifest.json"; sp=tmp_path/"summary.json"
    mp.write_text(json.dumps(manifest)); sp.write_text(json.dumps(summary))
    return arrays,raw,mp,sp,digest


def validate(paths):
    _,raw,mp,sp,digest=paths
    return post.validate_evidence(raw,mp,sp,expected_sha256=digest,canonical=False)


def test_sha_mismatch_rejected(tmp_path):
    _,raw,mp,sp,_=fixture(tmp_path)
    with pytest.raises(post.EvidenceError,match="SHA256 mismatch"): post.validate_evidence(raw,mp,sp,expected_sha256="0"*64,canonical=False)


def test_manifest_mismatch_rejected(tmp_path):
    x=fixture(tmp_path); data=json.loads(x[2].read_text()); data["seed"]=2; x[2].write_text(json.dumps(data))
    with pytest.raises(post.EvidenceError,match="protocol metadata"): validate(x)


def test_missing_array_rejected(tmp_path):
    x=fixture(tmp_path); data=json.loads(x[2].read_text()); data["arrays"].pop(next(iter(data["arrays"]))); x[2].write_text(json.dumps(data))
    with pytest.raises(post.EvidenceError,match="inventory"): validate(x)


@pytest.mark.parametrize("mutation,match",[("shape","shape mismatch"),("dtype","dtype mismatch")])
def test_wrong_shape_or_dtype_rejected(tmp_path,mutation,match):
    x=fixture(tmp_path); data=json.loads(x[2].read_text()); key=next(iter(data["arrays"])); data["arrays"][key][mutation]=([999] if mutation=="shape" else "float32"); x[2].write_text(json.dumps(data))
    with pytest.raises(post.EvidenceError,match=match): validate(x)


def test_object_array_rejected_without_pickle(tmp_path):
    x=list(fixture(tmp_path)); arrays=np.load(x[1],allow_pickle=False); values={k:arrays[k] for k in arrays.files}; arrays.close()
    key=next(iter(values)); values[key]=np.array([object()],dtype=object); np.savez(x[1],**values); digest=hashlib.sha256(x[1].read_bytes()).hexdigest()
    data=json.loads(x[2].read_text()); data["raw_sha256"]=digest; data["arrays"][key]={"shape":[1],"dtype":"object"}; x[2].write_text(json.dumps(data)); x[4]=digest
    with pytest.raises(post.EvidenceError,match="safely"): validate(x)


def test_nonfinite_and_false_finite_rejected(tmp_path):
    for mode in ("nan","flag"):
        d=tmp_path/mode; d.mkdir(); x=list(fixture(d)); archive=np.load(x[1]); values={k:archive[k] for k in archive.files}; archive.close()
        key=f"{post.CONDITIONS[0]}__physics_qpos" if mode=="nan" else f"{post.CONDITIONS[0]}__physics_finite"
        values[key].flat[0]=np.nan if mode=="nan" else False; np.savez(x[1],**values); digest=hashlib.sha256(x[1].read_bytes()).hexdigest(); data=json.loads(x[2].read_text()); data["raw_sha256"]=digest; x[2].write_text(json.dumps(data)); x[4]=digest
        with pytest.raises(post.EvidenceError): validate(x)


def test_known_divergence_and_activation_timing(tmp_path):
    x=fixture(tmp_path); arrays,_,_,validation=validate(x); e,c=post.CONDITIONS
    arrays[f"{e}__neural_admitted_contributions"][2:,0]=.2
    arrays[f"{e}__neural_observer_outputs"][1:,0]=5
    row=post._divergence("x",arrays[f"{e}__neural_admitted_contributions"],arrays[f"{c}__neural_admitted_contributions"],arrays[f"{e}__neural_time_ms"],None,"intervention")
    assert row["first_exact_inequality_ms"]==1.0
    activation=post._activation(arrays,e); channel=activation["channels"][0]
    assert channel["first_nonzero_observer_ms"]==.5 and channel["first_nonzero_admitted_ms"]==1.0 and channel["activation_episodes"]==1


def test_frozen_fall_rollover_detection(tmp_path):
    x=fixture(tmp_path); arrays,_,_,_=validate(x); e=post.CONDITIONS[0]
    arrays[f"{e}__physics_body_position"][10:,2]=.49
    arrays[f"{e}__physics_body_orientation"][15:,0]=0; arrays[f"{e}__physics_body_orientation"][15:,1]=1
    result=post._fall(arrays,e)
    assert result["fall"]["time_ms"]==1 and result["rollover"]["time_ms"]==1.5


def test_analysis_deterministic_and_compact(tmp_path):
    x=fixture(tmp_path,p=101,n=21); arrays,_,_,validation=validate(x)
    a=post.analyze(arrays,validation,validation["manifest_sha256"],"test")
    b=post.analyze(arrays,validation,validation["manifest_sha256"],"test")
    payload=json.dumps(a,sort_keys=True,allow_nan=False)
    assert payload==json.dumps(b,sort_keys=True,allow_nan=False) and len(payload)<1_000_000


def test_no_simulation_imports_required():
    source=Path(post.__file__).read_text()
    forbidden=("flygym","mujoco","brain.step(","sim.step(","_windows_m7")
    assert not any(word in source.lower() for word in forbidden)
    assert not any(name.startswith(("flygym","mujoco")) for name in sys.modules)


def test_replay_read_only_and_sha_checked(tmp_path):
    x=fixture(tmp_path); before=x[1].read_bytes(); arrays=m7_replay.load_replay(x[1],expected_sha256=x[4])
    assert arrays and x[1].read_bytes()==before
    with pytest.raises(post.EvidenceError): m7_replay.load_replay(x[1],expected_sha256="f"*64)
