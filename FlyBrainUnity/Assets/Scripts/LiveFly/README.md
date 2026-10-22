# Live Fly Phase 4 Unity viewer

`LiveFlyClient` is an output-only presentation client for `live_fly_pose` v1. It
does not launch or control Python and sends no data. Python/MuJoCo remains the
authority for time, physics, neural execution, body pose, and all 42 joint
positions.

## Component setup

1. Use the existing M7F workflow to create an authoritative M7F fly, or add
   `M7FScientificFlyBuilder` to a GameObject and invoke **Rebuild**.
2. Add `LiveFlyClient` to a scene GameObject and assign that fly's `M7FFlyRig`.
3. Keep host `127.0.0.1`, port `8765`, **Connect On Start** enabled, and
   **Presentation Interpolation** disabled for direct/latest-pose validation.
4. Do not run an M7F replay controller against the same rig.

The Inspector exposes state, session ID, last sequence/simulation time, received
poses, and replaced poses. Connection and JSON work runs on a task. `Update`
alone converts and applies the newest capacity-one pose to Unity transforms.
The runtime overlay separately reports TCP connection, hello receipt and
acceptance, raw and pose lines, accepted/rejected poses, slot consumption, rig
application, and the last background transport/parser/validation error.

The legacy `UnityFlyBridge` is deliberately not auto-installed when a
`LiveFlyClient` exists. The Python Live Fly publisher is single-client; allowing
the legacy `fly_state` client to connect first would consume and ignore the v1
hello/pose stream while the real client remained connected only at the TCP
backlog and waited forever for a hello.

## Coordinates

This viewer deliberately reuses the validated M7F import convention rather than
introducing another model basis. The polar basis is
`B(x,y,z) = (x,z,y)`, and the established M7F presentation scale is
`1 source mm = 0.1 Unity unit`. Since `det(B) = -1`, source axial joint axes use
`det(B) B`; the existing rig already stores those converted local axes. For a
source rotation matrix `R_s`, root orientation is `R_u = B R_s B^-1`.
`M7FCoordinates.SourceQuaternionToUnity` implements this by converting the
rotated source forward/up vectors and reconstructing the proper Unity rotation.
The wire quaternion is explicitly decoded from `[w,x,y,z]` before conversion.

## Manual acceptance

1. In a terminal run `python -m malecns_backend.live` and wait for initialization.
2. Press Play in Unity. Confirm status becomes **Receiving** and note session ID,
   sequence, and simulation time.
3. Observe authoritative live body/articulated motion for at least 30 wall seconds.
4. Stop Unity; verify Python continues advancing.
5. Press Play again; verify the same session ID and a later simulation time.
6. Stop Unity, then press Ctrl+C in the terminal and confirm Python shuts down.

Unity Stop only cancels/closes its TCP client. It never terminates or resets the
manually managed Python process.

## Motor interface selection

The terminal launcher defaults to the original 11-channel v1 session. Select an
expanded inventory explicitly from the repository root:

```sh
python -m malecns_backend.live --motor-interface v2
python -m malecns_backend.live --motor-interface v3
```

v2 admits 17 motor channels; v3 admits 20, including `joint_RFFemur`,
`joint_LFTarsus1`, and `joint_RFTarsus1`. All versions retain the six tibia
proprioceptive sensory inputs. Admission does not guarantee nonzero neural
output or visible movement. The startup line reports the selected inventory.
Only run one publisher at a time on port 8765.

### Manual checks for interface selection

1. Run `python -m malecns_backend.live --help`; expect v1/v2/v3 choices and exit.
2. Run `python -m malecns_backend.live --motor-interface v4`; expect an argument
   error and no session or pose server started.
3. Run the command without options; expect `motor_interface=v1 motor_channels=11
   sensory_channels=6`. Stop with Ctrl+C after initialization.
4. Run with `--motor-interface v2`; expect 17 motor channels and six sensory
   channels. Stop it before the next check.
5. Run with `--motor-interface v3`; expect 20 motor channels and six sensory
   channels. Wait for initialization, then press Play in the Unity Live Fly scene.
   Expect **Receiving**, advancing simulation time, and no transport errors.
6. Observe the terminal motor contributions for the three candidate joints.
   Record any nonzero contributions; if absent, record the simulated observation
   duration. Absence alone does not prove a mechanical failure.
7. Stop and restart Unity; expect the same Python session ID and later simulation
   time. Stop Unity and Ctrl+C Python; expect normal shutdown.
