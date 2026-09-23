"""M9D exporter tests use synthetic states and perform zero scientific transitions."""
import json
import struct
import numpy as np
import pytest
from malecns_backend.embodiment import m9d_replay_export as m9d


def arrays():
    result={}
    for ci,condition in enumerate(m9d.CONDITIONS):
        result[f"{condition}__physics_time_ms"]=np.arange(m9d.STATE_COUNT,dtype="<f8")*.1
        result[f"{condition}__physics_body_position"]=np.full((m9d.STATE_COUNT,3),ci,dtype="<f8")
        q=np.zeros((m9d.STATE_COUNT,4),dtype="<f8"); q[:,0]=1; result[f"{condition}__physics_body_orientation"]=q
        result[f"{condition}__physics_joint_position"]=np.full((m9d.STATE_COUNT,42),ci+.25,dtype="<f8")
    return result


def test_inert_zero_transition_contract_and_exact_joint_order():
    assert m9d.PHYSICS_TRANSITIONS == m9d.NEURAL_TRANSITIONS == 0
    assert len(m9d.JOINT_NAMES)==42
    assert m9d.JOINT_NAMES[:7]==("joint_LFCoxa","joint_LFCoxa_roll","joint_LFCoxa_yaw","joint_LFFemur","joint_LFFemur_roll","joint_LFTibia","joint_LFTarsus1")


def test_four_condition_root_pose_and_endpoint_round_trip():
    source=arrays(); m9d.validate_arrays(source)
    for condition in m9d.CONDITIONS:
        replay=m9d.parse_replay(m9d.serialize_condition(source,condition))
        assert replay["physics_time_ms"].shape==(15001,)
        for field,_ in m9d.FIELDS: assert np.array_equal(replay[field],source[f"{condition}__{field}"])


def test_malformed_shape_nonfinite_count_and_binary_fail_closed():
    source=arrays(); source["A_P__physics_joint_position"]=np.zeros((15001,41),dtype="<f8")
    with pytest.raises(m9d.EvidenceError,match="shape"): m9d.validate_arrays(source)
    source=arrays(); source["B_C__physics_body_position"][1,1]=np.nan
    with pytest.raises(m9d.EvidenceError,match="nonfinite"): m9d.validate_arrays(source)
    good=m9d.serialize_condition(arrays(),"A_P")
    with pytest.raises(m9d.EvidenceError): m9d.parse_replay(good[:-1])
    with pytest.raises(m9d.EvidenceError): m9d.parse_replay(struct.pack("<8sIII",b"WRONG!!!",1,15001,42))


def test_coordinate_conversion_and_force_manifest(monkeypatch,tmp_path):
    # Multiplication by the presentation scale can differ from an independently
    # parsed decimal literal by one binary64 ULP (3 * .1 versus literal .3).
    np.testing.assert_allclose(m9d.flygym_to_unity([1,2,3]),[.1,.3,.2],
                               rtol=0,atol=np.spacing(np.float64(.3)))
    paths=[]
    for condition in m9d.CONDITIONS:
        path=tmp_path/m9d.FILES[condition]; path.write_bytes(m9d.serialize_condition(arrays(),condition)); paths.append(path)
    monkeypatch.setattr(m9d,"_commit",lambda:"abc")
    manifest=m9d.build_manifest(paths)
    assert [x["id"] for x in manifest["conditions"]]==list(m9d.CONDITIONS)
    assert manifest["force"] == {"magnitude_native":1.024,"world_direction_source_xyz":[0,1,0],"unity_direction_xyz":[0,0,1],"target":"authoritative Thorax center of mass","torque_source_xyz":[0,0,0],"start_ms_inclusive":500.0,"stop_ms_exclusive":520.0,"transition_start_inclusive":5000,"transition_stop_exclusive":5200,"first_potentially_affected_state_ms":500.1}
    assert manifest["presentation_interpolation_default"] is False
    assert manifest["physics_transitions"]==manifest["neural_transitions"]==0
    assert manifest["unity_physics_authoritative"] is False


def test_conflicting_output_refused(tmp_path):
    output=tmp_path/"existing"; output.mkdir()
    with pytest.raises(FileExistsError): m9d.export(tmp_path,output)


def test_source_identity_fails_closed_for_lfs_pointer_checkout():
    if m9d.RAW_PATH.stat().st_size == m9d.CANONICAL["m9b_raw.npz"][0]: pytest.skip("canonical LFS object available")
    with pytest.raises(m9d.EvidenceError,match="identity mismatch"): m9d.validate_source()
