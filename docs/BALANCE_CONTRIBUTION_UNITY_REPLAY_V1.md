# Saved balance-contribution review in the existing Unity scene

The adapter `malecns_backend/live/balance_contribution_replay.py` reuses
`tactile_replay.replay_snapshot`, the existing PoseServer and the unchanged
42-coordinate LiveFly wire protocol. No Unity scene, rig, transform conversion,
controller, physics or CNS code is modified. It displays recorded MuJoCo poses.

Eligibility requires a COMPLETE V1.1 four-arm record, exact reconstructed saved
evaluation and unity_replay_eligible=true. Every raw gzip hash, source, identity,
RNG, clock, force, safety and prefix check is performed by the V1.1 evaluator
before clips are exposed. Incomplete/error/invalid evidence is rejected. A valid
null, negative, unqualified baseline or unrecovered behavioral outcome is allowed
and its limitations remain visible; favorable behavior is never a replay gate.

The actual42joint qpos addresses come from each recorded, native-validated model
inventory. Coordinate/action-index order, scalar ranges, uniqueness, complete
20,001-state clock, finite poses and root addresses are checked. There is no
assumption that action index equals qpos index, no remapping by similar names,
no invented targets, and no interpolation or smoothing in this adapter. The
existing Unity presentation mapping remains responsible for its established
coordinate/unit conversion. Root quaternion is passed as native wxyz.

All raw physics states remain intact. The existing newest-pose transport may
downsample display at30Hz; this does not change scientific evidence. Default0.1x
playback stretches the2second recording to20seconds. Switching/looping a clip
returns to saved t=0 and is explicitly logged as a replay reset, not a physical
transition. Tactile is OFF, all42position servos retain the declared assistance,
and only the admitted20-coordinate neural contribution is tested. This is not
independent balance, walking, a new simulation or a new ordinary-live mode.

Prospective adapter validation:16synthetic checks passed1.12s, followed by24
adapter/existing socket-transport checks passed1.51s after preserving complete
behavior-limit labels. Tests cover deliberately permuted actual qpos addresses,
all20001states, unchanged packet semantics, corruption/incomplete rejection,
no display server for failed evidence, valid-null eligibility and full-window
timing. They construct no native body/CNS and are not Unity Editor visual tests.
Real-record verification/eligibility must still be established after the native
assay; consult BALANCE_CONTRIBUTION_PROCESS_RESULTS.md for the actual result.

After user merge and accepted native evidence, Windows Git Bash:

```bash
cd ~/Documents/FlyBrainUnity
git switch newBrain && git pull --no-rebase --no-edit
PY="$HOME/Documents/FlyBrainUnity/.cache/malecns-balance-python312-v1/Scripts/python.exe"
RUN="docs/evidence/balance-contribution-process-v1_1/run-desktop-01"
git lfs pull --include="$RUN/*.json.gz"
"$PY" -m malecns_backend.live.balance_contribution_replay \
  --input "$RUN" --condition PUSHED --speed 0.1
```

Expected only after accepted four-arm integrity: a clearly labelled RECORDED
server at127.0.0.1:8765, looping NP then WP with printed intervention/pulse
markers and full behavioral limitations. `--condition ALL` includes NC and WC;
individual NC/WC/NP/WP clips and `--once` are also available. This command performs
offline verification and display only, never another physics/CNS experiment.

Open the repository's `FlyBrainUnity/` project in Unity (project version
6000.3.10f1), open `Assets/Scenes/LiveFly.unity`, then press Play. The existing
LiveFlyClient should connect to localhost8765 and apply the saved physical poses.
Use the Python console's NC/WC/NP/WP labels to identify clips. If the scene is
absent, the existing menu `FlyBrain/Live Fly/Create Live Fly Scene` creates it;
do not overwrite unsaved user scene edits. Do not start the ordinary live CNS
launcher simultaneously. Ctrl+C stops playback; it does not rerun the assay.

The adapter raises an error and opens no pose stream if evidence is not fully
verified. No partial recording is presented as an accepted balance test. Editor
visual validation must be reported separately from Python/transport checks.

Actual 2026-10-26 verification: full four-arm integrity accepted; all80,004
packets validated with native imports/CNS creation forbidden. The final adapter
and existing transport suite passed24tests in1.66s; console wrapper3tests in0.42s.
Unity6000.3.10f1 entered Play, connected and applied advancing poses with64/64
rig bindings. The default camera crops the upper body; full-body review needs
camera framing. Missing Blender import errors did not prevent this smoke test.
No Unity source/scene edits are part of this delivery. Recorded display is ready;
independent balance remains unproven. See the separate sanitized visual record.
