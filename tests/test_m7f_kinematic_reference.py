import json
import subprocess
import sys


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
