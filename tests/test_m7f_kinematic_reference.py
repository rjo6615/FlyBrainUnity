import json
import importlib.util
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location("m7f_kinematics", "tools/generate_m7f_kinematic_reference.py")
generator = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(generator)


def test_static_kinematic_reference_is_deterministic_and_transition_free(tmp_path):
    output = tmp_path / "reference.json"
    subprocess.run([sys.executable, "tools/generate_m7f_kinematic_reference.py", "--output", str(output)], check=True)
    actual = json.loads(output.read_text())
    assert [x["frame"] for x in actual["frames"]] == [0, 540, 541, 785, 1210, 1570, 2500, 3980, 5000]
    assert all(len(x["segments"]) == 24 for x in actual["frames"])
    assert all(sum(len(s["joints"]) for s in x["segments"]) == 42 for x in actual["frames"])
    assert actual["evaluation"] == {
        "method": "deterministic static MJCF tree forward kinematics",
        "mj_forward_calls": 0, "mj_step_calls": 0, "physics_transitions": 0, "MaleCNS_updates": 0,
    }


def test_vis1b_reference_is_archived_as_invalid_not_authoritative(tmp_path):
    output = tmp_path / "reference.json"
    subprocess.run([sys.executable, "tools/generate_m7f_kinematic_reference.py", "--output", str(output)], check=True)
    generated = json.loads(output.read_text())
    archived = json.loads(Path("FlyBrainUnity/Assets/StreamingAssets/M7FValidation/m7f_vis1b_invalid_reference.json").read_text())
    # Windows and POSIX serialize the two provenance paths with different separators.
    assert generated["frames"] == archived["frames"]
    assert generated["evaluation"] == archived["evaluation"]
    assert not Path("FlyBrainUnity/Assets/StreamingAssets/M7FValidation/m7f_frame0_kinematic_reference.json").exists()


def test_vis2_artifacts_are_deterministic_and_complete(tmp_path):
    rig = tmp_path / "rig.json"; reference = tmp_path / "reference.json"
    subprocess.run([sys.executable, "tools/build_m7f_vis2_artifacts.py", "--rig-output", str(rig),
                    "--reference-output", str(reference)], check=True)
    checked_rig = Path("FlyBrainUnity/Assets/StreamingAssets/M7FValidation/m7f_authoritative_rig.json")
    checked_reference = Path("FlyBrainUnity/Assets/StreamingAssets/M7FValidation/m7f_mujoco_reference_frames.json")
    assert rig.read_bytes() == checked_rig.read_bytes()
    assert reference.read_bytes() == checked_reference.read_bytes()
    rig_data = json.loads(rig.read_text()); native = json.loads(reference.read_text())
    assert len(rig_data["bodies"]) == 24
    assert rig_data["root_body"]["name"] == "Thorax"
    joints = [joint for body in rig_data["bodies"] for joint in body["joints"]]
    assert len(joints) == len({joint["name"] for joint in joints}) == 42
    assert len({joint["mj_qpos_address"] for joint in joints}) == 42
    assert [frame["frame"] for frame in native["frames"]] == list(generator.FRAMES)
    assert native["counters"] == {"mj_forward_calls": 9, "mj_step_calls": 0,
                                   "physics_transitions": 0, "neural_transitions": 0}


def test_authoritative_contract_matches_frozen_m7d_provenance():
    manifest = json.loads(Path("FlyBrainUnity/Assets/StreamingAssets/M7FReplay/m7f_manifest.json").read_text())
    assert tuple(manifest["joint_names"]) == generator.EXPECTED_JOINTS
    assert generator.FLYGYM_VERSION == "1.2.1"
    assert generator.MUJOCO_VERSION == "3.2.7"
    assert generator.FLYGYM_MJCF == "neuromechfly_seqik_kinorder_ypr.xml"


def test_verify_fails_closed_before_writing_crosscheck_without_dependencies(tmp_path):
    output = tmp_path / "reference.json"
    crosscheck = tmp_path / "crosscheck.json"
    completed = subprocess.run([sys.executable, "tools/generate_m7f_kinematic_reference.py",
        "--output", str(output), "--verify-mujoco", "--crosscheck-output", str(crosscheck)],
        capture_output=True, text=True)
    assert completed.returncode != 0
    assert not crosscheck.exists()
    assert "flygym" in (completed.stdout + completed.stderr).lower()


@pytest.mark.parametrize(("left", "right", "expected"), [
    ([1, 2, 3], [1, 2, 3], "EXACT_MATCH"),
    ([1, 2, 3], [1.0, 2.0, 3.0], "EXACT_MATCH"),
    ([1, 2, 3], [1, 2, 3 + 5e-13], "NUMERICALLY_EQUIVALENT"),
    ([1, 2, 3], [1, 2, 4], "DIFFERENT"),
    (None, [1, 2, 3], "MISSING"),
])
def test_model_field_classification(left, right, expected):
    assert generator._classification(left, right) == expected


def _mapping_fixture(*, names=("joint_A", "joint_B"), qaddrs=(9, 7), types=(3, 3)):
    mujoco = SimpleNamespace(
        mjtObj=SimpleNamespace(mjOBJ_JOINT=0, mjOBJ_BODY=1),
        mjtJoint=SimpleNamespace(mjJNT_HINGE=3),
        mj_id2name=lambda model, kind, index: model.joint_names[index] if kind == 0 else model.body_names[index],
    )
    model = SimpleNamespace(njnt=len(names), joint_names=list(names), body_names=["body_A", "body_B"],
        jnt_qposadr=list(qaddrs), jnt_type=list(types), jnt_bodyid=[0, 1])
    return mujoco, model


def test_unique_name_mapping_need_not_match_global_qpos_order():
    mujoco, model = _mapping_fixture()
    rows = generator._joint_mapping(mujoco, model, ("joint_A", "joint_B"),
                                    recorder_semantics_verified=True)
    assert [row["mj_qpos_address"] for row in rows] == [9, 7]
    assert [row["canonical_name"] for row in sorted(rows, key=lambda row: row["mj_qpos_address"])] == ["joint_B", "joint_A"]


def test_joint_mapping_rejects_missing_name():
    mujoco, model = _mapping_fixture()
    with pytest.raises(RuntimeError, match="maps .* 0 times"):
        generator._joint_mapping(mujoco, model, ("joint_A", "joint_missing"), recorder_semantics_verified=True)


def test_joint_mapping_rejects_duplicate_name():
    mujoco, model = _mapping_fixture()
    with pytest.raises(RuntimeError, match="duplicate"):
        generator._joint_mapping(mujoco, model, ("joint_A", "joint_A"), recorder_semantics_verified=True)


def test_joint_mapping_rejects_duplicate_qpos_address():
    mujoco, model = _mapping_fixture(qaddrs=(7, 7))
    with pytest.raises(RuntimeError, match="same MuJoCo qpos"):
        generator._joint_mapping(mujoco, model, ("joint_A", "joint_B"), recorder_semantics_verified=True)


def test_joint_mapping_rejects_non_scalar_joint():
    mujoco, model = _mapping_fixture(types=(3, 2))
    with pytest.raises(RuntimeError, match="not a scalar hinge"):
        generator._joint_mapping(mujoco, model, ("joint_A", "joint_B"), recorder_semantics_verified=True)


def test_joint_mapping_rejects_unverified_recorder_semantics():
    mujoco, model = _mapping_fixture()
    with pytest.raises(RuntimeError, match="semantics are unverified"):
        generator._joint_mapping(mujoco, model, ("joint_A", "joint_B"), recorder_semantics_verified=False)
