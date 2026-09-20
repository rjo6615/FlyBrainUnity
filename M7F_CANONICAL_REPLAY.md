# M7F canonical M7D replay

## Scientific purpose and provenance

M7F is a read-only reconstruction and presentation layer for the already
completed **M7D corrected spontaneous experiment**. It is not a new experiment.
Its canonical input is the local-only `m7d_raw.npz` of exactly 16,737,088 bytes
and SHA-256
`92b5c645a88fe74e5d6aa0988478c374e8fde3a0e923d42cc13974a3e60d8444`.
Both the M7D summary and manifest, and the M7E manifest and analysis, must say
`COMPLETE`; all recorded numeric arrays must be finite and have their frozen
shape and dtype. NumPy is always invoked with `allow_pickle=False`.

M7F imports no FlyGym, MuJoCo, MaleCNS runtime, or experiment runner. Preflight
and export perform **zero physics transitions and zero neural transitions**.
They only authenticate files, copy recorded values into a deterministic binary,
and import annotations from completed M7D/M7E evidence. M7D and M7E artifacts
are not modified or recomputed.

The canonical NPZ is ignored by Git and must remain local. No canonical replay
binary or completed manifest is included in this change: those are created only
after the user runs the Windows exporter.

## Commands

Run preflight first from the repository root:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7f_canonical_replay --windows-preflight
```

Expected terminal declaration ends in `EXPORT NOT RUN`. Only after reviewing
preflight, the future export command is:

```powershell
# DO NOT RUN YET: first run and review preflight.
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.m7f_canonical_replay --export-windows
```

Export refuses to overwrite either replay binary or a manifest whose status is
`CANONICAL_REPLAY_EXPORT_COMPLETE`.

## Binary replay format

Each condition has one little-endian file. The 24-byte header is:

| Field | Type |
|---|---|
| magic `M7FRPLY\0` | 8 bytes |
| schema version (`1`) | `uint32` |
| physical frame count | `uint32` |
| neural sample count | `uint32` |
| field count (`11`) | `uint32` |

The body contains contiguous C-order arrays, without padding: physical time
`float64[Np]`, root position `float64[Np,3]`, root quaternion (MuJoCo
`w,x,y,z`) `float64[Np,4]`, 42 joint positions `float64[Np,42]`, neural time
`float64[Nn]`, then observer, decoder, and admitted contribution
`float64[Nn,11]`, sensory encoding `float64[Nn,6]`, delivered-drive count
`int64[Nn]`, and aggregate spikes/activity `int64[Nn]`. Values remain source
precision; scientific frames are not interpolated or converted. The manifest
records every offset, shape, dtype, artifact size, and SHA-256.

The 42 joint order is explicit: for each `LF, LM, LH, RF, RM, RH`, the order is
`Coxa, Coxa_roll, Coxa_yaw, Femur, Femur_roll, Tibia, Tarsus1`. The 11 motor
and six sensory identities are also explicit in the manifest.

## Contact identity audit

The frozen M7D recorder stored `36 x 3` force vectors, but neither it nor its
manifest preserved the ordered contact sensor identities, geom IDs/names, or
body IDs/names. Static inspection can therefore establish the channel count but
not the identity of any channel. M7F records all 36 as `UNKNOWN` with confidence
`UNRESOLVED`; it does not use magnitude, timing, symmetry, leg motion, visual
appearance, or gait expectations. Current classification is
`CONTACT_IDENTITY_MAPPING_UNRESOLVED`, which does not block replay.

A future resolution requires all of the following exact frozen metadata:

1. the ordered `contact_sensor_placements` supplied to the M7D Fly instance;
2. FlyGym 1.2.1 source defining contact-force observation ordering; and
3. MuJoCo 3.2.7 compiled geom/body IDs and names for that exact model.

It is permissible to load that exact model on Windows solely to read immutable
metadata, but no `env.step`, `physics.step`, `mj_step`, `Brain.step`, or neural
runtime stepping may occur. Until an identity-bearing artifact is captured,
M7F exports no per-leg contact booleans or forces and the viewer displays
**CONTACT IDENTITY UNAVAILABLE**. It never labels stance, swing, support phase,
or gait.

## Coordinates and interpolation

Scientific arrays remain FlyGym right-handed, Z-up source coordinates. At
render time only, the established project transform maps `[x,y,z]` to
`[x,z,y]`, using `1 mm = 0.1 Unity unit`. Root orientation is converted by
rotating source forward/up vectors with the recorded quaternion and applying
the same axis mapping.

Presentation interpolation is off by default. When off, the renderer uses the
exact selected recorded frame. When on, Unity may linearly/spherically blend
only what is displayed between adjacent canonical frames. Blends are never
saved, exported, or treated as evidence.

## Unity setup

After canonical export:

1. Create `FlyBrainUnity/Assets/StreamingAssets/M7FReplay/`.
2. Copy `m7f_manifest.json`, `m7f_contact_mapping.json`,
   `m7f_enabled_replay.bin`, and `m7f_disabled_replay.bin` from
   `malecns_backend/embodiment/interface_output/m7f_replay/` into it. Do not
   copy `m7d_raw.npz`.
3. Create a dedicated `M7F Canonical Replay` scene. Do not add the live TCP
   bridge to that scene; replay and live mode are independent.
4. Add `M7FReplayLoader` and set its directory to `M7FReplay`.
5. Instantiate two copies of the visual fly. Remove/disable colliders,
   rigidbodies, NavMesh, IK, procedural animation, locomotion, balance, and
   force/torque scripts. Add `M7FFlyRig` to each.
6. Populate each rig's explicit 42-entry binding table with the exact names
   listed above. Assign each transform and its actual rotation axis. Missing
   mappings produce a visible error and stop replay; neighboring bones are
   never substituted. The existing FBX is a visual representation of FlyGym,
   not asserted to be identical physical geometry.
7. Add `M7FReplayController`; assign loader and both rigs. Add
   `M7FScientificUI`. Add `M7FReplayCamera` to the camera and select the shared
   comparison target. Render a non-colliding ground plane as visual reference.
8. Enter Play mode. Confirm the provenance panel, SHA, `5001` physical states,
   `1000` neural updates, and both zero-transition declarations before capture.

The static tripod pose is inherited from M7D's frozen `init_pose="tripod"` and
its recorded time-zero state. It is initialization provenance, not evidence of
a tripod gait.

## Viewer behavior

Controls include play, pause, restart, exact frame back/forward, scrub, speeds
0.1x through 10x, enabled, disabled, side-by-side, and optional presentation
interpolation. Side-by-side uses one clock, identical scale, and symmetric
visual offsets; its label explicitly says the offsets are presentation-only.
Single-condition modes preserve source coordinates without offsets.

The scientific panel distinguishes observer, decoder, and physically applied
contribution for all 11 interfaces. It also shows six tibial sensory values,
delivered drive count, aggregate CNS activity/spikes, root position, body-up Z,
physical frame/time, and the corresponding (0.5-ms cadence) neural index/time.
The timeline cursor includes M7D D1/D3 through D10 markers imported with exact
values from M7D; UI labels are rounded. Navigation bookmarks are descriptive,
not new classifications.

Camera modes are free orbit, follow, fixed side, fixed top, and reset. Camera,
joint intensity styling, ground, offsets, and interpolation are presentation
only. Unity physics never determines replay motion.

## Known limitations

* Contact identity is unresolved, so contact overlays are deliberately absent.
* Joint bindings and axes must be configured against the imported FBX in the
  Unity Editor; no silent name guessing is performed.
* Side-by-side separation changes only presentation positions and is labeled.
* No walking, gait, tripod-support, biological locomotion, reflex, stance, or
  swing classifier exists in M7F.
