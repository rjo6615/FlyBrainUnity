"""Synthetic-only tests for M7E; canonical M7D raw evidence is never opened."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from malecns_backend.embodiment import m7e_postrun_analysis as m


def fixture(tmp_path: Path, *, bad_shape=False, nonfinite=False, object_array=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    pc, nc = 51, 10
    pt = np.arange(pc, dtype=float) * .1
    nt = pt[5::5]
    arrays = {}
    for ci, condition in enumerate(m.CONDITIONS):
        for field, tail in m.PHYSICS_FIELDS.items():
            dtype = bool if field == "physics_finite" else float
            value = np.ones((pc, *tail), dtype=dtype) if field == "physics_finite" else np.zeros((pc, *tail), dtype=dtype)
            if field == "physics_time_ms": value = pt.copy()
            if field == "physics_body_position": value[:, 0] = pt / 1000
            if field == "physics_body_orientation": value[:, 0] = 1
            arrays[f"{condition}__{field}"] = value
        for field, tail in m.NEURAL_FIELDS.items():
            dtype = int if field in {"neural_delivered_drive_count", "neural_aggregate_spikes"} else float
            value = np.zeros((nc, *tail), dtype=dtype)
            if field == "neural_time_ms": value = nt.copy()
            arrays[f"{condition}__{field}"] = value
    a = m.CONDITIONS[0]
    arrays[f"{a}__physics_joint_position"][20:, m.JOINT_INDEX["joint_LFTibia"]] = .2
    arrays[f"{a}__physics_action"][20:, m.JOINT_INDEX["joint_LFTibia"]] = .2
    arrays[f"{a}__physics_qpos"][20:, 0] = .2
    arrays[f"{a}__neural_admitted_contributions"][3:, 0] = .1
    arrays[f"{a}__neural_decoder_outputs"][3:, 0] = .1
    arrays[f"{a}__neural_sensory_encoded"][5:, 0] = .3
    arrays[f"{a}__neural_delivered_drive_count"][5:] = 1
    arrays[f"{a}__neural_aggregate_spikes"][5:] = 1
    if bad_shape: arrays[f"{a}__physics_joint_position"] = arrays[f"{a}__physics_joint_position"][:, :-1]
    if nonfinite: arrays[f"{a}__physics_qpos"][0, 0] = np.nan
    if object_array: arrays[f"{a}__physics_qpos"] = np.array([[object()]], dtype=object)
    raw = tmp_path / "raw.npz"; np.savez_compressed(raw, **arrays)
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    inventory = {key: {"shape": list(value.shape), "dtype": str(value.dtype)} for key, value in arrays.items()}
    manifest = {"status":"COMPLETE", "schema":"M7D-CORRECTED-SPONTANEOUS.1",
                "source_commit":"synthetic", "raw":{"byte_size":raw.stat().st_size,"sha256":digest}, "arrays":inventory}
    body = {}
    for condition in m.CONDITIONS:
        pos = arrays[f"{condition}__physics_body_position"]
        body[condition] = {"body_path_length":float(np.linalg.norm(np.diff(pos,axis=0),axis=1).sum()),
            "net_body_displacement":(pos[-1]-pos[0]).tolist(), "minimum_body_height":0., "minimum_body_up_z":1.}
    summary = {"status":"COMPLETE", "schema":"M7D-CORRECTED-SPONTANEOUS.1",
        "raw_telemetry":{"sha256":digest}, "physics_states_per_condition":pc,
        "neural_updates_per_condition":nc, "condition_completion":dict.fromkeys(m.CONDITIONS, True),
        "per_condition":body, "causal_milestones":{}}
    mp, sp = tmp_path/"manifest.json", tmp_path/"summary.json"
    mp.write_text(json.dumps(manifest)); sp.write_text(json.dumps(summary))
    return raw, mp, sp, digest, arrays, summary


def load_synthetic(paths):
    raw, manifest, summary, digest, *_ = paths
    return m.validate_evidence(raw, manifest, summary, expected_sha256=digest,
                               expected_size=raw.stat().st_size, physics_count=51,
                               neural_count=10, canonical=False)


def test_provenance_wrong_hash_and_status_rejected(tmp_path):
    paths = fixture(tmp_path)
    with pytest.raises(m.EvidenceError, match="SHA-256 mismatch"):
        m.validate_evidence(paths[0], paths[1], paths[2], expected_sha256="0"*64,
                            expected_size=paths[0].stat().st_size, canonical=False)
    value=json.loads(paths[1].read_text()); value["status"]="INCOMPLETE"; paths[1].write_text(json.dumps(value))
    with pytest.raises(m.EvidenceError, match="status COMPLETE"):
        load_synthetic(paths)


def test_missing_array_shape_nonfinite_and_pickle_rejected(tmp_path):
    paths=fixture(tmp_path/"ok"); arrays=paths[4]; arrays.pop(next(iter(arrays)))
    np.savez_compressed(paths[0], **arrays)
    digest=hashlib.sha256(paths[0].read_bytes()).hexdigest()
    with pytest.raises(m.EvidenceError, match="SHA-256|inventory"):
        m.validate_evidence(paths[0],paths[1],paths[2],expected_sha256=digest,expected_size=paths[0].stat().st_size,physics_count=51,neural_count=10,canonical=False)
    for name, kwargs, match in (("shape",{"bad_shape":True},"shape/dtype"),("nan",{"nonfinite":True},"nonfinite"),("object",{"object_array":True},"allow_pickle=False")):
        p=fixture(tmp_path/name,**kwargs)
        with pytest.raises(m.EvidenceError, match=match): load_synthetic(p)


def test_ab_body_joint_neural_and_sensory_metrics(tmp_path):
    paths=fixture(tmp_path); arrays,_,summary,_=load_synthetic(paths); result=m.analyze_arrays(arrays,summary)
    tibia=result["joints"]["admitted_neural_joints"]["joint_LFTibia"]
    assert tibia["difference"]["first_meaningful_divergence_ms"] == 2.0
    assert result["joints"]["all_42"][m.CONDITIONS[0]]["joint_LFTibia"]["total_variation"] == pytest.approx(.2)
    assert result["body"][m.CONDITIONS[0]]["horizontal_displacement_magnitude"] == pytest.approx(.005)
    assert result["neural_motor"][m.CONDITIONS[0]]["joint_LFTibia"]["admitted_contributions"]["first_meaningful_ms"] == 2.0
    assert result["sensory"]["joint_LFTibia"]["first_meaningful_divergence_ms"] == 3.0
    assert result["physics_transitions"] == result["neural_transitions"] == 0


def test_periodicity_transient_constant_and_known_frequency():
    t=np.arange(0,1000,.5); sinusoid=np.sin(2*np.pi*8*t/1000)
    periodic=m.periodicity_metrics(sinusoid,t)
    assert periodic["dominant_non_dc_frequency_hz"] == pytest.approx(8)
    assert periodic["label"] == "OSCILLATORY_CANDIDATE"
    transient=np.zeros_like(t); transient[100:110]=1
    assert m.periodicity_metrics(transient,t)["label"] != "OSCILLATORY_CANDIDATE"
    assert m.periodicity_metrics(np.ones_like(t),t)["label"] == "NO_REPEATED_STRUCTURE"


def test_cross_correlation_known_lag_and_constant():
    x=np.zeros(100); x[20:25]=1; y=np.roll(x,7)
    result=m.cross_correlation(x,y,.5)
    assert abs(result["lag_at_maximum_ms"]) == 3.5
    assert m.cross_correlation(np.ones(10),np.ones(10),.5)["maximum_normalized_correlation"] is None


def test_summary_consistency_and_overwrite_protection(tmp_path):
    paths=fixture(tmp_path/"data"); arrays,_,summary,_=load_synthetic(paths)
    result=m.analyze_arrays(arrays,summary)
    assert all(x["status"] == "PASS" for x in result["summary_consistency"].values())
    out=tmp_path/"out"; out.mkdir(); (out/"m7e_analysis.json").write_text('{"status":"COMPLETE"}')
    assert not m.output_available(out)


def test_static_no_simulation_dependencies():
    source=Path(m.__file__).read_text()
    forbidden=("import flygym", "import mujoco", "from .neural", "_windows_m7d", "m7_spontaneous_locomotion")
    assert not any(token in source for token in forbidden)
    assert m.JOINT_NAMES[m.JOINT_INDEX["joint_LFTibia"]] == "joint_LFTibia"
