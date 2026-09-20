import json
import importlib.util
import subprocess
import sys
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


def test_checked_in_reference_matches_generator(tmp_path):
    output = tmp_path / "reference.json"
    subprocess.run([sys.executable, "tools/generate_m7f_kinematic_reference.py", "--output", str(output)], check=True)
    assert output.read_bytes() == open("FlyBrainUnity/Assets/StreamingAssets/M7FValidation/m7f_frame0_kinematic_reference.json", "rb").read()


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
