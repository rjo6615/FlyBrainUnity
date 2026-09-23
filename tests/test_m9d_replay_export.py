"""M9D exporter tests use synthetic states and perform zero scientific transitions."""
import hashlib
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


def source_files(tmp_path, monkeypatch):
    documents = {
        "m9b_manifest.json": {
            "status": "COMPLETE",
            "raw": {"byte_size": 3, "sha256": hashlib.sha256(b"raw").hexdigest()},
            "report": {"byte_size": 316, "sha256": "7299c349d5824fb9d5ef7713bf7ea5e9794972f3669790502609dfa5a3e8224e"},
        },
        "m9b_preregistration.json": {"design": {"conditions": list(m9d.CONDITIONS)}},
        "m9b_report.json": {"status": "COMPLETE_UNCLASSIFIED"},
    }
    canonical = {"m9b_raw.npz": (3, hashlib.sha256(b"raw").hexdigest())}
    (tmp_path / "m9b_raw.npz").write_bytes(b"raw")
    for name, document in documents.items():
        data = (json.dumps(document, indent=2) + "\n").encode()
        (tmp_path / name).write_bytes(data)
        canonical[name] = (len(data), hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(m9d, "CANONICAL", canonical)
    return canonical


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
    assert manifest["canonical_m9b_sources"]["m9b_report.json"]["identity_semantics"] == "canonical_lf_after_crlf_normalization"
    assert manifest["published_m9b_report_identity"] == {
        "identity_semantics": "exact_bytes_of_m9b_windows_publication",
        **m9d.PUBLISHED_WINDOWS_REPORT,
    }


def test_conflicting_output_refused(tmp_path):
    output=tmp_path/"existing"; output.mkdir()
    with pytest.raises(FileExistsError): m9d.export(tmp_path,output)


def test_source_identity_fails_closed_for_lfs_pointer_checkout():
    if m9d.RAW_PATH.stat().st_size == m9d.CANONICAL["m9b_raw.npz"][0]: pytest.skip("canonical LFS object available")
    with pytest.raises(m9d.EvidenceError,match="identity mismatch"): m9d.validate_source()


@pytest.mark.parametrize("newlines", [b"\n", b"\r\n"])
def test_json_sources_accept_lf_and_exact_crlf_without_modification(tmp_path, monkeypatch, newlines):
    canonical = source_files(tmp_path, monkeypatch)
    before = {}
    for name in canonical:
        path = tmp_path / name
        if name.endswith(".json") and newlines == b"\r\n":
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        before[name] = path.read_bytes()

    validated = m9d.validate_source(tmp_path)

    assert all((tmp_path / name).read_bytes() == data for name, data in before.items())
    for name in canonical:
        provenance = validated["source_provenance"][name]
        if name.endswith(".json"):
            assert provenance["identity_semantics"] == "canonical_lf_after_crlf_normalization"
            assert provenance["canonical_lf_identity"]["sha256"] == canonical[name][1]
            assert provenance["working_tree_identity"] == m9d._identity(before[name])
        else:
            assert provenance["identity_semantics"] == "exact_bytes"


@pytest.mark.parametrize("damage", ["mixed", "lone_cr", "content"])
def test_json_newline_corruption_and_content_mutation_fail_closed(tmp_path, monkeypatch, damage):
    source_files(tmp_path, monkeypatch)
    path = tmp_path / "m9b_preregistration.json"
    data = path.read_bytes()
    if damage == "mixed":
        first = data.index(b"\n")
        data = data[:first] + b"\r\n" + data[first + 1:]
    elif damage == "lone_cr":
        data = data.replace(b"\n", b"\r", 1)
    else:
        data = data.replace(b'"design"', b'"damage"', 1)
    path.write_bytes(data)

    with pytest.raises(m9d.EvidenceError):
        m9d.validate_source(tmp_path)


def test_binary_source_remains_exact_bytes_and_failed_validation_publishes_nothing(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_files(source_dir, monkeypatch)
    (source_dir / "m9b_raw.npz").write_bytes(b"raW")
    output = tmp_path / "publication" / "m9d_unity_replay"

    with pytest.raises(m9d.EvidenceError, match="identity mismatch"):
        m9d.export(source_dir, output)

    assert not output.exists()
    assert not output.parent.exists()
    assert not list(tmp_path.glob("**/.m9d.tmp-*"))
