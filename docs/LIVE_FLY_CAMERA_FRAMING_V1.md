# Full-body review of the accepted balance recording

2026-10-26. PR288 is merged into newBrain at7e14bc0. Its accepted four-arm
experiment and frozen implementation/specifications remain unchanged. The
new editor menu `FlyBrain/Live Fly/Frame Current Fly` fits the current active
fly renderer bounds in the Main Camera, including portrait Game views. It then
holds a fixed world view so translation and tilt remain visible. Invoke it after
the first recorded pose arrives. It can also frame a continuous live pose.

The command changes only the camera and its presentation settings. It does not
regenerate/save the scene, move the rig, alter received poses, rerun physics/CNS,
or change the scientific controls. Outside Play, it records Undo and marks the
scene dirty; the user chooses whether to save. During Play, framing is temporary.
There must be exactly one active LiveFlyClient and a tagged Main Camera with
M7FReplayCamera. Missing rig/renderers produce a warning. Framing covers the
current pose with15% margin, not an unlimited future trajectory: frame again if
the fly leaves view or the Game-view aspect ratio changes. The F key retains
the existing fixed/orbit toggle.

## Desktop Git Bash

After merging this PR, with Unity closed during the pull:

```bash
cd "$HOME/Documents/FlyBrainUnity" &&
git switch newBrain &&
git pull --no-rebase --no-edit &&
PY="$HOME/Documents/FlyBrainUnity/fly-brain-interactive/.venv/Scripts/python.exe" &&
RUN="docs/evidence/balance-contribution-process-v1_1/run-desktop-01" &&
git lfs pull --include="$RUN/*.json.gz" &&
"$PY" -m pytest -q -p no:cacheprovider \
  tests/test_balance_contribution_replay.py \
  tests/test_live_pose_transport.py \
  tests/test_balance_contribution_console.py &&
"$PY" -m malecns_backend.live.balance_contribution_replay \
  --input "$RUN" --condition PUSHED --speed 0.1
```

Expected:27tests pass, then accepted saved NP/WP clips stream to localhost8765.
Open FlyBrainUnity/ in Unity6000.3.10f1, open Assets/Scenes/LiveFly.unity, press
Play, wait for advancing received poses, then select
`FlyBrain > Live Fly > Frame Current Fly`. Check that head, abdomen and all feet
are visible. Watch the fixed view for displacement, tipping and foot contacts;
clip resets are replay boundaries, not physical jumps. Ctrl+C stops replay.
Do not launch the ordinary continuous live server on the same port simultaneously.

## Roadmap and limits

Design, implementation, real four-arm recording, integrity acceptance and Unity
connection are complete. Full-body visual review is the current gate. The recorded
label remains MIXED_OR_UNRESOLVED: enabled neural output lowers mean tilt but
does not consistently improve the declared measures. The experiment has one seed,
two seconds per arm and position assistance on all42actuators; neural motor
coverage is20/42, with no new admissions. Stability alone does not prove
independent neural balance or walking.

Next after visual review: predeclare a separately versioned controlled live
balance experiment using the existing kernel,20motor authority and transport,
with explicit disturbance schedule, assistance, recording, matched controls,
integrity/behavior criteria and stop policy. A continuous live viewer already
exists; it is not equivalent to that causal experiment. Testing reduced
mechanical assistance is a separate prospective scientific question. Do not
tune assistance, neural parameters or acceptance against observed outcomes.

## Validation

Replay/transport/console regression:27passed in2.93s on the desktop Python3.12.10,
NumPy2.0.2 environment. Initial sandbox attempt:20passed,3socket-permission
failures and4temporary-directory setup errors; unchanged suite passed with
required OS access. These checks construct no native body/CNS experiment.
Unity6000.3.10f1 EditMode:6passed in2.30s, exit0. Includes landscape/portrait
perspective and portrait orthographic full-bounds framing, fixed-world reference,
unchanged target transforms, empty-geometry refusal and existing scene/rig checks.
Initial run:2passed/4failed because SendMessage("LateUpdate") asserts
ShouldRunBehaviour in EditMode, including the existing orbit/fixed test. Tests
now directly invoke the same private callback via reflection; runtime lifecycle
and assertions are unchanged. Initial/final XML and private editor logs remain
in the isolated worktree's .cache/camera-framing/, not in scientific evidence.
An accidental second launcher exited1 while the original project import was
still running; it ran no tests. The final isolated run exited0.
Scene-building tests regenerated their isolated scene; that generated scene,
import changes and hydrated historical replay files are excluded from the PR.
No manual Unity visual review or new physics/CNS experiment occurred here.

To repeat the Unity regressions in Git Bash (Unity must be closed; the existing
scene-building test regenerates LiveFly.unity, so use an isolated checkout):

```bash
"/c/Program Files/Unity/Hub/Editor/6000.3.10f1/Editor/Unity.exe" \
  -batchmode -nographics -projectPath "$PWD/FlyBrainUnity" \
  -runTests -testPlatform EditMode -testFilter LiveFlySceneGenerationTests \
  -testResults "$PWD/camera-tests.xml" -logFile "$PWD/camera-tests.log"
```

Changed files: M7FReplayCamera.cs (bounds fit), LiveFlySceneGenerator.cs (editor
menu), LiveFlySceneGenerationTests.cs (camera regressions/EditMode invocation),
this guide, PROJECT_HANDOFF.md and UNITY_AND_BALANCE_ROADMAP.md (current status).
